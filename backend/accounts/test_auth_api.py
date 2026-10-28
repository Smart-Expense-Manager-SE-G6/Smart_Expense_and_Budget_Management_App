from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from rest_framework.exceptions import Throttled
from rest_framework.throttling import ScopedRateThrottle

from accounts.throttles import LoginFailureGuard

from audit.models import AuditLog

User = get_user_model()
PASSWORD = "Tr1cky-Passw0rd!"


class AuthApiTestCase(TestCase):
    def setUp(self):
        cache.clear()  # login throttle counters live in the cache

    def post(self, url, data, client=None, **extra):
        return (client or self.client).post(url, data, content_type="application/json", **extra)

    def register(self, email="alice@example.com", password=PASSWORD, **fields):
        return self.post("/api/v1/auth/register/", {"email": email, "password": password, **fields})

    def login(self, email="alice@example.com", password=PASSWORD):
        return self.post("/api/v1/auth/login/", {"email": email, "password": password})


class TCAuth01RegisterTests(AuthApiTestCase):
    """TC-Auth-01: a new user can register and is signed in."""

    def test_register_creates_user_and_signs_in(self):
        response = self.register(first_name="Alice", timezone="Europe/London")
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["email"], "alice@example.com")
        self.assertEqual(body["timezone"], "Europe/London")
        self.assertNotIn("password", body)
        self.assertTrue(User.objects.get(email="alice@example.com").password.startswith("bcrypt_sha256$"))
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 200)

    def test_email_is_normalised_and_unique(self):
        self.register(email="Alice@Example.com")
        response = self.register(email="ALICE@example.com")
        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertEqual((error["code"], error["field"]), ("email_taken", "email"))

    def test_weak_password_rejected_on_password_field(self):
        response = self.register(password="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "password")
        self.assertFalse(User.objects.exists())

    def test_invalid_timezone_rejected(self):
        response = self.register(timezone="Mars/Olympus")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "timezone")

    def test_registration_is_rate_limited(self):
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"register": "2/min"}):
            statuses = [self.register(email=f"user{i}@example.com").status_code for i in range(3)]
        self.assertEqual(statuses, [201, 201, 429])

    def test_missing_email(self):
        response = self.post("/api/v1/auth/register/", {"password": PASSWORD})
        self.assertEqual(response.json()["error"]["field"], "email")


class TCAuth02LoginLogoutTests(AuthApiTestCase):
    """TC-Auth-02: a registered user can log in and out; bad credentials are refused."""

    def setUp(self):
        super().setUp()
        User.objects.create_user("alice@example.com", password=PASSWORD)

    def test_login_with_valid_credentials(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "alice@example.com")
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 200)

    def test_login_email_is_case_insensitive(self):
        self.assertEqual(self.login(email="ALICE@example.com").status_code, 200)

    def test_wrong_password_and_unknown_email_look_the_same(self):
        wrong_password = self.login(password="nope")
        unknown_email = self.login(email="nobody@example.com")
        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_email.status_code, 401)
        self.assertEqual(wrong_password.json()["error"]["message"], unknown_email.json()["error"]["message"])
        self.assertEqual(wrong_password.json()["error"]["code"], "invalid_credentials")

    def test_logout_invalidates_session(self):
        self.login()
        self.assertEqual(self.post("/api/v1/auth/logout/", {}).status_code, 204)
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 401)

    def test_login_rotates_session_key(self):
        self.client.get("/api/v1/auth/csrf/")
        self.client.session.save()
        before = self.client.session.session_key
        self.login()
        self.assertNotEqual(self.client.session.session_key, before)

    def test_login_is_rate_limited(self):
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"login": "3/min"}):
            statuses = [self.login(password="nope").status_code for _ in range(4)]
        self.assertEqual(statuses, [401, 401, 401, 429])

    def test_forged_forwarded_for_does_not_bypass_ip_limit(self):
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", {"login": "2/min"}):
            statuses = [
                self.post("/api/v1/auth/login/", {"email": f"u{i}@example.com", "password": "x"},
                          HTTP_X_FORWARDED_FOR=f"10.0.0.{i}").status_code
                for i in range(3)
            ]
        self.assertEqual(statuses, [401, 401, 429])

