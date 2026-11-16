"""
Security tests for the STP section 5.1 checks (S3-15, NFR4-NFR6, NFR14, SRS 6.5).

TC-Sec-01  Password hashing and session expiry
TC-Sec-02  Data privacy: no access to another user's records (every resource)
TC-Sec-03  Fuzzing of input fields (expense amount, text fields, CSV import, query parameters)
TC-Sec-04  Penetration tests of authentication and role-based access
"""

import random
import string
from calendar import monthrange
from datetime import date, timedelta

from django.contrib.sessions.models import Session
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from alerts.models import Alert
from audit.models import AuditLog
from budgets.models import Budget, BudgetMember
from expenses.models import Category, Expense, RecurringRule

PW = "Tr1cky-Passw0rd!"
API = "/api/v1"

# Inputs an attacker or a careless client might send: SQL injection, XSS, path
# traversal, template and format strings, control characters, Unicode tricks,
# huge and malformed numbers.
NASTY_STRINGS = [
    "' OR '1'='1", "'; DROP TABLE expenses_expense; --", "\" OR \"\"=\"", "1; SELECT pg_sleep(5)--",
    "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "javascript:alert(1)", "\"><svg onload=alert(1)>",
    "../../../../etc/passwd", "..\\..\\windows\\win.ini", "{{7*7}}", "${7*7}", "%s%s%s%n", "{0.__class__}",
    "\x00", "line1\nline2\r\n", "\t", " ", "", "null", "None", "undefined", "NaN", "-0", "[]", "{}",
    "‮evil", "\U0001F4B8 money", "名前", "é" * 10, "A" * 300, "A" * 5000,
]
# Must be refused with 400.
NASTY_AMOUNTS = [
    "0", "-1", "-0.01", "0.001", "NaN", "Infinity", "-Infinity", "1,000", "99999999999999999999",
    "10000000000.00", "", " ", "abc", "1.2.3", "0x10", None, True, [], {},
]
# Unusual but valid numbers that Django REST Framework's DecimalField accepts.
# They must be stored as exactly the number they mean, never mangled.
LENIENT_AMOUNTS = {"1e3": "1000.00", "1E-2": "0.01", "+5": "5.00", "5 ": "5.00", "1_000": "1000.00",
                   "\uff11\uff10\uff10": "100.00", "\u0661\u0660\u0660": "100.00"}


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def month_bounds():
    today = date.today()
    return today.replace(day=1).isoformat(), today.replace(day=monthrange(today.year, today.month)[1]).isoformat()


class SecurityTestBase(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email="alice@example.com", password=PW)
        self.mallory = User.objects.create_user(email="mallory@example.com", password=PW)
        self.api = client_for(self.alice)
        self.attacker = client_for(self.mallory)
        self.food = Category.objects.get(name="Food", owner__isnull=True)


