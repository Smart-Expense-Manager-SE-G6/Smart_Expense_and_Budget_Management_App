# Smart Expense and Budget Management — Release Notes

## Release 1.0 — 2026-11-17

### Included

- Session-authenticated Django REST API with an OpenAPI 3 schema at `/api/v1/schema/` and interactive documentation at `/api/v1/schema/docs/`.
- Expense management with categories, merchant/notes, receipt storage, recurring rules, CSV import and audit history.
- Budgets with weekly/monthly periods, rollover mode, sharing, member roles and threshold alerts.
- Explainable anomaly alerts based on the previous five same-category expenses, documented in ADR-0004.
- Analytics, bounded one-year reports, PDF/XLSX exports, account settings and data-protection controls.
- Production Docker Compose deployment, health/monitoring endpoints, backups and CI regression checks.

### Verification evidence

- Requirements traceability: [`docs/rtm.md`](rtm.md)
- Model reference: [`docs/data-dictionary.md`](data-dictionary.md)
- API schema test: `backend/core/test_openapi.py`
- Test plan deviations and decisions: [`docs/deviations.md`](deviations.md) and [`docs/adr/`](adr/)
- User workflow: [`docs/user-guide.md`](user-guide.md)
