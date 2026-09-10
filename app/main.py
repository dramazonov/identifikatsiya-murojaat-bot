from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

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


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Please configure it in .env")

    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS is empty. No admin will receive appeal notifications.")

    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
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
