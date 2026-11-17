# Release Test Case Catalog

This catalog is the STP section 8 execution list for issue #84. The RTM remains the requirement source of truth. `Actual result` is intentionally `Pending execution` when no reproducible execution artifact exists in this repository.

| ID | Requirement | Type | Steps | Expected result | Actual result / evidence |
|:--|:--|:--|:--|:--|:--|
| TC-Auth-01 | FR1 registration | Automated | Submit valid unique email/password | Account is created and dashboard opens | Backend auth tests; E2E dependency |
| TC-Auth-02 | FR1 login/logout | Automated | Sign in, access protected route, sign out | Session authenticates; logout protects route | Backend auth tests; E2E dependency |
| TC-Auth-03 | FR2 profile | Automated | Update profile and reload | New profile data persists | Account settings tests |
| TC-Account-01 | FR2 account settings | Automated | Export and delete the account | Export is user-scoped; deletion removes owned data | `backend/accounts/test_account_settings.py` (`test_export_contains_every_kind_of_data`, `test_deletes_everything_the_user_owns`) |
| TC-Shared-01 | FR3 shared budgets | Automated | Owner adds member; member opens budget | Role permissions are enforced | `backend/budgets/test_shared.py` |
| TC-Exp-01 | FR4 expense CRUD | Automated | Create, edit and soft-delete expense | Data changes persist; deleted item is excluded | `backend/expenses/tests.py` |
| TC-Exp-02 | FR4 expense CRUD | Automated | Search and filter expenses | Matching results are returned without other users' data | `backend/expenses/tests.py` |
| TC-Exp-03 | FR5 receipt | Automated | Upload valid receipt and request it as owner | Receipt is accepted and protected | Expense API tests |
| TC-Exp-04 | FR6 recurring rules | Automated | Create, pause, resume and materialize rule | Due expense is generated once | `backend/expenses/test_recurring.py` |
| TC-Import-01 | FR7 CSV import | Automated | Preview CSV with one invalid row, then import | Valid rows import; bad row is reported | `backend/expenses/test_import.py` |
| TC-Cat-01 | FR8 categories | Automated | Create category/subcategory and list categories | Ownership and hierarchy rules hold | `backend/expenses/tests.py` |
| TC-Cat-02 | FR9 suggestions | Automated | Request suggestion for known merchant | Advisory category suggestion is returned | Category suggestion tests |
| TC-Bud-01 | FR10 budget creation | Automated | Create weekly/monthly budget | Valid budget is stored | `backend/budgets/tests.py` |
| TC-Bud-02 | FR11 utilization | Automated | Add expense within budget period | Utilization reflects current spend | Budget service tests |
| TC-Bud-03 | FR12 rollover/reset | Automated | Close period with rollover/reset mode | Next period uses configured behavior | Rollover command/tests |
| TC-Analytics-01 | FR13 analytics | Automated | Request summary, category and comparison data | Aggregates match stored expenses | `backend/analytics/tests.py` |
| TC-Analytics-02 | FR14 forecast | Automated | Request predictive insights with history | Projection is returned with stable shape | Analytics tests |
| TC-Analytics-03 | FR15 comparison | Automated | Request month/year comparison | Period series is returned | Analytics tests |
| TC-Alert-01 | FR16 thresholds | Automated | Spend through 80% and 100% | One alert per threshold/period | `backend/alerts/tests.py` |
| TC-Alert-02 | FR17 anomaly | Automated | Create five history expenses then >3x expense | Explainable anomaly alert is created | `backend/alerts/tests.py` |
| TC-Alert-03 | FR18 delivery | Automated | Trigger alert with email adapter configured/unconfigured | In-app alert persists and delivery status records | `backend/alerts/tests.py` |
| TC-Report-01 | FR19 date range | Automated | Request valid and over-limit ranges | Valid report returns; >366 days is rejected | `backend/analytics/tests.py` |
| TC-Report-02 | FR20 exports | Automated | Export PDF and XLSX | PDF and ZIP/XLSX responses are downloadable | `backend/analytics/tests.py` |
| TC-Audit-01 | FR21 audit trail | Automated | Update expense and request history | Before/after audit entry is visible | `backend/audit/test_api.py` |
| TC-Backup-01 | FR22 backup/restore | Scripted | Create backup and run rehearsal restore | Backup validates and rehearsal completes | `scripts/rehearse_restore.sh` |
| TC-Perf-01 | NFR1 performance | JMeter | Load dashboard/analytics with 10k expenses | p95 meets 2–3s target | Run artifact required; pending on this branch |
| TC-Perf-02 | NFR2 performance | JMeter | Run one-year report and PDF/XLSX exports | Each completes within 5s | Run artifact required; pending on this branch |
| TC-Perf-03 | NFR3 scaling | JMeter/Compose | Run with two backend replicas and shared cookie | Both replicas serve requests without session errors | Run artifact required; pending on this branch |
| TC-Sec-01 | NFR4/NFR5 auth/security | Automated | Check password hashing, session expiry and TLS settings | Credentials are protected; session expires | `backend/core/test_security.py` |
| TC-Sec-03 | NFR6 injection | Automated | Send malformed/query payloads | No injection or data disclosure | `backend/core/test_security.py` |
| TC-Sec-04 | NFR6 CSRF/XSS | Automated | Exercise unsafe methods and escaped content | CSRF and output protections hold | `backend/core/test_security.py` |
| TC-Responsive-01 | NFR7 responsive UI | Manual | Check dashboard at mobile/tablet/desktop widths | Layout remains usable without overflow | Frontend build; manual evidence pending |
| TC-A11y-01 | NFR8 accessibility | Manual | Keyboard navigate forms and inspect labels/focus | Controls are labeled and reachable | Frontend source; manual evidence pending |
| TC-Uptime-01 | NFR9 uptime | Scripted | Poll health endpoint and restart services | Health endpoint recovers | `deploy/smoke_test.sh` |
| TC-Backup-02 | NFR10 backups | Scripted | Run scheduled backup and inspect retention | Backup is created and old copies rotate | `scripts/backup.sh` |
| TC-Arch-01 | NFR11 architecture | Review | Inspect app boundaries and dependencies | Django apps remain modular | Repository review |
| TC-Log-01 | NFR12 request IDs | Automated | Request API and inspect response/log | Same request ID is traceable | `backend/core/tests.py` |
| TC-Container-01 | NFR13 containerization | Scripted | Build and start Compose stack | Services become healthy | `docker-compose.yml`, CI evidence |
| TC-Privacy-01 | NFR14 privacy | Automated | Access another user's objects and export/delete account | Ownership is enforced; data controls work | Account/security tests |
