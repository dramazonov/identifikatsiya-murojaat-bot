from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.appeal_categories import is_valid_appeal_category
from app.handlers.admin import notify_admins_new_appeal
from app.i18n import appeal_category_text, t
from app.keyboards import (
    APPEAL_ATTACHMENT_SKIP_CALLBACK,
    APPEAL_CANCEL_CALLBACK,
    APPEAL_CATEGORY_CALLBACK_PREFIX,
    APPEAL_CONFIRM_CALLBACK,
    appeal_attachment_keyboard,
    appeal_category_keyboard,
    appeal_confirmation_keyboard,
    main_menu_keyboard,
    remove_keyboard,
)
from app.services.appeal_service import create_appeal
from app.services.shared_state import acquire_submission, finish_submission, is_rate_limited
from app.services.telegram_delivery import split_text_for_telegram
from app.services.user_service import get_user_by_id, get_user_language
from app.services.validators import is_valid_appeal_subject, is_valid_appeal_text
from app.states import AppealSubmissionStates

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

MAX_PHOTO_BYTES = 10 * 1024 * 1024
MAX_PDF_BYTES = 20 * 1024 * 1024
RATE_LIMIT_MAX_SUBMISSIONS = 3
RATE_LIMIT_WINDOW_SECONDS = 60.0


