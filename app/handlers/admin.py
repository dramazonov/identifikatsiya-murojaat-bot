from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import ADMIN_IDS
from app.keyboards import APPEAL_REPLY_CALLBACK_PREFIX, admin_reply_keyboard
from app.models import Appeal, Suggestion, User
from app.services.appeal_service import complete_appeal, get_appeal_by_id, set_appeal_in_progress
from app.services.datetime_utils import format_tashkent
from app.services.user_service import get_user_by_id
from app.states import AdminStates

logger = logging.getLogger(__name__)

router = Router()

MIN_REPLY_LENGTH = 2
MAX_REPLY_LENGTH = 4000

NOT_ADMIN_TEXT = "Сизда ушбу амални бажариш ҳуқуқи мавжуд эмас."
APPEAL_NOT_FOUND_TEXT = "Мурожаат топилмади."
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
    """
    if not ADMIN_IDS:
        return

    text = _build_notification_text(appeal, user)
    keyboard = admin_reply_keyboard(appeal.id)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=keyboard)
        except Exception:
            logger.exception("Failed to notify admin %s about appeal %s", admin_id, appeal.appeal_number)


async def notify_admins_new_suggestion(bot: Bot, suggestion: Suggestion, user: User) -> None:
    """Send a new-suggestion notification to every admin.

    Mirrors ``notify_admins_new_appeal``'s best-effort semantics: a failure
    sending to one admin is logged and does not stop the rest from being
    notified. No "Жавоб бериш" button is attached -- admin replies to
    suggestions are not implemented yet. If ADMIN_IDS is empty this is a no-op.
    """
    if not ADMIN_IDS:
        return

    text = _build_suggestion_notification_text(suggestion, user)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
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

    appeal = await get_appeal_by_id(appeal_id)
    if appeal is None:
        await callback.answer(APPEAL_NOT_FOUND_TEXT, show_alert=True)
        return

    try:
        await set_appeal_in_progress(appeal_id, callback.from_user.id)
    except Exception:
        logger.exception("Failed to mark appeal %s as IN_PROGRESS", appeal_id)
        await callback.answer(GENERIC_ADMIN_ERROR_TEXT, show_alert=True)
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
    # reply that the database claims was already sent.
    try:
        await message.bot.send_message(user.telegram_id, citizen_text)
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
        try:
            await message.bot.edit_message_text(
                chat_id=notify_chat_id,
                message_id=notify_message_id,
                text=_build_notification_text(completed_appeal, user, admin_answer=admin_answer),
            )
        except Exception:
            # Purely cosmetic (the reply was already sent and saved) -- never
            # let this break the main flow.
            logger.exception("Failed to update admin notification message for appeal %s", appeal_id)


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


def _build_notification_text(appeal: Appeal, user: User, *, admin_answer: str | None = None) -> str:
    completed = admin_answer is not None
    header = "🟢 <b>Мурожаат кўриб чиқилди</b>" if completed else "🔔 <b>Янги мурожаат</b>"
    status_emoji = "🟢" if completed else "🟡"
    status_label = "COMPLETED" if completed else "NEW"

    lines = [
        header,
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
        "",
    ]

    if completed:
        lines += ["💬 <b>Админ жавоби:</b>", html.escape(admin_answer), ""]

    lines += [
        f"🕐 <b>Юборилган вақт:</b> {format_tashkent(appeal.created_at)}",
        "",
        f"{status_emoji} <b>Ҳолат:</b> {status_label}",
    ]

    return "\n".join(lines)


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
