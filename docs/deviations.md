# Deviation and Decision Log (S3-21)

The project documents are final and are not edited after approval:

- Project Proposal
- Functional & Non-Functional Requirements
- SRS v1.0 (05-Sep-2026)
- SASD v1.0 (05-Oct-2026)
- Software Test Plan (STP) v1.0
- Use Case Diagram v1.0

Where the built system differs from them, the difference and its reason are recorded here instead.
Most differences come from decisions the documents themselves left open (the SASD's open issues
OI-1 to OI-7). Those decisions are recorded as ADRs in `docs/adr/`.

Each row says what the document says, what was built, and why. "Ref" points to the ADR, issue or
pull request where the decision was made. Rows marked **Closing in Sprint 3** are gaps with an open
task; they will stop being deviations when that task is merged.

## 1. Decisions the documents left open

These are not departures from the documents. The documents asked for a decision, and this is the
decision.

| # | Document | Left open | Decided | Reason | Ref |
|:--|:--|:--|:--|:--|:--|
| D-01 | SRS 2.1, 2.5; SASD OI-1, C1, Table 4; Proposal | Stack: Python (Django) or JavaScript (MERN) | Django 5.2 + Django REST Framework, React 19 + Vite, PostgreSQL 16, Docker Compose | The domain needs exact decimals, uniqueness and referential integrity (SASD 3.5 rejects a document store for this reason). Django's ORM, migrations, admin and security middleware cover NFR4–NFR6 and NFR11 with the least custom code for a four-person team (SASD C4). | Sprint 1 |
| D-02 | SRS 2.5, NFR5; SASD OI-2, 3.6, 3.9; STP 5.1 | JWT or server-side session | Server-side sessions (Django `SessionAuthentication`) in an HttpOnly cookie, with CSRF protection; 30-minute idle expiry (`SESSION_IDLE_TIMEOUT_SECONDS`) | A browser-only client gains nothing from JWT. Sessions can be revoked instantly on logout or password change, and the token never reaches JavaScript (safer against XSS). Sessions are stored in PostgreSQL, so any backend instance can serve any request (NFR3). SRS and STP both allow "JWT/session". | ADR-0001 |
| D-03 | SASD OI-3; NFR2 | Maximum report and chart date range | 366 days; longer ranges return `DATE_RANGE_EXCEEDED` | Keeps the NFR2 "1-year range in 5 seconds" target bounded; 366 allows a full leap year. | ADR-0002 |
| D-04 | SASD OI-6; FR17 | Anomaly rule | An expense is an anomaly when it is more than 3 times the average of the user's previous 5 expenses in the same category; no alert until 5 exist | Simple, explainable, and avoids false positives for new users (the minimum sample size OI-6 asked for). | #41, PR #53 |
| D-05 | SASD OI-7; FR7 | Import file layout and statement formats | One CSV layout (`date`, `amount`, optional `category`, `payment_mode`, `merchant`, `notes`), UTF-8, at most 5 MB and 1,000 rows; per-row errors | No bank format had been selected (OI-7), and every bank's statement layout differs. Net-banking portals let customers download statements as CSV or as spreadsheets that save as CSV, so a bank statement is imported through that export into one documented layout. Unknown categories are imported uncategorised rather than rejected. | ADR-0003, #7, PR #81 |
| D-06 | SASD OI-4 | Which optional features enter v1.0 | Google login, push notifications and an ML classifier are not built | The SRS marks all three optional (FR1 "optionally", FR18 "push notification optional", FR9 "rule-based or lightweight ML"). Effort went to the mandatory requirements. SASD 1.2 already places push and trained ML models out of scope. | This log |
| D-07 | SASD OI-5 | Remaining sequence diagrams, physical schema, retention, uptime measurement | Physical schema in `docs/data-dictionary.md`; uptime measured by an external check on `/api/v1/health/` | Data dictionary produced in Sprint 1; the uptime check is part of S3-17. | #18, #79 |

## 2. SRS, Requirements document and Proposal

