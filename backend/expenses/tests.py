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
from .services import suggest_categories
from .views import CategoryViewSet, ExpenseViewSet


router = routers.DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("expenses", ExpenseViewSet, basename="expense")
urlpatterns = [path("", include(router.urls))]


@override_settings(ROOT_URLCONF=__name__)
class ExpenseApiTests(TestCase):
    def setUp(self):
        # Receipt uploads must never land in the real MEDIA_ROOT inside the repository.
        media_root = TemporaryDirectory()
        self.addCleanup(media_root.cleanup)
        media_override = override_settings(MEDIA_ROOT=media_root.name)
        media_override.enable()
        self.addCleanup(media_override.disable)

        self.User = get_user_model()
        self.user = self.User.objects.create_user("alice@example.com", "s3cure-pass!")
        self.other_user = self.User.objects.create_user("bob@example.com", "s3cure-pass!")
        self.global_category, _ = Category.objects.get_or_create(name="Food")
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

                with self.captureOnCommitCallbacks(execute=False) as callbacks:
                    delete_response = self.client.delete(f"/expenses/{expense.pk}/receipt/")

                self.assertEqual(delete_response.status_code, 204)
                expense.refresh_from_db()
                self.assertFalse(expense.receipt)
                # The file stays until the transaction commits, then is removed.
                self.assertTrue(stored_path.exists())
                for callback in callbacks:
                    callback()
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
        self.assertEqual(missing_response.status_code, 404)

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

    def test_has_receipt_reflects_upload_and_delete(self):
        expense = self.create_expense()
        self.assertFalse(self.client.get(f"/expenses/{expense.pk}/").json()["has_receipt"])

        self.client.post(
            f"/expenses/{expense.pk}/receipt/",
            {"receipt": SimpleUploadedFile("r.pdf", b"%PDF-1.7 r", content_type="application/pdf")},
            format="multipart",
        )
        self.assertTrue(self.client.get(f"/expenses/{expense.pk}/").json()["has_receipt"])

        self.client.delete(f"/expenses/{expense.pk}/receipt/")
        self.assertFalse(self.client.get(f"/expenses/{expense.pk}/").json()["has_receipt"])

    def test_deleting_a_missing_receipt_returns_404(self):
        expense = self.create_expense()

        response = self.client.delete(f"/expenses/{expense.pk}/receipt/")

        self.assertEqual(response.status_code, 404)

    def test_another_users_category_is_indistinguishable_from_unknown(self):
        private = Category.objects.create(name="Private", owner=self.other_user)

        foreign = self.client.post("/expenses/", self.payload(category=private.pk), content_type="application/json")
        unknown = self.client.post("/expenses/", self.payload(category=999999), content_type="application/json")

        self.assertEqual(foreign.status_code, 400)
        self.assertEqual(foreign.json()["error"]["code"], unknown.json()["error"]["code"])
        self.assertNotIn("another user", foreign.json()["error"]["message"])


