
from rest_framework import serializers

from expenses.models import Category
from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Budget
        fields = [
            "id",
            "user",
            "category",
            "category_name",
            "name",
            "limit_amount",
            "period",
            "start_date",
            "end_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after the start date."}
            )

        category = attrs.get(
            "category",
            getattr(self.instance, "category", None),
        )
        name = attrs.get("name", getattr(self.instance, "name", None))

        if category is not None and not Category.objects.filter(
            pk=category.pk
        ).exists():
            raise serializers.ValidationError(
                {"category": "Selected category does not exist."}
            )

        return attrs
