from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.documents import format_document_text, get_document
from app.keyboards import (
    DOCUMENT_CALLBACK_PREFIX,
    DOCUMENTS_BACK_CALLBACK,
    DOCUMENTS_HOME_CALLBACK,
    MENU_DOCUMENTS,
    document_detail_keyboard,
    documents_list_keyboard,
    main_menu_keyboard,
)

logger = logging.getLogger(__name__)

router = Router()

DOCUMENTS_INTRO_TEXT = "Қуйидаги ҳужжатлардан бирини танланг:"
DOCUMENT_NOT_FOUND_TEXT = "Ҳужжат топилмади. Илтимос, рўйхатдан қайта танланг."
MAIN_MENU_TEXT = "🏠 Асосий меню"


@router.message(F.text == MENU_DOCUMENTS)
async def open_documents(message: Message, state: FSMContext) -> None:
    # Reachable from any FSM state (registered before start.py's state
    # catch-alls) -- treat it as leaving whatever flow the user was in.
    await state.clear()
    await message.answer(DOCUMENTS_INTRO_TEXT, reply_markup=documents_list_keyboard())


@router.callback_query(F.data.startswith(f"{DOCUMENT_CALLBACK_PREFIX}:"))
async def show_document(callback: CallbackQuery) -> None:
    # This callback prefix is also used by the "📌 Асос: ..." reference
    # buttons on FAQ answers, so a document can be opened either from the
    # documents list or from a related FAQ answer.
    document_id = callback.data.split(":", 1)[1]
    document = get_document(document_id)

    if document is None:
        await callback.answer(DOCUMENT_NOT_FOUND_TEXT, show_alert=True)
        return

    if callback.message is not None:
        await callback.message.edit_text(
            format_document_text(document),
            reply_markup=document_detail_keyboard(document),
        )
    await callback.answer()


@router.callback_query(F.data == DOCUMENTS_BACK_CALLBACK)
async def back_to_documents_list(callback: CallbackQuery) -> None:
    if callback.message is not None:
        await callback.message.edit_text(DOCUMENTS_INTRO_TEXT, reply_markup=documents_list_keyboard())
    await callback.answer()


@router.callback_query(F.data == DOCUMENTS_HOME_CALLBACK)
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.answer(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()
