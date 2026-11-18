# Unit Test Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) on `main` at `69426f5`, 18 Nov 2026
**Result:** **366 backend tests and 2 frontend tests run, all passed, 0 failed, 0 errors** (CI log: "Ran 366 tests ... OK")

## What is tested and how

The backend tests use Django's test framework. Every test runs on a fresh **PostgreSQL 16** database, the same engine
as production, so model constraints, transactions and row locking are tested for real. Tests are independent: each
class creates its own users and data, and nothing depends on the order the tests run in.

| Kind | Base class | Classes | What it isolates |
|:--|:--|--:|:--|
| Pure unit tests | `SimpleTestCase` | 8 | One class with no database: email and chart adapters, log formatting, error-rate metrics, job status files |
| Unit and API-level tests | `TestCase` | 36 | One model, service or endpoint with the database; each test is rolled back afterwards |
| Transaction tests | `TransactionTestCase` | 1 | An audit entry is refused when there is no surrounding database transaction |

External services are replaced at their adapter boundary (email, charting), as SASD C3 requires, so no unit test
sends mail or calls the network. Where a rule depends on the date (recurring rules, rollover, session expiry), the
clock is fixed with mocks.

## Results by module

| Module | Tests | Passed | Failed | Responsibility |
|:--|--:|--:|--:|:--|
| `accounts` | 53 | 53 | 0 | Users, registration, login, profile, account settings (FR1, FR2) |
| `alerts` | 24 | 24 | 0 | Threshold and anomaly alerts, email delivery (FR16-FR18) |
| `analytics` | 28 | 28 | 0 | Summary, forecast, comparison, reports and exports (FR13-FR15, FR19, FR20) |
| `audit` | 23 | 23 | 0 | Append-only audit trail and its API (FR21) |
| `budgets` | 49 | 49 | 0 | Budgets, utilisation, rollover, shared budgets (FR3, FR10-FR12) |
| `core` | 56 | 56 | 0 | API layer: auth, error envelope, request IDs, security headers, adapters |
| `expenses` | 116 | 116 | 0 | Expenses, receipts, categories, suggestions, CSV import, recurring rules (FR4-FR9) |
| `monitoring` | 17 | 17 | 0 | Logging, error-rate alerts, monitoring dashboard (NFR9, NFR12) |
| **Total** | **366** | **366** | **0** | |

## Results by test file

