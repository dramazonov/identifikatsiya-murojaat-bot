from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.appeal_categories import is_valid_appeal_category
from app.handlers.admin import notify_admins_new_appeal
from app.i18n import t
from app.keyboards import (
    APPEAL_CANCEL_CALLBACK,
    APPEAL_CATEGORY_CALLBACK_PREFIX,
    appeal_category_keyboard,
    main_menu_keyboard,
    remove_keyboard,
)
from app.services.appeal_service import create_appeal
from app.services.shared_state import acquire_submission, finish_submission, is_rate_limited
from app.services.user_service import get_user_by_id, get_user_language
from app.services.validators import is_valid_appeal_text
from app.states import AppealSubmissionStates

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

RATE_LIMIT_MAX_SUBMISSIONS = 3
RATE_LIMIT_WINDOW_SECONDS = 60.0


async def _language(telegram_id: int, state: FSMContext) -> str:
    data = await state.get_data()
    return data.get("language_code") or await get_user_language(telegram_id)


async def start_appeal_submission(message: Message, state: FSMContext, language_code: str) -> None:
    """Citizen flow: choose direction -> write appeal -> submit immediately."""
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
    await state.set_state(AppealSubmissionStates.waiting_for_text)
    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not clear appeal category keyboard", exc_info=True)
        await callback.message.answer(
            t("appeal.text_prompt", language_code), reply_markup=remove_keyboard()
        )
    await callback.answer()


@router.message(AppealSubmissionStates.waiting_for_text, F.text)
async def appeal_text_received(message: Message, state: FSMContext) -> None:
    """Validate and save the appeal immediately after the citizen sends its text."""
    language_code = await _language(message.from_user.id, state)
    data = await state.get_data()
    category_code = data.get("category_code")
    appeal_text = message.text.strip()

    if not is_valid_appeal_category(category_code):
        await message.answer(t("common.invalid_action", language_code))
        return
    if not is_valid_appeal_text(appeal_text):
        await message.answer(t("appeal.invalid", language_code))
        return

    if await is_rate_limited(
        f"appeal_create:{message.from_user.id}",
        limit=RATE_LIMIT_MAX_SUBMISSIONS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    ):
        await message.answer(t("common.rate_limited", language_code))
        return

    # Telegram may redeliver the same update. The message identity makes the
    # final create operation idempotent without blocking genuinely new appeals.
    submission_key = f"appeal_create:{message.chat.id}:{message.message_id}"
    submission_token = await acquire_submission(submission_key)
    if submission_token is None:
        return

    try:
        appeal = await create_appeal(
            telegram_id=message.from_user.id,
            appeal_text=appeal_text,
            category_code=category_code,
            subject=None,
        )
    except Exception:
        await finish_submission(submission_key, submission_token, failed=True)
        logger.exception("Failed to save appeal for user %s", message.from_user.id)
        await message.answer(t("common.error", language_code))
        return

    await finish_submission(submission_key, submission_token)
    await state.clear()
    await message.answer(
        t("appeal.success_v2", language_code, appeal_number=appeal.appeal_number),
        reply_markup=main_menu_keyboard(language_code),
    )

    try:
        appeal_user = await get_user_by_id(appeal.user_id)
        if appeal_user is not None:
            await notify_admins_new_appeal(message.bot, appeal, appeal_user)
    except Exception:
        logger.exception("Failed to notify admins about appeal %s", appeal.appeal_number)


@router.message(AppealSubmissionStates.waiting_for_text)
async def appeal_text_invalid(message: Message, state: FSMContext) -> None:
    await message.answer(t("appeal.invalid", await _language(message.from_user.id, state)))


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
