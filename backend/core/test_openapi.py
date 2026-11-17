from django.test import TestCase


class OpenApiSchemaTests(TestCase):
    def test_schema_endpoint_returns_valid_openapi_document(self):
        response = self.client.get("/api/v1/schema/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["openapi"], "3.0.3")
        self.assertIn("/api/v1/expenses/", payload["paths"])
        self.assertIn("/api/v1/budgets/", payload["paths"])
