import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer
from aiogram import Bot, Dispatcher
from fakeredis.aioredis import FakeRedis

from app.http_server import create_http_app
from app.runtime import Settings
from app.services import shared_state


def production_settings():
    return Settings(mode="webhook", redis_url="redis://redis:6379/0",
                    base_url="https://example.org", secret="x" * 32)


@pytest.mark.parametrize("field,value", [("mode", "invalid"), ("redis_url", ""),
    ("base_url", "http://example.org"), ("secret", ""), ("path", "/health"), ("port", 0)])
def test_production_rejects_invalid_settings(field, value):
    with pytest.raises(ValueError):
        replace(production_settings(), **{field: value}).validate("postgresql+asyncpg://test")


def test_polling_default_allows_sqlite():
    Settings().validate("sqlite+aiosqlite:///test.db")
    with pytest.raises(ValueError):
        production_settings().validate("sqlite+aiosqlite:///test.db")


async def test_redis_atomic_rate_limit_and_expiry():
    redis = FakeRedis()
    shared_state.configure(redis, "test:rate")
    try:
        results = await asyncio.gather(*(shared_state.is_rate_limited("u", limit=3, window_seconds=60) for _ in range(20)))
        assert results.count(False) == 3
        assert await redis.zcard("test:rate:rate:u") == 3
        assert 0 < await redis.pttl("test:rate:rate:u") <= 60000
        assert not await shared_state.is_rate_limited("other", limit=3, window_seconds=60)
    finally:
        shared_state.configure()
        await redis.aclose()


async def test_redis_submission_lease_completion_and_release():
    redis = FakeRedis()
    shared_state.configure(redis, "test:dedup")
    try:
        tokens = await asyncio.gather(*(shared_state.acquire_submission("one") for _ in range(20)))
        winners = [t for t in tokens if t]
        assert len(winners) == 1
        assert 0 < await redis.ttl("test:dedup:submission:one") <= 300
        assert not await shared_state.finish_submission("one", "wrong-owner", failed=True)
        assert await shared_state.finish_submission("one", winners[0], failed=True)
        token = await shared_state.acquire_submission("one")
        assert token
        assert await shared_state.finish_submission("one", token)
        assert await shared_state.acquire_submission("one") is None
        assert await redis.ttl("test:dedup:submission:one") > 600000
        # Simulate expiry and replacement: stale worker cannot remove successor.
        await redis.delete("test:dedup:submission:one")
        successor = await shared_state.acquire_submission("one")
        assert successor
        assert not await shared_state.finish_submission("one", token, failed=True)
    finally:
        shared_state.configure()
        await redis.aclose()


async def test_redis_outage_does_not_fall_back_to_memory():
    redis = AsyncMock()
    redis.set.side_effect = ConnectionError("offline")
    shared_state.configure(redis)
    try:
        with pytest.raises(ConnectionError):
            await shared_state.acquire_submission("outage")
    finally:
        shared_state.configure()


async def test_webhook_secret_health_and_no_telegram_configuration():
    settings = production_settings()
    bot = Bot("123456:TEST_TOKEN_FOR_UNIT_TEST_ONLY")
    bot.set_webhook = AsyncMock()
    bot.delete_webhook = AsyncMock()
    dp = Dispatcher()
    dp.feed_webhook_update = AsyncMock(return_value=None)
    db, redis, cleanup = AsyncMock(), AsyncMock(), AsyncMock()
    app = create_http_app(settings, dp, bot, db_check=db, redis_check=redis, cleanup=cleanup)
    async with TestClient(TestServer(app)) as client:
        response = await client.get("/health")
        assert response.status == 200
        assert (await response.json())["database"] == "ok"
        response = await client.post(settings.path, json={"update_id": 1})
        assert response.status == 401
        dp.feed_webhook_update.assert_not_called()
        response = await client.post(settings.path, json={"update_id": 1},
                                    headers={"X-Telegram-Bot-Api-Secret-Token": settings.secret})
        assert response.status == 200
        dp.feed_webhook_update.assert_awaited_once()
        db.side_effect = RuntimeError("must-not-leak-credentials")
        response = await client.get("/health")
        assert response.status == 503
        assert "must-not-leak" not in await response.text()
    bot.set_webhook.assert_not_called()
    bot.delete_webhook.assert_not_called()
    cleanup.assert_awaited_once()


