# Test Execution Evidence Index

This index records where each test execution artifact belongs. CI-generated reports are linked by workflow run URL in the release PR; binary or generated reports are not committed unless the STP explicitly requires them.

| Evidence source | Command / workflow | Artifact to retain | Status |
|:--|:--|:--|:--|
| Backend unit/API | `cd backend; python manage.py test` | CI backend job URL, coverage summary | CI job defined; run URL to be added |
| Frontend | `cd frontend; npm ci; npm run lint; npm run build` | CI frontend job URL | CI job defined; run URL to be added |
| Postman/Newman | `newman run tests/postman_collection.json` | CI API job URL and Newman summary | CI job defined; run URL to be added |
| Selenium | `pytest tests/e2e --html=...` | HTML report and failure screenshots | Issue #74 dependency; run URL to be added |
| JMeter | `jmeter -n -t tests/performance/smart_expense.jmx ...` | `.jtl`, `statistics.json`, HTML report | Issue #75 was removed; no claim made |
| Security | backend security tests and `docs/security-report.md` | CI job/report | Existing repository evidence |
| Backup/restore | `scripts/rehearse_restore.sh` | CI backup job URL and logs | CI job defined; run URL to be added |
| UAT | [`uat-record.md`](uat-record.md) | Signed/dated acceptance record | Pending product-owner session |

## Run recording rule

For every executed source, record the workflow run URL, commit SHA, date/time (IST), runner/environment, test count, pass/fail count, and artifact URL in `test-summary.md`. A cancelled workflow is not a test result and must not be counted as executed or passed.

## Recorded run links

- [CI run #44036741974](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44036741974): backend, frontend, Newman API, and staging smoke.
- [Backup run #44036741922](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44036741922): backup and restore rehearsal.
