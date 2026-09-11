from __future__ import annotations

import html
import io
import logging
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from aiohttp import web
from aiogram import Bot

from app.data.appeal_categories import APPEAL_CATEGORIES
from app.i18n import appeal_category_text, appeal_status_text, t
from app.keyboards import admin_reply_keyboard
from app.services.admin_notification_state import clear_notifications, list_notifications
from app.services.admin_service import (
    ROLE_ADMIN,
    ROLE_SUPERADMIN,
    add_or_update_admin,
    all_admin_ids,
    all_superadmin_ids,
    get_admin_role,
    list_admin_entries,
    remove_dynamic_admin,
)
from app.services.appeal_service import claim_appeal, complete_appeal, release_appeal_claim
from app.services.datetime_utils import format_tashkent, utcnow
from app.services.delivery_status import DELIVERY_DELIVERED, DELIVERY_FAILED, classify_delivery_exception
from app.services.suggestion_service import review_suggestion
from app.services.telegram_delivery import send_long_message
from app.services.user_service import get_user_by_id, mark_user_unreachable
from app.services import web_admin_auth
from app.services.web_admin_service import (
    category_counts,
    dashboard_counts,
    get_appeal_view,
    list_appeals,
    list_suggestions,
    list_users,
    region_counts,
)

logger = logging.getLogger(__name__)

STATUS_LABELS = {
    "NEW": "Yangi",
    "IN_PROGRESS": "Ko‘rib chiqilmoqda",
    "COMPLETED": "Yakunlangan",
    "REJECTED": "Rad etilgan",
}
STATUS_BADGES = {
    "NEW": "badge-new",
    "IN_PROGRESS": "badge-progress",
    "COMPLETED": "badge-done",
    "REJECTED": "badge-rejected",
}


@dataclass(frozen=True)
class WebContext:
    admin_id: int
    role: str
    csrf: str

    @property
    def superadmin(self) -> bool:
        return self.role == ROLE_SUPERADMIN


def _e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _dt(value) -> str:
    return format_tashkent(value) if value is not None else "—"


def _security_headers(response: web.StreamResponse) -> web.StreamResponse:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    return response


def _html(body: str, *, status: int = 200) -> web.Response:
    return _security_headers(web.Response(text=body, status=status, content_type="text/html"))


async def _context(request: web.Request) -> WebContext | None:
    sid = request.cookies.get(web_admin_auth.cookie_name())
    session = await web_admin_auth.get_session(sid)
    if session is None:
        return None
    role = await get_admin_role(session.admin_id)
    if role is None:
        await web_admin_auth.destroy_session(sid)
        return None
    return WebContext(session.admin_id, role, session.csrf_token)


async def _require_context(request: web.Request, *, superadmin: bool = False) -> WebContext:
    ctx = await _context(request)
    if ctx is None:
        raise web.HTTPUnauthorized(text="Admin sessiyasi topilmadi. Telegram /admin orqali qayta kiring.")
    if superadmin and not ctx.superadmin:
        raise web.HTTPForbidden(text="Bu bo‘lim faqat SUPERADMIN uchun.")
    return ctx


async def _require_csrf(request: web.Request, ctx: WebContext):
    data = await request.post()
    token = str(data.get("csrf", ""))
    if not token or not secrets.compare_digest(token, ctx.csrf):
        raise web.HTTPForbidden(text="CSRF tekshiruvi muvaffaqiyatsiz.")
    return data


def _nav(ctx: WebContext, active: str) -> str:
    items = [
        ("dashboard", "/admin/", "▦", "Dashboard"),
        ("appeals", "/admin/appeals", "✉", "Murojaatlar"),
        ("users", "/admin/users", "◉", "Foydalanuvchilar"),
        ("stats", "/admin/stats", "▥", "Statistika"),
    ]
    if ctx.superadmin:
        items.insert(2, ("suggestions", "/admin/suggestions", "◆", "Takliflar"))
        items.insert(-1, ("admins", "/admin/admins", "♟", "Adminlar"))
    links = "".join(
        f'<a class="nav-link {"active" if key == active else ""}" href="{url}">'
        f'<span>{icon}</span>{_e(label)}</a>'
        for key, url, icon, label in items
    )
    return links


