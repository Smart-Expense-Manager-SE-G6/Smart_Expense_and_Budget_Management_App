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
# With OFFSITE_DIR set (production), each backup is followed by an encrypted
# off-site copy (S3-18). With REHEARSAL_SCHEDULE set, the newest backup is also
# restored into a scratch database on that schedule (TC-Backup-01, weekly in production).
job="sh $script_dir/backup.sh"
[ -z "${OFFSITE_DIR:-}" ] || job="$job && sh $script_dir/offsite_copy.sh"
printf '%s . %s/env && { %s; } >> %s 2>&1\n' \
    "$schedule" "$state" "$job" "$cron_log" > "$state/crontabs/root"
if [ -n "${REHEARSAL_SCHEDULE:-}" ]; then
    printf '%s . %s/env && sh %s/rehearse_restore.sh "$(cat %s/LATEST)" >> %s 2>&1\n' \
        "$REHEARSAL_SCHEDULE" "$state" "$script_dir" "$BACKUP_DIR" "$cron_log" >> "$state/crontabs/root"
fi

mkdir -p "$BACKUP_DIR"
if [ -z "$(find "$BACKUP_DIR/LATEST" -mmin -1440 2>/dev/null)" ]; then
    log "No backup in the last 24 hours, taking one now"
    sh -c "$job" || log "Backup failed; retrying at the next scheduled time"
fi

log "Daily backups scheduled: '$schedule' ($(date +%Z)), keeping $BACKUP_KEEP"
[ -z "${OFFSITE_DIR:-}" ] || log "Encrypted off-site copies to $OFFSITE_DIR after each backup, keeping ${OFFSITE_KEEP:-7}"
[ -z "${REHEARSAL_SCHEDULE:-}" ] || log "Restore rehearsal scheduled: '$REHEARSAL_SCHEDULE'"
exec crond -f -d 8 -c "$state/crontabs"
