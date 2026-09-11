from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import SUPERADMIN_IDS, all_admin_ids, is_admin, is_superadmin
from app.keyboards import (
    ADMIN_PANEL_CALLBACK_PREFIX,
    APPEAL_CANCEL_REPLY_CALLBACK_PREFIX,
    APPEAL_REPLY_CALLBACK_PREFIX,
    SUGGESTION_REVIEW_CALLBACK_PREFIX,
    admin_cancel_reply_keyboard,
    admin_panel_keyboard,
    admin_reply_keyboard,
    suggestion_review_keyboard,
)
from app.i18n import appeal_category_text, appeal_status_text, t
from app.models import Appeal, Suggestion, User
from app.services.appeal_service import (
    admin_appeal_counts,
    claim_appeal,
    complete_appeal,
    get_appeal_by_id,
    list_admin_appeals,
    release_appeal_claim,
    search_appeal_by_number,
)
from app.services.datetime_utils import format_tashkent, utcnow
from app.services.admin_notification_state import clear_notifications, list_notifications, remember_notification
from app.services.telegram_delivery import (
    TELEGRAM_MESSAGE_LIMIT,
    safe_edit_message_text,
    send_long_message,
)
from app.services.delivery_status import DELIVERY_DELIVERED, DELIVERY_FAILED, classify_delivery_exception
from app.services.user_service import get_user_by_id, mark_user_unreachable
from app.services.suggestion_service import list_suggestions, review_suggestion, suggestion_counts
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
    if not all_admin_ids():
        return

    body_text = _build_appeal_body_text(appeal, user)
    footer_text = _build_appeal_footer_text(appeal, completed=False)
    full_text = f"{body_text}\n\n{footer_text}"
    keyboard = admin_reply_keyboard(appeal.id)

    for admin_id in all_admin_ids():
        if appeal.attachment_file_id:
            try:
                caption = f"📎 {html.escape(appeal.appeal_number)} — мурожаат иловаси"
                if appeal.attachment_type == "PHOTO":
                    await bot.send_photo(admin_id, appeal.attachment_file_id, caption=caption)
                elif appeal.attachment_type == "PDF":
                    await bot.send_document(admin_id, appeal.attachment_file_id, caption=caption)
            except Exception:
                # Attachment delivery is best-effort. The textual appeal notification
                # must still reach the admin even if Telegram rejects the media copy.
                logger.exception(
                    "Failed to send attachment to admin %s for appeal %s",
                    admin_id,
                    appeal.appeal_number,
                )
        try:
            if len(full_text) <= TELEGRAM_MESSAGE_LIMIT:
                sent = await send_long_message(bot, admin_id, full_text, reply_markup=keyboard)
            else:
                await send_long_message(bot, admin_id, body_text)
                sent = await send_long_message(bot, admin_id, footer_text, reply_markup=keyboard)
            await remember_notification("appeal", appeal.id, admin_id, sent.chat.id, sent.message_id)
        except Exception:
            logger.exception("Failed to notify admin %s about appeal %s", admin_id, appeal.appeal_number)


async def notify_admins_new_suggestion(bot: Bot, suggestion: Suggestion, user: User) -> None:
    """Stage 23: suggestions go only to SUPERADMIN users."""
    if not SUPERADMIN_IDS:
        return
    text = _build_suggestion_notification_text(suggestion, user)
    keyboard = suggestion_review_keyboard(suggestion.id)
    for admin_id in SUPERADMIN_IDS:
        try:
            sent = await send_long_message(bot, admin_id, text, reply_markup=keyboard)
            await remember_notification("suggestion", suggestion.id, admin_id, sent.chat.id, sent.message_id)
        except Exception:
            logger.exception(
                "Failed to notify superadmin %s about suggestion %s", admin_id, suggestion.suggestion_number
            )




def _admin_display_name(user) -> str:
    return html.escape(getattr(user, "full_name", None) or getattr(user, "username", None) or str(user.id))


