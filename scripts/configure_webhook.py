"""Explicit operator command. Never imported by startup or invoked by tests."""
import asyncio
import sys

from aiogram import Bot
from app.config import BOT_TOKEN
from app.database import DATABASE_URL
from app.runtime import Settings


async def main():
    settings = Settings.from_env()
    settings.validate(DATABASE_URL)
    if settings.mode != "webhook":
        raise RuntimeError("Webhook configuration requires BOT_MODE=webhook")
    async with Bot(BOT_TOKEN) as bot:
        if sys.argv[1:] == ["--set"]:
            await bot.set_webhook(settings.base_url.rstrip("/") + settings.path,
                                  secret_token=settings.secret, drop_pending_updates=False,
                                  allowed_updates=["message", "callback_query"], max_connections=10)
            print("Webhook configured; pending updates retained.")
        elif sys.argv[1:] == ["--status"]:
            info = await bot.get_webhook_info()
            print({"configured": bool(info.url), "pending_updates": info.pending_update_count,
                   "has_delivery_error": bool(info.last_error_date)})
        else:
            raise RuntimeError("Use --set or --status")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        raise SystemExit("Webhook command failed (credentials and Telegram response omitted)")
