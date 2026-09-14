# Single-VPS production deployment

These commands are for a **new Ubuntu 24.04 LTS x86-64 VPS**, not Windows.
Nothing in this runbook has been executed on a VPS. Local Docker was intentionally
not installed. PostgreSQL/Redis server validation, container build, Compose and
Caddy runtime checks must pass here before webhook registration.

Initial operating minimum: 2 vCPU, 2 GiB RAM, 25 GiB SSD, a public IPv4 address,
root/sudo SSH access and a domain/subdomain you control. Prefer 4 GiB RAM and
40 GiB SSD for build headroom and retained backups. This is a starting capacity
budget, not a measured traffic guarantee. Obtain the SSH host-key fingerprint,
SSH user/port, provider firewall access and backup/snapshot facilities.

Only TCP 80/443 are published by this stack. Restrict SSH at the provider firewall
to your administration IP. Permit outbound DNS and HTTPS for Telegram, registries
and certificate issuance. Do not expose 5432, 6379, 8080 or Caddy admin port 2019.

## 1. Install Docker on the VPS

Use a fresh host without conflicting Docker/containerd packages. For an existing
host, inspect workloads and follow Docker's conflict-resolution instructions
before replacing packages. The repository-based installation follows
[Docker's Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker --version
sudo docker compose version
```

## 2. Obtain the reviewed release

The local database checkpoint is `18f525c`. **It does not contain the subsequent
production files.** No push was performed. Before cloning, explicitly approve
and publish a reviewed release commit containing this runbook and production
files, or arrange a reviewed source transfer. Do not deploy an older remote HEAD.
Replace `REVIEWED_PRODUCTION_COMMIT_SHA` below with that release's exact SHA.

```bash
sudo install -d -o "$USER" -g "$(id -gn)" /opt/identifikatsiya
git clone https://github.com/dramazonov/identifikatsiya-murojaat-bot.git /opt/identifikatsiya
cd /opt/identifikatsiya
git checkout --detach REVIEWED_PRODUCTION_COMMIT_SHA
test -f docker-compose.production.yml
test -f scripts/validate_postgres.py
```

Use a deploy key or your normal Git credential mechanism if the repository is
private. Never embed credentials in the clone URL or the image.

## 3. Create a separate server environment

Do not copy the Windows `.env`, database, or backups into the image.

```bash
sudo install -d -m 700 /etc/identifikatsiya
if sudo test -e /etc/identifikatsiya/production.env; then
  echo "Existing server env retained; edit deliberately."
else
  sudo install -m 600 .env.production.example /etc/identifikatsiya/production.env
fi
sudoedit /etc/identifikatsiya/production.env
```

Stop if the file already exists; edit it deliberately rather than overwriting it.
Populate the new file in the editor; do not paste secrets into chat or shell
commands. Use a password manager to generate a long URL-safe PostgreSQL password
and an independent 32-256 character `[A-Za-z0-9_-]` webhook secret. Values:

| Variable | Server value |
|---|---|
| BOT_TOKEN | Existing token, entered privately |
| ADMIN_IDS | Authorized admins' comma-separated Telegram IDs |
| BOT_MODE | `webhook` |
| POSTGRES_DB | `identifikatsiya` |
| POSTGRES_USER | `identifikatsiya` |
| POSTGRES_PASSWORD | Generated password |
| DATABASE_URL | `postgresql+asyncpg://identifikatsiya:GENERATED_PASSWORD@postgres:5432/identifikatsiya` |
| REDIS_URL | `redis://redis:6379/0` |
| BOT_DOMAIN | Your real bot subdomain, without scheme/path |
| WEBHOOK_BASE_URL | `https://` followed by that subdomain |
| WEBHOOK_PATH | `/telegram/webhook` |
| WEBHOOK_SECRET | Independent generated secret |
| WEB_SERVER_HOST | `0.0.0.0` |
| WEB_SERVER_PORT | `8080` |

Passwords containing URL-reserved characters must be percent-encoded in
DATABASE_URL. A generated hex password avoids URL and Compose interpolation
ambiguities. Do not `source` this file; Compose and the application parse it.
Redis has no password in this initial isolated-network configuration; no host
port is published. PostgreSQL credentials apply when the persistent volume is
first initialized; changing env values later does not change database roles.

Define this helper in each new VPS shell. It keeps credentials out of arguments
and terminal output. Never run bare `docker compose config`, which prints secrets.

```bash
set -euo pipefail
cd /opt/identifikatsiya
dc() { sudo docker compose --env-file /etc/identifikatsiya/production.env -f docker-compose.production.yml "$@"; }
dc config --quiet
dc build bot
```

## 4. Start databases, migrate and validate before traffic

```bash
dc up -d --wait postgres redis
dc run --rm --no-deps migrate
dc run --rm --no-deps bot python -m scripts.validate_postgres --confirm-test-records
dc run --rm --no-deps bot python -m scripts.validate_redis
```

The migration command runs Alembic `upgrade head` under a PostgreSQL advisory
lock; failures exit nonzero and prevent bot startup. The Compose migration job
also gates normal `up` startup. Workers only read/check the revision and never
create tables or run the SQLite compatibility patches in production.

The PostgreSQL validator also upgrades to HEAD, then checks the current Alembic HEAD revision
`c3e9f7a42d11`, model/schema agreement, tables, indexes, unique constraints, FKs,
UTC, service inserts/updates, concurrency, identifier length/format, admin claims,
constraint failures and rollbacks. It uses tagged negative Telegram IDs and
removes only its own records in `finally`. Sequences advance; gaps are expected
and are never reset. Run before live traffic because rollback checks compare
row counts. A killed process or broken connection can interrupt cleanup: inspect
rows tagged `vps-validation-` before rerunning; never truncate production tables.
No Telegram messages are sent by either validator.

**Stop on any failing command.** Do not start Caddy or register a webhook until
both validators pass. Image build and real-server execution were not available
on the Windows development machine.

This initializes a fresh PostgreSQL database; it does **not** import the SQLite
MVP's existing records. If those records must appear in production, first arrange
a separately reviewed transfer from a consistent SQLite backup, preserving IDs,
relationships and public numbers and advancing PostgreSQL sequences. Keep the
original SQLite file intact. Do not treat a fresh database as a completed data
migration.

## 5. DNS, bot and automatic HTTPS

Create an A record for BOT_DOMAIN pointing to the VPS IPv4. Add an AAAA record
only if IPv6 routing/firewall is actually configured; remove stale AAAA records.
Use DNS-only mode initially if a provider offers an HTTP proxy. Verify DNS from
outside the VPS and allow inbound TCP 80/443 in the provider firewall.

```bash
getent ahostsv4 YOUR_BOT_DOMAIN
dc up -d --wait bot
dc exec -T bot python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/health').read().decode())"
dc run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
dc up -d --wait
curl --fail --silent --show-error https://YOUR_BOT_DOMAIN/health
dc ps
```

Caddy routes only WEBHOOK_PATH and `/health` to the bot; all other paths return
404. It obtains/renews certificates automatically once public DNS and port
reachability are correct, following [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).
Certificate/account state persists in named volumes. `/health` returns 200 only
when both DB revision/readiness and Redis respond, or a redacted 503 otherwise.

## 6. Explicit Telegram cutover (operator action only)

Before this step, confirm there is no old polling process using this token.
Stop it only as part of your authorized cutover. Starting local polling later
will delete the webhook and drop pending updates, preserving the old MVP behavior.

Only after HTTPS health and both validation commands pass:

```bash
dc run --rm --no-deps bot python -m scripts.configure_webhook --set
dc run --rm --no-deps bot python -m scripts.configure_webhook --status
```

The helper reads credentials internally; it never prints the token, URL or
secret. It preserves pending updates. Startup and tests never invoke setWebhook.
The server validates `X-Telegram-Bot-Api-Secret-Token` using aiogram's supported
[aiohttp webhook handler](https://docs.aiogram.dev/en/v3.15.0/dispatcher/webhook.html).
Send a manual `/start` after cutover, then submit and answer a test appeal as the
operator. That manual end-to-end check does send Telegram messages.

## 7. Logs, restart, backups and reboot

```bash
dc logs --tail=100 bot migrate caddy
dc restart bot
dc ps
curl --fail --silent --show-error https://YOUR_BOT_DOMAIN/health
dc run --rm --no-deps bot python -m scripts.configure_webhook --status
sudo install -d -m 700 /var/backups/identifikatsiya
backup_file="/var/backups/identifikatsiya/pre-release-$(date -u +%Y%m%dT%H%M%S).dump"
dc exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' | sudo tee "$backup_file" >/dev/null
sudo chmod 600 "$backup_file"
```

Use timestamped filenames for subsequent backups, schedule them daily and copy
encrypted backups off-host. Rehearse `pg_restore` into a **separate empty
database** before relying on the backups. Retain the env file securely off-host
and include Caddy/Redis volumes in the backup plan. A persistent volume alone
is not a backup. Review logs privately; they may include citizen information.

For an approved reboot test:

```bash
sudo reboot
# Reconnect via SSH, redefine dc, then:
sudo systemctl is-active docker
dc ps
curl --fail --silent --show-error https://YOUR_BOT_DOMAIN/health
dc run --rm --no-deps bot python -m scripts.configure_webhook --status
```

Restart policies bring services back; bot startup fails until dependencies and
the expected revision are ready. Compose healthchecks report failure but Docker
does not automatically restart a process merely because it becomes unhealthy;
monitor external health and alert on failed checks, disk usage and backup age.

## 8. Releases and rollback

Before changing code: back up PostgreSQL, record the previous release SHA and
retain the old application image. Tag the current image before rebuilding:

```bash
sudo docker image tag identifikatsiya-bot:local identifikatsiya-bot:rollback
dc stop bot caddy
# Check out the next explicitly reviewed release here.
dc build bot
dc run --rm --no-deps migrate
dc run --rm --no-deps bot python -m scripts.validate_postgres --confirm-test-records
dc up -d --wait
```

For an application-only rollback **whose schema is still compatible**, restore
the previous release checkout (so Compose/Caddy match it), then use the retained
image without running an old migration:

```bash
dc stop bot caddy
git checkout --detach PREVIOUS_REVIEWED_RELEASE_SHA
sudo IMAGE_TAG=rollback docker compose --env-file /etc/identifikatsiya/production.env -f docker-compose.production.yml up -d --no-deps --no-build bot
dc up -d --no-deps --wait caddy
curl --fail --silent --show-error https://YOUR_BOT_DOMAIN/health
```

If schema compatibility is uncertain, keep workers stopped and plan a reviewed
forward fix or restore into a separate database. Never run the baseline
`alembic downgrade`: it drops application tables. Never use `down -v`, prune
volumes, or restore over the only copy of production data. A return to local
SQLite/polling is a separate data-and-webhook cutover, not this image rollback.

## State and delivery limits

Redis FSM keys include the bot ID; state/data expire after 24 hours. Event locks
last up to 300 seconds. Rate limits use atomic Lua sliding windows with TTLs.
Submission claims use SET NX with a 300-second pending lease, owner-checked
release on database failure, and a seven-day completed marker. Redis outages
fail closed; production never silently falls back to process memory. Redis AOF
and a no-eviction policy are enabled; monitor capacity and persistence health.

This provides duplicate protection during normal operation, **not exactly-once
delivery**. A crash after DB commit but before Redis completion can allow another
submission after the lease expires. A failure after completion can omit a user
confirmation/admin notification. Telegram delivery and DB/Redis commits are not
one transaction. Durable DB idempotency keys and an outbox are the next hardening
step if those crash windows are unacceptable. Aiogram can continue slow webhook
handlers in background after its response timeout; this is not a durable queue.

## Development

With no REDIS_URL and BOT_MODE unset (or `polling`), MemoryStorage and in-memory
limits/leases remain available. SQLite still defaults to `./bot.db`, including
safe legacy additive initialization. Tests force temporary SQLite, polling and
no external Redis, and use a Lua-capable fake Redis for atomic-operation tests:

```powershell
py -m pip install -r requirements-dev.txt
py -m compileall -q app
py -m pytest -q
```