_CSS = r"""
:root{--bg:#f4f6f8;--panel:#fff;--text:#17202a;--muted:#697386;--line:#e5e9ef;--brand:#146c5f;--brand2:#0e554b;--danger:#b42318;--warn:#9a6700;--sidebar:#112723;--shadow:0 8px 28px rgba(16,24,40,.06)}
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--text)}a{color:inherit}.shell{min-height:100vh;display:grid;grid-template-columns:245px 1fr}.sidebar{background:var(--sidebar);color:#e8f3f0;padding:24px 16px;position:sticky;top:0;height:100vh}.brand{font-weight:750;font-size:18px;padding:4px 12px 22px;line-height:1.3}.brand small{display:block;color:#9fc1b9;font-weight:500;font-size:12px;margin-top:5px}.nav-link{display:flex;gap:11px;align-items:center;text-decoration:none;padding:11px 12px;margin:4px 0;border-radius:10px;color:#cfe2dd;font-size:14px}.nav-link:hover,.nav-link.active{background:#1a3b35;color:#fff}.content{padding:28px 34px 48px;min-width:0}.topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:24px}.topbar h1{font-size:25px;margin:0}.role{font-size:12px;color:var(--muted)}.logout{display:inline}.btn{border:0;border-radius:9px;padding:9px 13px;cursor:pointer;font-weight:650;text-decoration:none;display:inline-block;font-size:13px}.btn-primary{background:var(--brand);color:#fff}.btn-primary:hover{background:var(--brand2)}.btn-light{background:#eef2f5;color:#344054}.btn-danger{background:#fee4e2;color:#912018}.btn-warn{background:#fff2cc;color:#7a4e00}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin-bottom:22px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:17px;box-shadow:var(--shadow)}.kpi-label{font-size:13px;color:var(--muted)}.kpi-value{font-size:28px;font-weight:780;margin-top:7px}.section{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);margin-bottom:20px;overflow:hidden}.section-head{padding:16px 18px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:12px}.section-head h2{font-size:16px;margin:0}.section-body{padding:18px}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th{text-align:left;color:#667085;font-size:12px;font-weight:700;background:#f9fafb}th,td{padding:11px 12px;border-bottom:1px solid #edf0f3;vertical-align:top}tr:last-child td{border-bottom:0}.num{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-weight:700}.muted{color:var(--muted)}.badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:11px;font-weight:750}.badge-new{background:#eaf3ff;color:#175cd3}.badge-progress{background:#fff4d6;color:#875d00}.badge-done{background:#e7f6ec;color:#067647}.badge-rejected{background:#fee4e2;color:#b42318}.filters{display:grid;grid-template-columns:2fr repeat(4,1fr) auto;gap:9px}.input,.select,.textarea{width:100%;border:1px solid #d0d5dd;border-radius:9px;padding:9px 10px;background:#fff;font:inherit;color:inherit}.textarea{min-height:130px;resize:vertical}.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:18px}.detail-list{display:grid;grid-template-columns:180px 1fr;gap:10px 16px;font-size:14px}.detail-list dt{color:var(--muted)}.detail-list dd{margin:0;word-break:break-word}.text-block{white-space:pre-wrap;background:#f8fafb;border:1px solid var(--line);border-radius:10px;padding:14px;line-height:1.5}.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:16px}.pagination{display:flex;justify-content:center;gap:8px;padding:15px}.pagination a{text-decoration:none;border:1px solid var(--line);background:#fff;padding:7px 10px;border-radius:8px}.alert{padding:12px 14px;border-radius:10px;margin-bottom:16px;background:#edf7f5;border:1px solid #b7ddd5;color:#155e52}.alert-error{background:#fff1f0;border-color:#f5c2c0;color:#8a1c13}.empty{text-align:center;color:var(--muted);padding:28px}.admin-row{display:flex;justify-content:space-between;gap:12px;align-items:center;border-bottom:1px solid var(--line);padding:11px 0}.admin-row:last-child{border:0}.mobile-only{display:none}
@media(max-width:1000px){.cards{grid-template-columns:repeat(2,1fr)}.filters{grid-template-columns:1fr 1fr}.grid-2{grid-template-columns:1fr}}
@media(max-width:760px){.shell{display:block}.sidebar{position:static;height:auto}.content{padding:18px}.nav-link{display:inline-flex;margin:3px}.cards{grid-template-columns:1fr 1fr}.topbar{align-items:flex-start}.detail-list{grid-template-columns:1fr}.detail-list dt{font-weight:700}.filters{grid-template-columns:1fr}.brand{padding-bottom:12px}}
"""


def _layout(ctx: WebContext, *, title: str, active: str, body: str) -> str:
    return f"""<!doctype html><html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{_e(title)} — Identifikatsiya</title><style>{_CSS}</style></head><body>
<div class="shell"><aside class="sidebar"><div class="brand">Identifikatsiya markazi<small>Web Admin Panel</small></div>{_nav(ctx, active)}</aside>
<main class="content"><div class="topbar"><div><h1>{_e(title)}</h1><div class="role">Telegram ID: {_e(ctx.admin_id)} · {_e(ctx.role)}</div></div><form class="logout" method="post" action="/admin/logout"><input type="hidden" name="csrf" value="{_e(ctx.csrf)}"><button class="btn btn-light" type="submit">Chiqish</button></form></div>{body}</main></div></body></html>"""