@override_settings(LOGIN_FAILURES_PER_ACCOUNT_AND_IP=3, LOGIN_FAILURES_PER_ACCOUNT=5)
class LoginFailureGuardTests(AuthApiTestCase):
    """Failed logins are limited per account without letting others lock the owner out."""

    def setUp(self):
        super().setUp()
        User.objects.create_user("alice@example.com", password=PASSWORD)

    def attempt(self, ip, password="nope"):
        return self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": password},
                         REMOTE_ADDR=ip).status_code

    def test_repeated_failures_block_that_ip_even_with_right_password(self):
        statuses = [self.attempt("10.0.0.1") for _ in range(3)]
        self.assertEqual(statuses, [401, 401, 401])
        self.assertEqual(self.attempt("10.0.0.1", PASSWORD), 429)

    def test_attacker_cannot_lock_owner_out_from_another_ip(self):
        for _ in range(4):
            self.attempt("10.6.6.6")
        self.assertEqual(self.attempt("192.168.1.10", PASSWORD), 200)

    def test_successful_logins_do_not_count(self):
        for _ in range(5):
            self.assertEqual(self.attempt("10.0.0.2", PASSWORD), 200)

    def test_success_resets_that_ips_failures(self):
        self.attempt("10.0.0.3")
        self.attempt("10.0.0.3")
        self.assertEqual(self.attempt("10.0.0.3", PASSWORD), 200)
        self.assertEqual([self.attempt("10.0.0.3") for _ in range(3)], [401, 401, 401])

    def test_distributed_guessing_hits_account_wide_limit_on_fresh_ips(self):
        statuses = [self.attempt(f"10.1.0.{i}") for i in range(6)]
        self.assertEqual(statuses, [401, 401, 401, 401, 401, 429])

    def test_trusted_device_gets_in_after_account_wide_cap(self):
        owner = Client()
        self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": PASSWORD},
                  client=owner, REMOTE_ADDR="192.168.1.10")
        owner.post("/api/v1/auth/logout/")
        for i in range(10):
            self.attempt(f"10.2.0.{i}")
        response = self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": PASSWORD},
                             client=owner, REMOTE_ADDR="192.168.1.10")
        self.assertEqual(response.status_code, 200)

    def test_new_device_waits_out_the_window_during_an_attack(self):
        for i in range(10):
            self.attempt(f"10.2.0.{i}")
        self.assertEqual(self.attempt("192.168.1.10", PASSWORD), 429)

    def test_password_change_revokes_trusted_device(self):
        owner = Client()
        self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": PASSWORD},
                  client=owner, REMOTE_ADDR="192.168.1.10")
        user = User.objects.get(email="alice@example.com")
        user.set_password("An0ther-Passw0rd!")
        user.save()
        for i in range(10):
            self.attempt(f"10.5.0.{i}")
        response = self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": "An0ther-Passw0rd!"},
                             client=owner, REMOTE_ADDR="192.168.1.10")
        self.assertEqual(response.status_code, 429)

    def test_trusted_cookie_is_bound_to_its_email(self):
        User.objects.create_user("bob@example.com", password=PASSWORD)
        device = Client()
        self.post("/api/v1/auth/login/", {"email": "bob@example.com", "password": PASSWORD}, client=device)
        for i in range(10):
            self.attempt(f"10.4.0.{i}")
        response = self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": PASSWORD},
                             client=device, REMOTE_ADDR="10.9.9.9")
        self.assertEqual(response.status_code, 429)

    def test_parallel_attempts_cannot_exceed_limit(self):
        # Reservations are counted before the password check, so the limit
        # holds even if the attempts are not awaited one by one.
        guard = LoginFailureGuard("alice@example.com", "10.3.0.1")
        for _ in range(3):
            guard.reserve_attempt()
        with self.assertRaises(Throttled):
            guard.reserve_attempt()


class CsrfTests(AuthApiTestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user("alice@example.com", password=PASSWORD)
        self.csrf_client = Client(enforce_csrf_checks=True)

    def test_login_without_csrf_token_is_refused(self):
        response = self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": PASSWORD},
                             client=self.csrf_client)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "csrf_failed")

    def test_login_with_csrf_token_from_csrf_endpoint(self):
        self.assertEqual(self.csrf_client.get("/api/v1/auth/csrf/").status_code, 204)
        token = self.csrf_client.cookies["csrftoken"].value
        response = self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": PASSWORD},
                             client=self.csrf_client, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)


class ProfileTests(AuthApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user("alice@example.com", password=PASSWORD, first_name="Alice")
        self.client.force_login(self.user)

    def test_view_profile(self):
        body = self.client.get("/api/v1/me/").json()
        self.assertEqual(set(body), {"id", "email", "first_name", "last_name", "timezone", "date_joined"})

    def test_edit_profile_persists_and_is_audited(self):
        response = self.client.patch("/api/v1/me/", {"first_name": "Alicia", "timezone": "Asia/Tokyo"},
                                     content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.timezone), ("Alicia", "Asia/Tokyo"))
        entry = AuditLog.objects.get()
        self.assertEqual((entry.before["first_name"], entry.after["first_name"]), ("Alice", "Alicia"))

    def test_email_cannot_be_changed(self):
        self.client.patch("/api/v1/me/", {"email": "evil@example.com"}, content_type="application/json")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "alice@example.com")

    def test_profile_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/me/").status_code, 401)
