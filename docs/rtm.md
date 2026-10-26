# Requirements Traceability Matrix (RTM)

- **Project:** Smart Expense & Budget Management Application
- **Version:** 1.0 (Sprint 1 Baseline)
- **QA Lead / Owner:** Shashank A (`PES2UG24CS461`)
- **Traceability Source:** SRS v1.0, SASD v1.0, STP v1.0

---

## 1. Functional Requirements (FR1 – FR22)

| Req ID | Requirement Description | Module Owner | Design Reference (SASD) | Target Code / Files | Test Case ID (STP) | Sprint 1 Status |
|:---|:---|:---|:---|:---|:---|:---|
| **FR1** | User registration and login (email/pwd, bcrypt) | Shriram | Sec 3.4, 4.3, Fig 4.1 | `accounts/views.py`, `accounts/serializers.py` | `TC-Auth-01`, `TC-Auth-02` | In Progress (#13) |
| **FR2** | Profile update and account settings | Shriram | Sec 3.4, 4.3 | `accounts/views.py` | `TC-Auth-03` | In Progress (#13) |
| **FR3** | Shared budget and role-based access (admin/member) | Shriram | Sec 3.4, 3.9, 4.3 | `budgets/models.py`, `budgets/permissions.py` | `TC-Shared-01` | Sprint 2 |
| **FR4** | Add, edit, view, delete expense entries (soft delete) | Shreya | Sec 3.4, 4.1 (D1, D4) | `expenses/models.py`, `expenses/views.py` | `TC-Exp-01`, `TC-Exp-02` | In Progress (#1, #2, #3) |
| **FR5** | Attach receipt/image to expense (secured store) | Shreya | Sec 3.4, 4.1 (D6) | `expenses/models.py`, `expenses/views.py` | `TC-Exp-03` | Todo (#5) |
| **FR6** | Recurring expense entries (rules materialization) | Shreya / Shashwath | Sec 3.4, 4.1 (D3) | `expenses/models.py`, `scheduler/tasks.py` | `TC-Exp-04` | Sprint 2 |
| **FR7** | Bulk import of expenses via CSV (per-row errors) | Shreya | Sec 4.3, OI-7 | `expenses/services.py`, `expenses/views.py` | `TC-Import-01` | Sprint 2 |
| **FR8** | Default categories & custom user categories/subcategories | Shreya | Sec 3.4, 4.1 | `categories/models.py`, `categories/views.py`| `TC-Cat-01` | Todo (#4) |
| **FR9** | Rule-based category auto-suggestion | Shreya | Sec 3.4, 4.1 (D8) | `categories/services.py` | `TC-Cat-02` | Sprint 2 |
| **FR10** | Set monthly/weekly budgets overall and per category | Shashwath | Sec 3.4, 4.1 (D2) | `budgets/models.py`, `budgets/views.py` | `TC-Bud-01` | Todo (Sprint 1) |
| **FR11** | Track budget utilization in real-time | Shashwath | Sec 3.4, 4.3 | `budgets/services.py`, `budgets/views.py` | `TC-Bud-02` | Todo (Sprint 1) |
| **FR12** | Budget rollover or reset at period end | Shashwath | Sec 3.4, 4.1 (D2) | `budgets/services.py`, `scheduler/tasks.py` | `TC-Bud-03` | Sprint 2 |
| **FR13** | Visual analytics (category, period, trend charts) | Shashank | Sec 3.4, 4.3 | `analytics/views.py`, `frontend/src/pages/Dashboard.jsx` | `TC-Analytics-01` | Planned (#21, #22) |
| **FR14** | Predictive insights (projected month-end spend) | Shashank | Sec 3.4, 4.3 | `analytics/services.py` | `TC-Analytics-02` | Sprint 2 |
| **FR15** | Spending comparison across months/years | Shashank | Sec 3.4, 4.3 | `analytics/views.py` | `TC-Analytics-03` | Sprint 2 |
| **FR16** | Threshold alerts at 80% and 100% (de-duplicated) | Shashwath | Sec 3.4, 4.1 (D5) | `alerts/models.py`, `alerts/services.py` | `TC-Alert-01` | Todo (Sprint 1) |
| **FR17** | Anomaly notification (spike detection) | Shashwath | Sec 3.4, 4.3, OI-6 | `alerts/services.py` | `TC-Alert-02` | Sprint 2 |
| **FR18** | In-app and email alert delivery (adapter) | Shashwath | Sec 3.4, 4.3, R4 | `alerts/adapters.py`, `alerts/views.py` | `TC-Alert-03` | Sprint 2 |
| **FR19** | Custom date range reports (1-year cap) | Shashank | Sec 3.4, 4.3, OI-3 | `reports/views.py`, `reports/validators.py` | `TC-Report-01` | Sprint 2 |
| **FR20** | PDF & Excel report export with summary/breakdowns | Shashank | Sec 3.4, 4.3, R4 | `reports/services.py`, `reports/adapters.py` | `TC-Report-02` | Sprint 2 |
| **FR21** | Audit trail of edits (written in same transaction) | Shriram | Sec 3.4, 3.5, 4.1 | `audit/models.py`, `audit/services.py` | `TC-Audit-01` | Done (#14) |
| **FR22** | Data backup and restore rehearsal | Shriram / Shashwath | Sec 3.4, 3.6, R6 | `scripts/backup.sh`, `scripts/restore.sh` | `TC-Backup-01` | Sprint 2 |

---

## 2. Non-Functional Requirements (NFR1 – NFR14)

| Req ID | Requirement Description | Target Metric | Design / Verification | Owner | Sprint 1 Status |
|:---|:---|:---|:---|:---|:---|
| **NFR1** | Dashboard & analytics load speed | <= 2–3s for 10,000 transactions | Composite DB indexes on `(user, date)`, `(user, category)`; seed script verification (`TC-Perf-01`) | Shashank | Planned (#20, #21) |
| **NFR2** | Report generation completion speed | <= 5s for 1-year date range | Date-range cap (OI-3); SQL aggregations | Shashank | Sprint 2 |
| **NFR3** | Horizontal scalability | Stateless app tier | Shared PostgreSQL session store; stateless REST API | Team 6 | Design verified |
| **NFR4** | Sensitive data encryption | Passwords hashed; TLS | `bcrypt` hashing; TLS/HTTPS; secure file root | Shriram | Verified (ADR 0001) |
| **NFR5** | Authentication & token expiry | Session expiry on logout & 30m idle | Django sessions in HttpOnly cookies; 401 on expired session | Shriram | Verified (ADR 0001, #12) |
| **NFR6** | Protection against SQLi, XSS, CSRF | Zero high/critical vulnerabilities | Django ORM parameterized queries; React auto-escaping; CSRF header | Shriram | Active in middleware |
| **NFR7** | Responsive UI | Mobile, tablet, desktop | Responsive CSS layouts without frameworks | Team 6 | Active in frontend |
| **NFR8** | Accessibility | WCAG basics (labels, contrast) | Form labels, keyboard focus, table fallbacks for charts | Team 6 | Enforced in UI |
| **NFR9** | Uptime | 99% uptime target | Health endpoint `/api/v1/health/` | Shriram | Done (#10) |
| **NFR10**| Automated backups | Daily scheduled backup | Cron job / scheduler script | Shriram / Shashwath | Sprint 2 |
| **NFR11**| Modular architecture | MVC pattern; loose coupling | Modular monolith with independent Django apps | Team 6 | Enforced |
| **NFR12**| Logging with Request ID | Request ID on every log & response | `RequestIdMiddleware` + standard logger | Shriram | Done (#12) |
| **NFR13**| Containerization | One-command start | `docker compose up --build` | Shriram | Done (#10) |
| **NFR14**| Data privacy compliance | Financial data isolated | Ownership checks on every endpoint; no 3rd-party data leaks | Team 6 | Enforced |
