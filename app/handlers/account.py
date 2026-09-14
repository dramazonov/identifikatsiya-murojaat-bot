from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.regions import localize_location_value

from app.i18n import (
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    appeal_category_text,
    appeal_status_text,
    normalize_language,
    t,
)
from app.keyboards import (
    MY_APPEALS_CALLBACK_PREFIX,
    SETTINGS_CALLBACK_PREFIX,
    SETTINGS_LANGUAGE_CALLBACK_PREFIX,
    contact_keyboard,
    main_menu_keyboard,
    menu_texts,
    my_appeals_keyboard,
    settings_keyboard,
    settings_language_keyboard,
)
from app.services.appeal_service import (
    count_user_appeals,
    get_user_appeal_by_id,
    list_user_appeals,
)
from app.services.datetime_utils import format_tashkent
from app.services.telegram_delivery import split_text_for_telegram
from app.services.user_service import (
    get_user_by_telegram_id,
    get_user_language,
    set_user_language,
    update_verified_phone,
)
from app.services.validators import normalize_phone
from app.states import AccountSettings

logger = logging.getLogger(__name__)
router = Router()
# Profile/appeal history contains personal data; never render it in groups/channels.
router.message.filter(F.chat.type == ChatType.PRIVATE)
router.callback_query.filter(F.message.chat.type == ChatType.PRIVATE)

APPEALS_PER_PAGE = 5


def _parse_non_negative_int(raw: str) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _status_text(status: str, language_code: str) -> str:
    # Never leak internal DB codes (NEW/COMPLETED/...) to citizens.
    return appeal_status_text(status, language_code)


def _status_emoji(status: str) -> str:
    return {
        "NEW": "🆕",
        "IN_PROGRESS": "🟡",
        "WAITING_FOR_USER": "⏳",
        "COMPLETED": "✅",
        "REJECTED": "⛔",
    }.get(status, "📌")


