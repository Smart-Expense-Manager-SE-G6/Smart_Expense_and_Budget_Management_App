# Production Deployment Runbook (S3-10)

- **Covers:** NFR4 (encryption in transit and at rest), NFR9 (uptime), NFR10 (backups), NFR13 (cloud and Docker), FR18 (email)
- **Files:** `docker-compose.prod.yml`, `deploy/` (Dockerfiles, `Caddyfile`, `smoke_test.sh`), `.env.prod.example`

## Demo on this machine (localhost)

The team runs the demo on a laptop, with the same production stack a server would run (R-13 in the [deviation log](deviations.md)). In WSL or Linux with Docker, from the repository root:

```bash
deploy/local-demo.sh            # first run creates .env.prod with random secrets, then starts everything
```

Open **https://localhost**. To avoid the browser's certificate warning, trust Caddy's local certificate once (Windows PowerShell, repository folder):

```powershell
certutil -user -addstore Root caddy-local-root.crt
```

Restart the browser after that. Other commands:
- Check the stack: `deploy/smoke_test.sh https://localhost --insecure`
- Stop, keeping the data: `deploy/local-demo.sh stop`
- Delete all demo data: `deploy/local-demo.sh reset`

Encrypted backup copies go to `./offsite`.

**Run a release instead of building.** Every commit on `main` is deployed and smoke-tested by the CI/CD pipeline, and its images are published to GitHub Container Registry. To run exactly what was tested:

```bash
deploy/local-demo.sh release          # newest commit on main
deploy/local-demo.sh release v1.0     # a tagged release
```

The rest of this document is for putting the same stack on a cloud VM.

## What runs

```text
            Internet
               │  80 / 443 only
         ┌─────▼──────┐   HTTPS (Let's Encrypt), HTTP→HTTPS redirect,
         │    web     │   security headers, strict CSP,
         │  (Caddy)   │   built React app
         └─┬───────┬──┘
   /api/*  │       │  /static/*  (admin CSS and JS)
  /admin/* │       │
     ┌─────▼────┐  │
     │ backend  │──┘  gunicorn, 3 workers, unprivileged user
     └─────┬────┘
           │       ┌───────────┐  ┌──────────┐
           ├───────│ scheduler │  │  backup  │  daily rollover + recurring expenses;
           │       └───────────┘  └────┬─────┘  daily database + receipts backup
     ┌─────▼────┐                      │
     │    db    │◄─────────────────────┘
     │ Postgres │  private Docker network only; never exposed
     └──────────┘
```

- One origin serves both the app and the API, so the session cookie and CSRF model from ADR-0001 work unchanged.
- Only the `web` service publishes ports. The database is never exposed to the internet.

## 1. Choose a host

Any Linux virtual machine with Docker works. NFR13 names AWS, Azure, Heroku and Render. A single VM on **Azure** (Azure for Students includes free credit) or **AWS** (EC2) is recommended, because the whole stack, including the backup service and the receipts disk, runs exactly as tested.

| Need | Minimum |
|:--|:--|
| VM size | 2 vCPU, 2 GB RAM (Azure B2s, AWS t3.small) |
| OS | Ubuntu 24.04 LTS |
| Disk | 30 GB |
| Open ports | 22 (SSH, your IP only), 80, 443 |

**Encryption at rest (NFR4).** The database, receipts and backups live on the VM's disk, so the disk must be encrypted:
- **Azure:** managed disks are encrypted at rest by default (server-side encryption with platform-managed keys). Nothing to turn on; record it in the evidence below.
- **AWS:** tick **"Encrypt this volume"** for the EBS root volume when launching the instance (or turn on EBS encryption by default for the region first).

Render was considered but not chosen: its free tier has no persistent disk, so uploaded receipts and the backup service would not survive a restart. This is recorded in the deviation log.

## 2. Domain name

Point a domain's DNS **A record** at the VM's public IP. With no domain, use the free sslip.io name of the IP: for `20.193.10.5` that is `20-193-10-5.sslip.io`. Caddy gets a real Let's Encrypt certificate for either.

