from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select, update

from app.config import ADMIN_IDS, SUPERADMIN_IDS
from app.database import async_session
from app.models import AdminContact, Appeal, BotAdmin
from app.services.datetime_utils import utcnow

ROLE_SUPERADMIN = "SUPERADMIN"
ROLE_ADMIN = "ADMIN"
VALID_ROLES = {ROLE_SUPERADMIN, ROLE_ADMIN}


@dataclass(frozen=True)
class AdminEntry:
    telegram_id: int
    role: str
    source: str
    removable: bool


def is_root_superadmin(telegram_id: int) -> bool:
    return telegram_id in SUPERADMIN_IDS


def is_static_admin(telegram_id: int) -> bool:
    return telegram_id in ADMIN_IDS and telegram_id not in SUPERADMIN_IDS


async def get_admin_role(telegram_id: int) -> str | None:
    if is_root_superadmin(telegram_id):
        return ROLE_SUPERADMIN

    async with async_session() as session:
        row = await session.scalar(select(BotAdmin).where(BotAdmin.telegram_id == telegram_id))
        if row is not None:
            return row.role

    if is_static_admin(telegram_id):
        return ROLE_ADMIN
    return None


async def is_admin(telegram_id: int) -> bool:
    return await get_admin_role(telegram_id) is not None


async def is_superadmin(telegram_id: int) -> bool:
    return await get_admin_role(telegram_id) == ROLE_SUPERADMIN


async def all_admin_ids() -> list[int]:
    async with async_session() as session:
        dynamic = list((await session.scalars(select(BotAdmin.telegram_id))).all())
    return list(dict.fromkeys([*SUPERADMIN_IDS, *ADMIN_IDS, *dynamic]))


async def all_superadmin_ids() -> list[int]:
    async with async_session() as session:
        dynamic = list(
            (
                await session.scalars(
                    select(BotAdmin.telegram_id).where(BotAdmin.role == ROLE_SUPERADMIN)
                )
            ).all()
        )
    return list(dict.fromkeys([*SUPERADMIN_IDS, *dynamic]))


async def list_admin_entries() -> list[AdminEntry]:
    entries: dict[int, AdminEntry] = {}
    for telegram_id in SUPERADMIN_IDS:
        entries[telegram_id] = AdminEntry(telegram_id, ROLE_SUPERADMIN, "ROOT", False)
    for telegram_id in ADMIN_IDS:
        if telegram_id not in entries:
            entries[telegram_id] = AdminEntry(telegram_id, ROLE_ADMIN, "ENV", False)

    async with async_session() as session:
        rows = list((await session.scalars(select(BotAdmin).order_by(BotAdmin.id))).all())
    for row in rows:
        if row.telegram_id not in entries:
            entries[row.telegram_id] = AdminEntry(row.telegram_id, row.role, "DB", True)
    return list(entries.values())


async def add_or_update_admin(telegram_id: int, role: str, added_by: int) -> AdminEntry:
    if role not in VALID_ROLES:
        raise ValueError("invalid admin role")
    if telegram_id <= 0:
        raise ValueError("invalid Telegram id")
    if telegram_id in SUPERADMIN_IDS:
        return AdminEntry(telegram_id, ROLE_SUPERADMIN, "ROOT", False)
    if telegram_id in ADMIN_IDS:
        if role != ROLE_ADMIN:
            raise ValueError("ADMIN_IDS entries are managed in environment settings")
        return AdminEntry(telegram_id, ROLE_ADMIN, "ENV", False)

    now = utcnow()
    async with async_session() as session:
        async with session.begin():
            row = await session.scalar(select(BotAdmin).where(BotAdmin.telegram_id == telegram_id))
            if row is None:
                row = BotAdmin(
                    telegram_id=telegram_id,
                    role=role,
                    added_by=added_by,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.role = role
                row.added_by = added_by
                row.updated_at = now
        return AdminEntry(telegram_id, role, "DB", True)


async def remove_dynamic_admin(telegram_id: int, removed_by: int) -> bool:
    """Remove one DB-managed admin and release their unfinished work.

    ROOT/ENV admins cannot be removed from Telegram. A superadmin cannot remove
    their own DB record during the same session, preventing accidental lockout.
    """
    if telegram_id in SUPERADMIN_IDS or telegram_id in ADMIN_IDS:
        return False
    if telegram_id == removed_by:
        return False

    now = utcnow()
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(delete(BotAdmin).where(BotAdmin.telegram_id == telegram_id))
            if result.rowcount <= 0:
                return False
            await session.execute(
                update(Appeal)
                .where(
                    Appeal.status == "IN_PROGRESS",
                    Appeal.admin_id == telegram_id,
                    Appeal.admin_answer.is_(None),
                )
                .values(status="NEW", admin_id=None, claim_expires_at=None, updated_at=now)
            )
            await session.execute(
                update(AdminContact)
                .where(
                    AdminContact.status == "IN_PROGRESS",
                    AdminContact.admin_id == telegram_id,
                    AdminContact.admin_answer.is_(None),
                )
                .values(status="NEW", admin_id=None, updated_at=now)
            )
    return True
