"""
Seed command generating 10,000 expense transactions for performance testing (Issue #20 / NFR1).

Strictly adheres to:
- SASD 4.1 (D1): Amounts stored as exact Decimal(12, 2) > 0.00.
- SASD 4.1 (D4): Preserves is_deleted=False on active transactions.
- SASD 4.1 (D7): Distributed within the user's time zone over the past 365 days.
- NFR1: Seed loads efficiently via bulk_create to support sub-3s query benchmarks.
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from expenses.models import Category, Expense

User = get_user_model()

DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Transportation",
    "Bills & Utilities",
    "Entertainment",
    "Shopping",
    "Healthcare",
    "Travel",
]

PAYMENT_METHODS = ["upi", "credit_card", "debit_card", "cash", "net_banking"]

SAMPLE_DESCRIPTIONS = {
    "Food & Dining": ["Lunch at Cafe", "Dinner with team", "Coffee and snacks", "Swiggy order", "Zomato delivery"],
    "Groceries": ["Weekly supermarket run", "Vegetables and fruits", "Dairy and essentials", "Blinkit order"],
    "Transportation": ["Metro card recharge", "Uber ride to office", "Auto rickshaw fare", "Fuel / Petrol"],
    "Bills & Utilities": ["Electricity bill", "Broadband internet", "Mobile recharge", "Piped gas bill"],
    "Entertainment": ["Movie tickets", "Streaming subscription", "Concert pass", "Weekend outing"],
    "Shopping": ["Clothing purchase", "Electronics accessory", "Home decor", "Amazon order"],
    "Healthcare": ["Pharmacy medicines", "Doctor consultation", "Health checkup", "Supplements"],
    "Travel": ["Train ticket", "Flight booking", "Hotel reservation", "Cab rental"],
}


class Command(BaseCommand):
    help = "Seed 10,000 realistic expense transactions for single-user performance testing (NFR1)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            default="perfuser@example.com",
            help="Target user email for seeded transactions (default: perfuser@example.com).",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=10000,
            help="Total number of transactions to generate (default: 10000).",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=2000,
            help="Database bulk insertion batch size (default: 2000).",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete existing expenses for this user before seeding.",
        )

    def handle(self, *args, **options):
        email = options["email"].lower().strip()
        count = options["count"]
        batch_size = options["batch_size"]
        clean = options["clean"]

        self.stdout.write(self.style.NOTICE(f"Preparing seed data for user '{email}' (Target: {count} transactions)..."))

        # 1. Ensure target user exists
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
                "timezone": "Asia/Kolkata",
            },
        )
        if created:
            user.set_password("Password123!")
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user: {email}"))
        else:
            self.stdout.write(f"Using existing user: {email}")

        # 2. Optionally clean existing transactions
        if clean:
            deleted_count, _ = Expense.objects.filter(owner=user).delete()
            self.stdout.write(self.style.WARNING(f"Cleaned {deleted_count} existing expenses for {email}."))

        # 3. Ensure global categories exist
        category_objects = []
        for cat_name in DEFAULT_CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                name=cat_name,
                owner=None,
                defaults={"is_active": True},
            )
            category_objects.append(cat)
        self.stdout.write(f"Verified {len(category_objects)} global categories.")

        # 4. Generate deterministic, realistic transactions across the past 365 days
        self.stdout.write(f"Generating {count} synthetic expense transactions...")
        today = date.today()
        expenses_to_create = []

        rng = random.Random(42)  # Deterministic seed for reproducible testing

        for _ in range(count):
            cat = rng.choice(category_objects)
            days_offset = rng.randint(0, 365)
            tx_date = today - timedelta(days=days_offset)

            # 85% regular everyday expenses (₹20 - ₹1500), 15% larger bills (₹1500 - ₹12000)
            if rng.random() < 0.85:
                amount_val = round(rng.uniform(20.0, 1500.0), 2)
            else:
                amount_val = round(rng.uniform(1500.0, 12000.0), 2)
            amount = Decimal(str(amount_val))

            desc_choices = SAMPLE_DESCRIPTIONS.get(cat.name, ["General Expense"])
            description = rng.choice(desc_choices)
            payment_method = rng.choice(PAYMENT_METHODS)

            expenses_to_create.append(
                Expense(
                    owner=user,
                    category=cat,
                    amount=amount,
                    description=description,
                    date=tx_date,
                    payment_method=payment_method,
                    is_deleted=False,
                )
            )

        # 5. Insert in atomic batches for optimal performance
        self.stdout.write(f"Bulk inserting {len(expenses_to_create)} records into PostgreSQL...")
        with transaction.atomic():
            Expense.objects.bulk_create(expenses_to_create, batch_size=batch_size)

        total_user_expenses = Expense.objects.filter(owner=user, is_deleted=False).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {count} transactions! User '{email}' now has {total_user_expenses} active expenses."
            )
        )
