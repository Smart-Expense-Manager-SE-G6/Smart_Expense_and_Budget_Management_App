from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from expenses.models import Category, Expense

User = get_user_model()


class AnalyticsAPITests(TestCase):
    """
    Comprehensive test suite for Analytics endpoints (FR13, R3, R4, NFR14).
    Validates:
    - Summary and by-category metrics.
    - Exact 2-decimal string format (SASD 4.1 D1).
    - Soft-delete exclusion (SASD 4.1 D4).
    - User data isolation (NFR14).
    - Date filtering and ADR-0003 365-day range cap.
    - Error envelope compliance (SASD 4.4).
    - Chart adapter integration (R4).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="shashank.analytics@example.com",
            password="SecurePassword123!",
            timezone="Asia/Kolkata",
        )
        self.other_user = User.objects.create_user(
            email="other.user@example.com",
            password="SecurePassword123!",
            timezone="Asia/Kolkata",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create categories
        self.cat_food = Category.objects.create(name="Food & Dining", is_active=True)
        self.cat_travel = Category.objects.create(name="Travel", is_active=True)
        self.cat_bills = Category.objects.create(name="Bills", is_active=True)

        today = date.today()

        # Expenses for self.user:
        # Food: 200.50 + 100.00 = 300.50
        # Travel: 500.25
        # Soft-deleted: 1000.00 (MUST BE EXCLUDED)
        # Outside date range: 250.00 (MUST BE EXCLUDED)
        Expense.objects.create(
            owner=self.user,
            category=self.cat_food,
            amount=Decimal("200.50"),
            date=today - timedelta(days=5),
            payment_method="upi",
        )
        Expense.objects.create(
            owner=self.user,
            category=self.cat_food,
            amount=Decimal("100.00"),
            date=today - timedelta(days=2),
            payment_method="cash",
        )
        Expense.objects.create(
            owner=self.user,
            category=self.cat_travel,
            amount=Decimal("500.25"),
            date=today - timedelta(days=1),
            payment_method="credit_card",
        )
        Expense.objects.create(
            owner=self.user,
            category=self.cat_bills,
            amount=Decimal("1000.00"),
            date=today - timedelta(days=3),
            payment_method="net_banking",
            is_deleted=True,  # Soft deleted
        )
        Expense.objects.create(
            owner=self.user,
            category=self.cat_bills,
            amount=Decimal("250.00"),
            date=today - timedelta(days=50),  # Prior period
            payment_method="upi",
        )

        # Other user's expense (MUST NEVER APPEAR)
        Expense.objects.create(
            owner=self.other_user,
            category=self.cat_food,
            amount=Decimal("9999.00"),
            date=today - timedelta(days=2),
            payment_method="upi",
        )

        self.start_date = (today - timedelta(days=10)).isoformat()
        self.end_date = today.isoformat()

    def test_summary_returns_correct_aggregates(self):
        url = f"/api/v1/analytics/summary/?start_date={self.start_date}&end_date={self.end_date}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # 200.50 + 100.00 + 500.25 = 800.75
        self.assertEqual(data["total_spend"], "800.75")
        self.assertEqual(data["transaction_count"], 3)
        # 800.75 / 3 = 266.916... -> 266.92
        self.assertEqual(data["average_expense"], "266.92")

        # Top category should be Travel (500.25 > 300.50)
        self.assertIsNotNone(data["top_category"])
        self.assertEqual(data["top_category"]["name"], "Travel")
        self.assertEqual(data["top_category"]["total_amount"], "500.25")

    def test_summary_empty_state_returns_zeroes(self):
        # Empty range in future
        future_start = (date.today() + timedelta(days=10)).isoformat()
        future_end = (date.today() + timedelta(days=20)).isoformat()

        url = f"/api/v1/analytics/summary/?start_date={future_start}&end_date={future_end}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["total_spend"], "0.00")
        self.assertEqual(data["transaction_count"], 0)
        self.assertEqual(data["average_expense"], "0.00")
        self.assertIsNone(data["top_category"])

    def test_by_category_breakdown_and_percentages(self):
        url = f"/api/v1/analytics/by-category/?start_date={self.start_date}&end_date={self.end_date}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["total_spend"], "800.75")
        categories = data["categories"]
        self.assertEqual(len(categories), 2)

        # Order by total amount desc: Travel (500.25), Food & Dining (300.50)
        first = categories[0]
        self.assertEqual(first["category_name"], "Travel")
        self.assertEqual(first["total_amount"], "500.25")
        self.assertEqual(first["transaction_count"], 1)
        # 500.25 / 800.75 * 100 = 62.47
        self.assertEqual(first["percentage"], 62.47)

        second = categories[1]
        self.assertEqual(second["category_name"], "Food & Dining")
        self.assertEqual(second["total_amount"], "300.50")
        self.assertEqual(second["transaction_count"], 2)
        # 300.50 / 800.75 * 100 = 37.53
        self.assertEqual(second["percentage"], 37.53)

        # Sum of percentages equals 100%
        self.assertAlmostEqual(first["percentage"] + second["percentage"], 100.0, places=1)

        # Verify chart adapter output (R4)
        self.assertIn("chart", data)
        self.assertEqual(data["chart"]["type"], "bar")
        self.assertEqual(data["chart"]["labels"], ["Travel", "Food & Dining"])
        self.assertEqual(data["chart"]["values"], [500.25, 300.5])

    def test_soft_deleted_and_other_user_expenses_excluded(self):
        url = f"/api/v1/analytics/summary/?start_date={self.start_date}&end_date={self.end_date}"
        response = self.client.get(url)
        data = response.json()

        # The 1000.00 soft deleted and 9999.00 other user must not be present
        self.assertNotEqual(data["total_spend"], "1800.75")
        self.assertNotEqual(data["total_spend"], "10799.75")
        self.assertEqual(data["total_spend"], "800.75")

    def test_date_validation_start_after_end_returns_400(self):
        today = date.today()
        url = f"/api/v1/analytics/summary/?start_date={today.isoformat()}&end_date={(today - timedelta(days=5)).isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_date_validation_exceeds_365_days_returns_400(self):
        today = date.today()
        start = (today - timedelta(days=400)).isoformat()
        end = today.isoformat()
        url = f"/api/v1/analytics/summary/?start_date={start}&end_date={end}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_invalid_date_format_returns_400(self):
        url = "/api/v1/analytics/summary/?start_date=2026-13-45"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_unauthenticated_access_returns_401(self):
        anonymous_client = APIClient()
        response = anonymous_client.get("/api/v1/analytics/summary/")
        self.assertEqual(response.status_code, 401)
