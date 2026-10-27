import calendar
import secrets
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from alerts.models import Alert
from budgets.models import Budget

from ...models import Category, Expense


USER_COUNT = 5
EXPENSES_PER_USER = 100
CATEGORIES = (
    "Synthetic Groceries",
    "Synthetic Dining",
    "Synthetic Transport",
    "Synthetic Utilities",
    "Synthetic Shopping",
    "Synthetic Healthcare",
    "Synthetic Entertainment",
    "Synthetic Education",
    "Synthetic Travel",
    "Synthetic Subscriptions",
)
PAYMENT_METHODS = ("UPI", "Credit Card", "Debit Card", "Cash", "Net Banking")
EXPENSE_TEMPLATES = (
    "Synthetic grocery purchase",
    "Synthetic restaurant meal",
    "Synthetic local transport",
    "Synthetic electricity bill",
    "Synthetic household shopping",
    "Synthetic pharmacy purchase",
    "Synthetic movie and leisure",
    "Synthetic course material",
    "Synthetic travel booking",
    "Synthetic streaming subscription",
)


def _six_month_window(today):
    return today - timedelta(days=182), today


def _month_end(day):
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


class Command(BaseCommand):
    help = "Create or reuse a safe, idempotent synthetic expense dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without changing the database.",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.summary = {
            "users": {"created": 0, "reused": 0},
            "categories": {"created": 0, "reused": 0},
            "expenses": {"created": 0, "reused": 0},
            "budgets": {"created": 0, "reused": 0},
            "alerts": {"created": 0, "reused": 0},
        }

        if self.dry_run:
            self._seed()
        else:
            with transaction.atomic():
                self._seed()

        mode = "would be " if self.dry_run else ""
        self.stdout.write(self.style.SUCCESS("Synthetic data seeding complete."))
        for record_type, counts in self.summary.items():
            self.stdout.write(
                f"{record_type.capitalize()}: "
                f"{counts['created']} {mode}created, "
                f"{counts['reused']} reused"
            )
        if self.dry_run:
            self.stdout.write("Dry run: no database changes were made.")

    def _seed(self):
        users = self._seed_users()
        categories = self._seed_categories()
        self._seed_expenses(users, categories)
        budgets = self._seed_budgets(users, categories)
        self._seed_alerts(budgets)

    def _seed_users(self):
        user_model = get_user_model()
        users = []

        for index in range(1, USER_COUNT + 1):
            email = f"synthetic.expense.user{index:02d}@example.invalid"
            user = user_model.objects.filter(email=email).first()
            if user is not None:
                self.summary["users"]["reused"] += 1
            elif self.dry_run:
                user = user_model(
                    email=email,
                    first_name=f"Synthetic User {index}",
                    timezone="Asia/Kolkata",
                )
                self.summary["users"]["created"] += 1
            else:
                user = user_model.objects.create_user(
                    email=email,
                    password=secrets.token_urlsafe(32),
                    first_name=f"Synthetic User {index}",
                    timezone="Asia/Kolkata",
                )
                self.summary["users"]["created"] += 1
            users.append(user)

        return users

    def _seed_categories(self):
        categories = []

        for name in CATEGORIES:
            category = Category.objects.filter(
                owner__isnull=True,
                name__iexact=name,
            ).first()
            if category is not None:
                self.summary["categories"]["reused"] += 1
            elif self.dry_run:
                category = Category(name=name)
                self.summary["categories"]["created"] += 1
            else:
                category = Category.objects.create(name=name)
                self.summary["categories"]["created"] += 1
            categories.append(category)

        return categories

    def _seed_expenses(self, users, categories):
        today = timezone.localdate()
        start_date, end_date = _six_month_window(today)
        date_span = (end_date - start_date).days

        for user in users:
            existing = {}
            if user.pk is not None:
                existing = {
                    expense.description: expense
                    for expense in Expense.objects.filter(
                        owner=user,
                        description__startswith="Synthetic expense ",
                    )
                }
            pending = []

            for index in range(EXPENSES_PER_USER):
                description = f"Synthetic expense {index + 1:03d}"
                if description in existing:
                    self.summary["expenses"]["reused"] += 1
                    continue

                expense_date = start_date + timedelta(
                    days=(index * date_span) // (EXPENSES_PER_USER - 1)
                )
                category_index = index % len(categories)
                amount = Decimal(
                    str(Decimal("120.00") + Decimal((index * 47) % 1880))
                ).quantize(Decimal("0.01"))
                pending.append(
                    Expense(
                        owner=user,
                        category=categories[category_index],
                        amount=amount,
                        description=description,
                        date=expense_date,
                        payment_method=PAYMENT_METHODS[index % len(PAYMENT_METHODS)],
                    )
                )

            if pending and not self.dry_run:
                Expense.objects.bulk_create(pending)
            self.summary["expenses"]["created"] += len(pending)

    def _seed_budgets(self, users, categories):
        today = timezone.localdate()
        current_month_start = today.replace(day=1)
        previous_month_end = current_month_start - timedelta(days=1)
        previous_month_start = previous_month_end.replace(day=1)
        current_week_start = today - timedelta(days=today.weekday())
        budget_specs = (
            (
                "Synthetic monthly groceries",
                categories[0],
                Decimal("2500.00"),
                "monthly",
                current_month_start,
                _month_end(current_month_start),
            ),
            (
                "Synthetic monthly dining",
                categories[1],
                Decimal("1800.00"),
                "monthly",
                previous_month_start,
                previous_month_end,
            ),
            (
                "Synthetic weekly transport",
                categories[2],
                Decimal("900.00"),
                "weekly",
                current_week_start,
                current_week_start + timedelta(days=6),
            ),
            (
                "Synthetic monthly utilities",
                categories[3],
                Decimal("2200.00"),
                "monthly",
                previous_month_start,
                previous_month_end,
            ),
        )
        budgets = []

        for user in users:
            for name, category, limit, period, start_date, end_date in budget_specs:
                budget = None
                if user.pk is not None:
                    budget = Budget.objects.filter(
                        user=user,
                        name=name,
                    ).first()
                if budget is not None:
                    self.summary["budgets"]["reused"] += 1
                elif self.dry_run:
                    budget = Budget(
                        user=user,
                        category=category,
                        name=name,
                        limit_amount=limit,
                        base_limit_amount=limit,
                        period=period,
                        start_date=start_date,
                        end_date=end_date,
                        rollover_mode="reset",
                    )
                    self.summary["budgets"]["created"] += 1
                else:
                    budget = Budget.objects.create(
                        user=user,
                        category=category,
                        name=name,
                        limit_amount=limit,
                        base_limit_amount=limit,
                        period=period,
                        start_date=start_date,
                        end_date=end_date,
                        rollover_mode="reset",
                    )
                    self.summary["budgets"]["created"] += 1
                budgets.append(budget)

        return budgets

    def _seed_alerts(self, budgets):
        for budget in budgets:
            spent = Decimal("0.00")
            if budget.pk is not None:
                expenses = Expense.objects.filter(
                    owner=budget.user,
                    category=budget.category,
                    is_deleted=False,
                    date__range=(budget.start_date, budget.end_date),
                )
                spent = expenses.aggregate(total=Sum("amount"))["total"]
            spent = spent if spent is not None else Decimal("0.00")

            for threshold in (80, 100):
                if spent * 100 < budget.limit_amount * threshold:
                    continue

                existing = None
                if budget.pk is not None:
                    existing = Alert.objects.filter(
                        budget=budget,
                        threshold_percentage=threshold,
                        period_start=budget.start_date,
                        alert_type="threshold",
                    ).first()
                if existing is not None:
                    self.summary["alerts"]["reused"] += 1
                    continue

                self.summary["alerts"]["created"] += 1
                if not self.dry_run:
                    percentage = (spent * Decimal("100")) / budget.limit_amount
                    Alert.objects.create(
                        user=budget.user,
                        budget=budget,
                        threshold_percentage=threshold,
                        period_start=budget.start_date,
                        alert_type="threshold",
                        title=f"Budget reached {threshold}%",
                        message=(
                            f"{budget.name}: spent {spent} of "
                            f"{budget.limit_amount} ({percentage:.1f}% used)."
                        ),
                    )
