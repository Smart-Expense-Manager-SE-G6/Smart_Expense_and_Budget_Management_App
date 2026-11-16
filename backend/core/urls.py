
from django.urls import include, path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("monitoring/", include("monitoring.urls")),
    path("", include("expenses.urls")),
    path("", include("budgets.urls")),
    path("", include("alerts.urls")),
    path("", include("audit.urls")),
    path("analytics/", include("analytics.urls")),
]
