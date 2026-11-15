"""TC-Audit-01: reading the audit trail (FR21, SASD 4.3 GET /audit, use case "View Audit Trail")."""

from calendar import monthrange
from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from audit.models import AuditLog
from expenses.models import Category

URL = "/api/v1/audit/"
PW = "Tr1cky-Passw0rd!"


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class AuditTrailApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password=PW, first_name="Owen")
        self.admin = User.objects.create_user(email="admin@example.com", password=PW)
        self.member = User.objects.create_user(email="member@example.com", password=PW)
        self.stranger = User.objects.create_user(email="stranger@example.com", password=PW)
        self.api = client_for(self.owner)
        self.food = Category.objects.get(name="Food", owner__isnull=True)

    def results(self, client=None, **params):
        response = (client or self.api).get(URL, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["results"]

    def add_expense(self, amount="100.00", client=None):
        response = (client or self.api).post("/api/v1/expenses/", {
            "amount": amount, "date": date.today().isoformat(), "category": self.food.id, "description": "Lunch"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["id"]

    def add_budget(self):
        today = date.today()
        response = self.api.post("/api/v1/budgets/", {
            "name": "Food", "category": self.food.id, "limit_amount": "1000.00", "period": "monthly",
            "start_date": today.replace(day=1).isoformat(),
            "end_date": today.replace(day=monthrange(today.year, today.month)[1]).isoformat(),
        }, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["id"]

    # --- what an entry looks like ---

    def test_editing_an_expense_shows_old_and_new_amount(self):
        expense_id = self.add_expense("100.00")
        self.api.patch(f"/api/v1/expenses/{expense_id}/", {"amount": "250.00"}, format="json")
        history = self.results(entity="expense", entity_id=expense_id)
        self.assertEqual([e["action"] for e in history], ["update", "create"])
        update = history[0]
        self.assertEqual(update["entity"], "expense")
        self.assertEqual(update["entity_id"], str(expense_id))
        self.assertEqual(update["actor_email"], "owner@example.com")
        self.assertEqual(update["changes"], [{"field": "amount", "old": "100.00", "new": "250.00"}])
        self.assertTrue(update["request_id"])

    def test_create_lists_values_and_hides_bookkeeping_fields(self):
        expense_id = self.add_expense("75.50")
        created = self.results(entity="expense", entity_id=expense_id)[0]
        fields = {c["field"] for c in created["changes"]}
        self.assertIn("amount", fields)
        self.assertFalse(fields & {"id", "created_at", "updated_at"})

    def test_soft_delete_is_in_the_history(self):
        expense_id = self.add_expense()
        self.api.delete(f"/api/v1/expenses/{expense_id}/")
        latest = self.results(entity="expense", entity_id=expense_id)[0]
        self.assertIn({"field": "is_deleted", "old": False, "new": True}, latest["changes"])

    def test_profile_changes_are_visible(self):
        self.api.patch("/api/v1/me/", {"first_name": "Owen J"}, format="json")
        entry = self.results(entity="profile")[0]
        self.assertIn({"field": "first_name", "old": "Owen", "new": "Owen J"}, entry["changes"])
        self.assertNotIn("password", {c["field"] for c in entry["changes"]})

    def test_newest_first_and_paginated(self):
        for amount in ("1.00", "2.00", "3.00"):
            self.add_expense(amount)
        response = self.api.get(URL, {"entity": "expense", "page_size": 2}).json()
        self.assertEqual(response["count"], 3)
        self.assertEqual(len(response["results"]), 2)
        self.assertIsNotNone(response["next"])
        amounts = [next(c["new"] for c in e["changes"] if c["field"] == "amount") for e in response["results"]]
        self.assertEqual(amounts, ["3.00", "2.00"])

    # --- who can see what ---

    def test_other_users_history_is_never_visible(self):
        expense_id = self.add_expense()
        self.assertEqual(self.results(client_for(self.stranger)), [])
        self.assertEqual(self.results(client_for(self.stranger), entity="expense", entity_id=expense_id), [])
        entry_id = AuditLog.objects.filter(entity_type="expenses.expense").first().pk
        self.assertEqual(client_for(self.stranger).get(f"{URL}{entry_id}/").status_code, 404)
        self.assertEqual(self.api.get(f"{URL}{entry_id}/").status_code, 200)

    def test_shared_budget_admin_sees_budget_and_membership_history(self):
        budget_id = self.add_budget()
        self.api.post(f"/api/v1/budgets/{budget_id}/members/", {"email": "admin@example.com", "role": "admin"}, format="json")
        self.api.post(f"/api/v1/budgets/{budget_id}/members/", {"email": "member@example.com", "role": "member"}, format="json")
        self.api.patch(f"/api/v1/budgets/{budget_id}/", {"limit_amount": "1500.00"}, format="json")

        admin_view = self.results(client_for(self.admin))
        kinds = {(e["entity"], e["action"]) for e in admin_view}
        self.assertIn(("budget", "update"), kinds)
        self.assertIn(("budget_member", "create"), kinds)

        member_view = self.results(client_for(self.member))
        self.assertFalse([e for e in member_view if e["entity"] in ("budget", "budget_member")])

    def test_removed_membership_stays_in_owner_history(self):
        budget_id = self.add_budget()
        member_id = self.api.post(f"/api/v1/budgets/{budget_id}/members/", {"email": "member@example.com"}, format="json").json()["id"]
        self.api.delete(f"/api/v1/budgets/{budget_id}/members/{member_id}/")
        actions = [e["action"] for e in self.results(entity="budget_member", entity_id=member_id)]
        self.assertEqual(actions, ["delete", "create"])

    def test_deleted_budget_history_stays_with_owner(self):
        budget_id = self.add_budget()
        self.assertEqual(self.api.delete(f"/api/v1/budgets/{budget_id}/").status_code, 204)
        actions = [e["action"] for e in self.results(entity="budget", entity_id=budget_id)]
        self.assertEqual(actions[0], "delete")

    def test_system_changes_have_no_actor(self):
        expense_id = self.add_expense()
        from audit.services import log_change
        from django.db import transaction
        from expenses.models import Expense
        with transaction.atomic():
            log_change(None, AuditLog.Action.UPDATE, Expense.objects.get(pk=expense_id), before={"owner_id": self.owner.pk})
        self.assertIsNone(self.results(entity="expense", entity_id=expense_id)[0]["actor_email"])

    # --- read-only and input checks ---

    def test_audit_trail_cannot_be_changed_through_the_api(self):
        self.add_expense()
        entry_id = AuditLog.objects.first().pk
        self.assertEqual(self.api.post(URL, {}, format="json").status_code, 405)
        self.assertEqual(self.api.patch(f"{URL}{entry_id}/", {"action": "delete"}, format="json").status_code, 405)
        self.assertEqual(self.api.put(f"{URL}{entry_id}/", {}, format="json").status_code, 405)
        self.assertEqual(self.api.delete(f"{URL}{entry_id}/").status_code, 405)
        self.assertTrue(AuditLog.objects.filter(pk=entry_id).exists())

    def test_bad_filters_are_rejected(self):
        response = self.api.get(URL, {"entity": "password"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "entity")
        self.assertEqual(self.api.get(URL, {"entity_id": "1;drop"}).status_code, 400)

    def test_requires_login(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)
