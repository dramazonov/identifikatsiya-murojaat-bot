from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services import daily_appeal_reminder as reminder
from app.services.datetime_utils import TASHKENT_TZ


def test_next_reminder_is_same_day_before_10():
    now = datetime(2026, 9, 14, 9, 30, tzinfo=TASHKENT_TZ)
    assert reminder.seconds_until_next_reminder(now) == 30 * 60


def test_next_reminder_is_next_day_at_or_after_10():
    now = datetime(2026, 9, 14, 10, 0, tzinfo=TASHKENT_TZ)
    assert reminder.seconds_until_next_reminder(now) == 24 * 60 * 60


@pytest.mark.asyncio
async def test_daily_reminder_sends_to_all_admins_once(monkeypatch):
    now = datetime(2026, 9, 14, 10, 0, tzinfo=TASHKENT_TZ)
    appeals = [
        SimpleNamespace(
            appeal_number="MUR-000001",
            created_at=datetime(2026, 9, 12, 5, 0),
        )
    ]
    summary = SimpleNamespace(total=3, new=2, in_progress=1, appeals=appeals)

    monkeypatch.setattr(reminder, "get_unanswered_appeal_summary", AsyncMock(return_value=summary))
    monkeypatch.setattr(reminder, "all_admin_ids", AsyncMock(return_value=[11, 22]))
    send = AsyncMock()
    monkeypatch.setattr(reminder, "safe_send_message", send)
    acquire = AsyncMock(return_value="lease")
    finish = AsyncMock(return_value=True)
    monkeypatch.setattr(reminder.shared_state, "acquire_submission", acquire)
    monkeypatch.setattr(reminder.shared_state, "finish_submission", finish)

    result = await reminder.send_daily_unanswered_appeal_reminder(object(), now=now)

    assert result.sent_to == 2
    assert result.failed_for == 0
    assert result.unanswered == 3
    assert send.await_count == 2
    assert {call.args[1] for call in send.await_args_list} == {11, 22}
    text = send.await_args_list[0].args[2]
    assert "3 та" in text
    assert "MUR-000001" in text
    acquire.assert_awaited_once_with("daily_unanswered_appeal_reminder:2026-09-14")
    finish.assert_awaited_once_with(
        "daily_unanswered_appeal_reminder:2026-09-14", "lease", failed=False
    )


@pytest.mark.asyncio
async def test_daily_reminder_skips_duplicate_day(monkeypatch):
    monkeypatch.setattr(
        reminder.shared_state,
        "acquire_submission",
        AsyncMock(return_value=None),
    )
    summary = AsyncMock()
    monkeypatch.setattr(reminder, "get_unanswered_appeal_summary", summary)

    result = await reminder.send_daily_unanswered_appeal_reminder(
        object(), now=datetime(2026, 9, 14, 10, 0, tzinfo=TASHKENT_TZ)
    )

    assert result.skipped is True
    summary.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_unanswered_means_no_admin_message(monkeypatch):
    summary = SimpleNamespace(total=0, new=0, in_progress=0, appeals=[])
    monkeypatch.setattr(reminder, "get_unanswered_appeal_summary", AsyncMock(return_value=summary))
    monkeypatch.setattr(reminder, "all_admin_ids", AsyncMock(return_value=[11]))
    send = AsyncMock()
    monkeypatch.setattr(reminder, "safe_send_message", send)
    monkeypatch.setattr(reminder.shared_state, "acquire_submission", AsyncMock(return_value="lease"))
    finish = AsyncMock(return_value=True)
    monkeypatch.setattr(reminder.shared_state, "finish_submission", finish)

    result = await reminder.send_daily_unanswered_appeal_reminder(
        object(), now=datetime(2026, 9, 14, 10, 0, tzinfo=TASHKENT_TZ)
    )

    assert result.unanswered == 0
    send.assert_not_awaited()
    finish.assert_awaited_once()
