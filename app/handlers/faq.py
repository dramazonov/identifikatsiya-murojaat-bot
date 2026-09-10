from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.documents import format_basis_line
from app.data.faq import get_category, get_question
from app.keyboards import (
    FAQ_BACK_CALLBACK,
    FAQ_CATEGORY_CALLBACK_PREFIX,
    FAQ_HOME_CALLBACK,
    FAQ_QUESTION_CALLBACK_PREFIX,
    MENU_FAQ,
    faq_answer_keyboard,
    faq_categories_keyboard,
    faq_questions_keyboard,
    main_menu_keyboard,
)

logger = logging.getLogger(__name__)

router = Router()

FAQ_INTRO_TEXT = "Керакли бўлимни танланг:"
FAQ_NOT_FOUND_TEXT = "Бўлим топилмади. Илтимос, рўйхатдан қайта танланг."
MAIN_MENU_TEXT = "🏠 Асосий меню"


@router.message(F.text == MENU_FAQ)
async def open_faq(message: Message, state: FSMContext) -> None:
    # Reachable from any FSM state (registered before start.py's state
    # catch-alls) -- treat it as leaving whatever flow the user was in.
    await state.clear()
    await message.answer(FAQ_INTRO_TEXT, reply_markup=faq_categories_keyboard())


@router.callback_query(F.data.startswith(f"{FAQ_CATEGORY_CALLBACK_PREFIX}:"))
async def show_questions(callback: CallbackQuery) -> None:
    category_id = callback.data.split(":", 1)[1]
    category = get_category(category_id)

    if category is None:
        await callback.answer(FAQ_NOT_FOUND_TEXT, show_alert=True)
        return

    if callback.message is not None:
        await callback.message.edit_text(
            f"{category['title']}\n\nСаволни танланг:",
            reply_markup=faq_questions_keyboard(category_id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{FAQ_QUESTION_CALLBACK_PREFIX}:"))
async def show_answer(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    category_id = parts[1] if len(parts) > 1 else ""
    question_index = _parse_index(parts[2]) if len(parts) > 2 else None

    question = get_question(category_id, question_index) if question_index is not None else None

    if question is None:
        await callback.answer(FAQ_NOT_FOUND_TEXT, show_alert=True)
        return

    related_documents = question.get("related_documents") or []
    text = f"❓ <b>{question['question']}</b>\n\n{question['answer']}"
    basis_line = format_basis_line(related_documents)
    if basis_line:
        text += f"\n\n{basis_line}"

    if callback.message is not None:
        await callback.message.edit_text(text, reply_markup=faq_answer_keyboard(related_documents))
    await callback.answer()


@router.callback_query(F.data == FAQ_BACK_CALLBACK)
async def back_to_categories(callback: CallbackQuery) -> None:
    if callback.message is not None:
        await callback.message.edit_text(FAQ_INTRO_TEXT, reply_markup=faq_categories_keyboard())
    await callback.answer()


@router.callback_query(F.data == FAQ_HOME_CALLBACK)
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()


def _parse_index(raw: str) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
