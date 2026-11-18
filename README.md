# Smart Expense and Budget Management Application

[![CI](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/workflows/ci.yml/badge.svg)](https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App/actions/workflows/ci.yml)

Team 6, PES University. React + Vite frontend, Django REST Framework API (`/api/v1`), PostgreSQL.

## Run it

Needs Docker with Compose (Docker Desktop on Windows/macOS, Docker Engine on Linux).

```bash
cp .env.example .env      # then set DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
```

| Service    | URL                                   |
|------------|---------------------------------------|
| Frontend   | http://localhost:5174                 |
| API        | http://localhost:8001/api/v1/health/  |
| Admin      | http://localhost:8001/admin/          |
| PostgreSQL | localhost:5433                        |

If your `.env` was copied before this change, add `http://localhost:5174` to `DJANGO_CSRF_TRUSTED_ORIGINS`, otherwise sign-in fails with "CSRF check failed".

The frontend proxies `/api` to the backend, so in React code always call relative URLs like `fetch('/api/v1/...')`.

## Common commands

```bash
docker compose exec backend python manage.py test            # backend tests
docker compose exec backend python manage.py makemigrations  # after model changes
docker compose exec backend python manage.py createsuperuser
docker compose down -v                                       # stop and wipe the database
docker compose up --build -V                                 # after pulling new npm/pip dependencies
```

## Layout

```
backend/         Django project (config/) and apps; one app per module
frontend/        React + Vite app
tests/           Selenium end-to-end journeys, Postman collection, accessibility audit
scripts/         backup, restore and off-site copy scripts
deploy/          production Dockerfiles, Caddy config, demo and smoke-test scripts
deliverables/    the approved course documents (proposal, requirements, SRS, SASD, test plan, use-case diagram)
docs/            everything we wrote about the system: start at docs/README.md
docker-compose.yml, docker-compose.prod.yml, .env.example, .env.prod.example
```

- **Course deliverables** (final, never edited): [`deliverables/`](deliverables/README.md)
- **Project documentation** (traceability, design decisions, testing, operations, user guide): [`docs/`](docs/README.md)

## API conventions (read before adding an endpoint)

- **Auth is on by default.** Every endpoint requires a logged-in session. Public endpoints must say `permission_classes = [AllowAny]`. See `docs/design/adr/0001-authentication-sessions.md`.
- **Errors:** just raise DRF exceptions (`serializer.is_valid(raise_exception=True)`, `NotFound(...)`, `PermissionDenied(...)`). They are converted to the SASD 4.4 envelope automatically:
  ```json
  {"error": {"code": "required", "message": "This field is required.", "field": "amount", "request_id": "3f2a..."}}
  ```
  Unhandled exceptions become a `500` with code `server_error`; the details only go to the log.
- **Users:** reference the user model as `settings.AUTH_USER_MODEL` in ForeignKeys. Users sign in with email; `user.timezone` holds their IANA time zone.
- **Logging:** use `logging.getLogger(__name__)`. Every line automatically carries `request_id`, which is also returned in the `X-Request-ID` response header.
- **Audit (FR21), required for every expense and budget write.** The change and its audit row are saved in one transaction, or neither is.
  - ViewSets: add the mixin and you're done.
    ```python
    from audit.mixins import AuditedModelViewSetMixin

    class ExpenseViewSet(AuditedModelViewSetMixin, viewsets.ModelViewSet): ...
    ```
  - Custom code, including soft delete (D4):
    ```python
    from audit.services import audited

    with audited(request.user, expense):
        expense.is_deleted = True
        expense.save()
    ```
  - Audit rows are append-only. Passwords are never recorded.
- **Frontend:** call relative URLs (`/api/v1/...`) and send the `X-CSRFToken` header (value of the `csrftoken` cookie) on POST, PUT, PATCH and DELETE.

### Receipts (FR5)

Authenticated owners can attach, retrieve, and delete a private receipt:

```text
POST   /api/v1/expenses/<id>/receipt/
GET    /api/v1/expenses/<id>/receipt/
DELETE /api/v1/expenses/<id>/receipt/
```

Receipts accept JPEG, PNG, and PDF files up to 5 MiB by default. The limit can
be changed with `RECEIPT_MAX_SIZE_BYTES`. Files are stored under the private
`MEDIA_ROOT` and are streamed only after the expense ownership check. Receipt
replacement is not supported; delete the existing receipt before uploading a
new one.
### Categories (FR8)

Authenticated users can list global defaults and their own active categories:

```text
GET    /api/v1/categories/
POST   /api/v1/categories/
GET    /api/v1/categories/<id>/
PATCH  /api/v1/categories/<id>/
DELETE /api/v1/categories/<id>/
```

Category creation accepts an optional `parent` for subcategories. Global
categories cannot be changed or deleted. Category responses retain the
`parent` identifier and include active, visible direct children in `children`.
Names remain unique per owner (case-insensitive), and a parent must be active
and visible to the requesting user. Deleting a custom category safely
deactivates it so existing expenses continue to reference it; a category with
active subcategories must have those subcategories reassigned or deactivated
first. Creating a category with the same name as a deleted one restores it.

### Category suggestions (FR9)

While entering an expense description, authenticated users can request advisory
suggestions:

```text
GET /api/v1/categories/suggestions/?description=Lunch%20at%20a%20cafe
```

Example response:

```json
{
  "suggestions": [
    {"id": 2, "name": "Food"}
  ]
}
```

Suggestions use hard-coded, deterministic keyword rules and return only active
global categories. The endpoint never assigns a category or changes an
expense; the user must explicitly select a suggestion. Empty or unmatched
descriptions return `{"suggestions": []}`. Custom categories are not suggested.

### Account settings (FR2, NFR14)

```text
PATCH  /api/v1/me/            {"email_alerts": false}  stop alert emails (in-app alerts continue)
POST   /api/v1/me/password/   {"current_password": "...", "new_password": "..."}
GET    /api/v1/me/export/     ZIP of everything stored about you, receipts included
DELETE /api/v1/me/            {"password": "..."}  delete the account and all its data
```

- Changing the password keeps the current session and signs out every other
  device (their sessions carry the old password hash). It is audited without
  the password.
- The export contains `profile.json`, `expenses.csv` (deleted expenses marked),
  your categories, recurring rules, budgets (owned and shared with you), alerts,
  your audit history and your receipt files.
- Deleting an account removes the user's expenses, receipt files, categories,
  recurring rules, budgets (shared budgets they own disappear for members too),
  memberships, alerts and their own audit history, then records one anonymous
  "account deleted" audit entry. The email can be registered again.
- `email_alerts` is the user's consent to sending alert emails through the
  external email provider (NFR14); it defaults to on.
- In the app, all of this is on the Profile page.

### Audit trail (FR21)

Every create, change and delete of an expense, category, recurring rule, budget,
budget membership or profile writes an append-only audit entry in the same
transaction. Read it with:

```text
GET /api/v1/audit/                                  everything you may see, newest first (paginated)
GET /api/v1/audit/?entity=expense&entity_id=12      one record's history
```

- `entity` is `expense`, `category`, `recurring_rule`, `budget`, `budget_member` or `profile`.
- Each entry has `action`, `actor_email` (null when the system made the change,
  e.g. the scheduler), `changes` (`field`, `old`, `new`), `request_id` and `created_at`.
- You see the history of your own records. Owners and admins of a shared budget
  also see that budget's changes and its membership changes. History stays
  visible after a record is deleted.
- Read-only: there is no way to change or delete an entry through the API.
- In the app, the clock icon on an expense row or a budget card opens its history.

## Backups (FR22, NFR10)

Backups cover the database and uploaded receipts (`backend/private_media`).
The scripts run in a `postgres:16-alpine` container, so nothing extra needs
installing on your machine.

