
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum

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
            # Send only once the surrounding change is committed, so a rolled-back
            # expense or budget never produces an email.
            transaction.on_commit(lambda alert=alert: send_alert_email(alert))

    return created_alerts


def detect_spending_anomaly(expense):
    """
    Detect an unusually large expense by comparing it with
    the user's previous five expenses in the same category.

    An anomaly is flagged when the new expense is greater
    than three times the historical average.
    """

    if expense.is_deleted:
        return None

    # Find expenses from the same user and category
    # that occurred before the current expense.
    previous_expenses = Expense.objects.filter(
        owner=expense.owner,
        category_id=expense.category_id,
        is_deleted=False,
    ).filter(
        Q(date__lt=expense.date)
        | Q(date=expense.date, created_at__lt=expense.created_at)
    ).exclude(
        pk=expense.pk
    ).order_by(
        "-date", "-created_at"
    )[:5]

    previous_amounts = [
        item.amount for item in previous_expenses
    ]

    # Wait until five previous expenses are available.
    if len(previous_amounts) < 5:
        return None

    average_amount = (
        sum(previous_amounts, Decimal("0.00"))
        / Decimal("5")
    )

    if average_amount <= 0:
        return None

    anomaly_limit = average_amount * Decimal("3")

    # The expense must be greater than three times the average.
    if expense.amount <= anomaly_limit:
        return None

    category_name = (
        expense.category.name
        if expense.category_id
        else "Uncategorized"
    )

    title = f"Unusual transaction detected - Expense #{expense.pk}"

    message = (
        f"Your {category_name} expense of {expense.amount} "
        f"is unusually high. Your average for the previous "
        f"five expenses in this category was {average_amount:.2f}."
    )

    # Avoid creating the same anomaly alert again
    # if this expense is evaluated more than once.
    alert, created = Alert.objects.get_or_create(
        user=expense.owner,
        alert_type="anomaly",
        title=title,
        defaults={
            "message": message,
            "period_start": expense.date,
        },
    )

    if created:
        return alert

    return None
