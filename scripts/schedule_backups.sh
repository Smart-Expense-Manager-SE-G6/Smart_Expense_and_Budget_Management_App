#!/bin/sh
# Daily scheduled backups (NFR10). The "backup" service in docker-compose.yml
# runs this, so `docker compose up` starts it with everything else:
#
#   docker compose logs -f backup
#
# Runs backup.sh on BACKUP_SCHEDULE, a cron expression in the container's
# time zone (UTC): by default 02:00 UTC (07:30 IST) every day. Laptops are
# often off at night, so on start it also takes a backup if the newest one
# is more than 24 hours old.
set -eu

script_dir="$(cd "$(dirname "$0")" && pwd)"
. "$script_dir/common.sh"

schedule="${BACKUP_SCHEDULE:-0 2 * * *}"
cron_log="${CRON_LOG:-/proc/1/fd/1}"   # the container's stdout
state="$(mktemp -d)"
mkdir "$state/crontabs"

# Cron jobs start with an empty environment, so give them this one.
export -p > "$state/env"
chmod 600 "$state/env"
printf '%s . %s/env && sh %s/backup.sh >> %s 2>&1\n' \
    "$schedule" "$state" "$script_dir" "$cron_log" > "$state/crontabs/root"

mkdir -p "$BACKUP_DIR"
if [ -z "$(find "$BACKUP_DIR/LATEST" -mmin -1440 2>/dev/null)" ]; then
    log "No backup in the last 24 hours, taking one now"
    sh "$script_dir/backup.sh" || log "Backup failed; retrying at the next scheduled time"
fi

log "Daily backups scheduled: '$schedule' ($(date +%Z)), keeping $BACKUP_KEEP"
exec crond -f -d 8 -c "$state/crontabs"
