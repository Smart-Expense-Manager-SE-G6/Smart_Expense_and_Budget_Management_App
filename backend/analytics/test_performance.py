"""Performance verification tests for NFR1 (10,000 transactions <= 2-3s) and NFR2 (1-year report <= 5s)."""

from datetime import date, timedelta
from decimal import Decimal
import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from expenses.models import Category, Expense

User = get_user_model()


class AnalyticsPerformanceTests(TestCase):
    """Verify NFR1 and NFR2 response-time budgets with 10,000 transactions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="perf@example.com",
            password="PerfPassword123!",
        )
        categories = [
            Category.objects.create(name=f"PerfCat-{i}", owner=cls.user)
            for i in range(6)
        ]
        today = date.today()
        expenses = [
            Expense(
                owner=cls.user,
                category=categories[i % len(categories)],
                amount=Decimal("125.50"),
                date=today - timedelta(days=i % 365),
                payment_method="card",
                notes=f"Perf txn {i}",
            )
            for i in range(10000)
        ]
        Expense.objects.bulk_create(expenses, batch_size=1000)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _timed_get(self, url):
        start = time.perf_counter()
        response = self.client.get(url)
        elapsed = time.perf_counter() - start
        self.assertEqual(response.status_code, 200, msg=f"{url} returned {response.status_code}")
        return elapsed

    def test_nfr1_dashboard_analytics_under_2s_for_10k_transactions(self):
        """NFR1: Dashboard & analytics endpoints load within 2-3s for 10,000 transactions."""
        endpoints = [
            "/api/v1/analytics/summary/",
            "/api/v1/analytics/by-category/",
            "/api/v1/analytics/predictive-insights/",
            "/api/v1/analytics/comparison/?granularity=monthly&months=6",
        ]
        for url in endpoints:
            elapsed = self._timed_get(url)
            self.assertLessEqual(elapsed, 2.0, msg=f"NFR1 exceeded on {url}: {elapsed:.3f}s")

    def test_nfr2_one_year_report_and_exports_under_5s(self):
        """NFR2: 1-year report generation and PDF/Excel exports complete within 5s."""
        end = date.today()
        start = end - timedelta(days=364)
        qs = f"start_date={start.isoformat()}&end_date={end.isoformat()}"
        endpoints = [
            f"/api/v1/analytics/reports/?{qs}",
            f"/api/v1/analytics/reports/export/?{qs}&export_format=pdf",
            f"/api/v1/analytics/reports/export/?{qs}&export_format=xlsx",
        ]
        for url in endpoints:
            elapsed = self._timed_get(url)
            self.assertLessEqual(elapsed, 5.0, msg=f"NFR2 exceeded on {url}: {elapsed:.3f}s")
