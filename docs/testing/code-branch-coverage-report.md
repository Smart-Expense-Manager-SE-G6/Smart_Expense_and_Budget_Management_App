# Code and Branch Coverage Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) at `69426f5`, 18 Nov 2026. Logs from that run are in [`reports/test-logs/`](reports/test-logs/).
**Objective:** measure backend statement and branch coverage with coverage.py.

## Result

| Measure | Covered | Total | % |
|---|--:|--:|--:|
| Statements (lines) | 2,464 | 2,605 | **94.6%** |
| Branches | 496 | 578 | **85.8%** |
| Combined | | | **93.0%** |

CI fails any build under 80% combined coverage (`backend/.coveragerc`, `fail_under = 80`).

## Detailed reports

- [Code Coverage Report](code-coverage-report.md): by module and by file, with the missed lines
- [Branch Coverage Report](branch-coverage-report.md): by module, every branch not taken, and why

## Artifacts

[`reports/coverage/coverage.json`](reports/coverage/coverage.json) (raw data) and
[`reports/coverage/index.html`](reports/coverage/index.html) (browsable HTML report) are the real output of this run.

## Frontend coverage

The frontend has 2 unit tests (`frontend/tests/monitoring.test.js`, Node's built-in test runner), which do not measure
coverage. The frontend's behaviour is covered by the 14 Selenium journeys instead
([System Test Report](system-test-report.md)).

## Commands

```bash
cd backend
coverage run manage.py test
coverage report
coverage json -o ../docs/testing/reports/coverage/coverage.json
coverage html -d ../docs/testing/reports/coverage
```

## Note on the first version of this report

The first version (commit 39b92d1 and the commits after it) recorded these suites as NOT RUN. They could not be run on that
machine: Python was not installed and the Docker daemon was not running. They were then run in GitHub Actions, on the
same environment the project's CI uses every day (Ubuntu, Python 3.12, PostgreSQL 16, Docker, headless Chrome). This
report records those results.
