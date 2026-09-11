"""aiogram's aiohttp webhook transport; registration is an explicit operator step."""
import asyncio

from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.admin_web import register_admin_web_routes


def create_http_app(settings, dispatcher, bot, *, db_check, redis_check, cleanup):
    app = web.Application(client_max_size=1024 * 1024)

    async def health(request):
        async def probe(check):
            try:
                await asyncio.wait_for(check(), timeout=3)
                return "ok"
            except Exception:
                return "unavailable"
        db, redis = await asyncio.gather(probe(db_check), probe(redis_check))
        ready = db == redis == "ok"
        return web.json_response({"status": "ok" if ready else "degraded",
                                  "database": db, "redis": redis}, status=200 if ready else 503)

    async def startup(app):
        await asyncio.wait_for(db_check(), timeout=10)
        await asyncio.wait_for(redis_check(), timeout=10)

    async def close(app):
        await cleanup()

    app.router.add_get("/health", health)
    register_admin_web_routes(app, bot)
    SimpleRequestHandler(dispatcher, bot, handle_in_background=True,
                         secret_token=settings.secret).register(app, path=settings.path)
    app.on_startup.append(startup)
    setup_application(app, dispatcher, bot=bot)
    app.on_cleanup.append(close)
    return app
