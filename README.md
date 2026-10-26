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

## Rules

- No secrets in code. Everything comes from `.env`, which is git-ignored.
- Money is stored as `Decimal`, never float. Timestamps are UTC.
