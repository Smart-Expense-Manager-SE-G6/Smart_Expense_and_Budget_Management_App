from django.urls import path

from .views import (
    AnalyticsByCategoryView,
    AnalyticsSummaryView,
    SpendingComparisonView,
)

urlpatterns = [
    path("summary/", AnalyticsSummaryView.as_view(), name="analytics-summary"),
    path("by-category/", AnalyticsByCategoryView.as_view(), name="analytics-by-category"),
    path("comparison/", SpendingComparisonView.as_view(), name="analytics-comparison"),
]
