from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import ADMIN_IDS
from app.keyboards import (
    ADMIN_CONTACT_REPLY_CALLBACK_PREFIX,
    MENU_ADMIN_CONTACT,
    admin_contact_reply_keyboard,
    main_menu_keyboard,
)
from app.models import AdminContact, User
from app.services.admin_contact_service import (
    complete_admin_contact,
    create_admin_contact,
    get_admin_contact_by_id,
    set_admin_contact_in_progress,
)
from app.services.datetime_utils import format_tashkent
from app.services.user_service import get_user_by_id
from app.services.validators import is_valid_admin_contact_message
from app.states import AdminContactReplyStates, AdminContactStates

logger = logging.getLogger(__name__)

router = Router()

MIN_REPLY_LENGTH = 2
MAX_REPLY_LENGTH = 4000

NOT_PROVIDED_TEXT = "Маълумот киритилмаган"

ASK_MESSAGE_TEXT = "💬 Админга юбориш учун хабарингизни ёзинг:"
INVALID_MESSAGE_TEXT = (
    "Хабар матни нотўғри. Илтимос, камида 2, кўпи билан 4000 та белгидан иборат матн киритинг."
)
CONTACT_SUCCESS_TEXT_TEMPLATE = (
    "✅ Хабарингиз қабул қилинди.\n\n"
    "Мурожаат рақами: {contact_number}\n\n"
    "Админлар томонидан кўриб чиқилади."
)
GENERIC_ERROR_TEXT = "Хатолик юз берди. Илтимос, бироздан сўнг қайта уриниб кўринг."

NOT_ADMIN_TEXT = "Сизда ушбу амални бажариш ҳуқуқи мавжуд эмас."
CONTACT_NOT_FOUND_TEXT = "Мурожаат топилмади."
STATE_LOST_TEXT = "Хатолик юз берди. Илтимос, мурожаат остидаги тугмани қайта босинг."
ASK_REPLY_TEXT = "Мурожаатга жавоб матнини ёзинг:"
INVALID_REPLY_TEXT = (
    "Жавоб матни нотўғри. Илтимос, камида 2, кўпи билан 4000 та белгидан иборат матн киритинг."
)
NO_RECIPIENT_TEXT = (
    "Ушбу мурожаат учун фойдаланувчи аниқланмади, жавоб юбориб бўлмайди."
)
SEND_FAILED_TEXT = (
    "Фойдаланувчига хабар юборишда хатолик юз берди. Жавоб сақланмади. "
    "Илтимос, бироздан сўнг қайта уриниб кўринг."
)
SAVE_FAILED_TEXT = (
    "Жавоб фойдаланувчига юборилди, лекин уни базага сақлашда хатолик юз берди. "
    "Илтимос, техник хизматга мурожаат қилинг."
)
REPLY_SUCCESS_TEXT = "Жавобингиз фойдаланувчига муваффақиятли юборилди ва сақланди."

USER_ANSWER_TEMPLATE = (
    "👨‍💼 <b>Админдан жавоб</b>\n\n"
    "📌 <b>Хабар рақами:</b> {contact_number}\n\n"
    "💬 <b>Жавоб:</b>\n\n"
    "{admin_answer}"
)


async def notify_admins_new_contact(bot: Bot, contact: AdminContact, user: User | None) -> None:
    """Send a new-admin-contact notification (with a "Жавоб бериш" button) to every admin.

    Mirrors notify_admins_new_appeal's best-effort semantics: a failure
    sending to one admin is logged and does not stop the rest from being
    notified. If ADMIN_IDS is empty this is a no-op.
    """
    if not ADMIN_IDS:
        return

    text = _build_notification_text(contact, user)
    keyboard = admin_contact_reply_keyboard(contact.id)

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=keyboard)
        except Exception:
            logger.exception(
                "Failed to notify admin %s about admin contact %s", admin_id, contact.contact_number
            )


@router.message(F.text == MENU_ADMIN_CONTACT)
async def menu_admin_contact(message: Message, state: FSMContext) -> None:
    # Reachable from any FSM state -- this router is included before
    # start_router (see app/main.py), so pressing this button always takes
    # priority over start_router's per-state catch-alls (e.g. mid-registration),
    # exactly like "📨 Мурожаат юбориш"/"💡 Таклиф юбориш" in app/handlers/start.py.
    # No registration required: a brand-new user can contact admins directly.
    await state.clear()
    await state.set_state(AdminContactStates.waiting_for_message)
    await message.answer(ASK_MESSAGE_TEXT)


@router.message(AdminContactStates.waiting_for_message, F.text)
async def process_admin_contact_message(message: Message, state: FSMContext) -> None:
    message_text = message.text.strip()

    if not is_valid_admin_contact_message(message_text):
        await message.answer(INVALID_MESSAGE_TEXT)
        return

    try:
        contact = await create_admin_contact(
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username,
            message_text=message_text,
        )
    except Exception:
        logger.exception("Failed to save admin contact message for user %s", message.from_user.id)
        await message.answer(GENERIC_ERROR_TEXT)
        return

    await state.clear()
    await message.answer(
        CONTACT_SUCCESS_TEXT_TEMPLATE.format(contact_number=contact.contact_number),
        reply_markup=main_menu_keyboard(),
    )

    # Notifying admins is best-effort: the citizen has already received their
    # success message above, so a failure here must never surface to them.
    try:
        contact_user = await get_user_by_id(contact.user_id) if contact.user_id is not None else None
        await notify_admins_new_contact(message.bot, contact, contact_user)
    except Exception:
        logger.exception("Failed to notify admins about admin contact %s", contact.contact_number)