## 3. Install and start

```bash
# On the VM
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER" && newgrp docker

git clone https://github.com/Smart-Expense-Manager-SE-G6/Smart_Expense_and_Budget_Management_App.git
cd Smart_Expense_and_Budget_Management_App
cp .env.prod.example .env.prod
nano .env.prod      # set SITE_ADDRESS, DJANGO_ALLOWED_HOSTS, DJANGO_CSRF_TRUSTED_ORIGINS,
                    # DJANGO_SECRET_KEY, POSTGRES_PASSWORD, email settings
chmod 600 .env.prod

docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

Generate each secret with `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`. `.env.prod` is git-ignored; never commit it.

Create an admin account for the Django admin site (audit trail, data fixes):

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py createsuperuser
```

## 4. Verify (acceptance criteria of S3-10)

```bash
deploy/smoke_test.sh https://<your domain>
```

It checks, with a throwaway account it creates and deletes:
- HTTP redirects to HTTPS, and the certificate is trusted;
- HSTS, CSP, no `Server` header from the API, no caching of API responses;
- the app, deep links, the health endpoint and admin static files load;
- register, logout, login, session cookie flags, add an expense, a report, and delete the account.

Then:
- `docker compose -f docker-compose.prod.yml --env-file .env.prod exec backend python manage.py check --deploy` must report no issues.
- Open the site in a browser, add an expense with a receipt and a budget, and download a PDF report.
- Trigger an alert (spend over 80% of a budget) and confirm the email arrives (FR18).
- Record the evidence (URL, date, smoke test output, `check --deploy` output, disk encryption setting) in the Test Summary Report (S3-20).

## 5. Email (FR18)

Set the `EMAIL_*` values in `.env.prod`. Brevo's free SMTP relay (300 emails a day) works with the defaults: create an account, create an SMTP key, and set `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` and a verified `DEFAULT_FROM_EMAIL`. Users can turn alert emails off in their profile; in-app alerts always appear.

## 6. Backups and restore

The `backup` service backs up the database and receipts daily into `./backups/` on the VM, copies each backup encrypted to off-site storage (`OFFSITE_PATH`), and rehearses a restore every Sunday. Setting up the off-site storage, the passphrase and every restore scenario: [recovery-runbook.md](recovery-runbook.md).

## 7. Updating

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
deploy/smoke_test.sh https://<your domain>
```

Migrations run automatically when the backend starts. Take a backup first for any release with migrations:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm backup /scripts/backup.sh
```

To roll back, `git checkout <previous tag or commit>` and run the same `up -d --build`. Restore the pre-update backup if the release changed the database.

## 8. Logs and health

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend web    # request ID on every API log line
curl -s https://<your domain>/api/v1/health/
```

An external uptime check on `/api/v1/health/` (NFR9) is set up under S3-17 (#79).

## Local rehearsal (done 16 Nov 2026)

The production stack was run locally exactly as above, with `SITE_ADDRESS=localhost` so Caddy uses its own certificate:

| Check | Result |
|:--|:--|
| `deploy/smoke_test.sh https://localhost --insecure` | 16/16 pass |
| Full browser suite (Edge, 16 scenarios incl. receipts, reports, session expiry, phone widths) under the strict CSP | 16/16 pass, no console errors |
| OWASP ZAP baseline, app and API over HTTPS | 0 FAIL each; only informational warnings (no COEP, which needs cross-origin isolation the app does not use; cache notes on hashed assets) |
| Backend runs as an unprivileged user (uid 10001); receipts writable after the backup service touched the volume | Pass |

Found and fixed during the rehearsal:
- The receipts volume could end up owned by root, which made uploads fail with 500. The backend entrypoint now fixes ownership on start, then drops privileges.
- Scanners that send no SNI could not connect. Caddy now has `default_sni`.

The live checks on the real host (trusted certificate, real email, disk encryption) remain for when the VM exists.
