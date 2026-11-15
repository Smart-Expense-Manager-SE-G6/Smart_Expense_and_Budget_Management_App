from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower


def receipt_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    return f"receipts/{instance.owner_id}/{uuid4().hex}{extension}"


class Category(models.Model):
    """
    A global category has no owner; an owned category belongs to one user.

    Model validation prevents self-parenting and cycles reachable through
    persisted parent links. Database constraints enforce scoped names and
    self-parenting, but deeper cycles require validation before saving because
    a SQL CHECK constraint cannot traverse an arbitrary hierarchy.
    """

    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="expense_categories",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                condition=Q(owner__isnull=True),
                name="category_global_name_ci_unique",
            ),
            models.UniqueConstraint(
                Lower("name"),
                F("owner"),
                condition=Q(owner__isnull=False),
                name="category_owner_name_ci_unique",
            ),
            models.CheckConstraint(
                condition=Q(parent__isnull=True) | ~Q(parent=F("pk")),
                name="category_not_own_parent",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "is_active"], name="category_owner_active_idx"),
        ]

    def clean(self):
        super().clean()

        if self.parent_id == self.pk and self.pk is not None:
            raise ValidationError({"parent": "A category cannot be its own parent."})

        if self.parent_id is None:
            return

        ancestor = self.parent
        visited = set()
        while ancestor is not None:
            if ancestor.pk in visited:
                raise ValidationError({"parent": "The category hierarchy contains a cycle."})
            visited.add(ancestor.pk)
            if self.pk is not None and ancestor.pk == self.pk:
                raise ValidationError({"parent": "The category hierarchy cannot contain a cycle."})
            ancestor = ancestor.parent

    def __str__(self):
        return self.name


class Expense(models.Model):
    """
    An INR expense independent of budgets.

    Expense deletion is represented by is_deleted. Future write APIs must use
    the existing audit.services.audited helper for create, update, and soft
    delete operations rather than hard-deleting rows.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    recurring_rule = models.ForeignKey(
        "RecurringRule", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="generated_expenses",
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    description = models.CharField(max_length=255, blank=True)
    merchant = models.CharField(max_length=255, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    payment_method = models.CharField(max_length=32, blank=True)
    receipt = models.FileField(
        blank=True,
        null=True,
        upload_to=receipt_upload_path,
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="expense_amount_positive",
            ),
            models.UniqueConstraint(fields=["recurring_rule", "date"], condition=Q(recurring_rule__isnull=False), name="expense_recurring_rule_date_unique"),
        ]
        indexes = [
            models.Index(
                fields=["owner", "is_deleted", "date"],
                name="expense_owner_active_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.owner} - {self.amount} on {self.date}"


class RecurringRule(models.Model):
    FREQUENCIES = [(value, value.title()) for value in ("daily", "weekly", "monthly", "yearly")]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recurring_rules")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT, related_name="recurring_rules")
    payment_method = models.CharField(max_length=32, blank=True)
    merchant = models.CharField(max_length=255, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCIES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="recurring_rule_amount_positive"),
            models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(start_date__lte=F("end_date")), name="recurring_rule_dates_valid"),
        ]
