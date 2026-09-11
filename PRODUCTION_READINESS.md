Production preparation status
=============================
Database checkpoint: 18f525c (Prepare database layer for PostgreSQL production).
The production changes after that checkpoint are intentionally uncommitted and
unpushed. DEPLOYMENT.md is the current runbook; it supersedes earlier stage notes.

Implemented: 20-character temporary identifiers; dialect-specific user upserts;
SQLite FK enforcement and legacy compatibility; Alembic baseline b9a1e47cb84b;
Redis FSM/event isolation, atomic limits and submission leases; explicit polling
and webhook modes; secret-protected aiohttp handler; dependency health endpoint;
read-only production revision gate; advisory-locked explicit migration job;
Docker/Compose/Caddy files; VPS PostgreSQL and Redis smoke scripts with scoped
cleanup; explicit webhook configuration helper (not run automatically).

Not executed here: local Docker installation, image builds, Compose/Caddy runtime
checks, real PostgreSQL or Redis server tests, VPS deployment, DNS changes,
Telegram webhook configuration, Telegram messages or Git push. These are explicit
VPS gates in DEPLOYMENT.md. SQLite MVP data has not been migrated to PostgreSQL.

Operational limitations: Redis claims and DB writes are not one transaction;
crashes can still cause duplicate creation or missed notifications. See the
runbook's state/delivery limits. The VPS smoke test advances sequences and cleans
only its own negative-ID, tagged test records. Backups and restore rehearsal,
provider firewall and external monitoring remain operator responsibilities.

Final local verification: 97 tests passed; compileall app exit 0. Compose YAML
parses and its port isolation, healthchecks and migration gate pass static tests.
VPS validator service operations and failure cleanup pass against temporary
SQLite; Redis scripts pass with a Lua-capable fake Redis. None of these substitute
for the real-server and image/runtime checks required by DEPLOYMENT.md.
Real bot.db: 2 users, 1 appeal, 1 suggestion, 1 admin contact. Complete rows,
identifiers and schema unchanged; integrity_check ok; foreign_key_check empty.
