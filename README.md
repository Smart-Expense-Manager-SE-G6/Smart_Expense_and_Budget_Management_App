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

## Rules

- No secrets in code. Everything comes from `.env`, which is git-ignored.
- Money is stored as `Decimal`, never float. Timestamps are UTC.
## Sprint 1 – Backend Testing & Verification

### Backend Testing Status

**Status: Backend test suite passed — 70/70 tests.**

The Sprint 1 backend has been tested using Django's automated test suite. The following checks were completed:

- [x] **Django system check** — `python manage.py check`
- [x] **Database migrations** — migrations applied successfully.
- [x] **Automated test suite** — all 70 tests passed using `python manage.py test`.
- [x] **Database setup** — PostgreSQL database configured and connected successfully.
- [x] **Synthetic test data** — sample users, categories, expenses, budgets, and alerts seeded successfully.
- [x] **Seed command dry run** — verified without making database changes.

### Areas Covered by Automated Tests

The existing test suite covers backend functionality including:

- Expense CRUD operations and soft deletion
- Expense filtering, sorting, pagination, and date/category queries
- Authentication behavior and user-level data isolation
- Receipt upload and retrieval
- Budget functionality and related validations
- Health endpoint and error handling

### Sprint 1 Review Notes

- The backend automated test suite is passing.
- The synthetic dataset is available for development and API testing.
- API endpoints requiring authentication must be tested with valid credentials.
- Authentication endpoints, category management, dashboard functionality, and other requirements should be checked against the submitted SRS, SAD, and Test Plan before declaring the entire Sprint 1 user flow complete.

**Last verification:** 70 automated tests passed.

