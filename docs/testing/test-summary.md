# Test Summary Report

**Release:** Smart Expense and Budget Management Application 1.0  
**Report date:** 2026-11-17  
**Prepared for:** Product owner Sudeepa Roy Dey  
**Prepared by:** QA lead Shashank / Team 6  
**Scope:** STP sections 5, 8, 13 and 14; issue #84

## Executive result

The report template and evidence index are complete. Final sign-off is **pending execution evidence** for the dependency suites and a product-owner UAT session. Cancelled GitHub Actions runs are excluded from the metrics.

### Recorded CI evidence update

Evidence is tied to merge commit `102c8959e00d07b37a20ff1ae9cf33a824b04973` for PR #109. The green [CI run #44036741974](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44036741974) recorded 362 backend tests with 362 passing, 2,434/2,588 lines (94.1%), 508/576 branches (88.2%), and 92% combined coverage; Newman recorded 9/9 requests and 17/17 assertions; frontend lint/build and the 16-check staging smoke test passed. The [backup run #44036741922](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44036741922) recorded TC-Backup-01 passing with all 19 table row counts matching. These figures supersede the placeholder suite values below.

Selenium and JMeter are **Not yet executed**. UAT remains **Pending session**. Case-level executed/pass percentages, defect density, and requirement coverage remain pending until their denominators can be supported by linked evidence; no estimates are claimed.

## STP section 14 metrics

| Metric | Definition | Result | Evidence / calculation |
|:--|:--|:--|:--|
| Test cases executed | executed planned cases ÷ planned cases × 100 | Pending run | Count from [`test-cases.md`](test-cases.md) and completed run artifacts |
| Test cases passed | passed executed cases ÷ executed cases × 100 | Pending run | CI/Selenium/Postman/JMeter/security result summaries |
| Test cases failed | failed executed cases ÷ executed cases × 100 | Pending run | Failed test names and linked defects |
| Defect density | confirmed defects ÷ executed test cases, reported per 100 cases | Pending run | [`defect-log.md`](defect-log.md) and final execution count |
| Defect aging | calendar days from defect opened to report/closure | See defect log | [`defect-log.md`](defect-log.md) |
| Requirement coverage | requirements with ≥1 executed test ÷ planned requirements × 100 | Pending run | RTM plus execution artifact links |

The issue acceptance calls out five metrics; pass and fail percentages are shown separately because they are independently required for sign-off.

## Test-level roll-up

| Suite | Planned | Executed | Passed | Failed | Cancelled / excluded | Run URL / artifact |
|:--|--:|--:|--:|--:|--:|:--|
| Backend unit/API | — | — | — | — | — | Add CI run URL |
| Frontend lint/build | 1 | — | — | — | — | Add CI run URL |
| Postman/Newman | — | — | — | — | — | Add CI run URL |
| Selenium E2E | — | — | — | — | Cancelled runs excluded | Add issue #74 run URL |
| JMeter performance | 3 | — | — | — | Dependency removed | No run claimed |
| Security | — | — | — | — | — | Add CI/report evidence |
| Backup/restore | 1 | — | — | — | — | Add CI run URL |

## Exit criteria

- [ ] 100% of planned test cases executed, with a linked artifact for each suite.
- [ ] 0 critical defects open; verify with the GitHub `bug` issue search at sign-off.
- [ ] Product owner UAT is completed and recorded in [`uat-record.md`](uat-record.md).
- [ ] All RTM requirements have at least one executed test case; see [`test-cases.md`](test-cases.md).
- [ ] Test evidence is tied to the release commit SHA and workflow run URL.

## Sign-off

| Role | Name | Decision | Date | Signature / link |
|:--|:--|:--|:--|:--|
| QA lead | Shashank A | Pending evidence | — | — |
| Product owner | Sudeepa Roy Dey | Pending UAT | — | — |
