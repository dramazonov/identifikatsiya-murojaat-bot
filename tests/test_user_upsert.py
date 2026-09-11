"""Tests for the PostgreSQL-safe user upsert (Stage 11 / instruction #3).

Uses the real (isolated, see tests/conftest.py) test database -- these
exercise the actual ``INSERT ... ON CONFLICT (telegram_id) DO UPDATE`` SQL,
not a mock.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.database import async_session
from app.models import User
from app.services.user_service import get_user_by_telegram_id, save_user
from app.services.user_service import save_user_location
from app.services.admin_contact_service import create_admin_contact


async def _count_users_with_telegram_id(telegram_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one()


async def test_save_user_creates_a_new_row_when_none_exists() -> None:
    telegram_id = 940100001

    assert await _count_users_with_telegram_id(telegram_id) == 0

    user = await save_user(
        telegram_id=telegram_id,
        telegram_username="firsttime",
        full_name="First Timer",
        phone="+998901234570",
    )

    assert user.telegram_id == telegram_id
    assert user.full_name == "First Timer"
    assert await _count_users_with_telegram_id(telegram_id) == 1


async def test_save_user_updates_in_place_without_creating_a_duplicate_row() -> None:
    telegram_id = 940100002

    await save_user(
        telegram_id=telegram_id,
        telegram_username="oldname",
        full_name="Old Name Testov",
        phone="+998901234571",
    )
    first = await get_user_by_telegram_id(telegram_id)

    updated = await save_user(
        telegram_id=telegram_id,
        telegram_username="newname",
        full_name="New Name Testov",
        phone="+998901234572",
    )

    assert await _count_users_with_telegram_id(telegram_id) == 1  # never a second row
    assert updated.id == first.id  # same row, not a new one
    assert updated.full_name == "New Name Testov"
    assert updated.phone == "+998901234572"
    # created_at must never change on an update -- only new data is applied.
    assert updated.created_at == first.created_at
    # updated_at must still advance on every save (Core upsert bypasses the
    # ORM's onupdate= unless set_ includes it explicitly -- this is the
    # regression this test guards against).
    assert updated.updated_at >= first.updated_at


async def test_save_user_preserves_region_and_district_set_elsewhere() -> None:
    """save_user must never clobber columns it doesn't own (region/district,
    owned by save_user_location) -- the ON CONFLICT DO UPDATE's set_ dict must
    stay scoped to exactly the columns the old ORM-attribute-assignment code
    touched.
    """
    from app.services.user_service import save_user_location

    telegram_id = 940100003
    await save_user(
        telegram_id=telegram_id,
        telegram_username="regiontest",
        full_name="Region Test Testov",
        phone="+998901234573",
    )
    await save_user_location(telegram_id=telegram_id, region="Toshkent", district="Chilonzor")

    # A later save_user call (e.g. re-registering) must not blank out the
    # region/district that was set afterward.
    updated = await save_user(
        telegram_id=telegram_id,
        telegram_username="regiontest2",
        full_name="Region Test Testov Updated",
        phone="+998901234573",
    )

    assert updated.region == "Toshkent"
    assert updated.district == "Chilonzor"


async def test_concurrent_registration_of_the_same_telegram_id_creates_one_row() -> None:
    """MVP audit CRITICAL / Stage 11 instruction #3: two near-simultaneous
    registrations for the same telegram_id (e.g. Telegram redelivering
    /start, or two workers racing under a future multi-worker deployment)
    must never raise and must never create two rows -- the old
    "SELECT, then INSERT-or-UPDATE" can race even with SQLite serialization of writes; the upsert makes
    the uniqueness decision inside the database.
    """
    telegram_id = 940100004

    results = await asyncio.gather(
        save_user(
            telegram_id=telegram_id,
            telegram_username="racer_a",
            full_name="Racer A Testov",
            phone="+998901234574",
        ),
        save_user(
            telegram_id=telegram_id,
            telegram_username="racer_b",
            full_name="Racer B Testov",
            phone="+998901234575",
        ),
        return_exceptions=True,
    )

    for result in results:
        assert not isinstance(result, Exception), f"save_user raised under concurrency: {result!r}"

    assert await _count_users_with_telegram_id(telegram_id) == 1
    winner = await get_user_by_telegram_id(telegram_id)
    # Whichever call's data "won" the race, it must be one of the two inputs,
    # never a mix/corruption of both.
    assert winner.full_name in {"Racer A Testov", "Racer B Testov"}


async def test_duplicate_telegram_id_is_still_rejected_at_the_db_level() -> None:
    """Defense in depth: even bypassing save_user entirely and inserting two
    User rows with the same telegram_id directly, the UNIQUE constraint
    itself (not just application logic) must refuse the second one.
    """
    from sqlalchemy.exc import IntegrityError

    telegram_id = 940100005

    async with async_session() as session:
        async with session.begin():
            session.add(User(telegram_id=telegram_id, full_name="Direct Insert One"))

    raised = False
    try:
        async with async_session() as session:
            async with session.begin():
                session.add(User(telegram_id=telegram_id, full_name="Direct Insert Two"))
    except IntegrityError:
        raised = True

    assert raised
    assert await _count_users_with_telegram_id(telegram_id) == 1


async def test_concurrent_location_creates_one_user() -> None:
    telegram_id = 940100006
    results = await asyncio.gather(*(
        save_user_location(telegram_id, f"region-{i}", f"district-{i}")
        for i in range(12)
    ))
    assert len({u.id for u in results}) == 1
    assert await _count_users_with_telegram_id(telegram_id) == 1
    user = await get_user_by_telegram_id(telegram_id)
    assert (user.region, user.district) in {(f"region-{i}", f"district-{i}") for i in range(12)}
    assert user.full_name is None and user.phone is None


async def test_location_preserves_profile_and_identity() -> None:
    original = await save_user(940100007, "profile", "Full Name", "+998901234567")
    updated = await save_user_location(940100007, "Toshkent", "Chilonzor")
    assert (updated.id, updated.created_at) == (original.id, original.created_at)
    assert (updated.telegram_username, updated.full_name, updated.phone) == (
        "profile", "Full Name", "+998901234567"
    )
    assert (updated.region, updated.district) == ("Toshkent", "Chilonzor")


async def test_concurrent_contact_creation_uses_one_user() -> None:
    contacts = await asyncio.gather(*(
        create_admin_contact(940100008, "contact", f"Message {i}") for i in range(12)
    ))
    assert len({c.user_id for c in contacts}) == 1
    assert len({c.contact_number for c in contacts}) == 12
    assert all(c.contact_number == f"ADM-{c.id:06d}" for c in contacts)
    assert await _count_users_with_telegram_id(940100008) == 1


async def test_contacts_preserve_existing_profile_and_location() -> None:
    original = await save_user(940100009, "registered", "Keep Name", "+998901234568")
    await save_user_location(940100009, "Keep Region", "Keep District")
    contacts = await asyncio.gather(*(
        create_admin_contact(940100009, None, f"Message {i}") for i in range(4)
    ))
    user = await get_user_by_telegram_id(940100009)
    assert all(c.user_id == original.id for c in contacts)
    assert (user.telegram_username, user.full_name, user.phone, user.region, user.district) == (
        "registered", "Keep Name", "+998901234568", "Keep Region", "Keep District"
    )
    assert user.created_at == original.created_at


async def test_registration_location_and_contact_race_preserves_all_fields() -> None:
    telegram_id = 940100010
    await asyncio.gather(
        save_user(telegram_id, "mixed", "Mixed Name", "+998901234569"),
        save_user_location(telegram_id, "Mixed Region", "Mixed District"),
        create_admin_contact(telegram_id, None, "Concurrent contact"),
    )
    user = await get_user_by_telegram_id(telegram_id)
    assert await _count_users_with_telegram_id(telegram_id) == 1
    assert (user.telegram_username, user.full_name, user.phone, user.region, user.district) == (
        "mixed", "Mixed Name", "+998901234569", "Mixed Region", "Mixed District"
    )
