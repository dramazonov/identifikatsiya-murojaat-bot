from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.regions import DISTRICTS, REGIONS
from app.handlers.admin import notify_admins_new_appeal, notify_admins_new_suggestion
from app.keyboards import (
    MENU_APPEAL,
    MENU_SUGGESTION,
    contact_keyboard,
    district_keyboard,
    main_menu_keyboard,
    region_keyboard,
    remove_keyboard,
)
from app.services.appeal_service import create_appeal
from app.services.suggestion_service import create_suggestion
from app.services.user_service import (
    get_user_by_id,
    get_user_by_telegram_id,
    save_user,
    save_user_location,
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

# Tracks, across the shared registration flow (full name -> phone -> region ->
# district), what the user was registering *for* -- so that once the flow
# finishes, they land on the right next step (appeal or suggestion text)
# instead of always landing on the appeal step. Stored under the "intent" key
# in FSM data; missing/unset defaults to INTENT_APPEAL to preserve the
# pre-existing behavior of /start and the "📨 Мурожаат юбориш" button.
INTENT_APPEAL = "appeal"
INTENT_SUGGESTION = "suggestion"

WELCOME_TEXT = (
    "Assalomu alaykum!\n\n"
    "Identifikatsiya markazining murojaatlar botiga xush kelibsiz.\n\n"
    "Илтимос, Ф.И.Ш.ингизни киритинг:"
)
WELCOME_BACK_TEXT = "🏠 АСОСИЙ МЕНЮ\n\nКеракли бўлимни танланг:"
INVALID_FULL_NAME_TEXT = "Илтимос, тўлиқ исм-фамилиянгизни киритинг (камида 5 та белги)."
ASK_PHONE_TEXT = "Телефон рақамингизни юборинг:"
INVALID_PHONE_TEXT = (
    "Телефон рақами нотўғри форматда. Илтимос, қайта киритинг ёки тугма орқали юборинг."
)
PHONE_ACCEPTED_TEXT = "✅ Телефон рақами қабул қилинди."
ASK_REGION_TEXT = "Вилоятингизни танланг:"
INVALID_REGION_TEXT = "Илтимос, вилоятни тугмалар орқали танланг:"
ASK_DISTRICT_TEXT = "Туман ёки шаҳарни танланг:"
INVALID_DISTRICT_TEXT = "Илтимос, туман ёки шаҳарни тугмалар орқали танланг:"
LOCATION_SUCCESS_TEXT = "Ҳудуд маълумотлари қабул қилинди."
ASK_APPEAL_TEXT = "Мурожаатингизни ёзинг:"
INVALID_APPEAL_TEXT = (
    "Мурожаат матни нотўғри. Илтимос, камида 5, кўпи билан 4000 та белгидан "
    "иборат матн киритинг."
)
APPEAL_SUCCESS_TEXT_TEMPLATE = (
    "Мурожаатингиз қабул қилинди.\n\n"
    "Мурожаат рақами: {appeal_number}\n\n"
    "Мурожаатингиз масъул ходимлар томонидан кўриб чиқилади."
)
ASK_SUGGESTION_TEXT = "Таклифингизни ёзинг:"
INVALID_SUGGESTION_TEXT = (
    "Таклиф матни нотўғри. Илтимос, камида 5, кўпи билан 4000 та белгидан "
    "иборат матн киритинг."
)
SUGGESTION_SUCCESS_TEXT_TEMPLATE = (
    "✅ Таклифингиз қабул қилинди.\n\n"
    "Таклиф рақами: {suggestion_number}"
)
GENERIC_ERROR_TEXT = "Хатолик юз берди. Илтимос, бироздан сўнг қайта уриниб кўринг."
CALLBACK_ERROR_TEXT = "Хатолик юз берди. Илтимос, /start орқали қайта бошланг."


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()

    user = await get_user_by_telegram_id(message.from_user.id)
    if user is not None:
        await message.answer(WELCOME_BACK_TEXT, reply_markup=main_menu_keyboard())
        return

    # New user: keep the existing registration flow unchanged.
    await state.set_state(Registration.waiting_for_full_name)
    await message.answer(WELCOME_TEXT)


@router.message(F.text == MENU_APPEAL)
async def menu_start_appeal(message: Message, state: FSMContext) -> None:
    # Reachable from any FSM state -- registered before the state-specific
    # catch-alls below so pressing this button always takes priority.
    await state.clear()

    user = await get_user_by_telegram_id(message.from_user.id)
    if user is not None and user.full_name and user.phone and user.region and user.district:
        # Already registered: go straight to composing the appeal, no need
        # to re-ask Ф.И.Ш./phone/region/district.
        await state.set_state(Registration.waiting_for_appeal)
        await message.answer(ASK_APPEAL_TEXT)
        return

    await state.set_state(Registration.waiting_for_full_name)
    await message.answer(WELCOME_TEXT)


@router.message(F.text == MENU_SUGGESTION)
async def menu_start_suggestion(message: Message, state: FSMContext) -> None:
    # Reachable from any FSM state -- registered before the state-specific
    # catch-alls below so pressing this button always takes priority.
    await state.clear()

    user = await get_user_by_telegram_id(message.from_user.id)
    if user is not None and user.full_name and user.phone and user.region and user.district:
        # Already registered: go straight to composing the suggestion, no need
        # to re-ask Ф.И.Ш./phone/region/district.
        await state.set_state(SuggestionStates.waiting_for_suggestion)
        await message.answer(ASK_SUGGESTION_TEXT)
        return

    await state.update_data(intent=INTENT_SUGGESTION)
    await state.set_state(Registration.waiting_for_full_name)
    await message.answer(WELCOME_TEXT)


@router.message(Registration.waiting_for_full_name, F.text)
async def process_full_name(message: Message, state: FSMContext) -> None:
    full_name = message.text.strip()

    if not is_valid_full_name(full_name):
        await message.answer(INVALID_FULL_NAME_TEXT)
        return

    await state.update_data(full_name=full_name)
    await state.set_state(Registration.waiting_for_phone)
    await message.answer(ASK_PHONE_TEXT, reply_markup=contact_keyboard())


@router.message(Registration.waiting_for_full_name)
async def process_full_name_invalid(message: Message) -> None:
    await message.answer(INVALID_FULL_NAME_TEXT)


@router.message(Registration.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.contact.phone_number)

    if phone is None:
        await message.answer(INVALID_PHONE_TEXT, reply_markup=contact_keyboard())
        return

    await _finish_registration(message, state, phone)


@router.message(Registration.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext) -> None:
    phone = normalize_phone(message.text)

    if phone is None:
        await message.answer(INVALID_PHONE_TEXT, reply_markup=contact_keyboard())
        return

    await _finish_registration(message, state, phone)


@router.message(Registration.waiting_for_phone)
async def process_phone_invalid(message: Message) -> None:
    await message.answer(INVALID_PHONE_TEXT, reply_markup=contact_keyboard())


async def _finish_registration(message: Message, state: FSMContext, phone: str) -> None:
    data = await state.get_data()
    full_name = data.get("full_name", "")

    try:
        await save_user(
            telegram_id=message.from_user.id,
            telegram_username=message.from_user.username,
            full_name=full_name,
            phone=phone,
        )
    except Exception:
        logger.exception("Failed to save user %s to the database", message.from_user.id)
        await message.answer(GENERIC_ERROR_TEXT, reply_markup=contact_keyboard())
        return

    await state.set_state(Registration.waiting_for_region)

    # Telegram only clears a reply keyboard (the "📱 Телефон рақамини
    # юбориш" contact button) when a message explicitly carries
    # ReplyKeyboardRemove -- sending the inline region keyboard on its own
    # would leave that button lingering on screen. So remove it first, in
    # its own message, then show the region prompt with its inline keyboard.
    await message.answer(PHONE_ACCEPTED_TEXT, reply_markup=remove_keyboard())
    await message.answer(ASK_REGION_TEXT, reply_markup=region_keyboard())


@router.callback_query(Registration.waiting_for_region, F.data.startswith("region:"))
async def process_region_selected(callback: CallbackQuery, state: FSMContext) -> None:
    region_id = _parse_index(callback.data.split(":")[1] if ":" in callback.data else "")

    if region_id is None or region_id not in range(len(REGIONS)):
        await callback.answer(CALLBACK_ERROR_TEXT, show_alert=True)
        return

    region_name = REGIONS[region_id]
    await state.update_data(region_id=region_id, region_name=region_name)
    await state.set_state(Registration.waiting_for_district)

    if callback.message is not None:
        await callback.message.edit_text(ASK_DISTRICT_TEXT, reply_markup=district_keyboard(region_id))
    await callback.answer()


@router.message(Registration.waiting_for_region)
async def process_region_invalid(message: Message) -> None:
    await message.answer(INVALID_REGION_TEXT, reply_markup=region_keyboard())


@router.callback_query(Registration.waiting_for_district, F.data.startswith("district:"))
async def process_district_selected(callback: CallbackQuery, state: FSMContext) -> None:
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
        await callback.answer(CALLBACK_ERROR_TEXT, show_alert=True)
        return

    region_name = REGIONS[region_id]
    district_name = DISTRICTS[region_id][district_id]

    try:
        await save_user_location(
            telegram_id=callback.from_user.id,
            region=region_name,
            district=district_name,
        )
    except Exception:
        logger.exception("Failed to save location for user %s", callback.from_user.id)
        await callback.answer(CALLBACK_ERROR_TEXT, show_alert=True)
        return

    # Route to whichever flow started registration (appeal composing by
    # default, matching the pre-existing behavior of /start and the
    # "📨 Мурожаат юбориш" button; suggestion composing when the user got here
    # via "💡 Таклиф юбориш" -- see INTENT_SUGGESTION).
    intent = data.get("intent", INTENT_APPEAL)

    if intent == INTENT_SUGGESTION:
        await state.set_state(SuggestionStates.waiting_for_suggestion)
        next_prompt = ASK_SUGGESTION_TEXT
    else:
        await state.set_state(Registration.waiting_for_appeal)
        next_prompt = ASK_APPEAL_TEXT

    if callback.message is not None:
        await callback.message.edit_text(LOCATION_SUCCESS_TEXT)
        await callback.message.answer(next_prompt)
    await callback.answer()


@router.message(Registration.waiting_for_district)
async def process_district_invalid(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    region_id = data.get("region_id")

    if region_id not in DISTRICTS:
        # Defensive fallback: state is inconsistent, restart from the region step.
        await state.set_state(Registration.waiting_for_region)
        await message.answer(ASK_REGION_TEXT, reply_markup=region_keyboard())
        return

    await message.answer(INVALID_DISTRICT_TEXT, reply_markup=district_keyboard(region_id))


@router.message(Registration.waiting_for_appeal, F.text)
async def process_appeal_text(message: Message, state: FSMContext) -> None:
    appeal_text = message.text.strip()

    if not is_valid_appeal_text(appeal_text):
        await message.answer(INVALID_APPEAL_TEXT)
        return

    try:
        appeal = await create_appeal(
            telegram_id=message.from_user.id,
            appeal_text=appeal_text,
        )
    except Exception:
        logger.exception("Failed to save appeal for user %s", message.from_user.id)
        await message.answer(GENERIC_ERROR_TEXT)
        return

    await state.clear()
    await message.answer(
        APPEAL_SUCCESS_TEXT_TEMPLATE.format(appeal_number=appeal.appeal_number),
        reply_markup=main_menu_keyboard(),
    )

    # Notifying admins is best-effort: the citizen has already received their
    # success message above, so a failure here must never surface to them.
    try:
        appeal_user = await get_user_by_id(appeal.user_id)
        if appeal_user is not None:
            await notify_admins_new_appeal(message.bot, appeal, appeal_user)
        else:
            logger.error(
                "User %s not found while notifying admins about appeal %s",
                appeal.user_id,
                appeal.appeal_number,
            )
    except Exception:
        logger.exception("Failed to notify admins about appeal %s", appeal.appeal_number)


@router.message(Registration.waiting_for_appeal)
async def process_appeal_invalid(message: Message) -> None:
    await message.answer(INVALID_APPEAL_TEXT)


@router.message(SuggestionStates.waiting_for_suggestion, F.text)
async def process_suggestion_text(message: Message, state: FSMContext) -> None:
    suggestion_text = message.text.strip()

    if not is_valid_suggestion_text(suggestion_text):
        await message.answer(INVALID_SUGGESTION_TEXT)
        return

    try:
        suggestion = await create_suggestion(
            telegram_id=message.from_user.id,
            suggestion_text=suggestion_text,
        )
    except Exception:
        logger.exception("Failed to save suggestion for user %s", message.from_user.id)
        await message.answer(GENERIC_ERROR_TEXT)
        return

    await state.clear()
    await message.answer(
        SUGGESTION_SUCCESS_TEXT_TEMPLATE.format(suggestion_number=suggestion.suggestion_number),
        reply_markup=main_menu_keyboard(),
    )

    # Notifying admins is best-effort: the citizen has already received their
    # success message above, so a failure here must never surface to them.
    try:
        suggestion_user = await get_user_by_id(suggestion.user_id)
        if suggestion_user is not None:
            await notify_admins_new_suggestion(message.bot, suggestion, suggestion_user)
        else:
            logger.error(
                "User %s not found while notifying admins about suggestion %s",
                suggestion.user_id,
                suggestion.suggestion_number,
            )
    except Exception:
        logger.exception("Failed to notify admins about suggestion %s", suggestion.suggestion_number)


@router.message(SuggestionStates.waiting_for_suggestion)
async def process_suggestion_invalid(message: Message) -> None:
    await message.answer(INVALID_SUGGESTION_TEXT)


def _parse_index(raw: str) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
