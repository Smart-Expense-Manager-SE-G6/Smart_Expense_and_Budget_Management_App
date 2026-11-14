from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

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

        # Global "Travel" and "Bills" are seeded by expenses migration 0002, so reuse them.
        self.cat_food = Category.objects.create(name="Food & Dining", is_active=True)
        self.cat_travel, _ = Category.objects.get_or_create(name="Travel", owner=None, defaults={"is_active": True})
        self.cat_bills, _ = Category.objects.get_or_create(name="Bills", owner=None, defaults={"is_active": True})

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

    def test_one_year_range_of_366_days_is_allowed(self):
        response = self.client.get("/api/v1/analytics/summary/?start_date=2025-10-31&end_date=2026-11-01")

        self.assertEqual(response.status_code, 200)

    def test_range_over_366_days_uses_adr_error_code(self):
        response = self.client.get("/api/v1/analytics/summary/?start_date=2025-10-31&end_date=2026-11-02")

        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertEqual((error["code"], error["field"]), ("DATE_RANGE_EXCEEDED", "date_range"))

    def test_default_range_uses_the_users_time_zone(self):
        # 20:00 UTC on 31 Oct is already 1 Nov in Asia/Kolkata (UTC+5:30).
        fixed_now = datetime(2026, 10, 31, 20, 0, tzinfo=dt_timezone.utc)
        with patch("django.utils.timezone.now", return_value=fixed_now):
            data = self.client.get("/api/v1/analytics/summary/").json()

        self.assertEqual((data["start_date"], data["end_date"]), ("2026-11-01", "2026-11-01"))


class CustomReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="report@example.com",
            password="Password123!",
        )
        self.client.force_authenticate(user=self.user)
        self.food, _ = Category.objects.get_or_create(name="Food", owner=self.user)

    def test_unauthenticated_returns_401(self):
        anon = APIClient()
        res = anon.get("/api/v1/analytics/reports/")
        self.assertEqual(res.status_code, 401)

    def test_custom_report_1_year_cap_enforced(self):
        res = self.client.get("/api/v1/analytics/reports/?start_date=2025-10-31&end_date=2026-11-02")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()["error"]["code"], "DATE_RANGE_EXCEEDED")

    def test_custom_report_includes_summary_categories_and_budget_vs_actual(self):
        from budgets.models import Budget

        Expense.objects.create(
            owner=self.user,
            category=self.food,
            amount=Decimal("400.00"),
            date=date(2026, 11, 5),
            payment_method="card",
        )
        Budget.objects.create(
            user=self.user,
            name="Food Nov",
            category=self.food,
            period="monthly",
            limit_amount=Decimal("1000.00"),
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 30),
        )

        res = self.client.get("/api/v1/analytics/reports/?start_date=2026-11-01&end_date=2026-11-30")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["summary"]["total_spend"], "400.00")
        self.assertEqual(res.data["summary"]["transaction_count"], 1)
        self.assertEqual(len(res.data["category_breakdown"]), 1)
        self.assertEqual(res.data["category_breakdown"][0]["category_name"], "Food")
        self.assertEqual(len(res.data["budget_vs_actual"]), 1)
        self.assertEqual(res.data["budget_vs_actual"][0]["actual_spent"], "400.00")
        self.assertEqual(res.data["budget_vs_actual"][0]["remaining_amount"], "600.00")
        self.assertEqual(res.data["budget_vs_actual"][0]["utilization_percentage"], 40.0)

    def test_export_pdf_report(self):
        Expense.objects.create(
            owner=self.user,
            category=self.food,
            amount=Decimal("250.00"),
            date=date(2026, 11, 5),
            payment_method="card",
        )
        res = self.client.get(
            "/api/v1/analytics/reports/export/?start_date=2026-11-01&end_date=2026-11-30&export_format=pdf"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))

    def test_export_excel_report(self):
        Expense.objects.create(
            owner=self.user,
            category=self.food,
            amount=Decimal("250.00"),
            date=date(2026, 11, 5),
            payment_method="card",
        )
        res = self.client.get(
            "/api/v1/analytics/reports/export/?start_date=2026-11-01&end_date=2026-11-30&export_format=xlsx"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(res.content.startswith(b"PK"))

    def test_export_invalid_format_returns_400(self):
        res = self.client.get(
            "/api/v1/analytics/reports/export/?start_date=2026-11-01&end_date=2026-11-30&export_format=csv"
        )
        self.assertEqual(res.status_code, 400)
