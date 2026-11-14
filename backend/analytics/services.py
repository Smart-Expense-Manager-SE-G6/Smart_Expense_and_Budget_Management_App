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


def get_spending_comparison(
    user,
    granularity: str = "monthly",
    months: int = 6,
    years: int = 3,
    category_id: int | None = None,
    reference_date=None,
):
    """
    Compare user spending across months or years using DB-level date truncation (FR15, NFR1).
    """
    from datetime import date
    from django.db.models.functions import TruncMonth, TruncYear
    from django.utils import timezone

    today = reference_date or timezone.localdate()

    qs = Expense.objects.filter(owner=user, is_deleted=False)
    if category_id is not None:
        qs = qs.filter(category_id=category_id)

    if granularity == "yearly":
        start_year = today.year - years + 1
        start_date = date(start_year, 1, 1)
        qs = qs.filter(date__gte=start_date, date__lte=today)
        rows = (
            qs.annotate(period=TruncYear("date"))
            .values("period")
            .annotate(total_amount=Sum("amount"), transaction_count=Count("id"))
            .order_by("period")
        )
        row_map = {
            r["period"].year: (r["total_amount"] or Decimal("0.00"), r["transaction_count"])
            for r in rows
            if r["period"] is not None
        }
        period_keys = [str(y) for y in range(start_year, today.year + 1)]
        raw_series = [(str(y), *row_map.get(y, (Decimal("0.00"), 0))) for y in range(start_year, today.year + 1)]
    else:
        # Monthly: build the last `months` calendar months ending at today's month
        total_months = today.year * 12 + (today.month - 1)
        start_total = total_months - months + 1
        start_year, start_month_zero = divmod(start_total, 12)
        start_date = date(start_year, start_month_zero + 1, 1)

        qs = qs.filter(date__gte=start_date, date__lte=today)
        rows = (
            qs.annotate(period=TruncMonth("date"))
            .values("period")
            .annotate(total_amount=Sum("amount"), transaction_count=Count("id"))
            .order_by("period")
        )
        row_map = {
            (r["period"].year, r["period"].month): (r["total_amount"] or Decimal("0.00"), r["transaction_count"])
            for r in rows
            if r["period"] is not None
        }
        raw_series = []
        for idx in range(start_total, total_months + 1):
            y, m0 = divmod(idx, 12)
            m = m0 + 1
            label = f"{y:04d}-{m:02d}"
            amt, cnt = row_map.get((y, m), (Decimal("0.00"), 0))
            raw_series.append((label, amt, cnt))

    periods = []
    chart_labels = []
    chart_values = []
    prev_amount = None

    for label, amt, cnt in raw_series:
        change_amount = None
        change_percentage = None
        if prev_amount is not None:
            diff = amt - prev_amount
            change_amount = format_decimal(diff)
            if prev_amount > Decimal("0.00"):
                change_percentage = round(float((diff / prev_amount) * 100), 2)
        prev_amount = amt

        periods.append(
            {
                "period": label,
                "total_amount": format_decimal(amt),
                "transaction_count": cnt,
                "change_amount": change_amount,
                "change_percentage": change_percentage,
            }
        )
        chart_labels.append(label)
        chart_values.append(float(amt))

    chart = create_spending_chart(
        title=f"Spending Comparison ({granularity.capitalize()})",
        labels=chart_labels,
        values=chart_values,
    )

    return {
        "granularity": granularity,
        "periods": periods,
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