def _status_badge(status: str) -> str:
    label = STATUS_LABELS.get(status, appeal_status_text(status, "uz_latn"))
    klass = STATUS_BADGES.get(status, "")
    return f'<span class="badge {klass}">{_e(label)}</span>'


def _page_links(path: str, page, params: dict[str, str]) -> str:
    if page.total_pages <= 1:
        return ""
    links = []
    if page.page > 1:
        p = dict(params, page=str(page.page - 1))
        links.append(f'<a href="{path}?{urlencode(p)}">← Oldingi</a>')
    links.append(f'<span class="muted">{page.page} / {page.total_pages}</span>')
    if page.page < page.total_pages:
        p = dict(params, page=str(page.page + 1))
        links.append(f'<a href="{path}?{urlencode(p)}">Keyingi →</a>')
    return '<div class="pagination">' + "".join(links) + "</div>"


async def login(request: web.Request) -> web.StreamResponse:
    admin_id = await web_admin_auth.consume_login_token(request.match_info.get("token", ""))
    if admin_id is None:
        return _html("<h2>Havola eskirgan yoki avval ishlatilgan.</h2><p>Telegramda /admin orqali yangi havola oling.</p>", status=401)
    role = await get_admin_role(admin_id)
    if role is None:
        return _html("<h2>Ruxsat yo‘q.</h2>", status=403)
    sid, _ = await web_admin_auth.create_session(admin_id)
    response = web.HTTPSeeOther(location="/admin/")
    response.set_cookie(
        web_admin_auth.cookie_name(), sid, httponly=True, secure=True, samesite="Strict",
        max_age=8 * 60 * 60, path="/admin",
    )
    return _security_headers(response)


async def admin_root(request: web.Request) -> web.StreamResponse:
    ctx = await _context(request)
    if ctx is None:
        return _html("<h2>Admin sessiyasi mavjud emas.</h2><p>Telegram botda <b>/admin</b> → <b>Web panel</b> orqali kiring.</p>", status=401)
    counts = await dashboard_counts()
    recent = await list_appeals(page=1)
    suggestion_card = (
        f'<div class="card"><div class="kpi-label">Takliflar</div><div class="kpi-value">{counts.get("suggestions",0)}</div></div>'
        if ctx.superadmin else ""
    )
    cards = f"""<div class="cards">
<div class="card"><div class="kpi-label">Jami murojaatlar</div><div class="kpi-value">{counts.get('appeals',0)}</div></div>
<div class="card"><div class="kpi-label">Yangi</div><div class="kpi-value">{counts.get('appeal_new',0)}</div></div>
<div class="card"><div class="kpi-label">Ko‘rib chiqilmoqda</div><div class="kpi-value">{counts.get('appeal_in_progress',0)}</div></div>
<div class="card"><div class="kpi-label">Foydalanuvchilar</div><div class="kpi-value">{counts.get('users',0)}</div></div>{suggestion_card}</div>"""
    rows = "".join(
        f'<tr><td class="num"><a href="/admin/appeals/{v.appeal.id}">{_e(v.appeal.appeal_number)}</a></td><td>{_e(v.user.full_name or "—")}</td><td>{_e(appeal_category_text(v.appeal.category_code,"uz_latn"))}</td><td>{_status_badge(v.effective_status)}</td><td>{_e(_dt(v.appeal.created_at))}</td></tr>'
        for v in recent.items[:8]
    ) or '<tr><td colspan="5" class="empty">Murojaatlar yo‘q.</td></tr>'
    body = cards + f'<div class="section"><div class="section-head"><h2>Oxirgi murojaatlar</h2><a class="btn btn-light" href="/admin/appeals">Barchasi</a></div><div class="table-wrap"><table><thead><tr><th>Raqam</th><th>F.I.Sh.</th><th>Yo‘nalish</th><th>Holat</th><th>Sana</th></tr></thead><tbody>{rows}</tbody></table></div></div>'
    return _html(_layout(ctx, title="Dashboard", active="dashboard", body=body))


