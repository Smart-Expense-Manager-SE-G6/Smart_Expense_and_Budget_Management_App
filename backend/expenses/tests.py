from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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
        body = response.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual([item["id"] for item in body["results"]], [own.pk])

    def create_expense(self, **overrides):
        values = {
            "owner": self.user,
            "category": self.custom_category,
            "amount": Decimal("10.00"),
            "date": date(2026, 10, 26),
        }
        values.update(overrides)
        return Expense.objects.create(**values)

    def list_ids(self, query=""):
        response = self.client.get(f"/expenses/{query}")
        self.assertEqual(response.status_code, 200)
        return [item["id"] for item in response.json()["results"]]

    def test_list_filters_by_category(self):
        matching = self.create_expense(category=self.custom_category)
        self.create_expense(category=self.global_category)

        self.assertEqual(self.list_ids(f"?category={self.custom_category.pk}"), [matching.pk])

    def test_list_filters_by_inclusive_date_range(self):
        before = self.create_expense(date=date(2026, 1, 1))
        matching = self.create_expense(date=date(2026, 6, 15))
        after = self.create_expense(date=date(2026, 12, 31))

        ids = self.list_ids("?start_date=2026-06-15&end_date=2026-06-15")

        self.assertEqual(ids, [matching.pk])
        self.assertNotIn(before.pk, ids)
        self.assertNotIn(after.pk, ids)

    def test_list_sorts_by_date_and_amount(self):
        oldest = self.create_expense(date=date(2026, 1, 1), amount=Decimal("30.00"))
        newest = self.create_expense(date=date(2026, 12, 1), amount=Decimal("10.00"))
        middle = self.create_expense(date=date(2026, 6, 1), amount=Decimal("20.00"))

        self.assertEqual(
            self.list_ids("?ordering=date"),
            [oldest.pk, middle.pk, newest.pk],
        )
        self.assertEqual(
            self.list_ids("?ordering=-date"),
            [newest.pk, middle.pk, oldest.pk],
        )
        self.assertEqual(
            self.list_ids("?ordering=amount"),
            [newest.pk, middle.pk, oldest.pk],
        )
        self.assertEqual(
            self.list_ids("?ordering=-amount"),
            [oldest.pk, middle.pk, newest.pk],
        )

    def test_list_uses_deterministic_default_ordering(self):
        first = self.create_expense(date=date(2026, 10, 26))
        second = self.create_expense(date=date(2026, 10, 26))

        self.assertEqual(self.list_ids(), [second.pk, first.pk])

    def test_list_paginates_with_default_and_requested_page_sizes(self):
        for index in range(25):
            self.create_expense(amount=Decimal(index + 1))

        default_response = self.client.get("/expenses/")
        requested_response = self.client.get("/expenses/?page=2&page_size=5")

        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(default_response.json()["count"], 25)
        self.assertEqual(len(default_response.json()["results"]), 20)
        self.assertEqual(requested_response.status_code, 200)
        self.assertEqual(len(requested_response.json()["results"]), 5)
        self.assertIsNotNone(requested_response.json()["previous"])

    def test_list_rejects_page_size_above_maximum(self):
        response = self.client.get("/expenses/?page_size=101")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "page_size")

    def test_list_rejects_invalid_page_and_page_size(self):
        for parameter in ("page=0", "page=-1", "page=abc", "page_size=0", "page_size=-1", "page_size=abc"):
            response = self.client.get(f"/expenses/?{parameter}")
            self.assertEqual(response.status_code, 400, parameter)
            self.assertEqual(response.json()["error"]["field"], parameter.split("=")[0])

    def test_list_rejects_invalid_filters_and_ordering(self):
        cases = [
            ("?start_date=not-a-date", "start_date"),
            ("?end_date=2026-02-30", "end_date"),
            ("?start_date=2026-12-01&end_date=2026-01-01", "date_range"),
            ("?category=abc", "category"),
            ("?category=999999", "category"),
            ("?ordering=owner", "ordering"),
        ]
        for query, field in cases:
            response = self.client.get(f"/expenses/{query}")
            self.assertEqual(response.status_code, 400, query)
            self.assertEqual(response.json()["error"]["field"], field)

    def test_filters_preserve_user_isolation_and_soft_delete(self):
        own = self.create_expense(date=date(2026, 5, 1))
        Expense.objects.create(
            owner=self.other_user,
            category=self.custom_category,
            amount=Decimal("20.00"),
            date=date(2026, 5, 1),
        )
        deleted = self.create_expense(date=date(2026, 5, 1), is_deleted=True)

        ids = self.list_ids("?start_date=2026-05-01&end_date=2026-05-01")

        self.assertEqual(ids, [own.pk])
        self.assertNotIn(deleted.pk, ids)

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

    @override_settings(RECEIPT_MAX_SIZE_BYTES=1024)
    def test_receipt_upload_retrieval_and_deletion(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                expense = self.create_expense()
                upload = SimpleUploadedFile(
                    "receipt.png",
                    b"\x89PNG\r\n\x1a\nreceipt",
                    content_type="image/png",
                )

                upload_response = self.client.post(
                    f"/expenses/{expense.pk}/receipt/",
                    {"receipt": upload},
                    format="multipart",
                )

                self.assertEqual(upload_response.status_code, 201)
                expense.refresh_from_db()
                self.assertTrue(expense.receipt.name.startswith(f"receipts/{self.user.pk}/"))
                self.assertNotIn("receipt.png", expense.receipt.name)
                stored_path = Path(media_root, expense.receipt.name)
                self.assertTrue(stored_path.is_file())
                self.assertEqual(AuditLog.objects.filter(entity_type="expenses.expense").count(), 1)

                retrieve_response = self.client.get(f"/expenses/{expense.pk}/receipt/")

                self.assertEqual(retrieve_response.status_code, 200)
                self.assertEqual(retrieve_response["Content-Type"], "image/png")
                self.assertIn("attachment", retrieve_response["Content-Disposition"])
                self.assertNotIn("private_media", retrieve_response.get("Content-Location", ""))
                self.assertNotIn("receipt.png", retrieve_response["Content-Disposition"])
                self.assertEqual(b"".join(retrieve_response.streaming_content), b"\x89PNG\r\n\x1a\nreceipt")

                delete_response = self.client.delete(f"/expenses/{expense.pk}/receipt/")

                self.assertEqual(delete_response.status_code, 204)
                expense.refresh_from_db()
                self.assertFalse(expense.receipt)
                self.assertFalse(stored_path.exists())
                self.assertEqual(AuditLog.objects.filter(entity_type="expenses.expense").count(), 2)

    def test_rejects_invalid_receipts_and_missing_receipts(self):
        expense = self.create_expense()
        invalid_extension = SimpleUploadedFile(
            "receipt.exe",
            b"MZnot-an-image",
            content_type="application/octet-stream",
        )
        invalid_content = SimpleUploadedFile(
            "receipt.png",
            b"not-a-png",
            content_type="image/png",
        )

        invalid_extension_response = self.client.post(
            f"/expenses/{expense.pk}/receipt/",
            {"receipt": invalid_extension},
            format="multipart",
        )
        invalid_content_response = self.client.post(
            f"/expenses/{expense.pk}/receipt/",
            {"receipt": invalid_content},
            format="multipart",
        )
        missing_response = self.client.get(f"/expenses/{expense.pk}/receipt/")

        self.assertEqual(invalid_extension_response.status_code, 400)
        self.assertEqual(invalid_content_response.status_code, 400)
        self.assertEqual(missing_response.status_code, 400)

    @override_settings(RECEIPT_MAX_SIZE_BYTES=8)
    def test_rejects_oversized_receipts(self):
        expense = self.create_expense()
        oversized = SimpleUploadedFile(
            "receipt.png",
            b"\x89PNG\r\n\x1a\nlarge",
            content_type="image/png",
        )

        response = self.client.post(
            f"/expenses/{expense.pk}/receipt/",
            {"receipt": oversized},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)

    def test_receipt_replacement_is_rejected(self):
        expense = self.create_expense()
        first = SimpleUploadedFile(
            "first.pdf",
            b"%PDF-1.7 first",
            content_type="application/pdf",
        )
        second = SimpleUploadedFile(
            "second.pdf",
            b"%PDF-1.7 second",
            content_type="application/pdf",
        )

        first_response = self.client.post(
            f"/expenses/{expense.pk}/receipt/",
            {"receipt": first},
            format="multipart",
        )
        second_response = self.client.post(
            f"/expenses/{expense.pk}/receipt/",
            {"receipt": second},
            format="multipart",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 400)

    def test_receipt_operations_are_owner_and_authentication_isolated(self):
        own_expense = self.create_expense()
        other_expense = Expense.objects.create(
            owner=self.other_user,
            category=self.global_category,
            amount=Decimal("10.00"),
            date=date(2026, 10, 26),
        )
        upload = SimpleUploadedFile(
            "receipt.pdf",
            b"%PDF-1.7 receipt",
            content_type="application/pdf",
        )

        other_response = self.client.post(
            f"/expenses/{other_expense.pk}/receipt/",
            {"receipt": upload},
            format="multipart",
        )
        self.assertEqual(other_response.status_code, 404)

        self.client.logout()
        unauthenticated_response = self.client.get(
            f"/expenses/{own_expense.pk}/receipt/"
        )
        self.assertEqual(unauthenticated_response.status_code, 401)
