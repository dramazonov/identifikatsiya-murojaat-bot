"""Test-session setup: points the app at an isolated SQLite database.

This MUST run before ``app.database`` is imported by anything -- that module
reads the ``DATABASE_URL`` env var once, at import time, to build its engine
(see app/database.py). Setting it here, at conftest.py's module level (rather
than inside a fixture), wins the race against pytest's own test collection,
which imports test modules -- and whatever they import -- before any fixture
runs.

This never touches the real ``./bot.db`` that the running bot process uses:
every DB-touching test in this suite reads/writes only this temp-directory
copy.
"""

from __future__ import annotations

import os
import tempfile

_test_db_dir = tempfile.mkdtemp(prefix="bot_test_db_")
_test_db_path = os.path.join(_test_db_dir, "test_bot.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db_path}"

os.environ["REDIS_URL"] = ""
os.environ["BOT_MODE"] = "polling"

import pytest_asyncio  # noqa: E402  (must follow the isolated DATABASE_URL above)


@pytest_asyncio.fixture(autouse=True)
async def _init_test_database() -> None:
    """Create the schema in the isolated test database before each test.

    Function-scoped (not session-scoped) so it always runs in the same
    per-test event loop as the test itself -- no extra event-loop-scope
    configuration needed. ``init_db()`` is safe to call repeatedly (create_all
    only creates missing tables; the migration helpers are no-ops once the
    columns already exist), so this stays cheap across the whole suite.
    """
    from app.database import init_db

    await init_db()
