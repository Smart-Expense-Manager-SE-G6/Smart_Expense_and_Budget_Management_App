#!/usr/bin/env bash
# Run the production stack on this machine for the demo (S3-10).
#
#   deploy/local-demo.sh                  # build from this checkout and start (creates .env.prod the first time)
#   deploy/local-demo.sh release [tag]    # run a release the CI/CD pipeline built and tested (default: latest main)
#   deploy/local-demo.sh stop             # stop, keeping the data
#   deploy/local-demo.sh reset            # stop and delete all demo data
#
# Same images and settings as a server: gunicorn, Caddy with HTTPS and security
# headers, PostgreSQL, the scheduler, daily backups with encrypted copies in ./offsite.
# Open https://localhost . Run from the repository root, in WSL or Linux with Docker.
set -euo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose -f docker-compose.prod.yml --env-file .env.prod)
registry="ghcr.io/smart-expense-manager-se-g6"
up_args=(up -d --build)

secret() { head -c 48 /dev/urandom | base64 | tr -d '/+=\n' | head -c 50; }

case "${1:-start}" in
  stop)  "${compose[@]}" down; exit 0 ;;
  reset) "${compose[@]}" down -v; rm -rf backups offsite; echo "Demo data deleted."; exit 0 ;;
  start) ;;
  release)
    tag="${2:-main}"
    export BACKEND_IMAGE="$registry/smart-expense-backend:$tag" \
           WEB_IMAGE="$registry/smart-expense-web:$tag" \
           BACKUP_IMAGE="$registry/smart-expense-backup:$tag"
    echo "Running release '$tag' from $registry (built and smoke-tested by the CI/CD pipeline)."
    up_args=(up -d --no-build --pull always)
    ;;
  *) echo "usage: $0 [start | release [tag] | stop | reset]" >&2; exit 2 ;;
esac

if [ ! -f .env.prod ]; then
  sed -e "s#^SITE_ADDRESS=.*#SITE_ADDRESS=localhost#" \
      -e "s#^ACME_EMAIL=.*#ACME_EMAIL=admin@localhost#" \
      -e "s#^DJANGO_SECRET_KEY=.*#DJANGO_SECRET_KEY=$(secret)#" \
      -e "s#^DJANGO_ALLOWED_HOSTS=.*#DJANGO_ALLOWED_HOSTS=localhost#" \
      -e "s#^DJANGO_CSRF_TRUSTED_ORIGINS=.*#DJANGO_CSRF_TRUSTED_ORIGINS=https://localhost#" \
      -e "s#^POSTGRES_PASSWORD=.*#POSTGRES_PASSWORD=$(secret)#" \
      -e "s#^OFFSITE_PATH=.*#OFFSITE_PATH=./offsite#" \
      -e "s#^BACKUP_PASSPHRASE=.*#BACKUP_PASSPHRASE=$(secret)#" \
      .env.prod.example > .env.prod
  chmod 600 .env.prod
  echo "Created .env.prod for localhost (random secrets; git-ignored)."
fi
mkdir -p offsite

"${compose[@]}" "${up_args[@]}"
printf 'Waiting for https://localhost '
for _ in $(seq 1 60); do
  if curl -sk -o /dev/null -w '%{http_code}' https://localhost/api/v1/health/ | grep -q 200; then break; fi
  printf '.'; sleep 2
done
echo
"${compose[@]}" ps --format '{{.Service}}: {{.Status}}'

# Caddy's local certificate authority, so the browser can be told to trust https://localhost.
"${compose[@]}" cp web:/data/caddy/pki/authorities/local/root.crt ./caddy-local-root.crt >/dev/null 2>&1 || true

cat <<'EOF'

The app is running at https://localhost

No certificate warning (once per machine), in Windows PowerShell from the repository folder:
  certutil -user -addstore Root caddy-local-root.crt
then restart the browser. (Remove it later with: certutil -user -delstore Root "Caddy Local Authority")

Check it:     deploy/smoke_test.sh https://localhost --insecure
Admin user:   docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py createsuperuser
Stop:         deploy/local-demo.sh stop      Delete all demo data: deploy/local-demo.sh reset
EOF
