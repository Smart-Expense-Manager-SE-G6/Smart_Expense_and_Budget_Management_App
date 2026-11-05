
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from budgets.models import Budget
from expenses.models import Expense
from .models import Alert
from .services import (
    evaluate_budget_thresholds,
    detect_spending_anomaly,
)


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


class SpendingAnomalyAlertTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            email="anomaly_test@example.com",
            password="test-password-123",
        )

    def add_expense(self, amount, is_deleted=False):
        return Expense.objects.create(
            owner=self.user,
            amount=Decimal(str(amount)),
            date=date(2026, 10, 15),
            description="Test expense",
            is_deleted=is_deleted,
        )

    def add_previous_expenses(self):
        # Average = (100 + 150 + 200 + 150 + 200) / 5 = 160
        for amount in [100, 150, 200, 150, 200]:
            self.add_expense(amount)

    def test_anomaly_alert_created_for_unusual_expense(self):
        self.add_previous_expenses()

        expense = self.add_expense(1000)

        alert = detect_spending_anomaly(expense)

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, "anomaly")
        self.assertEqual(alert.user, self.user)

    def test_no_alert_when_expense_is_within_limit(self):
        self.add_previous_expenses()

        expense = self.add_expense(400)

        alert = detect_spending_anomaly(expense)

        self.assertIsNone(alert)

    def test_no_alert_when_expense_equals_threshold(self):
        self.add_previous_expenses()

        # Average = 160; threshold = 160 * 3 = 480
        expense = self.add_expense(480)

        alert = detect_spending_anomaly(expense)

        self.assertIsNone(alert)

    def test_no_alert_with_fewer_than_five_previous_expenses(self):
        for amount in [100, 150, 200, 150]:
            self.add_expense(amount)

        expense = self.add_expense(1000)

        alert = detect_spending_anomaly(expense)

        self.assertIsNone(alert)

    def test_deleted_expenses_are_ignored(self):
        for amount in [100, 150, 200, 150]:
            self.add_expense(amount)

        self.add_expense(200, is_deleted=True)

        expense = self.add_expense(1000)

        alert = detect_spending_anomaly(expense)

        self.assertIsNone(alert)

    def test_repeated_evaluation_does_not_duplicate_alerts(self):
        self.add_previous_expenses()

        expense = self.add_expense(1000)

        first_alert = detect_spending_anomaly(expense)
        second_alert = detect_spending_anomaly(expense)

        self.assertIsNotNone(first_alert)
        self.assertIsNone(second_alert)

        self.assertEqual(
            Alert.objects.filter(
                user=self.user,
                alert_type="anomaly",
            ).count(),
            1,
        )
