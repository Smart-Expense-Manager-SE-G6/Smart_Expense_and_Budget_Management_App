
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from budgets.models import Budget
from expenses.models import Expense
from .models import Alert
from .services import evaluate_budget_thresholds


class BudgetThresholdAlertTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="alert_test@example.com",
            password="test-password-123",
        )

        self.budget = Budget.objects.create(
            user=self.user,
            name="Monthly Budget",
            limit_amount=Decimal("1000.00"),
            period="monthly",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 31),
        )

    def add_expense(self, amount):
        return Expense.objects.create(
            owner=self.user,
            amount=Decimal(str(amount)),
            date=date(2026, 10, 15),
            description="Test expense",
            is_deleted=False,
        )

    def test_alert_created_at_80_percent(self):
        self.add_expense("800.00")

        alert = Alert.objects.get(
            budget=self.budget,
            threshold_percentage=80,
        )

        self.assertEqual(alert.user, self.user)
        self.assertEqual(alert.alert_type, "threshold")

    def test_100_percent_creates_both_threshold_alerts(self):
        self.add_expense("1000.00")

        thresholds = set(
            Alert.objects.filter(
                budget=self.budget
            ).values_list(
                "threshold_percentage",
                flat=True,
            )
        )

        self.assertEqual(thresholds, {80, 100})

    def test_repeated_evaluation_does_not_duplicate_alerts(self):
        self.add_expense("800.00")

        evaluate_budget_thresholds(self.budget)
        evaluate_budget_thresholds(self.budget)

        self.assertEqual(
            Alert.objects.filter(budget=self.budget).count(),
            1,
        )

    def test_deleted_expenses_are_not_counted(self):
        self.add_expense("900.00")

        Expense.objects.create(
            owner=self.user,
            amount=Decimal("200.00"),
            date=date(2026, 10, 16),
            description="Deleted expense",
            is_deleted=True,
        )

        evaluate_budget_thresholds(self.budget)

        self.assertFalse(
            Alert.objects.filter(
                budget=self.budget,
                threshold_percentage=100,
            ).exists()
        )
