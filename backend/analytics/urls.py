from django.urls import path

from .views import AnalyticsByCategoryView, AnalyticsSummaryView, CustomReportView

urlpatterns = [
    path("summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("by-category/", AnalyticsByCategoryView.as_view(), name="analytics-by-category"),
    path("reports/", CustomReportView.as_view(), name="analytics-reports"),
]
