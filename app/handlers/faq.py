from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.documents import format_basis_line
from app.data.faq import answer_text, category_title, get_category, get_question, question_text
from app.i18n import t
from app.keyboards import (
    FAQ_BACK_CALLBACK,
    FAQ_CATEGORY_CALLBACK_PREFIX,
    FAQ_HOME_CALLBACK,
    FAQ_QUESTION_CALLBACK_PREFIX,
    faq_answer_keyboard,
    faq_categories_keyboard,
    faq_questions_keyboard,
    main_menu_keyboard,
    menu_texts,
    remove_keyboard,
)
from app.services.user_service import get_user_language

router = Router()


@router.message(F.text.in_(menu_texts("faq")))
async def open_faq(message: Message, state: FSMContext) -> None:
    await state.clear()
    language = await get_user_language(message.from_user.id)
    await message.answer(t("menu.faq", language), reply_markup=remove_keyboard())
    await message.answer(t("faq.intro", language), reply_markup=faq_categories_keyboard(language))


@router.callback_query(F.data.startswith(f"{FAQ_CATEGORY_CALLBACK_PREFIX}:"))
async def show_questions(callback: CallbackQuery) -> None:
    language = await get_user_language(callback.from_user.id)
    category_id = callback.data.split(":", 1)[1]
    category = get_category(category_id)
    if category is None:
        await callback.answer(t("faq.not_found", language), show_alert=True)
        return
    if callback.message is not None:
        await callback.message.edit_text(
            f"{category_title(category, language)}\n\n{t('faq.choose_question', language)}",
            reply_markup=faq_questions_keyboard(category_id, language),
        )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{FAQ_QUESTION_CALLBACK_PREFIX}:"))
async def show_answer(callback: CallbackQuery) -> None:
    language = await get_user_language(callback.from_user.id)
    parts = callback.data.split(":")
    category_id = parts[1] if len(parts) > 1 else ""
    question_index = _parse_index(parts[2]) if len(parts) > 2 else None
    question = get_question(category_id, question_index) if question_index is not None else None
    if question is None:
        await callback.answer(t("faq.not_found", language), show_alert=True)
        return

    related_documents = question.get("related_documents") or []
    text = f"❓ <b>{question_text(question, language)}</b>\n\n{answer_text(question, language)}"
    basis_line = format_basis_line(related_documents, language)
    if basis_line:
        text += f"\n\n{basis_line}"
    if callback.message is not None:
        await callback.message.edit_text(
            text, reply_markup=faq_answer_keyboard(related_documents, language)
        )
    await callback.answer()


@router.callback_query(F.data == FAQ_BACK_CALLBACK)
async def back_to_categories(callback: CallbackQuery) -> None:
    language = await get_user_language(callback.from_user.id)
    if callback.message is not None:
        await callback.message.edit_text(
            t("faq.intro", language), reply_markup=faq_categories_keyboard(language)
        )
    await callback.answer()


@router.callback_query(F.data == FAQ_HOME_CALLBACK)
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    language = await get_user_language(callback.from_user.id)
    if callback.message is not None:
        await callback.message.answer(
            t("menu.title", language), reply_markup=main_menu_keyboard(language)
        )
    await callback.answer()


def _parse_index(raw: str) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
