from __future__ import annotations

from sqlalchemy import select, update

from app.database import async_session
from app.models import AdminContact
from app.services.datetime_utils import utcnow
from app.services.temporary_number import generate_temporary_number
from app.services.user_service import get_or_create_user_id

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
            user_id = await get_or_create_user_id(session, telegram_id, telegram_username)

            # contact_number is NOT NULL + UNIQUE, so it can't be left empty
            # until the row's id is known. Insert with a random 20-character
            # placeholder first, then flush to get the autoincrement id, then
            # overwrite it with the final ADM-XXXXXX number -- avoiding any
            # race window where two concurrent inserts could compute and
            # collide on the same number.
            contact = AdminContact(
                contact_number=generate_temporary_number(),
                user_id=user_id,
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


async def claim_admin_contact(contact_id: int, admin_id: int) -> tuple[AdminContact | None, bool]:
    """Atomically mark an admin-contact message as being handled by ``admin_id``.

    Mirrors ``app.services.appeal_service.claim_appeal`` -- same first-claim-
    wins rationale (MVP audit CRITICAL #2 / instruction #5): a conditional
    ``UPDATE ... WHERE status = 'NEW'`` so two admins clicking "Жавоб бериш"
    on the same message can't both end up handling it.

    Returns ``(contact, claimed)``:
    - ``(None, False)`` -- no contact with this id exists.
    - ``(contact, True)`` -- this call claimed it just now (status was NEW).
    - ``(contact, False)`` -- already claimed (by this same admin on a
      redelivered Telegram update, or by a different one) --
      ``contact.admin_id`` tells the caller who. No write happened.
    """
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(
                update(AdminContact)
                .where(AdminContact.id == contact_id, AdminContact.status == "NEW")
                .values(status="IN_PROGRESS", admin_id=admin_id, updated_at=utcnow())
            )
            claimed = result.rowcount > 0

            contact = await session.get(AdminContact, contact_id)

        return contact, claimed


async def complete_admin_contact(
    contact_id: int,
    admin_id: int,
    admin_answer: str,
    *,
    delivery_status: str | None = None,
    delivery_error_code: str | None = None,
) -> AdminContact | None:
    """Record the admin's answer and mark the contact message COMPLETED.

    Persists the admin answer regardless of Telegram delivery outcome. Delivery
    status/error are recorded separately so a blocked/deleted/unreachable account
    never causes the official answer to be lost. Returns None if the contact does
    not exist.
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
            contact.delivery_status = delivery_status
            contact.delivery_attempted_at = now if delivery_status else None
            contact.delivery_error_code = delivery_error_code
            contact.updated_at = now

        return contact
