from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.services.admin_service import all_admin_ids, is_admin
from app.i18n import t
from app.keyboards import (
    ADMIN_CONTACT_REPLY_CALLBACK_PREFIX,
    admin_contact_reply_keyboard,
    main_menu_keyboard,
    menu_texts,
    remove_keyboard,
)
from app.models import AdminContact, User
from app.services.admin_contact_service import (
    claim_admin_contact,
    complete_admin_contact,
    create_admin_contact,
    get_admin_contact_by_id,
)
from app.services.datetime_utils import format_tashkent
from app.services.shared_state import acquire_submission, finish_submission, is_rate_limited
from app.services.telegram_delivery import (
    TELEGRAM_MESSAGE_LIMIT,
    safe_edit_message_text,
    send_long_message,
)
from app.services.delivery_status import DELIVERY_DELIVERED, DELIVERY_FAILED, classify_delivery_exception
from app.services.user_service import get_user_by_id, get_user_language, mark_user_unreachable
from app.services.validators import is_valid_admin_contact_message
from app.states import AdminContactReplyStates, AdminContactStates

logger = logging.getLogger(__name__)

router = Router()

MIN_REPLY_LENGTH = 2
MAX_REPLY_LENGTH = 4000

# MVP audit MEDIUM #8 / instruction #7: cap how many admin-contact messages a
# single citizen can submit in a short window, so accidental or careless
# rapid-fire re-sends can't spam every admin. Deliberately generous (well
# above any plausible normal-use rate) so it never blocks a genuine user --
# see app/services/rate_limit.py for the (Redis-swappable) backend.
RATE_LIMIT_MAX_SUBMISSIONS = 3
RATE_LIMIT_WINDOW_SECONDS = 60.0

NOT_PROVIDED_TEXT = "Маълумот киритилмаган"

ASK_MESSAGE_TEXT = "💬 Админга юбориш учун хабарингизни ёзинг:"
INVALID_MESSAGE_TEXT = (
    "Хабар матни нотўғри. Илтимос, камида 2, кўпи билан 4000 та белгидан иборат матн киритинг."
)
RATE_LIMITED_TEXT = (
    "⏳ Сиз жуда тез-тез хабар юбормоқдасиз. Илтимос, бир оз кутиб қайта уриниб кўринг."
)
CONTACT_SUCCESS_TEXT_TEMPLATE = (
    "✅ Хабарингиз қабул қилинди.\n\n"
    "Мурожаат рақами: {contact_number}\n\n"
    "Админлар томонидан кўриб чиқилади."
)
GENERIC_ERROR_TEXT = "Хатолик юз берди. Илтимос, бироздан сўнг қайта уриниб кўринг."

