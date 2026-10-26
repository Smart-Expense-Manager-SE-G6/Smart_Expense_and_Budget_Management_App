from django.db import transaction

from .models import AuditLog
from .services import audited, log_change


class AuditedModelViewSetMixin:
    """
    Drop-in for DRF ModelViewSet: create, update and destroy are each written
    atomically with an audit entry. Put it before ModelViewSet:

        class ExpenseViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet):
            ...

    For soft delete (D4), override perform_destroy to set the flag and call
    instance.save() inside `with audited(self.request.user, instance):`.
    """

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            log_change(self.request.user, AuditLog.Action.CREATE, instance)

    def perform_update(self, serializer):
        with audited(self.request.user, serializer.instance):
            serializer.save()

    def perform_destroy(self, instance):
        with audited(self.request.user, instance, action=AuditLog.Action.DELETE):
            instance.delete()
