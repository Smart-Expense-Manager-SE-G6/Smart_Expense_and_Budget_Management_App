#!/bin/sh
# Back up the database and receipt files (FR22).
#
#   docker compose run --rm backup /scripts/backup.sh
#
# Writes $BACKUP_DIR/<UTC timestamp>/ containing:
#   db.dump       pg_dump custom-format archive (restore with restore.sh)
#   media.tar.gz  backend/private_media (uploaded receipts)
#   counts.tsv    row count of every table, used by rehearse_restore.sh
#   info.txt      when, which database, server version, media file count
#   SHA256SUMS    checksums of the files above
#
# A backup is written to a temporary directory and only renamed into place
# when complete, so a failed run never looks like a usable backup. Only the
# newest $BACKUP_KEEP scheduled backups are kept. Labelled backups (set
# BACKUP_LABEL, as restore.sh does) are never pruned.
set -eu

. "$(dirname "$0")/common.sh"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
name="$stamp${BACKUP_LABEL:+-$BACKUP_LABEL}"
target="$BACKUP_DIR/$name"
partial="$BACKUP_DIR/.partial-$name"

[ -d "$MEDIA_DIR" ] || die "Media directory $MEDIA_DIR does not exist"
[ ! -e "$target" ] || die "$target already exists"
mkdir -p "$partial"
trap 'rm -rf "$partial"' EXIT

log "Backing up database $PGDATABASE on $PGHOST to $target"
pg_dump --format=custom --no-owner --file="$partial/db.dump" "$PGDATABASE"
table_counts "$PGDATABASE" > "$partial/counts.tsv"

log "Backing up receipts from $MEDIA_DIR"
tar -czf "$partial/media.tar.gz" -C "$MEDIA_DIR" .
media_files="$(find "$MEDIA_DIR" -type f | wc -l | tr -d ' ')"

{
    echo "created_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "database=$PGDATABASE"
    echo "server_version=$(psql -X -At -c 'SHOW server_version')"
    echo "tables=$(wc -l < "$partial/counts.tsv" | tr -d ' ')"
    echo "media_files=$media_files"
} > "$partial/info.txt"

(cd "$partial" && sha256sum db.dump media.tar.gz counts.tsv info.txt > SHA256SUMS)

mv "$partial" "$target"
trap - EXIT
printf '%s\n' "$name" > "$BACKUP_DIR/LATEST"
log "Backup complete: $name ($(du -sh "$target" | cut -f1), $media_files receipt files)"

if [ -z "${BACKUP_LABEL:-}" ]; then
    # Timestamps sort chronologically; keep the newest $BACKUP_KEEP.
    ls -1 "$BACKUP_DIR" | grep -E '^[0-9]{8}T[0-9]{6}Z$' | sort -r \
        | tail -n "+$((BACKUP_KEEP + 1))" | while read -r old; do
            log "Removing old backup $old"
            rm -rf "${BACKUP_DIR:?}/$old"
        done
fi
