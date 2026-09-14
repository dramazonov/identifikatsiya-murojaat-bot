from __future__ import annotations

import inspect

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from unittest.mock import AsyncMock

from app.admin_web import WebContext, _nav, register_admin_web_routes
from app.models import AuditLog
from app.services import web_admin_auth
from app.services.admin_service import ROLE_ADMIN, ROLE_SUPERADMIN
from app.services.audit_log_service import (
    list_audit_logs,
    list_recent_audit_logs,
    parse_audit_details,
    write_audit_log,
)


async def test_audit_log_append_and_filters_round_trip():
    actor = 991300001
    row = await write_audit_log(
        actor_telegram_id=actor,
        actor_role=ROLE_SUPERADMIN,
        action="APPEAL_REPLIED",
        target_type="APPEAL",
        target_id="MUR-991300",
        channel="TELEGRAM",
        details={"delivery_status": "DELIVERED", "appeal_id": 991300},
    )
    assert row.id is not None
    assert row.actor_telegram_id == actor
    assert row.actor_role == ROLE_SUPERADMIN
    assert parse_audit_details(row) == {
        "delivery_status": "DELIVERED",
        "appeal_id": 991300,
    }

    page = await list_audit_logs(actor=str(actor), action="appeal_replied", channel="telegram")
    assert page.total >= 1
    match = next(item for item in page.items if item.id == row.id)
    assert match.target_id == "MUR-991300"

    recent = await list_recent_audit_logs(limit=100)
    assert any(item.id == row.id for item in recent)


async def test_audit_log_rejects_invalid_channel():
    try:
        await write_audit_log(
            actor_telegram_id=991300002,
            actor_role=ROLE_SUPERADMIN,
            action="TEST",
            target_type="TEST",
            channel="SYSTEM",
        )
    except ValueError as exc:
        assert "channel" in str(exc)
    else:
        raise AssertionError("invalid audit channel accepted")


def test_superadmin_nav_has_read_only_audit_section_only_for_superadmin():
    regular = _nav(WebContext(991300010, ROLE_ADMIN, "csrf"), "dashboard")
    superadmin = _nav(WebContext(991300011, ROLE_SUPERADMIN, "csrf"), "dashboard")
    assert "/admin/audit" not in regular
    assert "/admin/audit" in superadmin
    assert "Audit jurnali" in superadmin


async def test_regular_admin_cannot_open_audit_web_section(monkeypatch):
    import app.admin_web as admin_web

    async def role(_admin_id):
        return ROLE_ADMIN

    monkeypatch.setattr(admin_web, "get_admin_role", role)
    web_admin_auth.configure(None, "stage30-audit-role", "https://example.org")
    try:
        sid, _ = await web_admin_auth.create_session(991300020)
        app = web.Application()
        register_admin_web_routes(app, AsyncMock())
        headers = {"Cookie": f"{web_admin_auth.cookie_name()}={sid}"}
        async with TestClient(TestServer(app)) as client:
            response = await client.get("/admin/audit", headers=headers, allow_redirects=False)
            assert response.status == 403
    finally:
        web_admin_auth.configure()


def test_stage30_privileged_actions_are_wired_to_audit():
    import app.handlers.admin as admin_handler
    import app.handlers.admin_contact as admin_contact_handler
    import app.admin_web as admin_web

    telegram_source = inspect.getsource(admin_handler)
    contact_source = inspect.getsource(admin_contact_handler)
    web_source = inspect.getsource(admin_web)

    for action in (
        "APPEAL_CLAIMED",
        "APPEAL_CLAIM_RELEASED",
        "APPEAL_REPLIED",
        "SUGGESTION_REVIEWED",
        "ADMIN_ADDED",
        "ADMIN_ROLE_CHANGED",
        "ADMIN_REMOVED",
        "BROADCAST_SENT",
    ):
        assert action in telegram_source

    for action in ("ADMIN_CONTACT_CLAIMED", "ADMIN_CONTACT_REPLIED"):
        assert action in contact_source

    for action in (
        "WEB_LOGIN",
        "WEB_LOGOUT",
        "APPEAL_CLAIMED",
        "APPEAL_CLAIM_RELEASED",
        "APPEAL_REPLIED",
        "SUGGESTION_REVIEWED",
        "ADMIN_ADDED",
        "ADMIN_ROLE_CHANGED",
        "ADMIN_REMOVED",
    ):
        assert action in web_source


def test_audit_model_has_no_foreign_keys_and_no_mutation_service_api():
    assert not AuditLog.__table__.foreign_keys
    import app.services.audit_log_service as service
    assert not hasattr(service, "delete_audit_log")
    assert not hasattr(service, "update_audit_log")
