
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import SimpleTestCase, TestCase

from budgets.models import Budget
from expenses.models import Expense
from .adapters import send_alert_email
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


class AlertEmailAdapterTests(SimpleTestCase):

    @patch("alerts.adapters.get_email_adapter")
    def test_send_alert_email_uses_configured_adapter(
        self, mock_get_adapter
    ):
        alert = Mock()
        alert.user.email = "user@example.com"
        alert.title = "Budget reached 80%"
        alert.message = "You have used 80% of your budget."

        expected_result = object()

        email_adapter = Mock()
        email_adapter.send_email.return_value = expected_result
        mock_get_adapter.return_value = email_adapter

        result = send_alert_email(alert)

        mock_get_adapter.assert_called_once_with()

        email_adapter.send_email.assert_called_once_with(
            recipient="user@example.com",
            subject="Budget reached 80%",
            message="You have used 80% of your budget.",
        )

        self.assertIs(result, expected_result)


class AlertApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="alerts.api@example.com", password="test-password-123")
        self.other = User.objects.create_user(email="other.alerts@example.com", password="test-password-123")
        self.client.force_login(self.user)

    def budget_payload(self, **overrides):
        payload = {
            "name": "October",
            "limit_amount": "1000.00",
            "period": "monthly",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31",
            "category": None,
        }
        payload.update(overrides)
        return payload

    def make_alert(self, owner):
        budget = Budget.objects.create(
            user=owner, name="Oct", limit_amount=Decimal("1000.00"), period="monthly",
            start_date=date(2026, 10, 1), end_date=date(2026, 10, 31),
        )
        Expense.objects.create(owner=owner, amount=Decimal("850.00"), date=date(2026, 10, 5))
        return Alert.objects.get(budget=budget)

    def thresholds(self):
        return sorted(a["threshold_percentage"] for a in self.client.get("/api/v1/alerts/").json())

    def test_list_shows_only_own_alerts(self):
        mine = self.make_alert(self.user)
        self.make_alert(self.other)

        response = self.client.get("/api/v1/alerts/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([a["id"] for a in response.json()], [mine.pk])

    def test_partial_update_marks_read_and_ignores_read_only_fields(self):
        alert = self.make_alert(self.user)

        response = self.client.patch(
            f"/api/v1/alerts/{alert.pk}/",
            {"is_read": True, "title": "changed", "threshold_percentage": 5},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        alert.refresh_from_db()
        self.assertEqual((alert.is_read, alert.title, alert.threshold_percentage), (True, "Budget reached 80%", 80))

    def test_mark_read_action(self):
        alert = self.make_alert(self.user)

        response = self.client.patch(f"/api/v1/alerts/{alert.pk}/mark-read/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_read"])

    def test_other_users_alert_cannot_be_read_or_changed(self):
        theirs = self.make_alert(self.other)

        self.assertEqual(self.client.get(f"/api/v1/alerts/{theirs.pk}/").status_code, 404)
        self.assertEqual(self.client.patch(f"/api/v1/alerts/{theirs.pk}/mark-read/").status_code, 404)
        theirs.refresh_from_db()
        self.assertFalse(theirs.is_read)

    def test_creating_a_budget_over_threshold_raises_alert(self):
        Expense.objects.create(owner=self.user, amount=Decimal("900.00"), date=date(2026, 10, 9))

        response = self.client.post("/api/v1/budgets/", self.budget_payload(), content_type="application/json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.thresholds(), [80])

    def test_lowering_a_budget_limit_raises_alert(self):
        Expense.objects.create(owner=self.user, amount=Decimal("900.00"), date=date(2026, 10, 9))
        budget_id = self.client.post(
            "/api/v1/budgets/", self.budget_payload(limit_amount="2000.00"), content_type="application/json"
        ).json()["id"]
        self.assertEqual(self.thresholds(), [])

        response = self.client.patch(
            f"/api/v1/budgets/{budget_id}/", {"limit_amount": "900.00"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.thresholds(), [80, 100])

    def test_alert_email_is_sent_only_after_commit(self):
        Budget.objects.create(
            user=self.user, name="Oct", limit_amount=Decimal("1000.00"), period="monthly",
            start_date=date(2026, 10, 1), end_date=date(2026, 10, 31),
        )
        with patch("alerts.adapters.get_email_adapter") as adapter:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                Expense.objects.create(owner=self.user, amount=Decimal("850.00"), date=date(2026, 10, 5))
            adapter.return_value.send_email.assert_not_called()

            for callback in callbacks:
                callback()

        adapter.return_value.send_email.assert_called_once_with(
            recipient="alerts.api@example.com",
            subject="Budget reached 80%",
            message="Oct: spent 850.00 of 1000.00 (85.0% used).",
        )

    def test_no_email_when_the_change_rolls_back(self):
        Budget.objects.create(
            user=self.user, name="Oct", limit_amount=Decimal("1000.00"), period="monthly",
            start_date=date(2026, 10, 1), end_date=date(2026, 10, 31),
        )
        with patch("alerts.adapters.get_email_adapter") as adapter:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                try:
                    with transaction.atomic():
                        Expense.objects.create(owner=self.user, amount=Decimal("850.00"), date=date(2026, 10, 5))
                        raise RuntimeError("simulated failure after the expense was written")
                except RuntimeError:
                    pass

        self.assertEqual(callbacks, [])
        adapter.return_value.send_email.assert_not_called()
        self.assertFalse(Alert.objects.exists())
