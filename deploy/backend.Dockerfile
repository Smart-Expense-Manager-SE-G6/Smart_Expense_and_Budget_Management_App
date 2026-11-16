# Production API image (S3-10). Build context: ./backend
#   docker compose -f docker-compose.prod.yml build
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user; it owns only the folders the app writes to.
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/private_media /app/staticfiles \
    && chown -R app:app /app/private_media /app/staticfiles
USER app

EXPOSE 8000

# Migrations (which also create the shared cache table) and static files for the
# admin site run on every start; both are safe to repeat.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput -v 0 && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 60 --access-logfile - --forwarded-allow-ips '*'"]
