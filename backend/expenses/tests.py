from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import include, path
from rest_framework import routers

from audit.models import AuditLog

from .models import Category, Expense
from .views import ExpenseViewSet


router = routers.DefaultRouter()
router.register("expenses", ExpenseViewSet, basename="expense")
urlpatterns = [path("", include(router.urls))]


@override_settings(ROOT_URLCONF=__name__)
class ExpenseApiTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user("alice@example.com", "s3cure-pass!")
        self.other_user = self.User.objects.create_user("bob@example.com", "s3cure-pass!")
        self.global_category = Category.objects.create(name="Food")
        self.custom_category = Category.objects.create(name="Travel", owner=self.user)
        self.client.force_login(self.user)

    def payload(self, **overrides):
        payload = {
            "category": self.custom_category.pk,
            "amount": "125.50",
            "description": "Lunch",
            "date": "2026-10-26",
            "payment_method": "UPI",
        }
        payload.update(overrides)
        return payload

    def test_list_returns_only_active_expenses_owned_by_user(self):
        own = Expense.objects.create(
            owner=self.user,
            category=self.custom_category,
            amount=Decimal("10.00"),
            date=date(2026, 10, 26),
        )
        Expense.objects.create(
            owner=self.other_user,
            category=self.global_category,
            amount=Decimal("20.00"),
            date=date(2026, 10, 26),
        )
        Expense.objects.create(
            owner=self.user,
            category=self.global_category,
            amount=Decimal("30.00"),
            date=date(2026, 10, 26),
            is_deleted=True,
        )

        response = self.client.get("/expenses/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [own.pk])

    def test_create_assigns_authenticated_owner_and_writes_audit_entry(self):
        response = self.client.post(
            "/expenses/",
            self.payload(owner=self.other_user.pk),
            content_type="application/json",
            HTTP_X_REQUEST_ID="expense-create",
        )

        self.assertEqual(response.status_code, 201)
        expense = Expense.objects.get()
        self.assertEqual(expense.owner, self.user)
        self.assertEqual(expense.amount, Decimal("125.50"))
        self.assertEqual(response.json()["owner"], self.user.pk)
        audit = AuditLog.objects.get(entity_type="expenses.expense")
        self.assertEqual(audit.action, AuditLog.Action.CREATE)
        self.assertEqual(audit.request_id, "expense-create")

    def test_rejects_another_users_category(self):
        category = Category.objects.create(name="Private", owner=self.other_user)

        response = self.client.post(
            "/expenses/",
            self.payload(category=category.pk),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "category")

    def test_rejects_inactive_category(self):
        self.custom_category.is_active = False
        self.custom_category.save(update_fields=["is_active"])

        response = self.client.post(
            "/expenses/",
            self.payload(),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "category")

    def test_retrieve_and_patch_are_limited_to_active_owned_expenses(self):
        expense = Expense.objects.create(
            owner=self.user,
            category=self.custom_category,
            amount=Decimal("10.00"),
            date=date(2026, 10, 26),
        )

        retrieve = self.client.get(f"/expenses/{expense.pk}/")
        patch = self.client.patch(
            f"/expenses/{expense.pk}/",
            {"amount": "11.25"},
            content_type="application/json",
        )

        self.assertEqual(retrieve.status_code, 200)
        self.assertEqual(patch.status_code, 200)
        expense.refresh_from_db()
        self.assertEqual(expense.amount, Decimal("11.25"))
        self.assertEqual(AuditLog.objects.filter(entity_type="expenses.expense").count(), 1)

    def test_other_users_expense_is_not_exposed(self):
        expense = Expense.objects.create(
            owner=self.other_user,
            category=self.global_category,
            amount=Decimal("10.00"),
            date=date(2026, 10, 26),
        )

        response = self.client.get(f"/expenses/{expense.pk}/")

        self.assertEqual(response.status_code, 404)

    def test_delete_soft_deletes_and_audits_expense(self):
        expense = Expense.objects.create(
            owner=self.user,
            category=self.custom_category,
            amount=Decimal("10.00"),
            date=date(2026, 10, 26),
        )

        response = self.client.delete(
            f"/expenses/{expense.pk}/",
            HTTP_X_REQUEST_ID="expense-delete",
        )

        self.assertEqual(response.status_code, 204)
        expense.refresh_from_db()
        self.assertTrue(expense.is_deleted)
        self.assertFalse(Expense.objects.filter(pk=expense.pk, is_deleted=False).exists())
        audit = AuditLog.objects.get(entity_type="expenses.expense")
        self.assertEqual(audit.action, AuditLog.Action.UPDATE)
        self.assertEqual(audit.request_id, "expense-delete")

    def test_deleted_expense_cannot_be_retrieved_updated_or_deleted_again(self):
        expense = Expense.objects.create(
            owner=self.user,
            category=self.custom_category,
            amount=Decimal("10.00"),
            date=date(2026, 10, 26),
            is_deleted=True,
        )

        self.assertEqual(self.client.get(f"/expenses/{expense.pk}/").status_code, 404)
        self.assertEqual(
            self.client.patch(
                f"/expenses/{expense.pk}/",
                {"amount": "12.00"},
                content_type="application/json",
            ).status_code,
            404,
        )
        self.assertEqual(self.client.delete(f"/expenses/{expense.pk}/").status_code, 404)

    def test_unauthenticated_requests_return_401(self):
        self.client.logout()

        response = self.client.get("/expenses/")

        self.assertEqual(response.status_code, 401)
