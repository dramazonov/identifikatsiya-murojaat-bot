from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./bot.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    async with engine.begin() as conn:
        # Creates the table (with the full current schema) if it does not exist yet.
        # If it already exists, create_all leaves it untouched -- existing data is preserved.
        await conn.run_sync(Base.metadata.create_all)

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
