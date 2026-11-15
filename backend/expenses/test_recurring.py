"""TC-Exp-04: recurring expense rules (FR6, SASD D3)."""

from datetime import date, datetime, timedelta, timezone as dt_timezone
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from alerts.models import Alert
from audit.models import AuditLog
from budgets.models import Budget
from expenses.management.commands.materialize_recurring_expenses import next_occurrence
from expenses.models import Category, Expense, RecurringRule

URL = "/api/v1/recurring-rules/"


def at_noon_utc(day):
    return datetime(day.year, day.month, day.day, 12, 0, tzinfo=dt_timezone.utc)


def run_on(day):
    """Run the daily command as if it were noon UTC on `day`."""
    with patch("analytics.validators.timezone.now", return_value=at_noon_utc(day)):
        call_command("materialize_recurring_expenses", stdout=StringIO())


class NextOccurrenceTests(TestCase):
    def test_daily_and_weekly(self):
        self.assertEqual(next_occurrence(date(2026, 12, 31), "daily", 31), date(2027, 1, 1))
        self.assertEqual(next_occurrence(date(2026, 12, 28), "weekly", 28), date(2027, 1, 4))

    def test_monthly_clamps_to_month_end_and_keeps_anchor(self):
        self.assertEqual(next_occurrence(date(2026, 1, 31), "monthly", 31), date(2026, 2, 28))
        self.assertEqual(next_occurrence(date(2026, 2, 28), "monthly", 31), date(2026, 3, 31))
        self.assertEqual(next_occurrence(date(2028, 1, 30), "monthly", 30), date(2028, 2, 29))
        self.assertEqual(next_occurrence(date(2026, 12, 15), "monthly", 15), date(2027, 1, 15))

    def test_yearly_keeps_the_month(self):
        self.assertEqual(next_occurrence(date(2026, 3, 10), "yearly", 10), date(2027, 3, 10))
        self.assertEqual(next_occurrence(date(2026, 12, 25), "yearly", 25), date(2027, 12, 25))

    def test_yearly_leap_day(self):
        self.assertEqual(next_occurrence(date(2028, 2, 29), "yearly", 29), date(2029, 2, 28))
        self.assertEqual(next_occurrence(date(2031, 2, 28), "yearly", 29), date(2032, 2, 29))


class MaterializeCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="rent@example.com", password="Tr1cky-Passw0rd!")
        self.food = Category.objects.get(name="Food", owner__isnull=True)

    def rule(self, **fields):
        values = {"owner": self.user, "amount": "15000.00", "frequency": "monthly", "start_date": date(2026, 1, 31)}
        values.update(fields)
        return RecurringRule.objects.create(**values)

    def dates(self, rule):
        return [e.date for e in Expense.objects.filter(recurring_rule=rule).order_by("date")]

    def test_month_end_rule_catches_up(self):
        rule = self.rule()
        run_on(date(2026, 3, 1))
        self.assertEqual(self.dates(rule), [date(2026, 1, 31), date(2026, 2, 28)])

    def test_catch_up_over_three_missed_periods(self):
        rule = self.rule(start_date=date(2026, 1, 5))
        run_on(date(2026, 4, 5))
        self.assertEqual(self.dates(rule), [date(2026, 1, 5), date(2026, 2, 5), date(2026, 3, 5), date(2026, 4, 5)])

    def test_running_twice_creates_nothing_new(self):
        rule = self.rule()
        run_on(date(2026, 3, 1))
        run_on(date(2026, 3, 1))
        self.assertEqual(len(self.dates(rule)), 2)

    def test_next_day_only_adds_the_new_occurrence(self):
        rule = self.rule(frequency="daily", start_date=date(2026, 5, 1))
        run_on(date(2026, 5, 3))
        run_on(date(2026, 5, 4))
        self.assertEqual(self.dates(rule), [date(2026, 5, d) for d in (1, 2, 3, 4)])

    def test_inactive_rule_creates_nothing(self):
        rule = self.rule(is_active=False)
        run_on(date(2026, 6, 1))
        self.assertEqual(self.dates(rule), [])

    def test_rule_stops_at_end_date(self):
        rule = self.rule(start_date=date(2026, 1, 10), end_date=date(2026, 2, 10))
        run_on(date(2026, 6, 1))
        self.assertEqual(self.dates(rule), [date(2026, 1, 10), date(2026, 2, 10)])

    def test_future_rule_creates_nothing_yet(self):
        rule = self.rule(start_date=date(2026, 7, 1))
        run_on(date(2026, 6, 30))
        self.assertEqual(self.dates(rule), [])

    def test_yearly_rule(self):
        rule = self.rule(frequency="yearly", start_date=date(2026, 3, 10))
        run_on(date(2028, 4, 1))
        self.assertEqual(self.dates(rule), [date(2026, 3, 10), date(2027, 3, 10), date(2028, 3, 10)])

    def test_uses_owner_time_zone_for_today(self):
        self.user.timezone = "Pacific/Kiritimati"  # UTC+14: already the next day at 12:00 UTC
        self.user.save(update_fields=["timezone"])
        rule = self.rule(frequency="daily", start_date=date(2026, 5, 2))
        run_on(date(2026, 5, 1))
        self.assertEqual(self.dates(rule), [date(2026, 5, 2)])

    def test_generated_expense_copies_rule_and_is_audited(self):
        rule = self.rule(category=self.food, payment_method="upi", merchant="Landlord", notes="Flat 4B", start_date=date(2026, 1, 1))
        run_on(date(2026, 1, 1))
        expense = Expense.objects.get(recurring_rule=rule)
        self.assertEqual((expense.owner, expense.category, str(expense.amount)), (self.user, self.food, "15000.00"))
        self.assertEqual((expense.payment_method, expense.merchant, expense.notes), ("upi", "Landlord", "Flat 4B"))
        self.assertTrue(AuditLog.objects.filter(entity_type="expenses.expense", entity_id=str(expense.pk),
                                                action=AuditLog.Action.CREATE).exists())

    def test_generated_expense_raises_budget_alert(self):
        today = date(2026, 1, 15)
        Budget.objects.create(user=self.user, name="Food", category=self.food, limit_amount="1000.00",
                              period="monthly", start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))
        self.rule(category=self.food, amount="900.00", start_date=today)
        run_on(today)
        self.assertTrue(Alert.objects.filter(user=self.user, alert_type="threshold", threshold_percentage=80).exists())


class RecurringRuleApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password="Tr1cky-Passw0rd!")
        self.other = User.objects.create_user(email="other@example.com", password="Tr1cky-Passw0rd!")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.food = Category.objects.get(name="Food", owner__isnull=True)

    def create(self, **body):
        values = {"amount": "500.00", "frequency": "monthly", "start_date": "2030-01-15", "category": self.food.id}
        values.update(body)
        return self.client.post(URL, values, format="json")

    def test_create_lists_with_next_run_date(self):
        response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["next_run_date"], "2030-01-15")
        self.assertEqual(response.json()["owner"], self.user.id)
        self.assertEqual(len(self.client.get(URL).json()), 1)

    def test_next_run_date_moves_past_today(self):
        start = date.today() - timedelta(days=3)
        response = self.create(frequency="weekly", start_date=start.isoformat())
        self.assertEqual(response.json()["next_run_date"], (start + timedelta(days=7)).isoformat())

    def test_rule_starting_today_creates_its_expense_immediately(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.create(start_date=date.today().isoformat())
        self.assertEqual(Expense.objects.filter(recurring_rule_id=response.json()["id"]).count(), 1)

    def test_pause_and_resume(self):
        rule_id = self.create().json()["id"]
        paused = self.client.patch(f"{URL}{rule_id}/", {"is_active": False}, format="json")
        self.assertEqual(paused.status_code, 200)
        self.assertFalse(RecurringRule.objects.get(pk=rule_id).is_active)
        self.assertIsNone(paused.json()["next_run_date"])
        resumed = self.client.patch(f"{URL}{rule_id}/", {"is_active": True}, format="json")
        self.assertTrue(RecurringRule.objects.get(pk=rule_id).is_active)
        self.assertEqual(resumed.json()["next_run_date"], "2030-01-15")

    def test_delete_ends_the_rule_and_keeps_expenses(self):
        with self.captureOnCommitCallbacks(execute=True):
            rule_id = self.create(start_date=date.today().isoformat()).json()["id"]
        self.assertEqual(self.client.delete(f"{URL}{rule_id}/").status_code, 204)
        self.assertFalse(RecurringRule.objects.get(pk=rule_id).is_active)
        self.assertEqual(Expense.objects.filter(recurring_rule_id=rule_id).count(), 1)

    def test_rule_changes_are_audited(self):
        rule_id = self.create().json()["id"]
        self.client.patch(f"{URL}{rule_id}/", {"amount": "600.00"}, format="json")
        actions = set(AuditLog.objects.filter(entity_type="expenses.recurringrule", entity_id=str(rule_id))
                      .values_list("action", flat=True))
        self.assertEqual(actions, {AuditLog.Action.CREATE, AuditLog.Action.UPDATE})

    def test_another_users_rule_is_not_found(self):
        rule = RecurringRule.objects.create(owner=self.other, amount="5.00", frequency="daily", start_date=date(2030, 1, 1))
        self.assertEqual(self.client.get(f"{URL}{rule.id}/").status_code, 404)
        self.assertEqual(self.client.patch(f"{URL}{rule.id}/", {"amount": "1.00"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(f"{URL}{rule.id}/").status_code, 404)

    def assert_field_error(self, response, field):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], field)

    def test_invalid_input(self):
        private = Category.objects.create(name="Private", owner=self.other)
        self.assert_field_error(self.create(amount="0"), "amount")
        self.assert_field_error(self.create(start_date="2030-02-01", end_date="2030-01-01"), "end_date")
        self.assert_field_error(self.create(category=private.id), "category")
        self.assert_field_error(self.create(frequency="hourly"), "frequency")

    def test_moving_start_after_end_is_rejected(self):
        rule_id = self.create(end_date="2030-06-01").json()["id"]
        self.assert_field_error(self.client.patch(f"{URL}{rule_id}/", {"start_date": "2030-07-01"}, format="json"), "end_date")

    def test_requires_login(self):
        self.assertIn(APIClient().get(URL).status_code, (401, 403))
