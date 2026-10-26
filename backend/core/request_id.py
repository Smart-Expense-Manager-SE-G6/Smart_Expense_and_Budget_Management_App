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
        request_id = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        request.request_id = request_id
        token = _current.set(request_id)
        started = time.monotonic()
        try:
            response = self.get_response(request)
            response[HEADER] = request_id
            logger.info(
                "%s %s %s %dms",
                request.method,
                request.get_full_path(),
                response.status_code,
                (time.monotonic() - started) * 1000,
            )
            # Already logged above with the request id; stops Django logging it
            # again after this middleware has returned and the id is gone.
            response._has_been_logged = True
            return response
        finally:
            _current.reset(token)


class RequestIdLogFilter(logging.Filter):
    """Adds record.request_id so log formats can use %(request_id)s."""

    def filter(self, record):
        record.request_id = get_request_id()
        return True
