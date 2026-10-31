from django.contrib.auth import get_user_model
from rest_framework import serializers

from expenses.models import Expense
from .models import Budget, BudgetMember
from .permissions import budget_role

SHARED_CATEGORY_MESSAGE = (
    "A shared budget can only use a default category, "
    "because members cannot use your custom categories."
)


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
        default=None,
    )
    owner_email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "user",
            "owner_email",
            "role",
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

    def get_role(self, budget):
        """The requesting user's role on this budget (FR3)."""
        request = self.context.get("request")
        return budget_role(budget, getattr(request, "user", None))

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

        category = attrs.get("category")
        if category is not None and category.owner_id is not None:
            owner = (
                self.instance.user
                if self.instance is not None
                else self.context["request"].user
            )
            if category.owner_id != owner.pk:
                raise serializers.ValidationError(
                    {"category": "Category is invalid or inaccessible."}
                )
            if (
                self.instance is not None
                and self.instance.memberships.exists()
            ):
                raise serializers.ValidationError(
                    {"category": SHARED_CATEGORY_MESSAGE}
                )

        return attrs


class BudgetMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = BudgetMember
        fields = ["id", "user", "email", "role", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "email", "created_at", "updated_at"]


class BudgetMemberCreateSerializer(serializers.Serializer):
    """Add an existing user to a budget by email. Needs `budget` in context."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=BudgetMember.Role.choices,
        default=BudgetMember.Role.MEMBER,
    )

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        budget = self.context["budget"]

        if budget.category is not None and budget.category.owner_id is not None:
            raise serializers.ValidationError(SHARED_CATEGORY_MESSAGE)

        user = get_user_model().objects.filter(email__iexact=attrs["email"]).first()
        if user is None:
            raise serializers.ValidationError(
                {"email": "No account is registered with this email."}
            )
        if user.pk == budget.user_id:
            raise serializers.ValidationError(
                {"email": "The budget owner is already an admin."}
            )
        if budget.memberships.filter(user=user).exists():
            raise serializers.ValidationError(
                {"email": "This user is already a member of the budget."}
            )

        attrs["user"] = user
        return attrs


class BudgetExpenseSerializer(serializers.ModelSerializer):
    """An expense counted by a shared budget, as other members see it."""

    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "owner",
            "owner_email",
            "category",
            "category_name",
            "amount",
            "description",
            "date",
            "payment_method",
        ]
        read_only_fields = fields
