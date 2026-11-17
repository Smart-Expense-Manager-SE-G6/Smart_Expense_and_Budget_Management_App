import json
import logging
import tempfile
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.adapters.email import DjangoEmailAdapter
from core.request_id import RequestIdMiddleware
from .logging import JsonFormatter
from .metrics import get_metrics, record_request, reset_metrics
from .models import EmailDeliveryFailure
from .status_files import read_job_status


class JsonLoggingTests(SimpleTestCase):
    def test_json_log_is_searchable_by_request_id_and_includes_context(self):
        record = logging.LogRecord(
            "api.request",
            logging.ERROR,
            __file__,
            1,
            "http.request",
            None,
            None,
        )
        record.request_id = "request-123"
        record.status_code = 503
        record.duration_ms = 25.5

        payload = json.loads(JsonFormatter().format(record))

        self.assertEqual(payload["request_id"], "request-123")
        self.assertEqual(payload["severity"], "ERROR")
        self.assertEqual(payload["status_code"], 503)
        self.assertEqual(payload["duration_ms"], 25.5)

    def test_application_and_error_logs_are_distinct_rotating_files(self):
        handlers = settings.LOGGING["handlers"]
        self.assertIn("RotatingFileHandler", handlers["application_file"]["class"])
        self.assertIn("RotatingFileHandler", handlers["error_file"]["class"])
        self.assertNotEqual(handlers["application_file"]["filename"], handlers["error_file"]["filename"])
        self.assertEqual(handlers["error_file"]["level"], "ERROR")

    def test_rotating_handler_keeps_a_previous_log(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "application.log"
            handler = RotatingFileHandler(path, maxBytes=120, backupCount=2, encoding="utf-8")
            handler.setFormatter(JsonFormatter())
            try:
                logger = logging.getLogger(f"monitoring.rotation.{id(handler)}")
                logger.addHandler(handler)
                logger.setLevel(logging.INFO)
                logger.propagate = False
                for index in range(5):
                    logger.info("rotating-log-entry-%s-%s", index, "x" * 50)
                handler.flush()
                self.assertTrue(Path(f"{path}.1").exists())
            finally:
                logger.removeHandler(handler)
                handler.close()


@override_settings(
    ERROR_RATE_WINDOW_SECONDS=300,
    ERROR_RATE_MIN_REQUESTS=3,
    ERROR_RATE_THRESHOLD_PERCENT=50,
    ERROR_ALERT_COOLDOWN_SECONDS=600,
    SLOW_REQUEST_THRESHOLD_MS=100,
    MONITORING_ALERT_EMAIL="ops@example.com",
)
class ErrorMonitoringTests(SimpleTestCase):
    def setUp(self):
        reset_metrics()

    def tearDown(self):
        reset_metrics()

    @patch("monitoring.metrics._dispatch_alert")
    def test_5xx_rate_threshold_alerts_and_suppresses_duplicates(self, dispatch_alert):
        record_request(200, 20)
        record_request(200, 20)
        record_request(500, 20)
        summary = record_request(503, 20)

        self.assertEqual(summary["error_count"], 2)
        self.assertEqual(summary["error_rate_percent"], 50)
        dispatch_alert.assert_called_once()

        record_request(500, 20)
        dispatch_alert.assert_called_once()

    @patch("monitoring.metrics.threading.Thread")
    def test_alert_delivery_runs_in_a_daemon_thread(self, thread):
        from .metrics import _dispatch_alert

        _dispatch_alert("ops@example.com", {"error_count": 1}, "request-1")

        thread.assert_called_once()
        thread.return_value.start.assert_called_once()
        self.assertTrue(thread.call_args.kwargs["daemon"])

    @patch("monitoring.services.record_email_failure")
    @patch("monitoring.metrics.send_mail", side_effect=OSError("smtp failure"))
    def test_failed_monitoring_email_is_recorded_without_raising(self, send_mail, record_failure):
        from .metrics import _deliver_alert

        _deliver_alert("ops@example.com", {
            "error_count": 1,
            "request_count": 1,
            "window_seconds": 300,
            "error_rate_percent": 100,
        }, "request-1")

        send_mail.assert_called_once()
        record_failure.assert_called_once()
        self.assertEqual(record_failure.call_args.kwargs["request_id"], "request-1")

    def test_slow_requests_are_counted(self):
        record_request(200, 101)
        record_request(500, 20)

        self.assertEqual(get_metrics()["slow_request_count"], 1)
        self.assertEqual(get_metrics()["error_count"], 1)

    def test_request_middleware_tracks_http_5xx_and_propagates_id(self):
        from django.http import HttpResponse
        from django.test import RequestFactory

        response = RequestIdMiddleware(lambda request: HttpResponse(status=503))(
            RequestFactory().get("/failure/", HTTP_X_REQUEST_ID="trace-503")
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["X-Request-ID"], "trace-503")
        self.assertEqual(get_metrics()["error_count"], 1)

    @patch("monitoring.metrics.record_request", side_effect=RuntimeError("metrics unavailable"))
    def test_metrics_failure_does_not_change_application_response(self, record):
        from django.http import HttpResponse
        from django.test import RequestFactory

        with self.assertLogs("api.request", level="ERROR"):
            response = RequestIdMiddleware(lambda request: HttpResponse("ok", status=200))(
                RequestFactory().get("/healthy/")
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
        record.assert_called_once()


class JobStatusFileTests(SimpleTestCase):
    def test_missing_status_is_unknown_and_valid_status_is_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with override_settings(MONITORING_STATE_DIR=root):
                self.assertEqual(read_job_status("backup", 3600)["status"], "unknown")
                (root / "backup.json").write_text(
                    json.dumps(
                        {
                            "status": "healthy",
                            "message": "Backup completed.",
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                    encoding="utf-8",
                )
                self.assertEqual(read_job_status("backup", 3600)["status"], "healthy")

    def test_stale_status_is_not_reported_as_healthy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "budget-scheduler.json"
            path.write_text(
                json.dumps({"status": "healthy", "updated_at": "2000-01-01T00:00:00+00:00"}),
                encoding="utf-8",
            )
            with override_settings(MONITORING_STATE_DIR=Path(directory)):
                self.assertEqual(read_job_status("budget-scheduler", 60)["status"], "stale")


class EmailFailureTrackingTests(TestCase):
    @patch("core.adapters.email.send_mail", side_effect=OSError("smtp failure"))
    def test_failed_email_is_persisted_with_masked_recipient_and_request_id(self, send_mail):
        result = DjangoEmailAdapter().send_email(
            "person@example.com",
            "Budget notice",
            "Message body",
        )

        self.assertFalse(result.success)
        failure = EmailDeliveryFailure.objects.get()
        self.assertEqual(failure.recipient, "p***@example.com")
        self.assertEqual(failure.subject, "Budget notice")
        self.assertEqual(failure.request_id, "-")
        send_mail.assert_called_once()

    @patch("monitoring.models.EmailDeliveryFailure.objects.create", side_effect=RuntimeError("tracking unavailable"))
    @patch("core.adapters.email.send_mail", side_effect=OSError("smtp failure"))
    def test_failure_tracking_error_does_not_replace_email_result(self, send_mail, record_failure):
        result = DjangoEmailAdapter().send_email("person@example.com", "Notice", "Body")

        self.assertFalse(result.success)
        self.assertEqual(result.message, "Email delivery failed.")
        send_mail.assert_called_once()
        record_failure.assert_called_once()


class MonitoringDashboardTests(TestCase):
    def setUp(self):
        # An empty status folder of our own: in Docker the real scheduler and backup
        # services write their status into the shared folder, so these tests must not read it.
        state_dir = tempfile.TemporaryDirectory()
        self.addCleanup(state_dir.cleanup)
        isolated = override_settings(MONITORING_STATE_DIR=Path(state_dir.name))
        isolated.enable()
        self.addCleanup(isolated.disable)
        self.admin = get_user_model().objects.create_superuser(
            email="monitor@example.com",
            password="Secure-test-password-2026!",
        )
        self.client.force_login(self.admin)
        reset_metrics()

    def tearDown(self):
        reset_metrics()

    def test_dashboard_returns_runtime_and_dependency_status(self):
        response = self.client.get(reverse("monitoring-dashboard"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["backend"]["status"], "healthy")
        self.assertEqual(data["database"]["status"], "healthy")
        self.assertEqual(data["budget_scheduler"]["status"], "unknown")
        self.assertEqual(data["backup"]["status"], "unknown")
        self.assertIn("error_rate_percent", data["errors"])
        self.assertEqual(data["email"]["latest_failures"], [])

    @patch("monitoring.views.connection")
    def test_dashboard_reports_database_failure(self, database):
        database.cursor.side_effect = OSError("database unavailable")

        response = self.client.get(reverse("monitoring-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["database"]["status"], "unhealthy")

    def test_dashboard_is_admin_only(self):
        self.client.logout()
        ordinary_user = get_user_model().objects.create_user(
            email="user@example.com",
            password="Secure-test-password-2026!",
        )
        self.client.force_login(ordinary_user)

        self.assertEqual(self.client.get(reverse("monitoring-dashboard")).status_code, 403)

    def test_dashboard_reports_latest_email_failures(self):
        EmailDeliveryFailure.objects.create(
            recipient="p***@example.com",
            subject="Budget alert",
            reason="Email backend raised an exception.",
            request_id="request-77",
        )

        response = self.client.get(reverse("monitoring-dashboard"))

        self.assertEqual(response.status_code, 200)
        failure = response.json()["email"]["latest_failures"][0]
        self.assertEqual(failure["recipient"], "p***@example.com")
        self.assertEqual(failure["request_id"], "request-77")
