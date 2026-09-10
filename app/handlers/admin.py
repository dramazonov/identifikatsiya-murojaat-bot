from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import ADMIN_IDS
from app.keyboards import APPEAL_REPLY_CALLBACK_PREFIX, admin_reply_keyboard
from app.models import Appeal, Suggestion, User
from app.services.appeal_service import claim_appeal, complete_appeal, get_appeal_by_id
from app.services.datetime_utils import format_tashkent
from app.services.telegram_delivery import (
    TELEGRAM_MESSAGE_LIMIT,
    safe_edit_message_text,
    send_long_message,
)
from app.services.user_service import get_user_by_id
from app.states import AdminStates

logger = logging.getLogger(__name__)

router = Router()

MIN_REPLY_LENGTH = 2
MAX_REPLY_LENGTH = 4000

NOT_ADMIN_TEXT = "Сизда ушбу амални бажариш ҳуқуқи мавжуд эмас."
APPEAL_NOT_FOUND_TEXT = "Мурожаат топилмади."
ALREADY_CLAIMED_TEXT = (
    "Бу мурожаат аллақачон бошқа админ томонидан қабул қилинган."
)
GENERIC_ADMIN_ERROR_TEXT = "Хатолик юз берди. Илтимос, бироздан сўнг қайта уриниб кўринг."
STATE_LOST_TEXT = "Хатолик юз берди. Илтимос, мурожаат остидаги тугмани қайта босинг."
ASK_REPLY_TEXT = "Мурожаатга жавоб матнини ёзинг:"
INVALID_REPLY_TEXT = (
    "Жавоб матни нотўғри. Илтимос, камида 2, кўпи билан 4000 та белгидан иборат матн киритинг."
)
SEND_FAILED_TEXT = (
    "Фуқарога хабар юборишда хатолик юз берди. Жавоб сақланмади. "
    "Илтимос, бироздан сўнг қайта уриниб кўринг."
)
SAVE_FAILED_TEXT = (
    "Жавоб фуқарога юборилди, лекин уни базага сақлашда хатолик юз берди. "
    "Илтимос, техник хизматга мурожаат қилинг."
)
REPLY_SUCCESS_TEXT = "Жавобингиз фуқарога муваффақиятли юборилди ва сақланди."

CITIZEN_ANSWER_TEMPLATE = (
    "📩 <b>Мурожаатингиз бўйича жавоб</b>\n\n"
    "🆔 <b>Мурожаат рақами:</b> {appeal_number}\n\n"
    "📝 <b>Жавоб:</b>\n\n"
    "{admin_answer}\n\n"
    "Мурожаатингиз кўриб чиқилди. Раҳмат!"
)


async def notify_admins_new_appeal(bot: Bot, appeal: Appeal, user: User) -> None:
    """Send a new-appeal notification (with a "Жавоб бериш" button) to every admin.

    A failure sending to one admin is logged and does not stop the rest from
    being notified. If ADMIN_IDS is empty this is a no-op (startup already logs
    a warning about that -- see app/main.py).

    MVP audit CRITICAL #1: appeal_text can be up to 4000 characters, and with
    the header/footer added this can exceed Telegram's 4096-char message
    limit -- previously that made the whole send silently fail (caught by the
    try/except below and only logged), so the admin never saw the appeal at
    all. Now: if the combined text fits in one message, it's sent exactly as
    before (single message, button attached, unchanged behavior for the
    common case). If it doesn't fit, the body is sent first (as one or more
    messages, split on line boundaries -- see send_long_message), followed by
    a short footer message that always fits and carries the reply button, so
    the button is never lost and is always attached to a message that stays
    editable within the limit later (see process_admin_reply_text).
    """
    if not ADMIN_IDS:
        return

    body_text = _build_appeal_body_text(appeal, user)
    footer_text = _build_appeal_footer_text(appeal, completed=False)
    full_text = f"{body_text}\n\n{footer_text}"
    keyboard = admin_reply_keyboard(appeal.id)

    for admin_id in ADMIN_IDS:
        try:
            if len(full_text) <= TELEGRAM_MESSAGE_LIMIT:
                await send_long_message(bot, admin_id, full_text, reply_markup=keyboard)
            else:
                await send_long_message(bot, admin_id, body_text)
                await send_long_message(bot, admin_id, footer_text, reply_markup=keyboard)
        except Exception:
            logger.exception("Failed to notify admin %s about appeal %s", admin_id, appeal.appeal_number)


async def notify_admins_new_suggestion(bot: Bot, suggestion: Suggestion, user: User) -> None:
    """Send a new-suggestion notification to every admin.

    Mirrors ``notify_admins_new_appeal``'s best-effort semantics: a failure
    sending to one admin is logged and does not stop the rest from being
    notified. No "Жавоб бериш" button is attached -- admin replies to
    suggestions are not implemented yet. If ADMIN_IDS is empty this is a no-op.

    MVP audit CRITICAL #1: no button is involved here, so a text that exceeds
    Telegram's 4096-char limit is simply delivered as multiple messages via
    send_long_message instead of silently failing to send at all.
    """
    if not ADMIN_IDS:
        return

    text = _build_suggestion_notification_text(suggestion, user)

    for admin_id in ADMIN_IDS:
        try:
            await send_long_message(bot, admin_id, text)
        except Exception:
            logger.exception(
                "Failed to notify admin %s about suggestion %s", admin_id, suggestion.suggestion_number
            )