async def appeals(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request)
    get = request.rel_url.query
    try:
        page_num = int(get.get("page", "1"))
    except ValueError:
        page_num = 1
    params = {k: get.get(k, "") for k in ("q", "status", "category", "region", "district")}
    result = await list_appeals(page=page_num, **params)
    options = '<option value="">Barcha holatlar</option>' + "".join(
        f'<option value="{s}" {"selected" if params["status"]==s else ""}>{_e(STATUS_LABELS[s])}</option>'
        for s in ("NEW", "IN_PROGRESS", "COMPLETED", "REJECTED")
    )
    categories = '<option value="">Barcha yo‘nalishlar</option>' + "".join(
        f'<option value="{c}" {"selected" if params["category"]==c else ""}>{_e(appeal_category_text(c,"uz_latn"))}</option>'
        for c in APPEAL_CATEGORIES
    )
    filters = f'''<div class="section"><div class="section-body"><form class="filters" method="get">
<input class="input" name="q" value="{_e(params['q'])}" placeholder="MUR, F.I.Sh., telefon yoki Telegram ID">
<select class="select" name="status">{options}</select><select class="select" name="category">{categories}</select>
<input class="input" name="region" value="{_e(params['region'])}" placeholder="Viloyat"><input class="input" name="district" value="{_e(params['district'])}" placeholder="Tuman">
<button class="btn btn-primary" type="submit">Qidirish</button></form></div></div>'''
    rows = "".join(
        f'<tr><td class="num"><a href="/admin/appeals/{v.appeal.id}">{_e(v.appeal.appeal_number)}</a></td><td>{_e(v.user.full_name or "—")}<br><span class="muted">{_e(v.user.phone or "—")}</span></td><td>{_e(v.user.region or "—")}<br><span class="muted">{_e(v.user.district or "—")}</span></td><td>{_e(appeal_category_text(v.appeal.category_code,"uz_latn"))}</td><td>{_status_badge(v.effective_status)}</td><td>{_e(v.appeal.admin_id or "—")}</td><td>{_e(_dt(v.appeal.created_at))}</td></tr>'
        for v in result.items
    ) or '<tr><td colspan="7" class="empty">Natija topilmadi.</td></tr>'
    table = f'<div class="section"><div class="section-head"><h2>Murojaatlar ({result.total})</h2></div><div class="table-wrap"><table><thead><tr><th>Raqam</th><th>Foydalanuvchi</th><th>Hudud</th><th>Yo‘nalish</th><th>Holat</th><th>Admin</th><th>Sana</th></tr></thead><tbody>{rows}</tbody></table></div>{_page_links("/admin/appeals",result,params)}</div>'
    return _html(_layout(ctx, title="Murojaatlar", active="appeals", body=filters+table))


async def appeal_detail(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request)
    try:
        appeal_id = int(request.match_info["appeal_id"])
    except ValueError:
        raise web.HTTPNotFound()
    view = await get_appeal_view(appeal_id)
    if view is None:
        raise web.HTTPNotFound()
    a, u = view.appeal, view.user
    attachment = "Yo‘q"
    if a.attachment_type == "PDF" and a.attachment_file_id:
        attachment = f'<a class="btn btn-light" target="_blank" href="/admin/appeals/{a.id}/pdf">PDFni ochish</a>'
    info = f'''<div class="grid-2"><div class="section"><div class="section-head"><h2>{_e(a.appeal_number)}</h2>{_status_badge(view.effective_status)}</div><div class="section-body"><dl class="detail-list">
<dt>Yo‘nalish</dt><dd>{_e(appeal_category_text(a.category_code,"uz_latn"))}</dd><dt>Yuborilgan vaqt</dt><dd>{_e(_dt(a.created_at))}</dd><dt>Biriktirilgan admin</dt><dd>{_e(a.admin_id or "—")}</dd><dt>Claim tugashi</dt><dd>{_e(_dt(a.claim_expires_at))}</dd><dt>PDF</dt><dd>{attachment}</dd><dt>Delivery</dt><dd>{_e(a.delivery_status or "—")}</dd></dl></div></div>
<div class="section"><div class="section-head"><h2>Foydalanuvchi</h2></div><div class="section-body"><dl class="detail-list"><dt>F.I.Sh.</dt><dd>{_e(u.full_name or "—")}</dd><dt>Telefon</dt><dd>{_e(u.phone or "—")}</dd><dt>Telegram ID</dt><dd>{_e(u.telegram_id)}</dd><dt>Hudud</dt><dd>{_e(u.region or "—")}, {_e(u.district or "—")}</dd><dt>Til</dt><dd>{_e(u.language_code)}</dd></dl></div></div></div>'''
    text = f'<div class="section"><div class="section-head"><h2>Murojaat matni</h2></div><div class="section-body"><div class="text-block">{_e(a.appeal_text)}</div></div></div>'
    actions = ""
    if view.effective_status == "NEW":
        actions = f'<form method="post" action="/admin/appeals/{a.id}/claim"><input type="hidden" name="csrf" value="{_e(ctx.csrf)}"><button class="btn btn-primary" type="submit">Ko‘rib chiqishni boshlash</button></form>'
    elif a.status == "IN_PROGRESS" and a.admin_id == ctx.admin_id and (a.claim_expires_at is None or a.claim_expires_at > utcnow()):
        actions = f'''<div class="section"><div class="section-head"><h2>Javob berish</h2></div><div class="section-body"><form method="post" action="/admin/appeals/{a.id}/reply"><input type="hidden" name="csrf" value="{_e(ctx.csrf)}"><textarea class="textarea" name="answer" minlength="2" maxlength="4000" required placeholder="Javob matni"></textarea><div class="actions"><button class="btn btn-primary" type="submit">Javobni yuborish</button></div></form><form method="post" action="/admin/appeals/{a.id}/release"><input type="hidden" name="csrf" value="{_e(ctx.csrf)}"><button class="btn btn-warn" type="submit">Bekor qilish</button></form></div></div>'''
    elif a.status == "IN_PROGRESS":
        actions = f'<div class="alert">Murojaat <b>{_e(a.admin_id)}</b> admin tomonidan ko‘rib chiqilmoqda.</div>'
    if a.admin_answer:
        actions += f'<div class="section"><div class="section-head"><h2>Admin javobi</h2></div><div class="section-body"><div class="text-block">{_e(a.admin_answer)}</div><p class="muted">Javob vaqti: {_e(_dt(a.answered_at))}</p></div></div>'
    return _html(_layout(ctx, title=f"Murojaat {a.appeal_number}", active="appeals", body=info+text+actions))