**Scheduled (NFR10):** `docker compose up` also starts the `backup` service,
which backs up daily at `BACKUP_SCHEDULE` (cron, UTC; default `0 2 * * *`,
07:30 IST). Because laptops are often off at that time, it also takes a backup
on start whenever the newest one is more than 24 hours old. Check it with
`docker compose logs backup`.

**Healthcheck:** Docker marks the backup service as healthy when `backups/LATEST` has been updated within the last 25 hours. If the marker is older, the service is marked unhealthy.

**By hand:**

```bash
docker compose run --rm backup /scripts/backup.sh                      # take a backup
docker compose run --rm backup /scripts/rehearse_restore.sh            # TC-Backup-01
docker compose run --rm backup /scripts/rehearse_restore.sh <backup>   # rehearse an older one

docker compose stop backend                                            # full restore
docker compose run --rm backup /scripts/restore.sh <backup>
docker compose start backend
```

- Each backup is a folder in `backups/` (git-ignored) named by its UTC time, e.g.
  `20261031T020000Z/`, holding `db.dump`, `media.tar.gz`, table row counts and
  `SHA256SUMS`. `backups/LATEST` names the newest regular backup (never a
  `*-pre-restore` safety copy). The newest `BACKUP_KEEP` (default 7) are kept.
- **Rehearsal (TC-Backup-01)** restores into a scratch database, never the live
  one, then checks checksums, every table's row count and every receipt file.
  It exits non-zero on any mismatch.
- **Restore** asks you to type the database name (or pass `--yes`), takes a
  `*-pre-restore` safety backup first so it can be undone, then replaces the
  database and all receipts. Restore with the same code version (migrations)
  the backup was taken with.

## Monitoring and uptime (S3-17, NFR9, NFR12)

The public liveness probe is `GET /api/v1/health/`. It returns HTTP 200 only
when the backend can query PostgreSQL. Against the public production HTTPS URL:

1. In UptimeRobot, add an **HTTP(s)** monitor for
   `https://<production-host>/api/v1/health/`; in Better Stack, create an
   **HTTP uptime check** for the same URL.
2. Set the expected response to HTTP 200, choose an interval of one minute
   where available (never more than five minutes), and enable email
   notifications to the operations contact. Confirm the plan supports the
   interval and alert policy needed for the five-minute target.
3. Use the provider's test/incident function and verify the email reaches the
   contact. Also temporarily stop the backend in a non-production environment
   to verify the check detects an outage.

The public host and monitor account must be supplied by the production
deployment; S3-10 has not yet delivered that deployment.

Set `MONITORING_ALERT_EMAIL` to the operations mailbox for in-app 5xx rate
alerts. These alerts use the existing Django SMTP configuration
(`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL`). Set `ENABLE_REAL_EMAIL=true` when
using the real email adapter; the stub adapter intentionally reports success.
The 5xx alert defaults are a 5-minute rolling window, at least 10 requests,
5% failing requests, and a 15-minute duplicate-alert cooldown. Tune with
`ERROR_RATE_WINDOW_SECONDS`, `ERROR_RATE_MIN_REQUESTS`,
`ERROR_RATE_THRESHOLD_PERCENT`, and `ERROR_ALERT_COOLDOWN_SECONDS`.
`SLOW_REQUEST_THRESHOLD_MS` defaults to 2,000 ms.

Application logs are newline-delimited JSON in `logs/application.log`;
HTTP 5xx responses and unhandled errors are also written to
`logs/error.log`. Both rotate at 10 MiB and retain five files by default.
Configure `APP_LOG_MAX_BYTES` and `APP_LOG_BACKUP_COUNT` to tune retention.
Every record includes a request ID. Search from the repository root with, for
example, `Select-String -Path .\logs\*.log* -Pattern '"request_id":"abc-123"'`
(PowerShell) or `grep -h '"request_id":"abc-123"' logs/*.log*` (Linux/macOS).
In Compose, the `logs/` directory is mounted for persistence.

