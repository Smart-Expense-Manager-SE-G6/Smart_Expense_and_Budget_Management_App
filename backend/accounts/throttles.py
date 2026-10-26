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

    - per (email, client IP): that IP is blocked for that account once it has
      too many failures;
    - per email across all IPs: a backstop against distributed guessing, but it
      only blocks IPs that already have a failure on this account, so the owner
      can always sign in from a clean network.

    Each attempt is reserved atomically before the password is checked (no
    check-then-record race); a successful login gives the reservation back.
    Counters use fixed windows of LOGIN_FAILURE_WINDOW_SECONDS. Production with
    several workers needs a shared cache backend (e.g. Redis) for this to hold.
    """

    def __init__(self, email, client_ip):
        self.pair_key = f"login-fail:{email}:{client_ip}"
        self.account_key = f"login-fail:{email}"

    @staticmethod
    def _incr(key):
        timeout = settings.LOGIN_FAILURE_WINDOW_SECONDS
        if cache.add(key, 1, timeout=timeout):  # starts the window
            return 1
        try:
            return cache.incr(key)  # keeps the original expiry
        except ValueError:  # expired between add() and incr()
            cache.add(key, 1, timeout=timeout)
            return 1

    def reserve_attempt(self):
        """Count this attempt as a failure up front; raise Throttled if over a limit."""
        pair = self._incr(self.pair_key)
        account = self._incr(self.account_key)
        ip_has_failures = pair > 1
        if pair > settings.LOGIN_FAILURES_PER_ACCOUNT_AND_IP or (
            ip_has_failures and account > settings.LOGIN_FAILURES_PER_ACCOUNT
        ):
            raise Throttled(wait=settings.LOGIN_FAILURE_WINDOW_SECONDS)

    def release_after_success(self):
        cache.delete(self.pair_key)
        try:
            cache.decr(self.account_key)
        except ValueError:  # window already expired
            pass
