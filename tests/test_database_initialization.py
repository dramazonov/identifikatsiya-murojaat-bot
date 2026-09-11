"""Fresh-process startup must register models and preserve existing data."""
import os
import subprocess
import sys


def test_direct_init_db_is_repeatable_and_enforces_fk(tmp_path):
    env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{tmp_path / 'init.db'}")
    code = '''
import asyncio
from app.database import engine, init_db
async def check():
    await init_db()
    async with engine.begin() as c:
        assert (await c.exec_driver_sql('PRAGMA foreign_keys')).scalar() == 1
        await c.exec_driver_sql('INSERT INTO users (telegram_id) VALUES (12345)')
    await init_db()
    async with engine.connect() as c:
        assert (await c.exec_driver_sql('SELECT telegram_id FROM users')).scalars().all() == [12345]
        assert (await c.exec_driver_sql('PRAGMA foreign_key_check')).all() == []
        tables = set((await c.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'")).scalars())
        assert {'users', 'appeals', 'suggestions', 'admin_contacts', 'bot_admins'} <= tables
    await engine.dispose()
asyncio.run(check())
'''
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
