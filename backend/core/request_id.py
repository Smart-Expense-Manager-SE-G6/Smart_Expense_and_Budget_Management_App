"""
Request id plumbing (NFR12): every request gets an id that is returned in the
X-Request-ID response header, included in error envelopes, and stamped on
every log line written while the request is being handled.
"""

import contextvars
import logging
import re
import time
import uuid

HEADER = "X-Request-ID"
_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_current = contextvars.ContextVar("request_id", default="-")

logger = logging.getLogger("api.request")


def get_request_id():
    """The id of the request being handled, or "-" outside a request."""
    return _current.get()


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get(HEADER, "")
        request_id = incoming if _SAFE_ID.fullmatch(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        token = _current.set(request_id)
        started = time.monotonic()
        try:
            try:
                response = self.get_response(request)
            except Exception:
                duration_ms = round((time.monotonic() - started) * 1000, 2)
                logger.exception(
                    "Unhandled request exception",
                    extra={
                        "http_method": request.method,
                        "path": request.path,
                        "status_code": 500,
                        "duration_ms": duration_ms,
                    },
                )
                self._record_request(500, duration_ms)
                raise

            response[HEADER] = request_id
            duration_ms = round((time.monotonic() - started) * 1000, 2)
            status_code = response.status_code
            level = logging.ERROR if status_code >= 500 else (
                logging.WARNING if duration_ms >= self._slow_threshold() else logging.INFO
            )
            logger.log(
                level,
                "http.request",
                extra={
                    "http_method": request.method,
                    "path": request.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            self._record_request(status_code, duration_ms)
            response._has_been_logged = True
            return response
        finally:
            _current.reset(token)

    @staticmethod
    def _slow_threshold():
        from django.conf import settings

        return settings.SLOW_REQUEST_THRESHOLD_MS

    @staticmethod
    def _record_request(status_code, duration_ms):
        from monitoring.metrics import record_request

        try:
            record_request(status_code, duration_ms)
        except Exception:
            logger.exception("Request monitoring failed")


class RequestIdLogFilter(logging.Filter):
    """Adds record.request_id so log formats can use %(request_id)s."""

    def filter(self, record):
        record.request_id = get_request_id()
        return True
