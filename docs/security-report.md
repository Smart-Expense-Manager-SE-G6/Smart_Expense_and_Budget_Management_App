# Security Test Report (S3-15)

- **Covers:** STP section 5.1 "Security Validation", NFR4, NFR5, NFR6, NFR14, SRS 6.5
- **Date:** 16 Nov 2026
- **Code tested:** branch `77-security-hardening`, based on `main` at `be7e321`
- **Environment:** PostgreSQL 16 in Docker Compose (the same images CI and production use), plus a local PostgreSQL 17 test cluster
- **Automated tests:** `backend/core/test_security.py` (TC-Sec-01 to TC-Sec-04); run in CI on every pull request

## Summary

| STP 5.1 check | How it was tested | Result |
|:--|:--|:--|
| 1. Password hashing and JWT/session token expiry | TC-Sec-01 (6 tests); sessions are used instead of JWT ([ADR-0001](adr/0001-authentication-sessions.md)) | **Pass** |
| 2. HTTPS/TLS verification | Django `check --deploy` with production settings; HSTS and secure-cookie tests; live check on the deployed site under S3-10 | **Pass** for configuration; live check on the deployed site is pending (S3-10, #72) |
| 3. Data-privacy compliance checks | TC-Sec-02 (4 tests): every resource and list refuses another user's data; plus the account export and deletion tests (TC-Account-01) | **Pass** |
| 4. Fuzzing of input fields (amount, notes, CSV import) | TC-Sec-03 (9 tests): about 30 attack strings and 20 malformed amounts per field, every query parameter, CSV cells, disguised uploads, and 300 seeded random inputs | **Pass** after fixing 1 defect (D-SEC-1) |
| 5. Penetration testing of authentication and role-based access | TC-Sec-04 (13 tests), plus an OWASP ZAP baseline scan of the frontend and API | **Pass**: no ZAP failures; header warnings fixed (D-SEC-4) |

**Defects found and fixed in this round: 4.** None remain open. **Dependency audit: 0 known vulnerabilities** after one upgrade.

## Defects found and fixed

| ID | Found by | Defect | Severity | Fix |
|:--|:--|:--|:--|:--|
| D-SEC-1 | Fuzzing (TC-Sec-03) | A CSV cell containing a NUL byte (`0x00`) made the import fail with a 500. PostgreSQL cannot store NUL, and one such cell rolled back every valid row in the file. | Medium (anyone with an account could break their own imports) | The importer now rejects that row with `INVALID_CHARACTER` and imports the rest. Regression test `test_nul_character_rejects_only_that_row`. |
| D-SEC-2 | `pip-audit` | Django REST Framework 3.16.1 had 5 published vulnerabilities. Three apply here: request bodies bypassing Django's upload size limit (PYSEC-2026-3827, CVE-2026-114136) and a slow `Accept` header parse (CVE-2026-114138), all denial of service. The other two affect features we do not use (AdminRenderer, TokenProxy). | High (unauthenticated denial of service) | Upgraded to 3.18.3. All 314 tests pass on it. |
| D-SEC-3 | Code review against NFR3 | No cache was configured, so each worker process kept its own login-failure and rate-limit counters. With several workers or replicas, an attacker got several times the allowed password guesses. | Medium | A shared database cache (`django_cache` table, created by migration `core 0001`), so every process and replica counts together. |
| D-SEC-4 | OWASP ZAP baseline | API responses had no Content-Security-Policy, Permissions-Policy or Cross-Origin-Resource-Policy, and were cacheable, so financial data could stay in a shared or browser cache. | Low | `core.security_headers.SecurityHeadersMiddleware` adds all four (`Cache-Control: no-store`) to every backend response except the admin site. Rescan: 0 failures, 66 passes. |

## 1. Password hashing and session expiry (TC-Sec-01)

| Test | What it proves |
|:--|:--|
| `test_passwords_are_stored_with_bcrypt` | Stored hashes start `bcrypt_sha256$` (NFR4); the plain password is not in the database. |
| `test_password_never_returned_or_audited` | Registration responses and audit snapshots never contain the password. |
| `test_session_expires_after_idle_timeout` | An expired session (30-minute idle timeout) gets 401. |
| `test_each_request_extends_the_idle_window` | Activity keeps the session alive; idle sessions die. |
| `test_logout_destroys_the_server_side_session` | Replaying a stolen session cookie after logout gets 401; the session row is gone. |
| `test_session_cookie_flags` | With production settings the session cookie is `HttpOnly`, `Secure` and `SameSite=Lax`. |

Password changes also sign out every other session (TC-Account-01, `test_change_keeps_this_session_and_signs_out_others`).

## 2. HTTPS/TLS (NFR4, NFR5)

- `manage.py check --deploy` with production settings (`DEBUG=false`, real secret key): **no issues** (1 silenced, see below).
- Outside development, the app redirects HTTP to HTTPS, sends HSTS for one year including subdomains, marks session and CSRF cookies `Secure`, and refuses to start without `DJANGO_SECRET_KEY`.
- `security.W021` (HSTS preload) is silenced on purpose. Preloading commits a domain to HTTPS-only in every browser for months and needs a domain the team owns. It can be turned on with `DJANGO_SECURE_HSTS_PRELOAD=true`.
- **Pending:** a live TLS check (certificate, redirect, HSTS header) on the deployed URL, done as part of S3-10 (#72).

## 3. Data privacy (NFR14, SRS 6.5) (TC-Sec-02)

| Test | What it proves |
|:--|:--|
| `test_every_resource_is_hidden_from_other_users` | 24 requests (GET, PATCH, DELETE and actions) by another user against expenses, receipts, categories, recurring rules, budgets, utilisation, budget expenses, members, alerts and audit entries: **all 404**, and nothing was changed. 404 rather than 403, so the attacker cannot tell the record exists. |
| `test_lists_never_contain_other_users_records` | Every list endpoint shows only the caller's own data. |
| `test_cannot_file_an_expense_under_someone_elses_category` | Category IDs from other users are refused. |
| `test_analytics_and_reports_only_count_own_spending` | Reports and analytics never include other users' expenses. |

Users can download all their data and delete their account (S3-09, TC-Account-01). No personal data is sent to a third party except alert emails, which the user can switch off (`email_alerts`).

## 4. Fuzzing (TC-Sec-03)

Every input below must give either a success or a 400 in the standard error envelope, never a 500, and must never reach the database as code.

| Test | Inputs | Result |
|:--|:--|:--|
| `test_expense_amount` | 19 malformed amounts: zero, negatives, too many decimals, NaN, ±Infinity, `1,000`, 20 digits, over the maximum, empty, hex, wrong types | All refused with 400 |
| `test_unusual_but_valid_amounts_keep_their_value` | `1e3`, `1E-2`, `+5`, `5 `, `1_000`, full-width and Arabic-Indic digits | Accepted and stored as exactly the number they mean |
| `test_text_fields_are_stored_verbatim_or_rejected` | About 30 strings in description, merchant and notes: SQL injection, XSS, path traversal, template and format strings, control characters, right-to-left override, emoji, 5,000 characters | No 500; stored text is returned unchanged; the `DROP TABLE` payload is stored as plain text and the table is intact |
| `test_names_of_categories_and_budgets` | The same strings as category and budget names | No 500 |
| `test_query_parameters` | Every string plus impossible dates in 12 query parameters (search, dates, paging, ordering, filters, report ranges, analytics) | No 500 |
| `test_csv_import_cells` | Every string as CSV cells in all six columns | No 500; accepted + rejected = total rows (found D-SEC-1) |
| `test_random_inputs` | 300 random strings and amounts from a fixed seed (reproducible) | No 500 |
| `test_upload_disguised_files` | An `.exe` renamed `.pdf`, an `.exe`, HTML and SVG with script disguised as PDF and PNG | All refused: extension, MIME type and file signature must match |
| `test_upload_path_traversal_stays_inside_receipts` | `../../../evil.pdf` | Stored under a random name in `receipts/<owner id>/` |

XSS also cannot happen in the frontend: React escapes all output, and the code has no `dangerouslySetInnerHTML` or `innerHTML`. SQL injection cannot happen in the backend: all queries go through the Django ORM; the only raw SQL is the health check's fixed `SELECT 1`.

## 5. Penetration testing of authentication and roles (TC-Sec-04)

| Attack | Test | Result |
|:--|:--|:--|
| Use the API without logging in | `test_unauthenticated_requests_are_refused` | 401 on all 8 resource lists |
| Brute-force a password | `test_brute_force_login_is_locked_out` | Locked out after 5 failures from one address (429); even the right password is refused until the window ends |
| Find out which emails have accounts | `test_login_does_not_reveal_which_emails_exist` | Same status and message for unknown email and wrong password |
| Session fixation | `test_session_fixation_is_prevented` | The session ID changes at login |
| Cross-site request forgery | `test_csrf_is_enforced_for_signed_in_writes`, `test_login_itself_is_csrf_protected` | Writes without the CSRF token get 403 `csrf_failed`; login itself is protected |
| Mass assignment | `test_mass_assignment_is_ignored` | Sending `email`, `is_staff`, `is_superuser`, `password` or `owner` is ignored |
| Member escalates to admin, adds people, edits or deletes the budget | `test_member_cannot_escalate_or_manage` | All 403; nothing changed |
| Admin takes ownership or deletes | `test_admin_cannot_take_ownership_or_delete` | Owner unchanged; delete 403 |
| Member removes another member | `test_member_can_only_leave_not_remove_others` | 403; leaving themselves is allowed |
| Reach the Django admin as a normal user | `test_django_admin_requires_staff` | Redirected to the admin login |
| Missing security headers | `test_api_responses_carry_security_headers`, `test_errors_and_unauthenticated_responses_carry_the_headers_too` | nosniff, `X-Frame-Options: DENY`, Referrer-Policy, CSP, Permissions-Policy, CORP and `no-store` on every response, including errors |

### OWASP ZAP baseline scan

The ZAP baseline scan (`zap-baseline.py`, `ghcr.io/zaproxy/zaproxy:stable`) was run against the running Docker stack.

| Target | Before fixes | After fixes |
|:--|:--|:--|
| API (`:8001/api/v1/`) | 0 FAIL, 5 WARN | **0 FAIL, 2 WARN, 66 PASS** |
| Frontend (`:5174`) | 0 FAIL, 7 WARN | Not rescanned yet; see below |

Remaining warnings and why they are acceptable:
- **API "Server header leaks version":** the scan ran against Django's development server. In production the API runs under gunicorn behind the HTTPS proxy, which removes the header (S3-10).
- **API "Non-storable content":** informational. It confirms `Cache-Control: no-store` is in place, which is intended.
- **Frontend header warnings** (CSP, nosniff, anti-clickjacking, Permissions-Policy, COEP): the scan ran against the Vite *development* server, which sends no security headers. Production serves the built frontend through the HTTPS proxy, which adds these headers. The frontend scan will be repeated against the deployed site (S3-10).
- ZAP found **no** XSS, information leaks, insecure cookies, vulnerable JavaScript libraries, session ID exposure or mixed content.

## Dependency audit

| Tool | Scope | Result |
|:--|:--|:--|
| `pip-audit -r backend/requirements.txt` | Backend | 5 vulnerabilities in djangorestframework 3.16.1, then **0 after the upgrade to 3.18.3** |
| `npm audit` | Frontend, production and development dependencies | **0 vulnerabilities** |

These audits will run in CI on every pull request once the rest of #73 is done.

## Accepted risks

| Risk | Why it is accepted |
|:--|:--|
| Registration says "email already registered", so it reveals whether an account exists | Telling a person why they cannot register is necessary for usability. Login does not reveal it, registration is rate-limited (5 per minute per address), and FR1 has no email verification flow (SASD OI-4). |
| The API accepts unusual but valid number formats (`1e3`, full-width digits) | The value stored is always exactly the number written; the CSV importer is stricter and accepts plain digits only. |
| The shared cache is a database table rather than Redis | One less service to run (SASD C4). Rate limits are not latency-sensitive, and PostgreSQL is already shared by every replica. |
