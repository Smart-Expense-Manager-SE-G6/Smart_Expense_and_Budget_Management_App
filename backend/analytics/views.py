from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_analytics_by_category, get_analytics_summary
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