@override_settings(ROOT_URLCONF=__name__)
class CategorySuggestionTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            "suggestions@example.com", "s3cure-pass!"
        )
        self.other_user = self.User.objects.create_user(
            "other@example.com", "s3cure-pass!"
        )
        self.global_categories = {
            name: Category.objects.get_or_create(name=name, owner=None)[0]
            for name in ("Food", "Travel", "Bills", "Shopping", "Healthcare")
        }
        self.client.force_login(self.user)

    def names(self, description):
        return [category.name for category in suggest_categories(description)]

    def test_known_keyword_returns_global_category(self):
        self.assertEqual(self.names("Lunch at a cafe"), ["Food"])

    def test_matching_is_case_insensitive_and_normalizes_whitespace(self):
        self.assertEqual(self.names("  ELECTRICITY   bill  "), ["Bills"])

    def test_punctuation_does_not_break_matching(self):
        self.assertEqual(self.names("flight-ticket"), ["Travel"])

    def test_unrelated_words_do_not_match_inside_words(self):
        self.assertEqual(self.names("medicality and foodie"), [])

    def test_multiple_matches_are_distinct_and_deterministically_ordered(self):
        self.assertEqual(
            self.names("Lunch, flight, shopping and doctor"),
            ["Food", "Travel", "Shopping", "Healthcare"],
        )

    def test_empty_and_unmatched_descriptions_return_no_suggestions(self):
        for description in (None, "", "   ", "stationery"):
            self.assertEqual(self.names(description), [])

    def test_only_active_global_categories_are_returned(self):
        self.global_categories["Food"].is_active = False
        self.global_categories["Food"].save(update_fields=["is_active"])
        Category.objects.create(name="Lunch", owner=self.user)

        self.assertEqual(self.names("lunch"), [])

    def test_custom_and_other_users_categories_are_never_returned(self):
        Category.objects.create(name="Private", owner=self.user)
        Category.objects.create(name="Travel", owner=self.other_user)

        self.assertEqual(self.names("private travel"), ["Travel"])

    def test_duplicate_global_and_custom_names_do_not_leak_custom_category(self):
        custom = Category.objects.create(name="Food", owner=self.user)

        suggestions = suggest_categories("food")

        self.assertEqual([category.name for category in suggestions], ["Food"])
        self.assertIsNone(suggestions[0].owner_id)
        self.assertNotEqual(suggestions[0].pk, custom.pk)

    def test_api_returns_suggestions_for_authenticated_user(self):
        response = self.client.get("/categories/suggestions/?description=Lunch")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"suggestions": [{"id": self.global_categories["Food"].pk, "name": "Food"}]},
        )

    def test_api_returns_empty_list_for_no_match_or_empty_description(self):
        for query in ("?description=stationery", "?description="):
            response = self.client.get(f"/categories/suggestions/{query}")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"suggestions": []})

    def test_api_rejects_descriptions_longer_than_expense_description(self):
        response = self.client.get(
            "/categories/suggestions/", {"description": "x" * 256}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "description")

    def test_api_requires_authentication(self):
        self.client.logout()

        response = self.client.get("/categories/suggestions/?description=Lunch")

        self.assertEqual(response.status_code, 401)

    def test_api_does_not_create_or_modify_records(self):
        before_categories = list(
            Category.objects.values_list("id", "is_active", "name")
        )
        before_expenses = Expense.objects.count()

        response = self.client.get("/categories/suggestions/?description=Lunch")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(Category.objects.values_list("id", "is_active", "name")),
            before_categories,
        )
        self.assertEqual(Expense.objects.count(), before_expenses)

    def test_suggestions_do_not_assign_or_overwrite_expense_categories(self):
        expense = Expense.objects.create(
            owner=self.user,
            category=None,
            amount=Decimal("10.00"),
            description="Lunch",
            date=date(2026, 10, 26),
        )

        self.client.get("/categories/suggestions/?description=Lunch")
        expense.refresh_from_db()
        self.assertIsNone(expense.category_id)

        expense.category = self.global_categories["Travel"]
        expense.save(update_fields=["category"])
        self.client.get("/categories/suggestions/?description=Lunch")
        expense.refresh_from_db()
        self.assertEqual(expense.category_id, self.global_categories["Travel"].pk)


