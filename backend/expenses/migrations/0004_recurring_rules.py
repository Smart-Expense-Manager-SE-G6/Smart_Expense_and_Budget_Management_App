from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import F, Q
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [("expenses", "0003_merge_20261028_1157")]
    operations = [
        migrations.CreateModel(
            name="RecurringRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("payment_method", models.CharField(blank=True, max_length=32)),
                ("merchant", models.CharField(blank=True, max_length=255)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("frequency", models.CharField(choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("yearly", "Yearly")], max_length=10)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="recurring_rules", to="expenses.category")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recurring_rules", to=settings.AUTH_USER_MODEL)),
            ],
            options={"constraints": [models.CheckConstraint(condition=Q(amount__gt=0), name="recurring_rule_amount_positive"), models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(start_date__lte=F("end_date")), name="recurring_rule_dates_valid")]},
        ),
        migrations.AddField(model_name="expense", name="recurring_rule", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_expenses", to="expenses.recurringrule")),
        migrations.AddField(model_name="expense", name="merchant", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="expense", name="notes", field=models.CharField(blank=True, max_length=255)),
        migrations.AddConstraint(model_name="expense", constraint=models.UniqueConstraint(condition=Q(recurring_rule__isnull=False), fields=("recurring_rule", "date"), name="expense_recurring_rule_date_unique")),
    ]
