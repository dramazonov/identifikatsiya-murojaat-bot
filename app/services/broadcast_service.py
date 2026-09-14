from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter

from app.services.delivery_status import classify_delivery_exception
from app.services.telegram_delivery import MAX_RETRY_AFTER_ATTEMPTS
from app.services.user_service import mark_user_unreachable

logger = logging.getLogger(__name__)

# Keep broadcasts comfortably below Telegram's global bot throughput. 429s are
# still handled from the server-provided retry_after value below.
BROADCAST_DELAY_SECONDS = 0.05


@dataclass(frozen=True)
class BroadcastResult:
    total: int
    sent: int
    failed: int
    unreachable: int


async def _copy_with_retry(
    bot: Bot,
    *,
    chat_id: int,
    from_chat_id: int,
    message_id: int,
) -> None:
    attempt = 0
    while True:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            return
        except TelegramRetryAfter as exc:
            attempt += 1
            if attempt > MAX_RETRY_AFTER_ATTEMPTS:
                raise
            await asyncio.sleep(exc.retry_after)


async def broadcast_copied_message(
    bot: Bot,
    recipient_ids: Iterable[int],
    *,
    from_chat_id: int,
    message_id: int,
    mark_unreachable_users: bool,
) -> BroadcastResult:
    """Copy one prepared Telegram message to each unique recipient safely.

    copy_message preserves the superadmin's text/media/caption while removing
    forwarding attribution, which makes the flow behave like a small channel.
    Recipient-specific failures never abort the remaining broadcast.
    """
    ids = list(dict.fromkeys(int(item) for item in recipient_ids if int(item) > 0))
    sent = failed = unreachable_count = 0

    for index, chat_id in enumerate(ids):
        try:
            await _copy_with_retry(
                bot,
                chat_id=chat_id,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            sent += 1
        except Exception as exc:
            failed += 1
            _error_code, unreachable = classify_delivery_exception(exc)
            if unreachable:
                unreachable_count += 1
                if mark_unreachable_users:
                    try:
                        await mark_user_unreachable(chat_id)
                    except Exception:
                        logger.exception("Could not mark broadcast recipient %s unreachable", chat_id)
            logger.warning(
                "Broadcast delivery failed for recipient %s (%s)",
                chat_id,
                type(exc).__name__,
            )

        if index + 1 < len(ids):
            await asyncio.sleep(BROADCAST_DELAY_SECONDS)

    return BroadcastResult(
        total=len(ids),
        sent=sent,
        failed=failed,
        unreachable=unreachable_count,
    )