NOT_ADMIN_TEXT = "Сизда ушбу амални бажариш ҳуқуқи мавжуд эмас."
CONTACT_NOT_FOUND_TEXT = "Мурожаат топилмади."
ALREADY_CLAIMED_TEXT = (
    "Бу мурожаат аллақачон бошқа админ томонидан қабул қилинган."
)
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

    MVP audit CRITICAL #1: message_text can be up to 4000 characters, which
    combined with the header/footer can exceed Telegram's 4096-char message
    limit -- see app.handlers.admin.notify_admins_new_appeal for the full
    rationale; the split-when-needed strategy here is identical.
    """
    admin_ids = await all_admin_ids()
    if not admin_ids:
        return

    body_text = _build_contact_body_text(contact, user)
    footer_text = _build_contact_footer_text(contact, completed=False)
    full_text = f"{body_text}\n\n{footer_text}"
    keyboard = admin_contact_reply_keyboard(contact.id)

    for admin_id in admin_ids:
        try:
            if len(full_text) <= TELEGRAM_MESSAGE_LIMIT:
                await send_long_message(bot, admin_id, full_text, reply_markup=keyboard)
            else:
                await send_long_message(bot, admin_id, body_text)
                await send_long_message(bot, admin_id, footer_text, reply_markup=keyboard)
        except Exception:
            logger.exception(
                "Failed to notify admin %s about admin contact %s", admin_id, contact.contact_number
            )


@router.message(F.text.in_(menu_texts("admin_contact")))
async def menu_admin_contact(message: Message, state: FSMContext) -> None:
    # Reachable from any FSM state -- this router is included before
    # start_router (see app/main.py), so pressing this button always takes
    # priority over start_router's per-state catch-alls (e.g. mid-registration),
    # exactly like "📨 Мурожаат юбориш"/"💡 Таклиф юбориш" in app/handlers/start.py.
    # No registration required: a brand-new user can contact admins directly.
    await state.clear()
    language = await get_user_language(message.from_user.id)
    await state.update_data(language_code=language)
    await state.set_state(AdminContactStates.waiting_for_message)
    await message.answer(t("admin_contact.ask", language), reply_markup=remove_keyboard())


@router.message(AdminContactStates.waiting_for_message, F.text)
async def process_admin_contact_message(message: Message, state: FSMContext) -> None:
    language = await get_user_language(message.from_user.id)
    message_text = message.text.strip()

    if not is_valid_admin_contact_message(message_text):
        await message.answer(t("admin_contact.invalid", language))
        return

    if await is_rate_limited(
        f"admin_contact_create:{message.from_user.id}",
        limit=RATE_LIMIT_MAX_SUBMISSIONS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    ):
        await message.answer(t("common.rate_limited", language))
        return

    # Idempotency (MVP audit instruction #4): guards against Telegram
    # redelivering the same update (message_id is unique per chat, so a
    # genuinely new message from the user is never mistaken for a duplicate).
    submission_key = f"admin_contact_create:{message.chat.id}:{message.message_id}"
    submission_token = await acquire_submission(submission_key)
    if submission_token is None:
        logger.info(
            "Ignoring duplicate delivery of message %s in chat %s (admin contact create)",
            message.message_id,
            message.chat.id,
        )
        return

    try:
        contact = await create_admin_contact(
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username,
            message_text=message_text,
        )
    except Exception:
        await finish_submission(submission_key, submission_token, failed=True)
        logger.exception("Failed to save admin contact message for user %s", message.from_user.id)
        await message.answer(t("common.error", language))
        return

    await finish_submission(submission_key, submission_token)
    await state.clear()
    await message.answer(
        t("admin_contact.success", language, contact_number=contact.contact_number),
        reply_markup=main_menu_keyboard(language),
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
    language = await get_user_language(message.from_user.id)
    await message.answer(t("admin_contact.invalid", language))


@router.callback_query(F.data.startswith(f"{ADMIN_CONTACT_REPLY_CALLBACK_PREFIX}:"))
async def process_admin_contact_reply_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return

    contact_id = _parse_contact_id(callback.data)
    if contact_id is None:
        await callback.answer(CONTACT_NOT_FOUND_TEXT, show_alert=True)
        return

    # Atomic first-claim-wins update -- see app.services.appeal_service.claim_appeal
    # for the full rationale (MVP audit CRITICAL #2 / instruction #5). A claim
    # already held by THIS SAME admin (redelivered callback_query -- instruction
    # #4) is treated as a safe no-op; held by a DIFFERENT admin is refused.
    try:
        contact, claimed = await claim_admin_contact(contact_id, callback.from_user.id)
    except Exception:
        logger.exception("Failed to claim admin contact %s", contact_id)
        await callback.answer(GENERIC_ERROR_TEXT, show_alert=True)
        return

    if contact is None:
        await callback.answer(CONTACT_NOT_FOUND_TEXT, show_alert=True)
        return

    if not claimed and contact.admin_id != callback.from_user.id:
        await callback.answer(ALREADY_CLAIMED_TEXT, show_alert=True)
        if callback.message is not None:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                logger.exception("Failed to clear stale reply button for admin contact %s", contact_id)
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
    if not await is_admin(message.from_user.id):
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

    user_text = t(
        "admin_contact.answer",
        user.language_code,
        contact_number=html.escape(contact.contact_number),
        admin_answer=html.escape(admin_answer),
    )

    delivery_status = DELIVERY_DELIVERED
    delivery_error_code = None
    try:
        await send_long_message(message.bot, user.telegram_id, user_text)
    except Exception as exc:
        delivery_status = DELIVERY_FAILED
        delivery_error_code, unreachable = classify_delivery_exception(exc)
        logger.exception(
            "Failed to deliver admin contact reply to user %s for contact %s",
            user.telegram_id,
            contact_id,
        )
        if unreachable:
            await mark_user_unreachable(user.telegram_id)

    try:
        completed_contact = await complete_admin_contact(
            contact_id,
            message.from_user.id,
            admin_answer,
            delivery_status=delivery_status,
            delivery_error_code=delivery_error_code,
        )
    except Exception:
        logger.exception("Failed to save admin contact answer for contact %s", contact_id)
        await message.answer(SAVE_FAILED_TEXT)
        await state.clear()
        return

    await state.clear()
    if delivery_status == DELIVERY_DELIVERED:
        await message.answer(REPLY_SUCCESS_TEXT)
    else:
        await message.answer(
            "⚠️ Жавоб базага сақланди, лекин фойдаланувчига Telegram орқали етказиб бўлмади."
        )

    if completed_contact is not None and notify_chat_id is not None and notify_message_id is not None:
        # Update the admin's own notification to reflect COMPLETED status
        # (dropping the now-answered button, by omitting reply_markup on the
        # edit). The admin's answer is always sent as its own separate
        # message below instead of folded into this edit, keeping the edit
        # itself within the 4096-char limit regardless of answer length.
        body_text = _build_contact_body_text(completed_contact, user)
        completed_footer = _build_contact_footer_text(completed_contact, completed=True)
        combined = f"{body_text}\n\n{completed_footer}"
        edit_text = combined if len(combined) <= TELEGRAM_MESSAGE_LIMIT else completed_footer

        try:
            await safe_edit_message_text(
                message.bot, chat_id=notify_chat_id, message_id=notify_message_id, text=edit_text
            )
        except Exception:
            # Purely cosmetic (the reply was already sent and saved) -- never
            # let this break the main flow.
            logger.exception(
                "Failed to update admin contact notification message for contact %s", contact_id
            )

        try:
            await send_long_message(
                message.bot,
                notify_chat_id,
                _build_answer_followup_text(completed_contact, admin_answer),
            )
        except Exception:
            logger.exception("Failed to send answer follow-up message for admin contact %s", contact_id)


@router.message(AdminContactReplyStates.waiting_for_reply)
async def process_admin_contact_reply_invalid(message: Message) -> None:
    if not await is_admin(message.from_user.id):
        return
    await message.answer(INVALID_REPLY_TEXT)


def _parse_contact_id(callback_data: str | None) -> int | None:
    if not callback_data or ":" not in callback_data:
        return None
    try:
        return int(callback_data.split(":", 1)[1])
    except ValueError:
        return None


def _build_contact_body_text(contact: AdminContact, user: User | None) -> str:
    """Everything about the admin-contact message except the timestamp/status footer.

    Split out from the old single ``_build_notification_text`` so it can be
    sent on its own (see ``notify_admins_new_contact``) when the combined
    message would exceed Telegram's 4096-char limit. This part never changes
    once the message is created, so it's reused as-is for the completion edit.
    """
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
    ]
    return "\n".join(lines)


def _build_contact_footer_text(contact: AdminContact, *, completed: bool) -> str:
    """The short timestamp/status line -- always well within the 4096 limit."""
    status_emoji = "🟢" if completed else "🟡"
    status_label = "COMPLETED" if completed else "NEW"
    lines = [
        f"🕐 <b>Сана ва вақт:</b> {format_tashkent(contact.created_at)}",
        "",
        f"{status_emoji} <b>Ҳолат:</b> {status_label}",
    ]
    return "\n".join(lines)


def _build_answer_followup_text(contact: AdminContact, admin_answer: str) -> str:
    """The admin's own answer, shown back to them as a separate confirmation message."""
    return (
        f"💬 <b>Жавоб юборилди</b> (Мурожаат {html.escape(contact.contact_number)}):\n\n"
        f"{html.escape(admin_answer)}"
    )
