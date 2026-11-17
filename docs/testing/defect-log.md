# Defect Log

The team tracked defects in the pull request that fixed them, with a regression test where one applies, instead of a
separate `bug`-labelled issue for each (see `docs/deviations.md` T-01: GitHub replaces Jira). Every row below is
written up in the linked pull request; nothing is reconstructed from memory.

**Aging** is calendar days from the day the defect was found (the day its fixing pull request was opened, or the
audit/run that found it) to the day the fix was merged into `main`.

| ID | Found by | Defect | Severity | Found | Fixed (merged) | Aging | Fix |
|:--|:--|:--|:--|:--|:--|--:|:--|
| DEF-01 | Sprint 2 end-to-end check | Recurring expenses command crashed on PostgreSQL whenever a rule existed (`FOR UPDATE` on a nullable outer join) | High | 2026-11-15 | 2026-11-15 | 0 | PR #82 |
| DEF-02 | Sprint 2 end-to-end check | Yearly recurring rules always moved to February | Medium | 2026-11-15 | 2026-11-15 | 0 | PR #82 |
| DEF-03 | Sprint 2 end-to-end check | Recurring rules could not be paused (`is_active` read-only; PATCH returned 200 and changed nothing) | Medium | 2026-11-15 | 2026-11-15 | 0 | PR #82 |
| DEF-04 | Sprint 2 end-to-end check | Nothing ran the recurring-expense command (scheduler only did budget rollover) | High | 2026-11-15 | 2026-11-15 | 0 | PR #82 |
| DEF-05 | Sprint 2 end-to-end check | Moving only `start_date` past an existing `end_date` was accepted | Low | 2026-11-15 | 2026-11-15 | 0 | PR #82 |
| DEF-06 | Fuzzing (security) | A NUL byte in a CSV cell made the whole import fail with 500 | High | 2026-11-16 | 2026-11-16 | 0 | PR #92 (D-SEC-1) |
| DEF-07 | `pip-audit` | djangorestframework 3.16.1 had 5 published vulnerabilities | High | 2026-11-16 | 2026-11-16 | 0 | PR #92 (D-SEC-2) |
| DEF-08 | Review against NFR3 | Failed-login counting was per worker, multiplying an attacker's guesses | Medium | 2026-11-16 | 2026-11-16 | 0 | PR #92 (D-SEC-3) |
| DEF-09 | OWASP ZAP | API responses lacked CSP, Permissions-Policy, CORP and were cacheable | Medium | 2026-11-16 | 2026-11-16 | 0 | PR #92 (D-SEC-4) |
| DEF-10 | Production rehearsal | Receipt uploads returned 500 when the receipts volume was created as root | High | 2026-11-16 | 2026-11-16 | 0 | PR #93 |
| DEF-11 | Production rehearsal | Clients without SNI could not connect over HTTPS | Low | 2026-11-16 | 2026-11-16 | 0 | PR #93 |
| DEF-12 | Disaster-recovery drill | After a restore, `backups/LATEST` pointed at the pre-restore (empty) safety backup | High | 2026-11-16 | 2026-11-16 | 0 | PR #93 |
| DEF-13 | Review of PR #100 | A NUL byte in expense search or payment filter returned 500 | Medium | 2026-11-16 | 2026-11-17 | 1 | PR #100 |
| DEF-14 | Docker test run | A monitoring dashboard test read the real scheduler's status files and failed in Docker | Low | 2026-11-17 | 2026-11-17 | 0 | PR #106 |
| DEF-15 | Selenium CI | E2E stack used different PostgreSQL passwords for the database and the backend | High | 2026-11-17 | 2026-11-17 | 0 | PR #107 |
| DEF-16 | Selenium CI | Suite used `url_not_contains`, which Selenium does not have, and a report hook that stored the wrong object | Medium | 2026-11-17 | 2026-11-17 | 0 | PR #107 |
| DEF-17 | Selenium CI | Sign-up rate limit (5/min) throttled the suite, which registers a user per test | Medium | 2026-11-17 | 2026-11-17 | 0 | PR #107 (test stack limits) |
| DEF-18 | Accessibility audit | Text colour contrast below 4.5:1 (muted, success, danger and primary text) | Medium | 2026-11-17 | see PR #105 | — | PR #105 |
| DEF-19 | Accessibility audit | Alerts page 382 px wide on a 360 px screen | Medium | 2026-11-17 | see PR #105 | — | PR #105 |
| DEF-20 | Accessibility audit | No skip link; scrollable report tables not keyboard reachable | Low | 2026-11-17 | see PR #105 | — | PR #105 |
| DEF-21 | Accessibility audit | ARIA problems: chart points and unread dot without a role; export button labels not matching visible text | Low | 2026-11-17 | see PR #105 | — | PR #105 |

## Summary

| Severity | Found | Open |
|:--|--:|--:|
| Critical | 0 | 0 |
| High | 8 | 0 |
| Medium | 8 | 0 (DEF-18, 19 close when PR #105 merges) |
| Low | 5 | 0 (DEF-20, 21 close when PR #105 merges) |
| **Total** | **21** | |

Average aging of the 17 merged fixes: 1 day across 17 defects = **0.06 days**; no defect stayed open longer than 1 day.
Update DEF-18 to DEF-21 with the PR #105 merge date when it lands.

## Defect policy

- Every newly found defect is written up in the fixing pull request with a regression test where one applies; a defect that is not fixed immediately gets a GitHub issue with the `bug` label.
- Severity is critical, high, medium or low, assigned by impact, not by implementation effort.
- A release cannot claim zero open critical defects until this log and the open `bug` issues have been checked at sign-off.
