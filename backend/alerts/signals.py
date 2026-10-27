from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from budgets.models import Budget
from expenses.models import Expense
from .services import evaluate_budget_thresholds


@receiver(post_save, sender=Expense)
def check_budget_thresholds(sender, instance, **kwargs):
    if instance.is_deleted:
        return

    budgets = Budget.objects.filter(
        user=instance.owner,
        start_date__lte=instance.date,
        end_date__gte=instance.date,
    ).filter(
        Q(category__isnull=True)
        | Q(category_id=instance.category_id)
    )

    for budget in budgets:
        evaluate_budget_thresholds(budget)