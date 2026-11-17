# Defect Log

GitHub Issues with the `bug` label are the system of record, replacing Jira in accordance with `docs/deviations.md` (T-01). This log is the release-facing index; it does not replace the issue discussions.

| Defect ID | GitHub issue | Summary | Severity | Found | Fixed / status | Aging at 2026-11-17 |
|:--|:--|:--|:--|:--|:--|--:|
| DEF-001 | #74 | E2E Docker startup used different PostgreSQL passwords for db and backend | High | 2026-11-17 | Fixed in `a7fca3d` on `feature/issue-74-selenium-e2e` | 0 days |
| DEF-002 | #74 | Selenium suite used unsupported `url_not_contains` expected condition | Medium | 2026-11-17 | Fixed in `b6eb5b1` on `feature/issue-74-selenium-e2e` | 0 days |

## Defect policy

- Every newly found defect gets a GitHub issue with the `bug` label and a link to the failing test or workflow artifact.
- Severity is critical, high, medium or low; severity is assigned by impact, not by implementation effort.
- Aging is calendar days from the issue's opened date to the report date; closed defects retain their historical aging.
- A release cannot claim zero critical defects until the GitHub issue search and open-issue review have been recorded in the Test Summary Report.
