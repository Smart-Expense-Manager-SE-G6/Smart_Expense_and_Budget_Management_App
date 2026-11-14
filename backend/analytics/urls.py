from django.urls import path

from .views import (
    AnalyticsByCategoryView,
    AnalyticsSummaryView,
    PredictiveInsightsView,
    SpendingComparisonView,
)

urlpatterns = [
    path("summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("by-category/", AnalyticsByCategoryView.as_view(), name="analytics-by-category"),
    path("predictive-insights/", PredictiveInsightsView.as_view(), name="analytics-predictive-insights"),
    path("comparison/", SpendingComparisonView.as_view(), name="analytics-comparison"),
]
