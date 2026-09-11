from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.regions import DISTRICTS, REGIONS
from app.handlers.admin import notify_admins_new_appeal, notify_admins_new_suggestion
from app.handlers.appeal_flow import start_appeal_submission
from app.i18n import DEFAULT_LANGUAGE, normalize_language, t
from app.keyboards import (
    LANGUAGE_CALLBACK_PREFIX,
    contact_keyboard,
    district_keyboard,
    language_keyboard,
    main_menu_keyboard,
    menu_texts,
    region_keyboard,
    remove_keyboard,
)
from app.services.appeal_service import create_appeal
from app.services.shared_state import acquire_submission, finish_submission, is_rate_limited
from app.services.suggestion_service import create_suggestion
from app.services.user_service import (
    PHONE_VERIFICATION_SOURCE_TELEGRAM,
    get_user_by_id,
    get_user_by_telegram_id,
    get_user_language,
    is_registration_complete,
    save_user,
    save_user_location,
    set_user_language,
)
from app.services.validators import (
    is_valid_appeal_text,
    is_valid_full_name,
    is_valid_suggestion_text,
    normalize_phone,
)
from app.states import Registration, SuggestionStates

logger = logging.getLogger(__name__)
router = Router()

INTENT_APPEAL = "appeal"
INTENT_SUGGESTION = "suggestion"
RATE_LIMIT_MAX_SUBMISSIONS = 3
RATE_LIMIT_WINDOW_SECONDS = 60.0


def _lang_from_data(data: dict) -> str:
    return normalize_language(data.get("language_code"))


async def _language_for_user(telegram_id: int, state: FSMContext | None = None) -> str:
    if state is not None:
        data = await state.get_data()
        if data.get("language_code"):
            return _lang_from_data(data)
    return await get_user_language(telegram_id)


async def _route_incomplete_registration(
    message: Message,
    state: FSMContext,
    *,
    language_code: str,
    telegram_id: int,
    intent: str | None = None,
) -> None:
    user = await get_user_by_telegram_id(telegram_id)
    await state.update_data(language_code=language_code)
    if intent:
        await state.update_data(intent=intent)

    if user is None or not user.full_name:
        await state.set_state(Registration.waiting_for_full_name)
        await message.answer(t("registration.ask_full_name", language_code), reply_markup=remove_keyboard())
        return

    if not user.phone or not user.phone_verified:
        await state.set_state(Registration.waiting_for_phone)
        await message.answer(
            t("registration.ask_phone", language_code),
            reply_markup=contact_keyboard(language_code),
        )
        return

    if not user.region or not user.district:
        await state.set_state(Registration.waiting_for_region)
        await message.answer(t("registration.ask_region", language_code), reply_markup=region_keyboard())
        return

    await _finish_registration_flow(message, state, language_code=language_code, intent=intent)


async def _finish_registration_flow(
    message: Message,
    state: FSMContext,
    *,
    language_code: str,
    intent: str | None = None,
) -> None:
    if intent == INTENT_APPEAL:
        await start_appeal_submission(message, state, language_code)
        return

    if intent == INTENT_SUGGESTION:
        await state.set_state(SuggestionStates.waiting_for_suggestion)
        await message.answer(t("suggestion.ask", language_code), reply_markup=remove_keyboard())
        return

    await state.clear()
    await message.answer(t("menu.title", language_code), reply_markup=main_menu_keyboard(language_code))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    submission_key = f"start:{message.chat.id}:{message.message_id}"
    submission_token = await acquire_submission(submission_key)
    if submission_token is None:
        logger.info("Ignoring duplicate delivery of /start message %s", message.message_id)
        return

    succeeded = False
    try:
        await state.clear()
        await state.set_state(Registration.waiting_for_language)
        await message.answer(
            t("language.choose", DEFAULT_LANGUAGE),
            reply_markup=language_keyboard(),
        )
        succeeded = True
    finally:
        await finish_submission(submission_key, submission_token, failed=not succeeded)


@router.callback_query(F.data.startswith(f"{LANGUAGE_CALLBACK_PREFIX}:"))
async def process_language_selected(callback: CallbackQuery, state: FSMContext) -> None:
    language_code = normalize_language(callback.data.split(":", 1)[1] if ":" in callback.data else None)
    if callback.data != f"{LANGUAGE_CALLBACK_PREFIX}:{language_code}":
        await callback.answer("Invalid language", show_alert=True)
        return

    user = await set_user_language(
        callback.from_user.id,
        callback.from_user.username,
        language_code,
    )
    await state.clear()
    await state.update_data(language_code=language_code)

    if callback.message is not None:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not clear language keyboard", exc_info=True)

        if is_registration_complete(user):
            await state.clear()
            await callback.message.answer(
                t("menu.title", language_code), reply_markup=main_menu_keyboard(language_code)
            )
        else:
            await _route_incomplete_registration(
                callback.message,
                state,
                language_code=language_code,
                telegram_id=callback.from_user.id,
            )
    await callback.answer()