| # | Section | Says | Built | Reason | Ref |
|:--|:--|:--|:--|:--|:--|
| R-01 | FR1 | Email/password, optionally OAuth/Google | Email/password only | Optional in the SRS; see D-06. | D-06 |
| R-02 | FR3, SRS 6.5 | "Only an 'admin' member may add or remove members or change shared-budget settings" | The budget's **owner** and any **admin** may manage members and settings; only the owner may delete the budget; members view and add expenses and may leave | The person who creates a shared budget is its first admin (the use-case diagram's Admin creates the shared budget). Keeping deletion with the owner stops an admin from deleting someone else's budget. Members have exactly the rights SRS 6.5 gives them. | #37, PR #67 |
| R-03 | FR3, use case "Add Shared Expense" | Members add expenses within the shared budget | Members add ordinary expenses; any expense in the budget's category and period counts towards the shared budget | Members do not need a separate "shared expense" form. Their expenses count in utilisation, alerts and rollover automatically, and the budget shows who spent what. | #37, PR #67 |
| R-04 | FR7 | "CSV/bank statement upload" | CSV upload; statements via their CSV export | See D-05. | ADR-0003 |
| R-05 | FR9 | Suggest from "past patterns or merchant name", rule-based or ML | Rule-based keyword suggestions; history-based suggestions are added in S3-02 | ML is optional (D-06). **Closing in Sprint 3:** the user's own past categorisation of a merchant becomes the first suggestion. | #57 |
| R-06 | FR13, SRS 3.1 | An analytics/insights view with pie, bar and line charts | Spending trend, forecast and category breakdown on the dashboard | **Closing in Sprint 3:** a separate Analytics page with all three chart types. | #69 |
| R-07 | FR16 | Alerts at thresholds "e.g., 80%, 100%" | Fixed thresholds of 80% and 100%, one alert per budget, threshold and period | The SRS gives these values; user-chosen thresholds were not required. | #26 |
| R-08 | FR18 | In-app and email | In-app alerts and email through an adapter, sent after the change commits | Email has been tested with Django's test mailer; **closing in Sprint 3:** a real email provider in production. Push is optional (D-06). | #42, #72 |
| R-09 | FR22, SRS 5.8.2 | "An admin can trigger a restore" | Backup, restore and rehearsal scripts run by the system operator (`docker compose run --rm backup /scripts/restore.sh`); daily automatic backups | Restore replaces the whole database, so it is an operator action, not an in-app button any user could press. The operator is the use-case diagram's Admin. TC-Backup-01 runs in CI on every pull request. | #45, #46 |
| R-10 | NFR4 | Encrypted at rest and in transit; bcrypt | bcrypt password hashing; HTTPS enforced outside development | **Closing in Sprint 3:** the production database and receipt storage use the hosting provider's at-rest encryption, recorded in the runbook. | #72 |
| R-11 | SRS 4 | Use case and entity-relationship diagrams "in a future revision" | Use case diagram delivered; entities documented in `docs/data-dictionary.md` | The data dictionary gives each entity's fields, types, keys and relationships, which is the information an ER diagram carries. | #18 |
| R-12 | FR4, Proposal | Field "payment mode" | Field `payment_method` (API and database) | Same meaning; the name follows the data dictionary. | #1 |

## 3. SASD v1.0