class PasswordAndSessionTests(SecurityTestBase):
    """TC-Sec-01: NFR4 (bcrypt) and NFR5 (session expiry)."""

    def test_passwords_are_stored_with_bcrypt(self):
        self.assertTrue(self.alice.password.startswith("bcrypt_sha256$"))
        self.assertNotIn(PW, self.alice.password)

    def test_password_never_returned_or_audited(self):
        response = APIClient().post(f"{API}/auth/register/", {"email": "new@example.com", "password": PW}, format="json")
        self.assertNotIn("password", response.json())
        for entry in AuditLog.objects.all():
            self.assertNotIn("password", (entry.before or {}) | (entry.after or {}))

    def test_session_expires_after_idle_timeout(self):
        browser = APIClient()
        self.assertTrue(browser.login(email="alice@example.com", password=PW))
        self.assertEqual(browser.get(f"{API}/me/").status_code, 200)
        Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))
        self.assertEqual(browser.get(f"{API}/me/").status_code, 401)

    def test_each_request_extends_the_idle_window(self):
        browser = APIClient()
        browser.login(email="alice@example.com", password=PW)
        Session.objects.update(expire_date=timezone.now() + timedelta(seconds=30))
        browser.get(f"{API}/me/")
        self.assertGreater(Session.objects.get().expire_date, timezone.now() + timedelta(minutes=25))

    def test_logout_destroys_the_server_side_session(self):
        browser = APIClient()
        browser.login(email="alice@example.com", password=PW)
        stolen_cookie = browser.cookies["sessionid"].value
        browser.post(f"{API}/auth/logout/")
        replay = APIClient()
        replay.cookies["sessionid"] = stolen_cookie
        self.assertEqual(replay.get(f"{API}/me/").status_code, 401)
        self.assertFalse(Session.objects.filter(session_key=stolen_cookie).exists())

    @override_settings(DEBUG=False, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True)
    def test_session_cookie_flags(self):
        browser = APIClient(enforce_csrf_checks=True)
        browser.get(f"{API}/auth/csrf/", secure=True)
        token = browser.cookies["csrftoken"].value
        response = browser.post(f"{API}/auth/login/", {"email": "alice@example.com", "password": PW},
                                format="json", HTTP_X_CSRFTOKEN=token, secure=True,
                                HTTP_ORIGIN="https://testserver", HTTP_REFERER="https://testserver/")
        cookie = response.cookies["sessionid"]
        self.assertTrue(cookie["httponly"])
        self.assertTrue(cookie["secure"])
        self.assertEqual(cookie["samesite"], "Lax")


