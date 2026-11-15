from calendar import monthrange
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from audit.services import log_change
from audit.models import AuditLog
from expenses.models import Expense, RecurringRule


def next_occurrence(value, frequency, anchor_day):
    if frequency == "daily":
        return value + timedelta(days=1)
    if frequency == "weekly":
        return value + timedelta(days=7)
    if frequency == "yearly":
        year = value.year + 1
        return date(year, 2, 28 if anchor_day == 29 and year % 4 else anchor_day)
    month = value.month + 1
    year = value.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return date(year, month, min(anchor_day, monthrange(year, month)[1]))


class Command(BaseCommand):
    help = "Materialize due recurring expense rules through today."

    def handle(self, *args, **options):
        today = timezone.localdate()
        created = 0
        for rule_id in RecurringRule.objects.filter(is_active=True, start_date__lte=today).values_list("id", flat=True):
            with transaction.atomic():
                rule = RecurringRule.objects.select_for_update().select_related("category", "owner").get(pk=rule_id)
                if not rule.is_active:
                    continue
                occurrence = rule.start_date
                while occurrence <= today and (rule.end_date is None or occurrence <= rule.end_date):
                    if not Expense.objects.filter(recurring_rule=rule, date=occurrence).exists():
                        expense = Expense.objects.create(owner=rule.owner, recurring_rule=rule, category=rule.category, amount=rule.amount, date=occurrence, payment_method=rule.payment_method, merchant=rule.merchant, notes=rule.notes, description=rule.notes)
                        log_change(rule.owner, AuditLog.Action.CREATE, expense)
                        created += 1
                    occurrence = next_occurrence(occurrence, rule.frequency, rule.start_date.day)
        self.stdout.write(self.style.SUCCESS(f"Created {created} recurring expenses."))