async def _set_notification_buttons(bot: Bot, appeal_id: int, enabled: bool) -> None:
    markup = admin_reply_keyboard(appeal_id) if enabled else None
    for info in (await list_notifications("appeal", appeal_id)).values():
        try:
            await bot.edit_message_reply_markup(
                chat_id=info["chat_id"], message_id=info["message_id"], reply_markup=markup
            )
        except Exception:
            logger.exception("Could not sync Telegram appeal buttons for %s", appeal_id)


async def _broadcast(bot: Bot, ids: list[int], text: str) -> None:
    for admin_id in ids:
        try:
            await send_long_message(bot, admin_id, text)
        except Exception:
            logger.exception("Could not broadcast web-admin update to %s", admin_id)


async def appeal_claim(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request)
    await _require_csrf(request, ctx)
    appeal_id = int(request.match_info["appeal_id"])
    appeal, claimed = await claim_appeal(appeal_id, ctx.admin_id)
    if appeal is None:
        raise web.HTTPNotFound()
    if not claimed and appeal.admin_id != ctx.admin_id:
        raise web.HTTPConflict(text="Murojaat boshqa admin tomonidan olingan.")
    if claimed:
        view = await get_appeal_view(appeal_id)
        if view is not None:
            try:
                await send_long_message(
                    request.app["bot"], view.user.telegram_id,
                    t("appeal.status_changed", view.user.language_code, appeal_number=appeal.appeal_number,
                      status=appeal_status_text("IN_PROGRESS", view.user.language_code)),
                )
            except Exception:
                logger.exception("Could not notify citizen about web claim %s", appeal_id)
        await _set_notification_buttons(request.app["bot"], appeal_id, False)
        await _broadcast(
            request.app["bot"], await all_admin_ids(),
            f"🟡 <b>{_e(appeal.appeal_number)}</b> murojaati <code>{ctx.admin_id}</code> admin tomonidan web panelda ko‘rib chiqilmoqda.",
        )
    raise web.HTTPSeeOther(location=f"/admin/appeals/{appeal_id}")


async def appeal_release(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request)
    await _require_csrf(request, ctx)
    appeal_id = int(request.match_info["appeal_id"])
    appeal = await release_appeal_claim(appeal_id, ctx.admin_id)
    if appeal is None:
        raise web.HTTPNotFound()
    await _set_notification_buttons(request.app["bot"], appeal_id, True)
    await _broadcast(
        request.app["bot"], await all_admin_ids(),
        f"🔓 <b>{_e(appeal.appeal_number)}</b> murojaati yana barcha adminlar uchun ochildi.",
    )
    raise web.HTTPSeeOther(location=f"/admin/appeals/{appeal_id}")


