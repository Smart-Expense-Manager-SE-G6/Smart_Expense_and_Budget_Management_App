# Selenium end-to-end tests (S3-12)

Real browser journeys through the whole app (React frontend → Django API → PostgreSQL), written with
Selenium 4 and pytest as the Software Test Plan (section 6) specifies. Each test is named after its test
case ID in [`docs/requirements/rtm.md`](../../docs/requirements/rtm.md).

| Test | Requirement | What it does |
|:--|:--|:--|
| `test_TC_Auth_01_register_lands_on_dashboard` | FR1 | Registers and lands on the dashboard greeting |
| `test_TC_Auth_02_login_logout_and_protected_redirect` | FR1, NFR5 | Signs out; a protected page redirects to sign-in; signs back in |
| `test_TC_Auth_03_profile_edit_persists` | FR2 | Edits the profile and checks it after a reload |
| `test_TC_Exp_01_add_edit_delete_expense` | FR4 | Adds (with merchant and notes), edits and deletes an expense |
| `test_TC_Exp_03_receipt_upload_and_link` | FR5 | Adds an expense with a PDF receipt; the receipt link appears |
| `test_TC_Exp_04_recurring_rule_pause_resume` | FR6 | Creates a monthly rule, pauses and resumes it |
| `test_TC_Audit_01_expense_history` | FR21 | Edits an expense; the History dialog shows the old and new amount |
| `test_TC_Import_01_csv_preview_and_import` | FR7 | Previews a CSV with a bad row, imports only the valid row |
| `test_TC_Cat_01_custom_subcategory` | FR8 | Creates a category and a nested subcategory |
| `test_TC_Cat_02_category_suggestion_accept` | FR9 | Typing "Uber ride…" suggests Travel; accepting it sets the category |
| `test_TC_Bud_01_create_budget` | FR10 | Creates a monthly budget |
| `test_TC_Alert_01_80_percent_alert` | FR16 | Spends 85% of a budget; the alert and the unread count appear |
| `test_TC_Shared_01_share_budget_with_member` | FR3 | Two browsers: the owner shares a budget; the member sees it read-only |
| `test_TC_Report_01_export_pdf_and_excel` | FR19, FR20 | Downloads the PDF and Excel reports and checks both files |

## Run locally

```bash
cp .env.example .env               # first time only
# The suite registers a user per test. Raise the sign-up and login limits for the test stack
# (they are a security feature: 5 and 10 per minute per address by default):
#   REGISTER_RATE_LIMIT=1000/min
#   LOGIN_RATE_LIMIT=1000/min
docker compose up -d --build
python -m pip install -r tests/e2e/requirements.txt
pytest tests/e2e -v --html=tests/e2e/artifacts/report.html --self-contained-html
```

- Set `E2E_BASE_URL` if the app is not at `http://localhost:5174`, and `E2E_TIMEOUT` (seconds, default 20) on a slow machine.
- Chrome runs headless; Selenium Manager downloads a matching driver.
- A failing test saves a screenshot per browser to `tests/e2e/artifacts/` before its browser closes.
- Every test registers its own user, so tests are independent and can run in any order.
- Waits are explicit (`WebDriverWait`). The only sleep is the short poll for a finished file download,
  because the browser gives no page event for it.

## In CI

The `End-to-end tests (Selenium)` job in `.github/workflows/ci.yml` starts the same Docker stack with the
raised limits, runs the suite, and uploads the screenshots and HTML report when a test fails.

Local result on 17 Nov 2026: 14/14 passed, three runs in a row (about 100 s per run).
