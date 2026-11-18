# Code Coverage Report (statement / line coverage)

**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) on `main` at `69426f5`, 18 Nov 2026 (browsable report: [`reports/coverage/index.html`](reports/coverage/index.html); raw data: [`reports/coverage/coverage.json`](reports/coverage/coverage.json))
**Tool:** coverage.py 7.6.10, with branch measurement on (`backend/.coveragerc`)
**Scope:** all backend application code; migrations, tests and `manage.py` are excluded.

## Result

| Measure | Covered | Total | % |
|:--|--:|--:|--:|
| **Lines (statements)** | 2,464 | 2,605 | **94.6%** |
| Branches | 496 | 578 | 85.8% |
| Combined (coverage.py total) | | | 93.0% |

**Quality gate:** CI fails the build if combined coverage drops below **80%** (`fail_under = 80`). This release is
13.0 points above the gate.

## By module

| Module | Files | Statements | Covered | Line coverage |
|:--|--:|--:|--:|--:|
| `accounts` | 9 | 319 | 310 | 97.2% |
| `alerts` | 10 | 169 | 161 | 95.3% |
| `analytics` | 7 | 372 | 340 | 91.4% |
| `audit` | 8 | 156 | 152 | 97.4% |
| `budgets` | 12 | 333 | 319 | 95.8% |
| `config` | 3 | 100 | 95 | 95.0% |
| `core` | 13 | 176 | 159 | 90.3% |
| `expenses` | 13 | 821 | 781 | 95.1% |
| `monitoring` | 9 | 159 | 147 | 92.5% |
| **Total** | **84** | **2,605** | **2,464** | **94.6%** |

## Files below 90% line coverage

| File | Statements | Missed | Line coverage | Missed lines |
|:--|--:|--:|--:|:--|
| `core/adapters/factory.py` | 9 | 3 | 66.7% | 10-11, 13 |
| `audit/admin.py` | 13 | 3 | 76.9% | 13, 16, 19 |
| `core/adapters/email.py` | 31 | 7 | 77.4% | 24, 52, 54-55, 74, 76-77 |
| `expenses/models.py` | 74 | 16 | 78.4% | 70, 72-73, 75-76, 78-86, 89, 152 |
| `monitoring/status_files.py` | 25 | 5 | 80.0% | 15-16, 18, 24-25 |
| `analytics/validators.py` | 32 | 4 | 87.5% | 15-16, 49-50 |
| `analytics/views.py` | 97 | 11 | 88.7% | 63, 96-98, 105-107, 111-114 |
| `core/adapters/charting.py` | 9 | 1 | 88.9% | 14 |
| `accounts/throttles.py` | 47 | 5 | 89.4% | 49-51, 66-67 |

The biggest gap is `Category.clean()` in `expenses/models.py`. The API checks category cycles in the serializer
(tested), so this model-level copy only runs from the Django admin. The other files are small: the real-email
switch in `core/adapters/factory.py`, SMTP failure paths in `core/adapters/email.py`, admin-site helpers in
`audit/admin.py`, and out-of-range query parameters in `analytics`. The
[Branch Coverage Report](branch-coverage-report.md) explains each gap and its risk.

## All files

