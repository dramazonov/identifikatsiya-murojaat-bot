from __future__ import annotations

from sqlalchemy import select, update

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
            # the row's id is known. Insert with a random 20-character placeholder
            # first, then flush to get the autoincrement id, then overwrite it
            # with the final MUR-XXXXXX number -- avoiding any race window where
            # two concurrent inserts could compute and collide on the same number.
            appeal = Appeal(
                appeal_number=generate_temporary_number(),
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


async def claim_appeal(appeal_id: int, admin_id: int) -> tuple[Appeal | None, bool]:
    """Atomically mark an appeal as being handled by ``admin_id`` -- first claim wins.

    MVP audit CRITICAL #2 / instruction #5: two admins clicking "Жавоб бериш"
    on the same appeal at nearly the same time must not both end up "handling"
    it (the previous unconditional UPDATE let the second click silently
    overwrite the first admin's claim -- last-write-wins). This does the claim
    as a single conditional ``UPDATE ... WHERE status = 'NEW'``: only the
    request that actually flips the row from NEW to IN_PROGRESS "wins"; SQLite
    serializes concurrent writers at the database level, so this is safe even
    under real concurrent calls, not just sequential ones.

    Returns ``(appeal, claimed)``:
    - ``(None, False)`` -- no appeal with this id exists.
    - ``(appeal, True)`` -- this call claimed it just now (status was NEW).
    - ``(appeal, False)`` -- appeal exists but was already claimed (by this
      same admin on a redelivered Telegram update, or by a different one) --
      ``appeal.admin_id`` tells the caller who. No write happened.
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                update(Appeal)
                .where(Appeal.id == appeal_id, Appeal.status == "NEW")
                .values(status="IN_PROGRESS", admin_id=admin_id, updated_at=utcnow())
            )
            claimed = result.rowcount > 0

            appeal = await session.get(Appeal, appeal_id)

        return appeal, claimed


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

            appeal.status = "COMPLETED"
            appeal.admin_id = admin_id
            appeal.admin_answer = admin_answer
            appeal.answered_at = now
            appeal.delivery_status = delivery_status
            appeal.delivery_attempted_at = now if delivery_status else None
            appeal.delivery_error_code = delivery_error_code
            appeal.updated_at = now

        return appeal
