#!/usr/bin/env bash
# Production smoke test (S3-10): checks a deployed site end to end.
#
#   deploy/smoke_test.sh https://smartexpense.example.com
#   deploy/smoke_test.sh https://localhost --insecure     # local test with Caddy's own certificate
#
# Creates a throwaway account, uses it, then deletes it. Exits non-zero on any failure.
set -u

base="${1:?usage: smoke_test.sh https://host [--insecure]}"
base="${base%/}"
curl_opts=(-s --max-time 20)
[ "${2:-}" = "--insecure" ] && curl_opts+=(-k)
host="${base#https://}"
jar="$(mktemp)"; trap 'rm -f "$jar"' EXIT
email="smoke-$(date +%s)-$RANDOM@example.com"
password="Smoke-Test-$(date +%s)-Pw!"
failures=0

check() {  # check "name" condition-exit-code
    if [ "$2" -eq 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; failures=$((failures + 1)); fi
}
header() {  # header URL NAME -> value
    curl "${curl_opts[@]}" -o /dev/null -D - "$1" | tr -d '\r' | grep -i "^$2:" | head -1 | cut -d' ' -f2-
}

# Transport (NFR4)
code=$(curl "${curl_opts[@]}" -o /dev/null -w '%{http_code} %{redirect_url}' "http://$host/")
case "$code" in 30[18]\ https://*) r=0 ;; *) r=1 ;; esac; check "HTTP redirects to HTTPS ($code)" $r
[ "${2:-}" = "--insecure" ] || { curl -s --max-time 20 -o /dev/null "$base/"; check "certificate is trusted" $?; }
hsts=$(header "$base/" strict-transport-security); [ -n "$hsts" ]; check "HSTS header ($hsts)" $?
csp=$(header "$base/" content-security-policy); [[ "$csp" == *"default-src 'self'"* ]]; check "CSP on the app" $?
server=$(header "$base/api/v1/health/" server); [ -z "$server" ]; check "no Server header from the API (got '${server}')" $?
[ "$(header "$base/api/v1/health/" cache-control)" = "no-store" ]; check "API responses are not cacheable" $?

# App and API are up
[ "$(curl "${curl_opts[@]}" -o /dev/null -w '%{http_code}' "$base/")" = 200 ]; check "app loads" $?
[ "$(curl "${curl_opts[@]}" -o /dev/null -w '%{http_code}' "$base/expenses")" = 200 ]; check "deep link serves the app" $?
curl "${curl_opts[@]}" "$base/api/v1/health/" | grep -q '"ok"\|"status"'; check "health endpoint" $?
[ "$(curl "${curl_opts[@]}" -o /dev/null -w '%{http_code}' "$base/static/admin/css/base.css")" = 200 ]; check "admin static files" $?

# A real user journey through the same origin, with session cookie and CSRF token (ADR-0001)
api() {  # api METHOD PATH [JSON] -> prints "status body"
    local token; token=$(awk '$6=="csrftoken"{print $7}' "$jar" | tail -1)
    curl "${curl_opts[@]}" -b "$jar" -c "$jar" -X "$1" "$base/api/v1$2" -H "Content-Type: application/json" \
        -H "X-CSRFToken: $token" -H "Origin: $base" -H "Referer: $base/" ${3:+--data "$3"} -w '\n%{http_code}'
}
api GET /auth/csrf/ > /dev/null
[ "$(api POST /auth/register/ "{\"email\":\"$email\",\"password\":\"$password\"}" | tail -1)" = 201 ]; check "register" $?
[ "$(api POST /auth/logout/ | tail -1)" = 204 ]; check "logout" $?
api GET /auth/csrf/ > /dev/null
[ "$(api POST /auth/login/ "{\"email\":\"$email\",\"password\":\"$password\"}" | tail -1)" = 200 ]; check "login" $?
grep -q "#HttpOnly_.*sessionid" "$jar" && awk '$7 && $6=="sessionid"{print $4}' "$jar" | grep -qi true
check "session cookie is HttpOnly and Secure" $?
today=$(date -u +%Y-%m-%d)
[ "$(api POST /expenses/ "{\"amount\":\"12.50\",\"date\":\"$today\",\"description\":\"smoke test\"}" | tail -1)" = 201 ]; check "add an expense" $?
api GET "/analytics/reports/?start_date=$today&end_date=$today" | tail -1 | grep -q 200; check "report" $?
[ "$(api DELETE /me/ "{\"password\":\"$password\"}" | tail -1)" = 204 ]; check "delete the test account" $?

echo
if [ "$failures" -eq 0 ]; then echo "Smoke test PASSED for $base"; else echo "Smoke test FAILED: $failures check(s) for $base"; exit 1; fi
