from __future__ import annotations

import html
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.keyboards import (
    ADMIN_PANEL_CALLBACK_PREFIX,
    ADMIN_MANAGE_CALLBACK_PREFIX,
    ADMIN_ROLE_CALLBACK_PREFIX,
    ADMIN_BROADCAST_CALLBACK_PREFIX,
    APPEAL_CANCEL_REPLY_CALLBACK_PREFIX,
    APPEAL_REPLY_CALLBACK_PREFIX,
    SUGGESTION_REVIEW_CALLBACK_PREFIX,
    admin_cancel_reply_keyboard,
    admin_panel_keyboard,
    admin_management_keyboard,
    admin_broadcast_audience_keyboard,
    admin_broadcast_confirm_keyboard,
    admin_role_keyboard,
    admin_reply_keyboard,
    suggestion_review_keyboard,
)
from app.i18n import appeal_category_text, appeal_status_text, t
from app.models import Appeal, Suggestion, User
from app.services.admin_service import (
    ROLE_ADMIN,
    ROLE_SUPERADMIN,
    add_or_update_admin,
    all_admin_ids,
    all_superadmin_ids,
    get_admin_role,
    is_admin,
    is_root_superadmin,
    is_superadmin,
    list_admin_entries,
    remove_dynamic_admin,
)
from app.services.appeal_service import (
    admin_appeal_counts,
    claim_appeal,
    complete_appeal,
    get_appeal_by_id,
    list_admin_appeals,
    list_unanswered_admin_appeals,
    get_unanswered_appeal_summary,
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
from app.services.user_service import (
    get_user_by_id,
    list_broadcast_user_ids,
    mark_user_unreachable,
)
from app.services.suggestion_service import list_suggestions, review_suggestion, suggestion_counts
from app.services.web_admin_auth import issue_login_url
from app.states import AdminBroadcastStates, AdminStates
from app.services.broadcast_service import broadcast_copied_message

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
    admin_ids = await all_admin_ids()
    if not admin_ids:
        return

    body_text = _build_appeal_body_text(appeal, user)
    footer_text = _build_appeal_footer_text(appeal, completed=False)
    full_text = f"{body_text}\n\n{footer_text}"
    keyboard = admin_reply_keyboard(appeal.id)

    for admin_id in admin_ids:
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
    superadmin_ids = await all_superadmin_ids()
    if not superadmin_ids:
        return
    text = _build_suggestion_notification_text(suggestion, user)
    keyboard = suggestion_review_keyboard(suggestion.id)
    for admin_id in superadmin_ids:
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
    for admin_id in await all_admin_ids():
        try:
            await send_long_message(bot, admin_id, text)
        except Exception:
            logger.exception("Failed to broadcast admin update to %s", admin_id)


async def _broadcast_superadmins(bot: Bot, text: str) -> None:
    for admin_id in await all_superadmin_ids():
        try:
            await send_long_message(bot, admin_id, text)
        except Exception:
            logger.exception("Failed to broadcast superadmin update to %s", admin_id)


@router.callback_query(F.data.startswith(f"{APPEAL_REPLY_CALLBACK_PREFIX}:"))
async def process_appeal_reply_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_admin(callback.from_user.id):
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
    if not await is_admin(callback.from_user.id):
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
    if not await is_superadmin(callback.from_user.id):
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
    if not await is_admin(message.from_user.id):
        await message.answer(NOT_ADMIN_TEXT)
        return
    await state.clear()
    role = await get_admin_role(message.from_user.id) or "ADMIN"
    superadmin = role == ROLE_SUPERADMIN
    unanswered = await get_unanswered_appeal_summary(limit=1)
    await message.answer(
        f"👨‍💼 <b>Админ панель</b>\n\nРоль: <b>{role}</b>",
        reply_markup=admin_panel_keyboard(
            superadmin=superadmin,
            unanswered_count=unanswered.total,
        ),
    )


async def _send_admin_management(message: Message) -> None:
    entries = await list_admin_entries()
    lines = ["👥 <b>Админлар</b>", ""]
    if not entries:
        lines.append("Админлар топилмади.")
    else:
        for entry in entries:
            if entry.source == "ROOT":
                label = "👑 ROOT SUPERADMIN"
            elif entry.role == ROLE_SUPERADMIN:
                label = "👑 SUPERADMIN"
            else:
                label = "👤 ADMIN"
            source = " (Render)" if entry.source in {"ROOT", "ENV"} else ""
            lines.append(f"{label}: <code>{entry.telegram_id}</code>{source}")
    lines.extend(["", "➕ Янги админ қўшиш ёки пастдаги динамик админни ўчириш мумкин."])
    await message.answer("\n".join(lines), reply_markup=admin_management_keyboard(entries))


@router.callback_query(F.data == f"{ADMIN_MANAGE_CALLBACK_PREFIX}:add")
async def admin_manage_add(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_superadmin(callback.from_user.id):
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminStates.waiting_for_admin_id)
    if callback.message is not None:
        await callback.message.answer("Янги админнинг Telegram ID рақамини киритинг:")
    await callback.answer()


@router.message(AdminStates.waiting_for_admin_id, F.text)
async def admin_manage_id_received(message: Message, state: FSMContext) -> None:
    if not await is_superadmin(message.from_user.id):
        await state.clear()
        await message.answer(NOT_ADMIN_TEXT)
        return
    raw = message.text.strip()
    if not raw.isdigit() or len(raw) > 20 or int(raw) <= 0:
        await message.answer("Telegram ID нотўғри. Фақат мусбат рақам киритинг.")
        return
    await state.update_data(target_admin_id=int(raw))
    await state.set_state(AdminStates.waiting_for_admin_role)
    await message.answer("Ролни танланг:", reply_markup=admin_role_keyboard())


@router.callback_query(
    AdminStates.waiting_for_admin_role,
    F.data.startswith(f"{ADMIN_ROLE_CALLBACK_PREFIX}:"),
)
async def admin_manage_role_selected(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_superadmin(callback.from_user.id):
        await state.clear()
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return
    role = (callback.data or "").split(":", 1)[1] if ":" in (callback.data or "") else ""
    if role not in {ROLE_SUPERADMIN, ROLE_ADMIN}:
        await callback.answer("Роль нотўғри.", show_alert=True)
        return
    data = await state.get_data()
    target_admin_id = data.get("target_admin_id")
    if not isinstance(target_admin_id, int):
        await state.clear()
        await callback.answer("Telegram ID топилмади. Қайта уриниб кўринг.", show_alert=True)
        return
    try:
        entry = await add_or_update_admin(target_admin_id, role, callback.from_user.id)
    except ValueError as exc:
        await state.clear()
        await callback.answer(str(exc), show_alert=True)
        return
    await state.clear()
    if callback.message is not None:
        await callback.message.answer(
            f"✅ <code>{entry.telegram_id}</code> — <b>{entry.role}</b> сифатида сақланди."
        )
        await _send_admin_management(callback.message)
    try:
        await send_long_message(
            callback.bot,
            entry.telegram_id,
            f"👨‍💼 Сизга ботда <b>{entry.role}</b> ҳуқуқи берилди. /admin орқали панелни очишингиз мумкин.",
        )
    except Exception:
        logger.info("Could not proactively notify new admin %s", entry.telegram_id)
    await callback.answer("Сақланди.")


@router.callback_query(F.data.startswith(f"{ADMIN_MANAGE_CALLBACK_PREFIX}:remove:"))
async def admin_manage_remove(callback: CallbackQuery) -> None:
    if not await is_superadmin(callback.from_user.id):
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return
    try:
        target_admin_id = int((callback.data or "").rsplit(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("Telegram ID нотўғри.", show_alert=True)
        return
    removed = await remove_dynamic_admin(target_admin_id, callback.from_user.id)
    if not removed:
        await callback.answer("Бу админни бот орқали ўчириб бўлмайди.", show_alert=True)
        return
    if callback.message is not None:
        await callback.message.answer(f"🗑 <code>{target_admin_id}</code> админлар рўйхатидан ўчирилди.")
        await _send_admin_management(callback.message)
    await callback.answer("Ўчирилди.")


@router.callback_query(F.data == f"{ADMIN_MANAGE_CALLBACK_PREFIX}:cancel")
async def admin_manage_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None and await is_superadmin(callback.from_user.id):
        await _send_admin_management(callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith(f"{ADMIN_BROADCAST_CALLBACK_PREFIX}:"))
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_superadmin(callback.from_user.id):
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return

    action = (callback.data or "").split(":", 1)[1] if ":" in (callback.data or "") else ""

    if action == "cancel":
        await state.clear()
        if callback.message is not None:
            role = await get_admin_role(callback.from_user.id) or ROLE_SUPERADMIN
            unanswered = await get_unanswered_appeal_summary(limit=1)
            await callback.message.answer(
                "❌ Хабар юбориш бекор қилинди.",
                reply_markup=admin_panel_keyboard(
                    superadmin=role == ROLE_SUPERADMIN,
                    unanswered_count=unanswered.total,
                ),
            )
        await callback.answer("Бекор қилинди.")
        return

    if action in {"users", "admins"}:
        recipients = (
            await list_broadcast_user_ids() if action == "users" else await all_admin_ids()
        )
        if not recipients:
            await callback.answer("Қабул қилувчилар топилмади.", show_alert=True)
            return
        await state.clear()
        await state.update_data(broadcast_audience=action)
        await state.set_state(AdminBroadcastStates.waiting_for_message)
        audience_label = "фойдаланувчилар" if action == "users" else "админлар"
        if callback.message is not None:
            await callback.message.answer(
                "📢 <b>Хабар тайёрлаш</b>\n\n"
                f"Қабул қилувчилар: <b>{len(recipients)} та {audience_label}</b>.\n\n"
                "Энди юбориладиган хабарни юборинг. Матн, фото, видео ёки PDF/ҳужжат бўлиши мумкин. "
                "Хабар қабул қилувчиларга худди шу кўринишда нусхаланади."
            )
        await callback.answer()
        return

    if action == "confirm":
        data = await state.get_data()
        audience = data.get("broadcast_audience")
        from_chat_id = data.get("broadcast_source_chat_id")
        message_id = data.get("broadcast_source_message_id")
        if (
            audience not in {"users", "admins"}
            or not isinstance(from_chat_id, int)
            or not isinstance(message_id, int)
        ):
            await state.clear()
            await callback.answer("Хабар маълумотлари топилмади. Қайта бошланг.", show_alert=True)
            return

        recipients = (
            await list_broadcast_user_ids() if audience == "users" else await all_admin_ids()
        )
        if not recipients:
            await state.clear()
            await callback.answer("Қабул қилувчилар топилмади.", show_alert=True)
            return

        await callback.answer("Хабар юбориш бошланди.")
        if callback.message is not None:
            await callback.message.answer(
                f"⏳ Хабар <b>{len(recipients)} та</b> қабул қилувчига юборилмоқда..."
            )

        # Clear before the potentially long send. A repeated confirm callback
        # cannot start the same broadcast again through this FSM session.
        await state.clear()
        result = await broadcast_copied_message(
            callback.bot,
            recipients,
            from_chat_id=from_chat_id,
            message_id=message_id,
            mark_unreachable_users=audience == "users",
        )

        if callback.message is not None:
            unanswered = await get_unanswered_appeal_summary(limit=1)
            await callback.message.answer(
                "✅ <b>Хабар юбориш якунланди</b>\n\n"
                f"👥 Жами: <b>{result.total}</b>\n"
                f"✅ Юборилди: <b>{result.sent}</b>\n"
                f"⚠️ Етиб бормади: <b>{result.failed}</b>\n"
                f"🚫 Ботни блоклаган/мавжуд эмас: <b>{result.unreachable}</b>",
                reply_markup=admin_panel_keyboard(
                    superadmin=True,
                    unanswered_count=unanswered.total,
                ),
            )
        return

    await callback.answer("Номаълум амал.", show_alert=True)


@router.message(AdminBroadcastStates.waiting_for_message)
async def admin_broadcast_message_received(message: Message, state: FSMContext) -> None:
    if not await is_superadmin(message.from_user.id):
        await state.clear()
        await message.answer(NOT_ADMIN_TEXT)
        return

    allowed = {
        ContentType.TEXT,
        ContentType.PHOTO,
        ContentType.VIDEO,
        ContentType.DOCUMENT,
        ContentType.ANIMATION,
    }
    if message.content_type not in allowed:
        await message.answer(
            "Бу турдаги хабар қўллаб-қувватланмайди. Матн, фото, видео, GIF ёки ҳужжат юборинг."
        )
        return

    data = await state.get_data()
    audience = data.get("broadcast_audience")
    if audience not in {"users", "admins"}:
        await state.clear()
        await message.answer("Хабар қабул қилувчилари топилмади. /admin орқали қайта бошланг.")
        return

    recipients = await list_broadcast_user_ids() if audience == "users" else await all_admin_ids()
    if not recipients:
        await state.clear()
        await message.answer("Қабул қилувчилар топилмади.")
        return

    await state.update_data(
        broadcast_source_chat_id=message.chat.id,
        broadcast_source_message_id=message.message_id,
    )
    await state.set_state(AdminBroadcastStates.waiting_for_confirmation)
    audience_label = "фойдаланувчилар" if audience == "users" else "админлар"
    await message.answer(
        "🔎 <b>Юборишдан олдин текширинг</b>\n\n"
        f"Қабул қилувчилар: <b>{len(recipients)} та {audience_label}</b>.\n"
        "Юқоридаги хабар айнан шу кўринишда юборилади.\n\n"
        "Юборишни тасдиқлайсизми?",
        reply_markup=admin_broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data.startswith(f"{ADMIN_PANEL_CALLBACK_PREFIX}:"))
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await is_admin(callback.from_user.id):
        await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
        return
    action = (callback.data or "").split(":", 1)[1] if ":" in (callback.data or "") else ""
    if action == "home":
        role = await get_admin_role(callback.from_user.id) or ROLE_ADMIN
        unanswered = await get_unanswered_appeal_summary(limit=1)
        if callback.message is not None:
            await callback.message.answer(
                f"👨‍💼 <b>Админ панель</b>\n\nРоль: <b>{role}</b>",
                reply_markup=admin_panel_keyboard(
                    superadmin=role == ROLE_SUPERADMIN,
                    unanswered_count=unanswered.total,
                ),
            )
    elif action == "broadcast":
        if not await is_superadmin(callback.from_user.id):
            await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
            return
        await state.clear()
        if callback.message is not None:
            await callback.message.answer(
                "📢 <b>Хабар юбориш</b>\n\nКимларга юборишни танланг:",
                reply_markup=admin_broadcast_audience_keyboard(),
            )
    elif action == "admins":
        if not await is_superadmin(callback.from_user.id):
            await callback.answer(NOT_ADMIN_TEXT, show_alert=True)
            return
        if callback.message is not None:
            await _send_admin_management(callback.message)
    elif action == "stats":
        appeals = await admin_appeal_counts()
        suggestions = await suggestion_counts() if await is_superadmin(callback.from_user.id) else {}
        text = (
            "📊 <b>Статистика</b>\n\n"
            f"🆕 Янги мурожаатлар: {appeals.get('NEW', 0)}\n"
            f"🟡 Кўриб чиқилмоқда: {appeals.get('IN_PROGRESS', 0)}\n"
            f"✅ Якунланган: {appeals.get('COMPLETED', 0)}\n"
            f"❌ Рад этилган: {appeals.get('REJECTED', 0)}"
        )
        if await is_superadmin(callback.from_user.id):
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
    elif action == "unanswered":
        rows = await list_unanswered_admin_appeals(limit=20)
        if not rows:
            await callback.message.answer("✅ Жавоб берилмаган мурожаатлар йўқ.")
        else:
            await callback.message.answer("⚠️ <b>Жавоб берилмаган мурожаатлар</b>")
            now = utcnow()
            for appeal in rows:
                expired = (
                    appeal.status == "IN_PROGRESS"
                    and appeal.claim_expires_at is not None
                    and appeal.claim_expires_at <= now
                )
                effective_status = "NEW" if appeal.status == "NEW" or expired else "IN_PROGRESS"
                markup = admin_reply_keyboard(appeal.id) if effective_status == "NEW" else None
                await callback.message.answer(
                    f"{html.escape(appeal.appeal_number)} — "
                    f"{appeal_status_text(effective_status, 'uz_cyrl')}",
                    reply_markup=markup,
                )
    elif action == "suggestions":
        if not await is_superadmin(callback.from_user.id):
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
    elif action == "web":
        try:
            url = await issue_login_url(callback.from_user.id)
        except Exception:
            logger.exception("Failed to create web admin login URL for %s", callback.from_user.id)
            await callback.answer("Web panel ҳозирча очилмади. Бироздан сўнг қайта урининг.", show_alert=True)
            return
        if callback.message is not None:
            await callback.message.answer(
                "🌐 Web admin panelга кириш учун қуйидаги тугмани босинг. "
                "Ҳавола 5 дақиқа амал қилади ва фақат бир марта ишлайди.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🌐 Web panelni ochish", url=url)]]
                ),
            )
    elif action == "search":
        await state.set_state(AdminStates.waiting_for_search)
        await callback.message.answer("🔎 Мурожаат рақамини киритинг. Масалан: MUR-000123")
    await callback.answer()


@router.message(AdminStates.waiting_for_search, F.text)
async def admin_search_message(message: Message, state: FSMContext) -> None:
    if not await is_admin(message.from_user.id):
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
    if not await is_admin(message.from_user.id):
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
