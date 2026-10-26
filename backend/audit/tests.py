from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import include, path
from rest_framework import routers, serializers, viewsets

from .mixins import AuditedModelViewSetMixin
from .models import AuditLog
from .services import audited, log_change

# The User model stands in for any business model (expense, budget, ...).
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name"]


class UserViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


router = routers.SimpleRouter()
router.register("things", UserViewSet)
urlpatterns = [path("", include(router.urls))]


class AuditedContextManagerTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user("actor@example.com", password="x")

    def test_create_is_logged_with_after_snapshot(self):
        obj = User(email="new@example.com")
        with audited(self.actor, obj):
            obj.save()
        entry = AuditLog.objects.get()
        self.assertEqual(entry.action, "create")
        self.assertEqual(entry.entity_type, "accounts.user")
        self.assertEqual(entry.entity_id, str(obj.pk))
        self.assertEqual(entry.actor, self.actor)
        self.assertIsNone(entry.before)
        self.assertEqual(entry.after["email"], "new@example.com")

    def test_update_records_before_and_after(self):
        obj = User.objects.create_user("bob@example.com", password="x", first_name="Bob")
        with audited(self.actor, obj):
            obj.first_name = "Robert"
            obj.save()
        entry = AuditLog.objects.get()
        self.assertEqual(entry.action, "update")
        self.assertEqual(entry.before["first_name"], "Bob")
        self.assertEqual(entry.after["first_name"], "Robert")

    def test_password_is_never_recorded(self):
        obj = User.objects.create_user("carol@example.com", password="x")
        with audited(self.actor, obj):
            obj.set_password("new-secret")
            obj.save()
        entry = AuditLog.objects.get()
        self.assertNotIn("password", entry.before)
        self.assertNotIn("password", entry.after)

    def test_hard_delete_keeps_entity_id(self):
        obj = User.objects.create_user("dave@example.com", password="x")
        original_id = obj.pk
        with audited(self.actor, obj, action=AuditLog.Action.DELETE):
            obj.delete()
        entry = AuditLog.objects.get()
        self.assertEqual(entry.action, "delete")
        self.assertEqual(entry.entity_id, str(original_id))
        self.assertIsNone(entry.after)

    def test_failure_inside_block_rolls_back_change_and_audit(self):
        obj = User.objects.create_user("erin@example.com", password="x", first_name="Erin")
        with self.assertRaises(RuntimeError):
            with audited(self.actor, obj):
                obj.first_name = "Changed"
                obj.save()
                raise RuntimeError("business rule failed")
        obj.refresh_from_db()
        self.assertEqual(obj.first_name, "Erin")
        self.assertFalse(AuditLog.objects.exists())

    def test_audit_failure_rolls_back_the_change(self):
        obj = User.objects.create_user("frank@example.com", password="x", first_name="Frank")
        with patch("audit.services.log_change", side_effect=DatabaseError("audit insert failed")):
            with self.assertRaises(DatabaseError):
                with audited(self.actor, obj):
                    obj.first_name = "Changed"
                    obj.save()
        obj.refresh_from_db()
        self.assertEqual(obj.first_name, "Frank")



class OutsideTransactionTests(TransactionTestCase):
    """TestCase wraps every test in a transaction, so this needs TransactionTestCase."""

    def test_log_change_outside_transaction_is_refused(self):
        obj = User.objects.create_user("gina@example.com", password="x")
        with self.assertRaises(RuntimeError):
            log_change(obj, "update", obj)
        self.assertFalse(AuditLog.objects.exists())


class AppendOnlyTests(TestCase):
    def test_entries_cannot_be_modified_or_deleted(self):
        actor = User.objects.create_user("h@example.com", password="x")
        with transaction.atomic():
            entry = log_change(actor, "update", actor)
        entry.action = "delete"
        with self.assertRaises(ValueError):
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()


@override_settings(ROOT_URLCONF=__name__)
class AuditedViewSetMixinTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user("actor@example.com", password="x")
        self.client.force_login(self.actor)

    def test_create_update_delete_each_write_one_entry(self):
        created = self.client.post("/things/", {"email": "t@example.com"}, content_type="application/json")
        self.assertEqual(created.status_code, 201)
        thing_id = created.json()["id"]

        self.client.patch(f"/things/{thing_id}/", {"first_name": "T"}, content_type="application/json")
        self.client.delete(f"/things/{thing_id}/")

        actions = list(AuditLog.objects.order_by("id").values_list("action", "entity_id", "actor"))
        self.assertEqual(
            actions,
            [
                ("create", str(thing_id), self.actor.pk),
                ("update", str(thing_id), self.actor.pk),
                ("delete", str(thing_id), self.actor.pk),
            ],
        )

    def test_entry_carries_request_id(self):
        self.client.post(
            "/things/", {"email": "r@example.com"}, content_type="application/json", HTTP_X_REQUEST_ID="req-77"
        )
        self.assertEqual(AuditLog.objects.get().request_id, "req-77")
