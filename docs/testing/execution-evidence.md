# Test Execution Evidence Index

This index records where each test execution artifact belongs. CI-generated reports are linked by workflow run URL in the release PR; binary or generated reports are not committed unless the STP explicitly requires them.

| Evidence source | Command / workflow | Artifact to retain | Status |
|:--|:--|:--|:--|
| Backend unit/API | `cd backend; python manage.py test` | CI backend job URL, coverage summary | [#44216307344](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307344): 366/366 passed, coverage 92.5% |
| Frontend | `cd frontend; npm ci; npm run lint; npm run build` | CI frontend job URL | [#44216307344](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307344): lint and build passed |
| Postman/Newman | `newman run tests/postman_collection.json` | CI API job URL and Newman summary | [#44216307344](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307344): 17/17 assertions passed |
| Selenium | `pytest tests/e2e --html=...` | HTML report and failure screenshots | [#44216307344](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307344): 14/14 passed |
| Performance | `python manage.py test analytics.test_performance` (timed tests, 10,000 expenses) | CI backend job | NFR1 and NFR2 passed in #44216307344. No JMeter plan exists; TC-Perf-03 (NFR3) not executed |
| Security | backend security tests and `docs/testing/security-report.md` | CI job/report | Recorded in `docs/testing/security-report.md` (PR #92) |
| Backup/restore | `scripts/rehearse_restore.sh` | CI backup job URL and logs | [#44216307590](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307590): rehearsal passed, 19/19 tables match |
| UAT | [`uat-record.md`](uat-record.md) | Signed/dated acceptance record | Pending product-owner session |

## Run recording rule

For every executed source, record the workflow run URL, commit SHA, date/time (IST), runner/environment, test count, pass/fail count, and artifact URL in `test-summary.md`. A cancelled workflow is not a test result and must not be counted as executed or passed.

## Recorded run links

- [CI run #44216307344](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307344) on `main` at `af9345f`, 18 Nov 2026: backend, frontend, Newman, Selenium, staging deploy and smoke test, restore rehearsal.
- [Backup run #44216307590](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307590) on `main` at `af9345f`: backup and restore rehearsal.
- Accessibility audit, 18 Nov 2026: [`accessibility-audit.md`](accessibility-audit.md).
