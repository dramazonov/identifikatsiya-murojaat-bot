"""Alembic migration environment (Stage 11 / instruction #5).

Wired to:
- ``app.database.Base.metadata`` as the single source of truth for
  autogenerate (after importing ``app.models`` so every model actually
  registers its table -- same ``# noqa: F401`` trick app/main.py already
  uses).
- The ``DATABASE_URL`` environment variable (instruction #7), read fresh on
  every run rather than baked into alembic.ini -- so ``py -m alembic upgrade
  head`` targets whatever database the app itself is currently configured
  for (SQLite today, PostgreSQL later), with no env.py edits either way.
  Falls back to the same default as app/database.py (./bot.db) when unset.

Uses SQLAlchemy's async-engine recipe (this app's engine is async throughout,
via aiosqlite/asyncpg) rather than the sync template alembic init generated:
migrations still run as plain sync functions (Alembic itself has no async
API), executed through ``AsyncConnection.run_sync`` inside an event loop
alembic drives with ``asyncio.run``.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from app.database_url import database_options, create_database_engine

from alembic import context
from app.database import Base  # also loads .env, without overriding the environment

# This is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging. This line sets up loggers
# basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL overrides whatever static placeholder sits in alembic.ini
# (instruction #7) -- read at run time, not import time, so tests can
# monkeypatch it per-call (see tests/test_alembic_baseline.py).
_normalized_url, _connect_args = database_options(
    os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")
)
config.set_main_option(
    "sqlalchemy.url", _normalized_url.render_as_string(hide_password=False).replace("%", "%%")
)

# Import every model so it registers its table on Base.metadata before
# autogenerate reads it -- mirrors the `# noqa: F401` import block in
# app/main.py, which exists for exactly this reason.
from app.models import (  # noqa: E402,F401
    AdminContact,
    BotAdmin,
    Appeal,
    Suggestion,
    User,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an
    Engine is acceptable here as well. By skipping the Engine creation we
    don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script
    output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # render_as_batch=True is required for SQLite: it can't ALTER a column/
    # constraint in place, so Alembic instead recreates the table under the
    # hood (copy -> drop -> rename) whenever a future migration needs to.
    # Harmless (and unused) for PostgreSQL, which supports ALTER directly --
    # left unconditional so the same env.py needs no per-dialect branching.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an AsyncEngine and associate a
    connection with the context.
    """
    connectable = create_database_engine(
        os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connection = config.attributes.get("connection")
    if connection is not None:
        do_run_migrations(connection)
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
