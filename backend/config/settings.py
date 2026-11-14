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
    "core",
    "accounts",
    "audit",
    "expenses",
    "budgets",
    "alerts.apps.AlertsConfig",
    "analytics",
]

MIDDLEWARE = [
    "core.request_id.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
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
# Trust X-Forwarded-Proto only when a reverse proxy we control sets it.
if int(env("NUM_PROXIES", "0")) > 0:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Failed-login limits (accounts.throttles.LoginFailureGuard).
LOGIN_FAILURE_WINDOW_SECONDS = int(env("LOGIN_FAILURE_WINDOW_SECONDS", "300"))
LOGIN_FAILURES_PER_ACCOUNT_AND_IP = int(env("LOGIN_FAILURES_PER_ACCOUNT_AND_IP", "5"))
LOGIN_FAILURES_PER_ACCOUNT = int(env("LOGIN_FAILURES_PER_ACCOUNT", "25"))
TRUSTED_DEVICE_MAX_AGE_SECONDS = int(env("TRUSTED_DEVICE_MAX_AGE_SECONDS", str(90 * 24 * 3600)))

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["core.authentication.SessionAuthentication401"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
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

# Every log line carries the request id (NFR12).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"request_id": {"()": "core.request_id.RequestIdLogFilter"}},
    "formatters": {
        "default": {"format": "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "filters": ["request_id"], "formatter": "default"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        # Django's own per-request line duplicates api.request; keep only warnings from it.
        "django.server": {"level": "WARNING"},
        "django.request": {"level": "ERROR"},
    },
}
