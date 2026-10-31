
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from expenses.models import Expense
from .adapters import send_alert_email
from .models import Alert


def evaluate_budget_thresholds(budget):
    """Create one alert per threshold for a budget period."""

    expenses = Expense.objects.filter(
        owner=budget.user,
        is_deleted=False,
        date__range=(budget.start_date, budget.end_date),
    )

    # Category-specific budgets count only their own category.
    # A budget without a category counts all expenses.
    if budget.category_id is not None:
        expenses = expenses.filter(category_id=budget.category_id)

    spent = expenses.aggregate(total=Sum("amount"))["total"]
    spent = spent if spent is not None else Decimal("0.00")

    limit_amount = budget.limit_amount

    if limit_amount <= 0:
        return []

    percentage = (spent * Decimal("100")) / limit_amount
    created_alerts = []

    for threshold in (80, 100):
        if percentage < threshold:
            continue

        with transaction.atomic():
            alert, created = Alert.objects.get_or_create(
                budget=budget,
                threshold_percentage=threshold,
                period_start=budget.start_date,
                alert_type="threshold",
                defaults={
                    "user": budget.user,
                    "title": f"Budget reached {threshold}%",
                    "message": (
                        f"{budget.name}: spent {spent} of "
                        f"{limit_amount} ({percentage:.1f}% used)."
                    ),
                },
            )

        if created:
            created_alerts.append(alert)
            send_alert_email(alert)

    return created_alerts
