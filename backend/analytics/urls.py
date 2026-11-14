from django.urls import path

from .views import (
    AnalyticsByCategoryView,
    AnalyticsSummaryView,
    PredictiveInsightsView,
    SpendingComparisonView,
    CustomReportExportView,
    CustomReportView,
)

urlpatterns = [
    path("summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("by-category/", AnalyticsByCategoryView.as_view(), name="analytics-by-category"),
    path("predictive-insights/", PredictiveInsightsView.as_view(), name="analytics-predictive-insights"),
    path("comparison/", SpendingComparisonView.as_view(), name="analytics-comparison"),
    path("reports/", CustomReportView.as_view(), name="analytics-reports"),
    path("reports/export/", CustomReportExportView.as_view(), name="analytics-reports-export"),
]
