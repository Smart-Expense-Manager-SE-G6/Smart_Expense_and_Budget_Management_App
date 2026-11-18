# API Test Report

## Objective and scope
Inspect the registered API surface and execute the existing Postman collection if Newman and a safe local server are available.

## Observed test asset

`tests/postman_collection.json` is present and contains health, CSRF, registration/login, profile, analytics, and logout requests. No Newman execution occurred because the local backend could not be started: Python was unavailable and Docker was not running.

| ID | Endpoint/scenario | Method/auth | Expected | Actual | Status |
|---|---|---|---|---|---|
| API-01 | Service health | GET, public | 200 and status payload | Collection not executed | NOT RUN |
| API-02 | CSRF bootstrap | GET, public | 204 and CSRF cookie | Collection not executed | NOT RUN |
| API-03 | Register | POST, public | 201 or documented conflict | Collection not executed | NOT RUN |
| API-04 | Login/profile | POST/GET, session | 200 and session cookie/profile | Collection not executed | NOT RUN |
| API-05 | Analytics summary/breakdown | GET, authenticated | 200 and expected fields | Collection not executed | NOT RUN |
| API-06 | Logout | POST, authenticated | 200/204 and session invalidation | Collection not executed | NOT RUN |

## Exact command

```powershell
npx.cmd newman run tests/postman_collection.json --env-var base_url=http://127.0.0.1:8000
```

Newman was not invoked; no API results are fabricated.