@router.callback_query(F.data.startswith(f"{APPEAL_REPLY_CALLBACK_PREFIX}:"))
async def process_appeal_reply_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return

    appeal_id = _parse_appeal_id(callback.data)
    if appeal_id is None:
        await callback.answer(APPEAL_NOT_FOUND_TEXT, show_alert=True)
        return

    # Atomic first-claim-wins update (MVP audit CRITICAL #2 / instruction #5):
    # only the request that actually flips the appeal from NEW to IN_PROGRESS
    # "wins". If it's already claimed by THIS SAME admin (a redelivered
    # Telegram callback_query for the same click -- instruction #4's
    # idempotency requirement), treat it as a safe no-op and proceed exactly
    # as if this were the winning claim. If it's claimed by a DIFFERENT admin,
    # refuse with a clear message instead of silently overwriting them.
    try:
        appeal, claimed = await claim_appeal(appeal_id, callback.from_user.id)
    except Exception:
        logger.exception("Failed to claim appeal %s", appeal_id)
        await callback.answer(GENERIC_ADMIN_ERROR_TEXT, show_alert=True)
        return

    if appeal is None:
        await callback.answer(APPEAL_NOT_FOUND_TEXT, show_alert=True)
        return

    if not claimed and appeal.admin_id != callback.from_user.id:
        await callback.answer(ALREADY_CLAIMED_TEXT, show_alert=True)
        if callback.message is not None:
            try:
                # Best-effort: drop the now-stale button on this admin's own
                # copy so they can't try to claim it again. Purely cosmetic --
                # the claim guard above is what actually prevents double-claim.
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                logger.exception("Failed to clear stale reply button for appeal %s", appeal_id)
        return

    await state.set_state(AdminStates.waiting_for_reply)
    await state.update_data(
        appeal_id=appeal_id,
        notify_chat_id=callback.message.chat.id if callback.message else None,
        notify_message_id=callback.message.message_id if callback.message else None,
    )

    if callback.message is not None:
        await callback.message.answer(ASK_REPLY_TEXT)
    await callback.answer()


@router.message(AdminStates.waiting_for_reply, F.text)
async def process_admin_reply_text(message: Message, state: FSMContext) -> None:
    if message.from_user.id not in ADMIN_IDS:
        # Shouldn't normally happen (only admins are ever put into this state),
        # but never let a non-admin act on it.
        await state.clear()
        await message.answer(NOT_ADMIN_TEXT)
        return

    admin_answer = message.text.strip()
    if not (MIN_REPLY_LENGTH <= len(admin_answer) <= MAX_REPLY_LENGTH):
        await message.answer(INVALID_REPLY_TEXT)
        return

    data = await state.get_data()
    appeal_id = data.get("appeal_id")
    notify_chat_id = data.get("notify_chat_id")
    notify_message_id = data.get("notify_message_id")

    if appeal_id is None:
        await state.clear()
        await message.answer(STATE_LOST_TEXT)
        return

    appeal = await get_appeal_by_id(appeal_id)
    if appeal is None:
        await state.clear()
        await message.answer(APPEAL_NOT_FOUND_TEXT)
        return

    user = await get_user_by_id(appeal.user_id)
    if user is None:
        await state.clear()
        await message.answer(APPEAL_NOT_FOUND_TEXT)
        return

    citizen_text = CITIZEN_ANSWER_TEMPLATE.format(
        appeal_number=html.escape(appeal.appeal_number),
        admin_answer=html.escape(admin_answer),
    )

    # Deliver to the citizen FIRST. Only persist admin_answer/COMPLETED once
    # delivery actually succeeded -- otherwise the citizen would never see a
    # reply that the database claims was already sent. citizen_text can
    # exceed 4096 chars when admin_answer is near its 4000-char max (MVP audit
    # CRITICAL #1), so this goes through send_long_message instead of a plain
    # send_message.
    try:
        await send_long_message(message.bot, user.telegram_id, citizen_text)
    except Exception:
        logger.exception(
            "Failed to deliver admin reply to user %s for appeal %s", user.telegram_id, appeal_id
        )
        await message.answer(SEND_FAILED_TEXT)
        # Keep AdminStates.waiting_for_reply / the stored appeal_id so the admin
        # can just retry without re-clicking the notification button.
        return

    try:
        completed_appeal = await complete_appeal(appeal_id, message.from_user.id, admin_answer)
    except Exception:
        logger.exception("Failed to save admin answer for appeal %s", appeal_id)
        await message.answer(SAVE_FAILED_TEXT)
        await state.clear()
        return

    await state.clear()
    await message.answer(REPLY_SUCCESS_TEXT)

    if completed_appeal is not None and notify_chat_id is not None and notify_message_id is not None:
        # Update the admin's own notification to reflect COMPLETED status
        # (and drop the now-answered button, by omitting reply_markup on the
        # edit). The admin's answer itself is always sent as its own separate
        # message below rather than folded into this edit -- that keeps the
        # edit itself within the 4096-char limit regardless of how long the
        # answer is (MVP audit CRITICAL #1), instead of the previous
        # behavior of embedding it directly, which could silently fail to
        # apply for a long appeal_text + long admin_answer combination.
        body_text = _build_appeal_body_text(completed_appeal, user)
        completed_footer = _build_appeal_footer_text(completed_appeal, completed=True)
        combined = f"{body_text}\n\n{completed_footer}"
        edit_text = combined if len(combined) <= TELEGRAM_MESSAGE_LIMIT else completed_footer

        try:
            await safe_edit_message_text(
                message.bot, chat_id=notify_chat_id, message_id=notify_message_id, text=edit_text
            )
        except Exception:
            # Purely cosmetic (the reply was already sent and saved) -- never
            # let this break the main flow.
            logger.exception("Failed to update admin notification message for appeal %s", appeal_id)

        try:
            await send_long_message(
                message.bot, notify_chat_id, _build_answer_followup_text(completed_appeal, admin_answer)
            )
        except Exception:
            logger.exception("Failed to send answer follow-up message for appeal %s", appeal_id)


