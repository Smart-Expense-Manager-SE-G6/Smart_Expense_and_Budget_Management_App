from rest_framework.authentication import SessionAuthentication


class SessionAuthentication401(SessionAuthentication):
    """
    Session auth that answers unauthenticated requests with 401 instead of 403.

    DRF only sends 401 when the auth class supplies a WWW-Authenticate value;
    the stock SessionAuthentication supplies none, so it falls back to 403.
    See docs/adr/0001-authentication-sessions.md.
    """

    def authenticate_header(self, request):
        return "Session"
