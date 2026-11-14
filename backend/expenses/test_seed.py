"""
Unit and integration tests for the seed_data management command (Issue #20 / NFR1).
Follows standard Django test runner discovery (test_*.py).
"""

from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from expenses.models import Category, Expense

User = get_user_model()


class SeedDataCommandTests(TestCase):
    """Verifies that seed_data generates valid, performant, and schema-compliant data."""

    def test_seed_data_generates_exact_count_and_types(self):
        out = StringIO()
        email = "test_perf@example.com"
        target_count = 500  # Representative test batch

        call_command("seed_data", email=email, count=target_count, stdout=out)

        # 1. Verify user created with active status and standard timezone
        user = User.objects.get(email=email)
        self.assertIsNotNone(user)
        self.assertTrue(user.is_active)
        self.assertEqual(user.timezone, "Asia/Kolkata")

        # 2. Verify global categories created
        categories = Category.objects.filter(owner=None, is_active=True)
        self.assertGreaterEqual(categories.count(), 8)

        # 3. Verify exact count, decimal amounts > 0, soft delete flag, and payment methods
        expenses = Expense.objects.filter(owner=user, is_deleted=False)
        self.assertEqual(expenses.count(), target_count)

        sample = expenses.first()
        self.assertIsInstance(sample.amount, Decimal)
        self.assertGreater(sample.amount, Decimal("0.00"))
        self.assertFalse(sample.is_deleted)
        self.assertIn(
            sample.payment_method,
            ["upi", "credit_card", "debit_card", "cash", "net_banking"],
        )

    def test_seed_data_clean_flag_wipes_previous(self):
        email = "test_clean@example.com"
        call_command("seed_data", email=email, count=50, stdout=StringIO())
        user = User.objects.get(email=email)
        self.assertEqual(Expense.objects.filter(owner=user).count(), 50)

        # Re-run with clean flag
        call_command("seed_data", email=email, count=25, clean=True, stdout=StringIO())
        self.assertEqual(Expense.objects.filter(owner=user).count(), 25)

    def test_seed_data_has_no_fixed_password(self):
        out = StringIO()
        call_command("seed_data", email="random_pw@example.com", count=1, stdout=out)

        user = User.objects.get(email="random_pw@example.com")
        self.assertFalse(user.check_password("Password123!"))
        generated = out.getvalue().split("Generated password (shown once): ")[1].split()[0]
        self.assertTrue(user.check_password(generated))

    def test_seed_data_accepts_explicit_password(self):
        call_command("seed_data", email="given_pw@example.com", count=1, password="Given-Passw0rd!", stdout=StringIO())

        self.assertTrue(User.objects.get(email="given_pw@example.com").check_password("Given-Passw0rd!"))


class SeedSyntheticDataCommandTests(TestCase):
    def test_synthetic_categories_belong_to_synthetic_users(self):
        globals_before = set(Category.objects.filter(owner__isnull=True).values_list("pk", flat=True))

        call_command("seed_synthetic_data", stdout=StringIO())

        self.assertEqual(set(Category.objects.filter(owner__isnull=True).values_list("pk", flat=True)), globals_before)
        synthetic = Category.objects.filter(name__startswith="Synthetic ")
        self.assertTrue(synthetic.exists())
        self.assertFalse(synthetic.filter(owner__isnull=True).exists())
        for expense in Expense.objects.filter(description__startswith="Synthetic expense "):
            self.assertEqual(expense.category.owner_id, expense.owner_id)

    def test_synthetic_seed_is_idempotent_and_dry_run_writes_nothing(self):
        call_command("seed_synthetic_data", "--dry-run", stdout=StringIO())
        self.assertFalse(Expense.objects.exists())

        call_command("seed_synthetic_data", stdout=StringIO())
        counts = (Category.objects.count(), Expense.objects.count())
        call_command("seed_synthetic_data", stdout=StringIO())
        self.assertEqual((Category.objects.count(), Expense.objects.count()), counts)
