from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

_LOGIN_TTL_SECONDS = 5 * 60
_SESSION_TTL_SECONDS = 8 * 60 * 60
_COOKIE_NAME = "ident_web_admin_session"

_redis = None
_namespace = "identifikatsiya:dev"
_base_url = ""
_memory_login: dict[str, tuple[int, float]] = {}
_memory_sessions: dict[str, tuple[int, str, float]] = {}

_CONSUME_SCRIPT = """
local v = redis.call('GET', KEYS[1])
if not v then return nil end
redis.call('DEL', KEYS[1])
return v
"""


@dataclass(frozen=True)
class WebAdminSession:
    admin_id: int
    csrf_token: str


def configure(redis=None, namespace: str = "identifikatsiya:dev", base_url: str = "") -> None:
    global _redis, _namespace, _base_url
    _redis = redis
    _namespace = namespace
    _base_url = base_url.rstrip("/")


def cookie_name() -> str:
    return _COOKIE_NAME


def _validate_base_url() -> str:
    url = urlsplit(_base_url)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise RuntimeError("Web admin requires WEBHOOK_BASE_URL with an HTTPS origin")
    if url.path not in {"", "/"} or url.query or url.fragment:
        raise RuntimeError("WEBHOOK_BASE_URL must be an HTTPS origin")
    return _base_url


def _purge_memory() -> None:
    now = time.monotonic()
    for token, (_, expiry) in list(_memory_login.items()):
        if expiry <= now:
            _memory_login.pop(token, None)
    for sid, (_, _, expiry) in list(_memory_sessions.items()):
        if expiry <= now:
            _memory_sessions.pop(sid, None)


async def issue_login_url(admin_id: int) -> str:
    if admin_id <= 0:
        raise ValueError("invalid admin id")
    base_url = _validate_base_url()
    token = secrets.token_urlsafe(32)
    if _redis is not None:
        ok = await _redis.set(
            f"{_namespace}:webadmin:login:{token}", str(admin_id), nx=True, ex=_LOGIN_TTL_SECONDS
        )
        if not ok:
            raise RuntimeError("could not allocate web admin login token")
    else:
        _purge_memory()
        _memory_login[token] = (admin_id, time.monotonic() + _LOGIN_TTL_SECONDS)
    return f"{base_url}/admin/login/{token}"


async def consume_login_token(token: str) -> int | None:
    if not token or len(token) > 256:
        return None
    if _redis is not None:
        value = await _redis.eval(_CONSUME_SCRIPT, 1, f"{_namespace}:webadmin:login:{token}")
        if value is None:
            return None
        if isinstance(value, bytes):
            value = value.decode("ascii", errors="ignore")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    _purge_memory()
    item = _memory_login.pop(token, None)
    return item[0] if item is not None else None


async def create_session(admin_id: int) -> tuple[str, WebAdminSession]:
    session_id = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    if _redis is not None:
        value = f"{admin_id}:{csrf}"
        await _redis.set(
            f"{_namespace}:webadmin:session:{session_id}", value, ex=_SESSION_TTL_SECONDS
        )
    else:
        _purge_memory()
        _memory_sessions[session_id] = (
            admin_id,
            csrf,
            time.monotonic() + _SESSION_TTL_SECONDS,
        )
    return session_id, WebAdminSession(admin_id=admin_id, csrf_token=csrf)


async def get_session(session_id: str | None) -> WebAdminSession | None:
    if not session_id or len(session_id) > 256:
        return None
    if _redis is not None:
        key = f"{_namespace}:webadmin:session:{session_id}"
        value = await _redis.get(key)
        if value is None:
            return None
        await _redis.expire(key, _SESSION_TTL_SECONDS)
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        admin_text, sep, csrf = str(value).partition(":")
        if not sep or not csrf:
            return None
        try:
            admin_id = int(admin_text)
        except ValueError:
            return None
        return WebAdminSession(admin_id=admin_id, csrf_token=csrf)
    _purge_memory()
    item = _memory_sessions.get(session_id)
    if item is None:
        return None
    admin_id, csrf, _ = item
    _memory_sessions[session_id] = (
        admin_id,
        csrf,
        time.monotonic() + _SESSION_TTL_SECONDS,
    )
    return WebAdminSession(admin_id=admin_id, csrf_token=csrf)


async def destroy_session(session_id: str | None) -> None:
    if not session_id:
        return
    if _redis is not None:
        await _redis.delete(f"{_namespace}:webadmin:session:{session_id}")
    else:
        _memory_sessions.pop(session_id, None)
