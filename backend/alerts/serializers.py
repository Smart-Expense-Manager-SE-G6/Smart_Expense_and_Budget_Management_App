
from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = [
            "id",
            "budget",
            "threshold_percentage",
            "period_start",
            "alert_type",
            "title",
            "message",
            "is_read",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "budget",
            "threshold_percentage",
            "period_start",
            "alert_type",
            "title",
            "message",
            "created_at",
        ]
        # Alerts are created only by the system (get_or_create under the database
        # constraint); clients may change is_read alone. DRF's auto-generated validator
        # for the conditional UniqueConstraint crashes on partial updates (KeyError
        # 'alert_type'), so it is switched off here.
        validators = []
