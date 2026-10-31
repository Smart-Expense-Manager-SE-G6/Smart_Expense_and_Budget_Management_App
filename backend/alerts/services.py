
from decimal import Decimal

from django.db import transaction

from budgets.services import amount_spent
from core.adapters.factory import get_email_adapter
from .models import Alert


def evaluate_budget_thresholds(budget):
    """Create one alert per threshold for a budget period."""

    # Counts the owner's and every member's expenses (FR3).
    spent = amount_spent(budget)

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

            email_adapter = get_email_adapter()
            email_adapter.send_email(
                recipient=budget.user.email,
                subject=alert.title,
                message=alert.message,
            )

    return created_alerts
