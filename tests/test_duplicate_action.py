"""End-to-end idempotency test for appeal creation (MVP audit instruction #4).

Simulates Telegram redelivering the exact same update (same chat_id +
message_id) to app.handlers.start.process_appeal_text and asserts the appeal
is only created once, using the real (isolated, see tests/conftest.py) test
database.
"""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import func, select

from app.database import async_session
from app.handlers.start import process_appeal_text
from app.models import Appeal
from app.services.user_service import save_user


class FakeBot:
    async def send_message(self, chat_id, text, **kwargs):
        return None


class FakeState:
    def __init__(self) -> None:
        self.clear_calls = 0
        self.data: dict = {}

    async def get_data(self) -> dict:
        return dict(self.data)

    async def clear(self) -> None:
        self.clear_calls += 1
        self.data.clear()


def _make_message(telegram_id: int, message_id: int, text: str):
    sent: list[str] = []

    async def answer(reply_text, **kwargs):
        sent.append(reply_text)

    message = SimpleNamespace(
        text=text,
        message_id=message_id,
        chat=SimpleNamespace(id=telegram_id),
        from_user=SimpleNamespace(id=telegram_id, username="dupuser"),
        bot=FakeBot(),
        answer=answer,
    )
    message._sent = sent  # test-only introspection hook
    return message


async def _count_appeals_with_text(appeal_text: str) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count()).select_from(Appeal).where(Appeal.appeal_text == appeal_text)
        )
        return result.scalar_one()


async def test_duplicate_message_delivery_creates_appeal_only_once() -> None:
    telegram_id = 930100001
    await save_user(
        telegram_id=telegram_id,
        telegram_username="dupuser",
        full_name="Dup User Testov",
        phone="+998901234568",
    )

    unique_text = "Duplicate-delivery test appeal text, long enough to pass validation."
    message_id = 555001

    before = await _count_appeals_with_text(unique_text)

    message1 = _make_message(telegram_id, message_id, unique_text)
    await process_appeal_text(message1, FakeState())

    # Simulates Telegram redelivering the exact same update (same message_id,
    # same chat) -- e.g. because the bot was slow to ack the first delivery.
    message2 = _make_message(telegram_id, message_id, unique_text)
    await process_appeal_text(message2, FakeState())

    after = await _count_appeals_with_text(unique_text)

    assert after - before == 1  # not 2 -- the duplicate never hit create_appeal
    assert message1._sent  # the first (genuine) delivery got its normal response
    assert not message2._sent  # the duplicate was silently ignored, no second response


async def test_two_distinct_messages_from_the_same_user_both_create_appeals() -> None:
    """Sanity check: the idempotency guard must never block genuinely new submissions."""
    telegram_id = 930100002
    await save_user(
        telegram_id=telegram_id,
        telegram_username="realuser",
        full_name="Real User Testov",
        phone="+998901234569",
    )

    text_a = "First distinct appeal text, long enough to pass validation checks."
    text_b = "Second distinct appeal text, long enough to pass validation checks."

    message_a = _make_message(telegram_id, 555100, text_a)
    await process_appeal_text(message_a, FakeState())

    message_b = _make_message(telegram_id, 555101, text_b)
    await process_appeal_text(message_b, FakeState())

    assert await _count_appeals_with_text(text_a) == 1
    assert await _count_appeals_with_text(text_b) == 1
    assert message_a._sent
    assert message_b._sent
