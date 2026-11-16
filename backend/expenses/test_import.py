"""TC-Import-01: CSV expense import with row-level errors (FR7, ADR-0003)."""

from decimal import Decimal
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from audit.models import AuditLog
from expenses.importers import MAX_ROWS
from expenses.models import Category, Expense

URL = "/api/v1/expenses/import/"
HEADER = "date,amount,category,payment_mode,merchant,notes\n"
SAMPLE = Path(__file__).parent / "fixtures" / "sample_expenses.csv"


class CsvImportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="importer@example.com", password="Tr1cky-Passw0rd!")
        self.other = User.objects.create_user(email="other@example.com", password="Tr1cky-Passw0rd!")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def upload(self, body, dry_run=False):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        file = SimpleUploadedFile("expenses.csv", data, content_type="text/csv")
        url = URL + ("?dry_run=true" if dry_run else "")
        return self.client.post(url, {"file": file}, format="multipart")

    def errors_for(self, response, row):
        return [(e["field"], e["error_code"]) for e in response.json()["errors"] if e["row_number"] == row]

    # --- whole file ---

    def test_sample_file_imports_every_row_with_audit(self):
        response = self.upload(SAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["accepted_count"], 2)
        self.assertEqual(response.json()["rejected_count"], 0)
        cafe = Expense.objects.get(owner=self.user, merchant="Cafe")
        self.assertEqual(cafe.amount, Decimal("125.50"))
        self.assertEqual(cafe.payment_method, "upi")
        self.assertEqual(cafe.category.name, "Food")
        self.assertEqual(cafe.notes, "Team lunch")
        self.assertEqual(Expense.objects.get(merchant="Metro").date.isoformat(), "2026-01-16")
        self.assertEqual(AuditLog.objects.filter(action=AuditLog.Action.CREATE, entity_type="expenses.expense").count(), 2)

    def test_dry_run_validates_without_saving(self):
        response = self.upload(SAMPLE.read_text(encoding="utf-8"), dry_run=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["accepted_count"], 2)
        self.assertTrue(response.json()["dry_run"])
        self.assertFalse(Expense.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_bad_rows_are_reported_and_good_rows_still_saved(self):
        body = HEADER + "2026-01-15,10.00,,,Good,\n,5,,,,\n2026-01-16,-3,,,,\n2026-01-17,20.00,,,Also good,\n"
        response = self.upload(body)
        self.assertEqual(response.json()["total_rows"], 4)
        self.assertEqual(response.json()["accepted_count"], 2)
        self.assertEqual(response.json()["rejected_count"], 2)
        self.assertEqual(self.errors_for(response, 3), [("date", "MISSING_FIELD")])
        self.assertEqual(self.errors_for(response, 4), [("amount", "INVALID_AMOUNT")])
        self.assertEqual(set(Expense.objects.values_list("merchant", flat=True)), {"Good", "Also good"})

    def test_error_carries_row_number_field_code_and_raw_value(self):
        response = self.upload(HEADER + "2026-02-30,12,,,,\n")
        error = response.json()["errors"][0]
        self.assertEqual(error["row_number"], 2)
        self.assertEqual(error["field"], "date")
        self.assertEqual(error["error_code"], "INVALID_DATE")
        self.assertEqual(error["raw_value"], "2026-02-30")
        self.assertTrue(error["message"])

    # --- amounts ---

    def test_invalid_amounts_are_rejected_per_row(self):
        bad = ["0", "-3", "1.234", "\"1,000\"", "1e2", "NaN", "Infinity", "abc", "10000000000.00"]
        body = HEADER + "".join(f"2026-01-15,{amount},,,,\n" for amount in bad)
        response = self.upload(body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rejected_count"], len(bad))
        self.assertEqual({e["error_code"] for e in response.json()["errors"]}, {"INVALID_AMOUNT"})
        self.assertFalse(Expense.objects.exists())

    def test_largest_amount_is_accepted(self):
        response = self.upload(HEADER + "2026-01-15,9999999999.99,,,,\n")
        self.assertEqual(response.json()["accepted_count"], 1)

    def test_missing_amount_reports_one_error(self):
        response = self.upload(HEADER + "2026-01-15,,,,,\n")
        self.assertEqual(self.errors_for(response, 2), [("amount", "MISSING_FIELD")])

    # --- other columns ---

    def test_payment_mode_must_be_known_and_defaults_to_other(self):
        body = HEADER + "2026-01-15,1,,bitcoin,,\n2026-01-16,2,,,Blank mode,\n2026-01-17,3,,Credit_Card,,\n"
        response = self.upload(body)
        self.assertEqual(self.errors_for(response, 2), [("payment_mode", "INVALID_PAYMENT_MODE")])
        self.assertEqual(Expense.objects.get(merchant="Blank mode").payment_method, "other")
        self.assertTrue(Expense.objects.filter(payment_method="credit_card").exists())

    def test_unknown_category_is_imported_uncategorised(self):
        response = self.upload(HEADER + "2026-01-15,5,No such category,,Mystery,\n")
        self.assertEqual(response.json()["accepted_count"], 1)
        self.assertIsNone(Expense.objects.get(merchant="Mystery").category)

    def test_another_users_category_is_never_used(self):
        Category.objects.create(name="Private", owner=self.other)
        self.upload(HEADER + "2026-01-15,5,Private,,Leak check,\n")
        self.assertIsNone(Expense.objects.get(merchant="Leak check").category)

    def test_own_category_beats_default_with_same_name(self):
        mine = Category.objects.create(name="Food", owner=self.user)
        self.upload(HEADER + "2026-01-15,5,food,,Mine,\n")
        self.assertEqual(Expense.objects.get(merchant="Mine").category, mine)

    def test_nul_character_rejects_only_that_row(self):
        response = self.upload(HEADER + "2026-01-15,5,,,Fine,\n" + '2026-01-16,6,,,"Bad\x00cell",\n')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.errors_for(response, 3), [("merchant", "INVALID_CHARACTER")])
        self.assertEqual(list(Expense.objects.values_list("merchant", flat=True)), ["Fine"])

    def test_long_text_fields_are_rejected(self):
        response = self.upload(HEADER + f"2026-01-15,5,,,{'m' * 256},\n")
        self.assertEqual(self.errors_for(response, 2), [("merchant", "FIELD_TOO_LONG")])

    def test_headers_are_case_insensitive_and_bom_is_ignored(self):
        body = "﻿Date, Amount ,Merchant\n15/01/2026,7.5,Bom shop\n"
        response = self.upload(body)
        self.assertEqual(response.json()["accepted_count"], 1)

    # --- file-level errors use the API error envelope ---

    def assert_file_error(self, response, code):
        self.assertEqual(response.status_code, 400)
        error = response.json()["error"]
        self.assertEqual(error["code"], code)
        self.assertEqual(error["field"], "file")
        self.assertGreater(len(error["message"]), 10)

    def test_missing_required_columns(self):
        self.assert_file_error(self.upload("foo,bar\n1,2\n"), "MISSING_COLUMNS")

    def test_empty_file(self):
        self.assert_file_error(self.upload(""), "INVALID_FILE")

    def test_non_utf8_file(self):
        self.assert_file_error(self.upload(b"\xff\xfe\x00garbage"), "INVALID_FILE")

    def test_too_many_rows(self):
        body = HEADER + "2026-01-15,1,,,,\n" * (MAX_ROWS + 1)
        self.assert_file_error(self.upload(body), "TOO_MANY_ROWS")
        self.assertFalse(Expense.objects.exists())

    def test_file_too_large(self):
        body = HEADER + "x" * (5 * 1024 * 1024)
        self.assert_file_error(self.upload(body), "FILE_TOO_LARGE")

    def test_missing_file(self):
        response = self.client.post(URL, {}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "file")

    def test_requires_login(self):
        self.assertEqual(APIClient().post(URL, {}, format="multipart").status_code, 401)
