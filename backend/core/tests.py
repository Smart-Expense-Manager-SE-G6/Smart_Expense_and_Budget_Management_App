from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import TestCase, override_settings
from django.urls import path, reverse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView


class ProtectedView(APIView):
    """Uses the project-wide default auth and permission classes."""

    def get(self, request):
        return Response({"user": request.user.username})


urlpatterns = [path("protected/", ProtectedView.as_view())]


class HealthCheckTests(TestCase):
    def test_health_returns_ok(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


@override_settings(ROOT_URLCONF=__name__)
class SessionAuthenticationTests(TestCase):
    """ADR 0001: anonymous, logged-out and expired credentials all get 401."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="s3cure-pass!")

    def test_anonymous_request_returns_401(self):
        self.assertEqual(self.client.get("/protected/").status_code, 401)

    def test_logged_in_request_succeeds(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/protected/").status_code, 200)

    def test_logged_out_session_returns_401(self):
        self.client.force_login(self.user)
        old_cookie = self.client.cookies["sessionid"].value
        self.client.logout()
        self.client.cookies["sessionid"] = old_cookie  # replay the old cookie
        self.assertEqual(self.client.get("/protected/").status_code, 401)

    def test_expired_session_returns_401(self):
        self.client.force_login(self.user)
        Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/protected/").status_code, 401)
