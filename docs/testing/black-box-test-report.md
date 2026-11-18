# Black-Box Test Report

**Release:** Smart Expense and Budget Management Application 1.0
**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) at `69426f5`, 18 Nov 2026. Logs from that run are in [`reports/test-logs/`](reports/test-logs/).
**Objective:** test the system against its requirements without looking at the code, using equivalence partitioning and boundary value analysis.

## Techniques

- **Equivalence partitioning:** inputs are split into classes the system should treat the same way (valid, invalid,
  missing, belonging to another user), and one test is chosen from each class.
- **Boundary value analysis:** values on and just past each limit the SRS or design sets: the 366-day report range,
  the 80% and 100% alert thresholds, the 5-expense anomaly sample, 1,000 import rows and 5 MB, and a page-size maximum.

## Executed tests

| ID | Partition or boundary | Expected | Test | Status |
|---|---|---|---|---|
| BB-FE-001 | Equivalence: valid monitoring status | Known status maps to its label and tone | frontend `monitoring.test.js` | PASS |
| BB-FE-002 | Equivalence: missing or unknown status | Status stays explicitly unknown | frontend `monitoring.test.js` | PASS |
| BB-01 | Registration: weak password partition | Refused with a field error | `test_weak_password_rejected_on_password_field` | PASS |
| BB-02 | Login: wrong password vs unknown e-mail | Both give the same answer (no account enumeration) | `test_wrong_password_and_unknown_email_look_the_same` | PASS |
| BB-03 | Budget limit boundaries: 0 and negative | Refused | `test_rejects_zero_and_negative_limits` | PASS |
| BB-04 | Import amounts: invalid, zero, negative, overflow | Only those rows rejected | `test_invalid_amounts_are_rejected_per_row` | PASS |
| BB-05 | Report range boundary: 366 days | Allowed | `test_one_year_range_of_366_days_is_allowed` | PASS |
| BB-06 | Report range boundary: over 366 days | 400 `DATE_RANGE_EXCEEDED` | `test_range_over_366_days_uses_adr_error_code` | PASS |
| BB-07 | Alert threshold boundary: 80% | One 80% alert | `test_alert_created_at_80_percent` | PASS |
| BB-08 | Alert threshold boundary: 100% | Both the 80% and 100% alerts | `test_100_percent_creates_both_threshold_alerts` | PASS |
| BB-09 | Anomaly minimum sample: fewer than 5 expenses | No anomaly alert | `test_no_alert_with_fewer_than_five_previous_expenses` | PASS |
| BB-10 | Import size limits: empty, over 1,000 rows, over 5 MB | Whole file refused with a reason | `test_empty_file`, `test_too_many_rows`, `test_file_too_large` | PASS |
| BB-11 | Receipt: missing, wrong type, oversized | Refused | `test_rejects_invalid_receipts_and_missing_receipts`, `test_rejects_oversized_receipts` | PASS |
| BB-12 | Duplicates: budget for the same period, member added twice | Refused | `test_rejects_duplicate_budgets_for_same_period`, `test_rejects_duplicate_member` | PASS |
| BB-13 | Pagination: page size above the maximum, invalid page | 400 | `test_list_rejects_page_size_above_maximum`, `test_list_rejects_invalid_page_and_page_size` | PASS |
| BB-14 | Export format partition: unknown format | 400 | `test_export_invalid_format_returns_400` | PASS |
| BB-15 | Shared budget role partition: member | Cannot change settings, add or remove members | `test_member_cannot_change_settings`, `test_member_cannot_add_members`, `test_member_cannot_remove_others` | PASS |
| BB-16 | Session: idle for longer than 30 minutes | Next request refused with 401 | `test_session_expires_after_idle_timeout` | PASS |
| BB-17 | Protected page without a session | Redirect to sign-in | Selenium `test_TC_Auth_02_login_logout_and_protected_redirect`; Postman "Profile after logout is refused" | PASS |
| BB-18 | Text input with a NUL character | Row or request refused, nothing else affected | `test_nul_character_rejects_only_that_row`, `test_TC_Exp_01_text_filters_refuse_nul_character` | PASS |

## Summary

Executed: 20. Passed: 20. Failed: 0. Not run: 0. The backend cases are part of the 366 / 366 backend
tests ([`backend-django-test.log`](reports/test-logs/backend-django-test.log)). The frontend cases are 2 / 2
([`frontend-test.log`](reports/test-logs/frontend-test.log)), and the browser and Postman cases are in their own logs.

## Commands

```bash
cd backend && python manage.py test
cd frontend && npm test
```

## Note on the first version of this report

The first version (commit 39b92d1 and the commits after it) recorded these suites as NOT RUN. They could not be run on that
machine: Python was not installed and the Docker daemon was not running. They were then run in GitHub Actions, on the
same environment the project's CI uses every day (Ubuntu, Python 3.12, PostgreSQL 16, Docker, headless Chrome). This
report records those results.
