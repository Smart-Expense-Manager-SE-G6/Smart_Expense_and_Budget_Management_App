from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from rest_framework.throttling import ScopedRateThrottle

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


class CsrfTests(AuthApiTestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_user("alice@example.com", password=PASSWORD)
        self.csrf_client = Client(enforce_csrf_checks=True)

    def test_login_without_csrf_token_is_refused(self):
        response = self.post("/api/v1/auth/login/", {"email": "alice@example.com", "password": PASSWORD},
                             client=self.csrf_client)
        self.assertEqual(response.status_code, 403)

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
