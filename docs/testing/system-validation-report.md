# System Validation Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44216307344](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307344) on `main` at `af9345f`, 18 Nov 2026; backup workflow run [#44216307590](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307590); accessibility audit of 18 Nov 2026
**Purpose:** confirm that the **whole system** does what the SRS requires: the frontend, API, database, scheduler,
backups and the production deployment working together. This is the STP's system and validation level, above the
unit tests in the [Unit Test Report](unit-test-report.md).

## Summary

| System-level suite | Environment | Result |
|:--|:--|:--|
| Selenium end-to-end journeys | Full Docker stack (React, Django, PostgreSQL) in headless Chrome | **14 / 14 passed** |
| Postman API collection (Newman) | Running API on PostgreSQL | **9 requests, 17 / 17 assertions passed** |
| Production deployment smoke test | Production stack: gunicorn, Caddy HTTPS, PostgreSQL, scheduler, backups | **16 / 16 checks passed** |
| Restore rehearsal (TC-Backup-01) | The deployed production stack | **Passed: all 19 tables match** |
| Performance (NFR1, NFR2) | 10,000 expenses on PostgreSQL | **2 / 2 passed** within the SRS limits |
| Dependency vulnerability audit | `pip-audit`, `npm audit` | **0 known vulnerabilities** |
| Accessibility and responsive audit | All pages at 360, 768, 1280 px | **0 axe violations, 0 overflow, 5 / 5 keyboard checks** |
| Security checks (STP 5.1) | API and deployed stack | **OWASP ZAP 0 FAIL**, see [`security-report.md`](security-report.md) |
| User acceptance (UAT) | Product owner | **Pending**: session not yet held, see [`uat-record.md`](uat-record.md) |

## End-to-end journeys (Selenium)

Each journey drives a real browser through the app, as a user would, and checks the result on screen or in the
downloaded file. Source: [`tests/e2e/test_journeys.py`](../../tests/e2e/test_journeys.py).

| Journey | Requirement | Validates | Result |
|:--|:--|:--|:--|
| `test_TC_Auth_01_register_lands_on_dashboard` | FR1 | Registering opens the dashboard with the user's name | Pass |
| `test_TC_Auth_02_login_logout_and_protected_redirect` | FR1, NFR5 | Sign out; protected pages redirect to sign-in; sign back in | Pass |
| `test_TC_Auth_03_profile_edit_persists` | FR2 | Profile changes survive a reload | Pass |
| `test_TC_Exp_01_add_edit_delete_expense` | FR4 | Add (with merchant and notes), edit and delete an expense | Pass |
| `test_TC_Exp_03_receipt_upload_and_link` | FR5 | A PDF receipt uploads and its link appears | Pass |
| `test_TC_Exp_04_recurring_rule_pause_resume` | FR6 | Create a monthly rule, then pause and resume it | Pass |
| `test_TC_Audit_01_expense_history` | FR21 | The History dialog shows the old and new amount | Pass |
| `test_TC_Import_01_csv_preview_and_import` | FR7 | The CSV preview reports the bad row; only the valid row is imported | Pass |
| `test_TC_Cat_01_custom_subcategory` | FR8 | Create a category and a nested subcategory | Pass |
| `test_TC_Cat_02_category_suggestion_accept` | FR9 | "Uber ride..." suggests Travel; accepting it sets the category | Pass |
| `test_TC_Bud_01_create_budget` | FR10 | Create a monthly budget | Pass |
| `test_TC_Alert_01_80_percent_alert` | FR16 | Spending 85% raises the 80% alert and the unread count | Pass |
| `test_TC_Shared_01_share_budget_with_member` | FR3 | Two browsers: the owner shares a budget; the member sees it read-only | Pass |
| `test_TC_Report_01_export_pdf_and_excel` | FR19, FR20 | The PDF and Excel reports download and are valid files | Pass |

## Production deployment smoke test

After CI deploys the real production stack (the same one used for the demo), `deploy/smoke_test.sh` checks it over
HTTPS:

| # | Check | Result |
|--:|:--|:--|
| 1 | HTTP redirects to HTTPS (308 https://localhost/) | Pass |
| 2 | HSTS header (max-age=31536000; includeSubDomains) | Pass |
| 3 | CSP on the app | Pass |
| 4 | no Server header from the API (got '') | Pass |
| 5 | API responses are not cacheable | Pass |
| 6 | app loads | Pass |
| 7 | deep link serves the app | Pass |
| 8 | health endpoint | Pass |
| 9 | admin static files | Pass |
| 10 | register | Pass |
| 11 | logout | Pass |
| 12 | login | Pass |
| 13 | session cookie is HttpOnly and Secure | Pass |
| 14 | add an expense | Pass |
| 15 | report | Pass |
| 16 | delete the test account | Pass |

## Validation against the requirements

| Requirement | System-level evidence | Result |
|:--|:--|:--|
| FR1-FR2 Accounts and profile | Selenium Auth 01-03; smoke test register, login, logout, account deletion | Pass |
| FR3 Shared budgets | Selenium Shared 01 (two users) | Pass |
| FR4-FR9 Expenses, receipts, recurring rules, import, categories, suggestions | Selenium Exp 01, 03, 04, Import 01, Cat 01, 02; smoke test "add an expense" | Pass |
| FR10-FR12 Budgets, utilisation, rollover | Selenium Bud 01 and Alert 01 (utilisation drives the alert); rollover by the scheduler service in the deployed stack, its logic unit-tested in `budgets/tests.py` | Pass |
| FR13-FR15 Analytics, forecast, comparison | Postman summary and breakdown requests; dashboard shown in every journey | Pass |
| FR16-FR18 Alerts | Selenium Alert 01 | Pass |
| FR19-FR20 Reports and exports | Selenium Report 01; smoke test "report" | Pass |
| FR21 Audit trail | Selenium Audit 01 | Pass |
| FR22 Backup and restore | Restore rehearsal on the deployed stack (19 tables) and the backup workflow | Pass |
| NFR1, NFR2 Performance | Timed tests on 10,000 expenses (`analytics/test_performance.py`) | Pass |
| NFR3 Scalability | Stateless API with a shared session and rate-limit store; the two-replica run was not executed | Not executed |
| NFR4-NFR6, NFR14 Security and privacy | Smoke test HTTPS, HSTS, CSP, secure cookies; OWASP ZAP; dependency audits | Pass |
| NFR7, NFR8 Responsive and accessible | [Accessibility audit](accessibility-audit.md) | Pass |
| NFR9, NFR12 Uptime and logging | Smoke test health endpoint; `X-Request-ID` header checked by Postman | Pass |
| NFR10 Backups | Daily backup service in the deployed stack; restore rehearsal | Pass (retention rotation not exercised) |
| NFR11 Modular architecture | No recorded architecture review | Not executed |
| NFR13 Containerised deployment | Production stack built and deployed in CI | Pass |

**Validated:** 34 of the 36 requirements have passing system-level evidence (NFR10 only partly). **Not executed:**
NFR3 and NFR11. **Final acceptance** waits for the product owner's UAT session.

## How to reproduce

```bash
docker compose up -d --build && pytest tests/e2e -v           # Selenium journeys (see tests/e2e/README.md)
bash deploy/local-demo.sh && bash deploy/smoke_test.sh https://localhost --insecure
```

