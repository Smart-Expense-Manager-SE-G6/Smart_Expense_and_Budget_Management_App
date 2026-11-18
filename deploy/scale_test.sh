#!/usr/bin/env bash
# TC-Perf-03 (NFR3): the API runs as several interchangeable replicas.
#
#   docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-build --scale backend=2
#   bash deploy/scale_test.sh https://localhost --insecure
#
# With two backend replicas behind Caddy it checks that:
#   1. one signed-in session works on both replicas (sessions live in PostgreSQL, not in a process);
#   2. writes with a CSRF token are accepted by both replicas;
#   3. requests are spread across both replicas (gunicorn access logs);
#   4. when one replica stops, the same session keeps working on the other.
set -uo pipefail

base="${1:?usage: scale_test.sh <base url> [--insecure]}"
curl_opts=(-s --max-time 20)
[ "${2:-}" = "--insecure" ] && curl_opts+=(-k)
compose=(docker compose -f docker-compose.prod.yml --env-file .env.prod)
jar="$(mktemp)"; trap 'rm -f "$jar"' EXIT
failures=0
check() { if [ "$2" = 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; failures=$((failures + 1)); fi; }

api() {  # method path [json body] -> prints the HTTP status
    local token; token=$(awk '$6=="csrftoken"{print $7}' "$jar" | tail -1)
    curl "${curl_opts[@]}" -b "$jar" -c "$jar" -X "$1" "$base/api/v1$2" -H "Content-Type: application/json" \
        -H "X-CSRFToken: $token" -H "Origin: $base" -H "Referer: $base/" ${3:+--data "$3"} \
        -o /dev/null -w '%{http_code}'
}

replicas=$("${compose[@]}" ps -q backend | wc -l)
[ "$replicas" -ge 2 ]; check "at least two backend replicas are running (found $replicas)" $?

email="scale.$(date +%s)$RANDOM@example.com"; password="Scale-Test-Passw0rd!"
api GET /auth/csrf/ > /dev/null
[ "$(api POST /auth/register/ "{\"email\":\"$email\",\"password\":\"$password\"}")" = 201 ]; check "register" $?
api GET /auth/csrf/ > /dev/null
[ "$(api POST /auth/login/ "{\"email\":\"$email\",\"password\":\"$password\"}")" = 200 ]; check "login once" $?

since="$(date -u +%Y-%m-%dT%H:%M:%SZ)"; sleep 1
reads_ok=0; for i in $(seq 1 40); do [ "$(api GET /me/)" = 200 ] && reads_ok=$((reads_ok + 1)); done
[ "$reads_ok" = 40 ]; check "40 reads with one session all succeed ($reads_ok/40)" $?
writes_ok=0; for i in $(seq 1 10); do
    [ "$(api PATCH /me/ "{\"first_name\":\"Scale$i\"}")" = 200 ] && writes_ok=$((writes_ok + 1))
done
[ "$writes_ok" = 10 ]; check "10 writes with the CSRF token all succeed ($writes_ok/10)" $?

echo "Requests served per replica since $since:"
served=0
for id in $("${compose[@]}" ps -q backend); do
    name=$(docker inspect -f '{{.Name}}' "$id" | tr -d /)
    n=$(docker logs --since "$since" "$id" 2>&1 | grep -cE '"(GET|PATCH) /api/v1/me/ ')
    echo "  $name: $n"
    [ "$n" -gt 0 ] && served=$((served + 1))
done
[ "$served" -ge 2 ]; check "requests were spread across $served replicas" $?

first=$("${compose[@]}" ps -q backend | head -1)
docker stop "$first" > /dev/null
after_ok=0; for i in $(seq 1 10); do [ "$(api GET /me/)" = 200 ] && after_ok=$((after_ok + 1)); done
[ "$after_ok" = 10 ]; check "with one replica stopped, the same session still works ($after_ok/10)" $?
docker start "$first" > /dev/null

[ "$(api DELETE /me/ "{\"password\":\"$password\"}")" = 204 ]; check "delete the test account" $?

if [ "$failures" = 0 ]; then echo; echo "Scale test PASSED for $base"; else echo; echo "Scale test FAILED: $failures check(s)"; exit 1; fi
