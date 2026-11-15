"""TC-Account-01: account settings (FR2, NFR14, S3-09): password change, data export, account deletion, email consent."""

import csv
import io
import json
import zipfile
from calendar import monthrange
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from alerts.models import Alert
from audit.models import AuditLog
from budgets.models import Budget, BudgetMember
from expenses.models import Category, Expense, RecurringRule

PW = "Tr1cky-Passw0rd!"
NEW_PW = "An0ther-Str0ng-Pass!"


def signed_in(email, password=PW):
    """A client with a real session, as a browser would have."""
    client = APIClient()
    assert client.login(email=email, password=password)
    return client


class AccountSettingsBase(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        media = override_settings(MEDIA_ROOT=self.media.name)
        media.enable()
        self.addCleanup(media.disable)
        self.user = User.objects.create_user(email="asha@example.com", password=PW, first_name="Asha")
        self.other = User.objects.create_user(email="ben@example.com", password=PW, first_name="Ben")
        self.api = signed_in("asha@example.com")
        self.food = Category.objects.get(name="Food", owner__isnull=True)

    def add_expense(self, client=None, amount="100.00", description="Lunch"):
        response = (client or self.api).post("/api/v1/expenses/", {
            "amount": amount, "date": date.today().isoformat(), "category": self.food.id,
            "description": description}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["id"]

    def add_receipt(self, expense_id, client=None):
        upload = SimpleUploadedFile("bill.pdf", b"%PDF-1.7 test receipt", content_type="application/pdf")
        response = (client or self.api).post(f"/api/v1/expenses/{expense_id}/receipt/", {"receipt": upload}, format="multipart")
        self.assertIn(response.status_code, (200, 201), response.content)
        return Expense.objects.get(pk=expense_id).receipt.name

    def add_budget(self, client=None, limit="1000.00"):
        today = date.today()
        response = (client or self.api).post("/api/v1/budgets/", {
            "name": "Food", "category": self.food.id, "limit_amount": limit, "period": "monthly",
            "start_date": today.replace(day=1).isoformat(),
            "end_date": today.replace(day=monthrange(today.year, today.month)[1]).isoformat()}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["id"]


class PasswordChangeTests(AccountSettingsBase):
    URL = "/api/v1/me/password/"

    def change(self, current=PW, new=NEW_PW, client=None):
        return (client or self.api).post(self.URL, {"current_password": current, "new_password": new}, format="json")

    def assert_field_error(self, response, field):
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(response.json()["error"]["field"], field)

    def test_wrong_current_password(self):
        self.assert_field_error(self.change(current="not-my-password"), "current_password")
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password(PW))

    def test_weak_new_password(self):
        self.assert_field_error(self.change(new="123"), "new_password")

    def test_same_password(self):
        self.assert_field_error(self.change(new=PW), "new_password")

    def test_change_keeps_this_session_and_signs_out_others(self):
        laptop = signed_in("asha@example.com")
        self.assertEqual(laptop.get("/api/v1/me/").status_code, 200)

        self.assertEqual(self.change().status_code, 204)

        self.assertEqual(self.api.get("/api/v1/me/").status_code, 200)
        self.assertEqual(laptop.get("/api/v1/me/").status_code, 401)
        user = User.objects.get(pk=self.user.pk)
        self.assertTrue(user.check_password(NEW_PW))
        self.assertFalse(user.check_password(PW))

    def test_change_is_audited_without_the_password(self):
        self.change()
        entry = AuditLog.objects.filter(entity_type="accounts.user", entity_id=str(self.user.pk)).latest("id")
        self.assertEqual(entry.action, AuditLog.Action.UPDATE)
        self.assertNotIn("password", json.dumps([entry.before, entry.after]))

    def test_requires_login(self):
        self.assertEqual(APIClient().post(self.URL, {}, format="json").status_code, 401)


class DataExportTests(AccountSettingsBase):
    URL = "/api/v1/me/export/"

    def export(self):
        response = self.api.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment;", response["Content-Disposition"])
        return zipfile.ZipFile(io.BytesIO(response.content))

    def test_export_contains_every_kind_of_data(self):
        kept = self.add_expense(amount="250.00", description="Groceries")
        gone = self.add_expense(amount="40.00", description="Snack")
        self.api.delete(f"/api/v1/expenses/{gone}/")
        self.add_receipt(kept)
        Category.objects.create(name="Pets", owner=self.user)
        RecurringRule.objects.create(owner=self.user, amount="999.00", frequency="monthly", start_date=date(2030, 1, 1))
        budget_id = self.add_budget(limit="200.00")  # 250 > 200, so alerts exist
        self.api.post(f"/api/v1/budgets/{budget_id}/members/", {"email": "ben@example.com"}, format="json")

        archive = self.export()
        names = set(archive.namelist())
        for expected in ("README.txt", "profile.json", "expenses.csv", "categories.json", "recurring_rules.json",
                         "budgets.json", "alerts.json", "history.json"):
            self.assertIn(expected, names)

        rows = list(csv.DictReader(io.StringIO(archive.read("expenses.csv").decode())))
        self.assertEqual({r["description"]: r["is_deleted"] for r in rows}, {"Groceries": "False", "Snack": "True"})
        self.assertEqual(next(r for r in rows if r["description"] == "Groceries")["amount"], "250.00")
        self.assertEqual(archive.read(f"receipts/{kept}_" + Expense.objects.get(pk=kept).receipt.name.rsplit("/", 1)[-1]),
                         b"%PDF-1.7 test receipt")
        self.assertEqual(json.loads(archive.read("profile.json"))["email"], "asha@example.com")
        self.assertEqual([c["name"] for c in json.loads(archive.read("categories.json"))], ["Pets"])
        self.assertEqual(json.loads(archive.read("recurring_rules.json"))[0]["amount"], "999.00")
        budgets = json.loads(archive.read("budgets.json"))
        self.assertEqual(budgets["owned"][0]["members"][0]["user__email"], "ben@example.com")
        self.assertTrue(json.loads(archive.read("alerts.json")))
        self.assertTrue(json.loads(archive.read("history.json")))

    def test_export_never_includes_other_users_data(self):
        ben = signed_in("ben@example.com")
        self.add_expense(client=ben, description="Ben's secret")
        archive = self.export()
        everything = b"".join(archive.read(name) for name in archive.namelist())
        self.assertNotIn(b"Ben's secret", everything)
        self.assertNotIn(b"ben@example.com", everything)

    def test_shared_budgets_are_listed_with_my_role(self):
        ben = signed_in("ben@example.com")
        budget_id = self.add_budget(client=ben)
        ben.post(f"/api/v1/budgets/{budget_id}/members/", {"email": "asha@example.com", "role": "admin"}, format="json")
        shared = json.loads(self.export().read("budgets.json"))["shared_with_me"]
        self.assertEqual([(b["owner_email"], b["role"]) for b in shared], [("ben@example.com", "admin")])

    def test_requires_login(self):
        self.assertEqual(APIClient().get(self.URL).status_code, 401)


class AccountDeletionTests(AccountSettingsBase):
    URL = "/api/v1/me/"

    def delete(self, password=PW, client=None):
        return (client or self.api).delete(self.URL, {"password": password}, format="json")

    def test_wrong_password_deletes_nothing(self):
        response = self.delete(password="nope")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "password")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_deletes_everything_the_user_owns(self):
        expense_id = self.add_expense(amount="900.00")
        receipt = self.add_receipt(expense_id)
        Category.objects.create(name="Pets", owner=self.user)
        RecurringRule.objects.create(owner=self.user, amount="5.00", frequency="daily", start_date=date(2030, 1, 1))
        self.add_budget()
        self.assertTrue(Path(self.media.name, receipt).exists())

        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.delete().status_code, 204)

        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        for model, field in ((Expense, "owner_id"), (Category, "owner_id"), (RecurringRule, "owner_id"),
                             (Budget, "user_id"), (Alert, "user_id")):
            self.assertFalse(model.objects.filter(**{field: self.user.pk}).exists(), model.__name__)
        self.assertFalse(Path(self.media.name, receipt).exists())

    def test_signed_out_and_email_can_register_again(self):
        self.delete()
        self.assertEqual(self.api.get("/api/v1/me/").status_code, 401)
        response = APIClient().post("/api/v1/auth/register/", {"email": "asha@example.com", "password": PW}, format="json")
        self.assertEqual(response.status_code, 201, response.content)

    def test_history_removed_and_one_anonymous_entry_kept(self):
        self.add_expense()
        self.api.patch("/api/v1/me/", {"first_name": "A"}, format="json")
        self.delete()
        remaining = AuditLog.objects.filter(entity_type__in=["expenses.expense", "accounts.user"])
        self.assertEqual(remaining.count(), 1)
        entry = remaining.get()
        self.assertEqual((entry.action, entry.actor, entry.before, entry.after), ("delete", None, None, None))

    def test_member_leaving_by_deletion_keeps_the_owners_budget(self):
        ben = signed_in("ben@example.com")
        budget_id = self.add_budget(client=ben)
        ben.post(f"/api/v1/budgets/{budget_id}/members/", {"email": "asha@example.com"}, format="json")
        self.delete()
        self.assertTrue(Budget.objects.filter(pk=budget_id).exists())
        self.assertFalse(BudgetMember.objects.filter(budget_id=budget_id).exists())

    def test_owner_deletion_removes_shared_budget_for_members(self):
        budget_id = self.add_budget()
        self.api.post(f"/api/v1/budgets/{budget_id}/members/", {"email": "ben@example.com"}, format="json")
        self.delete()
        ben_budgets = signed_in("ben@example.com").get("/api/v1/budgets/").json()
        self.assertEqual(ben_budgets, [])
        self.assertTrue(User.objects.filter(email="ben@example.com").exists())

    def test_requires_login(self):
        self.assertEqual(APIClient().delete(self.URL, {"password": PW}, format="json").status_code, 401)


class EmailAlertConsentTests(AccountSettingsBase):
    def test_setting_is_on_by_default_and_editable(self):
        self.assertTrue(self.api.get("/api/v1/me/").json()["email_alerts"])
        response = self.api.patch("/api/v1/me/", {"email_alerts": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.get(pk=self.user.pk).email_alerts)

    @patch("alerts.adapters.get_email_adapter")
    def test_alert_email_sent_when_allowed(self, adapter):
        self.add_budget(limit="100.00")
        with self.captureOnCommitCallbacks(execute=True):
            self.add_expense(amount="90.00")
        self.assertTrue(Alert.objects.filter(user=self.user).exists())
        self.assertTrue(adapter.return_value.send_email.called)

    @patch("alerts.adapters.get_email_adapter")
    def test_no_email_when_turned_off_but_alert_still_shown(self, adapter):
        self.api.patch("/api/v1/me/", {"email_alerts": False}, format="json")
        self.add_budget(limit="100.00")
        with self.captureOnCommitCallbacks(execute=True):
            self.add_expense(amount="90.00")
        self.assertTrue(Alert.objects.filter(user=self.user).exists())
        self.assertFalse(adapter.return_value.send_email.called)
