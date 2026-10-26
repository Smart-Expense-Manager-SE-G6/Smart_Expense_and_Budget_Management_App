from django.db import transaction
from rest_framework import viewsets

from audit.mixins import AuditedModelViewSetMixin
from audit.services import audited

from .models import Expense
from .serializers import ExpenseSerializer


class ExpenseViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Expense.objects.filter(owner=self.request.user, is_deleted=False)

    def perform_destroy(self, instance):
        with audited(self.request.user, instance):
            instance.is_deleted = True
            instance.save(update_fields=["is_deleted", "updated_at"])
