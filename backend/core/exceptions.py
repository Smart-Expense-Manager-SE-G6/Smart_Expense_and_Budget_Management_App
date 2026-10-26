"""
SASD 4.4 error envelope. Every error response from the API has this shape:

    {"error": {"code": "...", "message": "...", "field": "..." | null, "request_id": "..."}}

Raise normal DRF exceptions (ValidationError, NotFound, PermissionDenied, ...)
in views and serializers; this handler converts them.
"""

import logging

from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .request_id import get_request_id

logger = logging.getLogger("api.error")


def error_body(code, message, field=None):
    return {"error": {"code": code, "message": message, "field": field, "request_id": get_request_id()}}


def _first_error(detail, field=None):
    """Walk DRF's nested error detail and return (field, ErrorDetail) of the first error."""
    if isinstance(detail, dict):
        for key, value in detail.items():
            if key in ("non_field_errors", "detail"):
                return _first_error(value, field)
            return _first_error(value, f"{field}.{key}" if field else str(key))
    if isinstance(detail, list) and detail:
        return _first_error(detail[0], field)
    return field, detail


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        # Not an API exception: an unexpected crash. Log it, hide the details.
        logger.exception("Unhandled exception", exc_info=exc)
        return Response(
            error_body("server_error", "Something went wrong. Please try again."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    field, detail = _first_error(exc.detail if hasattr(exc, "detail") else response.data)
    code = getattr(detail, "code", None) or getattr(exc, "default_code", "error")
    response.data = error_body(code, str(detail), field)
    return response


def handler404(request, exception=None):
    return JsonResponse(error_body("not_found", "Not found."), status=404)


def handler500(request):
    return JsonResponse(error_body("server_error", "Something went wrong. Please try again."), status=500)
