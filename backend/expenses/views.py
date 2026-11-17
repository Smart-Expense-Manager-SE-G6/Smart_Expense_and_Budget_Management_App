
from datetime import date

from django.http import FileResponse
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from audit.mixins import AuditedModelViewSetMixin
from audit.models import AuditLog
from audit.services import audited, log_change

# FR17: Spending anomaly detection
from alerts.services import detect_spending_anomaly

from .models import Category, Expense, RecurringRule
from .serializers import CategorySerializer, ExpenseSerializer, ReceiptUploadSerializer, RecurringRuleSerializer
from .services import suggest_categories
from .importers import ImportFileError, import_expenses


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

        search = self._text_param("search").strip()
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search)
                | Q(merchant__icontains=search)
                | Q(notes__icontains=search)
            )

        payment_method = self._text_param("payment_method")
        if payment_method:
            queryset = queryset.filter(payment_method__iexact=payment_method)

        ordering = self.request.query_params.get("ordering", "-date")
        allowed_ordering = {"date", "-date", "amount", "-amount", "created_at", "-created_at"}
        if ordering not in allowed_ordering:
            raise ValidationError({"ordering": "Unsupported ordering field."})
        return queryset.order_by(ordering, "-id")

    def _text_param(self, parameter):
        """
        A text filter from the query string. PostgreSQL cannot store or compare the
        NUL character, so a value containing it would crash the query with a 500;
        it can never match stored text, so it is refused with a 400 instead.
        """
        value = self.request.query_params.get(parameter, "")
        if "\x00" in value:
            raise ValidationError({parameter: "Remove the NUL (0x00) character from this value."})
        return value

    def _parse_date(self, parameter):
        value = self.request.query_params.get(parameter)
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValidationError({parameter: "Date must use YYYY-MM-DD format."})

    # FR17: Run anomaly detection after creating an expense.
    # Calling super() preserves the existing audit logging.
    def perform_create(self, serializer):
        super().perform_create(serializer)
        detect_spending_anomaly(serializer.instance)

    def perform_destroy(self, instance):
        with audited(self.request.user, instance):
            instance.is_deleted = True
            instance.save(update_fields=["is_deleted", "updated_at"])

    @action(detail=False, methods=["post"], url_path="import", parser_classes=[MultiPartParser])
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            raise ValidationError({"file": "This field is required."})
        dry_run = request.query_params.get("dry_run", "false").lower() == "true"
        try:
            result = import_expenses(upload, request.user, dry_run=dry_run)
        except ImportFileError as exc:
            raise ValidationError({"file": exc.message}, code=exc.code)
        return Response(result, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["get", "post", "delete"],
        url_path="receipt",
        parser_classes=[MultiPartParser],
    )
    def receipt(self, request, pk=None):
        expense = self.get_object()
        if request.method == "GET":
            return self._retrieve_receipt(expense)
        if request.method == "DELETE":
            return self._delete_receipt(request, expense)

        if expense.receipt:
            raise ValidationError(
                {"receipt": "This expense already has a receipt. Delete it before uploading another."}
            )
        serializer = ReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipt = serializer.validated_data["receipt"]
        with audited(request.user, expense):
            expense.receipt = receipt
            expense.save(update_fields=["receipt", "updated_at"])
        return Response({"detail": "Receipt uploaded."}, status=status.HTTP_201_CREATED)

    def _retrieve_receipt(self, expense):
        if not expense.receipt:
            raise NotFound("This expense has no receipt.")
        try:
            receipt_file = expense.receipt.storage.open(expense.receipt.name, "rb")
        except (FileNotFoundError, OSError):
            raise NotFound("The stored receipt is unavailable.")
        content_type = "application/octet-stream"
        extension = expense.receipt.name.rsplit(".", 1)[-1].lower()
        if extension in {"jpg", "jpeg"}:
            content_type = "image/jpeg"
        elif extension == "png":
            content_type = "image/png"
        elif extension == "pdf":
            content_type = "application/pdf"
        response = FileResponse(receipt_file, content_type=content_type)
        response["Content-Disposition"] = (
            f'attachment; filename="receipt-{expense.pk}.{extension}"'
        )
        return response

    def _delete_receipt(self, request, expense):
        if not expense.receipt:
            raise NotFound("This expense has no receipt.")
        storage, name = expense.receipt.storage, expense.receipt.name
        with audited(request.user, expense):
            expense.receipt = None
            expense.save(update_fields=["receipt", "updated_at"])
            # Remove the file only once the change is committed; a rollback keeps both.
            transaction.on_commit(lambda: storage.delete(name))
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Category.objects.filter(
            is_active=True,
        ).filter(
            Q(owner__isnull=True) | Q(owner=self.request.user)
        ).filter(
            Q(parent__isnull=True) | Q(parent__is_active=True)
        ).select_related("owner", "parent").order_by("name", "id")

    def perform_create(self, serializer):
        name = serializer.validated_data["name"]
        deleted = Category.objects.filter(
            owner=self.request.user, is_active=False, name__iexact=name
        ).first()
        if deleted is not None:
            # Re-creating a deleted category restores it, so its old expenses
            # and budgets stay linked and the per-owner unique name holds.
            self._restore(deleted, serializer)
            return
        with transaction.atomic():
            category = serializer.save(owner=self.request.user)
            log_change(self.request.user, AuditLog.Action.CREATE, category)

    def _restore(self, category, serializer):
        parent = serializer.validated_data.get("parent")
        ancestor = parent
        while ancestor is not None:
            if ancestor.pk == category.pk:
                raise ValidationError({"parent": "The category hierarchy cannot contain a cycle."})
            ancestor = ancestor.parent
        with audited(self.request.user, category):
            category.name = serializer.validated_data["name"]
            category.parent = parent
            category.is_active = True
            category.save(update_fields=["name", "parent", "is_active", "updated_at"])
        serializer.instance = category

    def perform_update(self, serializer):
        if serializer.instance.owner_id is None:
            raise PermissionDenied("Global categories cannot be modified.")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        if instance.owner_id is None:
            raise PermissionDenied("Global categories cannot be deleted.")
        if instance.children.filter(is_active=True).exists():
            raise ValidationError(
                {"parent": "Deactivate or reassign active subcategories first."}
            )
        with audited(self.request.user, instance):
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=False, methods=["get"], url_path="suggestions")
    def suggestions(self, request):
        description = request.query_params.get("description", "")
        merchant = request.query_params.get("merchant", "")
        if "\x00" in description:
            raise ValidationError(
                {"description": "Description cannot contain NUL characters."}
            )
        if "\x00" in merchant:
            raise ValidationError(
                {"merchant": "Merchant cannot contain NUL characters."}
            )
        if len(description) > 255:
            raise ValidationError(
                {"description": "Description must not exceed 255 characters."}
            )
        if len(merchant) > 255:
            raise ValidationError(
                {"merchant": "Merchant must not exceed 255 characters."}
            )
        return Response(
            {
                "suggestions": [
                    {"id": category.pk, "name": category.name}
                    for category in suggest_categories(
                        description, user=request.user, merchant=merchant
                    )
                ]
            }
        )


class RecurringRuleViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    serializer_class = RecurringRuleSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return RecurringRule.objects.filter(owner=self.request.user).select_related("category", "owner")

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._materialize_after_commit(serializer.instance)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._materialize_after_commit(serializer.instance)

    @staticmethod
    def _materialize_after_commit(rule):
        """Create any expenses already due (e.g. a rule starting today) without waiting for the daily run."""
        from .management.commands.materialize_recurring_expenses import materialize_rule

        transaction.on_commit(lambda: materialize_rule(rule.pk))

    def perform_destroy(self, instance):
        with audited(self.request.user, instance):
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
