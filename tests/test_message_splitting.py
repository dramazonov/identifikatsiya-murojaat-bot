"""Tests for app.services.telegram_delivery -- the 4096-char message-limit handling.

MVP audit CRITICAL #1: a long appeal/suggestion/admin-contact notification
must never silently fail to send and must never be truncated.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.services.telegram_delivery import (
    TELEGRAM_MESSAGE_LIMIT,
    send_long_message,
    split_text_for_telegram,
)


def test_default_limit_matches_telegram() -> None:
    assert TELEGRAM_MESSAGE_LIMIT == 4096


def test_short_text_is_returned_as_a_single_chunk() -> None:
    text = "hello world"

    assert split_text_for_telegram(text) == [text]


def test_long_text_splits_on_line_boundaries_and_nothing_is_lost() -> None:
    line = "x" * 100
    text = "\n".join([line] * 60)  # ~6059 chars

    chunks = split_text_for_telegram(text, limit=1000)

    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)
    # Rejoining the chunks (they were split at "\n" boundaries) reproduces
    # the original text exactly -- nothing truncated or dropped.
    assert "\n".join(chunks) == text


def test_single_oversized_line_is_hard_split_without_losing_content() -> None:
    text = "y" * 5000  # one line, no newlines at all

    chunks = split_text_for_telegram(text, limit=2000)

    assert len(chunks) == 3
    assert all(len(chunk) <= 2000 for chunk in chunks)
    assert "".join(chunks) == text


def test_text_at_exactly_the_limit_is_one_chunk() -> None:
    text = "z" * 4096

    assert split_text_for_telegram(text) == [text]


def test_text_one_over_the_limit_splits() -> None:
    text = "z" * 4097

    chunks = split_text_for_telegram(text)

    assert len(chunks) == 2
    assert "".join(chunks) == text


class _FakeChat:
    def __init__(self, chat_id: int) -> None:
        self.id = chat_id


class _FakeMessage:
    def __init__(self, message_id: int, chat_id: int) -> None:
        self.message_id = message_id
        self.chat = _FakeChat(chat_id)


class FakeBot:
    """Records every send_message call; never actually talks to Telegram."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._next_id = 1

    async def send_message(self, chat_id, text, reply_markup=None, **kwargs):
        self.calls.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        message = _FakeMessage(self._next_id, chat_id)
        self._next_id += 1
        return message


async def test_send_long_message_short_text_sends_exactly_one_message_with_markup() -> None:
    bot = FakeBot()
    markup = SimpleNamespace(marker="the-reply-button")

    result = await send_long_message(bot, 42, "short text", reply_markup=markup)

    assert len(bot.calls) == 1
    assert bot.calls[0]["text"] == "short text"
    assert bot.calls[0]["reply_markup"] is markup
    assert result.chat.id == 42


async def test_send_long_message_long_text_splits_and_markup_only_on_last_chunk() -> None:
    bot = FakeBot()
    markup = SimpleNamespace(marker="the-reply-button")
    line = "z" * 100
    text = "\n".join([line] * 60)  # exceeds the default 4096 limit

    result = await send_long_message(bot, 42, text, reply_markup=markup)

    assert len(bot.calls) > 1
    for call in bot.calls[:-1]:
        assert call["reply_markup"] is None
    assert bot.calls[-1]["reply_markup"] is markup
    # Nothing truncated: every chunk sent, concatenated, reproduces the text.
    assert "\n".join(call["text"] for call in bot.calls) == text
    # The returned Message is the LAST one sent -- the one carrying the button.
    assert result.chat.id == 42
    assert result.message_id == bot._next_id - 1


async def test_send_long_message_without_markup_never_attaches_one() -> None:
    bot = FakeBot()

    await send_long_message(bot, 42, "no button here")

    assert bot.calls[0]["reply_markup"] is None
