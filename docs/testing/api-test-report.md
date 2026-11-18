# API Test Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) at `69426f5`, 18 Nov 2026. Logs from that run are in [`reports/test-logs/`](reports/test-logs/).
**Objective:** check the REST API from outside, as a client would, with the Postman collection run by Newman.

## Environment

The API (Django development server) on a fresh PostgreSQL 16 database, after `migrate`. Newman 6.2.1 runs
[`tests/postman_collection.json`](../../tests/postman_collection.json) against it.

## Results

| ID | Endpoint / scenario | Method, auth | Expected | Actual | Status |
|---|---|---|---|---|---|
| API-01 | `/api/v1/health/` | GET, public | 200, status ok, `X-Request-ID` header | 3 / 3 assertions passed | PASS |
| API-02 | `/api/v1/auth/csrf/` | GET, public | 204 and CSRF cookie | 2 / 2 passed | PASS |
| API-03 | `/api/v1/auth/register/` | POST, public | 201, or 400 if the account exists | 2 / 2 passed | PASS |
| API-04 | `/api/v1/auth/login/`, `/api/v1/me/` | POST, GET, session | 200, session cookie, matching profile | 4 / 4 passed | PASS |
| API-05 | `/api/v1/analytics/summary/`, `/by-category/` | GET, authenticated | 200 with summary fields, breakdown and chart | 4 / 4 passed | PASS |
| API-06 | `/api/v1/auth/logout/` | POST, authenticated | 200 or 204 | 1 / 1 passed | PASS |
| API-07 | `/api/v1/me/` after logout | GET, no session | 401, session invalidated | 1 / 1 passed | PASS |

## Summary

**9 requests, 17 / 17 assertions passed, 0 failed** ([`newman.log`](reports/test-logs/newman.log)).

The Postman collection is the external check. Every endpoint is also tested from inside, through Django's API test
client, by the 366 backend tests in the [Unit Test Report](unit-test-report.md). Those tests cover success, validation
errors, permissions and other users' data. The full list of endpoints is in the SASD v1.1, Table 8, and in the OpenAPI
description at `/api/v1/schema/`.

## Command

```bash
npx newman run tests/postman_collection.json --env-var base_url=http://127.0.0.1:8000
```

## Note on the first version of this report

The first version (commit 39b92d1 and the commits after it) recorded these suites as NOT RUN. They could not be run on that
machine: Python was not installed and the Docker daemon was not running. They were then run in GitHub Actions, on the
same environment the project's CI uses every day (Ubuntu, Python 3.12, PostgreSQL 16, Docker, headless Chrome). This
report records those results.
