#!/bin/sh
# Bring an encrypted off-site copy back for restore (S3-18, FR22).
#
#   offsite_fetch.sh                                   # newest copy in OFFSITE_DIR
#   offsite_fetch.sh 20261116T020000Z.tar.gz.enc       # a given one
#
# Checks the copy's checksum, decrypts it with BACKUP_PASSPHRASE into BACKUP_DIR,
# and verifies the backup inside. Then restore it with:
#   restore.sh <backup name printed below>
set -eu

. "$(dirname "$0")/common.sh"

: "${OFFSITE_DIR:?OFFSITE_DIR is not set}"
: "${BACKUP_PASSPHRASE:?BACKUP_PASSPHRASE is not set}"
command -v openssl > /dev/null || die "openssl is not installed (use deploy/backup.Dockerfile)"

if [ $# -eq 0 ]; then
    newest="$(ls -1 "$OFFSITE_DIR" 2>/dev/null | grep -E '^[0-9]{8}T[0-9]{6}Z.*\.tar\.gz\.enc$' | sort -r | head -1)" || true
    [ -n "$newest" ] || die "No off-site copies in $OFFSITE_DIR"
    set -- "$newest"
fi
file="$OFFSITE_DIR/$(basename "$1")"
[ -f "$file" ] || die "$file does not exist"
if [ -f "$file.sha256" ]; then
    (cd "$OFFSITE_DIR" && sha256sum -c "$(basename "$file").sha256" > /dev/null) || die "Checksum mismatch: $file is damaged"
    log "PASS off-site copy checksum"
fi

name="$(basename "$file" .tar.gz.enc)"
mkdir -p "$BACKUP_DIR"
[ ! -e "$BACKUP_DIR/$name" ] || die "$BACKUP_DIR/$name already exists; restore it directly"
log "Decrypting $(basename "$file")"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:BACKUP_PASSPHRASE -in "$file" \
    | tar -xzf - -C "$BACKUP_DIR" || die "Could not decrypt $file (wrong BACKUP_PASSPHRASE?)"
verify_backup "$BACKUP_DIR/$name"
log "PASS backup $name is complete and its checksums match"
log "Now restore it: restore.sh $name"
