# Branch Coverage Report

**Evidence:** CI run [#44234445329](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/runs/44234445329) on `main` at `69426f5`, 18 Nov 2026 (browsable report: [`reports/coverage/index.html`](reports/coverage/index.html); raw data: [`reports/coverage/coverage.json`](reports/coverage/coverage.json))
**Tool:** coverage.py 7.6.10 with `branch = True`

Line coverage shows that a line ran. **Branch coverage** shows that *both* outcomes of every decision ran: the `if`
and the `else`, and a loop that runs as well as one that does not. It is the stricter measure, because a line can be
fully covered while one of its branches never happens.

## Result

| Measure | Covered | Total | % |
|:--|--:|--:|--:|
| **Branches** | 496 | 578 | **85.8%** |
| Partially covered decisions (one outcome never taken) | | 64 | |
| Lines, for comparison | 2,464 | 2,605 | 94.6% |

## By module

| Module | Branches | Covered | Branch coverage | Partial decisions |
|:--|--:|--:|--:|--:|
| `accounts` | 28 | 27 | 96.4% | 1 |
| `alerts` | 38 | 31 | 81.6% | 7 |
| `analytics` | 98 | 76 | 77.6% | 20 |
| `audit` | 24 | 24 | 100.0% | 0 |
| `budgets` | 70 | 65 | 92.9% | 5 |
| `config` | 10 | 6 | 60.0% | 4 |
| `core` | 22 | 17 | 77.3% | 3 |
| `expenses` | 268 | 234 | 87.3% | 20 |
| `monitoring` | 20 | 16 | 80.0% | 4 |
| **Total** | **578** | **496** | **85.8%** | **64** |

## Branches not taken

Each entry `a -> b` means the decision on line `a` never jumped to line `b` during the tests (`a -> exit` means it
never left the function that way).

| File | Branch coverage | Missing branches |
|:--|--:|:--|
| `core/adapters/factory.py` | 0.0% | 10 -> 11, 10 -> 13 |
| `expenses/models.py` | 0.0% | 72 -> 73, 72 -> 75, 75 -> 76, 75 -> 78, 80 -> exit, 80 -> 81, 81 -> 82, 81 -> 83, 84 -> 85, 84 -> 86 |
| `core/adapters/email.py` | 50.0% | 51 -> 52, 71 -> 74 |
| `monitoring/services.py` | 50.0% | 11 -> 12 |
| `config/settings.py` | 60.0% | 22 -> 23, 94 -> 95, 185 -> 186, 249 -> 275 |
| `analytics/services.py` | 69.6% | 11 -> 12, 13 -> 14, 109 -> 112, 158 -> 159, 161 -> 162, 170 -> 171, 187 -> 191, 219 -> 221, 221 -> 222, 221 -> 224, 275 -> 276, 333 -> 335, 392 -> 395, 398 -> 401 |
| `accounts/models.py` | 75.0% | 17 -> 18 |
| `alerts/adapters.py` | 75.0% | 33 -> 34 |
| `alerts/views.py` | 75.0% | 20 -> 21, 28 -> 29, 30 -> 31 |
| `monitoring/metrics.py` | 75.0% | 19 -> 20, 113 -> 114 |
| `monitoring/status_files.py` | 75.0% | 17 -> 18 |
| `analytics/exporters.py` | 80.0% | 13 -> 14, 72 -> 73, 92 -> 93, 103 -> 106 |
| `expenses/serializers.py` | 82.0% | 46 -> 47, 67 -> 68, 71 -> 72, 77 -> 78, 85 -> 86, 94 -> 95, 162 -> 163, 177 -> 178, 222 -> 223 |
| `alerts/services.py` | 83.3% | 22 -> 23, 66 -> 67, 97 -> 98 |
| `analytics/views.py` | 83.3% | 62 -> 63, 95 -> 96, 104 -> 105, 110 -> 111 |
| `budgets/management/commands/rollover_budgets.py` | 83.3% | 29 -> 30, 31 -> 35 |
| `budgets/permissions.py` | 83.3% | 25 -> 26, 39 -> 40 |
| `expenses/services.py` | 85.0% | 54 -> 55, 84 -> 85, 97 -> 96 |
| `expenses/views.py` | 86.8% | 179 -> 180, 181 -> 183, 183 -> 184, 183 -> 185, 234 -> 235, 235 -> 236, 235 -> 237, 269 -> 270, 277 -> 278 |
| `core/exceptions.py` | 90.0% | 29 -> 33 |
| `expenses/management/commands/materialize_recurring_expenses.py` | 92.9% | 58 -> 59 |
| `expenses/management/commands/seed_synthetic_data.py` | 96.3% | 298 -> 305, 310 -> 293 |
| `budgets/serializers.py` | 97.1% | 87 -> 88 |

**16 files that contain decisions have every branch covered.**

## Reading the gaps

The largest gaps, and why they are not covered:

| Gap | Why it is not reached by the tests | Risk |
|:--|:--|:--|
| `expenses/models.py` `Category.clean()` (all 10 branches) | The API checks category cycles in the serializer and the restore view (`expenses/serializers.py`, `expenses/views.py`), and those checks are tested. The model-level copy only runs from the Django admin site. | Low: duplicate of a tested check |
| `config/settings.py` (4 branches) | Settings are read once at start-up with the test configuration, so the other side of each switch (missing required variable, `USE_SQLITE`, `NUM_PROXIES`, file logging) never runs in the suite. The production side is exercised by the staging deployment in the same CI run. | Low |
| `core/adapters/factory.py` (2 branches) | Tests build the email adapters directly; the `ENABLE_REAL_EMAIL` switch that picks one is not called. | Low |
| `analytics/services.py` (14 branches) | Forecasts for a past or future month (only the current month is tested), and empty-input edges of the helpers. | Medium: the next tests to add |
| `analytics/views.py` (4 branches) | Out-of-range `year` and `months` query parameters (400 responses). | Low: same pattern is tested for the 366-day report cap |

Every authentication, ownership and role decision is covered on both sides (allowed and refused), by
`core/test_security.py` and `budgets/test_shared.py`. The audit module has 100% branch coverage.

## How to reproduce

```bash
cd backend
coverage run manage.py test      # .coveragerc sets branch = True
coverage report --show-missing   # Branch, BrPart and Missing columns
```

