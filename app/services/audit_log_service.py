from __future__ import annotations

import json
from dataclasses import dataclass
from math import ceil
from typing import Any

from sqlalchemy import String, cast, func, select

from app.database import async_session
from app.models import AuditLog
from app.services.admin_service import get_admin_role

AUDIT_PAGE_SIZE = 50
VALID_CHANNELS = {"TELEGRAM", "WEB"}


@dataclass(frozen=True)
class AuditPage:
    items: list[AuditLog]
    page: int
    total_pages: int
    total: int


def _serialize_details(details: dict[str, Any] | None) -> str | None:
    if not details:
        return None
    return json.dumps(details, ensure_ascii=False, separators=(",", ":"), default=str)


def parse_audit_details(row: AuditLog) -> dict[str, Any]:
    if not row.details_json:
        return {}
    try:
        value = json.loads(row.details_json)
    except (TypeError, ValueError):
        return {"raw": row.details_json}
    return value if isinstance(value, dict) else {"value": value}


async def write_audit_log(
    *,
    actor_telegram_id: int,
    action: str,
    target_type: str,
    target_id: str | int | None = None,
    channel: str,
    details: dict[str, Any] | None = None,
    actor_role: str | None = None,
) -> AuditLog:
    """Append one privileged-action audit row.

    Audit payloads intentionally contain identifiers, statuses and result counts,
    not message bodies, bot tokens, database URLs, Redis URLs or session secrets.
    """
    if actor_telegram_id <= 0:
        raise ValueError("invalid audit actor")
    action = action.strip().upper()
    target_type = target_type.strip().upper()
    channel = channel.strip().upper()
    if not action or len(action) > 64:
        raise ValueError("invalid audit action")
    if not target_type or len(target_type) > 40:
        raise ValueError("invalid audit target type")
    if channel not in VALID_CHANNELS:
        raise ValueError("invalid audit channel")
    role = actor_role or await get_admin_role(actor_telegram_id) or "UNKNOWN"
    if len(role) > 20:
        role = role[:20]
    target_value = None if target_id is None else str(target_id)
    if target_value is not None and len(target_value) > 128:
        target_value = target_value[:128]

    row = AuditLog(
        actor_telegram_id=actor_telegram_id,
        actor_role=role,
        action=action,
        target_type=target_type,
        target_id=target_value,
        channel=channel,
        details_json=_serialize_details(details),
    )
    async with async_session() as session:
        async with session.begin():
            session.add(row)
            await session.flush()
        return row


async def list_recent_audit_logs(*, limit: int = 20) -> list[AuditLog]:
    if limit <= 0 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    async with async_session() as session:
        return list(
            (
                await session.scalars(
                    select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
                )
            ).all()
        )


async def list_audit_logs(
    *,
    page: int = 1,
    actor: str = "",
    action: str = "",
    channel: str = "",
) -> AuditPage:
    page = max(1, page)
    predicates = []
    actor = actor.strip()
    action = action.strip().upper()
    channel = channel.strip().upper()
    if actor:
        predicates.append(cast(AuditLog.actor_telegram_id, String).like(f"%{actor}%"))
    if action:
        predicates.append(AuditLog.action == action)
    if channel in VALID_CHANNELS:
        predicates.append(AuditLog.channel == channel)

    async with async_session() as session:
        count_stmt = select(func.count(AuditLog.id))
        stmt = select(AuditLog)
        for predicate in predicates:
            count_stmt = count_stmt.where(predicate)
            stmt = stmt.where(predicate)
        total = int((await session.execute(count_stmt)).scalar_one())
        total_pages = max(1, ceil(total / AUDIT_PAGE_SIZE))
        page = min(page, total_pages)
        items = list(
            (
                await session.scalars(
                    stmt.order_by(AuditLog.id.desc())
                    .offset((page - 1) * AUDIT_PAGE_SIZE)
                    .limit(AUDIT_PAGE_SIZE)
                )
            ).all()
        )
    return AuditPage(items=items, page=page, total_pages=total_pages, total=total)
