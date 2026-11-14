# Smart Expense and Budget Management Application

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

## Rules

- No secrets in code. Everything comes from `.env`, which is git-ignored.
- Money is stored as `Decimal`, never float. Timestamps are UTC.

## Sprint 1 – Testing & Verification

### Running the checks

With the stack running (`docker compose up --build`):

```bash
docker compose exec backend python manage.py check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend python manage.py test
npx newman run tests/postman_collection.json      # API smoke test, base_url http://localhost:8001
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
