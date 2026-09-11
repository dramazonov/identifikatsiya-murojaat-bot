"""Real Redis smoke test using a unique namespace, cleaned on exit."""
import asyncio
import uuid

from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.base import DefaultKeyBuilder, StorageKey
from app.config import BOT_TOKEN  # loads .env; never printed or used for API calls
from app.runtime import Settings
from app.services import shared_state


async def main():
    settings = Settings.from_env()
    if not settings.redis_url:
        raise RuntimeError("REDIS_URL required")
    redis = Redis.from_url(settings.redis_url, socket_timeout=5)
    prefix = "identifikatsiya:validation:" + uuid.uuid4().hex
    shared_state.configure(redis, prefix)
    try:
        await redis.ping()
        results = await asyncio.gather(*(shared_state.is_rate_limited("test", limit=3, window_seconds=60) for _ in range(20)))
        if results.count(False) != 3:
            raise RuntimeError("Atomic limit failed")
        leases = await asyncio.gather(*(shared_state.acquire_submission("test") for _ in range(20)))
        owners = [token for token in leases if token]
        if len(owners) != 1:
            raise RuntimeError("Deduplication failed")
        await shared_state.finish_submission("test", owners[0])
        if await shared_state.acquire_submission("test") is not None:
            raise RuntimeError("Completion was not retained")
        storage = RedisStorage(redis, key_builder=DefaultKeyBuilder(prefix=prefix), state_ttl=60, data_ttl=60)
        key = StorageKey(bot_id=1, chat_id=1, user_id=1)
        await storage.set_state(key, "validation")
        if await storage.get_state(key) != "validation":
            raise RuntimeError("FSM persistence failed")
        print("PASS: real Redis Lua rate limiting, submission leases and FSM storage")
    finally:
        async for key in redis.scan_iter(match=prefix + ":*"):
            await redis.delete(key)
        shared_state.configure()
        await redis.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        raise SystemExit("Redis validation failed (connection details omitted)")
