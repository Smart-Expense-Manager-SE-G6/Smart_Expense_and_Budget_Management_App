from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import Throttled
from rest_framework.throttling import ScopedRateThrottle


class ClientIpScopedThrottle(ScopedRateThrottle):
    """
    Scoped rate limit that always counts per client IP, even for signed-in
    sessions (the stock class switches to per-user once logged in, which
    would give every newly registered account a fresh allowance).
    """

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class LoginFailureGuard:
    """
    Limits failed logins per account without letting a third party lock the
    real user out:

    - per (email, client IP): only that IP is blocked for that account, so an
      attacker cannot stop the owner signing in from their own network;
    - per email across all IPs: a looser backstop against distributed guessing.

    Only failures count, and a successful login clears that IP's counter.
    Counters use fixed windows of LOGIN_FAILURE_WINDOW_SECONDS.
    """

    def __init__(self, email, client_ip):
        self.pair_key = f"login-fail:{email}:{client_ip}"
        self.account_key = f"login-fail:{email}"

    def check(self):
        if (
            cache.get(self.pair_key, 0) >= settings.LOGIN_FAILURES_PER_ACCOUNT_AND_IP
            or cache.get(self.account_key, 0) >= settings.LOGIN_FAILURES_PER_ACCOUNT
        ):
            raise Throttled(wait=settings.LOGIN_FAILURE_WINDOW_SECONDS)

    def record_failure(self):
        for key in (self.pair_key, self.account_key):
            # add() starts the window; incr() keeps its original expiry.
            if not cache.add(key, 1, timeout=settings.LOGIN_FAILURE_WINDOW_SECONDS):
                try:
                    cache.incr(key)
                except ValueError:  # expired between add() and incr()
                    cache.add(key, 1, timeout=settings.LOGIN_FAILURE_WINDOW_SECONDS)

    def record_success(self):
        cache.delete(self.pair_key)
