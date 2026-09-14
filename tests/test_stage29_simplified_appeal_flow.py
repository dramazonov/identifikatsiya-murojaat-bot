from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import app.handlers.appeal_flow as flow
from app.states import AppealSubmissionStates


class FakeState:
    def __init__(self, data: dict | None = None) -> None:
        self.data = dict(data or {})
        self.state = AppealSubmissionStates.waiting_for_text
        self.cleared = False

    async def get_data(self) -> dict:
        return dict(self.data)

    async def update_data(self, **kwargs) -> None:
        self.data.update(kwargs)

    async def set_state(self, state) -> None:
        self.state = state

    async def clear(self) -> None:
        self.data.clear()
        self.state = None
        self.cleared = True


class FakeMessage:
    def __init__(self, text: str = "This is a valid appeal text for the simplified flow.") -> None:
        self.text = text
        self.message_id = 501
        self.chat = SimpleNamespace(id=10001)
        self.from_user = SimpleNamespace(id=10001)
        self.bot = object()
        self.answers: list[tuple[str, dict]] = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


async def test_text_submission_creates_appeal_immediately_without_pdf_or_confirmation(monkeypatch):
    state = FakeState({"language_code": "uz_latn", "category_code": "DATABASE"})
    message = FakeMessage()
    appeal = SimpleNamespace(appeal_number="MUR-000777", user_id=123)

    create_appeal = AsyncMock(return_value=appeal)
    finish_submission = AsyncMock()
    notify = AsyncMock()

    monkeypatch.setattr(flow, "is_rate_limited", AsyncMock(return_value=False))
    monkeypatch.setattr(flow, "acquire_submission", AsyncMock(return_value="lease-token"))
    monkeypatch.setattr(flow, "finish_submission", finish_submission)
    monkeypatch.setattr(flow, "create_appeal", create_appeal)
    monkeypatch.setattr(flow, "get_user_by_id", AsyncMock(return_value=SimpleNamespace(id=123)))
    monkeypatch.setattr(flow, "notify_admins_new_appeal", notify)

    await flow.appeal_text_received(message, state)

    create_appeal.assert_awaited_once_with(
        telegram_id=10001,
        appeal_text=message.text,
        category_code="DATABASE",
        subject=None,
    )
    finish_submission.assert_awaited_once_with(
        "appeal_create:10001:501", "lease-token"
    )
    assert state.cleared is True
    assert any("MUR-000777" in text for text, _ in message.answers)
    assert all("PDF" not in text.upper() for text, _ in message.answers)
    notify.assert_awaited_once()


async def test_invalid_text_stays_in_text_step(monkeypatch):
    state = FakeState({"language_code": "uz_latn", "category_code": "DATABASE"})
    message = FakeMessage("x")
    create_appeal = AsyncMock()
    monkeypatch.setattr(flow, "create_appeal", create_appeal)

    await flow.appeal_text_received(message, state)

    create_appeal.assert_not_awaited()
    assert state.state == AppealSubmissionStates.waiting_for_text
    assert state.cleared is False
    assert message.answers


async def test_duplicate_delivery_is_silently_ignored(monkeypatch):
    state = FakeState({"language_code": "uz_latn", "category_code": "DATABASE"})
    message = FakeMessage()
    create_appeal = AsyncMock()

    monkeypatch.setattr(flow, "is_rate_limited", AsyncMock(return_value=False))
    monkeypatch.setattr(flow, "acquire_submission", AsyncMock(return_value=None))
    monkeypatch.setattr(flow, "create_appeal", create_appeal)

    await flow.appeal_text_received(message, state)

    create_appeal.assert_not_awaited()
    assert state.cleared is False
    assert message.answers == []