@router.message(AdminStates.waiting_for_reply)
async def process_admin_reply_invalid(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(INVALID_REPLY_TEXT)


def _parse_appeal_id(callback_data: str | None) -> int | None:
    if not callback_data or ":" not in callback_data:
        return None
    try:
        return int(callback_data.split(":", 1)[1])
    except ValueError:
        return None


def _build_appeal_body_text(appeal: Appeal, user: User) -> str:
    """Everything about the appeal except the timestamp/status footer.

    Split out from the old single ``_build_notification_text`` so it can be
    sent on its own (see ``notify_admins_new_appeal``) when the combined
    message would exceed Telegram's 4096-char limit. This part never changes
    once the appeal is created, so it's reused as-is for the completion edit.
    """
    lines = [
        "🔔 <b>Янги мурожаат</b>",
        "",
        f"🆔 <b>Рақам:</b> {html.escape(appeal.appeal_number)}",
        "",
        f"👤 <b>Ф.И.Ш.:</b> {html.escape(user.full_name or '-')}",
        "",
        f"📱 <b>Телефон:</b> {html.escape(user.phone or '-')}",
        "",
        f"📍 <b>Вилоят:</b> {html.escape(user.region or '-')}",
        "",
        f"🏙 <b>Туман/шаҳар:</b> {html.escape(user.district or '-')}",
        "",
        "📝 <b>Мурожаат:</b>",
        html.escape(appeal.appeal_text),
    ]
    return "\n".join(lines)


def _build_appeal_footer_text(appeal: Appeal, *, completed: bool) -> str:
    """The short timestamp/status line -- always well within the 4096 limit.

    Sent as its own final message (carrying the reply button) whenever the
    body doesn't fit alongside it; always used as-is for the completion edit,
    since it never grows with the appeal/answer text.
    """
    status_emoji = "🟢" if completed else "🟡"
    status_label = "COMPLETED" if completed else "NEW"
    lines = [
        f"🕐 <b>Юборилган вақт:</b> {format_tashkent(appeal.created_at)}",
        "",
        f"{status_emoji} <b>Ҳолат:</b> {status_label}",
    ]
    return "\n".join(lines)


def _build_answer_followup_text(appeal: Appeal, admin_answer: str) -> str:
    """The admin's own answer, shown back to them as a separate confirmation message."""
    return (
        f"💬 <b>Жавоб юборилди</b> (Мурожаат {html.escape(appeal.appeal_number)}):\n\n"
        f"{html.escape(admin_answer)}"
    )


def _build_suggestion_notification_text(suggestion: Suggestion, user: User) -> str:
    lines = [
        "💡 <b>ЯНГИ ТАКЛИФ</b>",
        "",
        f"🆔 <b>Рақам:</b> {html.escape(suggestion.suggestion_number)}",
        "",
        f"👤 <b>Ф.И.Ш.:</b> {html.escape(user.full_name or '-')}",
        "",
        f"📞 <b>Телефон:</b> {html.escape(user.phone or '-')}",
        "",
        f"📍 <b>Вилоят:</b> {html.escape(user.region or '-')}",
        "",
        f"🏘 <b>Туман/шаҳар:</b> {html.escape(user.district or '-')}",
        "",
        "📝 <b>Таклиф:</b>",
        html.escape(suggestion.suggestion_text),
        "",
        f"🕐 <b>Юборилган вақт:</b> {format_tashkent(suggestion.created_at)}",
    ]

    return "\n".join(lines)