@router.message(F.text.in_(menu_texts("appeal")))
async def menu_start_appeal(message: Message, state: FSMContext) -> None:
    await state.clear()
    language_code = await get_user_language(message.from_user.id)
    user = await get_user_by_telegram_id(message.from_user.id)
    if is_registration_complete(user):
        await start_appeal_submission(message, state, language_code)
        return

    await _route_incomplete_registration(
        message,
        state,
        language_code=language_code,
        telegram_id=message.from_user.id,
        intent=INTENT_APPEAL,
    )


@router.message(F.text.in_(menu_texts("suggestion")))
async def menu_start_suggestion(message: Message, state: FSMContext) -> None:
    await state.clear()
    language_code = await get_user_language(message.from_user.id)
    user = await get_user_by_telegram_id(message.from_user.id)
    if is_registration_complete(user):
        await state.update_data(language_code=language_code)
        await state.set_state(SuggestionStates.waiting_for_suggestion)
        await message.answer(t("suggestion.ask", language_code), reply_markup=remove_keyboard())
        return

    await _route_incomplete_registration(
        message,
        state,
        language_code=language_code,
        telegram_id=message.from_user.id,
        intent=INTENT_SUGGESTION,
    )


@router.message(Registration.waiting_for_full_name, F.text)
async def process_full_name(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    full_name = message.text.strip()
    if not is_valid_full_name(full_name):
        await message.answer(t("registration.invalid_full_name", language_code))
        return

    await state.update_data(full_name=full_name, language_code=language_code)
    await state.set_state(Registration.waiting_for_phone)
    await message.answer(t("registration.ask_phone", language_code), reply_markup=contact_keyboard(language_code))


@router.message(Registration.waiting_for_full_name)
async def process_full_name_invalid(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    await message.answer(t("registration.invalid_full_name", language_code))


@router.message(Registration.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    contact = message.contact
    if contact.user_id is None or contact.user_id != message.from_user.id:
        await message.answer(
            t("registration.wrong_contact", language_code),
            reply_markup=contact_keyboard(language_code),
        )
        return

    phone = normalize_phone(contact.phone_number)
    if phone is None:
        await message.answer(
            t("registration.invalid_phone", language_code),
            reply_markup=contact_keyboard(language_code),
        )
        return

    await _finish_verified_phone(message, state, phone, language_code)


@router.message(Registration.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    await message.answer(
        t("registration.manual_phone_rejected", language_code),
        reply_markup=contact_keyboard(language_code),
    )


@router.message(Registration.waiting_for_phone)
async def process_phone_invalid(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    await message.answer(
        t("registration.manual_phone_rejected", language_code),
        reply_markup=contact_keyboard(language_code),
    )


async def _finish_verified_phone(
    message: Message, state: FSMContext, phone: str, language_code: str
) -> None:
    data = await state.get_data()
    existing = await get_user_by_telegram_id(message.from_user.id)
    full_name = data.get("full_name") or (existing.full_name if existing else None)
    if not full_name:
        await state.set_state(Registration.waiting_for_full_name)
        await message.answer(t("registration.ask_full_name", language_code), reply_markup=remove_keyboard())
        return

    try:
        user = await save_user(
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username,
            full_name=full_name,
            phone=phone,
            phone_verified=True,
            phone_verification_source=PHONE_VERIFICATION_SOURCE_TELEGRAM,
            language_code=language_code,
        )
    except Exception:
        logger.exception("Failed to save verified phone for user %s", message.from_user.id)
        await message.answer(t("common.error", language_code), reply_markup=contact_keyboard(language_code))
        return

    await message.answer(t("registration.phone_accepted", language_code), reply_markup=remove_keyboard())
    intent = data.get("intent")
    if user.region and user.district:
        await _finish_registration_flow(
            message, state, language_code=language_code, intent=intent
        )
        return

    await state.set_state(Registration.waiting_for_region)
    await message.answer(t("registration.ask_region", language_code), reply_markup=region_keyboard())


@router.callback_query(Registration.waiting_for_region, F.data.startswith("region:"))
async def process_region_selected(callback: CallbackQuery, state: FSMContext) -> None:
    language_code = await _language_for_user(callback.from_user.id, state)
    region_id = _parse_index(callback.data.split(":")[1] if ":" in callback.data else "")
    if region_id is None or region_id not in range(len(REGIONS)):
        await callback.answer(t("common.error", language_code), show_alert=True)
        return

    await state.update_data(region_id=region_id, region_name=REGIONS[region_id], language_code=language_code)
    await state.set_state(Registration.waiting_for_district)
    if callback.message is not None:
        await callback.message.edit_text(
            t("registration.ask_district", language_code),
            reply_markup=district_keyboard(region_id),
        )
    await callback.answer()


@router.message(Registration.waiting_for_region)
async def process_region_invalid(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    await message.answer(t("registration.invalid_region", language_code), reply_markup=region_keyboard())


@router.callback_query(Registration.waiting_for_district, F.data.startswith("district:"))
async def process_district_selected(callback: CallbackQuery, state: FSMContext) -> None:
    language_code = await _language_for_user(callback.from_user.id, state)
    parts = callback.data.split(":")
    region_id = _parse_index(parts[1]) if len(parts) > 1 else None
    district_id = _parse_index(parts[2]) if len(parts) > 2 else None
    data = await state.get_data()
    expected_region_id = data.get("region_id")

    if (
        region_id is None
        or district_id is None
        or region_id != expected_region_id
        or region_id not in DISTRICTS
        or district_id not in range(len(DISTRICTS[region_id]))
    ):
        await callback.answer(t("common.error", language_code), show_alert=True)
        return

    try:
        await save_user_location(
            telegram_id=callback.from_user.id,
            region=REGIONS[region_id],
            district=DISTRICTS[region_id][district_id],
        )
    except Exception:
        logger.exception("Failed to save location for user %s", callback.from_user.id)
        await callback.answer(t("common.error", language_code), show_alert=True)
        return

    intent = data.get("intent")
    if callback.message is not None:
        await callback.message.edit_text(t("registration.location_saved", language_code))
        await _finish_registration_flow(
            callback.message, state, language_code=language_code, intent=intent
        )
    await callback.answer()


@router.message(Registration.waiting_for_district)
async def process_district_invalid(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    data = await state.get_data()
    region_id = data.get("region_id")
    if region_id not in DISTRICTS:
        await state.set_state(Registration.waiting_for_region)
        await message.answer(t("registration.ask_region", language_code), reply_markup=region_keyboard())
        return
    await message.answer(
        t("registration.invalid_district", language_code), reply_markup=district_keyboard(region_id)
    )


async def process_appeal_text(message: Message, state: FSMContext) -> None:
    """Legacy regression hook for the pre-Stage-22 direct-text path.

    It is intentionally not registered as a router handler anymore. Stage 22
    uses app.handlers.appeal_flow, but keeping this function preserves the
    existing duplicate-delivery/lease regression tests around the low-level
    create operation.
    """
    language_code = await _language_for_user(message.from_user.id, state)
    appeal_text = message.text.strip()
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

    submission_key = f"appeal_create:{message.chat.id}:{message.message_id}"
    submission_token = await acquire_submission(submission_key)
    if submission_token is None:
        return

    try:
        appeal = await create_appeal(telegram_id=message.from_user.id, appeal_text=appeal_text)
    except Exception:
        await finish_submission(submission_key, submission_token, failed=True)
        logger.exception("Failed to save appeal for user %s", message.from_user.id)
        await message.answer(t("common.error", language_code))
        return

    await finish_submission(submission_key, submission_token)
    await state.clear()
    await message.answer(
        t("appeal.success", language_code, appeal_number=appeal.appeal_number),
        reply_markup=main_menu_keyboard(language_code),
    )
    try:
        appeal_user = await get_user_by_id(appeal.user_id)
        if appeal_user is not None:
            await notify_admins_new_appeal(message.bot, appeal, appeal_user)
    except Exception:
        logger.exception("Failed to notify admins about appeal %s", appeal.appeal_number)


@router.message(SuggestionStates.waiting_for_suggestion, F.text)
async def process_suggestion_text(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    suggestion_text = message.text.strip()
    if not is_valid_suggestion_text(suggestion_text):
        await message.answer(t("suggestion.invalid", language_code))
        return

    if await is_rate_limited(
        f"suggestion_create:{message.from_user.id}",
        limit=RATE_LIMIT_MAX_SUBMISSIONS,
        window_seconds=RATE_LIMIT_WINDOW_SECONDS,
    ):
        await message.answer(t("common.rate_limited", language_code))
        return

    submission_key = f"suggestion_create:{message.chat.id}:{message.message_id}"
    submission_token = await acquire_submission(submission_key)
    if submission_token is None:
        return

    try:
        suggestion = await create_suggestion(
            telegram_id=message.from_user.id, suggestion_text=suggestion_text
        )
    except Exception:
        await finish_submission(submission_key, submission_token, failed=True)
        logger.exception("Failed to save suggestion for user %s", message.from_user.id)
        await message.answer(t("common.error", language_code))
        return

    await finish_submission(submission_key, submission_token)
    await state.clear()
    await message.answer(
        t("suggestion.success", language_code, suggestion_number=suggestion.suggestion_number),
        reply_markup=main_menu_keyboard(language_code),
    )
    try:
        suggestion_user = await get_user_by_id(suggestion.user_id)
        if suggestion_user is not None:
            await notify_admins_new_suggestion(message.bot, suggestion, suggestion_user)
    except Exception:
        logger.exception("Failed to notify admins about suggestion %s", suggestion.suggestion_number)


@router.message(SuggestionStates.waiting_for_suggestion)
async def process_suggestion_invalid(message: Message, state: FSMContext) -> None:
    language_code = await _language_for_user(message.from_user.id, state)
    await message.answer(t("suggestion.invalid", language_code))


def _parse_index(raw: str) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
