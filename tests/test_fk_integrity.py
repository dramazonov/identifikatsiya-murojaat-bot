"""Tests for SQLite foreign-key enforcement (Stage 11 / instruction #2).

Before Stage 11, ``PRAGMA foreign_keys=ON`` was never issued, so SQLite
never actually enforced the ``ForeignKey("users.id")`` declared on
appeals.user_id / suggestions.user_id / admin_contacts.user_id -- a row
referencing a non-existent user would insert successfully. These tests prove
the pragma (app/database.py's ``_set_sqlite_pragmas``) actually takes effect,
using the real (isolated, see tests/conftest.py) test database.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import async_session
from app.models import AdminContact, Appeal, Suggestion, User
from app.services.appeal_service import create_appeal
from app.services.suggestion_service import create_suggestion
from app.services.user_service import save_user

NONEXISTENT_USER_ID = 999_999_999


async def test_appeal_with_nonexistent_user_id_is_rejected() -> None:
    async with async_session() as session:
        raised = False
        try:
            async with session.begin():
                session.add(
                    Appeal(
                        appeal_number="FK-TEST-0001",
                        user_id=NONEXISTENT_USER_ID,
                        appeal_text="Orphan appeal text for FK enforcement test.",
                        status="NEW",
                    )
                )
        except IntegrityError:
            raised = True

        assert raised, "appeals.user_id FK is not being enforced"


async def test_suggestion_with_nonexistent_user_id_is_rejected() -> None:
    async with async_session() as session:
        raised = False
        try:
            async with session.begin():
                session.add(
                    Suggestion(
                        suggestion_number="FK-TEST-0002",
                        user_id=NONEXISTENT_USER_ID,
                        suggestion_text="Orphan suggestion text for FK enforcement test.",
                        status="NEW",
                    )
                )
        except IntegrityError:
            raised = True

        assert raised, "suggestions.user_id FK is not being enforced"


async def test_admin_contact_with_nonexistent_user_id_is_rejected() -> None:
    async with async_session() as session:
        raised = False
        try:
            async with session.begin():
                session.add(
                    AdminContact(
                        contact_number="FK-TEST-0003",
                        user_id=NONEXISTENT_USER_ID,
                        message_text="Orphan admin contact for FK enforcement test.",
                        status="NEW",
                    )
                )
        except IntegrityError:
            raised = True

        assert raised, "admin_contacts.user_id FK is not being enforced"


async def test_admin_contact_with_null_user_id_is_still_allowed() -> None:
    """user_id is nullable on admin_contacts by design (instruction #2 must
    not turn a legitimate NULL into a rejected write) -- FK enforcement never
    applies to a NULL foreign key column, on any database.
    """
    async with async_session() as session:
        async with session.begin():
            session.add(
                AdminContact(
                    contact_number="FK-TEST-0004",
                    user_id=None,
                    message_text="Admin contact with no resolvable user.",
                    status="NEW",
                )
            )
    # No exception raised -- reaching here is the assertion.


async def test_appeal_and_suggestion_with_real_user_still_work() -> None:
    """Regression guard: turning FK enforcement on must not break the normal,
    valid path (create_appeal/create_suggestion always insert a real user_id
    from an existing users row).
    """
    telegram_id = 940200001
    await save_user(
        telegram_id=telegram_id,
        telegram_username="fkgooduser",
        full_name="FK Good User Testov",
        phone="+998901234580",
    )

    appeal = await create_appeal(telegram_id=telegram_id, appeal_text="A perfectly valid appeal text.")
    suggestion = await create_suggestion(
        telegram_id=telegram_id, suggestion_text="A perfectly valid suggestion text."
    )

    assert appeal.id is not None
    assert suggestion.id is not None


async def test_deleting_a_referenced_user_is_rejected_not_silently_orphaning() -> None:
    """With FK enforcement on, the database itself now refuses to create an
    orphan row -- deleting a user that still has an appeal must fail (there is
    no ON DELETE CASCADE declared), rather than silently leaving a dangling
    appeals.user_id behind as it would have before Stage 11.
    """
    telegram_id = 940200002
    await save_user(
        telegram_id=telegram_id,
        telegram_username="fkdeletetest",
        full_name="FK Delete Test Testov",
        phone="+998901234581",
    )
    await create_appeal(telegram_id=telegram_id, appeal_text="Appeal that keeps its user alive.")

    async with async_session() as session:
        raised = False
        try:
            async with session.begin():
                user = (
                    await session.execute(select(User).where(User.telegram_id == telegram_id))
                ).scalar_one()
                await session.delete(user)
        except IntegrityError:
            raised = True

        assert raised, "deleting a user with a referencing appeal should be rejected by the FK"
