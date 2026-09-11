from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine
from app.models import User


def _dialect_insert():
    """The dialect-specific ``insert()`` construct for the two backends this
    app targets (Stage 11/12) -- shared by every upsert below so the
    dialect switch lives in exactly one place.
    """
    return pg_insert if engine.dialect.name == "postgresql" else sqlite_insert


async def get_or_create_user_id(
    session: AsyncSession, telegram_id: int, telegram_username: str | None = None
) -> int:
    """Return the ``users.id`` for ``telegram_id``, creating a minimal row if needed.

    Stage 12 / instruction #8: shared by ``app.services.admin_contact_service
    .create_admin_contact`` so its "create a minimal user if none exists yet"
    step is race-safe under concurrent requests for the same telegram_id,
    without duplicating the dialect-upsert logic already written for
    ``save_user``. Runs inside the CALLER's session/transaction (unlike
    ``save_user``, which opens its own) so it composes into a larger atomic
    transaction -- e.g. create-user-then-create-admin-contact stays one
    transaction, exactly as before.

    Uses ``ON CONFLICT (telegram_id) DO NOTHING`` rather than ``DO UPDATE``:
    callers of this helper only want an id to hang a foreign key off of, and
    must never clobber an already-registered user's full_name/phone/region/
    district (unlike save_user, which is an explicit "the user just told me
    their name/phone" write). If the row already exists, the INSERT is a
    no-op and the follow-up SELECT simply reads it back -- race-safe because
    ``DO NOTHING`` never raises ``IntegrityError`` on the ``telegram_id``
    UNIQUE constraint the way a plain INSERT would.
    """
    stmt = _dialect_insert()(User).values(telegram_id=telegram_id, telegram_username=telegram_username)
    stmt = stmt.on_conflict_do_nothing(index_elements=[User.telegram_id])
    await session.execute(stmt)

    result = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
    return result.scalar_one()


async def save_user(
    telegram_id: int,
    telegram_username: str | None,
    full_name: str,
    phone: str,
) -> User:
    """Create a new user or update the existing one for this telegram_id.

    Stage 11 / instruction #3: a single atomic
    ``INSERT ... ON CONFLICT (telegram_id) DO UPDATE`` instead of the old
    "SELECT, then INSERT-or-UPDATE" (check-then-act). The old pattern could race under both SQLite and PostgreSQL: two requests could both see "no row yet" and
    both try to INSERT, and the loser would raise ``IntegrityError`` on the
    ``telegram_id`` UNIQUE constraint instead of updating. The upsert makes
    the same call safe under real concurrency on either database -- see
    tests/test_user_upsert.py's concurrent-registration test (``asyncio.gather``
    with the same telegram_id).

    ``sqlalchemy.dialects.sqlite``/``postgresql`` are the only two dialects
    this app targets (current: SQLite; future: PostgreSQL), and both expose
    the identical ``ON CONFLICT (...) DO UPDATE SET ...`` API -- the dialect
    switch below (mirroring the one already in app/database.py's pragma
    listener) is the only difference between the two backends.
    """
    async with async_session() as session:
        async with session.begin():
            stmt = _dialect_insert()(User).values(
                telegram_id=telegram_id,
                telegram_username=telegram_username,
                full_name=full_name,
                phone=phone,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={
                    "telegram_username": stmt.excluded.telegram_username,
                    "full_name": stmt.excluded.full_name,
                    "phone": stmt.excluded.phone,
                    # A Core-level "ON CONFLICT DO UPDATE" bypasses the ORM
                    # unit-of-work, so the column's onupdate=func.now() never
                    # fires on its own here (unlike the old ORM-attribute-set
                    # path) -- set it explicitly to keep updated_at behavior
                    # unchanged. created_at is deliberately left out of set_,
                    # same as before: it must never change on an update.
                    "updated_at": func.now(),
                },
            )
            await session.execute(stmt)

        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one()


async def save_user_location(telegram_id: int, region: str, district: str) -> User:
    """Save the selected region/district for an existing (or new) user.

    Updates the existing record for this telegram_id instead of creating a duplicate.

    Stage 12 / instruction #7: same "SELECT, then INSERT-or-UPDATE" ->
    ``ON CONFLICT DO UPDATE`` rewrite as ``save_user`` (Stage 11), same
    concurrency rationale -- see save_user's docstring. Scoped to only
    region/district: telegram_username/full_name/phone are deliberately left
    out of both the INSERT ``values()`` (so a brand-new row's other columns
    stay NULL, exactly as ``User(telegram_id=telegram_id)`` used to leave
    them) and the ``DO UPDATE SET`` (so an existing user's profile data is
    never touched by this call) -- see
    tests/test_user_upsert.py::test_save_user_location_preserves_profile_fields.
    """
    async with async_session() as session:
        async with session.begin():
            stmt = _dialect_insert()(User).values(
                telegram_id=telegram_id,
                region=region,
                district=district,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={
                    "region": stmt.excluded.region,
                    "district": stmt.excluded.district,
                    "updated_at": func.now(),
                },
            )
            await session.execute(stmt)

        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one()


async def get_user_by_id(user_id: int) -> User | None:
    """Fetch a single user by their primary key, or None if it doesn't exist."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    """Fetch a single user by their Telegram id, or None if it doesn't exist."""
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()
