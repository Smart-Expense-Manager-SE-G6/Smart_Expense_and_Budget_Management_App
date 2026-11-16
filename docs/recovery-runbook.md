# Recovery Runbook (S3-18)

- **Covers:** FR22 (backup and restore), NFR10 (daily backups), SRS 5.8.2 ("an admin can trigger a restore"), use case "Backup or Restore Data" (Admin)
- **Who runs it:** the system operator, which is the use-case diagram's Admin: a team member with SSH access to the production VM and the backup passphrase.
- **Setup and day-to-day operation:** [deployment.md](deployment.md)

## Recovery objectives

| Objective | Target | How it is met |
|:--|:--|:--|
| **RPO** (most data that can be lost) | 24 hours | Daily backup at 02:00 UTC, plus an extra backup on start whenever the newest one is over 24 hours old. Take a manual backup before risky changes. |
| **RTO** (time to be back online) | 1 hour | Measured: **11 seconds** of recovery work once a server exists (drill below). A fresh VM takes about 15–30 minutes to create and install. |
| Copies kept | 7 local + 7 encrypted off-site | `BACKUP_KEEP`, `OFFSITE_KEEP` |
| Proof that backups restore | Weekly | Automatic rehearsal every Sunday 03:30 UTC (TC-Backup-01), plus on every pull request in CI |

## What is backed up

Every backup is one folder: the database dump (`db.dump`), all receipt files (`media.tar.gz`), every table's row count, and SHA-256 checksums. Each night:
1. `backup.sh` writes the folder into `backups/` on the VM.
2. `offsite_copy.sh` encrypts the whole folder with AES-256 (PBKDF2, 600,000 rounds) using `BACKUP_PASSPHRASE`, and writes `<name>.tar.gz.enc` plus its checksum to `OFFSITE_PATH`.

The server alone cannot protect against losing the server, so **`OFFSITE_PATH` must be storage outside the VM**:

- **Azure:** create a Storage Account and a file share, then mount it on the VM at `/mnt/offsite` using the "Connect" instructions in the portal (SMB, mounted from `/etc/fstab`). Azure Storage is encrypted at rest.
- **AWS:** create a private S3 bucket and mount it at `/mnt/offsite` with Mountpoint for Amazon S3 (`mount-s3 <bucket> /mnt/offsite --allow-delete`). S3 encrypts objects at rest by default.

The copies are encrypted before they leave the server, so the storage provider never sees financial data in clear text (NFR14).

**The passphrase.** Store `BACKUP_PASSPHRASE` in a password manager shared by the team, not only on the server. Without it, the off-site copies cannot be decrypted. Rotating it affects new copies only; keep the old passphrase until the last copy made with it has expired (7 days).

All commands below run on the VM, in the repository folder, with:

```bash
c="docker compose -f docker-compose.prod.yml --env-file .env.prod"
```

## Scenario A: undo a bad change (server is fine)

For example, someone deleted data by mistake, or a release damaged data.

```bash
$c run --rm backup /scripts/restore.sh            # lists the backups, newest first
$c stop backend scheduler
$c run --rm backup /scripts/restore.sh 20261116T020000Z   # type the database name to confirm
$c start backend scheduler
deploy/smoke_test.sh https://<domain>
```

`restore.sh` first takes a `*-pre-restore` safety backup, so the restore itself can be undone the same way. Data entered after the chosen backup is lost; tell users which time the data was restored to.

## Scenario B: the server or its disk is lost

1. **Create a new VM and install** as in [deployment.md](deployment.md) steps 1–3, but **do not start the stack yet**. Put the same `.env.prod` back (from the team's password manager), and mount the off-site storage at `OFFSITE_PATH`.
2. **Start only the database:**
   ```bash
   $c up -d db
   ```
3. **Fetch, decrypt and verify the newest off-site copy:**
   ```bash
   $c run --rm --no-deps backup /scripts/offsite_fetch.sh
   ```
   It checks the copy's checksum, decrypts it, checks every file inside, and prints the backup name. A wrong passphrase or a damaged copy stops here with an error. To use an older copy, give its file name: `offsite_fetch.sh 20261115T020000Z.tar.gz.enc`.
4. **Restore it:**
   ```bash
   $c run --rm --no-deps backup /scripts/restore.sh --yes <backup name from step 3>
   ```
5. **Start everything and check:**
   ```bash
   $c up -d
   deploy/smoke_test.sh https://<domain>
   ```
   If the VM has a new IP address, update the DNS record first; Caddy gets a new certificate by itself.
6. **Record** the time of the backup used (this is the data loss) and how long recovery took.

## Scenario C: check backups are healthy (weekly, 2 minutes)

```bash
$c ps backup                                          # must say "healthy" (a backup in the last 25 hours)
$c logs --since 168h backup | grep -E "Backup complete|Off-site copy complete|PASSED|ERROR"
ls -l /mnt/offsite                                    # one .tar.gz.enc per day, at most 7
```

The Sunday rehearsal must show `TC-Backup-01 PASSED`. If anything failed, run it by hand:

```bash
$c run --rm backup /scripts/rehearse_restore.sh       # takes a fresh backup and restores it into a scratch database
```

## Drill record: 16 Nov 2026 (local production stack)

The drill ran the production images (`docker-compose.prod.yml`) on one machine, with `OFFSITE_PATH` as a local folder standing in for cloud storage.

| Step | Result |
|:--|:--|
| Data before | 9 users, **20,506 expenses**, 32 budgets, 35 audit entries, 5 receipt files |
| Nightly job (backup + encrypted off-site copy) | 2 s; 416 KB backup, 332 KB encrypted copy, which starts `Salted__` and is unreadable without the passphrase |
| **Disaster** | `docker compose down -v` (database, receipts and static volumes deleted) and the local `backups/` folder deleted. Only the off-site copy remained. |
| Start an empty database | 2 s |
| Fetch, checksum, decrypt, verify | 1 s |
| Restore database and receipts | 2 s |
| Start the app | 6 s |
| **Total recovery time** | **11 seconds** |
| Data after | Identical: every row count, and all 5 receipt files (same SHA-256 checksums) |
| App checks | The drill user logs in; their 3 receipts download with the original content; `smoke_test.sh` passes 16/16 |
| Weekly rehearsal job | `TC-Backup-01 PASSED`: 18 tables and 5 receipt files match |
| Scheduler after recovery | Took a new backup and off-site copy at once, because none was less than 24 hours old |

Issues found by the drill and fixed:
- After a restore, `LATEST` pointed at the pre-restore safety backup, which in a disaster is a backup of an empty database. The weekly rehearsal and the next off-site copy would have used it. `LATEST` now only names regular backups.
- Two backups started within the same second clashed (fixed in #91).

The real off-site storage, the production VM and the timing on it remain to be recorded once the VM exists.
