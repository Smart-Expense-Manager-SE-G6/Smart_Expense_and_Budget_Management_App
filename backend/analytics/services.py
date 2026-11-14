from decimal import Decimal

from django.db.models import Avg, Count, Sum

from core.charting_service import create_spending_chart
from expenses.models import Expense


def format_decimal(val):
    """Formats Decimal value to 2 decimal places as a string (SASD 4.1 D1)."""
    if val is None:
        return "0.00"
    if not isinstance(val, Decimal):
        val = Decimal(str(val))
    return f"{val.quantize(Decimal('0.01')):.2f}"


def get_analytics_summary(user, start_date, end_date):
    """
    Computes summary metrics for expenses within date range.

    Strictly satisfies:
    - SASD 3.5 / 3.6 / R3: Database-side aggregation with no row-by-row python loops.
    - SASD 4.1 (D1): Amounts stored and reported with 2 decimal places.
    - SASD 4.1 (D4): Excludes soft-deleted expenses (is_deleted=False).
    - NFR14: Strictly scopes data to requesting user.
    """
    base_qs = Expense.objects.filter(
        owner=user,
        is_deleted=False,
        date__gte=start_date,
        date__lte=end_date,
    )

    agg = base_qs.aggregate(
        total_spend=Sum("amount"),
        transaction_count=Count("id"),
        average_expense=Avg("amount"),
    )

    total_spend = agg["total_spend"] or Decimal("0.00")
    transaction_count = agg["transaction_count"] or 0
    average_expense = agg["average_expense"] or Decimal("0.00")

    # Determine top spending category via SQL ordering
    top_cat_agg = (
        base_qs.values("category__id", "category__name")
        .annotate(cat_total=Sum("amount"))
        .order_by("-cat_total")
        .first()
    )

    top_category = None
    if top_cat_agg and top_cat_agg["cat_total"]:
        top_category = {
            "id": top_cat_agg["category__id"],
            "name": top_cat_agg["category__name"] or "Uncategorized",
            "total_amount": format_decimal(top_cat_agg["cat_total"]),
        }

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_spend": format_decimal(total_spend),
        "transaction_count": transaction_count,
        "average_expense": format_decimal(average_expense),
        "top_category": top_category,
    }


def get_analytics_by_category(user, start_date, end_date):
    """
    Computes breakdown of spending grouped by category.

    Strictly satisfies:
    - SASD 3.5 / 3.6 / R3: Database-side GROUP BY aggregation via Django ORM.
    - SASD 4.1 (D1, D4): Exact Decimals, excludes soft-deleted records.
    - R4: Integrates with core charting adapter service.
    - Returns breakdown array and chart data structure.
    """
    base_qs = Expense.objects.filter(
        owner=user,
        is_deleted=False,
        date__gte=start_date,
        date__lte=end_date,
    )

    total_spend = base_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    category_records = (
        base_qs.values("category__id", "category__name")
        .annotate(
            total_amount=Sum("amount"),
            transaction_count=Count("id"),
        )
        .order_by("-total_amount")
    )

    categories = []
    chart_labels = []
    chart_values = []

    for item in category_records:
        cat_total = item["total_amount"] or Decimal("0.00")
        cat_name = item["category__name"] or "Uncategorized"
        count = item["transaction_count"]

        percentage = 0.0
        if total_spend > Decimal("0.00"):
            percentage = round(float((cat_total / total_spend) * 100), 2)

        categories.append(
            {
                "category_id": item["category__id"],
                "category_name": cat_name,
                "total_amount": format_decimal(cat_total),
                "transaction_count": count,
                "percentage": percentage,
            }
        )

        chart_labels.append(cat_name)
        chart_values.append(float(cat_total))

    # Generate chart payload via adapter (R4)
    chart = create_spending_chart(
        title=f"Category Breakdown ({start_date} to {end_date})",
        labels=chart_labels,
        values=chart_values,
    )

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_spend": format_decimal(total_spend),
        "categories": categories,
        "chart": chart,
    }


