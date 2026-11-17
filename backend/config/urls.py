from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.exceptions import handler404 as api_not_found

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/schema/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="schema-docs"),
    # Unknown API URLs get the JSON error envelope, even with DEBUG on.
    re_path(r"^api/", api_not_found),
]

handler404 = "core.exceptions.handler404"
handler500 = "core.exceptions.handler500"
