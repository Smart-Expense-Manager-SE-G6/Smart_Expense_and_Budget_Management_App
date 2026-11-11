
from decimal import Decimal

from django.db.models import Q
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
            "rollover_mode",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            # Mirrors the budget_limit_positive constraint so bad input is a 400, not a database error.
            "limit_amount": {"min_value": Decimal("0.01")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            # Only global categories and the user's own; another user's category
            # gets the same "does not exist" error as an unknown id.
            self.fields["category"].queryset = Category.objects.filter(
                Q(owner__isnull=True) | Q(owner=request.user)
            )

    def validate_category(self, category):
        if category is not None and not category.is_active:
            raise serializers.ValidationError("The selected category is inactive.")
        return category

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
                {
                    "end_date": (
                        "End date must be on or after the start date."
                    )
                }
            )

        category = attrs.get(
            "category",
            getattr(self.instance, "category", None),
        )

        # The database constraint cannot catch duplicate overall budgets
        # (NULL categories are distinct), so check both cases here.
        duplicates = Budget.objects.filter(
            user=self.context["request"].user,
            category=category,
            start_date=start_date,
            end_date=end_date,
        )
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                "A budget for this category and period already exists.",
                code="duplicate_budget",
            )

        return attrs
