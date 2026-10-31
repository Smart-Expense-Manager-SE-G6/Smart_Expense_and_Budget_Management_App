from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.mixins import AuditedModelViewSetMixin
from audit.models import AuditLog
from audit.services import audited, log_change
from expenses.views import ExpensePagination

from .models import BudgetMember
from .permissions import MANAGER_ROLES, BudgetRolePermission, budget_role
from .serializers import (
    BudgetExpenseSerializer,
    BudgetMemberCreateSerializer,
    BudgetMemberSerializer,
    BudgetSerializer,
)
from .services import amount_spent, budget_expenses, budgets_for_user


class BudgetViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated, BudgetRolePermission]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        # Budgets the user owns or shares (FR3); anything else is a 404.
        return budgets_for_user(self.request.user).select_related(
            "user", "category"
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            budget = serializer.save(user=self.request.user)
            log_change(self.request.user, AuditLog.Action.CREATE, budget)

    def perform_destroy(self, instance):
        with audited(
            self.request.user,
            instance,
            action=AuditLog.Action.DELETE,
        ):
            instance.delete()

    # FR11 - Budget utilization, counting every member's spending (FR3).
    @action(detail=True, methods=["get"], url_path="utilization")
    def utilization(self, request, pk=None):
        budget = self.get_object()

        spent = amount_spent(budget)
        remaining_amount = budget.limit_amount - spent

        percentage_used = (
            spent * Decimal("100") / budget.limit_amount
        ).quantize(Decimal("0.01"))

        return Response({
            "budget_id": budget.pk,
            "amount_spent": str(spent),
            "budget_limit": str(budget.limit_amount),
            "remaining_amount": str(remaining_amount),
            "percentage_used": str(percentage_used),
        })

    # FR3 - Expenses of everyone sharing the budget.
    @action(detail=True, methods=["get"], url_path="expenses")
    def expenses(self, request, pk=None):
        budget = self.get_object()
        queryset = (
            budget_expenses(budget)
            .select_related("owner", "category")
            .order_by("-date", "-id")
        )
        paginator = ExpensePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        data = BudgetExpenseSerializer(page, many=True).data
        return paginator.get_paginated_response(data)

    # FR3 - List members (anyone sharing) or add one (admins).
    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        budget = self.get_object()

        if request.method == "GET":
            memberships = budget.memberships.select_related("user")
            return Response(BudgetMemberSerializer(memberships, many=True).data)

        serializer = BudgetMemberCreateSerializer(
            data=request.data,
            context={"budget": budget, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        membership = BudgetMember(
            budget=budget,
            user=serializer.validated_data["user"],
            role=serializer.validated_data["role"],
        )
        try:
            with audited(request.user, membership):
                membership.save()
        except IntegrityError:
            raise ValidationError(
                {"email": "This user is already a member of the budget."}
            )
        return Response(
            BudgetMemberSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    # FR3 - Change a member's role (admins) or remove them (admins, or themselves).
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"members/(?P<member_id>\d+)",
    )
    def member_detail(self, request, pk=None, member_id=None):
        budget = self.get_object()
        membership = (
            budget.memberships.select_related("user").filter(pk=member_id).first()
        )
        if membership is None:
            raise NotFound("Member not found.")

        is_manager = budget_role(budget, request.user) in MANAGER_ROLES

        if request.method == "DELETE":
            if not is_manager and membership.user_id != request.user.pk:
                raise PermissionDenied("Only a budget admin can remove other members.")
            with audited(request.user, membership, action=AuditLog.Action.DELETE):
                membership.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        if not is_manager:
            raise PermissionDenied("Only a budget admin can change member roles.")
        serializer = BudgetMemberSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        with audited(request.user, membership):
            serializer.save()
        return Response(serializer.data)
