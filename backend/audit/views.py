"""
FR21 / SASD 4.3 `GET /audit`: read the audit trail.

Read-only. A user sees the history of:
- their own expenses, categories and recurring rules, and their own profile;
- budgets they own, and budgets they manage as an admin (SRS 6.5), including
  membership changes on those budgets.

Matching uses the stored before/after snapshots, so history stays visible
after a record is deleted.
"""

from django.db.models import Q
from rest_framework import mixins, serializers, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from budgets.models import BudgetMember
from budgets.services import budgets_for_user

from .models import AuditLog

# Friendly names accepted by ?entity= and returned as "entity".
ENTITIES = {
    "expense": "expenses.expense",
    "category": "expenses.category",
    "recurring_rule": "expenses.recurringrule",
    "budget": "budgets.budget",
    "budget_member": "budgets.budgetmember",
    "profile": "accounts.user",
}
LABELS = {label: name for name, label in ENTITIES.items()}

# Bookkeeping fields that change on every save and say nothing to the user.
HIDDEN_FIELDS = {"id", "created_at", "updated_at", "last_login", "password"}


def managed_budget_ids(user):
    """Budgets the user owns or administers."""
    budgets = budgets_for_user(user)
    admin_of = BudgetMember.objects.filter(user=user, role=BudgetMember.Role.ADMIN).values_list("budget_id", flat=True)
    return list(budgets.filter(Q(user=user) | Q(pk__in=admin_of)).values_list("pk", flat=True))


def visible_to(user):
    """A filter for the audit rows this user may read."""

    def owned(label, field):
        return Q(entity_type=label) & (Q(**{f"after__{field}": user.pk}) | Q(**{f"before__{field}": user.pk}))

    budget_ids = managed_budget_ids(user)
    return (
        owned("expenses.expense", "owner_id")
        | owned("expenses.category", "owner_id")
        | owned("expenses.recurringrule", "owner_id")
        | owned("budgets.budget", "user_id")
        | Q(entity_type="budgets.budget", entity_id__in=[str(pk) for pk in budget_ids])
        | (Q(entity_type="budgets.budgetmember")
           & (Q(after__budget_id__in=budget_ids) | Q(before__budget_id__in=budget_ids)))
        | Q(entity_type="accounts.user", entity_id=str(user.pk))
    )


def changes(entry):
    """Field-by-field differences: [{"field", "old", "new"}]."""
    before, after = entry.before or {}, entry.after or {}
    fields = [f for f in {**before, **after} if f not in HIDDEN_FIELDS]
    rows = []
    for field in sorted(fields):
        old, new = before.get(field), after.get(field)
        if entry.action == AuditLog.Action.UPDATE and old == new:
            continue
        rows.append({"field": field, "old": old, "new": new})
    return rows


class AuditEntrySerializer(serializers.ModelSerializer):
    entity = serializers.SerializerMethodField()
    actor_email = serializers.SerializerMethodField()
    changes = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "action", "entity", "entity_id", "actor_email", "changes", "request_id", "created_at"]

    def get_entity(self, entry):
        return LABELS.get(entry.entity_type, entry.entity_type)

    def get_actor_email(self, entry):
        # None means the system did it (scheduler, recurring rules, rollover).
        return entry.actor.email if entry.actor else None

    def get_changes(self, entry):
        return changes(entry)


class AuditPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AuditViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET /api/v1/audit/?entity=expense&entity_id=12 — newest first. No write methods exist."""

    serializer_class = AuditEntrySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AuditPagination

    def get_queryset(self):
        queryset = AuditLog.objects.filter(visible_to(self.request.user)).select_related("actor")
        entity = self.request.query_params.get("entity")
        if entity:
            if entity not in ENTITIES:
                raise ValidationError({"entity": f"Must be one of: {', '.join(ENTITIES)}."})
            queryset = queryset.filter(entity_type=ENTITIES[entity])
        entity_id = self.request.query_params.get("entity_id")
        if entity_id:
            if not entity_id.isdigit():
                raise ValidationError({"entity_id": "Must be a number."})
            queryset = queryset.filter(entity_id=entity_id)
        return queryset.order_by("-created_at", "-id")