| Test file | Tests | Requirements / test cases | Test classes |
|:--|--:|:--|:--|
| [`accounts/test_account_settings.py`](../../backend/accounts/test_account_settings.py) | 20 | FR2, NFR14 (TC-Account-01) | PasswordChangeTests, DataExportTests, AccountDeletionTests, EmailAlertConsentTests |
| [`accounts/test_auth_api.py`](../../backend/accounts/test_auth_api.py) | 30 | FR1, FR2, NFR5 (TC-Auth-01 to 03) | TCAuth01RegisterTests, TCAuth02LoginLogoutTests, LoginFailureGuardTests, CsrfTests, ProfileTests |
| [`accounts/tests.py`](../../backend/accounts/tests.py) | 3 | FR1 user model | UserModelTests |
| [`alerts/tests.py`](../../backend/alerts/tests.py) | 24 | FR16, FR17, FR18 (TC-Alert-01 to 03) | BudgetThresholdAlertTests, SpendingAnomalyAlertTests, AlertEmailAdapterTests, AlertApiTests |
| [`analytics/test_performance.py`](../../backend/analytics/test_performance.py) | 2 | NFR1, NFR2 (TC-Perf-01, 02) | AnalyticsPerformanceTests |
| [`analytics/tests.py`](../../backend/analytics/tests.py) | 26 | FR13, FR14, FR15, FR19, FR20 (TC-Analytics, TC-Report) | AnalyticsAPITests, PredictiveInsightsTests, SpendingComparisonTests, CustomReportTests |
| [`audit/test_api.py`](../../backend/audit/test_api.py) | 13 | FR21 (TC-Audit-01) | AuditTrailApiTests |
| [`audit/tests.py`](../../backend/audit/tests.py) | 10 | FR21 audit writing, append-only | AuditedContextManagerTests, OutsideTransactionTests, AppendOnlyTests, AuditedViewSetMixinTests |
| [`budgets/test_shared.py`](../../backend/budgets/test_shared.py) | 26 | FR3 (TC-Shared-01) | TCShared01MembershipTests, SharedBudgetValidationTests, SharedBudgetSpendingTests |
| [`budgets/tests.py`](../../backend/budgets/tests.py) | 23 | FR10, FR11, FR12 (TC-Bud-01 to 03) | BudgetAPITests, BudgetRolloverTests |
| [`core/test_adapters.py`](../../backend/core/test_adapters.py) | 5 | SASD C3 adapters (email, charts) | StubEmailAdapterTests, DjangoEmailAdapterTests, StubChartingAdapterTests, ChartingServiceTests |
| [`core/test_api_layer.py`](../../backend/core/test_api_layer.py) | 13 | SASD 4.4 error envelope, NFR12 request IDs | ErrorEnvelopeTests, UnknownApiUrlTests, RequestIdTests |
| [`core/test_openapi.py`](../../backend/core/test_openapi.py) | 1 | API documentation (OpenAPI schema) | OpenApiSchemaTests |
| [`core/test_security.py`](../../backend/core/test_security.py) | 32 | NFR4, NFR5, NFR6, NFR14 (TC-Sec-01, 03, 04) | PasswordAndSessionTests, OtherUsersDataTests, FuzzingTests, AuthAndRolePenetrationTests |
| [`core/tests.py`](../../backend/core/tests.py) | 5 | NFR9 health check, session auth | HealthCheckTests, SessionAuthenticationTests |
| [`expenses/test_import.py`](../../backend/expenses/test_import.py) | 21 | FR7 (TC-Import-01) | CsvImportTests |
| [`expenses/test_recurring.py`](../../backend/expenses/test_recurring.py) | 25 | FR6 (TC-Exp-04) | NextOccurrenceTests, MaterializeCommandTests, RecurringRuleApiTests |
| [`expenses/test_seed.py`](../../backend/expenses/test_seed.py) | 6 | NFR1 test data (10,000 transactions) | SeedDataCommandTests, SeedSyntheticDataCommandTests |
| [`expenses/tests.py`](../../backend/expenses/tests.py) | 64 | FR4, FR5, FR8, FR9 (TC-Exp, TC-Cat) | ExpenseApiTests, CategorySuggestionTests, CategoryApiTests |
| [`monitoring/tests.py`](../../backend/monitoring/tests.py) | 17 | NFR9, NFR12 (TC-Log-01) | JsonLoggingTests, ErrorMonitoringTests, JobStatusFileTests, EmailFailureTrackingTests, MonitoringDashboardTests |

## Coverage reached by these tests

Line coverage is **94.6%** (2,464 of 2,605 statements), branch coverage is
**85.8%** (496 of 578 branches) and the combined figure is **93.0%**. Details are
in [`code-coverage-report.md`](code-coverage-report.md) and [`branch-coverage-report.md`](branch-coverage-report.md).

## Frontend

| Test file | Tests | Passed | What it checks |
|:--|--:|--:|:--|
| [`frontend/tests/monitoring.test.js`](../../frontend/tests/monitoring.test.js) | 2 | 2 | Monitoring statuses map to the right label and colour; a missing or unknown status stays "unknown" |

These run with Node's built-in test runner (`npm test`), as the "Frontend unit tests" step of the CI frontend job.
ESLint and a production build also check the frontend on every pull request, and the 14 Selenium journeys in the
[System Validation Report](system-validation-report.md) test its behaviour in a real browser.

## Logs and artifacts

- [`reports/test-logs/backend-django-test.log`](reports/test-logs/backend-django-test.log): the backend test run ("Ran 366 tests ... OK")
- [`reports/test-logs/frontend-test.log`](reports/test-logs/frontend-test.log): the frontend unit tests (2 pass, 0 fail)
- [`reports/coverage/index.html`](reports/coverage/index.html): the coverage report from the same run

## How to reproduce

```bash
cd backend
pip install -r requirements.txt coverage==7.6.10
coverage run manage.py test          # needs PostgreSQL; settings come from .env
coverage report
```

In CI this is the "Backend tests and coverage" job in `.github/workflows/ci.yml`, which runs on every pull request and
every push to `main`.

