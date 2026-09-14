# identifikatsiya-murojaat-bot

Telegram bot skeleton built with aiogram 3.x, SQLAlchemy 2.x (async, SQLite) and python-dotenv.

## Stack

- Python 3.12
- aiogram 3.x
- SQLite
- SQLAlchemy 2.x
- python-dotenv

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in the values:

   ```
   copy .env.example .env
   ```

   - `BOT_TOKEN` — your Telegram bot token from @BotFather
   - `ADMIN_IDS` — comma-separated Telegram user IDs of admins

3. Run the bot:

   ```
   python -m app.main
   ```

## Structure

```
app/
  main.py            # entry point, starts polling
  config.py          # loads BOT_TOKEN and ADMIN_IDS from .env
  database.py         # SQLAlchemy async engine/session setup
  handlers/
    start.py          # /start command handler
  models/              # SQLAlchemy models
  services/            # business logic
```

## Implemented

- `/start` — replies with a welcome message.

## Production preparation

See [DEPLOYMENT.md](DEPLOYMENT.md) for the reviewed VPS workflow and runtime
limitations. Production code is prepared; real PostgreSQL/Redis, Docker and
HTTPS validation are still required on the VPS before cutover.

- Development: BOT_MODE=polling (default), SQLite, optional Redis.
- Production: BOT_MODE=webhook, PostgreSQL + Redis, explicit Alembic migration
  job, aiohttp webhook server and Caddy HTTPS. Startup never registers a webhook.
- Template: .env.production.example; keep the real server env outside the repo.
- Tests: install requirements-dev.txt; run py -m compileall -q app and py -m pytest -q.

## Stage 23 — Admin workflow 2.0

- Two admin roles: SUPERADMIN and ADMIN. `SUPERADMIN_IDS` is the immutable ROOT bootstrap; additional roles are managed from the bot.
- New appeals are broadcast to every admin; the first reply click atomically claims the appeal for 15 minutes.
- All other admin copies lose the reply button after a successful claim; cancel reopens the appeal.
- Suggestions are delivered only to SUPERADMIN users and have a single one-time `Ko‘rib chiqildi` action.
- `/admin` opens the role-aware admin panel with appeals, search and statistics; suggestion views are superadmin-only.

## Stage 24 — Dynamic admins + simplified appeals

- `SUPERADMIN_IDS` contains the immutable ROOT superadmin(s). A ROOT superadmin cannot be removed from Telegram.
- `/admin` → `👥 Админлар` lets any superadmin add DB-managed SUPERADMIN or ADMIN accounts and remove DB-managed accounts.
- SUPERADMIN users receive appeals and suggestions; ADMIN users receive appeals but never suggestion notifications or suggestion controls.
- Removing a dynamic admin also releases their unfinished appeal/admin-contact claim so work is not stranded.
- Citizen appeal flow is intentionally short: direction → appeal text → optional PDF → confirmation. No separate subject is requested.
- New appeal submissions accept PDF only (up to 20 MB); old photo attachments remain displayable for historical records.

## Stage 25 — Web Admin Panel

Production webhook mode now also exposes a protected web admin UI under `/admin/`.
Admins do not use a separate password: open Telegram `/admin`, choose `🌐 Web panel`,
and use the one-time 5-minute login link. The link is single-use; the resulting
HttpOnly/Secure/SameSite session is stored in Redis and re-checks the admin role on
every request.

Web panel v1 includes:
- Dashboard KPIs and recent appeals.
- Appeal search/filter/detail, atomic claim/release, replies and protected PDF viewing.
- User directory (read-only).
- Suggestions for SUPERADMIN only, with one-step `Reviewed` action.
- Dynamic ADMIN/SUPERADMIN management for SUPERADMIN only; ROOT env superadmins stay protected.
- Basic category and region statistics.

All state-changing web actions use CSRF tokens. Telegram admin functionality remains
available in parallel and shares the same database claim/review rules.

## Stage 27 — daily unanswered appeal reminder

In production, the bot schedules a daily reminder at **10:00 Asia/Tashkent**. If there are unanswered `NEW`/`IN_PROGRESS` appeals, every current ADMIN and SUPERADMIN receives one consolidated Telegram warning with counts and the oldest appeal numbers. The run is idempotent per Tashkent calendar day through the existing Redis-backed lease mechanism, so duplicate scheduler tasks do not create duplicate daily warnings. No message is sent when there are zero unanswered appeals.
