
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
