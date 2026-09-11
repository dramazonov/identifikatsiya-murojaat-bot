from __future__ import annotations

from urllib.parse import urlsplit
from unittest.mock import AsyncMock

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.admin_web import register_admin_web_routes
from app.services import web_admin_auth
from app.services.admin_service import ROLE_ADMIN, ROLE_SUPERADMIN
from app.services.appeal_service import create_appeal
from app.services.user_service import save_user
from app.services.web_admin_service import get_appeal_view, list_appeals


async def test_one_time_login_token_and_session_memory():
    web_admin_auth.configure(None, "stage25-auth", "https://example.org")
    try:
        url = await web_admin_auth.issue_login_url(970000001)
        token = urlsplit(url).path.rsplit("/", 1)[1]
        assert await web_admin_auth.consume_login_token(token) == 970000001
        assert await web_admin_auth.consume_login_token(token) is None

        sid, created = await web_admin_auth.create_session(970000001)
        loaded = await web_admin_auth.get_session(sid)
        assert loaded == created
        await web_admin_auth.destroy_session(sid)
        assert await web_admin_auth.get_session(sid) is None
    finally:
        web_admin_auth.configure()


async def test_web_admin_appeal_search_and_detail():
    telegram_id = 970100001
    await save_user(
        telegram_id, "webadmin", "Stage Twenty Five Citizen", "+998901111111",
        language_code="uz_latn",
    )
    appeal = await create_appeal(
        telegram_id,
        "Web admin searchable appeal",
        category_code="IDENTIFICATION",
    )
    result = await list_appeals(q=appeal.appeal_number)
    assert any(item.appeal.id == appeal.id for item in result.items)
    result = await list_appeals(q="Twenty Five Citizen")
    assert any(item.appeal.id == appeal.id for item in result.items)
    detail = await get_appeal_view(appeal.id)
    assert detail is not None
    assert detail.user.telegram_id == telegram_id
    assert detail.effective_status == "NEW"


async def test_web_admin_requires_telegram_session():
    app = web.Application()
    register_admin_web_routes(app, AsyncMock())
    async with TestClient(TestServer(app)) as client:
        response = await client.get("/admin/", allow_redirects=False)
        assert response.status == 401
        text = await response.text()
        assert "/admin" in text
        assert "BOT_TOKEN" not in text


async def test_web_login_token_is_single_use_and_sets_secure_cookie(monkeypatch):
    import app.admin_web as admin_web

    async def role(_admin_id):
        return ROLE_SUPERADMIN

    monkeypatch.setattr(admin_web, "get_admin_role", role)
    web_admin_auth.configure(None, "stage25-login", "https://example.org")
    try:
        url = await web_admin_auth.issue_login_url(970000010)
        token = urlsplit(url).path.rsplit("/", 1)[1]
        app = web.Application()
        register_admin_web_routes(app, AsyncMock())
        async with TestClient(TestServer(app)) as client:
            response = await client.get(f"/admin/login/{token}", allow_redirects=False)
            assert response.status == 303
            cookie = response.headers.get("Set-Cookie", "")
            assert "HttpOnly" in cookie
            assert "Secure" in cookie
            assert "SameSite=Strict" in cookie
            again = await client.get(f"/admin/login/{token}", allow_redirects=False)
            assert again.status == 401
    finally:
        web_admin_auth.configure()


async def test_regular_admin_cannot_open_superadmin_web_sections(monkeypatch):
    import app.admin_web as admin_web

    async def role(_admin_id):
        return ROLE_ADMIN

    monkeypatch.setattr(admin_web, "get_admin_role", role)
    web_admin_auth.configure(None, "stage25-role", "https://example.org")
    try:
        sid, _ = await web_admin_auth.create_session(970000020)
        app = web.Application()
        register_admin_web_routes(app, AsyncMock())
        headers = {"Cookie": f"{web_admin_auth.cookie_name()}={sid}"}
        async with TestClient(TestServer(app)) as client:
            suggestions = await client.get("/admin/suggestions", headers=headers, allow_redirects=False)
            admins = await client.get("/admin/admins", headers=headers, allow_redirects=False)
            assert suggestions.status == 403
            assert admins.status == 403
    finally:
        web_admin_auth.configure()
