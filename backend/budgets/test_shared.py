from datetime import date
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from alerts.models import Alert
from audit.models import AuditLog
from budgets.models import Budget, BudgetMember
from expenses.models import Category, Expense

User = get_user_model()
PASSWORD = "TestPassword123!"


class SharedBudgetTestCase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password=PASSWORD)
        self.alice = User.objects.create_user(email="alice@example.com", password=PASSWORD)
        self.carol = User.objects.create_user(email="carol@example.com", password=PASSWORD)
        self.outsider = User.objects.create_user(email="outsider@example.com", password=PASSWORD)

        self.budget = Budget.objects.create(
            user=self.owner,
            name="Household",
            limit_amount=Decimal("1000.00"),
            period="monthly",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        )
        self.url = f"/api/v1/budgets/{self.budget.pk}/"

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def share(self, user, role=BudgetMember.Role.MEMBER):
        return BudgetMember.objects.create(budget=self.budget, user=user, role=role)

    def add_member(self, actor, email, role="member"):
        return self.client_for(actor).post(
            f"{self.url}members/", {"email": email, "role": role}, format="json"
        )

    def expense(self, user, amount, **fields):
        return Expense.objects.create(
            owner=user,
            amount=Decimal(amount),
            date=fields.pop("date", date(2026, 10, 15)),
            **fields,
        )

    def assert_error(self, response, status_code, code, field=None):
        self.assertEqual(response.status_code, status_code)
        error = response.json()["error"]
        self.assertEqual(error["code"], code)
        if field is not None:
            self.assertEqual(error["field"], field)


