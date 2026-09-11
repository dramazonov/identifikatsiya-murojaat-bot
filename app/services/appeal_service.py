from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, or_, select, update

from app.database import async_session
from app.models import Appeal, User
from app.services.datetime_utils import utcnow
from app.services.temporary_number import generate_temporary_number

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


async def create_appeal(
    telegram_id: int,
    appeal_text: str,
    *,
    category_code: str | None = None,
    subject: str | None = None,
    attachment_type: str | None = None,
    attachment_file_id: str | None = None,
    attachment_file_unique_id: str | None = None,
    attachment_name: str | None = None,
    attachment_size: int | None = None,
) -> Appeal:
    """Create a new appeal for the user identified by their Telegram id.

    Stage 22 metadata is keyword-only so every pre-Stage-22 caller remains
    backward compatible. Raises ValueError if no matching user exists.
    """
    now = utcnow()

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if user is None:
                raise ValueError(f"User with telegram_id={telegram_id} not found")

            # appeal_number is NOT NULL + UNIQUE, so it can't be left empty until
            # the row's id is known. Insert with a random 20-character placeholder
            # first, then flush to get the autoincrement id, then overwrite it
            # with the final MUR-XXXXXX number -- avoiding any race window where
            # two concurrent inserts could compute and collide on the same number.
            appeal = Appeal(
                appeal_number=generate_temporary_number(),
                user_id=user.id,
                category_code=category_code,
                subject=subject,
                appeal_text=appeal_text,
                attachment_type=attachment_type,
                attachment_file_id=attachment_file_id,
                attachment_file_unique_id=attachment_file_unique_id,
                attachment_name=attachment_name,
                attachment_size=attachment_size,
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


CLAIM_TIMEOUT_MINUTES = 15


async def claim_appeal(appeal_id: int, admin_id: int) -> tuple[Appeal | None, bool]:
    """Atomically claim an appeal for 15 minutes; expired claims can be reclaimed."""
    now = utcnow()
    expires = now + timedelta(minutes=CLAIM_TIMEOUT_MINUTES)
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                update(Appeal)
                .where(
                    Appeal.id == appeal_id,
                    or_(
                        Appeal.status == "NEW",
                        (Appeal.status == "IN_PROGRESS")
                        & (Appeal.claim_expires_at.is_not(None))
                        & (Appeal.claim_expires_at <= now),
                    ),
                )
                .values(
                    status="IN_PROGRESS",
                    admin_id=admin_id,
                    claim_expires_at=expires,
                    updated_at=now,
                )
            )
            claimed = result.rowcount > 0
            appeal = await session.get(Appeal, appeal_id)
        return appeal, claimed


async def release_appeal_claim(appeal_id: int, admin_id: int) -> Appeal | None:
    """Release only the current admin's unfinished claim back to NEW."""
    now = utcnow()
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                update(Appeal)
                .where(
                    Appeal.id == appeal_id,
                    Appeal.status == "IN_PROGRESS",
                    Appeal.admin_id == admin_id,
                    Appeal.admin_answer.is_(None),
                )
                .values(status="NEW", admin_id=None, claim_expires_at=None, updated_at=now)
            )
            return await session.get(Appeal, appeal_id)


async def list_admin_appeals(status: str, *, limit: int = 10) -> list[Appeal]:
    now = utcnow()
    async with async_session() as session:
        stmt = select(Appeal)
        if status == "NEW":
            stmt = stmt.where(
                or_(
                    Appeal.status == "NEW",
                    (Appeal.status == "IN_PROGRESS")
                    & (Appeal.claim_expires_at.is_not(None))
                    & (Appeal.claim_expires_at <= now),
                )
            )
        else:
            stmt = stmt.where(Appeal.status == status)
        result = await session.execute(stmt.order_by(Appeal.id.desc()).limit(limit))
        return list(result.scalars().all())


async def search_appeal_by_number(appeal_number: str) -> Appeal | None:
    async with async_session() as session:
        result = await session.execute(
            select(Appeal).where(func.upper(Appeal.appeal_number) == appeal_number.strip().upper())
        )
        return result.scalar_one_or_none()


async def admin_appeal_counts() -> dict[str, int]:
    now = utcnow()
    async with async_session() as session:
        result = await session.execute(select(Appeal.status, func.count(Appeal.id)).group_by(Appeal.status))
        counts = {status: int(count) for status, count in result.all()}
        expired = await session.execute(
            select(func.count(Appeal.id)).where(
                Appeal.status == "IN_PROGRESS",
                Appeal.claim_expires_at.is_not(None),
                Appeal.claim_expires_at <= now,
            )
        )
        expired_count = int(expired.scalar_one())
        counts["NEW"] = counts.get("NEW", 0) + expired_count
        counts["IN_PROGRESS"] = max(0, counts.get("IN_PROGRESS", 0) - expired_count)
        return counts


async def complete_appeal(
    appeal_id: int,
    admin_id: int,
    admin_answer: str,
    *,
    delivery_status: str | None = None,
    delivery_error_code: str | None = None,
) -> Appeal | None:
    """Record the admin's answer and mark the appeal COMPLETED.

    Persists the admin answer regardless of Telegram delivery outcome. Delivery
    status/error are recorded separately so a blocked/deleted/unreachable account
    never causes the official answer to be lost. Returns None if the appeal does
    not exist.
    """
    now = utcnow()

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(Appeal).where(Appeal.id == appeal_id))
            appeal = result.scalar_one_or_none()

            if appeal is None:
                return None
            if appeal.status != "IN_PROGRESS" or appeal.admin_id != admin_id:
                return None

            appeal.status = "COMPLETED"
            appeal.admin_id = admin_id
            appeal.admin_answer = admin_answer
            appeal.answered_at = now
            appeal.claim_expires_at = None
            appeal.delivery_status = delivery_status
            appeal.delivery_attempted_at = now if delivery_status else None
            appeal.delivery_error_code = delivery_error_code
            appeal.updated_at = now

        return appeal

async def count_user_appeals(telegram_id: int) -> int:
    """Count appeals owned by one Telegram user."""
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Appeal.id))
            .join(User, Appeal.user_id == User.id)
            .where(User.telegram_id == telegram_id)
        )
        return int(result.scalar_one())


async def list_user_appeals(
    telegram_id: int, *, offset: int = 0, limit: int = 5
) -> list[Appeal]:
    """Return one citizen's appeals newest-first.

    The ownership predicate lives in the query, not only in the Telegram
    callback layer, so a forged appeal id/page cannot expose another user's
    records.
    """
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if limit <= 0 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    async with async_session() as session:
        result = await session.execute(
            select(Appeal)
            .join(User, Appeal.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .order_by(Appeal.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


async def get_user_appeal_by_id(telegram_id: int, appeal_id: int) -> Appeal | None:
    """Fetch an appeal only when it belongs to ``telegram_id``."""
    async with async_session() as session:
        result = await session.execute(
            select(Appeal)
            .join(User, Appeal.user_id == User.id)
            .where(User.telegram_id == telegram_id, Appeal.id == appeal_id)
        )
        return result.scalar_one_or_none()
