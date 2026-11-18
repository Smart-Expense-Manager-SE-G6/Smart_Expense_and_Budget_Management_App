#!/bin/sh
# Encrypted off-site copy of a backup (S3-18, FR22, NFR10).
#
#   offsite_copy.sh             # copies the newest backup (backups/LATEST)
#   offsite_copy.sh <backup>    # copies a given one
#
# Writes <backup>.tar.gz.enc into OFFSITE_DIR: the whole backup folder (database
# dump, receipts, checksums), encrypted with AES-256 (PBKDF2, 600,000 rounds) using
# BACKUP_PASSPHRASE. OFFSITE_DIR should be storage outside the server, e.g. an
# Azure Files share or S3 bucket mounted on the VM (docs/operations/recovery-runbook.md).
# Keeps the newest OFFSITE_KEEP copies (default 7). Needs openssl (deploy/backup.Dockerfile).
set -eu

. "$(dirname "$0")/common.sh"

: "${OFFSITE_DIR:?OFFSITE_DIR is not set}"
: "${BACKUP_PASSPHRASE:?BACKUP_PASSPHRASE is not set}"
[ "${#BACKUP_PASSPHRASE}" -ge 20 ] || die "BACKUP_PASSPHRASE must be at least 20 characters"
command -v openssl > /dev/null || die "openssl is not installed (use deploy/backup.Dockerfile)"
OFFSITE_KEEP="${OFFSITE_KEEP:-7}"

if [ $# -eq 0 ]; then
    [ -f "$BACKUP_DIR/LATEST" ] || die "No backup to copy: $BACKUP_DIR/LATEST is missing"
    set -- "$(cat "$BACKUP_DIR/LATEST")"
fi
source="$(resolve_backup "$1")"
name="$(basename "$source")"
verify_backup "$source"
mkdir -p "$OFFSITE_DIR"

target="$OFFSITE_DIR/$name.tar.gz.enc"
partial="$OFFSITE_DIR/.partial-$name"
trap 'rm -f "$partial"' EXIT

log "Encrypting $name to $OFFSITE_DIR"
tar -czf - -C "$BACKUP_DIR" "$name" \
    | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:BACKUP_PASSPHRASE -out "$partial"
mv "$partial" "$target"
(cd "$OFFSITE_DIR" && sha256sum "$name.tar.gz.enc" > "$name.tar.gz.enc.sha256")
log "Off-site copy complete: $(basename "$target") ($(du -h "$target" | cut -f1))"

# Keep the newest $OFFSITE_KEEP copies (names sort by time).
ls -1 "$OFFSITE_DIR" | grep -E '^[0-9]{8}T[0-9]{6}Z.*\.tar\.gz\.enc$' | sort -r | tail -n +"$((OFFSITE_KEEP + 1))" |
    while read -r old; do
        rm -f "$OFFSITE_DIR/$old" "$OFFSITE_DIR/$old.sha256"
        log "Removed old off-site copy $old"
    done