async def appeal_reply(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request)
    data = await _require_csrf(request, ctx)
    appeal_id = int(request.match_info["appeal_id"])
    answer = str(data.get("answer", "")).strip()
    if not 2 <= len(answer) <= 4000:
        raise web.HTTPBadRequest(text="Javob 2-4000 belgidan iborat bo‘lishi kerak.")
    view = await get_appeal_view(appeal_id)
    if view is None:
        raise web.HTTPNotFound()
    appeal, user = view.appeal, view.user
    if appeal.status != "IN_PROGRESS" or appeal.admin_id != ctx.admin_id:
        raise web.HTTPConflict(text="Murojaat Sizga biriktirilmagan.")
    if appeal.claim_expires_at is not None and appeal.claim_expires_at <= utcnow():
        raise web.HTTPConflict(text="15 daqiqalik claim muddati tugagan.")

    citizen_text = t(
        "appeal.admin_answer", user.language_code,
        appeal_number=_e(appeal.appeal_number), admin_answer=_e(answer),
    )
    delivery_status, delivery_error_code = DELIVERY_DELIVERED, None
    try:
        await send_long_message(request.app["bot"], user.telegram_id, citizen_text)
    except Exception as exc:
        delivery_status = DELIVERY_FAILED
        delivery_error_code, unreachable = classify_delivery_exception(exc)
        if unreachable:
            await mark_user_unreachable(user.telegram_id)
        logger.exception("Web admin reply delivery failed for appeal %s", appeal_id)
    completed = await complete_appeal(
        appeal_id, ctx.admin_id, answer,
        delivery_status=delivery_status, delivery_error_code=delivery_error_code,
    )
    if completed is None:
        raise web.HTTPConflict(text="Murojaat holati o‘zgargan. Sahifani yangilang.")
    await _set_notification_buttons(request.app["bot"], appeal_id, False)
    await clear_notifications("appeal", appeal_id)
    await _broadcast(
        request.app["bot"], await all_admin_ids(),
        f"✅ <b>{_e(completed.appeal_number)}</b> murojaatiga <code>{ctx.admin_id}</code> admin web panel orqali javob yubordi.",
    )
    raise web.HTTPSeeOther(location=f"/admin/appeals/{appeal_id}")


async def appeal_pdf(request: web.Request) -> web.StreamResponse:
    await _require_context(request)
    appeal_id = int(request.match_info["appeal_id"])
    view = await get_appeal_view(appeal_id)
    if view is None or view.appeal.attachment_type != "PDF" or not view.appeal.attachment_file_id:
        raise web.HTTPNotFound()
    tg_file = await request.app["bot"].get_file(view.appeal.attachment_file_id)
    if not tg_file.file_path:
        raise web.HTTPNotFound()
    buf = io.BytesIO()
    await request.app["bot"].download_file(tg_file.file_path, destination=buf)
    data = buf.getvalue()
    name = view.appeal.attachment_name or f"{view.appeal.appeal_number}.pdf"
    safe_name = "".join(ch for ch in name if ch.isalnum() or ch in "._-")[:120] or "document.pdf"
    response = web.Response(body=data, content_type="application/pdf")
    response.headers["Content-Disposition"] = f'inline; filename="{safe_name}"'
    return _security_headers(response)


async def users(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request)
    q = request.rel_url.query.get("q", "")
    try:
        page_num = int(request.rel_url.query.get("page", "1"))
    except ValueError:
        page_num = 1
    result = await list_users(page=page_num, q=q)
    search = f'<div class="section"><div class="section-body"><form class="filters" method="get"><input class="input" name="q" value="{_e(q)}" placeholder="F.I.Sh., telefon, Telegram ID, hudud"><button class="btn btn-primary" type="submit">Qidirish</button></form></div></div>'
    rows = "".join(
        f'<tr><td>{_e(u.full_name or "—")}</td><td>{_e(u.phone or "—")}</td><td class="num">{_e(u.telegram_id)}</td><td>{_e(u.region or "—")}</td><td>{_e(u.district or "—")}</td><td>{_e(u.language_code)}</td><td>{_e(u.telegram_status)}</td><td>{_e(_dt(u.created_at))}</td></tr>'
        for u in result.items
    ) or '<tr><td colspan="8" class="empty">Foydalanuvchilar topilmadi.</td></tr>'
    table = f'<div class="section"><div class="section-head"><h2>Foydalanuvchilar ({result.total})</h2></div><div class="table-wrap"><table><thead><tr><th>F.I.Sh.</th><th>Telefon</th><th>Telegram ID</th><th>Viloyat</th><th>Tuman</th><th>Til</th><th>Telegram</th><th>Ro‘yxatdan o‘tgan</th></tr></thead><tbody>{rows}</tbody></table></div>{_page_links("/admin/users",result,{"q":q})}</div>'
    return _html(_layout(ctx, title="Foydalanuvchilar", active="users", body=search+table))