async def _appeals_page_payload(telegram_id: int, language_code: str, page: int):
    total = await count_user_appeals(telegram_id)
    if total == 0:
        return None

    total_pages = max(1, (total + APPEALS_PER_PAGE - 1) // APPEALS_PER_PAGE)
    page = min(max(page, 0), total_pages - 1)
    appeals = await list_user_appeals(
        telegram_id,
        offset=page * APPEALS_PER_PAGE,
        limit=APPEALS_PER_PAGE,
    )
    text = t(
        "my_appeals.title",
        language_code,
        current_page=page + 1,
        total_pages=total_pages,
        total=total,
    )
    keyboard = my_appeals_keyboard(
        appeals,
        page=page,
        total_pages=total_pages,
        language_code=language_code,
        status_emoji=_status_emoji,
        status_text=_status_text,
    )
    return text, keyboard


@router.message(F.text.in_(menu_texts("my_appeals")))
async def menu_my_appeals(message: Message, state: FSMContext) -> None:
    await state.clear()
    language_code = await get_user_language(message.from_user.id)
    payload = await _appeals_page_payload(message.from_user.id, language_code, 0)
    if payload is None:
        await message.answer(
            t("my_appeals.empty", language_code),
            reply_markup=main_menu_keyboard(language_code),
        )
        return
    text, keyboard = payload
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(f"{MY_APPEALS_CALLBACK_PREFIX}:page:"))
async def my_appeals_page(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    page = _parse_non_negative_int(callback.data.rsplit(":", 1)[-1])
    if page is None:
        await callback.answer(t("common.invalid_action", language_code), show_alert=True)
        return

    payload = await _appeals_page_payload(callback.from_user.id, language_code, page)
    if payload is None:
        await callback.answer(t("my_appeals.empty_short", language_code), show_alert=True)
        return

    if callback.message is not None:
        text, keyboard = payload
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith(f"{MY_APPEALS_CALLBACK_PREFIX}:item:"))
async def my_appeals_detail(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    appeal_id = _parse_non_negative_int(callback.data.rsplit(":", 1)[-1])
    if appeal_id is None:
        await callback.answer(t("common.invalid_action", language_code), show_alert=True)
        return

    # Security boundary: the database query includes telegram_id ownership.
    # A forged callback containing another citizen's appeal id therefore returns None.
    appeal = await get_user_appeal_by_id(callback.from_user.id, appeal_id)
    if appeal is None:
        await callback.answer(t("my_appeals.not_found", language_code), show_alert=True)
        return

    answer = appeal.admin_answer or t("my_appeals.no_answer", language_code)
    attachment_key = {
        "PHOTO": "appeal.attachment.photo",
        "PDF": "appeal.attachment.pdf",
    }.get(appeal.attachment_type, "appeal.attachment.none")
    detail = t(
        "my_appeals.detail",
        language_code,
        appeal_number=appeal.appeal_number,
        created_at=format_tashkent(appeal.created_at),
        status=_status_text(appeal.status, language_code),
        category=appeal_category_text(appeal.category_code, language_code),
        attachment=t(attachment_key, language_code),
        appeal_text=appeal.appeal_text,
        admin_answer=answer,
    )

    if callback.message is not None:
        chunks = split_text_for_telegram(detail)
        back_keyboard = my_appeals_keyboard(
            [], page=0, total_pages=1, language_code=language_code, detail_back_only=True
        )
        for index, chunk in enumerate(chunks):
            await callback.message.answer(
                chunk,
                parse_mode=None,
                reply_markup=back_keyboard if index == len(chunks) - 1 else None,
            )
    await callback.answer()


@router.callback_query(F.data == f"{MY_APPEALS_CALLBACK_PREFIX}:back")
async def my_appeals_back(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    payload = await _appeals_page_payload(callback.from_user.id, language_code, 0)
    if callback.message is not None:
        if payload is None:
            await callback.message.answer(
                t("my_appeals.empty", language_code),
                reply_markup=main_menu_keyboard(language_code),
            )
        else:
            text, keyboard = payload
            await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == f"{MY_APPEALS_CALLBACK_PREFIX}:home")
async def my_appeals_home(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    if callback.message is not None:
        await callback.message.answer(
            t("menu.title", language_code), reply_markup=main_menu_keyboard(language_code)
        )
    await callback.answer()


@router.message(F.text.in_(menu_texts("settings")))
async def menu_settings(message: Message, state: FSMContext) -> None:
    await state.clear()
    language_code = await get_user_language(message.from_user.id)
    await message.answer(
        t("settings.title", language_code), reply_markup=settings_keyboard(language_code)
    )


@router.callback_query(F.data == f"{SETTINGS_CALLBACK_PREFIX}:profile")
async def settings_profile(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    user = await get_user_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("settings.profile_not_found", language_code), show_alert=True)
        return

    verified = t("settings.yes", language_code) if user.phone_verified else t("settings.no", language_code)
    language_label = LANGUAGE_LABELS.get(normalize_language(user.language_code), user.language_code)
    profile_text = t(
        "settings.profile_text",
        language_code,
        full_name=user.full_name or "—",
        phone=user.phone or "—",
        verified=verified,
        region=localize_location_value(user.region, language_code),
        district=localize_location_value(user.district, language_code),
        language=language_label,
    )
    if callback.message is not None:
        await callback.message.edit_text(
            profile_text,
            parse_mode=None,
            reply_markup=settings_keyboard(language_code, back_only=True),
        )
    await callback.answer()


@router.callback_query(F.data == f"{SETTINGS_CALLBACK_PREFIX}:language")
async def settings_language(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    if callback.message is not None:
        await callback.message.edit_text(
            t("settings.language_choose", language_code),
            reply_markup=settings_language_keyboard(language_code),
        )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{SETTINGS_LANGUAGE_CALLBACK_PREFIX}:"))
async def settings_language_selected(callback: CallbackQuery, state: FSMContext) -> None:
    raw_language = callback.data.split(":", 1)[1] if ":" in callback.data else ""
    if raw_language not in SUPPORTED_LANGUAGES:
        current = await get_user_language(callback.from_user.id)
        await callback.answer(t("common.invalid_action", current), show_alert=True)
        return

    language_code = normalize_language(raw_language)
    await set_user_language(callback.from_user.id, callback.from_user.username, language_code)
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text(t("settings.language_changed", language_code))
        await callback.message.answer(
            t("menu.title", language_code), reply_markup=main_menu_keyboard(language_code)
        )
    await callback.answer()


@router.callback_query(F.data == f"{SETTINGS_CALLBACK_PREFIX}:phone")
async def settings_phone(callback: CallbackQuery, state: FSMContext) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await state.clear()
    await state.update_data(language_code=language_code)
    await state.set_state(AccountSettings.waiting_for_phone)
    if callback.message is not None:
        await callback.message.answer(
            t("settings.phone_prompt", language_code),
            reply_markup=contact_keyboard(language_code),
        )
    await callback.answer()


@router.message(AccountSettings.waiting_for_phone, F.contact)
async def settings_phone_contact(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    language_code = normalize_language(data.get("language_code") or await get_user_language(message.from_user.id))
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

    user = await update_verified_phone(message.from_user.id, message.from_user.username, phone)
    if user is None:
        await state.clear()
        await message.answer(
            t("settings.profile_not_found", language_code),
            reply_markup=main_menu_keyboard(language_code),
        )
        return

    await state.clear()
    await message.answer(
        t("settings.phone_changed", language_code),
        reply_markup=main_menu_keyboard(language_code),
    )


@router.message(AccountSettings.waiting_for_phone, F.text)
async def settings_phone_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    language_code = normalize_language(data.get("language_code") or await get_user_language(message.from_user.id))
    await message.answer(
        t("registration.manual_phone_rejected", language_code),
        reply_markup=contact_keyboard(language_code),
    )


@router.message(AccountSettings.waiting_for_phone)
async def settings_phone_invalid(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    language_code = normalize_language(data.get("language_code") or await get_user_language(message.from_user.id))
    await message.answer(
        t("registration.manual_phone_rejected", language_code),
        reply_markup=contact_keyboard(language_code),
    )


@router.callback_query(F.data == f"{SETTINGS_CALLBACK_PREFIX}:back")
async def settings_back(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    if callback.message is not None:
        await callback.message.edit_text(
            t("settings.title", language_code), reply_markup=settings_keyboard(language_code)
        )
    await callback.answer()


@router.callback_query(F.data == f"{SETTINGS_CALLBACK_PREFIX}:home")
async def settings_home(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    if callback.message is not None:
        await callback.message.answer(
            t("menu.title", language_code), reply_markup=main_menu_keyboard(language_code)
        )
    await callback.answer()
