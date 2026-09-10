from __future__ import annotations

"""Shared helpers for delivering Telegram messages safely.

Centralizes two concerns that used to be handled ad hoc (or not at all) at
each call site that sends a message built from user-supplied free text
(appeal/suggestion/admin-contact text, admin replies):

Telegram's hard 4096-character-per-message limit
--------------------------------------------------
``split_text_for_telegram`` breaks a long text into chunks on line
boundaries, so a literal HTML tag such as ``"<b>...</b>"`` -- always confined
to a single line in this codebase's notification templates -- is never cut in
half. ``send_long_message`` sends those chunks as separate messages,
attaching an optional ``reply_markup`` only to the LAST one, since that's the
message the recipient is meant to act on (e.g. the "Жавоб бериш" button).
Nothing is ever truncated -- a text that doesn't fit in one message is simply
delivered as several.

Telegram's flood control (HTTP 429 / TelegramRetryAfter)
----------------------------------------------------------
``safe_send_message`` and ``safe_edit_message_text`` retry once per the
server-recommended wait (``retry_after``), up to ``MAX_RETRY_AFTER_ATTEMPTS``
times, so a transient rate limit is absorbed instead of either failing
outright or retrying forever. Any other ``TelegramAPIError`` (forbidden, bad
request, etc.) is never retried here -- it propagates immediately so the
caller's own try/except + logging (already present at every call site) can
handle it exactly as before.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)

# Telegram's hard per-message character limit (applies to both send and edit).
TELEGRAM_MESSAGE_LIMIT = 4096

# Bounded retry count for flood-control (429) waits -- see safe_send_message/
# safe_edit_message_text. Keeps a burst of flood control from turning into an
# infinite retry loop that could stall the whole polling process.
MAX_RETRY_AFTER_ATTEMPTS = 3


def split_text_for_telegram(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Split ``text`` into chunks of at most ``limit`` characters each.

    Prefers to break on line boundaries (``"\\n"``) so a chunk boundary never
    lands inside one of this codebase's ``<b>...</b>`` labels -- those are
    always emitted as a single, short, self-contained line. If a single line
    is itself longer than ``limit`` (only possible for the free-text body of
    an appeal/suggestion/admin-contact message, or an admin's reply, all of
    which are ``html.escape()``-d plain text with no tags to break), that
    line is further split on plain character boundaries, which is safe for
    the same reason -- there is no tag there to cut in half.

    Never drops or truncates any content; the returned chunks, rejoined with
    ``"\\n"`` at the points they were split, reproduce ``text`` exactly.
    """
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""

    for line in text.split("\n"):
        candidate = f"{current}\n{line}" if current else line

        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        # The line on its own may still exceed the limit -- hard-split it.
        while len(line) > limit:
            chunks.append(line[:limit])
            line = line[limit:]
        current = line

    if current:
        chunks.append(current)

    return chunks


async def safe_send_message(bot: Bot, chat_id: int, text: str, **kwargs: object) -> Message:
    """``bot.send_message`` with bounded retry on Telegram flood control (429).

    On ``TelegramRetryAfter``, sleeps for the server-recommended
    ``retry_after`` seconds and retries, up to ``MAX_RETRY_AFTER_ATTEMPTS``
    times total. After that many flood-control hits in a row, gives up and
    re-raises -- callers keep their existing try/except + logging as the
    final safety net, this never retries forever.
    """
    attempt = 0
    while True:
        try:
            return await bot.send_message(chat_id, text, **kwargs)
        except TelegramRetryAfter as exc:
            attempt += 1
            if attempt > MAX_RETRY_AFTER_ATTEMPTS:
                logger.error(
                    "Giving up sending message to %s after %d flood-control retries",
                    chat_id,
                    MAX_RETRY_AFTER_ATTEMPTS,
                )
                raise
            logger.warning(
                "Flood control sending to %s: waiting %s s (attempt %d/%d)",
                chat_id,
                exc.retry_after,
                attempt,
                MAX_RETRY_AFTER_ATTEMPTS,
            )
            await asyncio.sleep(exc.retry_after)


async def safe_edit_message_text(
    bot: Bot, *, chat_id: int, message_id: int, text: str, **kwargs: object
) -> Message | bool:
    """``bot.edit_message_text`` with the same bounded 429 retry as ``safe_send_message``."""
    attempt = 0
    while True:
        try:
            return await bot.edit_message_text(
                chat_id=chat_id, message_id=message_id, text=text, **kwargs
            )
        except TelegramRetryAfter as exc:
            attempt += 1
            if attempt > MAX_RETRY_AFTER_ATTEMPTS:
                logger.error(
                    "Giving up editing message %s/%s after %d flood-control retries",
                    chat_id,
                    message_id,
                    MAX_RETRY_AFTER_ATTEMPTS,
                )
                raise
            logger.warning(
                "Flood control editing %s/%s: waiting %s s (attempt %d/%d)",
                chat_id,
                message_id,
                exc.retry_after,
                attempt,
                MAX_RETRY_AFTER_ATTEMPTS,
            )
            await asyncio.sleep(exc.retry_after)


async def send_long_message(
    bot: Bot,
    chat_id: int,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    """Send ``text`` as one or more messages, always staying within Telegram's limit.

    Splits via :func:`split_text_for_telegram`. When ``text`` fits in a
    single message (the common case), this sends exactly one message --
    identical to a plain ``send_message`` call. When it doesn't, ``text`` is
    delivered as several messages and ``reply_markup`` (if given) is attached
    only to the LAST one, since that's the message the recipient is meant to
    act on. Each chunk is sent via :func:`safe_send_message`, so flood
    control is handled the same way regardless of how many chunks there are.

    Returns the last ``Message`` sent -- callers that need to remember "the
    message carrying the button" (to edit or reference it later) should keep
    its chat/message id.
    """
    chunks = split_text_for_telegram(text)
    last_message: Message | None = None

    for index, chunk in enumerate(chunks):
        is_last = index == len(chunks) - 1
        last_message = await safe_send_message(
            bot, chat_id, chunk, reply_markup=reply_markup if is_last else None
        )

    assert last_message is not None  # split_text_for_telegram always returns >= 1 chunk
    return last_message