async def suggestions(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request, superadmin=True)
    status = request.rel_url.query.get("status", "")
    try:
        page_num = int(request.rel_url.query.get("page", "1"))
    except ValueError:
        page_num = 1
    result = await list_suggestions(page=page_num, status=status)
    rows = "".join(
        f'<tr><td class="num">{_e(v.suggestion.suggestion_number)}</td><td>{_e(v.user.full_name or "—")}<br><span class="muted">{_e(v.user.phone or "—")}</span></td><td><div class="text-block">{_e(v.suggestion.suggestion_text)}</div></td><td>{_e("Ko‘rib chiqildi" if v.suggestion.status=="REVIEWED" else "Yangi")}</td><td>{_e(_dt(v.suggestion.created_at))}</td><td>{("<form method=\"post\" action=\"/admin/suggestions/%s/review\"><input type=\"hidden\" name=\"csrf\" value=\"%s\"><button class=\"btn btn-primary\" type=\"submit\">Ko‘rib chiqildi</button></form>" % (v.suggestion.id,_e(ctx.csrf))) if v.suggestion.status=="NEW" else "—"}</td></tr>'
        for v in result.items
    ) or '<tr><td colspan="6" class="empty">Takliflar yo‘q.</td></tr>'
    table = f'<div class="section"><div class="section-head"><h2>Takliflar ({result.total})</h2><div><a class="btn btn-light" href="/admin/suggestions?status=NEW">Yangi</a> <a class="btn btn-light" href="/admin/suggestions?status=REVIEWED">Ko‘rib chiqilgan</a></div></div><div class="table-wrap"><table><thead><tr><th>Raqam</th><th>Foydalanuvchi</th><th>Taklif</th><th>Holat</th><th>Sana</th><th>Amal</th></tr></thead><tbody>{rows}</tbody></table></div>{_page_links("/admin/suggestions",result,{"status":status})}</div>'
    return _html(_layout(ctx, title="Takliflar", active="suggestions", body=table))


async def suggestion_review(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request, superadmin=True)
    await _require_csrf(request, ctx)
    suggestion_id = int(request.match_info["suggestion_id"])
    suggestion, changed = await review_suggestion(suggestion_id, ctx.admin_id)
    if suggestion is None:
        raise web.HTTPNotFound()
    if changed:
        for info in (await list_notifications("suggestion", suggestion.id)).values():
            try:
                await request.app["bot"].edit_message_reply_markup(
                    chat_id=info["chat_id"], message_id=info["message_id"], reply_markup=None
                )
            except Exception:
                logger.exception("Could not clear suggestion button %s", suggestion.id)
        citizen = await get_user_by_id(suggestion.user_id)
        if citizen is not None:
            try:
                await send_long_message(
                    request.app["bot"], citizen.telegram_id,
                    t("suggestion.reviewed", citizen.language_code, suggestion_number=suggestion.suggestion_number),
                )
            except Exception:
                logger.exception("Could not notify citizen about suggestion %s", suggestion.id)
        await clear_notifications("suggestion", suggestion.id)
        await _broadcast(
            request.app["bot"], await all_superadmin_ids(),
            f"☑️ <b>{_e(suggestion.suggestion_number)}</b> taklifi <code>{ctx.admin_id}</code> SUPERADMIN tomonidan web panelda ko‘rib chiqildi.",
        )
    raise web.HTTPSeeOther(location="/admin/suggestions")


async def admins(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request, superadmin=True)
    entries = await list_admin_entries()
    rows = ""
    for entry in entries:
        role = "ROOT SUPERADMIN" if entry.source == "ROOT" else entry.role
        remove = ""
        if entry.removable and entry.telegram_id != ctx.admin_id:
            remove = f'<form method="post" action="/admin/admins/{entry.telegram_id}/remove"><input type="hidden" name="csrf" value="{_e(ctx.csrf)}"><button class="btn btn-danger" type="submit">O‘chirish</button></form>'
        rows += f'<div class="admin-row"><div><b>{_e(role)}</b> · <span class="num">{_e(entry.telegram_id)}</span><br><span class="muted">Manba: {_e(entry.source)}</span></div>{remove}</div>'
    body = f'''<div class="grid-2"><div class="section"><div class="section-head"><h2>Adminlar</h2></div><div class="section-body">{rows or '<div class="empty">Adminlar yo‘q.</div>'}</div></div>
<div class="section"><div class="section-head"><h2>Admin qo‘shish / rolni yangilash</h2></div><div class="section-body"><form method="post" action="/admin/admins/add"><input type="hidden" name="csrf" value="{_e(ctx.csrf)}"><p><input class="input" name="telegram_id" inputmode="numeric" required placeholder="Telegram ID"></p><p><select class="select" name="role"><option value="ADMIN">ADMIN</option><option value="SUPERADMIN">SUPERADMIN</option></select></p><button class="btn btn-primary" type="submit">Saqlash</button></form></div></div></div>'''
    return _html(_layout(ctx, title="Adminlar", active="admins", body=body))


