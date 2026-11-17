import logging
import threading
import time
from collections import deque

from django.conf import settings
from django.core.mail import send_mail

from core.request_id import get_request_id

logger = logging.getLogger("monitoring.errors")
_lock = threading.Lock()
_requests = deque()
_last_alert_at = None


def _prune(now, window_seconds):
    cutoff = now - window_seconds
    while _requests and _requests[0][0] < cutoff:
        _requests.popleft()


def reset_metrics():
    """Reset process-local metrics; intended for tests and worker initialization."""
    global _last_alert_at
    with _lock:
        _requests.clear()
        _last_alert_at = None


def _summary(now):
    window_seconds = settings.ERROR_RATE_WINDOW_SECONDS
    _prune(now, window_seconds)
    request_count = len(_requests)
    error_count = sum(status >= 500 for _, status, _ in _requests)
    slow_count = sum(duration >= settings.SLOW_REQUEST_THRESHOLD_MS for _, _, duration in _requests)
    rate = (error_count * 100 / request_count) if request_count else 0
    return {
        "window_seconds": window_seconds,
        "request_count": request_count,
        "error_count": error_count,
        "error_rate_percent": round(rate, 2),
        "slow_request_count": slow_count,
    }


def get_metrics():
    with _lock:
        return _summary(time.monotonic())


def _deliver_alert(recipient, summary, request_id):
    try:
        send_mail(
            subject="Smart Expense Manager: elevated HTTP 5xx rate",
            message=(
                f"{summary['error_count']} of {summary['request_count']} "
                f"requests failed with HTTP 5xx in the last "
                f"{summary['window_seconds']} seconds "
                f"({summary['error_rate_percent']}%)."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Could not deliver monitoring threshold alert")
        from monitoring.services import record_email_failure

        record_email_failure(
            recipient,
            "Elevated HTTP 5xx rate",
            "Monitoring alert email could not be delivered.",
            request_id=request_id,
        )


def _dispatch_alert(recipient, summary, request_id):
    worker = threading.Thread(
        target=_deliver_alert,
        args=(recipient, summary, request_id),
        name="monitoring-alert-email",
        daemon=True,
    )
    worker.start()


def record_request(status_code, duration_ms):
    """Track a request and dispatch a rate-limited email if its threshold trips."""
    global _last_alert_at
    now = time.monotonic()
    alert_summary = None
    with _lock:
        _requests.append((now, status_code, duration_ms))
        summary = _summary(now)
        if (
            summary["request_count"] >= settings.ERROR_RATE_MIN_REQUESTS
            and summary["error_rate_percent"] >= settings.ERROR_RATE_THRESHOLD_PERCENT
            and (
                _last_alert_at is None
                or now - _last_alert_at >= settings.ERROR_ALERT_COOLDOWN_SECONDS
            )
        ):
            _last_alert_at = now
            alert_summary = summary

    if alert_summary is not None:
        logger.error(
            "HTTP 5xx error-rate threshold exceeded",
            extra=alert_summary,
        )
        recipient = settings.MONITORING_ALERT_EMAIL
        if not recipient:
            logger.error("Monitoring alert email is not configured")
            return summary
        try:
            _dispatch_alert(recipient, alert_summary, get_request_id())
        except Exception:
            logger.exception("Could not start monitoring threshold alert")
    return summary
