from __future__ import annotations

"""Remember admin notification message ids so Stage 23 can update every copy.

Redis is used in production; an in-memory fallback keeps local development and
unit tests deterministic. The mapping is deliberately ephemeral metadata: if
it is lost, database claim guards still prevent double handling. Keeping this
out of the relational schema avoids coupling official appeal data to Telegram
message ids.
"""

import json
import time
from typing import Any

from app.services import shared_state

_TTL_SECONDS = 7 * 24 * 60 * 60
_memory: dict[str, tuple[dict[str, Any], float]] = {}


def _key(kind: str, object_id: int) -> str:
    return f"{kind}:{object_id}"


async def remember_notification(kind: str, object_id: int, admin_id: int, chat_id: int, message_id: int) -> None:
    key = _key(kind, object_id)
    redis = getattr(shared_state, "_redis", None)
    namespace = getattr(shared_state, "_namespace", "identifikatsiya:dev")
    payload = json.dumps({"chat_id": chat_id, "message_id": message_id})
    if redis is not None:
        redis_key = f"{namespace}:admin_notifications:{key}"
        await redis.hset(redis_key, str(admin_id), payload)
        await redis.expire(redis_key, _TTL_SECONDS)
        return

    now = time.monotonic()
    for stale in [k for k, (_v, expiry) in _memory.items() if expiry <= now]:
        _memory.pop(stale, None)
    bucket, _expiry = _memory.get(key, ({}, now + _TTL_SECONDS))
    bucket[str(admin_id)] = {"chat_id": chat_id, "message_id": message_id}
    _memory[key] = (bucket, now + _TTL_SECONDS)


async def list_notifications(kind: str, object_id: int) -> dict[int, dict[str, int]]:
    key = _key(kind, object_id)
    redis = getattr(shared_state, "_redis", None)
    namespace = getattr(shared_state, "_namespace", "identifikatsiya:dev")
    if redis is not None:
        raw = await redis.hgetall(f"{namespace}:admin_notifications:{key}")
        result: dict[int, dict[str, int]] = {}
        for admin_id, payload in raw.items():
            aid = int(admin_id.decode() if isinstance(admin_id, bytes) else admin_id)
            text = payload.decode() if isinstance(payload, bytes) else payload
            parsed = json.loads(text)
            result[aid] = {"chat_id": int(parsed["chat_id"]), "message_id": int(parsed["message_id"])}
        return result

    bucket, expiry = _memory.get(key, ({}, 0))
    if expiry <= time.monotonic():
        _memory.pop(key, None)
        return {}
    return {int(aid): dict(info) for aid, info in bucket.items()}


async def clear_notifications(kind: str, object_id: int) -> None:
    key = _key(kind, object_id)
    redis = getattr(shared_state, "_redis", None)
    namespace = getattr(shared_state, "_namespace", "identifikatsiya:dev")
    if redis is not None:
        await redis.delete(f"{namespace}:admin_notifications:{key}")
    _memory.pop(key, None)