| File | Statements | Missed | Line coverage |
|:--|--:|--:|--:|
| `accounts/__init__.py` | 0 | 0 | n/a |
| `accounts/account_data.py` | 68 | 2 | 97.1% |
| `accounts/admin.py` | 10 | 0 | 100.0% |
| `accounts/apps.py` | 4 | 0 | 100.0% |
| `accounts/models.py` | 34 | 2 | 94.1% |
| `accounts/serializers.py` | 58 | 0 | 100.0% |
| `accounts/throttles.py` | 47 | 5 | 89.4% |
| `accounts/urls.py` | 3 | 0 | 100.0% |
| `accounts/views.py` | 95 | 0 | 100.0% |
| `alerts/__init__.py` | 0 | 0 | n/a |
| `alerts/adapters.py` | 22 | 1 | 95.5% |
| `alerts/admin.py` | 1 | 0 | 100.0% |
| `alerts/apps.py` | 6 | 0 | 100.0% |
| `alerts/models.py` | 21 | 1 | 95.2% |
| `alerts/serializers.py` | 8 | 0 | 100.0% |
| `alerts/services.py` | 44 | 3 | 93.2% |
| `alerts/signals.py` | 13 | 0 | 100.0% |
| `alerts/urls.py` | 5 | 0 | 100.0% |
| `alerts/views.py` | 49 | 3 | 93.9% |
| `analytics/__init__.py` | 0 | 0 | n/a |
| `analytics/apps.py` | 4 | 0 | 100.0% |
| `analytics/exporters.py` | 75 | 3 | 96.0% |
| `analytics/services.py` | 161 | 14 | 91.3% |
| `analytics/urls.py` | 3 | 0 | 100.0% |
| `analytics/validators.py` | 32 | 4 | 87.5% |
| `analytics/views.py` | 97 | 11 | 88.7% |
| `audit/__init__.py` | 0 | 0 | n/a |
| `audit/admin.py` | 13 | 3 | 76.9% |
| `audit/apps.py` | 4 | 0 | 100.0% |
| `audit/mixins.py` | 14 | 0 | 100.0% |
| `audit/models.py` | 27 | 1 | 96.3% |
| `audit/services.py` | 29 | 0 | 100.0% |
| `audit/urls.py` | 5 | 0 | 100.0% |
| `audit/views.py` | 64 | 0 | 100.0% |
| `budgets/__init__.py` | 0 | 0 | n/a |
| `budgets/admin.py` | 1 | 0 | 100.0% |
| `budgets/apps.py` | 3 | 0 | 100.0% |
| `budgets/management/__init__.py` | 0 | 0 | n/a |
| `budgets/management/commands/__init__.py` | 0 | 0 | n/a |
| `budgets/management/commands/rollover_budgets.py` | 55 | 2 | 96.4% |
| `budgets/models.py` | 36 | 2 | 94.4% |
| `budgets/permissions.py` | 26 | 2 | 92.3% |
| `budgets/serializers.py` | 98 | 1 | 99.0% |
| `budgets/services.py` | 15 | 0 | 100.0% |
| `budgets/urls.py` | 5 | 0 | 100.0% |
| `budgets/views.py` | 94 | 7 | 92.6% |
| `config/__init__.py` | 0 | 0 | n/a |
| `config/settings.py` | 93 | 5 | 94.6% |
| `config/urls.py` | 7 | 0 | 100.0% |
| `core/__init__.py` | 0 | 0 | n/a |
| `core/adapters/__init__.py` | 0 | 0 | n/a |
| `core/adapters/charting.py` | 9 | 1 | 88.9% |
| `core/adapters/email.py` | 31 | 7 | 77.4% |
| `core/adapters/factory.py` | 9 | 3 | 66.7% |
| `core/apps.py` | 4 | 0 | 100.0% |
| `core/authentication.py` | 10 | 0 | 100.0% |
| `core/charting_service.py` | 4 | 0 | 100.0% |
| `core/exceptions.py` | 33 | 1 | 97.0% |
| `core/request_id.py` | 52 | 5 | 90.4% |
| `core/security_headers.py` | 11 | 0 | 100.0% |
| `core/urls.py` | 3 | 0 | 100.0% |
| `core/views.py` | 10 | 0 | 100.0% |
| `expenses/__init__.py` | 0 | 0 | n/a |
| `expenses/apps.py` | 4 | 0 | 100.0% |
| `expenses/importers.py` | 97 | 2 | 97.9% |
| `expenses/management/__init__.py` | 0 | 0 | n/a |
| `expenses/management/commands/__init__.py` | 0 | 0 | n/a |
| `expenses/management/commands/materialize_recurring_expenses.py` | 47 | 1 | 97.9% |
| `expenses/management/commands/seed_data.py` | 64 | 0 | 100.0% |
| `expenses/management/commands/seed_synthetic_data.py` | 139 | 0 | 100.0% |
| `expenses/models.py` | 74 | 16 | 78.4% |
| `expenses/serializers.py` | 125 | 9 | 92.8% |
| `expenses/services.py` | 44 | 2 | 95.5% |
| `expenses/urls.py` | 7 | 0 | 100.0% |
| `expenses/views.py` | 220 | 10 | 95.5% |
| `monitoring/__init__.py` | 0 | 0 | n/a |
| `monitoring/apps.py` | 4 | 0 | 100.0% |
| `monitoring/logging.py` | 13 | 0 | 100.0% |
| `monitoring/metrics.py` | 60 | 5 | 91.7% |
| `monitoring/models.py` | 11 | 1 | 90.9% |
| `monitoring/services.py` | 20 | 1 | 95.0% |
| `monitoring/status_files.py` | 25 | 5 | 80.0% |
| `monitoring/urls.py` | 3 | 0 | 100.0% |
| `monitoring/views.py` | 23 | 0 | 100.0% |

## How to reproduce

```bash
cd backend
coverage run manage.py test
coverage report            # table in the terminal
coverage html              # browsable report in backend/htmlcov/
```