The staff-only **Monitoring** page (`/monitoring`) shows backend and database
checks, scheduler and backup job status, rolling 5xx/slow-request counts, and
the latest recorded email delivery failures (recipient local parts are masked).
Job status is shared with the containers through the `monitoring-state` Docker
volume; a missing status is shown as unknown and an overdue status as stale.
Scheduler data becomes fresh after its first run; backup data after its first
backup. Docker's existing backup healthcheck remains in place.
The rolling request counters and duplicate-alert cooldown are process-local;
for a future multi-worker deployment, configure a shared metrics/cache backend
before treating the displayed error rate as an instance-wide aggregate.

The S3-10 production HTTPS deployment and public monitoring account are not
configured by this change. Create the external monitor and notification
contact in the chosen provider, set the alert mailbox and SMTP credentials in
the deployment environment, then test both the monitor notification and an
in-app 5xx alert.

### Recurring expenses (FR6)

A recurring rule creates an ordinary expense on each due date (rent every month,
a subscription every year):

```text
GET    /api/v1/recurring-rules/        list your rules, with next_run_date
POST   /api/v1/recurring-rules/        {"amount": "15000.00", "frequency": "monthly", "start_date": "2026-01-31", ...}
PATCH  /api/v1/recurring-rules/<id>/   edit; {"is_active": false} pauses, {"is_active": true} resumes
DELETE /api/v1/recurring-rules/<id>/   ends the rule (expenses already created are kept)
```

- `frequency` is `daily`, `weekly`, `monthly` or `yearly`. Monthly and yearly
  rules keep the start date's day and clamp to the month end: a rule starting
  31 Jan runs on 28 Feb, then 31 Mar.
- The `budget-scheduler` service runs `manage.py materialize_recurring_expenses`
  daily. It catches up on missed days, never creates the same date twice, and
  uses each owner's time zone for "today". Creating or editing a rule also
  creates any expenses already due straight away.
- Generated expenses link to their rule (`recurring_rule`), count towards
  budgets, raise alerts and are audited like any other expense.

### Shared budgets (FR3)

A budget owner can share a budget with other registered users:

```text
GET    /api/v1/budgets/<id>/members/              list members
POST   /api/v1/budgets/<id>/members/              {"email": "...", "role": "member" | "admin"}
PATCH  /api/v1/budgets/<id>/members/<member_id>/  {"role": "admin"}
DELETE /api/v1/budgets/<id>/members/<member_id>/
GET    /api/v1/budgets/<id>/expenses/             expenses counted by the budget (paginated)
```

| Role   | View budget, utilization, expenses | Edit settings, manage members | Delete budget |
|--------|:---:|:---:|:---:|
| owner  | yes | yes | yes |
| admin  | yes | yes | no  |
| member | yes | no (may only leave) | no |

- Members add expenses as usual (`POST /api/v1/expenses/`). Their expenses count
  towards the shared budget's utilization, threshold alerts and rollover.
- Users with no role get `404`; members trying an admin action get `403`.
- A shared budget can only use a default category (or none), because members
  cannot use the owner's custom categories.
- Every membership change writes an audit entry (FR21). Rollover copies the
  members into the next period.
- Budget responses include `owner_email`, `role` (your role on that budget) and `member_count`.
- In the app, the people icon on a budget card opens the sharing dialog: owners and admins add people by email,
  change roles and remove members; members see who shares the budget and its recent spending, and can leave.

## Security (NFR4–NFR6, STP 5.1)

The security checks the test plan asks for, how each was done and the results
(including the OWASP ZAP scan and dependency audits) are in
[`docs/testing/security-report.md`](docs/testing/security-report.md). The automated part runs in CI:
`python manage.py test core.test_security`.

## Deviations from the project documents

The SRS, SASD, STP and other project documents are final. Every place the code knowingly differs from them, and why, is in [`docs/requirements/deviations.md`](docs/requirements/deviations.md).

## Deploying to production (NFR13)

