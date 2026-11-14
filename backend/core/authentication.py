from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied


class SessionAuthentication401(SessionAuthentication):
    """
    Session auth that answers unauthenticated requests with 401 instead of 403.

    DRF only sends 401 when the auth class supplies a WWW-Authenticate value;
    the stock SessionAuthentication supplies none, so it falls back to 403.
    See docs/adr/0001-authentication-sessions.md.
    """

    def authenticate_header(self, request):
        return "Session"

    def enforce_csrf(self, request):
        # Same code and message as Django's CSRF failure view (core.exceptions.csrf_failure),
        # so the frontend sees one error for one problem.
        try:
            super().enforce_csrf(request)
        except PermissionDenied as exc:
            raise PermissionDenied(
                "CSRF check failed. Reload the page and try again.", code="csrf_failed"
            ) from exc
