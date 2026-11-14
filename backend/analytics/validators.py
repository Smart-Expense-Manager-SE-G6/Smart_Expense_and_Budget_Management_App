from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from rest_framework import serializers

# docs/adr/0002-report-date-range-cap.md
MAX_RANGE_DAYS = 366


def user_today(user):
    """Today's date in the user's configured IANA time zone (D7)."""
    try:
        zone = ZoneInfo(getattr(user, "timezone", None) or "Asia/Kolkata")
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("Asia/Kolkata")
    return timezone.now().astimezone(zone).date()


def parse_date_range(request):
    """
    Parses and validates start_date and end_date query parameters.

    - Missing values default to the current month to date, in the user's time zone (D7).
    - The range is capped at 366 days with error code DATE_RANGE_EXCEEDED (ADR 0002).
    - Returns a tuple of (start_date, end_date) as datetime.date objects.
    """
    today = user_today(request.user)

    start_param = request.query_params.get("start_date")
    end_param = request.query_params.get("end_date")

    # 1. Parse start_date
    if start_param:
        try:
            start_date = date.fromisoformat(start_param)
        except ValueError:
            raise serializers.ValidationError(
                {"start_date": "Invalid date format. Expected ISO-8601 YYYY-MM-DD."}
            )
    else:
        # Default to first day of current calendar month
        start_date = today.replace(day=1)

    # 2. Parse end_date
    if end_param:
        try:
            end_date = date.fromisoformat(end_param)
        except ValueError:
            raise serializers.ValidationError(
                {"end_date": "Invalid date format. Expected ISO-8601 YYYY-MM-DD."}
            )
    else:
        # Default to today
        end_date = today

    # 3. Check start <= end
    if start_date > end_date:
        raise serializers.ValidationError(
            {"date_range": "start_date must be earlier than or equal to end_date."}
        )

    # 4. Check the one-year cap (ADR 0002)
    if (end_date - start_date).days > MAX_RANGE_DAYS:
        raise serializers.ValidationError(
            {
                "date_range": (
                    "Report date range cannot exceed 366 days (1 year). "
                    "Please select a narrower date range."
                )
            },
            code="DATE_RANGE_EXCEEDED",
        )

    return start_date, end_date
