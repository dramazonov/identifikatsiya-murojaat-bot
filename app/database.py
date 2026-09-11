from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# DATABASE_URL is the single source of truth for which database/driver to use
# (Stage 11 / instruction #7), read by both the app and alembic/env.py. Unset
# in normal/current use, so the default below -- the real, unchanged ./bot.db
# via the same SQLite+aiosqlite driver as before -- keeps today's MVP running
# exactly as-is. Tests override it (see tests/conftest.py) to an isolated
# temp-file database instead of this default. Production will set it to a
# PostgreSQL URL, e.g. postgresql+asyncpg://user:pass@host/dbname -- no code
# change needed here, only the env var.
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")


def _connect_args_for(url: str) -> dict:
    """Dialect-specific DBAPI connect kwargs, dispatched off the DATABASE_URL prefix.

    Empty for SQLite (unchanged behavior). For a future PostgreSQL URL, pins
    the asyncpg session's timezone to UTC -- app/services/datetime_utils.py's
    "naive UTC everywhere" storage strategy relies on ``func.now()`` producing
    UTC; SQLite's ``CURRENT_TIMESTAMP`` is always UTC already, but Postgres's
    ``now()`` reflects the session timezone, so without this a non-UTC server/
    session default would silently corrupt every server-generated timestamp.
    """
    if url.startswith("postgresql"):
        return {"server_settings": {"timezone": "UTC"}}
    return {}


engine = create_async_engine(DATABASE_URL, echo=False, connect_args=_connect_args_for(DATABASE_URL))
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    """Apply per-connection SQLite pragmas for concurrency (MVP audit HIGH #4)
    and referential integrity (Stage 11 / instruction #2).

    Guarded to SQLite only (Stage 11 / instruction #4): this "connect" event
    fires for every DBAPI connection regardless of dialect, but ``PRAGMA`` is
    SQLite-only syntax -- running it against a future PostgreSQL connection
    would raise on every single connection. Without this guard, switching
    DATABASE_URL to PostgreSQL would break immediately.

    ``journal_mode=WAL`` lets readers and a writer work concurrently instead
    of SQLite's default rollback-journal mode, where a write blocks readers.
    ``busy_timeout`` makes a writer that finds the database briefly locked by
    another connection *wait* (up to 5s) and retry internally instead of
    immediately raising ``database is locked``. ``foreign_keys=ON`` makes
    SQLite actually enforce the ``ForeignKey`` declarations already present on
    the models (previously declared but never enforced -- see the Stage 10
    audit); a read-only check of the real ./bot.db (PRAGMA foreign_key_check
    + integrity_check, both clean, no orphans) confirmed this is safe to turn
    on without breaking any existing row. None of the three touch existing
    data or the schema. Runs on every new DBAPI connection (SQLAlchemy's
    "connect" event) because ``busy_timeout``/``foreign_keys`` are
    per-connection settings; ``journal_mode=WAL`` is a per-database-file
    setting that only needs to take effect once, but re-issuing it on each
    connect is a harmless no-op after that.
    """
    if engine.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    # Register all tables even when invoked directly, outside app.main.
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        # Creates the table (with the full current schema) if it does not exist yet.
        # If it already exists, create_all leaves it untouched -- existing data is preserved.
        await conn.run_sync(Base.metadata.create_all)

    # SQLite-only (Stage 11 / instruction #6): these patch an already-existing
    # SQLite file created before the column existed, via SQLite-specific
    # ``PRAGMA table_info``/``ALTER TABLE ADD COLUMN``. A fresh PostgreSQL
    # database has no such history -- create_all above already creates every
    # table with every column from the current models -- so running these
    # against PostgreSQL would be both unnecessary and (PRAGMA being SQLite
    # syntax) an immediate crash. Left in place rather than removed: this is
    # still how the real, currently-running ./bot.db gets patched, and Alembic
    # (see alembic/) is not yet wired into this startup path -- see the
    # Stage 11 report for the migration-path plan.
    if engine.dialect.name == "sqlite":
        await _migrate_users_table()
        await _migrate_appeals_table()


async def _migrate_users_table() -> None:
    """Safely add new columns to an already-existing ``users`` table (SQLite).

    ``Base.metadata.create_all`` never alters an existing table, so a bot.db created
    before Stage 3 would be missing the new ``region``/``district`` columns. This adds
    them in place, without touching existing rows.
    """
    async with engine.begin() as conn:
        result = await conn.exec_driver_sql("PRAGMA table_info(users)")
        existing_columns = {row[1] for row in result.fetchall()}

        if "region" not in existing_columns:
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN region VARCHAR(255)")

        if "district" not in existing_columns:
            await conn.exec_driver_sql("ALTER TABLE users ADD COLUMN district VARCHAR(255)")


async def _migrate_appeals_table() -> None:
    """Safely add the Stage 5 admin-reply columns to an already-existing ``appeals`` table.

    Same rationale as ``_migrate_users_table``: ``create_all`` never alters an existing
    table, so a bot.db created before Stage 5 would be missing ``admin_id``/``admin_answer``/
    ``answered_at``. This adds them in place, without touching existing rows.
    """
    async with engine.begin() as conn:
        result = await conn.exec_driver_sql("PRAGMA table_info(appeals)")
        existing_columns = {row[1] for row in result.fetchall()}

        if "admin_id" not in existing_columns:
            await conn.exec_driver_sql("ALTER TABLE appeals ADD COLUMN admin_id BIGINT")

        if "admin_answer" not in existing_columns:
            await conn.exec_driver_sql("ALTER TABLE appeals ADD COLUMN admin_answer TEXT")

        if "answered_at" not in existing_columns:
            await conn.exec_driver_sql("ALTER TABLE appeals ADD COLUMN answered_at DATETIME")
