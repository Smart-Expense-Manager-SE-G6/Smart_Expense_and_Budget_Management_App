from datetime import date

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination

from audit.mixins import AuditedModelViewSetMixin
from audit.services import audited

from .models import Category, Expense
from .serializers import ExpenseSerializer


class ExpensePagination(PageNumberPagination):
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


class ExpenseViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    pagination_class = ExpensePagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Expense.objects.filter(owner=self.request.user, is_deleted=False)

        category = self.request.query_params.get("category")
        if category is not None:
            try:
                category_id = int(category)
            except (TypeError, ValueError):
                raise ValidationError({"category": "Category must be a valid ID."})
            if category_id < 1:
                raise ValidationError({"category": "Category must be a valid ID."})
            if not Category.objects.filter(
                Q(pk=category_id),
                Q(owner__isnull=True) | Q(owner=self.request.user),
            ).exists():
                raise ValidationError({"category": "Category is invalid or inaccessible."})
            queryset = queryset.filter(category_id=category_id)

        start_date = self._parse_date("start_date")
        end_date = self._parse_date("end_date")
        if start_date and end_date and start_date > end_date:
            raise ValidationError({"date_range": "start_date cannot be later than end_date."})
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        ordering = self.request.query_params.get("ordering", "-date")
        allowed_ordering = {"date", "-date", "amount", "-amount", "created_at", "-created_at"}
        if ordering not in allowed_ordering:
            raise ValidationError({"ordering": "Unsupported ordering field."})
        return queryset.order_by(ordering, "-id")

    def _parse_date(self, parameter):
        value = self.request.query_params.get(parameter)
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValidationError({parameter: "Date must use YYYY-MM-DD format."})

    def perform_destroy(self, instance):
        with audited(self.request.user, instance):
            instance.is_deleted = True
            instance.save(update_fields=["is_deleted", "updated_at"])
