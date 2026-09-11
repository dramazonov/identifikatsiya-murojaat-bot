from __future__ import annotations

"""Legacy synchronous memory helpers used by development and regression tests.

Production handlers use shared_state's asynchronous Redis-capable API. This
module's rate limiter is its no-Redis fallback; already_processed is retained
for compatibility with existing callers and tests.
"""

import time
from collections import defaultdict, deque

_SEEN_KEYS_MAX_SIZE = 5000  # bounds memory for a long-running process

_seen_keys: dict[str, float] = {}
_hit_windows: dict[str, deque[float]] = defaultdict(deque)


def already_processed(key: str, ttl_seconds: float = 120.0) -> bool:
    """Idempotency guard: True if ``key`` was already marked within ``ttl_seconds``.

    Marks ``key`` as seen (with the current time) as a side effect on every
    call, so the window keeps sliding forward on repeated hits. Callers pick
    a ``key`` that uniquely identifies the *Telegram update* being processed
    (e.g. ``f"appeal_create:{chat_id}:{message_id}"``), not the resulting
    application action -- two distinct legitimate messages always get
    distinct message ids, so this never blocks a genuine new submission.
    """
    now = time.monotonic()
    _prune_seen_keys(now)

    last_seen = _seen_keys.get(key)
    _seen_keys[key] = now

    if last_seen is None:
        return False
    return (now - last_seen) < ttl_seconds


def _prune_seen_keys(now: float, *, max_size: int = _SEEN_KEYS_MAX_SIZE) -> None:
    if len(_seen_keys) <= max_size:
        return
    # Cheap bound on memory, not an exact LRU -- correctness comes from the
    # TTL comparison in already_processed, this only stops unbounded growth.
    oldest_first = sorted(_seen_keys, key=_seen_keys.__getitem__)
    for stale_key in oldest_first[: len(_seen_keys) // 2]:
        del _seen_keys[stale_key]


def is_rate_limited(key: str, *, limit: int, window_seconds: float) -> bool:
    """Fixed-window rate limit: True if ``key`` has already hit ``limit`` actions.

    within the last ``window_seconds``, meaning the caller's action should be
    refused. An attempt that is refused does NOT itself count against the
    window (so a blocked user isn't punished further just for retrying), but
    every attempt that is ALLOWED is recorded immediately.
    """
    now = time.monotonic()
    window = _hit_windows[key]

    while window and now - window[0] > window_seconds:
        window.popleft()

    if len(window) >= limit:
        return True

    window.append(now)
    return False
