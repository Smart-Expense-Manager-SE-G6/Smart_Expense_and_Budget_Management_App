#!/bin/sh
# TC-Backup-02 (NFR10): scheduled backups are rotated, labelled backups are kept.
#
#   docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm -T backup /scripts/retention_test.sh
#
# Works in a scratch folder, so the real backups are not touched. Takes four scheduled
# backups with BACKUP_KEEP=2 plus one labelled backup, then checks that only the newest two
# scheduled backups remain, the labelled one survives, and LATEST names the newest.
set -u   # no -e: a failed check is counted, not fatal

scratch="$(mktemp -d /tmp/retention.XXXXXX)"
trap 'rm -rf "$scratch"' EXIT
export BACKUP_DIR="$scratch" BACKUP_KEEP=2
failures=0
check() { if [ "$2" = 0 ]; then echo "PASS  $1"; else echo "FAIL  $1"; failures=$((failures + 1)); fi; }
regular() { ls -1 "$BACKUP_DIR" | grep -E '^[0-9]{8}T[0-9]{6}Z$' | sort; }

BACKUP_LABEL=manual /scripts/backup.sh > /dev/null || exit 1
for i in 1 2 3 4; do /scripts/backup.sh > /dev/null || exit 1; sleep 1; done

echo "Backups after four scheduled runs with BACKUP_KEEP=2:"
ls -1 "$BACKUP_DIR" | sed 's/^/  /'

[ "$(regular | wc -l)" -eq 2 ]; check "only the newest 2 scheduled backups are kept" $?
ls -1 "$BACKUP_DIR" | grep -q -- '-manual$'; check "the labelled backup is never pruned" $?
[ "$(cat "$BACKUP_DIR/LATEST")" = "$(regular | tail -1)" ]; check "LATEST names the newest scheduled backup" $?
newest="$BACKUP_DIR/$(regular | tail -1)"
(cd "$newest" && sha256sum -c -s SHA256SUMS); check "the newest backup passes its checksum" $?

if [ "$failures" = 0 ]; then echo; echo "Retention test PASSED"; else echo; echo "Retention test FAILED: $failures check(s)"; exit 1; fi
