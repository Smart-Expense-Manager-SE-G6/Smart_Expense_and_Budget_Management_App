from django.conf import settings
from django.db import models
from django.db.models import Q


class Budget(models.Model):
    PERIOD_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    ]

    ROLLOVER_CHOICES = [
        ("reset", "Reset"),
        ("rollover", "Rollover"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    category = models.ForeignKey(
        "expenses.Category",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="budgets",
    )
    name = models.CharField(max_length=100)

    # Current spending limit for this budget period.
    limit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    # Original limit before any unused amount is carried forward.
    # Nullable so existing budgets remain compatible.
    base_limit_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    period = models.CharField(
        max_length=10,
        choices=PERIOD_CHOICES,
    )
    start_date = models.DateField()
    end_date = models.DateField()

    rollover_mode = models.CharField(
        max_length=10,
        choices=ROLLOVER_CHOICES,
        default="reset",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(limit_amount__gt=0),
                name="budget_limit_positive",
            ),
            models.CheckConstraint(
                condition=Q(start_date__lte=models.F("end_date")),
                name="budget_dates_valid",
            ),
            models.UniqueConstraint(
                fields=[
                    "user",
                    "category",
                    "start_date",
                    "end_date",
                ],
                name="unique_budget_period",
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.limit_amount}"
