"""
Budget spending, shared by utilization, threshold alerts and rollover.

A budget counts the expenses of everyone who shares it: the owner and every
member (FR3). For a budget nobody else shares, that is just the owner.
"""

from decimal import Decimal

from django.db.models import Q, Sum

from expenses.models import Expense

from .models import Budget, BudgetMember

CENT = Decimal("0.01")


def budgets_for_user(user):
    """Budgets the user owns or is a member of."""
    return Budget.objects.filter(
        Q(user=user)
        | Q(pk__in=BudgetMember.objects.filter(user=user).values("budget_id"))
    )


def budget_expenses(budget):
    """Active expenses that count towards the budget."""
    expenses = Expense.objects.filter(
        Q(owner_id=budget.user_id)
        | Q(owner_id__in=BudgetMember.objects.filter(budget=budget).values("user_id")),
        is_deleted=False,
        date__range=(budget.start_date, budget.end_date),
    )
    # A budget without a category counts all expenses.
    if budget.category_id is not None:
        expenses = expenses.filter(category_id=budget.category_id)
    return expenses


def amount_spent(budget):
    total = budget_expenses(budget).aggregate(total=Sum("amount"))["total"]
    return (total or Decimal("0")).quantize(CENT)
