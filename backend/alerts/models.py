
from django.conf import settings
from django.db import models


class Alert(models.Model):
    ALERT_TYPE_CHOICES = [
        ("threshold", "Budget Threshold"),
        ("anomaly", "Spending Anomaly"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    budget = models.ForeignKey(
        "budgets.Budget",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alerts",
    )
    threshold_percentage = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )
    period_start = models.DateField(null=True, blank=True)
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPE_CHOICES,
        default="threshold",
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["budget", "threshold_percentage", "period_start"],
                condition=models.Q(
                    alert_type="threshold",
                    budget__isnull=False,
                    threshold_percentage__isnull=False,
                    period_start__isnull=False,
                ),
                name="unique_budget_threshold_period_alert",
            ),
        ]

    def __str__(self):
        return self.title
