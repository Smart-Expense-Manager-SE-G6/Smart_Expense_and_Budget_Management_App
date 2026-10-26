from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class LoginEmailThrottle(SimpleRateThrottle):
    """
    Limits login attempts per target account, whatever IP they come from,
    so one account cannot be brute-forced from many addresses.
    """

    scope = "login_email"

    def get_cache_key(self, request, view):
        data = request.data if hasattr(request.data, "get") else {}
        email = str(data.get("email", "")).strip().lower()
        if not email:
            return None
        return self.cache_format % {"scope": self.scope, "ident": email}


class ClientIpScopedThrottle(ScopedRateThrottle):
    """
    Scoped rate limit that always counts per client IP, even for signed-in
    sessions (the stock class switches to per-user once logged in, which
    would give every newly registered account a fresh allowance).
    """

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
