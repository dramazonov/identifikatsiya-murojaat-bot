Production readiness audit ? 2026-09-11
========================================
Current: aiogram polling; SQLAlchemy async; SQLite/aiosqlite; WAL, 5-second busy
 timeout and per-connection foreign key enforcement. FSM, rate limiting and
idempotency are process-local memory. No Docker or webhook server is present.

Stage 11: database compatibility groundwork is present (environment URL,
SQLite-specific guards, UTC asyncpg settings, baseline, unique indexed business
identifiers, FK declarations and save_user upsert). Real PostgreSQL remains
unverified. Python observed: 3.13.15; README's 3.12 is historical.

Stage 12: real SQLite already at b9a1e47cb84b before this session. Completed
admin-contact helper wiring; retained profile/location upserts and legacy
SQLite patches; hardened test isolation and database/Alembic .env parity;
covered concurrent and mixed writes and direct initialization. No live DB
migration or application write performed. The previously existing backup is
bot.db.backup_STAGE12_20260910_171830 (40960 bytes); existence observed, restore
fitness not established by this audit. No new backup needed because no DB
mutation was needed. Both Python process checks found no running Python bot;
no process was started, stopped or restarted.

Stage 13 ? real PostgreSQL (not production-ready yet)
Temporary-number length blocker fixed in Stage 13: all three services now use
TMP- plus secrets.token_urlsafe(12), exactly 20 ASCII characters and 96 random
bits. Existing VARCHAR(20) columns and final MUR-/TAK-/ADM- formats are unchanged.
No schema migration was needed. Random generation is not guaranteed unique:
for one million generated values, the birthday collision bound is about
6.3e-18; only overlapping temporary values in the same table can conflict.
The UNIQUE index remains authoritative. A collision raises IntegrityError and
rolls back the entire operation; there is no automatic collision retry. It
cannot silently overwrite another submission. Placeholders are replaced in
the same transaction before commit.

Stage 13 validation attempt: asyncpg 0.30.0 installed and import verified.
Docker CLI and Compose unavailable on PATH; standard system/user Docker binary
locations also absent. Docker was not installed. No PostgreSQL container or
volume was created, so no cleanup was necessary. Real PostgreSQL Alembic and
service integration validation were NOT run, per the requested stop condition.
The length defect is fixed, but PostgreSQL readiness and Redis-stage readiness
remain NO until real PostgreSQL validation succeeds.

SQLite regression: 76 tests passed; compileall exit 0. Ten new tests cover the
helper and actual INSERT values, concurrent submissions and rollback for all
three services. Real bot.db counts remain 2 users, 1 appeal, 1 suggestion and
1 admin contact; complete rows/identifiers and schema unchanged; integrity ok;
foreign_key_check empty; revision remains b9a1e47cb84b. Evidence files:
audit_stage13_before.json and audit_stage13_after.json.

Provision an isolated PostgreSQL test instance and install/verify asyncpg.
Run baseline upgrade, schema comparison and real integration tests for user
upserts, simultaneous contacts, admin claims, FK enforcement, UTC timestamps
and initialization. The current suite deliberately forces temporary SQLite;
add a separate opt-in PostgreSQL test target, never reuse production credentials.
Rehearse importing a SQLite backup, preserve IDs/business numbers, reset PG
sequences to imported maxima, verify rows/FKs/counts, and test backup restore.
Decide pool sizes and migration ownership before any production cutover.

Stage 14 ? Redis (not ready)
Add Redis dependency and environment configuration; wire RedisStorage with
appropriate key namespaces/TTLs and FSM event isolation. Convert the synchronous
rate-limit/idempotency helpers AND handler call sites to async Redis operations.
Use atomic operations/scripts for limits. Track in-progress versus completed
updates and release/retry failed work; the current memory guard marks work
before successful persistence and loses state on restart. Test multiple
workers, duplicates, failures, TTLs, restart persistence and Redis outages.
For external Telegram delivery, define retry/outbox behavior: DB commit and
message delivery are not one transaction, so Redis alone cannot guarantee
exactly-once effects. Current 429 retries/splitting do not solve that gap.

Stage 15 ? Docker (not implemented)
Add reviewed Dockerfile, dockerignore (exclude secrets/SQLite/backups), pinned
runtime and Compose services for app/PostgreSQL/Redis/proxy. Use persistent
volumes, health checks, non-root app, secret injection, controlled migration
job, logging, restart policy and tested backups/restores. No public DB/Redis
ports in production. Validate locally before deploying.

Stage 16 ? VPS + HTTPS + webhook (not implemented; deployment deferred)
Target: Telegram -> HTTPS -> Caddy/Nginx -> aiogram webhook -> Redis/PostgreSQL.
Implement/test HTTP entry point, webhook secret validation, health endpoint,
shutdown and configuration separating polling from webhook operation. Current
main() calls delete_webhook(drop_pending_updates=True): do not run it during
webhook cutover. Plan domain/DNS/TLS, firewall, monitoring, backups and rollback
on a single VPS. Register webhook only during explicitly authorized cutover.

NEXT SINGLE STEP: make Docker available, then resume Stage 13 validation with
a disposable PostgreSQL 16 container bound only to localhost.

Validation results
------------------
Initial suite: 58 passed. Final suite: 66 passed in 11.61 seconds.
py -m compileall -q app: exit 0. Git diff --check: no whitespace errors.
Real DB before/after: users 2/2, appeals 1/1, suggestions 1/1, contacts 1/1.
All application-row fingerprints and schema entries unchanged; integrity_check
ok; foreign_key_check empty; all four audited duplicate counts and all three
orphan counts zero. Evidence: audit_stage12_before.json / audit_stage12_after.json.
No .env/token edits, DB application/schema writes, bot stops, webhook changes,
commits, pushes or deployment were performed.
