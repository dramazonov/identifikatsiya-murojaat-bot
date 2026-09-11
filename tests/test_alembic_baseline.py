"""Alembic metadata-consistency check (Stage 11 / instruction #8).

Proves the full migration chain (baseline b9a1e47cb84b through current HEAD
a8b4d6e21c90) builds the same schema the current SQLAlchemy models declare: apply
``alembic upgrade head`` to a brand-new, empty, throwaway SQLite file (never
the real ./bot.db, and never the shared tests/conftest.py database), then
reflect that database back and diff it against app.database.Base.metadata.
An empty diff means "the migration and the models agree" -- the same check
``alembic check`` performs.

Deliberately a plain sync ``def test_...`` (not ``async def``): Alembic has
no async API of its own -- alembic/env.py drives its own event loop via
``asyncio.run(...)`` for the async engine, which raises if called from
*inside* an already-running event loop. pytest-asyncio's ``asyncio_mode =
auto`` only wraps ``async def`` tests, so a plain ``def`` here runs with no
event loop already active, exactly like invoking the ``alembic`` CLI itself.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.database import Base

# Importing app.models is what registers every table on Base.metadata (same
# reason app/main.py and alembic/env.py both do this) -- required so this
# module doesn't silently compare against an empty metadata if it's ever the
# first thing in the process to touch app.database.Base.
import app.models  # noqa: F401,E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_alembic_baseline_matches_current_models(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "alembic_baseline_check.db"
    db_url = f"sqlite:///{db_path}"

    # alembic/env.py reads DATABASE_URL itself (Stage 11 / instruction #7);
    # point it at this throwaway file for the duration of this test only.
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")

    alembic_cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    sync_engine = create_engine(db_url)
    try:
        table_names = set(inspect(sync_engine).get_table_names())

        with sync_engine.connect() as connection:
            migration_context = MigrationContext.configure(connection)
            diff = compare_metadata(migration_context, Base.metadata)
    finally:
        sync_engine.dispose()

    # Ignore Alembic's own bookkeeping table -- it's not part of the app's
    # schema and every fresh `alembic upgrade head` creates it.
    diff = [
        entry
        for entry in diff
        if not (
            len(entry) >= 2
            and hasattr(entry[1], "name")
            and entry[1].name == "alembic_version"
        )
    ]

    assert diff == [], f"models and the migration chain disagree: {diff!r}"

    # Sanity check the reflection actually saw the real tables (a silently
    # empty/mis-pointed DATABASE_URL would otherwise make the diff trivially
    # empty for the wrong reason).
    assert {"users", "appeals", "suggestions", "admin_contacts", "bot_admins"} <= table_names


def test_alembic_url_with_percent_and_stamp_preserves_data(tmp_path, monkeypatch):
    import sqlite3

    db_path = tmp_path / "percent%database.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    sync_engine = create_engine(f"sqlite:///{db_path}")
    try:
        Base.metadata.create_all(sync_engine)
        with sync_engine.begin() as connection:
            connection.exec_driver_sql("INSERT INTO users (telegram_id, full_name) VALUES (999, 'Keep')")
    finally:
        sync_engine.dispose()
    with sqlite3.connect(db_path) as connection:
        before = connection.execute("SELECT * FROM users").fetchall()
        schema = connection.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name").fetchall()
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    command.stamp(cfg, "head")
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT * FROM users").fetchall() == before
        assert connection.execute("SELECT version_num FROM alembic_version").fetchall() == [("a8b4d6e21c90",)]
        after = connection.execute("SELECT type, name, sql FROM sqlite_master WHERE tbl_name != 'alembic_version' ORDER BY type, name").fetchall()
        assert after == schema


def test_postgresql_baseline_compiles_offline(monkeypatch):
    from io import StringIO

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://example:encoded%25@localhost/example")
    output = StringIO()
    cfg = Config(str(REPO_ROOT / "alembic.ini"), output_buffer=output)
    command.upgrade(cfg, "head", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE users" in sql
    assert "SERIAL" in sql
    assert "PRAGMA" not in sql
    assert "a8b4d6e21c90" in sql
