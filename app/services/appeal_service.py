from __future__ import annotations

import uuid

from sqlalchemy import select

from app.database import async_session
from app.models import Appeal, User
from app.services.datetime_utils import utcnow

APPEAL_NUMBER_PREFIX = "MUR"
APPEAL_NUMBER_DIGITS = 6


def generate_appeal_number(appeal_id: int) -> str:
    """Format a sequential, human-readable appeal number from the appeal's row id.

    ``appeal_id`` comes from the ``appeals`` table's autoincrement primary key
    (SQLite assigns it atomically per-insert and, with ``sqlite_autoincrement``
    enabled on the model, never reuses it), so numbers stay unique and strictly
    sequential -- MUR-000001, MUR-000002, ... -- even with concurrent submissions.
    """
    return f"{APPEAL_NUMBER_PREFIX}-{appeal_id:0{APPEAL_NUMBER_DIGITS}d}"


async def create_appeal(telegram_id: int, appeal_text: str) -> Appeal:
    """Create a new appeal for the user identified by their Telegram id.

    Raises ValueError if no user with this telegram_id exists.
    """
    now = utcnow()

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if user is None:
                raise ValueError(f"User with telegram_id={telegram_id} not found")

            # appeal_number is NOT NULL + UNIQUE, so it can't be left empty until
            # the row's id is known. Insert with a globally-unique placeholder
            # first, then flush to get the autoincrement id, then overwrite it
            # with the final MUR-XXXXXX number -- avoiding any race window where
            # two concurrent inserts could compute and collide on the same number.
            appeal = Appeal(
                appeal_number=f"TMP-{uuid.uuid4().hex}",
                user_id=user.id,
                appeal_text=appeal_text,
                status="NEW",
                created_at=now,
                updated_at=now,
            )
            session.add(appeal)
            await session.flush()  # assigns appeal.id

            appeal.appeal_number = generate_appeal_number(appeal.id)
            await session.flush()

        return appeal


async def get_appeal_by_id(appeal_id: int) -> Appeal | None:
    """Fetch a single appeal by its primary key, or None if it doesn't exist."""
    async with async_session() as session:
        result = await session.execute(select(Appeal).where(Appeal.id == appeal_id))
        return result.scalar_one_or_none()


async def set_appeal_in_progress(appeal_id: int, admin_id: int) -> Appeal | None:
    """Mark an appeal as being handled by an admin.

    Sets status=IN_PROGRESS and records which admin picked it up. Returns None
    if no appeal with this id exists (caller should treat that as "not found").
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(Appeal).where(Appeal.id == appeal_id))
            appeal = result.scalar_one_or_none()

            if appeal is None:
                return None

            appeal.status = "IN_PROGRESS"
            appeal.admin_id = admin_id
            appeal.updated_at = utcnow()

        return appeal


async def complete_appeal(appeal_id: int, admin_id: int, admin_answer: str) -> Appeal | None:
    """Record the admin's answer and mark the appeal COMPLETED.

    Callers must only call this AFTER the answer has been successfully delivered
    to the citizen -- this function itself does no delivery, only persistence.
    Returns None if no appeal with this id exists.
    """
    now = utcnow()

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(Appeal).where(Appeal.id == appeal_id))
            appeal = result.scalar_one_or_none()

            if appeal is None:
                return None

            appeal.status = "COMPLETED"
            appeal.admin_id = admin_id
            appeal.admin_answer = admin_answer
            appeal.answered_at = now
            appeal.updated_at = now

        return appeal
