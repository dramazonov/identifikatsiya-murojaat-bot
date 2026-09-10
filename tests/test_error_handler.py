"""Tests for the global aiogram error handler (MVP audit HIGH #3 / instruction #2)."""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram.types import Chat, ErrorEvent, Message, Update

from app.main import GLOBAL_ERROR_TEXT, global_error_handler


class RecordingBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))


def _update_with_message(chat_id: int) -> Update:
    message = Message(message_id=1, date=datetime.now(timezone.utc), chat=Chat(id=chat_id, type="private"))
    return Update(update_id=1, message=message)


async def test_notifies_the_user_with_the_exact_safe_text() -> None:
    bot = RecordingBot()
    event = ErrorEvent(update=_update_with_message(chat_id=777), exception=RuntimeError("db is on fire"))

    handled = await global_error_handler(event, bot)

    assert handled is True
    assert bot.sent == [(777, GLOBAL_ERROR_TEXT)]


async def test_never_leaks_exception_details_to_the_user() -> None:
    bot = RecordingBot()
    secret = "internal stack trace / connection string detail"
    event = ErrorEvent(update=_update_with_message(chat_id=777), exception=RuntimeError(secret))

    await global_error_handler(event, bot)

    sent_text = bot.sent[0][1]
    assert secret not in sent_text
    assert sent_text == GLOBAL_ERROR_TEXT


async def test_no_extractable_chat_does_not_crash_and_sends_nothing() -> None:
    bot = RecordingBot()
    update = Update(update_id=2)  # no message, no callback_query
    event = ErrorEvent(update=update, exception=RuntimeError("boom"))

    handled = await global_error_handler(event, bot)

    assert handled is True
    assert bot.sent == []


async def test_failure_to_notify_the_user_is_swallowed_not_raised() -> None:
    class BrokenBot:
        async def send_message(self, chat_id, text, **kwargs):
            raise RuntimeError("Telegram is unreachable")

    event = ErrorEvent(update=_update_with_message(chat_id=777), exception=RuntimeError("original error"))

    # Must not itself raise -- a failure notifying the user must never crash
    # the error handler (which would then be unhandled all over again).
    handled = await global_error_handler(event, BrokenBot())

    assert handled is True
