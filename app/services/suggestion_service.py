from __future__ import annotations

from sqlalchemy import select

from app.database import async_session
from app.models import Suggestion, User
from app.services.datetime_utils import utcnow
from app.services.temporary_number import generate_temporary_number

SUGGESTION_NUMBER_PREFIX = "TAK"
SUGGESTION_NUMBER_DIGITS = 6


def generate_suggestion_number(suggestion_id: int) -> str:
    """Format a sequential, human-readable suggestion number from the row id.

    ``suggestion_id`` comes from the ``suggestions`` table's autoincrement primary
    key (SQLite assigns it atomically per-insert and, with ``sqlite_autoincrement``
    enabled on the model, never reuses it), so numbers stay unique and strictly
    sequential -- TAK-000001, TAK-000002, ... -- even with concurrent submissions.
    """
    return f"{SUGGESTION_NUMBER_PREFIX}-{suggestion_id:0{SUGGESTION_NUMBER_DIGITS}d}"


async def create_suggestion(telegram_id: int, suggestion_text: str) -> Suggestion:
    """Create a new suggestion for the user identified by their Telegram id.

    Raises ValueError if no user with this telegram_id exists.
    """
    now = utcnow()

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if user is None:
                raise ValueError(f"User with telegram_id={telegram_id} not found")

            # suggestion_number is NOT NULL + UNIQUE, so it can't be left empty
            # until the row's id is known. Insert with a random 20-character
            # placeholder first, then flush to get the autoincrement id, then
            # overwrite it with the final TAK-XXXXXX number -- avoiding any race
            # window where two concurrent inserts could compute and collide on
            # the same number.
            suggestion = Suggestion(
                suggestion_number=generate_temporary_number(),
                user_id=user.id,
                suggestion_text=suggestion_text,
                status="NEW",
                created_at=now,
                updated_at=now,
            )
            session.add(suggestion)
            await session.flush()  # assigns suggestion.id

            suggestion.suggestion_number = generate_suggestion_number(suggestion.id)
            await session.flush()

        return suggestion


async def get_suggestion_by_id(suggestion_id: int) -> Suggestion | None:
    """Fetch a single suggestion by its primary key, or None if it doesn't exist."""
    async with async_session() as session:
        result = await session.execute(select(Suggestion).where(Suggestion.id == suggestion_id))
        return result.scalar_one_or_none()
