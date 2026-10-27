
from django.test import SimpleTestCase, override_settings

from core.adapters.email import (
    DjangoEmailAdapter,
    StubEmailAdapter,
)
from core.adapters.charting import StubChartingAdapter
from core.charting_service import create_spending_chart


class StubEmailAdapterTests(SimpleTestCase):
    def test_stub_does_not_send_real_email(self):
        result = StubEmailAdapter().send_email(
            "user@example.com",
            "Budget alert",
            "Your budget reached 80%.",
        )

        self.assertTrue(result.success)
        self.assertIn("nothing was sent", result.message)


class DjangoEmailAdapterTests(SimpleTestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.com",
    )
    def test_django_adapter_sends_using_configured_backend(self):
        from django.core import mail

        result = DjangoEmailAdapter().send_email(
            "user@example.com",
            "Budget alert",
            "Your budget reached 80%.",
        )

        self.assertTrue(result.success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Budget alert")


class StubChartingAdapterTests(SimpleTestCase):
    def test_creates_chart_data(self):
        result = StubChartingAdapter().create_chart(
            "Monthly spending",
            ["January", "February"],
            [100.0, 150.0],
        )

        self.assertEqual(result["type"], "bar")
        self.assertEqual(result["labels"], ["January", "February"])
        self.assertEqual(result["values"], [100.0, 150.0])

    def test_rejects_mismatched_labels_and_values(self):
        with self.assertRaises(ValueError):
            StubChartingAdapter().create_chart(
                "Monthly spending",
                ["January", "February"],
                [100.0],
            )


class ChartingServiceTests(SimpleTestCase):
    def test_spending_chart_uses_charting_adapter(self):
        result = create_spending_chart(
            "Monthly spending",
            ["January", "February"],
            [100.0, 150.0],
        )

        self.assertEqual(result["title"], "Monthly spending")
        self.assertEqual(result["type"], "bar")
        self.assertEqual(result["values"], [100.0, 150.0])
