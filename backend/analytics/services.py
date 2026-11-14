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
