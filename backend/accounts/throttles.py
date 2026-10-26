from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.crypto import constant_time_compare, salted_hmac
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
    Limits failed logins per account:

    - per (email, client IP): that IP is blocked for that account once it has
      too many failures;
    - per email across all IPs: a hard cap against distributed guessing that
      applies to every IP. Only a trusted device (one holding the signed cookie
      set after an earlier successful login for this email) may get past it,
      so an attacker cannot lock the owner out of devices they already use.

    Each attempt is reserved atomically before the password is checked (no
    check-then-record race); a successful login gives the reservation back.
    Counters use fixed windows of LOGIN_FAILURE_WINDOW_SECONDS. Production with
    several workers needs a shared cache backend (e.g. Redis) for this to hold.
    """

    def __init__(self, email, client_ip, trusted_device=False):
        self.pair_key = f"login-fail:{email}:{client_ip}"
        self.account_key = f"login-fail:{email}"
        self.trusted_device = trusted_device

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
        if pair > settings.LOGIN_FAILURES_PER_ACCOUNT_AND_IP or (
            account > settings.LOGIN_FAILURES_PER_ACCOUNT and not self.trusted_device
        ):
            raise Throttled(wait=settings.LOGIN_FAILURE_WINDOW_SECONDS)

    def release_after_success(self):
        cache.delete(self.pair_key)
        try:
            cache.decr(self.account_key)
        except ValueError:  # window already expired
            pass


TRUSTED_DEVICE_COOKIE = "trusted_device"
_TRUSTED_DEVICE_SALT = "accounts.trusted-device"


def _device_token(user):
    # Tied to the current password hash: changing the password revokes every
    # trusted-device cookie for the account. Survives logout on purpose.
    return f"{user.email}:{salted_hmac(_TRUSTED_DEVICE_SALT, user.password).hexdigest()}"


def is_trusted_device(request, email):
    value = request.get_signed_cookie(
        TRUSTED_DEVICE_COOKIE, default=None, salt=_TRUSTED_DEVICE_SALT,
        max_age=settings.TRUSTED_DEVICE_MAX_AGE_SECONDS,
    )
    if not value:
        return False
    user = get_user_model().objects.filter(email=email).only("email", "password").first()
    return user is not None and constant_time_compare(value, _device_token(user))


def mark_trusted_device(response, user):
    response.set_signed_cookie(
        TRUSTED_DEVICE_COOKIE, _device_token(user), salt=_TRUSTED_DEVICE_SALT,
        max_age=settings.TRUSTED_DEVICE_MAX_AGE_SECONDS,
        httponly=True, samesite="Lax", secure=not settings.DEBUG,
    )
