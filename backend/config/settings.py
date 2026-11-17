"""
Django settings for the Smart Expense & Budget Management API.

All secrets and environment-specific values come from environment variables
(see .env.example at the repo root). Nothing secret is hard-coded here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# backend/.env first, then the repo-root .env that the README creates (used when
# running outside Docker). Variables already set in the environment always win.
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")

def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise ImproperlyConfigured(f"Environment variable {name} is required")
    return value


def env_bool(name, default=False):
    return env(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
# Fail closed: outside debug the app refuses to start with a missing secret key
# instead of silently signing sessions with a publicly known one.
SECRET_KEY = env("DJANGO_SECRET_KEY", required=not DEBUG) or "django-insecure-dev-key-debug-only"
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5174,http://localhost:5173")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "core",
    "accounts",
    "audit",
    "expenses",
    "budgets",
    "alerts.apps.AlertsConfig",
    "analytics",
    "monitoring",
]

MIDDLEWARE = [
    "core.request_id.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "core.security_headers.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL unless SQLite is asked for explicitly; a missing POSTGRES_* variable is
# an error rather than a silent switch to a different database engine.
if env_bool("USE_SQLITE", False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", required=True),
            "USER": env("POSTGRES_USER", required=True),
            "PASSWORD": env("POSTGRES_PASSWORD", required=True),
            "HOST": env("POSTGRES_HOST", "localhost"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }

AUTH_USER_MODEL = "accounts.User"

# bcrypt first (NFR4); the others stay so older hashes can still be verified.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Timestamps are stored in UTC (D7); budget periods use the user's own time zone.
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = BASE_DIR / "private_media"
RECEIPT_MAX_SIZE_BYTES = int(env("RECEIPT_MAX_SIZE_BYTES", str(5 * 1024 * 1024)))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email Configuration - Brevo SMTP
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", "smtp-relay.brevo.com")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "krshashwath2@gmail.com")

# Operational monitoring. The state directory is shared with the scheduler and
# backup containers; log files are kept in a separate mounted directory.
MONITORING_STATE_DIR = Path(env("MONITORING_STATE_DIR", "/monitoring"))
MONITORING_SCHEDULER_MAX_AGE_SECONDS = int(env("MONITORING_SCHEDULER_MAX_AGE_SECONDS", str(30 * 60 * 60)))
MONITORING_BACKUP_MAX_AGE_SECONDS = int(env("MONITORING_BACKUP_MAX_AGE_SECONDS", str(26 * 60 * 60)))
MONITORING_ALERT_EMAIL = env("MONITORING_ALERT_EMAIL", "")
ERROR_RATE_WINDOW_SECONDS = int(env("ERROR_RATE_WINDOW_SECONDS", "300"))
ERROR_RATE_MIN_REQUESTS = int(env("ERROR_RATE_MIN_REQUESTS", "10"))
ERROR_RATE_THRESHOLD_PERCENT = float(env("ERROR_RATE_THRESHOLD_PERCENT", "5"))
ERROR_ALERT_COOLDOWN_SECONDS = int(env("ERROR_ALERT_COOLDOWN_SECONDS", "900"))
SLOW_REQUEST_THRESHOLD_MS = int(env("SLOW_REQUEST_THRESHOLD_MS", "2000"))

# Authentication: server-side sessions (docs/adr/0001-authentication-sessions.md).
# Idle timeout: the session expires after this many seconds without a request.
SESSION_COOKIE_AGE = int(env("SESSION_IDLE_TIMEOUT_SECONDS", "1800"))
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False  # React reads it to send the X-CSRFToken header
CSRF_FAILURE_VIEW = "core.exceptions.csrf_failure"

# Transport security (NFR4). On by default outside debug; each can be overridden from
# the environment, e.g. DJANGO_SECURE_SSL_REDIRECT=false when TLS ends elsewhere.
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = int(env("DJANGO_SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
# Preloading tells every browser to use HTTPS for the domain for months and needs a
# domain the team owns and submits to hstspreload.org. Off by default (the deployment
# runs on a hosting provider's subdomain), so check --deploy's W021 is expected.
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
SILENCED_SYSTEM_CHECKS = [] if SECURE_HSTS_PRELOAD else ["security.W021"]
# Trust X-Forwarded-Proto only when a reverse proxy we control sets it.
if int(env("NUM_PROXIES", "0")) > 0:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Shared cache (S3-15). Rate limits and failed-login lockouts are counted here, so
# every worker process and every backend replica (NFR3) sees the same counts. The
# table is created by migration core 0001. A local in-memory cache would give each
# process its own allowance and multiply the number of guesses an attacker gets.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
        "TIMEOUT": 3600,
        "OPTIONS": {"MAX_ENTRIES": 50000},
    }
}

# Failed-login limits (accounts.throttles.LoginFailureGuard).
LOGIN_FAILURE_WINDOW_SECONDS = int(env("LOGIN_FAILURE_WINDOW_SECONDS", "300"))
LOGIN_FAILURES_PER_ACCOUNT_AND_IP = int(env("LOGIN_FAILURES_PER_ACCOUNT_AND_IP", "5"))
LOGIN_FAILURES_PER_ACCOUNT = int(env("LOGIN_FAILURES_PER_ACCOUNT", "25"))
TRUSTED_DEVICE_MAX_AGE_SECONDS = int(env("TRUSTED_DEVICE_MAX_AGE_SECONDS", str(90 * 24 * 3600)))

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["core.authentication.SessionAuthentication401"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "login": env("LOGIN_RATE_LIMIT", "10/min"),  # per client IP
        "register": env("REGISTER_RATE_LIMIT", "5/min"),  # per client IP
    },
    # Number of trusted reverse proxies in front of Django. 0 = use the socket
    # address and ignore X-Forwarded-For, which clients can forge.
    "NUM_PROXIES": int(env("NUM_PROXIES", "0")),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Smart Expense and Budget Management API",
    "DESCRIPTION": "Session-authenticated API for expenses, budgets, analytics and alerts.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LOG_DIR = Path(env("APP_LOG_DIR", str(BASE_DIR / "logs")))
LOG_MAX_BYTES = int(env("APP_LOG_MAX_BYTES", str(10 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(env("APP_LOG_BACKUP_COUNT", "5"))

LOG_HANDLERS = {
    "console": {
        "class": "logging.StreamHandler",
        "filters": ["request_id"],
        "formatter": "json",
    },
}
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for log_name in ("application.log", "error.log"):
        with (LOG_DIR / log_name).open("a", encoding="utf-8"):
            pass
except OSError:
    # Console logging still works when the deployment cannot write local logs.
    LOG_DIR = None
if LOG_DIR is not None:
    LOG_HANDLERS.update(
        {
            "application_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(LOG_DIR / "application.log"),
                "maxBytes": LOG_MAX_BYTES,
                "backupCount": LOG_BACKUP_COUNT,
                "encoding": "utf-8",
                "filters": ["request_id"],
                "formatter": "json",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(LOG_DIR / "error.log"),
                "maxBytes": LOG_MAX_BYTES,
                "backupCount": LOG_BACKUP_COUNT,
                "encoding": "utf-8",
                "level": "ERROR",
                "filters": ["request_id"],
                "formatter": "json",
            },
        }
    )

# Every log line is structured JSON and carries the current request id.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "core.request_id.RequestIdLogFilter"}},
    "formatters": {"json": {"()": "monitoring.logging.JsonFormatter"}},
    "handlers": LOG_HANDLERS,
    "root": {
        "handlers": list(LOG_HANDLERS),
        "level": env("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        # Django's own per-request line duplicates api.request; keep only warnings from it.
        "django.server": {"level": "WARNING"},
        "django.request": {"level": "ERROR"},
    },
}
