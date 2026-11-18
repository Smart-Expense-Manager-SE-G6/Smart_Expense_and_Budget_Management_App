# Regression Test Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) at `69426f5`, 18 Nov 2026. Logs from that run are in [`reports/test-logs/`](reports/test-logs/).
**Objective:** show that existing features still work after every change.

## How regression testing is done

The full test suite runs automatically in GitHub Actions on **every pull request and every push to `main`**. A pull
request is merged only after all its checks pass (a team rule; enforcing it with branch protection needs an
organisation admin). Since CI was set up in Sprint 3, the workflow has run
**79 times**. This report records the final release run.

## Results

| ID | Area | Suite | Result | Status |
|---|---|---|---|---|
| REG-01 | Frontend | ESLint, 2 unit tests, production build | 2 / 2 tests; lint and build passed | PASS |
| REG-02 | Authentication and protected navigation | Backend auth and security tests; Selenium Auth 01-03; Postman | All passed | PASS |
| REG-03 | Expenses, categories, budgets | Backend tests; Selenium Exp, Cat, Bud journeys | All passed | PASS |
| REG-04 | Shared budgets, recurring rules | `budgets/test_shared.py`, `expenses/test_recurring.py`; Selenium Shared 01, Exp 04 | All passed | PASS |
| REG-05 | CSV import and exports | `expenses/test_import.py`, analytics export tests; Selenium Import 01, Report 01 | All passed | PASS |
| REG-06 | Navigation and responsive layout | Selenium journeys through every main page; accessibility audit at 360, 768 and 1280 px | All passed; 0 violations | PASS |
| REG-07 | Deployment, backup and restore | Production deploy, smoke test, restore rehearsal | 16 / 16; 19 / 19 tables | PASS |
| REG-08 | Dependencies | `pip-audit`, `npm audit` | 0 known vulnerabilities | PASS |

## Summary

Executed: 8 groups. Passed: 8. Failed: 0. Not run: 0. Totals in this run: 366 backend tests, 2 frontend tests,
14 Selenium journeys, 17 Postman assertions and 16 smoke checks, all passed.

Failures found by these runs were fixed in the same pull request before merging; the defects found during the
project are in the [defect log](defect-log.md).

## Note on the first version of this report

The first version (commit 39b92d1 and the commits after it) recorded these suites as NOT RUN. They could not be run on that
machine: Python was not installed and the Docker daemon was not running. They were then run in GitHub Actions, on the
same environment the project's CI uses every day (Ubuntu, Python 3.12, PostgreSQL 16, Docker, headless Chrome). This
report records those results.
