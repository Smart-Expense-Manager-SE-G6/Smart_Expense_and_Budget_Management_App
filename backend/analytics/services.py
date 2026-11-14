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


def get_custom_date_range_report(user, start_date, end_date):
    """
    Generate a custom date range report with summary statistics,
    category-wise breakdown, and budget vs. actual comparison (FR19, FR20, NFR2).
    """
    from budgets.models import Budget

    summary_data = get_analytics_summary(user, start_date, end_date)
    category_data = get_analytics_by_category(user, start_date, end_date)

    budgets = (
        Budget.objects.filter(
            user=user,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        .select_related("category")
        .order_by("start_date", "name")
    )

    budget_vs_actual = []
    for budget in budgets:
        overlap_start = max(start_date, budget.start_date)
        overlap_end = min(end_date, budget.end_date)
        spent_qs = Expense.objects.filter(
            owner=user,
            is_deleted=False,
            date__gte=overlap_start,
            date__lte=overlap_end,
        )
        if budget.category_id is not None:
            spent_qs = spent_qs.filter(category_id=budget.category_id)

        actual_spent = spent_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        remaining = budget.limit_amount - actual_spent
        utilization = 0.0
        if budget.limit_amount > Decimal("0.00"):
            utilization = round(float((actual_spent / budget.limit_amount) * 100), 2)

        budget_vs_actual.append(
            {
                "budget_id": budget.id,
                "name": budget.name,
                "category_name": budget.category.name if budget.category else "Overall",
                "period": budget.period,
                "start_date": budget.start_date.isoformat(),
                "end_date": budget.end_date.isoformat(),
                "limit_amount": format_decimal(budget.limit_amount),
                "actual_spent": format_decimal(actual_spent),
                "remaining_amount": format_decimal(remaining),
                "utilization_percentage": utilization,
            }
        )

    total_spend_dec = Decimal(summary_data["total_spend"])
    tx_count = summary_data["transaction_count"]
    avg_spend = (total_spend_dec / Decimal(tx_count)).quantize(Decimal("0.01")) if tx_count > 0 else Decimal("0.00")

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": {
            "total_spend": summary_data["total_spend"],
            "transaction_count": tx_count,
            "average_spend": format_decimal(avg_spend),
        },
        "category_breakdown": category_data["categories"],
        "budget_vs_actual": budget_vs_actual,
    }
