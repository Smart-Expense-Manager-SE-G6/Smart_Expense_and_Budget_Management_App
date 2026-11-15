"""
FR6 / SASD D3: turn recurring rules into ordinary expenses on their due dates.

Safe to run any number of times a day: each rule is locked while it is
processed, and an expense is created only for dates the rule has not produced
yet (also enforced by the unique (recurring_rule, date) constraint). Missed
runs are caught up on the next run. "Today" is the rule owner's local date.
"""

from calendar import monthrange
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from analytics.validators import user_today
from audit.models import AuditLog
from audit.services import log_change
from expenses.models import Expense, RecurringRule


def _on_day(year, month, anchor_day):
    """The anchor day in that month, clamped to the month's last day (31 Jan -> 28 Feb)."""
    return date(year, month, min(anchor_day, monthrange(year, month)[1]))


def next_occurrence(value, frequency, anchor_day):
    if frequency == "daily":
        return value + timedelta(days=1)
    if frequency == "weekly":
        return value + timedelta(days=7)
    if frequency == "yearly":
        return _on_day(value.year + 1, value.month, anchor_day)
    month = value.month % 12 + 1
    year = value.year + (1 if value.month == 12 else 0)
    return _on_day(year, month, anchor_day)


def due_dates(rule, today):
    """Every occurrence from the start date up to today and the end date, inclusive."""
    last = min(today, rule.end_date) if rule.end_date else today
    occurrence = rule.start_date
    while occurrence <= last:
        yield occurrence
        occurrence = next_occurrence(occurrence, rule.frequency, rule.start_date.day)


def materialize_rule(rule_id):
    """Create the missing expenses for one rule. Returns how many were created."""
    with transaction.atomic():
        # Lock only the rule row: the category join is nullable and PostgreSQL
        # refuses FOR UPDATE on the nullable side of an outer join.
        rule = (
            RecurringRule.objects.select_for_update(of=("self",))
            .select_related("category", "owner")
            .get(pk=rule_id)
        )
        if not rule.is_active:
            return 0
        today = user_today(rule.owner)
        done = set(Expense.objects.filter(recurring_rule=rule).values_list("date", flat=True))
        created = 0
        for occurrence in due_dates(rule, today):
            if occurrence in done:
                continue
            expense = Expense.objects.create(
                owner=rule.owner,
                recurring_rule=rule,
                category=rule.category,
                amount=rule.amount,
                date=occurrence,
                payment_method=rule.payment_method,
                merchant=rule.merchant,
                notes=rule.notes,
                description=rule.merchant or rule.notes,
            )
            log_change(rule.owner, AuditLog.Action.CREATE, expense)
            created += 1
        return created


class Command(BaseCommand):
    help = "Create the expenses that active recurring rules are due to produce, up to today."

    def handle(self, *args, **options):
        rule_ids = RecurringRule.objects.filter(is_active=True).values_list("id", flat=True)
        created = sum(materialize_rule(rule_id) for rule_id in rule_ids)
        self.stdout.write(self.style.SUCCESS(f"Created {created} recurring expenses."))
