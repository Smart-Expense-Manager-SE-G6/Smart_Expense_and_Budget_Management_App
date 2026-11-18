# System Test Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) at `69426f5`, 18 Nov 2026. Logs from that run are in [`reports/test-logs/`](reports/test-logs/).
**Objective:** check the complete user workflows end to end, through the real browser UI, on the full stack.

## Environment

The whole application in Docker (React frontend, Django API, PostgreSQL 16) started by `docker compose up -d --build`,
driven by Selenium 4 in headless Chrome ([`tests/e2e/`](../../tests/e2e/README.md)). The production stack (gunicorn,
Caddy HTTPS, PostgreSQL, scheduler, backups) is then deployed and smoke-tested in the same run.

## Test cases

| ID | Scenario | Expected | Actual | Status |
|---|---|---|---|---|
| ST-01 | Registration and login | User reaches the protected app | `test_TC_Auth_01_register_lands_on_dashboard` and `test_TC_Auth_02_login_logout_and_protected_redirect` passed | PASS |
| ST-02 | Expense CRUD | Create, edit, delete succeeds | `test_TC_Exp_01_add_edit_delete_expense` passed | PASS |
| ST-03 | Receipt upload | Receipt link appears | `test_TC_Exp_03_receipt_upload_and_link` passed | PASS |
| ST-04 | Categories and subcategories | Category workflow succeeds | `test_TC_Cat_01_custom_subcategory` and `test_TC_Cat_02_category_suggestion_accept` passed | PASS |
| ST-05 | Budgets and alerts | Tracking and alert workflow succeeds | `test_TC_Bud_01_create_budget` and `test_TC_Alert_01_80_percent_alert` passed | PASS |
| ST-06 | Shared budget | Member sees the shared budget read-only | `test_TC_Shared_01_share_budget_with_member` (two browsers) passed | PASS |
| ST-07 | Recurring expenses | Pause and resume succeed | `test_TC_Exp_04_recurring_rule_pause_resume` passed | PASS |
| ST-08 | CSV import | Preview reports the invalid row; only valid rows import | `test_TC_Import_01_csv_preview_and_import` passed | PASS |
| ST-09 | PDF and Excel exports | Files download successfully | `test_TC_Report_01_export_pdf_and_excel` passed; both files checked | PASS |
| ST-10 | Session expiry and logout | Protected access is refused after logout or expiry | Logout and the protected-page redirect: `test_TC_Auth_02_login_logout_and_protected_redirect` (browser). Idle expiry: `test_session_expires_after_idle_timeout` and `test_expired_session_returns_401` (API level, clock advanced 30 minutes) | PASS |
| ST-11 | User data isolation | Users cannot see one another's data | `test_every_resource_is_hidden_from_other_users` and `test_lists_never_contain_other_users_records` (API level, every resource type) | PASS |
| ST-12 | Audit history | Edits show before and after values | `test_TC_Audit_01_expense_history` passed | PASS |
| ST-13 | Production deployment | The deployed stack works over HTTPS | `deploy/smoke_test.sh`: 16 / 16 checks passed | PASS |

ST-10's idle expiry and ST-11 are checked through the API rather than the browser: waiting 30 real minutes in a browser
test, or signing in as every user type, would add nothing the API tests do not already show. Both run in the same CI
run.

## Summary

Executed: 13. Passed: 13. Failed: 0. Not run: 0. Selenium: **14 / 14 journeys passed**
([`selenium-e2e.log`](reports/test-logs/selenium-e2e.log)). Smoke test: **16 / 16 checks**
([`deployment-smoke-test.log`](reports/test-logs/deployment-smoke-test.log)). Each requirement's system-level evidence is in the
[System Validation Report](system-validation-report.md).

## Commands

```bash
docker compose up -d --build
pip install -r tests/e2e/requirements.txt
pytest tests/e2e -v --html=tests/e2e/artifacts/report.html --self-contained-html
bash deploy/local-demo.sh && bash deploy/smoke_test.sh https://localhost --insecure
```

The suite registers a new user per test, so the test stack raises the sign-up and login rate limits
(see `tests/e2e/README.md`).

## Note on the first version of this report

The first version (commit 39b92d1 and the commits after it) recorded these suites as NOT RUN. They could not be run on that
machine: Python was not installed and the Docker daemon was not running. They were then run in GitHub Actions, on the
same environment the project's CI uses every day (Ubuntu, Python 3.12, PostgreSQL 16, Docker, headless Chrome). This
report records those results.
