# Test Summary Report

**Release:** Smart Expense and Budget Management Application 1.0  
**Report date:** 2026-11-18  
**Prepared for:** Product owner Sudeepa Roy Dey  
**Prepared by:** QA lead Shashank / Team 6  
**Scope:** STP sections 5, 8, 13 and 14; issue #84

## Evidence this report is based on

| Source | Run | Commit | Date |
|:--|:--|:--|:--|
| CI (backend, frontend, Postman, Selenium, staging deploy) | [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) | `69426f5` on `main` | 2026-11-18 |
| Backup and restore workflow | [#44234445241](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445241) | `69426f5` on `main` | 2026-11-18 |
| Accessibility and responsive audit | [`accessibility-audit.md`](accessibility-audit.md) | PR #105 | 2026-11-18 |
| Security checks | [`../security-report.md`](security-report.md) | PR #92 | 2026-11-16 |

Cancelled workflow runs are not counted. Every number below comes from these runs.

## Executive result

38 of the 39 planned test cases were executed and all 38 passed. 21 defects were found during Sprints 2 and 3 and
all of them are fixed on `main`. One test case has no recorded run (TC-Arch-01, an architecture review), and product-owner UAT has not happened yet, so **final sign-off is pending** those items.

## STP section 14 metrics

| Metric | Definition | Result | Calculation |
|:--|:--|:--|:--|
| Test cases executed | executed ÷ planned × 100 | **97.4%** | 38 ÷ 39 × 100 ([`test-cases.md`](test-cases.md)) |
| Test cases passed | passed ÷ executed × 100 | **100%** | 38 ÷ 38 × 100 |
| Test cases failed | failed ÷ executed × 100 | **0%** | 0 ÷ 38 × 100 |
| Defect density | defects ÷ executed cases × 100 | **55.3 per 100 cases** | 21 ÷ 38 × 100 ([`defect-log.md`](defect-log.md)) |
| Defect aging | days from found to fix merged, averaged | **0.24 days** (max 1 day) | 5 defect-days ÷ 21 defects |
| Requirement coverage | requirements with ≥1 executed test ÷ requirements × 100 | **97.2%** | 35 ÷ 36 (FR1–FR22, NFR1–NFR14); not yet covered: NFR11 |

Defect density counts every confirmed defect, including the three in the Selenium test setup (DEF-15 to DEF-17).
Without those, it is 18 ÷ 38 × 100 = 47.4 per 100 cases.

## Test-level roll-up

| Suite | Executed | Passed | Failed | Evidence |
|:--|--:|--:|--:|:--|
| Backend unit, integration and API tests (Django) | 366 tests | 366 | 0 | CI #44234445329, backend job |
| Backend coverage | 2,464 / 2,605 lines (**94.6%**); 496 / 578 branches (**85.8%**); combined **93.0%** | | | CI coverage artifact; gate fails under 80% |
| Frontend lint and production build | 2 checks | 2 | 0 | CI frontend job |
| Postman / Newman API | 9 requests, 17 assertions | 17 | 0 | CI API job |
| Selenium end-to-end journeys | 14 tests | 14 | 0 | CI end-to-end job |
| Performance (NFR1, NFR2) | 2 timed tests on 10,000 expenses | 2 | 0 | `analytics/test_performance.py`, in the backend job |
| Staging deployment smoke test (HTTPS) | 16 checks | 16 | 0 | CI deploy job |
| Restore rehearsal (TC-Backup-01) | 19 tables | 19 match | 0 | CI deploy job and backup run #44234445241 |
| Accessibility (axe-core, 3 widths) and keyboard | all pages; 5 keyboard checks | 0 violations; 5 | 0 | [`accessibility-audit.md`](accessibility-audit.md) |
| Security (STP 5.1) | 5 checks | 5 | 0 | [`../security-report.md`](security-report.md): OWASP ZAP 0 FAIL, pip-audit and npm audit 0 vulnerabilities |
| Scale test (NFR3) and backup retention (NFR10) | 2 tests on the production stack | 2 | 0 | [`scale-test.log`](reports/test-logs/scale-test.log), [`retention-test.log`](reports/test-logs/retention-test.log); both now run in CI |

## Detailed reports

- [Unit Test Report](unit-test-report.md)
- [System Validation Report](system-validation-report.md)
- [Code Coverage Report](code-coverage-report.md)
- [Branch Coverage Report](branch-coverage-report.md)

## Exit criteria

- [ ] 100% of planned test cases executed: 38/39; TC-Arch-01 has no run.
- [x] 0 critical defects open: none found; all 21 defects fixed.
- [ ] Product owner UAT completed and recorded in [`uat-record.md`](uat-record.md).
- [ ] All requirements have at least one executed test: 35/36; NFR11 outstanding.
- [x] Evidence tied to a commit SHA and workflow run URL: `69426f5`, runs listed above.

## Sign-off

| Role | Name | Decision | Date | Signature / link |
|:--|:--|:--|:--|:--|
| QA lead | Shashank A | Pending | — | — |
| Product owner | Sudeepa Roy Dey | Pending UAT | — | — |
