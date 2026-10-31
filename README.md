# Smart Expense and Budget Management Application

Team 6, PES University. React + Vite frontend, Django REST Framework API (`/api/v1`), PostgreSQL.

## Run it

Needs Docker with Compose (Docker Desktop on Windows/macOS, Docker Engine on Linux).

```bash
cp .env.example .env      # then set DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
```

| Service  | URL                                   |
|----------|---------------------------------------|
| Frontend | http://localhost:5173                 |
| API      | http://localhost:8000/api/v1/health/  |
| Admin    | http://localhost:8000/admin/          |

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
backend/    Django project (config/) and apps; one app per module
frontend/   React + Vite app
docker-compose.yml, .env.example
```

## API conventions (read before adding an endpoint)

- **Auth is on by default.** Every endpoint requires a logged-in session. Public endpoints must say `permission_classes = [AllowAny]`. See `docs/adr/0001-authentication-sessions.md`.
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
categories cannot be changed or deleted. Deleting a custom category safely
deactivates it so existing expenses continue to reference it.

## Backups (FR22)

Backups cover the database and uploaded receipts (`backend/private_media`).
The scripts run in a `postgres:16-alpine` container, so nothing extra needs
installing on your machine.

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
  `SHA256SUMS`. `backups/LATEST` names the newest one. The newest
  `BACKUP_KEEP` (default 7) are kept.
- **Rehearsal (TC-Backup-01)** restores into a scratch database, never the live
  one, then checks checksums, every table's row count and every receipt file.
  It exits non-zero on any mismatch.
- **Restore** asks you to type the database name (or pass `--yes`), takes a
  `*-pre-restore` safety backup first so it can be undone, then replaces the
  database and all receipts. Restore with the same code version (migrations)
  the backup was taken with.

## Rules

- No secrets in code. Everything comes from `.env`, which is git-ignored.
- Money is stored as `Decimal`, never float. Timestamps are UTC.
## Sprint 1 – Backend Testing & Verification

### Testing Status

**Automated backend tests: 70/70 passed**

The backend has been tested using Django's automated test suite. The following checks have been completed successfully:

- [x] Django system check (`python manage.py check`)
- [x] Database migrations applied successfully
- [x] Automated test suite — 70 tests passed
- [x] PostgreSQL database setup and connectivity verified
- [x] Synthetic test data seeded successfully
- [x] Synthetic data dry run completed without database changes

### Functionality Covered by Tests

The automated test suite covers:

- Authentication behavior and user data isolation
- Expense CRUD operations and soft deletion
- Expense filtering, sorting, pagination, and date/category queries
- Receipt upload and retrieval
- Budget functionality and validations
- Health endpoint and error handling

### Synthetic Test Data

A Django management command is available to populate the database with synthetic data for development and testing.

Run a dry run first:

```bash
python manage.py seed_synthetic_data --dry-run
```

To seed the database:

```bash
python manage.py seed_synthetic_data
```

The seed command creates sample users, categories, expenses, budgets, and alerts.

### Sprint 1 Verification Notes

- All 70 automated backend tests passed during verification.
- The backend database and migrations were verified successfully.
- API endpoints requiring authentication must be tested using valid credentials.
- The complete user flow and remaining requirements must be checked against the project's SRS, SAD, and Test Plan before declaring Sprint 1 fully complete.
