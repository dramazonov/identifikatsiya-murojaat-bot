from __future__ import annotations

from sqlalchemy import select

from app.database import async_session
from app.models import User


async def save_user(
    telegram_id: int,
    telegram_username: str | None,
    full_name: str,
    phone: str,
) -> User:
    """Create a new user or update the existing one for this telegram_id."""
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if user is None:
                user = User(telegram_id=telegram_id)
                session.add(user)

            user.telegram_username = telegram_username
            user.full_name = full_name
            user.phone = phone

        return user


async def save_user_location(telegram_id: int, region: str, district: str) -> User:
    """Save the selected region/district for an existing (or new) user.

    Updates the existing record for this telegram_id instead of creating a duplicate.
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if user is None:
                user = User(telegram_id=telegram_id)
                session.add(user)

            user.region = region
            user.district = district

        return user


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