async def _language(telegram_id: int, state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("language_code") or await get_user_language(telegram_id)


async def start_appeal_submission(message: Message, state: FSMContext, language_code: str) -> None:
    """Enter the Stage 22 structured appeal workflow."""
    await state.clear()
    await state.update_data(language_code=language_code)
    await state.set_state(AppealSubmissionStates.waiting_for_category)
    await message.answer(
        t("appeal.category_prompt", language_code),
        reply_markup=appeal_category_keyboard(language_code),
    )


@router.callback_query(
    AppealSubmissionStates.waiting_for_category,
    F.data.startswith(f"{APPEAL_CATEGORY_CALLBACK_PREFIX}:"),
)
async def appeal_category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    language_code = await _language(callback.from_user.id, state)
    code = callback.data.split(":", 1)[1] if callback.data and ":" in callback.data else None
    if not is_valid_appeal_category(code):
        await callback.answer(t("common.invalid_action", language_code), show_alert=True)
        return

    await state.update_data(category_code=code)
    await state.set_state(AppealSubmissionStates.waiting_for_subject)
    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not clear appeal category keyboard", exc_info=True)
        await callback.message.answer(t("appeal.subject_prompt", language_code), reply_markup=remove_keyboard())
    await callback.answer()


@router.message(AppealSubmissionStates.waiting_for_subject, F.text)
async def appeal_subject_received(message: Message, state: FSMContext) -> None:
    language_code = await _language(message.from_user.id, state)
    subject = message.text.strip()
    if not is_valid_appeal_subject(subject):
        await message.answer(t("appeal.subject_invalid", language_code))
        return
    await state.update_data(subject=subject)
    await state.set_state(AppealSubmissionStates.waiting_for_text)
    await message.answer(t("appeal.text_prompt", language_code))


@router.message(AppealSubmissionStates.waiting_for_subject)
async def appeal_subject_invalid(message: Message, state: FSMContext) -> None:
    await message.answer(t("appeal.subject_invalid", await _language(message.from_user.id, state)))


@router.message(AppealSubmissionStates.waiting_for_text, F.text)
async def appeal_text_received(message: Message, state: FSMContext) -> None:
    language_code = await _language(message.from_user.id, state)
    appeal_text = message.text.strip()
    if not is_valid_appeal_text(appeal_text):
        await message.answer(t("appeal.invalid", language_code))
        return
    await state.update_data(appeal_text=appeal_text)
    await state.set_state(AppealSubmissionStates.waiting_for_attachment)
    await message.answer(
        t("appeal.attachment_prompt", language_code),
        reply_markup=appeal_attachment_keyboard(language_code),
    )


@router.message(AppealSubmissionStates.waiting_for_text)
async def appeal_text_invalid(message: Message, state: FSMContext) -> None:
    await message.answer(t("appeal.invalid", await _language(message.from_user.id, state)))


async def _send_confirmation(message: Message, state: FSMContext, language_code: str) -> None:
    data = await state.get_data()
    attachment_type = data.get("attachment_type")
    attachment_key = {
        "PHOTO": "appeal.attachment.photo",
        "PDF": "appeal.attachment.pdf",
    }.get(attachment_type, "appeal.attachment.none")
    text = t(
        "appeal.confirmation",
        language_code,
        category=appeal_category_text(data.get("category_code"), language_code),
        subject=data.get("subject") or "—",
        attachment=t(attachment_key, language_code),
        appeal_text=data.get("appeal_text") or "—",
    )
    await state.set_state(AppealSubmissionStates.waiting_for_confirmation)
    chunks = split_text_for_telegram(text)
    keyboard = appeal_confirmation_keyboard(language_code)
    for index, chunk in enumerate(chunks):
        await message.answer(
            chunk,
            parse_mode=None,
            reply_markup=keyboard if index == len(chunks) - 1 else None,
        )


@router.callback_query(
    AppealSubmissionStates.waiting_for_attachment,
    F.data == APPEAL_ATTACHMENT_SKIP_CALLBACK,
)
async def appeal_attachment_skipped(callback: CallbackQuery, state: FSMContext) -> None:
    language_code = await _language(callback.from_user.id, state)
    await state.update_data(
        attachment_type=None,
        attachment_file_id=None,
        attachment_file_unique_id=None,
        attachment_name=None,
        attachment_size=None,
    )
    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not clear attachment keyboard", exc_info=True)
        await _send_confirmation(callback.message, state, language_code)
    await callback.answer()


@router.message(AppealSubmissionStates.waiting_for_attachment, F.photo)
async def appeal_photo_received(message: Message, state: FSMContext) -> None:
    language_code = await _language(message.from_user.id, state)
    photo = message.photo[-1]
    file_size = int(photo.file_size or 0)
    if file_size > MAX_PHOTO_BYTES:
        await message.answer(
            t("appeal.attachment_too_large", language_code),
            reply_markup=appeal_attachment_keyboard(language_code),
        )
        return
    await state.update_data(
        attachment_type="PHOTO",
        attachment_file_id=photo.file_id,
        attachment_file_unique_id=photo.file_unique_id,
        attachment_name=None,
        attachment_size=file_size or None,
    )
    await _send_confirmation(message, state, language_code)


@router.message(AppealSubmissionStates.waiting_for_attachment, F.document)
async def appeal_pdf_received(message: Message, state: FSMContext) -> None:
    language_code = await _language(message.from_user.id, state)
    document = message.document
    filename = document.file_name or ""
    if document.mime_type != "application/pdf" or (filename and not filename.lower().endswith(".pdf")):
        await message.answer(
            t("appeal.attachment_invalid", language_code),
            reply_markup=appeal_attachment_keyboard(language_code),
        )
        return
    file_size = int(document.file_size or 0)
    if file_size > MAX_PDF_BYTES:
        await message.answer(
            t("appeal.attachment_too_large", language_code),
            reply_markup=appeal_attachment_keyboard(language_code),
        )
        return
    await state.update_data(
        attachment_type="PDF",
        attachment_file_id=document.file_id,
        attachment_file_unique_id=document.file_unique_id,
        attachment_name=filename or None,
        attachment_size=file_size or None,
    )
    await _send_confirmation(message, state, language_code)


@router.message(AppealSubmissionStates.waiting_for_attachment)
async def appeal_attachment_invalid(message: Message, state: FSMContext) -> None:
    language_code = await _language(message.from_user.id, state)
    await message.answer(
        t("appeal.attachment_invalid", language_code),
        reply_markup=appeal_attachment_keyboard(language_code),
    )


@router.callback_query(F.data == APPEAL_CANCEL_CALLBACK)
async def appeal_cancelled(callback: CallbackQuery, state: FSMContext) -> None:
    language_code = await _language(callback.from_user.id, state)
    await state.clear()
    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not clear cancelled appeal keyboard", exc_info=True)
        await callback.message.answer(
            t("appeal.cancelled", language_code),
            reply_markup=main_menu_keyboard(language_code),
        )
    await callback.answer()


@router.callback_query(
    AppealSubmissionStates.waiting_for_confirmation,
    F.data == APPEAL_CONFIRM_CALLBACK,
)
async def appeal_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    language_code = await _language(callback.from_user.id, state)
    data = await state.get_data()
    category_code = data.get("category_code")
    subject = (data.get("subject") or "").strip()
    appeal_text = (data.get("appeal_text") or "").strip()
    if not (
        is_valid_appeal_category(category_code)
        and is_valid_appeal_subject(subject)
        and is_valid_appeal_text(appeal_text)
    ):
        await callback.answer(t("common.invalid_action", language_code), show_alert=True)
        return

    if await is_rate_limited(
        f"appeal_create:{callback.from_user.id}",
        limit=RATE_LIMIT_MAX_SUBMISSIONS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    ):
        await callback.answer(t("common.rate_limited", language_code), show_alert=True)
        return

    submission_key = f"appeal_confirm:{callback.from_user.id}:{callback.id}"
    submission_token = await acquire_submission(submission_key)
    if submission_token is None:
        return

    try:
        appeal = await create_appeal(
            callback.from_user.id,
            appeal_text,
            category_code=category_code,
            subject=subject,
            attachment_type=data.get("attachment_type"),
            attachment_file_id=data.get("attachment_file_id"),
            attachment_file_unique_id=data.get("attachment_file_unique_id"),
            attachment_name=data.get("attachment_name"),
            attachment_size=data.get("attachment_size"),
        )
    except Exception:
        await finish_submission(submission_key, submission_token, failed=True)
        logger.exception("Failed to save Stage 22 appeal for user %s", callback.from_user.id)
        await callback.answer(t("common.error", language_code), show_alert=True)
        return

    await finish_submission(submission_key, submission_token)
    await state.clear()
    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not clear appeal confirmation keyboard", exc_info=True)
        await callback.message.answer(
            t("appeal.success_v2", language_code, appeal_number=appeal.appeal_number),
            reply_markup=main_menu_keyboard(language_code),
        )

    try:
        appeal_user = await get_user_by_id(appeal.user_id)
        if appeal_user is not None:
            await notify_admins_new_appeal(callback.bot, appeal, appeal_user)
    except Exception:
        logger.exception("Failed to notify admins about appeal %s", appeal.appeal_number)
    await callback.answer()


@router.message(AppealSubmissionStates.waiting_for_confirmation)
async def appeal_confirmation_invalid(message: Message, state: FSMContext) -> None:
    language_code = await _language(message.from_user.id, state)
    await message.answer(
        t("common.invalid_action", language_code),
        reply_markup=appeal_confirmation_keyboard(language_code),
    )
