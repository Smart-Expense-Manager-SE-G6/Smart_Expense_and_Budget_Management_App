# Shared settings for backup.sh, restore.sh and rehearse_restore.sh (FR22).
# Sourced, not run. Written for POSIX sh (busybox ash in postgres:16-alpine).

: "${POSTGRES_DB:?POSTGRES_DB is not set (copy .env.example to .env)}"
: "${POSTGRES_USER:?POSTGRES_USER is not set}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is not set}"

PGHOST="${PGHOST:-db}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-$POSTGRES_USER}"
PGPASSWORD="${PGPASSWORD:-$POSTGRES_PASSWORD}"
PGDATABASE="${PGDATABASE:-$POSTGRES_DB}"
export PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE

BACKUP_DIR="${BACKUP_DIR:-/backups}"   # one sub-directory per backup
MEDIA_DIR="${MEDIA_DIR:-/media}"       # backend/private_media (receipts)
BACKUP_KEEP="${BACKUP_KEEP:-7}"        # scheduled backups to keep

log() {
    printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

die() {
    log "ERROR: $*" >&2
    exit 1
}

# Row count of every table in the public schema, one "table<TAB>count" per line.
table_counts() {
    psql -X -q -v ON_ERROR_STOP=1 -At -F "$(printf '\t')" -d "$1" <<'SQL'
SELECT format('SELECT %L, count(*) FROM %I.%I', table_name, table_schema, table_name)
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
\gexec
SQL
}

# Checks a backup directory is complete and its files are intact.
verify_backup() {
    for file in db.dump media.tar.gz counts.tsv info.txt SHA256SUMS; do
        [ -f "$1/$file" ] || die "$1 is not a complete backup: $file is missing"
    done
    (cd "$1" && sha256sum -c SHA256SUMS > /dev/null) || die "Checksum mismatch in $1"
}

list_backups() {
    found="$(ls -1 "$BACKUP_DIR" 2>/dev/null | grep -E '^[0-9]{8}T[0-9]{6}Z' | sort -r)" || true
    echo "Backups in $BACKUP_DIR (newest first):" >&2
    printf '%s\n' "${found:-(none)}" >&2
}

# A backup name (as listed in $BACKUP_DIR) or an absolute path.
resolve_backup() {
    case "$1" in
        /*) printf '%s\n' "$1" ;;
        *) printf '%s\n' "$BACKUP_DIR/$1" ;;
    esac
}