async def admin_add(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request, superadmin=True)
    data = await _require_csrf(request, ctx)
    raw = str(data.get("telegram_id", "")).strip()
    role = str(data.get("role", "")).strip()
    if not raw.isdigit() or int(raw) <= 0 or role not in {ROLE_ADMIN, ROLE_SUPERADMIN}:
        raise web.HTTPBadRequest(text="Telegram ID yoki rol noto‘g‘ri.")
    await add_or_update_admin(int(raw), role, ctx.admin_id)
    try:
        await send_long_message(
            request.app["bot"], int(raw),
            f"👨‍💼 Sizga botda <b>{role}</b> huquqi berildi. /admin orqali panelni ochishingiz mumkin.",
        )
    except Exception:
        logger.info("Could not proactively notify web-added admin %s", raw)
    raise web.HTTPSeeOther(location="/admin/admins")


async def admin_remove(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request, superadmin=True)
    await _require_csrf(request, ctx)
    target = int(request.match_info["telegram_id"])
    removed = await remove_dynamic_admin(target, ctx.admin_id)
    if not removed:
        raise web.HTTPConflict(text="Bu adminni o‘chirib bo‘lmaydi.")
    raise web.HTTPSeeOther(location="/admin/admins")


async def stats(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request)
    cats = await category_counts()
    regions = await region_counts()
    cat_rows = "".join(f'<tr><td>{_e(appeal_category_text(code,"uz_latn"))}</td><td>{count}</td></tr>' for code,count in cats) or '<tr><td colspan="2">Ma’lumot yo‘q</td></tr>'
    region_rows = "".join(f'<tr><td>{_e(region or "—")}</td><td>{count}</td></tr>' for region,count in regions) or '<tr><td colspan="2">Ma’lumot yo‘q</td></tr>'
    body = f'<div class="grid-2"><div class="section"><div class="section-head"><h2>Yo‘nalishlar kesimida</h2></div><table><thead><tr><th>Yo‘nalish</th><th>Soni</th></tr></thead><tbody>{cat_rows}</tbody></table></div><div class="section"><div class="section-head"><h2>Viloyatlar kesimida</h2></div><table><thead><tr><th>Viloyat</th><th>Soni</th></tr></thead><tbody>{region_rows}</tbody></table></div></div>'
    return _html(_layout(ctx, title="Statistika", active="stats", body=body))


async def logout(request: web.Request) -> web.StreamResponse:
    ctx = await _require_context(request)
    await _require_csrf(request, ctx)
    sid = request.cookies.get(web_admin_auth.cookie_name())
    await web_admin_auth.destroy_session(sid)
    response = web.HTTPSeeOther(location="/admin/")
    response.del_cookie(web_admin_auth.cookie_name(), path="/admin")
    return _security_headers(response)


async def admin_redirect(request: web.Request) -> web.StreamResponse:
    raise web.HTTPPermanentRedirect(location="/admin/")


def register_admin_web_routes(app: web.Application, bot: Bot) -> None:
    app["bot"] = bot
    app.router.add_get("/admin", admin_redirect)
    app.router.add_get("/admin/", admin_root)
    app.router.add_get("/admin/login/{token}", login)
    app.router.add_post("/admin/logout", logout)
    app.router.add_get("/admin/appeals", appeals)
    app.router.add_get("/admin/appeals/{appeal_id:\\d+}", appeal_detail)
    app.router.add_post("/admin/appeals/{appeal_id:\\d+}/claim", appeal_claim)
    app.router.add_post("/admin/appeals/{appeal_id:\\d+}/release", appeal_release)
    app.router.add_post("/admin/appeals/{appeal_id:\\d+}/reply", appeal_reply)
    app.router.add_get("/admin/appeals/{appeal_id:\\d+}/pdf", appeal_pdf)
    app.router.add_get("/admin/users", users)
    app.router.add_get("/admin/suggestions", suggestions)
    app.router.add_post("/admin/suggestions/{suggestion_id:\\d+}/review", suggestion_review)
    app.router.add_get("/admin/admins", admins)
    app.router.add_post("/admin/admins/add", admin_add)
    app.router.add_post("/admin/admins/{telegram_id:\\d+}/remove", admin_remove)
    app.router.add_get("/admin/stats", stats)