@router.message(AdminContactStates.waiting_for_message)
async def process_admin_contact_message_invalid(message: Message) -> None:
    await message.answer(INVALID_MESSAGE_TEXT)


@router.callback_query(F.data.startswith(f"{ADMIN_CONTACT_REPLY_CALLBACK_PREFIX}:"))
async def process_admin_contact_reply_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return

    contact_id = _parse_contact_id(callback.data)
    if contact_id is None:
        await callback.answer(CONTACT_NOT_FOUND_TEXT, show_alert=True)
        return

    contact = await get_admin_contact_by_id(contact_id)
    if contact is None:
        await callback.answer(CONTACT_NOT_FOUND_TEXT, show_alert=True)
        return

    try:
        await set_admin_contact_in_progress(contact_id, callback.from_user.id)
    except Exception:
        logger.exception("Failed to mark admin contact %s as IN_PROGRESS", contact_id)
        await callback.answer(GENERIC_ERROR_TEXT, show_alert=True)
        return

    await state.set_state(AdminContactReplyStates.waiting_for_reply)
    await state.update_data(
        contact_id=contact_id,
        notify_chat_id=callback.message.chat.id if callback.message else None,
        notify_message_id=callback.message.message_id if callback.message else None,
    )

    if callback.message is not None:
        await callback.message.answer(ASK_REPLY_TEXT)
    await callback.answer()


@router.message(AdminContactReplyStates.waiting_for_reply, F.text)
async def process_admin_contact_reply_text(message: Message, state: FSMContext) -> None:
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
    contact_id = data.get("contact_id")
    notify_chat_id = data.get("notify_chat_id")
    notify_message_id = data.get("notify_message_id")

    if contact_id is None:
        await state.clear()
        await message.answer(STATE_LOST_TEXT)
        return

    contact = await get_admin_contact_by_id(contact_id)
    if contact is None:
        await state.clear()
        await message.answer(CONTACT_NOT_FOUND_TEXT)
        return

    user = await get_user_by_id(contact.user_id) if contact.user_id is not None else None
    if user is None:
        await state.clear()
        await message.answer(NO_RECIPIENT_TEXT)
        return

    user_text = USER_ANSWER_TEMPLATE.format(
        contact_number=html.escape(contact.contact_number),
        admin_answer=html.escape(admin_answer),
    )

    # Deliver to the citizen FIRST. Only persist admin_answer/COMPLETED once
    # delivery actually succeeded -- otherwise the citizen would never see a
    # reply that the database claims was already sent.
    try:
        await message.bot.send_message(user.telegram_id, user_text)
    except Exception:
        logger.exception(
            "Failed to deliver admin contact reply to user %s for contact %s",
            user.telegram_id,
            contact_id,
        )
        await message.answer(SEND_FAILED_TEXT)
        # Keep AdminContactReplyStates.waiting_for_reply / the stored contact_id
        # so the admin can just retry without re-clicking the notification button.
        return

    try:
        completed_contact = await complete_admin_contact(contact_id, message.from_user.id, admin_answer)
    except Exception:
        logger.exception("Failed to save admin contact answer for contact %s", contact_id)
        await message.answer(SAVE_FAILED_TEXT)
        await state.clear()
        return

    await state.clear()
    await message.answer(REPLY_SUCCESS_TEXT)

    if completed_contact is not None and notify_chat_id is not None and notify_message_id is not None:
        try:
            await message.bot.edit_message_text(
                chat_id=notify_chat_id,
                message_id=notify_message_id,
                text=_build_notification_text(completed_contact, user, admin_answer=admin_answer),
            )
        except Exception:
            # Purely cosmetic (the reply was already sent and saved) -- never
            # let this break the main flow.
            logger.exception(
                "Failed to update admin contact notification message for contact %s", contact_id
            )


@router.message(AdminContactReplyStates.waiting_for_reply)
async def process_admin_contact_reply_invalid(message: Message) -> None:
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(INVALID_REPLY_TEXT)


def _parse_contact_id(callback_data: str | None) -> int | None:
    if not callback_data or ":" not in callback_data:
        return None
    try:
        return int(callback_data.split(":", 1)[1])
    except ValueError:
        return None


def _build_notification_text(
    contact: AdminContact, user: User | None, *, admin_answer: str | None = None
) -> str:
    lines = [
        "👨‍💼 <b>АДМИН БИЛАН БОҒЛАНИШ</b>",
        "",
        f"🆔 <b>Мурожаат рақами:</b> {html.escape(contact.contact_number)}",
        f"👤 <b>Ф.И.Ш.:</b> {html.escape(user.full_name) if user and user.full_name else NOT_PROVIDED_TEXT}",
        f"📱 <b>Телефон:</b> {html.escape(user.phone) if user and user.phone else NOT_PROVIDED_TEXT}",
        f"📍 <b>Вилоят:</b> {html.escape(user.region) if user and user.region else NOT_PROVIDED_TEXT}",
        f"🏙 <b>Туман/шаҳар:</b> {html.escape(user.district) if user and user.district else NOT_PROVIDED_TEXT}",
        "",
        "💬 <b>Хабар:</b>",
        html.escape(contact.message_text),
        "",
        f"🕐 <b>Сана ва вақт:</b> {format_tashkent(contact.created_at)}",
    ]

    if admin_answer is not None:
        lines += ["", "💬 <b>Админ жавоби:</b>", html.escape(admin_answer)]

    return "\n".join(lines)
