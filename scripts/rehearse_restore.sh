#!/bin/sh
# TC-Backup-01: prove a backup can be fully restored (FR22, R6).
#
#   docker compose run --rm backup /scripts/rehearse_restore.sh           # takes a fresh backup
#   docker compose run --rm backup /scripts/rehearse_restore.sh <backup>  # an existing one
#
# Restores the backup into a scratch database, so the live database and
# receipts are never touched. Then checks that every table has the row count
# it had when the backup was taken and that every receipt file is in the
# archive. Exits non-zero if anything does not match.
set -eu

. "$(dirname "$0")/common.sh"

if [ $# -eq 0 ]; then
    sh "$(dirname "$0")/backup.sh"
    set -- "$(cat "$BACKUP_DIR/LATEST")"
fi

source="$(resolve_backup "$1")"
name="$(basename "$source")"
scratch="${PGDATABASE}_restore_rehearsal"
staging="$(mktemp -d)"
cleanup() {
    rm -rf "$staging"
    dropdb --if-exists "$scratch" > /dev/null 2>&1 || true
}
trap cleanup EXIT

log "TC-Backup-01: rehearsing a full restore of $name"

verify_backup "$source"
log "PASS backup is complete and checksums match"

PGOPTIONS="-c client_min_messages=warning" dropdb --if-exists "$scratch"
createdb "$scratch"
pg_restore --no-owner --single-transaction --exit-on-error \
    --dbname="$scratch" "$source/db.dump"
log "PASS database restored into scratch database $scratch"

table_counts "$scratch" > "$staging/restored.tsv"
if diff "$source/counts.tsv" "$staging/restored.tsv" > "$staging/diff.txt"; then
    log "PASS row counts match for all $(wc -l < "$staging/restored.tsv" | tr -d ' ') tables"
else
    cat "$staging/diff.txt" >&2
    die "FAIL row counts differ between backup time (-) and restore (+)"
fi

mkdir "$staging/media"
tar -xzf "$source/media.tar.gz" -C "$staging/media"
expected="$(sed -n 's/^media_files=//p' "$source/info.txt")"
restored="$(find "$staging/media" -type f | wc -l | tr -d ' ')"
[ "$restored" = "$expected" ] \
    || die "FAIL receipts: backup recorded $expected files, archive holds $restored"
log "PASS all $restored receipt files restored"

log "TC-Backup-01 PASSED for $name"
