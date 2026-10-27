
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
