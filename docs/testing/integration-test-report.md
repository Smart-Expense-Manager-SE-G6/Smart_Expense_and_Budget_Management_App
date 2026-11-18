# Integration Test Report

## Objective and scope
Assess existing interactions between frontend/backend, backend/database, authentication/protected APIs, expenses/categories/budgets, alerts, recurring rules, CSV imports, and report exports.

## Results

| ID | Interaction | Expected | Actual | Status |
|---|---|---|---|---|
| INT-01 | Frontend ↔ backend | UI calls return expected API responses | Selenium/API environment unavailable | NOT RUN |
| INT-02 | Backend ↔ database | CRUD persists and reads safely | Python/Docker unavailable | NOT RUN |
| INT-03 | Authentication ↔ protected APIs | Unauthenticated access rejected; session accepted | Not executed | NOT RUN |
| INT-04 | Expenses ↔ categories/budgets | Relationships and utilization work | Not executed | NOT RUN |
| INT-05 | Budget alerts | Threshold generates alert | Not executed | NOT RUN |
| INT-06 | Recurring rules | Rule lifecycle/materialization works | Not executed | NOT RUN |
| INT-07 | CSV imports | Valid/invalid rows handled | Not executed | NOT RUN |
| INT-08 | Reports/exports | PDF and Excel reflect data | Not executed | NOT RUN |

## Exact commands

```powershell
py -3 backend/manage.py test
npx.cmd newman run tests/postman_collection.json --env-var base_url=http://127.0.0.1:8000
pytest tests/e2e -v
```

No configuration, database, or production environment was changed. Missing coverage is recorded rather than inferred.
