from __future__ import annotations

import uuid

from sqlalchemy import select

from app.database import async_session
from app.models import AdminContact, User
from app.services.datetime_utils import utcnow

CONTACT_NUMBER_PREFIX = "ADM"
CONTACT_NUMBER_DIGITS = 6


def generate_contact_number(contact_id: int) -> str:
    """Format a sequential, human-readable contact number from the row id.

    Mirrors generate_appeal_number/generate_suggestion_number: ``contact_id``
    comes from the ``admin_contacts`` table's autoincrement primary key
    (SQLite assigns it atomically per-insert and, with ``sqlite_autoincrement``
    enabled on the model, never reuses it), so numbers stay unique and
    strictly sequential -- ADM-000001, ADM-000002, ... -- even with
    concurrent submissions.
    """
    return f"{CONTACT_NUMBER_PREFIX}-{contact_id:0{CONTACT_NUMBER_DIGITS}d}"


async def create_admin_contact(
    telegram_id: int,
    telegram_username: str | None,
    message_text: str,
) -> AdminContact:
    """Create a new "contact admin" message for the given Telegram user.

    Unlike create_appeal/create_suggestion, this does NOT require the citizen
    to have completed the registration flow. If no matching ``users`` row
    exists yet, a minimal one (telegram_id + telegram_username only) is
    created here -- this keeps enough identity to deliver the admin's reply
    later, while leaving full_name/phone/region/district unset (displayed as
    "Маълумот киритилмаган" in the admin notification). If the citizen later
    completes full registration, save_user() updates this same row (it looks
    up by telegram_id) instead of creating a duplicate.
    """
    now = utcnow()

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()

            if user is None:
                user = User(telegram_id=telegram_id, telegram_username=telegram_username)
                session.add(user)
                await session.flush()  # assigns user.id

            # contact_number is NOT NULL + UNIQUE, so it can't be left empty
            # until the row's id is known. Insert with a globally-unique
            # placeholder first, then flush to get the autoincrement id, then
            # overwrite it with the final ADM-XXXXXX number -- avoiding any
            # race window where two concurrent inserts could compute and
            # collide on the same number.
            contact = AdminContact(
                contact_number=f"TMP-{uuid.uuid4().hex}",
                user_id=user.id,
                message_text=message_text,
                status="NEW",
                created_at=now,
                updated_at=now,
            )
            session.add(contact)
            await session.flush()  # assigns contact.id

            contact.contact_number = generate_contact_number(contact.id)
            await session.flush()

        return contact


async def get_admin_contact_by_id(contact_id: int) -> AdminContact | None:
    """Fetch a single admin contact message by its primary key, or None."""
    async with async_session() as session:
        result = await session.execute(select(AdminContact).where(AdminContact.id == contact_id))
        return result.scalar_one_or_none()


async def set_admin_contact_in_progress(contact_id: int, admin_id: int) -> AdminContact | None:
    """Mark an admin contact message as being handled by an admin.

    Sets status=IN_PROGRESS and records which admin picked it up. Returns None
    if no contact with this id exists (caller should treat that as "not found").
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(AdminContact).where(AdminContact.id == contact_id))
            contact = result.scalar_one_or_none()

            if contact is None:
                return None

            contact.status = "IN_PROGRESS"
            contact.admin_id = admin_id
            contact.updated_at = utcnow()

        return contact


async def complete_admin_contact(
    contact_id: int, admin_id: int, admin_answer: str
) -> AdminContact | None:
    """Record the admin's answer and mark the contact message COMPLETED.

    Callers must only call this AFTER the answer has been successfully
    delivered to the citizen -- this function itself does no delivery, only
    persistence. Returns None if no contact with this id exists.
    """
    now = utcnow()

    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(AdminContact).where(AdminContact.id == contact_id))
            contact = result.scalar_one_or_none()

            if contact is None:
                return None

            contact.status = "COMPLETED"
            contact.admin_id = admin_id
            contact.admin_answer = admin_answer
            contact.answered_at = now
            contact.updated_at = now

        return contact
