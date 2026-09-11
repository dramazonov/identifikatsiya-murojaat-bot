"""Observe actual INSERT placeholders and committed identifiers in all services."""

import asyncio
import re

import pytest
from sqlalchemy import event, func, select

from app.database import async_session
from app.models import AdminContact, Appeal, Suggestion, User
from app.services.admin_contact_service import create_admin_contact
from app.services.appeal_service import create_appeal
from app.services.suggestion_service import create_suggestion
from app.services.temporary_number import generate_temporary_number
from app.services.user_service import save_user


CASES = [
    (Appeal, "appeal_number", "MUR", create_appeal),
    (Suggestion, "suggestion_number", "TAK", create_suggestion),
    (AdminContact, "contact_number", "ADM", create_admin_contact),
]


async def create(service, telegram_id):
    if service is create_admin_contact:
        return await service(telegram_id, "test", "Test contact")
    return await service(telegram_id, "Test submission")


def test_temporary_number_length_and_alphabet():
    for _ in range(100):
        assert re.fullmatch(r"TMP-[A-Za-z0-9_-]{16}", generate_temporary_number())


@pytest.mark.parametrize("model,column,prefix,service", CASES)
async def test_insert_placeholder_fits_and_public_number_commits(model, column, prefix, service):
    telegram_id = 950100000 + CASES.index((model, column, prefix, service))
    await save_user(telegram_id, "test", "Test User", "+998901234567")
    seen = []

    def before_insert(mapper, connection, target):
        value = getattr(target, column)
        seen.append(value)
        assert re.fullmatch(r"TMP-[A-Za-z0-9_-]{16}", value)
        assert len(value) <= model.__table__.c[column].type.length

    event.listen(model, "before_insert", before_insert)
    try:
        row = await create(service, telegram_id)
    finally:
        event.remove(model, "before_insert", before_insert)
    assert len(seen) == 1
    expected = f"{prefix}-{row.id:06d}"
    assert getattr(row, column) == expected
    async with async_session() as session:
        assert getattr(await session.get(model, row.id), column) == expected


@pytest.mark.parametrize("model,column,prefix,service", CASES)
async def test_concurrent_submissions_have_distinct_public_numbers(model, column, prefix, service):
    telegram_id = 950200000 + CASES.index((model, column, prefix, service))
    await save_user(telegram_id, "test", "Test User", "+998901234567")
    rows = await asyncio.gather(*(create(service, telegram_id) for _ in range(8)))
    assert len({getattr(row, column) for row in rows}) == 8
    assert all(getattr(row, column) == f"{prefix}-{row.id:06d}" for row in rows)


@pytest.mark.parametrize("model,column,prefix,service", CASES)
async def test_failure_before_final_number_rolls_back_insert(model, column, prefix, service):
    telegram_id = 950300000 + CASES.index((model, column, prefix, service))
    if service is not create_admin_contact:
        await save_user(telegram_id, "test", "Test User", "+998901234567")
    async with async_session() as session:
        before = await session.scalar(select(func.count()).select_from(model))

    def fail_update(mapper, connection, target):
        raise RuntimeError("Injected failure before final number")

    event.listen(model, "before_update", fail_update)
    try:
        with pytest.raises(RuntimeError, match="Injected failure"):
            await create(service, telegram_id)
    finally:
        event.remove(model, "before_update", fail_update)
    async with async_session() as session:
        assert await session.scalar(select(func.count()).select_from(model)) == before
        if service is create_admin_contact:
            assert await session.scalar(select(User).where(User.telegram_id == telegram_id)) is None
