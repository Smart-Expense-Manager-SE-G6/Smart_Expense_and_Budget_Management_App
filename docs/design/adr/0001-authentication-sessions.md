# ADR 0001: Server-side sessions for authentication (resolves OI-2)

- **Status:** Accepted
- **Date:** 2026-10-26
- **Owner:** Shriram Chandrasekar
- **Requirements:** OI-2, NFR5

## Context

The React frontend and Django REST Framework API need an authentication mechanism. OI-2 asks whether to use JWT or server-side sessions, and how credentials expire and are invalidated. NFR5 requires that a logged-out or expired credential can no longer be used.

The frontend is served through the Vite dev server, which proxies `/api` to Django, so the browser sees a single origin. There is no mobile app and no third-party API client.

## Options

| | JWT (access + refresh token) | Server-side session (Django) |
|---|---|---|
| Logout invalidation | Needs a token blacklist table, checked on every request | Built in: logout deletes the session row |
| Expiry | Short access token plus refresh flow on the client | One setting, enforced by the server |
| Token storage in browser | Usually `localStorage`, readable by any XSS | `HttpOnly` cookie, not readable by JavaScript |
| CSRF | Not needed if sent in a header | Needed; Django provides it |
| Extra dependencies | `djangorestframework-simplejwt` | None |
| Statelessness / multi-service scaling | Yes | No, but we are a single modular monolith |

## Decision

Use **Django server-side sessions** with DRF `SessionAuthentication`.

- Session id in an `HttpOnly`, `SameSite=Lax` cookie; `Secure` when not in debug.
- **Idle timeout:** 30 minutes (`SESSION_IDLE_TIMEOUT_SECONDS`), refreshed on every request. A financial app should not stay logged in on an unattended screen.
- **Logout** calls Django `logout()`, which deletes the session server-side.
- **Unauthenticated, expired or logged-out requests return `401`**, not DRF's default `403`, via `core.authentication.SessionAuthentication401`.
- All endpoints require authentication by default; public endpoints (health, register, login) opt out explicitly with `AllowAny`.
- **CSRF:** React reads the `csrftoken` cookie and sends it as the `X-CSRFToken` header on unsafe methods (POST, PUT, PATCH, DELETE).

## Consequences

- Revocation is immediate and simple; no blacklist to maintain.
- Every authenticated request does one session lookup in PostgreSQL. Fine at our scale (NFR1 targets one user with 10,000 transactions).
- The frontend must always call relative `/api/...` URLs so cookies stay same-origin, and must send the CSRF header.
- If we ever add a mobile client or split into services, revisit this ADR; token auth could be added alongside sessions without removing them.
- Optional Google sign-in (Sprint 2, stretch) ends in a normal Django login, so it fits this model.
