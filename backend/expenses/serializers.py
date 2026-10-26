from rest_framework import serializers

from .models import Category, Expense


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            "id",
            "owner",
            "category",
            "amount",
            "description",
            "date",
            "payment_method",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "is_deleted", "created_at", "updated_at"]

    def validate_category(self, category):
        if category is None:
            return category

        user = self.context["request"].user
        if not category.is_active:
            raise serializers.ValidationError("The selected category is inactive.")
        if category.owner_id is not None and category.owner_id != user.pk:
            raise serializers.ValidationError("You cannot use another user's category.")
        return category

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)