`docker-compose.prod.yml` runs the app on any Linux VM: gunicorn for the API, the
built React app behind Caddy (automatic HTTPS, security headers), PostgreSQL,
the scheduler and daily backups. Step-by-step guide, encryption at rest and
verification: [`docs/operations/deployment.md`](docs/operations/deployment.md). Encrypted off-site backups and
how to recover from losing the server: [`docs/operations/recovery-runbook.md`](docs/operations/recovery-runbook.md). Check a deployment with
`deploy/smoke_test.sh https://<domain>`. For the demo, `deploy/local-demo.sh` runs the same
production stack on https://localhost.

## Rules

- No secrets in code. Everything comes from `.env`, which is git-ignored.
- Money is stored as `Decimal`, never float. Timestamps are UTC.

## Sprint 1 – Testing & Verification

### CI/CD pipeline (S3-11)

Every pull request and every push to `main` runs `.github/workflows/ci.yml`:

| Job | What it checks |
|:--|:--|
| Backend tests and coverage | `manage.py check`, no missing migrations, the full test suite on PostgreSQL 16, line and branch coverage (fails under 80%) |
| Frontend lint and build | `npm run lint` and `npm run build` |
| API tests (Postman) | `tests/postman_collection.json` with newman against a running server |
| Deploy to staging and smoke test (CD) | After all three pass: builds the production images, deploys the full production stack (gunicorn, Caddy HTTPS, PostgreSQL, scheduler, backups) on the runner, runs `deploy/smoke_test.sh` and a restore rehearsal against it. On `main` the tested images are then published to GitHub Container Registry |

The coverage table is on each run's summary page, and the full HTML report is a
downloadable artifact (`backend-coverage`). The same coverage settings work
locally:

```bash
cd backend
coverage run manage.py test
coverage report            # line + branch, fails under 80%
```

The separate `Backup and Restore Tests` workflow runs TC-Backup-01 on every pull request.

So every commit on `main` is a deployed, smoke-tested release (continuous delivery):

```text
test (backend, frontend, API) -> deploy to staging on the runner -> smoke test -> publish images
```

Run the newest tested release with `deploy/local-demo.sh release`. Tagging a commit
(`git tag v1.0 && git push origin v1.0`) runs `.github/workflows/release.yml`, which gives that
commit's tested images the version tag and creates a GitHub Release. Nothing is rebuilt.

### Running the checks

With the stack running (`docker compose up --build`):

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test
npx newman run tests/postman_collection.json      # API smoke test, base_url http://localhost:8001
npm --prefix frontend test                         # monitoring status presentation tests
```

Outside Docker, run `python manage.py test` from `backend/` with the `POSTGRES_*` values in `.env`
(or `USE_SQLITE=true` for a quick local run).

### Latest result

**157 backend tests pass on PostgreSQL in Docker (2026-11-12).** System check clean, no missing
migrations, Postman collection passing against the running stack.

### Functionality covered by tests

- Registration, login, logout, session expiry, CSRF, rate limits and lockout
- Profile editing and audit trail entries for every expense, category and budget change
- Expense CRUD, soft deletion, filtering, sorting, pagination and per-user isolation
- Receipt upload, download, deletion and access protection
- Default, custom and restored categories with hierarchy checks
- Budget validation (owner, active category, limit, period dates, duplicates), utilisation and rollover
- 80% and 100% threshold alerts, de-duplication, alert API and email after commit
- Analytics summary and category breakdown, date-range cap (ADR 0002)
- Health endpoint, error envelope and request-id logging

### Test data

```bash
python manage.py seed_data --count 10000            # one user with 10,000 expenses (NFR1); prints a generated password
python manage.py seed_synthetic_data --dry-run      # report what would be created
python manage.py seed_synthetic_data                # 5 users with their own categories, expenses, budgets and alerts
```

### Verification notes

- API endpoints requiring authentication must be tested with a signed-in session and the `X-CSRFToken` header.
- The complete user flow and remaining requirements must be checked against the project's SRS, SASD and Test Plan before declaring Sprint 1 fully complete.