class OtherUsersDataTests(SecurityTestBase):
    """TC-Sec-02: NFR14 and SRS 6.5. Every resource refuses another user's IDs with 404."""

    def setUp(self):
        super().setUp()
        start, end = month_bounds()
        self.category = Category.objects.create(name="Private", owner=self.alice)
        self.expense = Expense.objects.create(owner=self.alice, amount="50.00", date=date.today(), category=self.food)
        self.rule = RecurringRule.objects.create(owner=self.alice, amount="10.00", frequency="monthly", start_date=date(2030, 1, 1))
        self.budget = Budget.objects.create(user=self.alice, name="Food", category=self.food, limit_amount="100.00",
                                            period="monthly", start_date=start, end_date=end)
        self.member = BudgetMember.objects.create(budget=self.budget, user=User.objects.create_user(email="m@example.com", password=PW))
        self.alert = Alert.objects.create(user=self.alice, budget=self.budget, threshold_percentage=80, title="80%")
        self.audit_id = AuditLog.objects.create(actor=self.alice, action="create", entity_type="expenses.expense",
                                                entity_id=str(self.expense.pk), after={"owner_id": self.alice.pk}).pk

    def test_every_resource_is_hidden_from_other_users(self):
        e, c, r, b, m, a = self.expense.pk, self.category.pk, self.rule.pk, self.budget.pk, self.member.pk, self.alert.pk
        receipt = SimpleUploadedFile("r.pdf", b"%PDF-1.7 x", content_type="application/pdf")
        attempts = [
            ("get", f"/expenses/{e}/", None), ("patch", f"/expenses/{e}/", {"amount": "1.00"}), ("delete", f"/expenses/{e}/", None),
            ("get", f"/expenses/{e}/receipt/", None), ("delete", f"/expenses/{e}/receipt/", None),
            ("post", f"/expenses/{e}/receipt/", {"receipt": receipt}),
            ("get", f"/categories/{c}/", None), ("patch", f"/categories/{c}/", {"name": "x"}), ("delete", f"/categories/{c}/", None),
            ("get", f"/recurring-rules/{r}/", None), ("patch", f"/recurring-rules/{r}/", {"amount": "1.00"}),
            ("delete", f"/recurring-rules/{r}/", None),
            ("get", f"/budgets/{b}/", None), ("patch", f"/budgets/{b}/", {"limit_amount": "1.00"}), ("delete", f"/budgets/{b}/", None),
            ("get", f"/budgets/{b}/utilization/", None), ("get", f"/budgets/{b}/expenses/", None),
            ("get", f"/budgets/{b}/members/", None), ("post", f"/budgets/{b}/members/", {"email": "mallory@example.com"}),
            ("patch", f"/budgets/{b}/members/{m}/", {"role": "admin"}), ("delete", f"/budgets/{b}/members/{m}/", None),
            ("get", f"/alerts/{a}/", None), ("patch", f"/alerts/{a}/mark-read/", None),
            ("get", f"/audit/{self.audit_id}/", None),
        ]
        for method, path, body in attempts:
            fmt = "multipart" if body and "receipt" in body else "json"
            response = getattr(self.attacker, method)(API + path, body, format=fmt)
            with self.subTest(method=method, path=path):
                self.assertEqual(response.status_code, 404, response.content[:200])

        self.expense.refresh_from_db()
        self.assertEqual(str(self.expense.amount), "50.00")
        self.assertFalse(self.expense.is_deleted)
        self.assertTrue(Budget.objects.filter(pk=b).exists())
        self.assertFalse(BudgetMember.objects.filter(budget=self.budget, user=self.mallory).exists())

    def test_lists_never_contain_other_users_records(self):
        for path in ("/expenses/", "/categories/", "/recurring-rules/", "/budgets/", "/alerts/", "/audit/"):
            body = self.attacker.get(API + path).json()
            items = body.get("results", body) if isinstance(body, dict) else body
            with self.subTest(path=path):
                self.assertNotIn("alice@example.com", str(items))
                ids = {item.get("id") for item in items if isinstance(item, dict)}
                self.assertFalse(ids & {self.expense.pk, self.rule.pk, self.budget.pk, self.alert.pk, self.audit_id}
                                 if path != "/categories/" else ids & {self.category.pk})

    def test_cannot_file_an_expense_under_someone_elses_category(self):
        response = self.attacker.post(f"{API}/expenses/", {"amount": "5.00", "date": date.today().isoformat(),
                                                            "category": self.category.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["field"], "category")

    def test_analytics_and_reports_only_count_own_spending(self):
        start, end = month_bounds()
        report = self.attacker.get(f"{API}/analytics/reports/", {"start_date": start, "end_date": end}).json()
        self.assertEqual(report["summary"]["transaction_count"], 0)
        summary = self.attacker.get(f"{API}/analytics/summary/").json()
        self.assertNotIn("50.00", str(summary))


class FuzzingTests(SecurityTestBase):
    """TC-Sec-03: STP 5.1 fuzzing. No input may cause a server error or reach the database as code."""

    def assert_no_server_error(self, response, label):
        self.assertLess(response.status_code, 500, f"{label}: {response.status_code} {response.content[:200]!r}")
        if response.status_code >= 400:
            self.assertIn("error", response.json(), label)  # always the SASD 4.4 envelope

    def test_expense_amount(self):
        for amount in NASTY_AMOUNTS:
            response = self.api.post(f"{API}/expenses/", {"amount": amount, "date": date.today().isoformat()}, format="json")
            with self.subTest(amount=amount):
                self.assert_no_server_error(response, f"amount={amount!r}")
                self.assertEqual(response.status_code, 400)
        self.assertEqual(Expense.objects.count(), 0)

    def test_unusual_but_valid_amounts_keep_their_value(self):
        for raw, expected in LENIENT_AMOUNTS.items():
            response = self.api.post(f"{API}/expenses/", {"amount": raw, "date": date.today().isoformat()}, format="json")
            with self.subTest(amount=raw):
                self.assertEqual(response.status_code, 201)
                self.assertEqual(str(Expense.objects.get(pk=response.json()["id"]).amount), expected)

    def test_text_fields_are_stored_verbatim_or_rejected(self):
        for text in NASTY_STRINGS:
            body = {"amount": "1.00", "date": date.today().isoformat(), "description": text, "merchant": text, "notes": text}
            response = self.api.post(f"{API}/expenses/", body, format="json")
            with self.subTest(text=text[:40]):
                self.assert_no_server_error(response, f"text={text[:40]!r}")
                if response.status_code == 201:
                    stored = Expense.objects.get(pk=response.json()["id"])
                    self.assertEqual(stored.description, response.json()["description"])
                    self.assertIn(stored.description.strip(), text.replace("\x00", "").strip() or stored.description)
        # The SQL injection payloads were stored as plain text; the table is still there.
        self.assertTrue(Expense.objects.filter(description__contains="DROP TABLE").exists())

    def test_names_of_categories_and_budgets(self):
        start, end = month_bounds()
        for text in NASTY_STRINGS:
            with self.subTest(text=text[:40]):
                self.assert_no_server_error(self.api.post(f"{API}/categories/", {"name": text}, format="json"), "category")
                budget = {"name": text, "limit_amount": "100.00", "period": "monthly", "start_date": start, "end_date": end}
                self.assert_no_server_error(self.api.post(f"{API}/budgets/", budget, format="json"), "budget")

    def test_query_parameters(self):
        for value in NASTY_STRINGS + ["2026-13-45", "9999-12-31", "0000-00-00", "-1", "999999999"]:
            for path, params in (
                ("/expenses/", {"search": value}), ("/expenses/", {"date_from": value}), ("/expenses/", {"page": value}),
                ("/expenses/", {"page_size": value}), ("/expenses/", {"category": value}), ("/expenses/", {"ordering": value}),
                ("/categories/suggestions/", {"description": value}), ("/audit/", {"entity": value}),
                ("/audit/", {"entity_id": value}), ("/analytics/reports/", {"start_date": value, "end_date": value}),
                ("/analytics/comparison/", {"granularity": value}), ("/analytics/summary/", {"year": value, "month": value}),
            ):
                with self.subTest(path=path, params=str(params)[:60]):
                    self.assert_no_server_error(self.api.get(API + path, params), f"{path} {params}")

    def test_csv_import_cells(self):
        header = "date,amount,category,payment_mode,merchant,notes\n"

        def quote(cell):
            return '"' + cell.replace('"', '""') + '"'

        rows = [",".join(quote(c) for c in (date.today().isoformat(), "1.00", text, "upi", text, text)) for text in NASTY_STRINGS]
        rows += [",".join(quote(c) for c in (text, text, "", "", "", "")) for text in NASTY_STRINGS]
        body = (header + "\n".join(rows) + "\n").encode("utf-8")
        upload = SimpleUploadedFile("fuzz.csv", body, content_type="text/csv")
        response = self.api.post(f"{API}/expenses/import/", {"file": upload}, format="multipart")
        self.assert_no_server_error(response, "csv import")
        result = response.json()
        self.assertEqual(result["accepted_count"] + result["rejected_count"], result["total_rows"])

    def test_random_inputs(self):
        """Property-style fuzzing: 300 random strings from a fixed seed, so any failure is reproducible."""
        rng = random.Random(20261116)
        alphabet = string.printable + "éß漢字‮\U0001F4B8'\";<>{}%$\\"
        for i in range(300):
            text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120)))
            amount = rng.choice(["", text[:12], str(rng.uniform(-1e6, 1e12)), str(rng.randint(-5, 10**15))])
            response = self.api.post(f"{API}/expenses/", {"amount": amount, "date": date.today().isoformat(),
                                                           "description": text[:255]}, format="json")
            with self.subTest(i=i):
                self.assert_no_server_error(response, f"random #{i}")

    def test_upload_disguised_files(self):
        expense = Expense.objects.create(owner=self.alice, amount="5.00", date=date.today())
        for name, data, ctype in (
            ("evil.pdf", b"MZ\x90\x00 windows exe", "application/pdf"),
            ("evil.exe", b"MZ\x90\x00", "application/octet-stream"),
            ("evil.pdf.html", b"<script>alert(1)</script>", "text/html"),
            ("evil.png", b"<svg onload=alert(1)>", "image/png"),
        ):
            upload = SimpleUploadedFile(name, data, content_type=ctype)
            response = self.api.post(f"{API}/expenses/{expense.pk}/receipt/", {"receipt": upload}, format="multipart")
            with self.subTest(name=name):
                self.assertEqual(response.status_code, 400)
        expense.refresh_from_db()
        self.assertFalse(expense.receipt)

    def test_upload_path_traversal_stays_inside_receipts(self):
        expense = Expense.objects.create(owner=self.alice, amount="5.00", date=date.today())
        upload = SimpleUploadedFile("../../../evil.pdf", b"%PDF-1.7 x", content_type="application/pdf")
        self.api.post(f"{API}/expenses/{expense.pk}/receipt/", {"receipt": upload}, format="multipart")
        expense.refresh_from_db()
        if expense.receipt:  # the parser strips the path; the file gets a random name in receipts/<owner id>/
            self.assertTrue(expense.receipt.name.startswith(f"receipts/{self.alice.pk}/"))
            self.assertNotIn("..", expense.receipt.name)
            self.assertNotIn("evil", expense.receipt.name)