class TCShared01MembershipTests(SharedBudgetTestCase):
    """TC-Shared-01: an owner shares a budget and roles control access."""

    def test_owner_adds_member_by_email_with_audit(self):
        response = self.add_member(self.owner, "Alice@Example.com")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "alice@example.com")
        self.assertEqual(response.data["role"], "member")
        membership = BudgetMember.objects.get(budget=self.budget, user=self.alice)
        log = AuditLog.objects.get(entity_type="budgets.budgetmember")
        self.assertEqual(log.action, AuditLog.Action.CREATE)
        self.assertEqual(log.actor, self.owner)
        self.assertEqual(log.entity_id, str(membership.pk))

    def test_member_sees_shared_budget_with_role(self):
        self.share(self.alice)

        response = self.client_for(self.alice).get("/api/v1/budgets/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.budget.pk)
        self.assertEqual(response.data[0]["role"], "member")
        self.assertEqual(response.data[0]["owner_email"], "owner@example.com")

    def test_owner_sees_owner_role(self):
        response = self.client_for(self.owner).get(self.url)

        self.assertEqual(response.data["role"], "owner")

    def test_outsider_gets_404_not_403(self):
        client = self.client_for(self.outsider)

        self.assertEqual(client.get(self.url).status_code, 404)
        self.assertEqual(client.get(f"{self.url}members/").status_code, 404)
        self.assertEqual(client.get(f"{self.url}expenses/").status_code, 404)

    def test_member_cannot_change_settings(self):
        self.share(self.alice)

        response = self.client_for(self.alice).patch(
            self.url, {"limit_amount": "5000.00"}, format="json"
        )

        self.assert_error(response, 403, "permission_denied")
        self.budget.refresh_from_db()
        self.assertEqual(self.budget.limit_amount, Decimal("1000.00"))

    def test_member_cannot_add_members(self):
        self.share(self.alice)

        response = self.add_member(self.alice, "carol@example.com")

        self.assert_error(response, 403, "permission_denied")
        self.assertFalse(BudgetMember.objects.filter(user=self.carol).exists())

    def test_member_cannot_change_roles(self):
        self.share(self.alice)
        carol = self.share(self.carol)

        response = self.client_for(self.alice).patch(
            f"{self.url}members/{carol.pk}/", {"role": "admin"}, format="json"
        )

        self.assert_error(response, 403, "permission_denied")
        carol.refresh_from_db()
        self.assertEqual(carol.role, "member")

    def test_admin_can_change_settings_and_manage_members(self):
        alice = self.share(self.alice)
        promote = self.client_for(self.owner).patch(
            f"{self.url}members/{alice.pk}/", {"role": "admin"}, format="json"
        )
        self.assertEqual(promote.status_code, 200)
        self.assertEqual(promote.data["role"], "admin")

        update = self.client_for(self.alice).patch(
            self.url, {"limit_amount": "1500.00"}, format="json"
        )
        added = self.add_member(self.alice, "carol@example.com")

        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.data["limit_amount"], "1500.00")
        self.assertEqual(added.status_code, 201)
        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="budgets.budget",
                action=AuditLog.Action.UPDATE,
                actor=self.alice,
            ).exists()
        )

    def test_only_owner_can_delete_budget(self):
        self.share(self.alice, role=BudgetMember.Role.ADMIN)

        denied = self.client_for(self.alice).delete(self.url)
        allowed = self.client_for(self.owner).delete(self.url)

        self.assert_error(denied, 403, "permission_denied")
        self.assertEqual(allowed.status_code, 204)
        self.assertFalse(Budget.objects.filter(pk=self.budget.pk).exists())
        self.assertFalse(BudgetMember.objects.exists())

    def test_member_can_leave(self):
        alice = self.share(self.alice)

        response = self.client_for(self.alice).delete(f"{self.url}members/{alice.pk}/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client_for(self.alice).get(self.url).status_code, 404)
        log = AuditLog.objects.get(entity_type="budgets.budgetmember")
        self.assertEqual(log.action, AuditLog.Action.DELETE)
        self.assertEqual(log.entity_id, str(alice.pk))

    def test_member_cannot_remove_others(self):
        self.share(self.alice)
        carol = self.share(self.carol)

        response = self.client_for(self.alice).delete(f"{self.url}members/{carol.pk}/")

        self.assert_error(response, 403, "permission_denied")
        self.assertTrue(BudgetMember.objects.filter(pk=carol.pk).exists())

    def test_admin_removes_member(self):
        alice = self.share(self.alice)

        response = self.client_for(self.owner).delete(f"{self.url}members/{alice.pk}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(BudgetMember.objects.exists())

    def test_unknown_member_id_is_404(self):
        response = self.client_for(self.owner).delete(f"{self.url}members/999999/")

        self.assert_error(response, 404, "not_found")

    def test_members_list(self):
        self.share(self.alice)
        self.share(self.carol, role=BudgetMember.Role.ADMIN)

        response = self.client_for(self.alice).get(f"{self.url}members/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(m["email"], m["role"]) for m in response.data],
            [("alice@example.com", "member"), ("carol@example.com", "admin")],
        )


class SharedBudgetValidationTests(SharedBudgetTestCase):
    def test_rejects_unknown_email(self):
        response = self.add_member(self.owner, "nobody@example.com")

        self.assert_error(response, 400, "invalid", field="email")

    def test_rejects_owner(self):
        response = self.add_member(self.owner, "owner@example.com")

        self.assert_error(response, 400, "invalid", field="email")

    def test_rejects_duplicate_member(self):
        self.share(self.alice)

        response = self.add_member(self.owner, "alice@example.com")

        self.assert_error(response, 400, "invalid", field="email")
        self.assertEqual(BudgetMember.objects.count(), 1)

    def test_rejects_unknown_role(self):
        response = self.add_member(self.owner, "alice@example.com", role="superuser")

        self.assert_error(response, 400, "invalid_choice", field="role")

    def test_cannot_share_budget_with_custom_category(self):
        self.budget.category = Category.objects.create(name="Kids", owner=self.owner)
        self.budget.save()

        response = self.add_member(self.owner, "alice@example.com")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(BudgetMember.objects.exists())

    def test_shared_budget_cannot_switch_to_custom_category(self):
        self.share(self.alice)
        custom = Category.objects.create(name="Kids", owner=self.owner)

        response = self.client_for(self.owner).patch(
            self.url, {"category": custom.pk}, format="json"
        )

        self.assert_error(response, 400, "invalid", field="category")

    def test_shared_budget_can_use_default_category(self):
        self.share(self.alice)
        default = Category.objects.filter(owner__isnull=True).first()

        response = self.client_for(self.owner).patch(
            self.url, {"category": default.pk}, format="json"
        )

        self.assertEqual(response.status_code, 200)

    def test_budget_rejects_another_users_category(self):
        private = Category.objects.create(name="Secret", owner=self.outsider)

        response = self.client_for(self.owner).post(
            "/api/v1/budgets/",
            {
                "name": "Mine",
                "limit_amount": "100.00",
                "period": "monthly",
                "start_date": "2026-11-01",
                "end_date": "2026-11-30",
                "category": private.pk,
            },
            format="json",
        )

        self.assert_error(response, 400, "invalid", field="category")
        self.assertFalse(Budget.objects.filter(name="Mine").exists())


class SharedBudgetSpendingTests(SharedBudgetTestCase):
    def test_utilization_counts_every_member(self):
        self.share(self.alice)
        self.expense(self.owner, "200.00")
        self.expense(self.alice, "300.00")
        self.expense(self.outsider, "999.00")
        self.expense(self.alice, "50.00", is_deleted=True)

        response = self.client_for(self.alice).get(f"{self.url}utilization/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["amount_spent"], "500.00")
        self.assertEqual(response.data["remaining_amount"], "500.00")
        self.assertEqual(response.data["percentage_used"], "50.00")

    def test_member_views_budget_expenses(self):
        self.share(self.alice)
        self.expense(self.owner, "200.00", description="Groceries")
        self.expense(self.alice, "300.00", description="Electricity")
        self.expense(self.outsider, "999.00")
        self.expense(self.alice, "10.00", date=date(2026, 11, 2))

        response = self.client_for(self.alice).get(f"{self.url}expenses/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            {(e["owner_email"], e["amount"]) for e in response.data["results"]},
            {("owner@example.com", "200.00"), ("alice@example.com", "300.00")},
        )

    def test_member_expense_triggers_threshold_alert(self):
        self.share(self.alice)

        self.expense(self.alice, "800.00")

        alert = Alert.objects.get(budget=self.budget, threshold_percentage=80)
        self.assertEqual(alert.user, self.owner)

    def test_rollover_keeps_members(self):
        self.budget.start_date = date(2026, 9, 1)
        self.budget.end_date = date(2026, 9, 30)
        self.budget.base_limit_amount = Decimal("1000.00")
        self.budget.rollover_mode = "rollover"
        self.budget.save()
        self.share(self.alice, role=BudgetMember.Role.ADMIN)
        self.expense(self.owner, "100.00", date=date(2026, 9, 10))
        self.expense(self.alice, "400.00", date=date(2026, 9, 11))

        call_command("rollover_budgets", stdout=StringIO())

        next_budget = Budget.objects.get(user=self.owner, start_date=date(2026, 10, 1))
        # 1000 base + (1000 - 500 spent by both) carried forward.
        self.assertEqual(next_budget.limit_amount, Decimal("1500.00"))
        self.assertEqual(
            list(next_budget.memberships.values_list("user__email", "role")),
            [("alice@example.com", "admin")],
        )
