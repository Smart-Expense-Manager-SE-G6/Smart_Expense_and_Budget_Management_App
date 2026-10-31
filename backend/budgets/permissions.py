"""
Shared-budget roles (FR3, SRS 6.5).

owner   The user who created the budget (Budget.user). Always an admin;
        cannot be removed or demoted. Only the owner may delete the budget.
admin   May change budget settings and add, remove or re-role members.
member  May view the budget, its utilization and its expenses. Their own
        expenses count towards it. May leave the budget.

Users with no role never see the budget at all (404, not 403).
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import BudgetMember

OWNER = "owner"
ADMIN = BudgetMember.Role.ADMIN
MEMBER = BudgetMember.Role.MEMBER
MANAGER_ROLES = {OWNER, ADMIN}


def budget_role(budget, user):
    """The user's role on the budget, or None if they have no access."""
    if user is None or not user.is_authenticated:
        return None
    if budget.user_id == user.pk:
        return OWNER
    return (
        BudgetMember.objects.filter(budget=budget, user=user)
        .values_list("role", flat=True)
        .first()
    )


class BudgetRolePermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        role = budget_role(obj, request.user)
        if role is None:
            return False
        if request.method in SAFE_METHODS:
            return True
        if view.action == "member_detail":
            # Members may remove themselves; the view checks the rest.
            return True
        if view.action == "destroy":
            self.message = "Only the budget owner can delete this budget."
            return role == OWNER
        self.message = "Only a budget admin can do this."
        return role in MANAGER_ROLES