async def _set_appeal_buttons(bot: Bot, appeal_id: int, *, enabled: bool) -> None:
    notifications = await list_notifications("appeal", appeal_id)
    markup = admin_reply_keyboard(appeal_id) if enabled else None
    for info in notifications.values():
        try:
            await bot.edit_message_reply_markup(
                chat_id=info["chat_id"], message_id=info["message_id"], reply_markup=markup
            )
        except Exception:
            logger.exception("Failed to update appeal buttons for %s", appeal_id)


async def _broadcast_admins(bot: Bot, text: str) -> None:
    for admin_id in all_admin_ids():
        try:
            await send_long_message(bot, admin_id, text)
        except Exception:
            logger.exception("Failed to broadcast admin update to %s", admin_id)


async def _broadcast_superadmins(bot: Bot, text: str) -> None:
    for admin_id in SUPERADMIN_IDS:
        try:
            await send_long_message(bot, admin_id, text)
        except Exception:
            logger.exception("Failed to broadcast superadmin update to %s", admin_id)


@router.callback_query(F.data.startswith(f"{APPEAL_REPLY_CALLBACK_PREFIX}:"))
async def process_appeal_reply_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
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

    # The database keeps stable English status codes, but citizens never see
    # those internal values. Notify them with the label in their selected UI
    # language (Uzbek users see "Ko‘rib chiqilmoqda" / "Кўриб чиқилмоқда").
    if claimed:
        try:
            citizen = await get_user_by_id(appeal.user_id)
            if citizen is not None:
                await send_long_message(
                    callback.bot,
                    citizen.telegram_id,
                    t(
                        "appeal.status_changed",
                        citizen.language_code,
                        appeal_number=appeal.appeal_number,
                        status=appeal_status_text("IN_PROGRESS", citizen.language_code),
                    ),
                )
        except Exception:
            logger.exception("Failed to notify citizen about IN_PROGRESS status for appeal %s", appeal_id)

        # Remove the reply button from every admin copy immediately. The DB claim
        # above is authoritative; these edits are only the synchronized UI.
        await _set_appeal_buttons(callback.bot, appeal_id, enabled=False)
        await _broadcast_admins(
            callback.bot,
            f"🟡 <b>{html.escape(appeal.appeal_number)}</b> мурожаати {_admin_display_name(callback.from_user)} томонидан кўриб чиқилмоқда.",
        )

    await state.set_state(AdminStates.waiting_for_reply)
    await state.update_data(
        appeal_id=appeal_id,
        notify_chat_id=callback.message.chat.id if callback.message else None,
        notify_message_id=callback.message.message_id if callback.message else None,
    )

    if callback.message is not None:
        await callback.message.answer(ASK_REPLY_TEXT, reply_markup=admin_cancel_reply_keyboard(appeal_id))
    await callback.answer()


