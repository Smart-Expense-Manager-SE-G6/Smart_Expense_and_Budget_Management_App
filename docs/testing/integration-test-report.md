# Integration Test Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) at `69426f5`, 18 Nov 2026. Logs from that run are in [`reports/test-logs/`](reports/test-logs/).
**Objective:** check that the parts of the system work together: frontend and API, API and database, authentication and protected endpoints, and the modules that depend on each other.

## Results

| ID | Interaction | Expected | Actual | Status |
|---|---|---|---|---|
| INT-01 | Frontend ↔ backend | UI calls return the expected API responses | 14 Selenium journeys through React → Django → PostgreSQL passed | PASS |
| INT-02 | Backend ↔ database | CRUD persists and reads safely | 366 backend tests on PostgreSQL 16 (36 database test classes); `makemigrations --check` found no missing migrations | PASS |
| INT-03 | Authentication ↔ protected APIs | Unauthenticated access refused; session accepted | `accounts/test_auth_api.py` (30 tests) and Postman "Profile after logout is refused" passed | PASS |
| INT-04 | Expenses ↔ categories and budgets | Relationships and utilisation work | `test_budget_utilization_calculates_spending`, `test_category_budget_utilization_counts_only_matching_category`, `test_cannot_file_an_expense_under_someone_elses_category` passed | PASS |
| INT-05 | Expenses ↔ budget alerts | Crossing a threshold creates an alert | `test_alert_created_at_80_percent`, `test_100_percent_creates_both_threshold_alerts`, `test_lowering_a_budget_limit_raises_alert`; browser `test_TC_Alert_01_80_percent_alert` passed | PASS |
| INT-06 | Recurring rules ↔ expenses ↔ scheduler | Rules create expenses once when due | `expenses/test_recurring.py` (25 tests, including the scheduled command and catch-up after missed periods) passed | PASS |
| INT-07 | CSV import ↔ expenses and categories | Valid rows saved, invalid rows reported | `expenses/test_import.py` (21 tests); browser `test_TC_Import_01_csv_preview_and_import` passed | PASS |
| INT-08 | Reports ↔ analytics ↔ exports | PDF and Excel reflect the data | `analytics/tests.py` report and export tests; browser `test_TC_Report_01_export_pdf_and_excel` downloaded both files | PASS |
| INT-09 | Every change ↔ audit log | Audit entry written in the same transaction | `audit/tests.py` (10 tests, including the transaction test) and `audit/test_api.py` (13) passed | PASS |
| INT-10 | Production services together | gunicorn, Caddy, PostgreSQL, scheduler and backups work as one stack | Deployed in CI; smoke test 16 / 16; restore rehearsal: all 19 tables match | PASS |

## Summary

Executed: 10. Passed: 10. Failed: 0. Not run: 0. Logs: [`backend-django-test.log`](reports/test-logs/backend-django-test.log),
[`newman.log`](reports/test-logs/newman.log), [`selenium-e2e.log`](reports/test-logs/selenium-e2e.log),
[`deployment-smoke-test.log`](reports/test-logs/deployment-smoke-test.log).

## Commands

```bash
cd backend && python manage.py test                     # needs PostgreSQL
npx newman run tests/postman_collection.json --env-var base_url=http://127.0.0.1:8000
pytest tests/e2e -v                                     # needs the Docker stack
```

## Note on the first version of this report

The first version (commit 39b92d1 and the commits after it) recorded these suites as NOT RUN. They could not be run on that
machine: Python was not installed and the Docker daemon was not running. They were then run in GitHub Actions, on the
same environment the project's CI uses every day (Ubuntu, Python 3.12, PostgreSQL 16, Docker, headless Chrome). This
report records those results.
