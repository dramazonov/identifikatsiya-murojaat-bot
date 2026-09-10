"""Unit tests for app.services.rate_limit (idempotency + rate limiting).

Pure, DB-free tests -- the clock is monkeypatched so they're deterministic
and instant, never sleeping in real time.
"""

from __future__ import annotations

import app.services.rate_limit as rate_limit


def test_already_processed_first_call_is_false(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: 100.0)

    assert rate_limit.already_processed("key-1", ttl_seconds=60) is False


def test_already_processed_duplicate_within_ttl_is_true(monkeypatch) -> None:
    times = iter([100.0, 105.0])
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: next(times))

    assert rate_limit.already_processed("key-2", ttl_seconds=60) is False
    assert rate_limit.already_processed("key-2", ttl_seconds=60) is True


def test_already_processed_after_ttl_is_false_again(monkeypatch) -> None:
    times = iter([100.0, 300.0])  # 200s apart, well past a 60s TTL
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: next(times))

    assert rate_limit.already_processed("key-3", ttl_seconds=60) is False
    assert rate_limit.already_processed("key-3", ttl_seconds=60) is False


def test_already_processed_distinct_keys_never_collide(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: 100.0)

    assert rate_limit.already_processed("msg:1:100", ttl_seconds=60) is False
    assert rate_limit.already_processed("msg:1:101", ttl_seconds=60) is False


def test_is_rate_limited_allows_up_to_the_limit_then_blocks(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: 100.0)
    key = "user:1"

    assert rate_limit.is_rate_limited(key, limit=3, window_seconds=60) is False
    assert rate_limit.is_rate_limited(key, limit=3, window_seconds=60) is False
    assert rate_limit.is_rate_limited(key, limit=3, window_seconds=60) is False
    # A normal user submitting occasionally never gets here -- only truly
    # rapid-fire submissions (3 within the same second) trip this.
    assert rate_limit.is_rate_limited(key, limit=3, window_seconds=60) is True


def test_is_rate_limited_does_not_penalize_a_refused_attempt(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: 100.0)
    key = "user:2"

    assert rate_limit.is_rate_limited(key, limit=1, window_seconds=60) is False
    assert rate_limit.is_rate_limited(key, limit=1, window_seconds=60) is True
    # Still blocked, not "double counted" into some worse state.
    assert rate_limit.is_rate_limited(key, limit=1, window_seconds=60) is True


def test_is_rate_limited_window_expires(monkeypatch) -> None:
    times = iter([100.0, 100.0, 100.0, 200.0])
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: next(times))
    key = "user:3"

    assert rate_limit.is_rate_limited(key, limit=2, window_seconds=60) is False  # hit 1 @ t=100
    assert rate_limit.is_rate_limited(key, limit=2, window_seconds=60) is False  # hit 2 @ t=100
    assert rate_limit.is_rate_limited(key, limit=2, window_seconds=60) is True  # hit 3 @ t=100 -> blocked
    # 100s later, well past the 60s window -- old hits have expired.
    assert rate_limit.is_rate_limited(key, limit=2, window_seconds=60) is False


def test_is_rate_limited_distinct_users_do_not_share_a_budget(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: 100.0)

    assert rate_limit.is_rate_limited("user:a", limit=1, window_seconds=60) is False
    # A different user's key must not be affected by user:a's usage.
    assert rate_limit.is_rate_limited("user:b", limit=1, window_seconds=60) is False