| # | Section | Says | Built | Reason | Ref |
|:--|:--|:--|:--|:--|:--|
| A-01 | 4.3, Figure 4.1 | Credential sent in an `Authorization` header; login returns a token with `expires_at` | Session cookie plus `X-CSRFToken` header; login returns the user | Follows D-02. SASD 4.3 was written to hold either choice of OI-2. | ADR-0001 |
| A-02 | 4.3 Table 8 | `GET, PATCH /users/me` | `GET, PATCH /api/v1/me/` | Shorter path; same behaviour. | #13 |
| A-03 | 4.3 Table 8 | `GET /budgets/{id}/utilisation` | `GET /api/v1/budgets/{id}/utilization/` | US spelling, used consistently across the code. | #25 |
| A-04 | 4.3 Table 8 | `POST /alerts/{id}/read`; `GET, PUT /alert-preferences` | `PATCH /api/v1/alerts/{id}/mark-read/` (the Alerts screen's "Mark all read" marks each unread alert); no preferences endpoint | Thresholds are fixed (R-07). **Closing in Sprint 3:** an email on/off setting in account settings (S3-09). | #26, #71 |
| A-05 | 4.3 Table 8 | `GET /categories/suggest` | `GET /api/v1/categories/suggestions/?description=` | Plural noun, matching the response key `suggestions`. | #9 |
| A-06 | 4.3 Table 8 | `/recurring-expenses` | `/api/v1/recurring-rules/` | The resource is the rule, not the expenses it creates (SASD D3). | #6 |
| A-07 | 4.3 Table 8 | `/expenses/import` as a job returning 202 | `POST /api/v1/expenses/import/` returns 200 with the result; `?dry_run=true` previews | With a 1,000-row cap the import finishes within the request, so a job resource adds complexity without benefit. | ADR-0003 |
| A-08 | 4.3 Table 8 | `/analytics/summary, /by-category, /trend, /projection, /comparison` | `/summary/`, `/by-category/`, `/predictive-insights/`, `/comparison/` (with a monthly trend series) | The trend line comes from the comparison series, so a separate endpoint was not needed; "predictive-insights" names FR14. | #21, #39, #40 |
| A-09 | 4.3 Table 8 | `POST /reports` (stored artefact) and `GET /reports/{id}/download` | `GET /api/v1/analytics/reports/` and `GET /api/v1/analytics/reports/export/?export_format=pdf|xlsx` | Reports are generated on request within the NFR2 time limit, so nothing has to be stored or cleaned up. SASD 3.6 already says report artefacts "may be regenerated and are not part of the record". | #43, #44 |
| A-10 | 4.3 Table 8; 3.6 | `POST /shared-budgets`; a `SharedBudget` entity | Any budget can be shared: `GET, POST /api/v1/budgets/{id}/members/`, `PATCH, DELETE …/members/{member_id}/`; a `BudgetMember` entity | One budget model for personal and shared budgets means utilisation, alerts and rollover work the same for both, with no duplicated logic. | #37, PR #67 |
| A-11 | 4.3 Table 8 | `GET /audit` | Audit entries are written for every change; **closing in Sprint 3:** `GET /api/v1/audit/` and a history panel | Until then the audit trail is viewable in the Django admin site. | #83 |
| A-12 | 4.3 example | IDs such as `exp_55021`, `bdg_301` | Integer IDs | The SASD examples are illustrative; integer primary keys are the Django default and every endpoint checks ownership, so IDs reveal nothing usable. | — |
| A-13 | 4.4 Table 9 | Error codes such as `AUTH_INVALID`, `NOT_OWNER`, `PERIOD_CLOSED` | Same envelope `{error: {code, message, field, request_id}}`; codes are DRF's (`not_authenticated`, `permission_denied`, `not_found`, `invalid`) plus our own (`invalid_credentials`, `duplicate_budget`, `DATE_RANGE_EXCEEDED`, import codes) | The envelope, field and request ID match 4.4 exactly. Codes reuse the framework's stable names instead of renaming each one. Another user's records return 404, so nothing reveals that a record exists (4.4 "refuse without revealing"). | #12 |
| A-14 | 4.4 | Application log and separate error log, rotated | Structured console logs with request ID | **Closing in Sprint 3:** rotating application and error log files. | #79 |
| A-15 | 4.5 Table 10 | Budget screen includes "alert thresholds" | Thresholds fixed at 80% and 100% | See R-07. | #26 |
| A-16 | 4.2 | Figure captions | The caption under the expense diagram says "Figure 4.1 – Authentication", and the caption under the login diagram says "Figure 4.2 – Recording an expense" | The two captions are swapped in the document; the diagrams themselves are correct. | — |
| A-17 | 2.2, 3.8 | "Data dictionary and RTM – to be produced" | Both produced: `docs/data-dictionary.md`, `docs/rtm.md` | Done after the SASD was approved. | #18 |
| A-18 | 4.6 OI-1 to OI-7 | Open issues | All decided | See section 1. | ADR-0001 to 0003 |

## 4. Software Test Plan

| # | Section | Says | Built | Reason | Ref |
|:--|:--|:--|:--|:--|:--|
| T-01 | 6 Tools | Jira for defect tracking | GitHub Issues with the `bug` label, on the team's GitHub project board | Code, pull requests, reviews and defects live in one place, and a defect links directly to the pull request that fixes it. | #84 |
| T-02 | 6 Tools | Selenium or Cypress for UI automation | Selenium (Python), under S3-12 | Matches the STP. The Playwright scripts used for interim checks in Sprints 1 and 2 are being ported. | #74 |
| T-03 | 6 Tools | Postman for API testing | Postman collection run with newman in CI on every pull request | Matches the STP. | #86 |
| T-04 | 6 Tools | JMeter for performance | JMeter test plan under S3-13 | Matches the STP. | #75 |
| T-05 | 5 Types | Regression testing | The full backend suite, lint, build and Postman run on every pull request (GitHub Actions) | Every change is regression-tested before merge. | #86 |
| T-06 | 7 Schedule | Execution 1–10 Oct, UAT 12–15 Oct | Testing ran in every sprint, continuously through CI; UAT is scheduled at the end of Sprint 3 | The schedule assumed one test phase after development. Testing each feature as it was built found defects earlier. | #84 |
| T-07 | 5.1 | "JWT/session token expiry" | Session idle expiry (30 minutes) | See D-02. | ADR-0001 |
| T-08 | 1 Definitions | JWT | Not used | See D-02. | ADR-0001 |
| T-09 | 4 | ML classifier accuracy excluded beyond a functional check | No ML classifier | See D-06. | — |

## 5. Use Case Diagram v1.0

| # | Use case | Built as | Reason | Ref |
|:--|:--|:--|:--|:--|
| U-01 | Create Shared Budget (Admin) | Create a budget, then add people from the sharing dialog | One budget model (A-10). The creator is the owner and first admin. | PR #67 |
| U-02 | Manage Members Add or Remove (Admin) | Sharing dialog: add by email, change role, remove; members can leave | — | PR #67 |
| U-03 | View Audit Trail (Admin) | Django admin site today; **closing in Sprint 3:** in-app history | See A-11. | #83 |
| U-04 | Backup or Restore Data (Admin) | Operator scripts and a daily scheduled backup | See R-09. | #45, #46 |
| U-05 | Login «include» Authenticate User | Session login | See D-02. | ADR-0001 |

## 6. How to keep this log

- Add a row whenever the code knowingly differs from a document, in the same pull request as the change.
- Remove the "Closing in Sprint 3" note from a row when its issue is merged, and change "Built" to what was built.
- Keep the reason short and specific, and link the ADR, issue or pull request.