class AuthAndRolePenetrationTests(SecurityTestBase):
    """TC-Sec-04: attacks on authentication (NFR5, NFR6) and shared-budget roles (FR3, SRS 6.5)."""

    def test_unauthenticated_requests_are_refused(self):
        anonymous = APIClient()
        for path in ("/me/", "/expenses/", "/categories/", "/budgets/", "/alerts/", "/audit/", "/recurring-rules/",
                     "/analytics/summary/"):
            with self.subTest(path=path):
                self.assertEqual(anonymous.get(API + path).status_code, 401)

    def test_brute_force_login_is_locked_out(self):
        attacker = APIClient()
        codes = [attacker.post(f"{API}/auth/login/", {"email": "alice@example.com", "password": f"guess{i}"},
                               format="json").status_code for i in range(8)]
        self.assertEqual(codes[:5], [401] * 5)
        self.assertIn(429, codes[5:])
        # Even the right password is refused while locked out from this address.
        self.assertEqual(attacker.post(f"{API}/auth/login/", {"email": "alice@example.com", "password": PW},
                                       format="json").status_code, 429)

    def test_login_does_not_reveal_which_emails_exist(self):
        unknown = APIClient().post(f"{API}/auth/login/", {"email": "nobody@example.com", "password": "x"}, format="json")
        wrong = APIClient().post(f"{API}/auth/login/", {"email": "alice@example.com", "password": "x"}, format="json")
        self.assertEqual((unknown.status_code, unknown.json()["error"]["message"]),
                         (wrong.status_code, wrong.json()["error"]["message"]))

    def test_session_fixation_is_prevented(self):
        browser = APIClient()
        browser.get(f"{API}/auth/csrf/")
        browser.cookies["sessionid"] = "attacker-chosen-session-id"
        browser.post(f"{API}/auth/login/", {"email": "alice@example.com", "password": PW}, format="json")
        self.assertNotEqual(browser.cookies["sessionid"].value, "attacker-chosen-session-id")

    def test_csrf_is_enforced_for_signed_in_writes(self):
        browser = APIClient(enforce_csrf_checks=True)
        browser.get(f"{API}/auth/csrf/")
        token = browser.cookies["csrftoken"].value
        browser.post(f"{API}/auth/login/", {"email": "alice@example.com", "password": PW}, format="json", HTTP_X_CSRFTOKEN=token)
        body = {"amount": "5.00", "date": date.today().isoformat()}
        forged = browser.post(f"{API}/expenses/", body, format="json")
        self.assertEqual(forged.status_code, 403)
        self.assertEqual(forged.json()["error"]["code"], "csrf_failed")
        token = browser.cookies["csrftoken"].value
        self.assertEqual(browser.post(f"{API}/expenses/", body, format="json", HTTP_X_CSRFTOKEN=token).status_code, 201)

    def test_login_itself_is_csrf_protected(self):
        browser = APIClient(enforce_csrf_checks=True)
        response = browser.post(f"{API}/auth/login/", {"email": "alice@example.com", "password": PW}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_mass_assignment_is_ignored(self):
        self.api.patch(f"{API}/me/", {"email": "attacker@example.com", "is_staff": True, "is_superuser": True,
                                      "id": 999, "password": "x"}, format="json")
        self.alice.refresh_from_db()
        self.assertEqual((self.alice.email, self.alice.is_staff, self.alice.is_superuser),
                         ("alice@example.com", False, False))
        self.assertTrue(self.alice.check_password(PW))
        expense = self.api.post(f"{API}/expenses/", {"amount": "5.00", "date": date.today().isoformat(),
                                                      "owner": self.mallory.pk}, format="json").json()
        self.assertEqual(Expense.objects.get(pk=expense["id"]).owner, self.alice)

    def shared_budget(self):
        start, end = month_bounds()
        budget = Budget.objects.create(user=self.alice, name="Home", category=self.food, limit_amount="500.00",
                                       period="monthly", start_date=start, end_date=end)
        membership = BudgetMember.objects.create(budget=budget, user=self.mallory, role=BudgetMember.Role.MEMBER)
        return budget, membership

    def test_member_cannot_escalate_or_manage(self):
        budget, membership = self.shared_budget()
        base = f"{API}/budgets/{budget.pk}"
        attempts = [
            self.attacker.patch(f"{base}/members/{membership.pk}/", {"role": "admin"}, format="json"),
            self.attacker.post(f"{base}/members/", {"email": "friend@example.com"}, format="json"),
            self.attacker.patch(f"{base}/", {"limit_amount": "1.00", "user": self.mallory.pk}, format="json"),
            self.attacker.delete(f"{base}/"),
        ]
        self.assertEqual([r.status_code for r in attempts], [403] * 4)
        membership.refresh_from_db()
        budget.refresh_from_db()
        self.assertEqual((membership.role, budget.user, str(budget.limit_amount)), ("member", self.alice, "500.00"))

    def test_admin_cannot_take_ownership_or_delete(self):
        budget, membership = self.shared_budget()
        membership.role = BudgetMember.Role.ADMIN
        membership.save()
        base = f"{API}/budgets/{budget.pk}"
        self.attacker.patch(f"{base}/", {"user": self.mallory.pk, "name": "Mine now"}, format="json")
        self.assertEqual(self.attacker.delete(f"{base}/").status_code, 403)
        budget.refresh_from_db()
        self.assertEqual(budget.user, self.alice)

    def test_member_can_only_leave_not_remove_others(self):
        budget, membership = self.shared_budget()
        other = BudgetMember.objects.create(budget=budget, user=User.objects.create_user(email="o@example.com", password=PW))
        self.assertEqual(self.attacker.delete(f"{API}/budgets/{budget.pk}/members/{other.pk}/").status_code, 403)
        self.assertEqual(self.attacker.delete(f"{API}/budgets/{budget.pk}/members/{membership.pk}/").status_code, 204)

    def test_django_admin_requires_staff(self):
        browser = APIClient()
        browser.login(email="alice@example.com", password=PW)
        response = browser.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("Content-Security-Policy", response)  # the admin site keeps Django's defaults
        self.assertIn("/admin/login/", response["Location"])

    def test_api_responses_carry_security_headers(self):
        response = self.api.get(f"{API}/me/")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("default-src 'none'", response["Content-Security-Policy"])
        self.assertIn("camera=()", response["Permissions-Policy"])
        self.assertEqual(response["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_errors_and_unauthenticated_responses_carry_the_headers_too(self):
        for response in (APIClient().get(f"{API}/expenses/"), self.api.get(f"{API}/expenses/999999/"),
                         self.api.get(f"{API}/no-such-endpoint/"), APIClient().get("/"), APIClient().get("/robots.txt")):
            with self.subTest(status=response.status_code):
                self.assertEqual(response["Cache-Control"], "no-store")
                self.assertIn("default-src 'none'", response["Content-Security-Policy"])
