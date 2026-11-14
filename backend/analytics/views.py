from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    get_analytics_by_category,
    get_analytics_summary,
    get_spending_comparison,
)
from .validators import parse_date_range


class AnalyticsSummaryView(APIView):
    """
    Endpoint for overall spending analytics summary (FR13, R3).
    GET /api/v1/analytics/summary?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date, end_date = parse_date_range(request)
        data = get_analytics_summary(request.user, start_date, end_date)
        return Response(data)


class AnalyticsByCategoryView(APIView):
    """
    Endpoint for category-wise spending analytics breakdown (FR13, R3).
    GET /api/v1/analytics/by-category?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date, end_date = parse_date_range(request)
        data = get_analytics_by_category(request.user, start_date, end_date)
        return Response(data)


class SpendingComparisonView(APIView):
    """
    Endpoint for comparing spending across months or years (FR15).
    GET /api/v1/analytics/comparison/?granularity=monthly|yearly&months=6&years=3&category_id=
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        granularity = request.query_params.get("granularity", "monthly").lower()
        if granularity not in ("monthly", "yearly"):
            raise ValidationError({"granularity": "Must be 'monthly' or 'yearly'."})

        months = 6
        if "months" in request.query_params:
            try:
                months = int(request.query_params["months"])
                if months < 1 or months > 24:
                    raise ValueError
            except ValueError:
                raise ValidationError({"months": "Must be an integer between 1 and 24."})

        years = 3
        if "years" in request.query_params:
            try:
                years = int(request.query_params["years"])
                if years < 1 or years > 5:
                    raise ValueError
            except ValueError:
                raise ValidationError({"years": "Must be an integer between 1 and 5."})

        category_id = None
        if request.query_params.get("category_id"):
            try:
                category_id = int(request.query_params["category_id"])
            except ValueError:
                raise ValidationError({"category_id": "Must be an integer."})

        data = get_spending_comparison(
            request.user,
            granularity=granularity,
            months=months,
            years=years,
            category_id=category_id,
        )
        return Response(data)
