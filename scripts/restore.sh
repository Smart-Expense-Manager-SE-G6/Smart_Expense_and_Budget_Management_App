#!/bin/sh
# Restore the database and receipt files from a backup (FR22).
#
#   docker compose stop backend
#   docker compose run --rm backup /scripts/restore.sh 20261031T020000Z
#   docker compose start backend
#
# Replaces every table in the backup and all receipt files. A safety backup
# labelled "pre-restore" is taken first, so a restore can itself be undone.
# Asks you to type the database name to confirm, unless --yes is given.
# Restore with the same code version (migrations) the backup was taken with.
set -eu

. "$(dirname "$0")/common.sh"

assume_yes=0
if [ "${1:-}" = "--yes" ]; then
    assume_yes=1
    shift
fi
if [ $# -ne 1 ]; then
    list_backups
    die "Usage: restore.sh [--yes] <backup>"
fi

source="$(resolve_backup "$1")"
verify_backup "$source"
case "$MEDIA_DIR" in
    "" | /) die "Refusing to restore receipts into MEDIA_DIR='$MEDIA_DIR'" ;;
esac
[ -d "$MEDIA_DIR" ] || die "Media directory $MEDIA_DIR does not exist"

if [ "$assume_yes" -ne 1 ]; then
    printf 'This replaces database "%s" and all receipts with backup %s.\n' \
        "$PGDATABASE" "$(basename "$source")"
    printf 'Type the database name to continue: '
    read -r answer || answer=""
    [ "$answer" = "$PGDATABASE" ] || die "Restore cancelled"
fi

log "Taking a safety backup of the current data first"
BACKUP_LABEL=pre-restore sh "$(dirname "$0")/backup.sh"

log "Restoring database $PGDATABASE from $(basename "$source")"
pg_restore --clean --if-exists --no-owner --single-transaction --exit-on-error \
    --dbname="$PGDATABASE" "$source/db.dump"

log "Restoring receipts into $MEDIA_DIR"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"' EXIT
tar -xzf "$source/media.tar.gz" -C "$staging"
find "$MEDIA_DIR" -mindepth 1 -depth -exec rm -rf {} \;
cp -a "$staging/." "$MEDIA_DIR/"
log "Restore complete from $(basename "$source")"