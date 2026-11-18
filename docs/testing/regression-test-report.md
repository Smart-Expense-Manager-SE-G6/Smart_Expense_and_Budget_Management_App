# Regression Test Report

## Objective and scope
Execute available regression checks for authentication, expenses, categories, budgets, shared budgets, recurring rules, CSV import, reports/exports, navigation, and responsive layouts.

## Results

| ID | Area | Expected | Actual | Status |
|---|---|---|---|---|
| REG-01 | Frontend monitoring regression | Existing tests pass | 2 passed | PASS |
| REG-02 | Authentication and protected navigation | Regression suite passes | Selenium unavailable | NOT RUN |
| REG-03 | Expenses/categories/budgets | Regression suite passes | Backend unavailable | NOT RUN |
| REG-04 | Shared budgets/recurring rules | Regression suite passes | Backend/E2E unavailable | NOT RUN |
| REG-05 | CSV import and exports | Regression suite passes | API/E2E unavailable | NOT RUN |
| REG-06 | Navigation/responsive layouts | Browser checks pass | No browser suite executed | NOT RUN |

## Exact commands

```powershell
npm.cmd test --prefix frontend
py -3 backend/manage.py test
pytest tests/e2e -v
```

## Summary

Executed: 1 frontend regression group, PASS. Not run: 5 groups. No application source, tests, configuration, database, branch, or remote repository were modified.