def get_predictive_insights(user, year: int | None = None, month: int | None = None, reference_date=None):
    """
    Compute projected month-end spend based on the user's current daily burn rate (FR14).
    """
    import calendar
    from datetime import date
    from django.utils import timezone
    from budgets.models import Budget

    today = reference_date or timezone.localdate()
    target_year = year or today.year
    target_month = month or today.month

    _, days_in_month = calendar.monthrange(target_year, target_month)
    month_start = date(target_year, target_month, 1)
    month_end = date(target_year, target_month, days_in_month)

    if (target_year, target_month) < (today.year, today.month):
        days_elapsed = days_in_month
        cutoff_date = month_end
    elif (target_year, target_month) > (today.year, today.month):
        days_elapsed = 0
        cutoff_date = month_start
    else:
        days_elapsed = max(today.day, 1)
        cutoff_date = today

    days_remaining = max(days_in_month - days_elapsed, 0)

    if days_elapsed == 0:
        total_spent = Decimal("0.00")
        cat_rows = []
    else:
        qs = Expense.objects.filter(
            owner=user,
            is_deleted=False,
            date__gte=month_start,
            date__lte=cutoff_date,
        )
        total_spent = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        cat_rows = (
            qs.values("category__id", "category__name")
            .annotate(total_amount=Sum("amount"))
            .order_by("-total_amount")
        )

    if days_elapsed > 0:
        daily_avg = (total_spent / Decimal(days_elapsed)).quantize(Decimal("0.01"))
        projected_spend = (daily_avg * Decimal(days_in_month)).quantize(Decimal("0.01"))
    else:
        daily_avg = Decimal("0.00")
        projected_spend = Decimal("0.00")

    # Check active monthly budgets overlapping this month
    active_budget_limit = (
        Budget.objects.filter(
            user=user,
            period="monthly",
            start_date__lte=month_end,
            end_date__gte=month_start,
            category__isnull=True,
        ).aggregate(total=Sum("limit_amount"))["total"]
    )
    if active_budget_limit is None:
        active_budget_limit = (
            Budget.objects.filter(
                user=user,
                period="monthly",
                start_date__lte=month_end,
                end_date__gte=month_start,
            ).aggregate(total=Sum("limit_amount"))["total"]
        )

    projected_overrun = None
    status = "no_budget"
    if active_budget_limit is not None and active_budget_limit > Decimal("0.00"):
        projected_overrun = format_decimal(projected_spend - active_budget_limit)
        ratio = projected_spend / active_budget_limit
        if ratio > Decimal("1.0"):
            status = "over_budget"
        elif ratio >= Decimal("0.8"):
            status = "at_risk"
        else:
            status = "on_track"

    by_category = []
    for row in cat_rows:
        cat_spent = row["total_amount"] or Decimal("0.00")
        cat_daily = (cat_spent / Decimal(days_elapsed)).quantize(Decimal("0.01")) if days_elapsed > 0 else Decimal("0.00")
        cat_proj = (cat_daily * Decimal(days_in_month)).quantize(Decimal("0.01"))
        by_category.append(
            {
                "category_id": row["category__id"],
                "category_name": row["category__name"] or "Uncategorized",
                "spent_so_far": format_decimal(cat_spent),
                "daily_average": format_decimal(cat_daily),
                "projected_month_end": format_decimal(cat_proj),
            }
        )

    return {
        "year": target_year,
        "month": target_month,
        "days_in_month": days_in_month,
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "total_spent_so_far": format_decimal(total_spent),
        "daily_average_spend": format_decimal(daily_avg),
        "projected_month_end_spend": format_decimal(projected_spend),
        "active_monthly_budget_limit": format_decimal(active_budget_limit) if active_budget_limit is not None else None,
        "projected_overrun": projected_overrun,
        "status": status,
        "by_category": by_category,
    }
