"""Explicit PostgreSQL release job, serialized with a session advisory lock."""
import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.database import engine


async def migrate():
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Production migration job requires PostgreSQL")
    try:
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT pg_advisory_lock(724198301)")
            await conn.commit()
            try:
                def upgrade(connection):
                    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
                    cfg.attributes["connection"] = connection
                    command.upgrade(cfg, "head")
                await conn.run_sync(upgrade)
                await conn.commit()
            finally:
                await conn.rollback()
                await conn.exec_driver_sql("SELECT pg_advisory_unlock(724198301)")
                await conn.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(migrate())
    except Exception:
        raise SystemExit("Migration failed; check database readiness and reviewed migrations (credentials omitted)")
