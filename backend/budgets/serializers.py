
import calendar
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from expenses.models import Category, Expense
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
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "user",
            "owner_email",
            "role",
            "member_count",
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

    def get_role(self, budget):
        """The requesting user's role on this budget: owner, admin or member (FR3)."""
        request = self.context.get("request")
        return budget_role(budget, getattr(request, "user", None))

    def get_member_count(self, budget):
        annotated = getattr(budget, "num_members", None)
        return annotated if annotated is not None else budget.memberships.count()

    def owner(self):
        """The budget's owner; admins may edit a budget they do not own."""
        return self.instance.user if self.instance is not None else self.context["request"].user

    def validate_category(self, category):
        if category is not None and not category.is_active:
            raise serializers.ValidationError("The selected category is inactive.")
        if category is not None and category.owner_id is not None:
            if category.owner_id != self.owner().pk:
                raise serializers.ValidationError("Category is invalid or inaccessible.")
            if self.instance is not None and self.instance.memberships.exists():
                raise serializers.ValidationError(SHARED_CATEGORY_MESSAGE)
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

        # D2: the period label must match the explicit dates, the same way
        # rollover_budgets computes the next period. Only checked when the period
        # or dates are being set, so older budgets can still be renamed.
        period = attrs.get("period", getattr(self.instance, "period", None))
        if start_date and end_date and {"period", "start_date", "end_date"} & attrs.keys():
            if period == "weekly" and end_date != start_date + timedelta(days=6):
                raise serializers.ValidationError(
                    {"end_date": "A weekly budget must cover exactly 7 days (end date = start date + 6 days)."}
                )
            if period == "monthly":
                if start_date.day != 1:
                    raise serializers.ValidationError(
                        {"start_date": "A monthly budget must start on the first day of a month."}
                    )
                month_end = start_date.replace(day=calendar.monthrange(start_date.year, start_date.month)[1])
                if end_date != month_end:
                    raise serializers.ValidationError(
                        {"end_date": "A monthly budget must end on the last day of the month it starts in."}
                    )

        category = attrs.get(
            "category",
            getattr(self.instance, "category", None),
        )

        # The database constraint cannot catch duplicate overall budgets
        # (NULL categories are distinct), so check both cases here.
        duplicates = Budget.objects.filter(
            user=self.owner(),
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


class BudgetMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = BudgetMember
        fields = ["id", "user", "email", "name", "role", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "email", "name", "created_at", "updated_at"]

    def get_name(self, membership):
        return membership.user.get_full_name()


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
