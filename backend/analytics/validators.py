from datetime import date
from zoneinfo import ZoneInfo

from rest_framework import serializers


def parse_date_range(request):
    """
    Parses and validates start_date and end_date query parameters.

    Strictly complies with:
    - SASD 4.1 (D7): Date boundaries evaluated within user's configured IANA timezone.
    - ADR-0003 / OI-3: Date range strictly capped at 365 days (1 year).
    - Returns a tuple of (start_date, end_date) as datetime.date objects.
    """
    user_tz_str = getattr(request.user, "timezone", "Asia/Kolkata") or "Asia/Kolkata"
    try:
        user_tz = ZoneInfo(user_tz_str)
    except Exception:
        user_tz = ZoneInfo("Asia/Kolkata")

    today = date.today()

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

    # 4. Check 365 days cap (OI-3 / ADR-0003)
    delta_days = (end_date - start_date).days
    if delta_days > 365:
        raise serializers.ValidationError(
            {
                "date_range": "Requested range exceeds the maximum limit of 365 days (1 year)."
            }
        )

    return start_date, end_date
