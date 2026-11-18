# RTM Release Completeness Audit (#78)

This evidence index complements `docs/requirements/rtm.md` and is kept beside it so every release requirement family points to repository files that exist.

| Requirement family | Implementation evidence | Test/evidence files |
|:--|:--|:--|
| FR1–FR3 | `backend/accounts/`, `backend/budgets/`, shared-budget UI | `backend/accounts/test_auth_api.py`, `backend/budgets/test_shared.py`, `tests/e2e/test_journeys.py` |
| FR4–FR9 | `backend/expenses/`, expense and category UI | `backend/expenses/tests.py`, `backend/expenses/test_import.py`, `backend/expenses/test_recurring.py`, `tests/e2e/test_journeys.py` |
| FR10–FR12 | `backend/budgets/`, rollover command and UI | `backend/budgets/tests.py`, `backend/budgets/test_shared.py` |
| FR13–FR15 | `backend/analytics/`, dashboard and reports UI | `backend/analytics/tests.py` |
| FR16–FR18 | `backend/alerts/` and alert UI | `backend/alerts/tests.py`, `frontend/src/pages/AlertsPage.jsx` |
| FR19–FR20 | `backend/analytics/views.py`, `backend/analytics/exporters.py` | `backend/analytics/tests.py`, `tests/e2e/test_journeys.py` |
| FR21–FR22 | `backend/audit/`, backup/restore scripts | `backend/audit/test_api.py`, `scripts/rehearse_restore.sh` |
| NFR1–NFR3 | analytics queries, production deployment, PostgreSQL sessions | `docs/design/adr/0001-authentication-sessions.md`, `docs/operations/deployment.md`, `tests/postman_collection.json` |
| NFR4–NFR6 | authentication and security middleware | `backend/core/test_security.py`, `docs/testing/security-report.md` |
| NFR7–NFR8 | responsive/accessibility styles and labeled forms | `frontend/src/styles/`, `frontend/src/components/FormField.jsx` |
| NFR9–NFR14 | health, monitoring, backups, logging and privacy controls | `backend/monitoring/tests.py`, `scripts/`, `backend/core/tests.py` |

The OpenAPI contract is generated at `/api/v1/schema/` and validated by `backend/core/test_openapi.py`. The source RTM remains the requirement-by-requirement matrix; this page is its release evidence index.
