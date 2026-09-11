from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent, Update

from app.config import BOT_TOKEN, SUPERADMIN_IDS, all_admin_ids
from app.database import init_db
from app.handlers.admin import router as admin_router
from app.handlers.appeal_flow import router as appeal_router
from app.handlers.admin_contact import router as admin_contact_router
from app.handlers.account import router as account_router
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


def build_dispatcher(storage=None, isolation=None):
    dp = Dispatcher(storage=storage, events_isolation=isolation)
    dp.errors.register(global_error_handler)
    dp.include_router(faq_router)
    dp.include_router(documents_router)
    dp.include_router(admin_contact_router)
    dp.include_router(start_router)
    dp.include_router(appeal_router)
    # Keep account_router after start_router so /start always wins even while
    # a settings FSM state (for example phone update) is active.
    dp.include_router(account_router)
    dp.include_router(admin_router)
    return dp


def runtime_components(settings):
    from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
    from aiogram.fsm.storage.redis import RedisStorage, RedisEventIsolation
    from aiogram.fsm.storage.base import DefaultKeyBuilder
    from redis.asyncio import Redis
    from app.services import shared_state

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    namespace = f"identifikatsiya:{bot.id}"
    redis = Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=3) if settings.redis_url else None
    shared_state.configure(redis, namespace)
    if redis is None:
        storage, isolation = MemoryStorage(), SimpleEventIsolation()
    else:
        keys = DefaultKeyBuilder(prefix=f"{namespace}:fsm", with_bot_id=True)
        storage = RedisStorage(redis, key_builder=keys, state_ttl=86400, data_ttl=86400)
        isolation = RedisEventIsolation(redis, key_builder=keys, lock_kwargs={"timeout": 300})
    return bot, build_dispatcher(storage, isolation), redis


async def poll(settings):
    from app.database import engine
    bot, dp, redis = runtime_components(settings)
    try:
        await init_db()
        if redis is not None:
            await redis.ping()
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await dp.storage.close()
        await dp.fsm.events_isolation.close()
        await bot.session.close()
        await engine.dispose()


async def webhook_app(settings):
    from app.database import engine, verify_schema
    from app.http_server import create_http_app
    bot, dp, redis = runtime_components(settings)

    async def cleanup():
        await dp.storage.close()
        await dp.fsm.events_isolation.close()
        await bot.session.close()
        await engine.dispose()

    return create_http_app(settings, dp, bot, db_check=verify_schema,
                           redis_check=redis.ping, cleanup=cleanup)


def main():
    from aiohttp import web
    from app.database import DATABASE_URL
    from app.runtime import Settings
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    settings.validate(DATABASE_URL)
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured")
    if not all_admin_ids():
        logger.warning("No admin ids configured. No admin will receive notifications.")
    if not SUPERADMIN_IDS:
        logger.warning("SUPERADMIN_IDS is empty. Suggestions will not have a superadmin recipient.")
    if settings.mode == "polling":
        asyncio.run(poll(settings))
    else:
        web.run_app(webhook_app(settings), host=settings.host, port=settings.port,
                    access_log=None, print=None)


if __name__ == "__main__":
    main()
