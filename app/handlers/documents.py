from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.data.documents import format_document_text, get_document
from app.i18n import t
from app.keyboards import (
    DOCUMENT_CALLBACK_PREFIX,
    DOCUMENTS_BACK_CALLBACK,
    DOCUMENTS_HOME_CALLBACK,
    document_detail_keyboard,
    documents_list_keyboard,
    main_menu_keyboard,
    menu_texts,
    remove_keyboard,
)
from app.services.user_service import get_user_language

router = Router()


@router.message(F.text.in_(menu_texts("documents")))
async def open_documents(message: Message, state: FSMContext) -> None:
    await state.clear()
    language = await get_user_language(message.from_user.id)
    await message.answer(t("menu.documents", language), reply_markup=remove_keyboard())
    await message.answer(t("documents.intro", language), reply_markup=documents_list_keyboard(language))


@router.callback_query(F.data.startswith(f"{DOCUMENT_CALLBACK_PREFIX}:"))
async def show_document(callback: CallbackQuery) -> None:
    language = await get_user_language(callback.from_user.id)
    document_id = callback.data.split(":", 1)[1]
    document = get_document(document_id)
    if document is None:
        await callback.answer(t("documents.not_found", language), show_alert=True)
        return
    if callback.message is not None:
        await callback.message.edit_text(
            format_document_text(document, language),
            reply_markup=document_detail_keyboard(document, language),
        )
    await callback.answer()


@router.callback_query(F.data == DOCUMENTS_BACK_CALLBACK)
async def back_to_documents_list(callback: CallbackQuery) -> None:
    language = await get_user_language(callback.from_user.id)
    if callback.message is not None:
        await callback.message.edit_text(
            t("documents.intro", language), reply_markup=documents_list_keyboard(language)
        )
    await callback.answer()


@router.callback_query(F.data == DOCUMENTS_HOME_CALLBACK)
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    language = await get_user_language(callback.from_user.id)
    if callback.message is not None:
        await callback.message.answer(
            t("menu.title", language), reply_markup=main_menu_keyboard(language)
        )
    await callback.answer()