@override_settings(ROOT_URLCONF=__name__)
class CategoryApiTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user("alice@example.com", "s3cure-pass!")
        self.other_user = self.User.objects.create_user("bob@example.com", "s3cure-pass!")
        self.global_category, _ = Category.objects.get_or_create(name="Food")
        self.client.force_login(self.user)

    def post_category(self, **payload):
        return self.client.post(
            "/categories/",
            payload,
            content_type="application/json",
        )

    def test_list_returns_global_and_own_active_categories_only(self):
        own = Category.objects.create(name="Personal", owner=self.user)
        Category.objects.create(name="Private", owner=self.other_user)
        Category.objects.create(name="Inactive", owner=self.user, is_active=False)

        response = self.client.get("/categories/")

        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()}
        self.assertIn(self.global_category.pk, ids)
        self.assertIn(own.pk, ids)
        self.assertNotIn(Category.objects.get(name="Private").pk, ids)
        self.assertNotIn(Category.objects.get(name="Inactive").pk, ids)

    def test_create_assigns_owner_and_audits(self):
        response = self.post_category(name="Subscriptions")

        self.assertEqual(response.status_code, 201)
        category = Category.objects.get(name="Subscriptions")
        self.assertEqual(category.owner, self.user)
        audit = AuditLog.objects.get(entity_type="expenses.category")
        self.assertEqual(audit.action, AuditLog.Action.CREATE)

    def test_rejects_empty_and_duplicate_names(self):
        Category.objects.create(name="Travel", owner=self.user)
        for name in ("", "   ", "travel"):
            response = self.post_category(name=name)
            self.assertEqual(response.status_code, 400)
            self.assertIn("name", response.json()["error"]["field"])

    def test_allows_same_name_as_global_category(self):
        response = self.post_category(name="Food")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Category.objects.filter(name__iexact="food").count(), 2)

    def test_creates_subcategory_under_visible_parent(self):
        response = self.post_category(name="Coffee", parent=self.global_category.pk)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Category.objects.get(name="Coffee").parent_id,
            self.global_category.pk,
        )

    def test_rejects_inaccessible_parent(self):
        private = Category.objects.create(name="Private", owner=self.other_user)

        response = self.post_category(name="Child", parent=private.pk)

        self.assertEqual(response.status_code, 400)
        self.assertIn("parent", response.json()["error"]["field"])

    def test_rejects_circular_parent_update(self):
        first = Category.objects.create(name="First", owner=self.user)
        second = Category.objects.create(name="Second", owner=self.user, parent=first)
        response = self.client.patch(
            f"/categories/{first.pk}/",
            {"parent": second.pk},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("parent", response.json()["error"]["field"])

    def test_global_categories_cannot_be_updated_or_deleted(self):
        update = self.client.patch(
            f"/categories/{self.global_category.pk}/",
            {"name": "Changed"},
            content_type="application/json",
        )
        delete = self.client.delete(f"/categories/{self.global_category.pk}/")

        self.assertEqual(update.status_code, 403)
        self.assertEqual(delete.status_code, 403)
        self.global_category.refresh_from_db()
        self.assertEqual(self.global_category.name, "Food")
        self.assertTrue(self.global_category.is_active)

    def test_other_users_category_is_not_exposed(self):
        private = Category.objects.create(name="Private", owner=self.other_user)

        self.assertEqual(self.client.get(f"/categories/{private.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/categories/{private.pk}/").status_code, 404)

    def test_delete_deactivates_referenced_custom_category_and_audits(self):
        category = Category.objects.create(name="Bills", owner=self.user)
        Expense.objects.create(
            owner=self.user,
            category=category,
            amount=Decimal("10.00"),
            date=date(2026, 10, 26),
        )

        response = self.client.delete(f"/categories/{category.pk}/")

        self.assertEqual(response.status_code, 204)
        category.refresh_from_db()
        self.assertFalse(category.is_active)
        self.assertEqual(
            AuditLog.objects.filter(
                entity_type="expenses.category",
                action=AuditLog.Action.UPDATE,
            ).count(),
            1,
        )

    def test_expenses_accept_global_and_custom_categories(self):
        custom = Category.objects.create(name="Custom", owner=self.user)

        for category in (self.global_category, custom):
            response = self.client.post(
                "/expenses/",
                {
                    "category": category.pk,
                    "amount": "10.00",
                    "date": "2026-10-26",
                },
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 201)

    def test_recreating_a_deleted_category_restores_it(self):
        category = Category.objects.create(name="Gym", owner=self.user)
        expense = Expense.objects.create(
            owner=self.user,
            category=category,
            amount=Decimal("10.00"),
            date=date(2026, 10, 26),
        )
        self.client.delete(f"/categories/{category.pk}/")

        response = self.post_category(name="gym")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], category.pk)
        category.refresh_from_db()
        self.assertTrue(category.is_active)
        self.assertEqual(category.name, "gym")
        expense.refresh_from_db()
        self.assertEqual(expense.category_id, category.pk)
        self.assertEqual(Category.objects.filter(owner=self.user, name__iexact="gym").count(), 1)

    def test_restoring_cannot_create_a_cycle(self):
        parent = Category.objects.create(name="Transport", owner=self.user)
        child = Category.objects.create(name="Metro", owner=self.user, parent=parent)
        self.client.delete(f"/categories/{parent.pk}/")

        response = self.post_category(name="Transport", parent=child.pk)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "parent")
        parent.refresh_from_db()
        self.assertFalse(parent.is_active)

    def test_renaming_onto_a_deleted_categorys_name_is_rejected(self):
        deleted = Category.objects.create(name="Gym", owner=self.user, is_active=False)
        other = Category.objects.create(name="Fitness", owner=self.user)

        response = self.client.patch(
            f"/categories/{other.pk}/",
            {"name": "GYM"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "name")
        deleted.refresh_from_db()
        self.assertFalse(deleted.is_active)
