from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exporters import export_report_excel, export_report_pdf
from .services import (
    get_analytics_by_category,
    get_analytics_summary,
    get_custom_date_range_report,
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


class CustomReportView(APIView):
    """
    Endpoint for custom date range reports with 1-year cap (FR19, FR20, NFR2).
    GET /api/v1/analytics/reports/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date, end_date = parse_date_range(request)
        data = get_custom_date_range_report(request.user, start_date, end_date)
        return Response(data)


class CustomReportExportView(APIView):
    """
    Endpoint for exporting custom date range reports as PDF or Excel (FR19, FR20, NFR2).
    GET /api/v1/analytics/reports/export/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&export_format=pdf|xlsx
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        export_format = request.query_params.get("export_format", "pdf").lower()
        if export_format not in ("pdf", "xlsx"):
            raise ValidationError({"export_format": "Must be 'pdf' or 'xlsx'."})

        start_date, end_date = parse_date_range(request)
        report_data = get_custom_date_range_report(request.user, start_date, end_date)
        filename_base = f"expense_report_{report_data['start_date']}_to_{report_data['end_date']}"

        if export_format == "pdf":
            content = export_report_pdf(report_data)
            response = HttpResponse(content, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename_base}.pdf"'
            return response

        content = export_report_excel(report_data)
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename_base}.xlsx"'
        return response
