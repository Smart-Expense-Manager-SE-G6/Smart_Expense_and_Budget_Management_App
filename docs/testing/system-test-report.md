# System Test Report

## Objective and scope
Assess end-to-end user workflows: registration/login, expense CRUD, receipt upload, category management, budget tracking/alerts, shared budgets, recurring expenses, CSV import, PDF/Excel export, session expiry/logout, and user isolation.

## Environment and tools

Node.js v24.14.1 was available. Python and Docker daemon were unavailable. The existing Selenium suite in `tests/e2e/` contains 14 journeys, including the listed workflows except separate session-expiry coverage.

## Test cases

| ID | Scenario | Expected | Actual | Status |
|---|---|---|---|---|
| ST-01 | Registration and login | User reaches protected app | Selenium suite could not start: Python unavailable | NOT RUN |
| ST-02 | Expense CRUD | Create, edit, delete succeeds | Not executed | NOT RUN |
| ST-03 | Receipt upload | Receipt link appears | Not executed | NOT RUN |
| ST-04 | Categories/subcategories | Category workflow succeeds | Not executed | NOT RUN |
| ST-05 | Budgets and alerts | Tracking and alert workflow succeeds | Not executed | NOT RUN |
| ST-06 | Shared budget | Member sees read-only shared budget | Not executed | NOT RUN |
| ST-07 | Recurring expenses | Pause/resume workflow succeeds | Not executed | NOT RUN |
| ST-08 | CSV import | Preview/import handles invalid row | Not executed | NOT RUN |
| ST-09 | PDF and Excel exports | Files download successfully | Not executed | NOT RUN |
| ST-10 | Session expiry/logout | Protected access is rejected after logout/expiry | No dedicated runnable evidence | NOT RUN |
| ST-11 | User data isolation | Users cannot see one another’s data | Not executed | NOT RUN |

## Exact command

```powershell
pytest tests/e2e -v --html=tests/e2e/artifacts/report.html --self-contained-html
```

This command was not runnable because Python is not installed. Docker-dependent setup was also unavailable because the Docker daemon was not running. No production system was targeted.

## Summary and limitations

Executed: 0. Passed: 0. Failed: 0. Not run: 11. The repository’s E2E README describes the scenarios, but those descriptions are not execution evidence for this run.
