from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine
from app.i18n import DEFAULT_LANGUAGE, normalize_language
from app.models import User
from app.services.datetime_utils import utcnow

TELEGRAM_STATUS_ACTIVE = "ACTIVE"
TELEGRAM_STATUS_UNREACHABLE = "UNREACHABLE"
PHONE_VERIFICATION_SOURCE_TELEGRAM = "TELEGRAM_CONTACT"


def _dialect_insert():
    return pg_insert if engine.dialect.name == "postgresql" else sqlite_insert


async def get_or_create_user_id(
    session: AsyncSession, telegram_id: int, telegram_username: str | None = None
) -> int:
    stmt = _dialect_insert()(User).values(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        language_code=DEFAULT_LANGUAGE,
        telegram_status=TELEGRAM_STATUS_ACTIVE,
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=[User.telegram_id])
    await session.execute(stmt)
    result = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
    return result.scalar_one()


async def save_user(
    telegram_id: int,
    telegram_username: str | None,
    full_name: str,
    phone: str,
    *,
    phone_verified: bool | None = None,
    phone_verification_source: str | None = None,
    language_code: str | None = None,
) -> User:
    """Create/update the citizen profile atomically.

    Registration passes ``phone_verified=True`` only after Telegram returns a
    Contact whose ``user_id`` matches the sender. Existing call sites that do
    not explicitly verify ownership retain the safe default ``False``.
    """
    now = utcnow()
    language = normalize_language(language_code)
    verified_for_insert = bool(phone_verified) if phone_verified is not None else False
    async with async_session() as session:
        async with session.begin():
            stmt = _dialect_insert()(User).values(
                telegram_id=telegram_id,
                telegram_username=telegram_username,
                full_name=full_name,
                phone=phone,
                phone_verified=verified_for_insert,
                phone_verification_source=(
                    phone_verification_source if phone_verified is not None else None
                ),
                phone_verified_at=now if phone_verified else None,
                language_code=language,
                telegram_status=TELEGRAM_STATUS_ACTIVE,
                last_seen_at=now,
                unreachable_at=None,
            )
            update_values = {
                "telegram_username": stmt.excluded.telegram_username,
                "full_name": stmt.excluded.full_name,
                "phone": stmt.excluded.phone,
                "telegram_status": TELEGRAM_STATUS_ACTIVE,
                "last_seen_at": now,
                "unreachable_at": None,
                "updated_at": func.now(),
            }
            if phone_verified is not None:
                update_values.update(
                    {
                        "phone_verified": verified_for_insert,
                        "phone_verification_source": phone_verification_source,
                        "phone_verified_at": now if phone_verified else None,
                    }
                )
            if language_code is not None:
                update_values["language_code"] = language
            stmt = stmt.on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_=update_values,
            )
            await session.execute(stmt)

        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one()


async def set_user_language(
    telegram_id: int, telegram_username: str | None, language_code: str
) -> User:
    """Persist language choice without overwriting registration fields."""
    language = normalize_language(language_code)
    now = utcnow()
    async with async_session() as session:
        async with session.begin():
            stmt = _dialect_insert()(User).values(
                telegram_id=telegram_id,
                telegram_username=telegram_username,
                language_code=language,
                telegram_status=TELEGRAM_STATUS_ACTIVE,
                last_seen_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={
                    "telegram_username": stmt.excluded.telegram_username,
                    "language_code": language,
                    "telegram_status": TELEGRAM_STATUS_ACTIVE,
                    "last_seen_at": now,
                    "unreachable_at": None,
                    "updated_at": func.now(),
                },
            )
            await session.execute(stmt)
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one()


async def update_verified_phone(
    telegram_id: int, telegram_username: str | None, phone: str
) -> User | None:
    """Replace only the citizen's verified phone number.

    Used by Settings -> phone update. Ownership is re-verified by the handler
    through Telegram Contact ``user_id`` before this function is called, so the
    database can safely mark the new number as Telegram-verified without
    rewriting the rest of the profile.
    """
    now = utcnow()
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    telegram_username=telegram_username,
                    phone=phone,
                    phone_verified=True,
                    phone_verification_source=PHONE_VERIFICATION_SOURCE_TELEGRAM,
                    phone_verified_at=now,
                    telegram_status=TELEGRAM_STATUS_ACTIVE,
                    last_seen_at=now,
                    unreachable_at=None,
                    updated_at=now,
                )
            )
            if result.rowcount == 0:
                return None

        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def save_user_location(telegram_id: int, region: str, district: str) -> User:
    now = utcnow()
    async with async_session() as session:
        async with session.begin():
            stmt = _dialect_insert()(User).values(
                telegram_id=telegram_id,
                region=region,
                district=district,
                language_code=DEFAULT_LANGUAGE,
                telegram_status=TELEGRAM_STATUS_ACTIVE,
                last_seen_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={
                    "region": stmt.excluded.region,
                    "district": stmt.excluded.district,
                    "telegram_status": TELEGRAM_STATUS_ACTIVE,
                    "last_seen_at": now,
                    "unreachable_at": None,
                    "updated_at": func.now(),
                },
            )
            await session.execute(stmt)

        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one()


async def mark_user_active(telegram_id: int) -> None:
    now = utcnow()
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    telegram_status=TELEGRAM_STATUS_ACTIVE,
                    last_seen_at=now,
                    unreachable_at=None,
                    updated_at=now,
                )
            )


async def mark_user_unreachable(telegram_id: int) -> None:
    now = utcnow()
    async with async_session() as session:
        async with session.begin():
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    telegram_status=TELEGRAM_STATUS_UNREACHABLE,
                    unreachable_at=now,
                    updated_at=now,
                )
            )


async def get_user_by_id(user_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def get_user_language(telegram_id: int) -> str:
    user = await get_user_by_telegram_id(telegram_id)
    return normalize_language(user.language_code if user is not None else None)


def is_registration_complete(user: User | None) -> bool:
    return bool(
        user
        and user.full_name
        and user.phone
        and user.phone_verified
        and user.region
        and user.district
    )
