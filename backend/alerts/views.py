
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Alert
from .serializers import AlertSerializer


class AlertPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_number(self, request, paginator):
        value = request.query_params.get(self.page_query_param, "1")
        if not value.isdigit() or int(value) < 1:
            raise ValidationError({"page": "Page must be a positive integer."})
        return value

    def get_page_size(self, request):
        value = request.query_params.get(self.page_size_query_param)
        if value is None:
            return self.page_size
        if not value.isdigit() or int(value) < 1:
            raise ValidationError({"page_size": "Page size must be a positive integer."})
        if int(value) > self.max_page_size:
            raise ValidationError(
                {"page_size": f"Page size cannot exceed {self.max_page_size}."}
            )
        return int(value)


class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AlertPagination
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Alert.objects.filter(user=self.request.user).select_related(
            "budget", "expense"
        )
        alert_type = self.request.query_params.get("type")
        if alert_type in dict(Alert.ALERT_TYPE_CHOICES):
            queryset = queryset.filter(alert_type=alert_type)
        if self.request.query_params.get("unread", "").lower() == "true":
            queryset = queryset.filter(is_read=False)
        return queryset

    @action(detail=True, methods=["patch"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        alert = self.get_object()
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        return Response(self.get_serializer(alert).data)

    @action(detail=False, methods=["patch"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated_count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"updated_count": updated_count})
