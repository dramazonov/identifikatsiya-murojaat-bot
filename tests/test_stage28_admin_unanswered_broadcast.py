from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.enums import ContentType

from app import keyboards
from app.handlers import admin as admin_handler
from app.services import broadcast_service
from app.services.broadcast_service import BroadcastResult
from app.states import AdminBroadcastStates


class FakeState:
    def __init__(self, data=None):
        self.data = dict(data or {})
        self.state = None

    async def clear(self):
        self.data = {}
        self.state = None

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return dict(self.data)

    async def set_state(self, state):
        self.state = state


class FakeMessage:
    def __init__(self, *, user_id=1, chat_id=1, message_id=10, content_type=ContentType.TEXT):
        self.from_user = SimpleNamespace(id=user_id)
        self.chat = SimpleNamespace(id=chat_id)
        self.message_id = message_id
        self.content_type = content_type
        self.answer = AsyncMock()
        self.bot = object()


class FakeCallback:
    def __init__(self, data, *, user_id=1):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = FakeMessage(user_id=user_id, chat_id=user_id)
        self.answer = AsyncMock()
        self.bot = object()


def _button_texts(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


def test_admin_panel_has_unanswered_count_and_superadmin_broadcast_button():
    regular = keyboards.admin_panel_keyboard(superadmin=False, unanswered_count=7)
    regular_texts = _button_texts(regular)
    assert "⚠️ Жавобсиз мурожаатлар (7)" in regular_texts
    assert "📢 Хабар юбориш" not in regular_texts

    superadmin = keyboards.admin_panel_keyboard(superadmin=True, unanswered_count=7)
    super_texts = _button_texts(superadmin)
    assert "⚠️ Жавобсиз мурожаатлар (7)" in super_texts
    assert "📢 Хабар юбориш" in super_texts


@pytest.mark.asyncio
async def test_superadmin_can_start_user_broadcast(monkeypatch):
    monkeypatch.setattr(admin_handler, "is_superadmin", AsyncMock(return_value=True))
    monkeypatch.setattr(admin_handler, "list_broadcast_user_ids", AsyncMock(return_value=[11, 22, 33]))

    callback = FakeCallback(f"{keyboards.ADMIN_BROADCAST_CALLBACK_PREFIX}:users")
    state = FakeState()

    await admin_handler.admin_broadcast_callback(callback, state)

    assert state.data["broadcast_audience"] == "users"
    assert state.state == AdminBroadcastStates.waiting_for_message
    assert "3 та" in callback.message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_broadcast_message_is_saved_for_confirmation(monkeypatch):
    monkeypatch.setattr(admin_handler, "is_superadmin", AsyncMock(return_value=True))
    monkeypatch.setattr(admin_handler, "list_broadcast_user_ids", AsyncMock(return_value=[11, 22]))

    state = FakeState({"broadcast_audience": "users"})
    message = FakeMessage(user_id=99, chat_id=99, message_id=444)

    await admin_handler.admin_broadcast_message_received(message, state)

    assert state.data["broadcast_source_chat_id"] == 99
    assert state.data["broadcast_source_message_id"] == 444
    assert state.state == AdminBroadcastStates.waiting_for_confirmation
    assert "2 та" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_confirm_broadcast_sends_and_clears_state(monkeypatch):
    monkeypatch.setattr(admin_handler, "is_superadmin", AsyncMock(return_value=True))
    monkeypatch.setattr(admin_handler, "list_broadcast_user_ids", AsyncMock(return_value=[11, 22]))
    monkeypatch.setattr(
        admin_handler,
        "broadcast_copied_message",
        AsyncMock(return_value=BroadcastResult(total=2, sent=2, failed=0, unreachable=0)),
    )
    monkeypatch.setattr(
        admin_handler,
        "get_unanswered_appeal_summary",
        AsyncMock(return_value=SimpleNamespace(total=4)),
    )

    callback = FakeCallback(f"{keyboards.ADMIN_BROADCAST_CALLBACK_PREFIX}:confirm", user_id=99)
    state = FakeState(
        {
            "broadcast_audience": "users",
            "broadcast_source_chat_id": 99,
            "broadcast_source_message_id": 444,
        }
    )

    await admin_handler.admin_broadcast_callback(callback, state)

    assert state.data == {}
    admin_handler.broadcast_copied_message.assert_awaited_once_with(
        callback.bot,
        [11, 22],
        from_chat_id=99,
        message_id=444,
        mark_unreachable_users=True,
    )
    assert "Юборилди: <b>2</b>" in callback.message.answer.await_args_list[-1].args[0]


@pytest.mark.asyncio
async def test_broadcast_service_deduplicates_recipients(monkeypatch):
    copy = AsyncMock()
    monkeypatch.setattr(broadcast_service, "_copy_with_retry", copy)
    monkeypatch.setattr(broadcast_service.asyncio, "sleep", AsyncMock())

    result = await broadcast_service.broadcast_copied_message(
        object(),
        [11, 11, 22],
        from_chat_id=99,
        message_id=100,
        mark_unreachable_users=False,
    )

    assert result == BroadcastResult(total=2, sent=2, failed=0, unreachable=0)
    assert [call.kwargs["chat_id"] for call in copy.await_args_list] == [11, 22]


@pytest.mark.asyncio
async def test_user_broadcast_marks_unreachable_recipient(monkeypatch):
    copy = AsyncMock(side_effect=RuntimeError("blocked"))
    mark = AsyncMock()
    monkeypatch.setattr(broadcast_service, "_copy_with_retry", copy)
    monkeypatch.setattr(broadcast_service, "classify_delivery_exception", lambda exc: ("RuntimeError", True))
    monkeypatch.setattr(broadcast_service, "mark_user_unreachable", mark)
    monkeypatch.setattr(broadcast_service.asyncio, "sleep", AsyncMock())

    result = await broadcast_service.broadcast_copied_message(
        object(),
        [11],
        from_chat_id=99,
        message_id=100,
        mark_unreachable_users=True,
    )

    assert result == BroadcastResult(total=1, sent=0, failed=1, unreachable=1)
    mark.assert_awaited_once_with(11)
