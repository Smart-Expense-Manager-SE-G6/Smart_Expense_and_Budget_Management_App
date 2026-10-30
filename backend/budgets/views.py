from decimal import Decimal
from django.db.models import Sum
from rest_framework.decorators import action
from rest_framework.response import Response
from expenses.models import Expense
from django.db import transaction
from rest_framework import viewsets

from audit.mixins import AuditedModelViewSetMixin
from audit.models import AuditLog
from audit.services import audited

from .models import Budget
from .serializers import BudgetSerializer


class BudgetViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related(
            "user", "category"
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            budget = serializer.save(user=self.request.user)
            from audit.services import log_change
            log_change(self.request.user, AuditLog.Action.CREATE, budget)

    def perform_destroy(self, instance):
        with audited(
            self.request.user,
            instance,
            action=AuditLog.Action.DELETE,
        ):
            instance.delete()

    # NEW: FR11 - Budget utilization
    @action(detail=True, methods=["get"], url_path="utilization")
    def utilization(self, request, pk=None):
        budget = self.get_object()

        expenses = Expense.objects.filter(
            owner=request.user,
            is_deleted=False,
            date__range=(budget.start_date, budget.end_date),
        )

        if budget.category_id is not None:
            expenses = expenses.filter(category_id=budget.category_id)

        amount_spent = expenses.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        remaining_amount = budget.limit_amount - amount_spent

        percentage_used = (
            amount_spent * Decimal("100") / budget.limit_amount
        ).quantize(Decimal("0.01"))

        return Response({
            "budget_id": budget.pk,
            "amount_spent": str(amount_spent),
            "budget_limit": str(budget.limit_amount),
            "remaining_amount": str(remaining_amount),
            "percentage_used": str(percentage_used),
        })