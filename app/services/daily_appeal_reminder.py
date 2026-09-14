from __future__ import annotations

import asyncio
import html
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards import ADMIN_PANEL_CALLBACK_PREFIX
from app.services import shared_state
from app.services.admin_service import all_admin_ids
from app.services.appeal_service import get_unanswered_appeal_summary
from app.services.datetime_utils import TASHKENT_TZ, to_tashkent
from app.services.telegram_delivery import safe_send_message

logger = logging.getLogger(__name__)

REMINDER_HOUR = 10
REMINDER_MINUTE = 0
REMINDER_LIST_LIMIT = 10


@dataclass(frozen=True)
class ReminderRunResult:
    sent_to: int
    failed_for: int
    unanswered: int
    skipped: bool = False


def seconds_until_next_reminder(now: datetime | None = None) -> float:
    """Seconds until the next 10:00 Asia/Tashkent reminder slot."""
    local_now = now or datetime.now(TASHKENT_TZ)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=TASHKENT_TZ)
    else:
        local_now = local_now.astimezone(TASHKENT_TZ)

    target = local_now.replace(
        hour=REMINDER_HOUR,
        minute=REMINDER_MINUTE,
        second=0,
        microsecond=0,
    )
    if local_now >= target:
        target += timedelta(days=1)
    return max(0.0, (target - local_now).total_seconds())


def _age_label(created_at: datetime, *, now: datetime | None = None) -> str:
    local_now = now or datetime.now(TASHKENT_TZ)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=TASHKENT_TZ)
    else:
        local_now = local_now.astimezone(TASHKENT_TZ)
    created_local = to_tashkent(created_at)
    days = max(0, (local_now.date() - created_local.date()).days)
    if days == 0:
        return "бугун"
    return f"{days} кундан бери"


def _build_reminder_text(summary, *, now: datetime | None = None) -> str:
    lines = [
        "⚠️ <b>Жавоб берилмаган мурожаатлар</b>",
        "",
        f"⏰ Соат 10:00 ҳолатига <b>{summary.total} та</b> мурожаатга ҳали жавоб берилмаган.",
        "",
        f"🆕 Янги: <b>{summary.new}</b>",
        f"🟡 Кўриб чиқилмоқда: <b>{summary.in_progress}</b>",
    ]

    if summary.appeals:
        lines.extend(["", "📌 <b>Энг аввалги мурожаатлар:</b>"])
        for appeal in summary.appeals:
            lines.append(
                f"• {html.escape(appeal.appeal_number)} — {_age_label(appeal.created_at, now=now)}"
            )
        remaining = summary.total - len(summary.appeals)
        if remaining > 0:
            lines.append(f"• … ва яна {remaining} та")

    lines.extend(["", "Илтимос, жавоб берилмаган мурожаатларни кўриб чиқинг."])
    return "\n".join(lines)


def _reminder_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📨 Жавобсиз мурожаатларни кўриш",
                callback_data=f"{ADMIN_PANEL_CALLBACK_PREFIX}:unanswered",
            )
        ]]
    )


async def send_daily_unanswered_appeal_reminder(
    bot: Bot,
    *,
    now: datetime | None = None,
) -> ReminderRunResult:
    """Send one idempotent daily reminder to every current admin/superadmin.

    The idempotency key is based on the Asia/Tashkent calendar date. It is
    stored in the same Redis-backed submission lease mechanism used elsewhere
    in production, so accidental duplicate scheduler tasks/restarts cannot
    send the same day's reminder twice. In local development the existing
    in-memory fallback is used.
    """
    local_now = now or datetime.now(TASHKENT_TZ)
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=TASHKENT_TZ)
    else:
        local_now = local_now.astimezone(TASHKENT_TZ)

    day_key = local_now.date().isoformat()
    lease_key = f"daily_unanswered_appeal_reminder:{day_key}"
    token = await shared_state.acquire_submission(lease_key)
    if token is None:
        return ReminderRunResult(sent_to=0, failed_for=0, unanswered=0, skipped=True)

    succeeded = False
    try:
        summary = await get_unanswered_appeal_summary(limit=REMINDER_LIST_LIMIT)
        if summary.total == 0:
            succeeded = True
            return ReminderRunResult(sent_to=0, failed_for=0, unanswered=0)

        admin_ids = await all_admin_ids()
        if not admin_ids:
            # Keep this run retryable if administrators are temporarily
            # misconfigured instead of silently marking the day as complete.
            return ReminderRunResult(sent_to=0, failed_for=0, unanswered=summary.total)

        text = _build_reminder_text(summary, now=local_now)
        keyboard = _reminder_keyboard()
        sent = 0
        failed = 0
        for admin_id in admin_ids:
            try:
                await safe_send_message(bot, admin_id, text, reply_markup=keyboard)
                sent += 1
            except Exception:
                failed += 1
                logger.exception(
                    "Failed to send daily unanswered-appeal reminder to admin %s",
                    admin_id,
                )

        # A permanently unreachable former admin must not cause every active
        # admin to receive duplicate reminders. The current admin list can be
        # corrected independently; once this run attempted all recipients, it
        # counts as the day's reminder.
        succeeded = True
        return ReminderRunResult(
            sent_to=sent,
            failed_for=failed,
            unanswered=summary.total,
        )
    finally:
        await shared_state.finish_submission(lease_key, token, failed=not succeeded)


async def daily_unanswered_appeal_reminder_loop(bot: Bot) -> None:
    """Long-lived scheduler: fire every day at 10:00 Asia/Tashkent."""
    while True:
        try:
            delay = seconds_until_next_reminder()
            logger.info("Daily unanswered-appeal reminder scheduled in %.0f seconds", delay)
            await asyncio.sleep(delay)
            result = await send_daily_unanswered_appeal_reminder(bot)
            logger.info(
                "Daily unanswered-appeal reminder finished: unanswered=%s sent=%s failed=%s skipped=%s",
                result.unanswered,
                result.sent_to,
                result.failed_for,
                result.skipped,
            )
            # Avoid recalculating the exact same 10:00 boundary if the send
            # completed within the same clock tick.
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Daily unanswered-appeal reminder loop failed; retrying in 60 seconds")
            await asyncio.sleep(60)