@router.message(AdminStates.waiting_for_reply, F.text)
async def process_admin_reply_text(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
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
    if appeal.status != "IN_PROGRESS" or appeal.admin_id != message.from_user.id:
        await state.clear()
        await message.answer("⚠️ Бу мурожаат энди Сизга бириктирилмаган.")
        return
    if appeal.claim_expires_at is not None and appeal.claim_expires_at <= utcnow():
        await state.clear()
        await message.answer("⏱ Жавоб бериш учун 15 дақиқалик вақт тугади. Мурожаатни қайта қабул қилинг.")
        return

    user = await get_user_by_id(appeal.user_id)
    if user is None:
        await state.clear()
        await message.answer(APPEAL_NOT_FOUND_TEXT)
        return

    citizen_text = t(
        "appeal.admin_answer",
        user.language_code,
        appeal_number=html.escape(appeal.appeal_number),
        admin_answer=html.escape(admin_answer),
    )

    delivery_status = DELIVERY_DELIVERED
    delivery_error_code = None
    try:
        await send_long_message(message.bot, user.telegram_id, citizen_text)
    except Exception as exc:
        delivery_status = DELIVERY_FAILED
        delivery_error_code, unreachable = classify_delivery_exception(exc)
        logger.exception(
            "Failed to deliver admin reply to user %s for appeal %s", user.telegram_id, appeal_id
        )
        if unreachable:
            await mark_user_unreachable(user.telegram_id)

    try:
        completed_appeal = await complete_appeal(
            appeal_id,
            message.from_user.id,
            admin_answer,
            delivery_status=delivery_status,
            delivery_error_code=delivery_error_code,
        )
    except Exception:
        logger.exception("Failed to save admin answer for appeal %s", appeal_id)
        await message.answer(SAVE_FAILED_TEXT)
        await state.clear()
        return

    await state.clear()
    if delivery_status == DELIVERY_DELIVERED:
        await message.answer(REPLY_SUCCESS_TEXT)
    else:
        await message.answer(
            "⚠️ Жавоб базага сақланди, лекин фуқарога Telegram орқали етказиб бўлмади."
        )

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

    if completed_appeal is not None:
        await _broadcast_admins(
            message.bot,
            f"✅ <b>{html.escape(completed_appeal.appeal_number)}</b> мурожаати бўйича {_admin_display_name(message.from_user)} жавоб юборди.",
        )
        await clear_notifications("appeal", appeal_id)


@router.callback_query(F.data.startswith(f"{APPEAL_CANCEL_REPLY_CALLBACK_PREFIX}:"))
async def process_appeal_cancel_reply(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return
    appeal_id = _parse_appeal_id(callback.data)
    if appeal_id is None:
        await callback.answer(APPEAL_NOT_FOUND_TEXT, show_alert=True)
        return
    appeal = await release_appeal_claim(appeal_id, callback.from_user.id)
    if appeal is None:
        await callback.answer(APPEAL_NOT_FOUND_TEXT, show_alert=True)
        return
    if appeal.status != "NEW":
        await callback.answer("Бу мурожаатни бекор қилиш мумкин эмас.", show_alert=True)
        return
    await state.clear()
    await _set_appeal_buttons(callback.bot, appeal_id, enabled=True)
    await _broadcast_admins(
        callback.bot,
        f"🔓 <b>{html.escape(appeal.appeal_number)}</b> мурожаати яна жавоб бериш учун очилди.",
    )
    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await callback.answer("Мурожаат қайта очилди.")


@router.callback_query(F.data.startswith(f"{SUGGESTION_REVIEW_CALLBACK_PREFIX}:"))
async def process_suggestion_review(callback: CallbackQuery) -> None:
    if not is_superadmin(callback.from_user.id):
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return
    suggestion_id = _parse_appeal_id(callback.data)
    if suggestion_id is None:
        await callback.answer("Таклиф топилмади.", show_alert=True)
        return
    suggestion, changed = await review_suggestion(suggestion_id, callback.from_user.id)
    if suggestion is None:
        await callback.answer("Таклиф топилмади.", show_alert=True)
        return
    if not changed:
        await callback.answer("Бу таклиф аввал кўриб чиқилган.", show_alert=True)
        if callback.message is not None:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        return

    notifications = await list_notifications("suggestion", suggestion.id)
    for info in notifications.values():
        try:
            await callback.bot.edit_message_reply_markup(
                chat_id=info["chat_id"], message_id=info["message_id"], reply_markup=None
            )
        except Exception:
            logger.exception("Failed to clear suggestion review button for %s", suggestion.id)

    citizen = await get_user_by_id(suggestion.user_id)
    if citizen is not None:
        try:
            await send_long_message(
                callback.bot,
                citizen.telegram_id,
                t("suggestion.reviewed", citizen.language_code, suggestion_number=suggestion.suggestion_number),
            )
        except Exception:
            logger.exception("Failed to notify citizen about reviewed suggestion %s", suggestion.id)

    await _broadcast_superadmins(
        callback.bot,
        f"☑️ <b>{html.escape(suggestion.suggestion_number)}</b> таклифи {_admin_display_name(callback.from_user)} томонидан кўриб чиқилди.",
    )
    await clear_notifications("suggestion", suggestion.id)
    await callback.answer("Таклиф кўриб чиқилди.")


@router.message(Command("admin"))
async def admin_panel_command(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await message.answer(NOT_ADMIN_TEXT)
        return
    await state.clear()
    role = "SUPERADMIN" if is_superadmin(message.from_user.id) else "ADMIN"
    await message.answer(
        f"👨‍💼 <b>Админ панель</b>\n\nРоль: <b>{role}</b>",
        reply_markup=admin_panel_keyboard(superadmin=is_superadmin(message.from_user.id)),
    )


@router.callback_query(F.data.startswith(f"{ADMIN_PANEL_CALLBACK_PREFIX}:"))
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return
    action = (callback.data or "").split(":", 1)[1] if ":" in (callback.data or "") else ""
    if action == "stats":
        appeals = await admin_appeal_counts()
        suggestions = await suggestion_counts() if is_superadmin(callback.from_user.id) else {}
        text = (
            "📊 <b>Статистика</b>\n\n"
            f"🆕 Янги мурожаатлар: {appeals.get('NEW', 0)}\n"
            f"🟡 Кўриб чиқилмоқда: {appeals.get('IN_PROGRESS', 0)}\n"
            f"✅ Якунланган: {appeals.get('COMPLETED', 0)}\n"
            f"❌ Рад этилган: {appeals.get('REJECTED', 0)}"
        )
        if is_superadmin(callback.from_user.id):
            text += f"\n\n💡 Янги таклифлар: {suggestions.get('NEW', 0)}\n☑️ Кўриб чиқилган: {suggestions.get('REVIEWED', 0)}"
        await callback.message.answer(text)
    elif action == "appeals":
        rows = await list_admin_appeals("NEW", limit=10)
        if not rows:
            await callback.message.answer("📨 Янги мурожаатлар йўқ.")
        else:
            await callback.message.answer("📨 <b>Охирги янги мурожаатлар</b>")
            for appeal in rows:
                await callback.message.answer(
                    f"{html.escape(appeal.appeal_number)} — {appeal_status_text('NEW', 'uz_cyrl')}",
                    reply_markup=admin_reply_keyboard(appeal.id),
                )
    elif action == "suggestions":
        if not is_superadmin(callback.from_user.id):
            await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
            return
        rows = await list_suggestions(status="NEW", limit=10)
        if not rows:
            await callback.message.answer("💡 Янги таклифлар йўқ.")
        else:
            for suggestion in rows:
                await callback.message.answer(
                    f"💡 {html.escape(suggestion.suggestion_number)}",
                    reply_markup=suggestion_review_keyboard(suggestion.id),
                )
    elif action == "search":
        await state.set_state(AdminStates.waiting_for_search)
        await callback.message.answer("🔎 Мурожаат рақамини киритинг. Масалан: MUR-000123")
    await callback.answer()


@router.message(AdminStates.waiting_for_search, F.text)
async def admin_search_message(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    appeal = await search_appeal_by_number(message.text.strip())
    await state.clear()
    if appeal is None:
        await message.answer("Мурожаат топилмади.")
        return
    user = await get_user_by_id(appeal.user_id)
    if user is None:
        await message.answer("Мурожаат эгаси топилмади.")
        return
    text = f"{_build_appeal_body_text(appeal, user)}\n\n{_build_appeal_footer_text(appeal, completed=appeal.status == 'COMPLETED')}"
    markup = admin_reply_keyboard(appeal.id) if appeal.status == "NEW" else None
    await send_long_message(message.bot, message.chat.id, text, reply_markup=markup)


@router.message(AdminStates.waiting_for_reply)
async def process_admin_reply_invalid(message: Message) -> None:
    if not is_admin(message.from_user.id):
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
    attachment_label = {"PHOTO": "Фото", "PDF": "PDF ҳужжат"}.get(
        appeal.attachment_type, "Йўқ"
    )
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
        f"🗂 <b>Йўналиш:</b> {html.escape(appeal_category_text(appeal.category_code, 'uz_cyrl'))}",
        "",
        f"📋 <b>Мавзу:</b> {html.escape(appeal.subject or '-')}",
        "",
        f"📎 <b>Илова:</b> {attachment_label}",
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
    status_emoji = {
        "NEW": "🆕",
        "IN_PROGRESS": "🟡",
        "WAITING_FOR_USER": "⏳",
        "COMPLETED": "✅",
        "REJECTED": "⛔",
    }.get(appeal.status, "📌")
    status_label = appeal_status_text(appeal.status, "uz_cyrl")
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
