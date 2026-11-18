# Release Test Case Catalog

This catalog is the STP section 8 execution list for issue #84. The RTM remains the requirement source of truth. Results are from CI run [#44216307344](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44216307344) on `main` at `af9345f` (18 Nov 2026), the backup run, and the 18 Nov accessibility audit. A case without a recorded run is marked **Not executed**.

| ID | Requirement | Type | Steps | Expected result | Actual result / evidence |
|:--|:--|:--|:--|:--|:--|
| TC-Auth-01 | FR1 registration | Automated | Submit valid unique email/password | Account is created and dashboard opens | **Pass**: `accounts/test_auth_api.py`; Selenium `test_TC_Auth_01` (CI #44216307344) |
| TC-Auth-02 | FR1 login/logout | Automated | Sign in, access protected route, sign out | Session authenticates; logout protects route | **Pass**: `accounts/test_auth_api.py`; Selenium `test_TC_Auth_02` (CI #44216307344) |
| TC-Auth-03 | FR2 profile | Automated | Update profile and reload | New profile data persists | **Pass**: `accounts/test_auth_api.py`, `accounts/test_account_settings.py`; Selenium `test_TC_Auth_03` (CI #44216307344) |
| TC-Account-01 | FR2 account settings | Automated | Export and delete the account | Export is user-scoped; deletion removes owned data | **Pass**: `accounts/test_account_settings.py` (CI #44216307344) |
| TC-Shared-01 | FR3 shared budgets | Automated | Owner adds member; member opens budget | Role permissions are enforced | **Pass**: `budgets/test_shared.py`; Selenium `test_TC_Shared_01`, two browsers (CI #44216307344) |
| TC-Exp-01 | FR4 expense CRUD | Automated | Create, edit and soft-delete expense | Data changes persist; deleted item is excluded | **Pass**: `expenses/tests.py`; Selenium `test_TC_Exp_01` (CI #44216307344) |
| TC-Exp-02 | FR4 expense CRUD | Automated | Search and filter expenses | Matching results are returned without other users' data | **Pass**: `expenses/tests.py` search and filter tests (CI #44216307344) |
| TC-Exp-03 | FR5 receipt | Automated | Upload valid receipt and request it as owner | Receipt is accepted and protected | **Pass**: `expenses/tests.py` receipt tests; Selenium `test_TC_Exp_03` (CI #44216307344) |
| TC-Exp-04 | FR6 recurring rules | Automated | Create, pause, resume and materialize rule | Due expense is generated once | **Pass**: `expenses/test_recurring.py`; Selenium `test_TC_Exp_04` (CI #44216307344) |
| TC-Import-01 | FR7 CSV import | Automated | Preview CSV with one invalid row, then import | Valid rows import; bad row is reported | **Pass**: `expenses/test_import.py`; Selenium `test_TC_Import_01` (CI #44216307344) |
| TC-Cat-01 | FR8 categories | Automated | Create category/subcategory and list categories | Ownership and hierarchy rules hold | **Pass**: `expenses/tests.py`; Selenium `test_TC_Cat_01` (CI #44216307344) |
| TC-Cat-02 | FR9 suggestions | Automated | Request suggestion for known merchant | Advisory category suggestion is returned | **Pass**: `expenses/tests.py` suggestion tests; Selenium `test_TC_Cat_02` (CI #44216307344) |
| TC-Bud-01 | FR10 budget creation | Automated | Create weekly/monthly budget | Valid budget is stored | **Pass**: `budgets/tests.py`; Selenium `test_TC_Bud_01` (CI #44216307344) |
| TC-Bud-02 | FR11 utilization | Automated | Add expense within budget period | Utilization reflects current spend | **Pass**: `budgets/tests.py` utilisation tests (CI #44216307344) |
| TC-Bud-03 | FR12 rollover/reset | Automated | Close period with rollover/reset mode | Next period uses configured behavior | **Pass**: `budgets/tests.py` rollover tests (CI #44216307344) |
| TC-Analytics-01 | FR13 analytics | Automated | Request summary, category and comparison data | Aggregates match stored expenses | **Pass**: `analytics/tests.py` (CI #44216307344) |
| TC-Analytics-02 | FR14 forecast | Automated | Request predictive insights with history | Projection is returned with stable shape | **Pass**: `analytics/tests.py` predictive insights (CI #44216307344) |
| TC-Analytics-03 | FR15 comparison | Automated | Request month/year comparison | Period series is returned | **Pass**: `analytics/tests.py` comparison (CI #44216307344) |
| TC-Alert-01 | FR16 thresholds | Automated | Spend through 80% and 100% | One alert per threshold/period | **Pass**: `alerts/tests.py`; Selenium `test_TC_Alert_01` (CI #44216307344) |
| TC-Alert-02 | FR17 anomaly | Automated | Create five history expenses then >3x expense | Explainable anomaly alert is created | **Pass**: `alerts/tests.py` anomaly tests (CI #44216307344) |
| TC-Alert-03 | FR18 delivery | Automated | Trigger alert with email adapter configured/unconfigured | In-app alert persists and delivery status records | **Pass**: `alerts/tests.py` delivery tests (CI #44216307344) |
| TC-Report-01 | FR19 date range | Automated | Request valid and over-limit ranges | Valid report returns; >366 days is rejected | **Pass**: `analytics/tests.py` 366-day cap (CI #44216307344) |
| TC-Report-02 | FR20 exports | Automated | Export PDF and XLSX | PDF and ZIP/XLSX responses are downloadable | **Pass**: `analytics/tests.py`; Selenium `test_TC_Report_01` downloads both files (CI #44216307344) |
| TC-Audit-01 | FR21 audit trail | Automated | Update expense and request history | Before/after audit entry is visible | **Pass**: `audit/test_api.py`; Selenium `test_TC_Audit_01` (CI #44216307344) |
| TC-Backup-01 | FR22 backup/restore | Scripted | Create backup and run rehearsal restore | Backup validates and rehearsal completes | **Pass**: restore rehearsal, row counts match for all 19 tables (CI #44216307344 and backup run #44216307590) |
| TC-Perf-01 | NFR1 performance | JMeter | Load dashboard/analytics with 10k expenses | p95 meets 2–3s target | **Pass**, timed Django test not JMeter: `analytics/test_performance.py::test_nfr1_dashboard_analytics_under_2s_for_10k_transactions` (CI #44216307344) |
| TC-Perf-02 | NFR2 performance | JMeter | Run one-year report and PDF/XLSX exports | Each completes within 5s | **Pass**, timed Django test not JMeter: `analytics/test_performance.py::test_nfr2_one_year_report_and_exports_under_5s` (CI #44216307344) |
| TC-Perf-03 | NFR3 scaling | JMeter/Compose | Run with two backend replicas and shared cookie | Both replicas serve requests without session errors | **Not executed**: no two-replica run recorded |
| TC-Sec-01 | NFR4/NFR5 auth/security | Automated | Check password hashing, session expiry and TLS settings | Credentials are protected; session expires | **Pass**: `core/test_security.py` (CI #44216307344); see `docs/testing/security-report.md` |
| TC-Sec-03 | NFR6 injection | Automated | Send malformed/query payloads | No injection or data disclosure | **Pass**: `core/test_security.py` (CI #44216307344); OWASP ZAP 0 FAIL in `docs/testing/security-report.md` |
| TC-Sec-04 | NFR6 CSRF/XSS | Automated | Exercise unsafe methods and escaped content | CSRF and output protections hold | **Pass**: `core/test_security.py` (CI #44216307344) |
| TC-Responsive-01 | NFR7 responsive UI | Manual | Check dashboard at mobile/tablet/desktop widths | Layout remains usable without overflow | **Pass**: 0 overflow at 360/768/1280 px, [accessibility audit](accessibility-audit.md) 18 Nov |
| TC-A11y-01 | NFR8 accessibility | Manual | Keyboard navigate forms and inspect labels/focus | Controls are labeled and reachable | **Pass**: axe-core 0 violations, 5/5 keyboard checks, [accessibility audit](accessibility-audit.md) 18 Nov |
| TC-Uptime-01 | NFR9 uptime | Scripted | Poll health endpoint and restart services | Health endpoint recovers | **Pass**: staging smoke test 16/16 incl. health (CI #44216307344); recovery drill in `docs/operations/recovery-runbook.md` |
| TC-Backup-02 | NFR10 backups | Scripted | Run scheduled backup and inspect retention | Backup is created and old copies rotate | **Partly executed**: backup creation passes (backup run #44216307590); retention rotation not exercised, so counted as not executed |
| TC-Arch-01 | NFR11 architecture | Review | Inspect app boundaries and dependencies | Django apps remain modular | **Not executed**: no recorded architecture review |
| TC-Log-01 | NFR12 request IDs | Automated | Request API and inspect response/log | Same request ID is traceable | **Pass**: `core/tests.py`, `monitoring/tests.py` request-ID tests (CI #44216307344) |
| TC-Container-01 | NFR13 containerization | Scripted | Build and start Compose stack | Services become healthy | **Pass**: production Compose stack built, deployed and smoke-tested (CI #44216307344) |
| TC-Privacy-01 | NFR14 privacy | Automated | Access another user's objects and export/delete account | Ownership is enforced; data controls work | **Pass**: `core/test_security.py`, `accounts/test_account_settings.py` (CI #44216307344) |
