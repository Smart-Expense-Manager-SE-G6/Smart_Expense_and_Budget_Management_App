from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    get_analytics_by_category,
    get_analytics_summary,
    get_predictive_insights,
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


class PredictiveInsightsView(APIView):
    """
    Endpoint for predictive month-end spend insights (FR14).
    GET /api/v1/analytics/predictive-insights/?year=YYYY&month=MM
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        year_param = request.query_params.get("year")
        month_param = request.query_params.get("month")
        year = None
        month = None
        if year_param is not None:
            try:
                year = int(year_param)
                if year < 2000 or year > 2100:
                    raise ValueError
            except ValueError:
                raise ValidationError({"year": "Year must be an integer between 2000 and 2100."})
        if month_param is not None:
            try:
                month = int(month_param)
                if month < 1 or month > 12:
                    raise ValueError
            except ValueError:
                raise ValidationError({"month": "Month must be an integer between 1 and 12."})

        data = get_predictive_insights(request.user, year=year, month=month)
        return Response(data)
