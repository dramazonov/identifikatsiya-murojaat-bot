"""Redis atomic submission leases and sliding-window rate limits, with dev fallback.

No automatic fallback on Redis outages: production fails closed. A DB commit
and Redis completion are not atomic; see DEPLOYMENT.md for crash-window limits.
"""
import secrets
import time

from app.services import rate_limit

_redis = None
_namespace = "identifikatsiya:dev"
_owners = {}
PENDING_SECONDS = 300
DONE_SECONDS = 7 * 24 * 60 * 60

RATE_SCRIPT = """
local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - tonumber(ARGV[1]))
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 1 end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], ARGV[1])
return 0
"""
FINISH_SCRIPT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
if ARGV[2] == 'release' then return redis.call('DEL', KEYS[1]) end
redis.call('SET', KEYS[1], 'done', 'EX', ARGV[2])
return 1
"""


def configure(redis=None, namespace="identifikatsiya:dev"):
    global _redis, _namespace
    _redis, _namespace = redis, namespace


async def is_rate_limited(key, *, limit, window_seconds):
    if _redis is None:
        return rate_limit.is_rate_limited(key, limit=limit, window_seconds=window_seconds)
    return bool(await _redis.eval(RATE_SCRIPT, 1, f"{_namespace}:rate:{key}",
                                  max(1, int(window_seconds * 1000)), limit, secrets.token_hex(16)))


async def acquire_submission(key):
    token = secrets.token_hex(16)
    if _redis is not None:
        acquired = await _redis.set(f"{_namespace}:submission:{key}", token,
                                    nx=True, ex=PENDING_SECONDS)
        return token if acquired else None
    now = time.monotonic()
    # Expiry also bounds memory without evicting live deduplication entries.
    for stale in [k for k, (_, expiry) in _owners.items() if expiry <= now]:
        del _owners[stale]
    if key in _owners:
        return None
    _owners[key] = (token, now + PENDING_SECONDS)
    return token


async def finish_submission(key, token, *, failed=False):
    if _redis is not None:
        return bool(await _redis.eval(FINISH_SCRIPT, 1, f"{_namespace}:submission:{key}",
                                      token, "release" if failed else DONE_SECONDS))
    if key not in _owners or _owners[key][0] != token:
        return False
    if failed:
        del _owners[key]
    else:
        _owners[key] = ("done", time.monotonic() + DONE_SECONDS)
    return True
