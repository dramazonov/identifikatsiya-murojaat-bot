"""Tests for Telegram flood-control (429) handling in app.services.telegram_delivery.

MVP audit / instruction #6: retry_after must be honored, and retries must be
bounded -- never infinite. asyncio.sleep is monkeypatched so these tests run
instantly instead of actually waiting.
"""

from __future__ import annotations

import pytest
from aiogram.exceptions import TelegramRetryAfter

from app.services import telegram_delivery
from app.services.telegram_delivery import MAX_RETRY_AFTER_ATTEMPTS, safe_send_message


def _retry_after_error(seconds: int) -> TelegramRetryAfter:
    return TelegramRetryAfter(method=None, message="Too Many Requests", retry_after=seconds)


class FlakyBot:
    """Raises TelegramRetryAfter `fail_times` times, then succeeds."""

    def __init__(self, fail_times: int, retry_after: int = 3) -> None:
        self.fail_times = fail_times
        self.retry_after = retry_after
        self.attempts = 0

    async def send_message(self, chat_id, text, **kwargs):
        self.attempts += 1
        if self.attempts <= self.fail_times:
            raise _retry_after_error(self.retry_after)
        return {"chat_id": chat_id, "text": text}


class AlwaysFloodedBot:
    def __init__(self) -> None:
        self.attempts = 0

    async def send_message(self, chat_id, text, **kwargs):
        self.attempts += 1
        raise _retry_after_error(1)


@pytest.fixture
def fake_sleep(monkeypatch):
    sleeps: list[float] = []

    async def _sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(telegram_delivery.asyncio, "sleep", _sleep)
    return sleeps


async def test_safe_send_message_retries_after_flood_control_and_succeeds(fake_sleep) -> None:
    bot = FlakyBot(fail_times=2, retry_after=3)

    result = await safe_send_message(bot, 1, "hi")

    assert bot.attempts == 3
    assert fake_sleep == [3, 3]  # waited the server-recommended amount, each retry
    assert result == {"chat_id": 1, "text": "hi"}


async def test_safe_send_message_honors_retry_after_value(fake_sleep) -> None:
    bot = FlakyBot(fail_times=1, retry_after=17)

    await safe_send_message(bot, 1, "hi")

    assert fake_sleep == [17]


async def test_safe_send_message_gives_up_after_max_attempts_never_infinite(fake_sleep) -> None:
    bot = AlwaysFloodedBot()

    with pytest.raises(TelegramRetryAfter):
        await safe_send_message(bot, 1, "hi")

    # Bounded: exactly MAX_RETRY_AFTER_ATTEMPTS retries before giving up and
    # re-raising -- proves this can never loop forever.
    assert len(fake_sleep) == MAX_RETRY_AFTER_ATTEMPTS
    assert bot.attempts == MAX_RETRY_AFTER_ATTEMPTS + 1


async def test_safe_send_message_does_not_retry_other_errors(fake_sleep) -> None:
    class BadRequestBot:
        async def send_message(self, chat_id, text, **kwargs):
            raise ValueError("not a flood-control error")

    with pytest.raises(ValueError):
        await safe_send_message(BadRequestBot(), 1, "hi")

    assert fake_sleep == []  # never slept/retried for a non-429 error
