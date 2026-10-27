
import calendar
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from budgets.models import Budget
from expenses.models import Expense


def next_period_dates(budget):
    """Return the dates for the next weekly or monthly period."""
    next_start = budget.end_date + timedelta(days=1)

    if budget.period == "weekly":
        next_end = next_start + timedelta(days=6)
    elif budget.period == "monthly":
        last_day = calendar.monthrange(
            next_start.year,
            next_start.month,
        )[1]
        next_end = next_start.replace(day=last_day)
    else:
        raise ValueError(
            f"Unsupported budget period: {budget.period}"
        )

    return next_start, next_end


class Command(BaseCommand):
    help = "Process expired budgets and create their next periods."

    def handle(self, *args, **options):
        today = timezone.localdate()
        processed = 0

        expired_ids = list(
            Budget.objects.filter(end_date__lt=today)
            .order_by("end_date")
            .values_list("id", flat=True)
        )

        for budget_id in expired_ids:
            with transaction.atomic():
                budget = (
                    Budget.objects.select_for_update(of=("self",))
                    .select_related("user", "category")
                    .filter(pk=budget_id)
                    .first()
                )

                if budget is None or budget.end_date >= today:
                    continue

                expenses = Expense.objects.filter(
                    owner=budget.user,
                    is_deleted=False,
                    date__gte=budget.start_date,
                    date__lte=budget.end_date,
                )

                if budget.category_id is not None:
                    expenses = expenses.filter(
                        category_id=budget.category_id
                    )

                spent = expenses.aggregate(
                    total=Sum("amount")
                )["total"]

                if spent is None:
                    spent = Decimal("0.00")

                base_limit = (
                    budget.base_limit_amount
                    if budget.base_limit_amount is not None
                    else budget.limit_amount
                )

                unused = max(
                    Decimal("0.00"),
                    budget.limit_amount - spent,
                )

                carry_forward = (
                    unused
                    if budget.rollover_mode == "rollover"
                    else Decimal("0.00")
                )

                next_start, next_end = next_period_dates(budget)
                next_limit = base_limit + carry_forward

                # Locking the source budget serializes processing of
                # that budget. Explicitly check for an existing period,
                # including budgets whose category is NULL.
                next_budget_exists = Budget.objects.filter(
                    user=budget.user,
                    category=budget.category,
                    start_date=next_start,
                    end_date=next_end,
                ).exists()

                if next_budget_exists:
                    continue

                Budget.objects.create(
                    user=budget.user,
                    category=budget.category,
                    name=budget.name,
                    limit_amount=next_limit,
                    base_limit_amount=base_limit,
                    period=budget.period,
                    start_date=next_start,
                    end_date=next_end,
                    rollover_mode=budget.rollover_mode,
                )

                processed += 1

                self.stdout.write(
                    f"Created next period for '{budget.name}': "
                    f"{next_start} to {next_end}, "
                    f"limit {next_limit}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Budget rollover complete. "
                f"New periods created: {processed}"
            )
        )
