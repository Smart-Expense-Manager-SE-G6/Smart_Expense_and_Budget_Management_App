from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class AuditLog(models.Model):
    """
    Append-only record of a business change (FR21). Written by audit.services
    in the same transaction as the change itself; never edited afterwards.
    """

    class Action(models.TextChoices):
        CREATE = "create"
        UPDATE = "update"
        DELETE = "delete"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    entity_type = models.CharField(max_length=100)  # model label, e.g. "expenses.expense"
    entity_id = models.CharField(max_length=64)
    # DjangoJSONEncoder keeps Decimal amounts exact (stored as strings) and dates as ISO 8601.
    before = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    after = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    request_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("Audit entries are append-only and cannot be modified")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit entries are append-only and cannot be deleted")

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id}"
