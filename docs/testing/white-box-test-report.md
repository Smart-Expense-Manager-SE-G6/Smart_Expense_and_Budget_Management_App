# White-Box Test Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) at `69426f5`, 18 Nov 2026. Logs from that run are in [`reports/test-logs/`](reports/test-logs/).
**Objective:** measure how much of the code's structure the tests exercise, from instrumentation rather than inspection.

## Measurement

coverage.py 7.6.10 with branch measurement on, over the whole backend test run (366 tests).

| Criterion | Covered | Total | % |
|---|--:|--:|--:|
| Statement (line) coverage | 2,464 | 2,605 | **94.6%** |
| Branch (decision) coverage | 496 | 578 | **85.8%** |
| Functions executed at least once | 199 | 216 | **92.1%** |
| Functions with every line executed | 156 | 216 | 72.2% |
| Combined statement + branch (coverage.py total) | | | 93.0% |

coverage.py does not measure condition coverage (each part of a compound condition) separately. Branch coverage is
the strongest criterion it reports, and it is the one the STP asks for.

## Decision paths and exception paths

Tests were written against the code's own decisions, on both sides, for example:

| Decision in the code | Both outcomes tested by |
|---|---|
| Is the requester the owner, an admin or a member? | `test_admin_can_change_settings_and_manage_members` / `test_member_cannot_change_settings` |
| Has the budget crossed 80%? 100%? | `test_alert_created_at_80_percent` / `test_no_alert_when_expense_is_within_limit` |
| Is there a previous period to roll over? Was it already rolled? | `test_rollover_creates_next_period` / `test_running_command_twice_does_not_duplicate_period` |
| Did the e-mail provider fail? | `test_failed_email_is_persisted_with_masked_recipient_and_request_id` |
| Did recording the failure itself fail? | `test_failure_tracking_error_does_not_replace_email_result` |
| Did metrics collection fail during a request? | `test_metrics_failure_does_not_change_application_response` |
| Is an audit entry being written outside a transaction? | `test_log_change_outside_transaction_is_refused` |

## Uncovered code

Every line and branch that the tests do not reach is listed, with the reason and the risk, in the
[Code Coverage Report](code-coverage-report.md) and the [Branch Coverage Report](branch-coverage-report.md). The
biggest gap is a model-level category cycle check that duplicates a tested API check.

## Artifacts

- [`reports/coverage/coverage.json`](reports/coverage/coverage.json): raw coverage data from this run
- [`reports/coverage/index.html`](reports/coverage/index.html): browsable HTML report, line by line
- [`reports/test-logs/backend-coverage.log`](reports/test-logs/backend-coverage.log): the `coverage report` table

## Commands

```bash
cd backend
coverage run manage.py test      # .coveragerc: branch = True
coverage report --show-missing
coverage html
```

## Note on the first version of this report

The first version (commit 39b92d1 and the commits after it) recorded these suites as NOT RUN. They could not be run on that
machine: Python was not installed and the Docker daemon was not running. They were then run in GitHub Actions, on the
same environment the project's CI uses every day (Ubuntu, Python 3.12, PostgreSQL 16, Docker, headless Chrome). This
report records those results.
