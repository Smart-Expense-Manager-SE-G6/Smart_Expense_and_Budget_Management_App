import logging

from django.test import TestCase, override_settings
from django.urls import path
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

from .request_id import RequestIdLogFilter, _current


class AmountSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class ValidateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        AmountSerializer(data=request.data).is_valid(raise_exception=True)
        return Response({"ok": True})


class MissingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise NotFound("Expense not found.")


class CrashView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise RuntimeError("boom")


class PrivateView(APIView):
    def get(self, request):
        return Response({})


urlpatterns = [
    path("validate/", ValidateView.as_view()),
    path("missing/", MissingView.as_view()),
    path("crash/", CrashView.as_view()),
    path("private/", PrivateView.as_view()),
]


@override_settings(ROOT_URLCONF=__name__)
class ErrorEnvelopeTests(TestCase):
    """SASD 4.4: every error has {error: {code, message, field, request_id}}."""

    def assertEnvelope(self, response, status, code, field=None):
        self.assertEqual(response.status_code, status)
        error = response.json()["error"]
        self.assertEqual(set(error), {"code", "message", "field", "request_id"})
        self.assertEqual(error["code"], code)
        self.assertEqual(error["field"], field)
        self.assertEqual(error["request_id"], response["X-Request-ID"])
        return error

    def test_validation_error_names_the_field(self):
        response = self.client.post("/validate/", {"amount": "abc"}, content_type="application/json")
        self.assertEnvelope(response, 400, "invalid", field="amount")

    def test_missing_field(self):
        response = self.client.post("/validate/", {}, content_type="application/json")
        self.assertEnvelope(response, 400, "required", field="amount")

    def test_not_found(self):
        error = self.assertEnvelope(self.client.get("/missing/"), 404, "not_found")
        self.assertEqual(error["message"], "Expense not found.")

    def test_unauthenticated(self):
        self.assertEnvelope(self.client.get("/private/"), 401, "not_authenticated")

    def test_method_not_allowed(self):
        self.assertEnvelope(self.client.delete("/missing/"), 405, "method_not_allowed")

    def test_unhandled_exception_hides_details(self):
        with self.assertLogs("api.error", level="ERROR"):
            error = self.assertEnvelope(self.client.get("/crash/"), 500, "server_error")
        self.assertNotIn("boom", error["message"])


class UnknownApiUrlTests(TestCase):
    def test_unknown_api_url_returns_envelope(self):
        response = self.client.get("/api/v1/does-not-exist/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "not_found")


@override_settings(ROOT_URLCONF=__name__)
class RequestIdTests(TestCase):
    def test_request_id_generated(self):
        response = self.client.get("/missing/")
        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_safe_incoming_request_id_is_reused(self):
        response = self.client.get("/missing/", HTTP_X_REQUEST_ID="abc-123")
        self.assertEqual(response["X-Request-ID"], "abc-123")
        self.assertEqual(response.json()["error"]["request_id"], "abc-123")

    def test_unsafe_incoming_request_id_is_replaced(self):
        response = self.client.get("/missing/", HTTP_X_REQUEST_ID="bad id\nwith newline")
        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_each_request_is_logged_with_its_id(self):
        with self.assertLogs("api.request", level="INFO") as logs:
            response = self.client.get("/missing/", HTTP_X_REQUEST_ID="trace-me")
        self.assertEqual(response.status_code, 404)
        self.assertIn("GET /missing/ 404", logs.output[0])

    def test_log_filter_stamps_current_request_id(self):
        record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", None, None)
        token = _current.set("req-42")
        try:
            RequestIdLogFilter().filter(record)
        finally:
            _current.reset(token)
        self.assertEqual(getattr(record, "request_id"), "req-42")