async def test_production_init_only_verifies_schema(monkeypatch):
    import app.database as database
    monkeypatch.setenv("BOT_MODE", "webhook")
    verify = AsyncMock()
    monkeypatch.setattr(database, "verify_schema", verify)
    monkeypatch.setattr(database, "_migrate_users_table", AsyncMock(side_effect=AssertionError("legacy migration")))
    await database.init_db()
    verify.assert_awaited_once()


async def test_fsm_redis_state_shared_and_namespaced():
    from aiogram.fsm.storage.redis import RedisStorage
    from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey
    redis = FakeRedis()
    keys = DefaultKeyBuilder(prefix="test:fsm", with_bot_id=True)
    a = RedisStorage(redis, key_builder=keys, state_ttl=86400, data_ttl=86400)
    b = RedisStorage(redis, key_builder=keys, state_ttl=86400, data_ttl=86400)
    key = StorageKey(bot_id=1, chat_id=2, user_id=2)
    try:
        await a.set_state(key, "test-state")
        await a.set_data(key, {"region": "Test"})
        assert await b.get_state(key) == "test-state"
        assert await b.get_data(key) == {"region": "Test"}
        assert await b.get_state(StorageKey(bot_id=99, chat_id=2, user_id=2)) is None
        assert await redis.ttl(keys.build(key, "state")) > 0
    finally:
        await redis.aclose()


async def test_polling_retains_explicit_webhook_deletion(monkeypatch):
    from types import SimpleNamespace
    import app.main as main
    import app.database as database
    bot = AsyncMock()
    dp = SimpleNamespace(storage=AsyncMock(), fsm=SimpleNamespace(events_isolation=AsyncMock()),
                         start_polling=AsyncMock())
    monkeypatch.setattr(main, "runtime_components", lambda settings: (bot, dp, None))
    monkeypatch.setattr(main, "init_db", AsyncMock())
    monkeypatch.setattr(database, "engine", AsyncMock())
    await main.poll(Settings())
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)
    bot.set_webhook.assert_not_called()
    dp.start_polling.assert_awaited_once_with(bot)


@pytest.mark.parametrize("kind", ["appeal", "suggestion", "admin_contact"])
async def test_failed_submission_releases_lease_for_retry(monkeypatch, kind):
    from tests.test_duplicate_action import _make_message, FakeState
    from app.services.user_service import save_user
    import app.handlers.start as start
    import app.handlers.admin_contact as contact
    module = contact if kind == "admin_contact" else start
    handler = getattr(module, "process_admin_contact_message" if kind == "admin_contact" else f"process_{kind}_text")
    telegram_id = 980100000 + ["appeal", "suggestion", "admin_contact"].index(kind)
    await save_user(telegram_id, "test", "Test Person", "+998901234567")
    message = _make_message(telegram_id, 123, "Long valid submission text for retry after database failure.")
    original = getattr(module, f"create_{kind}")
    failed = AsyncMock(side_effect=RuntimeError("DB failure"))
    monkeypatch.setattr(module, f"create_{kind}", failed)
    await handler(message, FakeState())
    failed.assert_awaited_once()
    # The same update can retry after the failed transaction.
    retried = AsyncMock(wraps=original)
    monkeypatch.setattr(module, f"create_{kind}", retried)
    await handler(message, FakeState())
    retried.assert_awaited_once()
    # A third delivery is blocked after the successful commit.
    await handler(message, FakeState())
    retried.assert_awaited_once()
