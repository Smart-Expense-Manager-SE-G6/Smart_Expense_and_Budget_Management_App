
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from budgets.models import Budget
from expenses.models import Expense


class BudgetAPITests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="budgettester@example.com",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            email="otheruser@example.com",
            password="TestPassword123!",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.payload = {
            "name": "Monthly Budget",
            "limit_amount": "5000.00",
            "period": "monthly",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "category": None,
        }

    def test_create_budget(self):
        response = self.client.post(
            "/api/v1/budgets/",
            self.payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Budget.objects.count(), 1)

        budget = Budget.objects.get()
        self.assertEqual(budget.user, self.user)
        self.assertEqual(budget.name, "Monthly Budget")

    def test_list_shows_only_current_users_budgets(self):
        Budget.objects.create(
            user=self.user,
            name="My Budget",
            limit_amount=Decimal("1000.00"),
            period="monthly",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        )

        Budget.objects.create(
            user=self.other_user,
            name="Other Budget",
            limit_amount=Decimal("2000.00"),
            period="monthly",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        )

        response = self.client.get("/api/v1/budgets/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "My Budget")

    def test_rejects_invalid_date_range(self):
        payload = {
            **self.payload,
            "start_date": "2026-10-31",
            "end_date": "2026-10-01",
        }

        response = self.client.post(
            "/api/v1/budgets/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Budget.objects.count(), 0)

    def test_user_cannot_view_another_users_budget(self):
        other_budget = Budget.objects.create(
            user=self.other_user,
            name="Private Budget",
            limit_amount=Decimal("2000.00"),
            period="monthly",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        )

        response = self.client.get(
            f"/api/v1/budgets/{other_budget.pk}/"
        )

        self.assertEqual(response.status_code, 404)


class BudgetRolloverTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="rollovertester@example.com",
            password="TestPassword123!",
        )

    def create_expired_budget(self, rollover_mode="rollover"):
        return Budget.objects.create(
            user=self.user,
            name="Monthly Budget",
            limit_amount=Decimal("5000.00"),
            base_limit_amount=Decimal("5000.00"),
            period="monthly",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            rollover_mode=rollover_mode,
        )

    def test_rollover_creates_next_period(self):
        self.create_expired_budget()

        call_command("rollover_budgets")

        next_budget = Budget.objects.filter(
            user=self.user,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        ).first()

        self.assertIsNotNone(next_budget)
        self.assertEqual(
            next_budget.limit_amount,
            Decimal("10000.00"),
        )
        self.assertEqual(
            next_budget.base_limit_amount,
            Decimal("5000.00"),
        )
        self.assertEqual(
            next_budget.rollover_mode,
            "rollover",
        )

    def test_rollover_carries_forward_unused_amount(self):
        self.create_expired_budget(rollover_mode="rollover")

        Expense.objects.create(
            owner=self.user,
            amount=Decimal("1000.00"),
            date=date(2026, 9, 15),
        )

        call_command("rollover_budgets")

        next_budget = Budget.objects.get(
            user=self.user,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        )

        # 5000 limit - 1000 spent = 4000 unused.
        # Next limit = 5000 base + 4000 carried forward.
        self.assertEqual(
            next_budget.limit_amount,
            Decimal("9000.00"),
        )
        self.assertEqual(
            next_budget.base_limit_amount,
            Decimal("5000.00"),
        )

    def test_reset_mode_does_not_carry_forward_unused_amount(self):
        self.create_expired_budget(rollover_mode="reset")

        Expense.objects.create(
            owner=self.user,
            amount=Decimal("1000.00"),
            date=date(2026, 9, 15),
        )

        call_command("rollover_budgets")

        next_budget = Budget.objects.get(
            user=self.user,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        )

        self.assertEqual(
            next_budget.limit_amount,
            Decimal("5000.00"),
        )
        self.assertEqual(next_budget.rollover_mode, "reset")

    def test_running_command_twice_does_not_duplicate_period(self):
        self.create_expired_budget()

        call_command("rollover_budgets")
        call_command("rollover_budgets")

        next_periods = Budget.objects.filter(
            user=self.user,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        )

        self.assertEqual(next_periods.count(), 1)
