from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent, Update

from app.config import ADMIN_IDS, BOT_TOKEN
from app.database import init_db
from app.handlers.admin import router as admin_router
from app.handlers.admin_contact import router as admin_contact_router
from app.handlers.documents import router as documents_router
from app.handlers.faq import router as faq_router
from app.handlers.start import router as start_router
from app.models import (  # noqa: F401  (registers the models with Base.metadata)
    AdminContact,
    Appeal,
    Suggestion,
    User,
)

logger = logging.getLogger(__name__)

# MVP audit HIGH #3: shown to the user by global_error_handler below whenever
# a handler raises an exception aiogram wasn't already told how to handle.
# Deliberately generic -- exception details (which could include internal
# state) are logged, never shown to the user.
GLOBAL_ERROR_TEXT = "⚠️ Техник хатолик юз берди.\nИлтимос, /start орқали қайта уриниб кўринг."


def _extract_chat_id(update: Update) -> int | None:
    """Best-effort chat id to notify about an unhandled error, or None if there isn't one.

    Covers the two update kinds this bot actually handles (plain messages and
    callback queries) -- anything else (e.g. an update type not otherwise
    processed) is left alone rather than guessed at.
    """
    if update.message is not None:
        return update.message.chat.id
    if update.callback_query is not None and update.callback_query.message is not None:
        return update.callback_query.message.chat.id
    return None


async def global_error_handler(event: ErrorEvent, bot: Bot) -> bool:
    """Catch-all for exceptions raised by any handler (MVP audit HIGH #3).

    Without this, an unhandled exception was only ever logged by aiogram
    internally -- the user got no response at all and had no way to know
    anything went wrong. This logs the full exception (for diagnosis) and
    sends the user a safe, generic message, never exception details.

    Returning True marks the error as handled so aiogram doesn't also log it
    a second time as "unhandled".
    """
    logger.exception(
        "Unhandled exception while processing update %s",
        event.update.update_id,
        exc_info=event.exception,
    )

    chat_id = _extract_chat_id(event.update)
    if chat_id is not None:
        try:
            await bot.send_message(chat_id, GLOBAL_ERROR_TEXT)
        except Exception:
            logger.exception("Failed to notify chat %s about an unhandled error", chat_id)

    return True


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Please configure it in .env")

    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS is empty. No admin will receive appeal notifications.")

    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.errors.register(global_error_handler)
    # faq_router, documents_router and admin_contact_router are included
    # before start_router so their main-menu buttons take priority over
    # start_router's per-state catch-all handlers, letting the user reach
    # them from any point in the registration flow.
    dp.include_router(faq_router)
    dp.include_router(documents_router)
    dp.include_router(admin_contact_router)
    dp.include_router(start_router)
    dp.include_router(admin_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
