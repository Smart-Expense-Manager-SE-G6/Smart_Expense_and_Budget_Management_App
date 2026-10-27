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

## Rules

- No secrets in code. Everything comes from `.env`, which is git-ignored.
- Money is stored as `Decimal`, never float. Timestamps are UTC.
