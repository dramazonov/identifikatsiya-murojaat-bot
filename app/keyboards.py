from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.data.documents import DOCUMENTS, get_document
from app.data.faq import FAQ_CATEGORIES, get_category
from app.data.regions import DISTRICTS, REGIONS

CONTACT_BUTTON_TEXT = "📱 Телефон рақамини юбориш"
REGION_CALLBACK_PREFIX = "region"
DISTRICT_CALLBACK_PREFIX = "district"
APPEAL_REPLY_CALLBACK_PREFIX = "appeal_reply"
ADMIN_CONTACT_REPLY_CALLBACK_PREFIX = "admin_contact_reply"
REPLY_BUTTON_TEXT = "✍️ Жавоб бериш"

# --- Main menu -------------------------------------------------------------

MENU_FAQ = "❓ Тайёр савол-жавоблар"
MENU_APPEAL = "📨 Мурожаат юбориш"
MENU_SUGGESTION = "💡 Таклиф юбориш"
MENU_DOCUMENTS = "📚 Қарор, қонун ва расмий ҳужжатлар билан танишиш"
MENU_ADMIN_CONTACT = "👨‍💼 Админ билан боғланиш"

# --- FAQ ---------------------------------------------------------------

FAQ_CATEGORY_CALLBACK_PREFIX = "faq_cat"
FAQ_QUESTION_CALLBACK_PREFIX = "faq_q"
FAQ_BACK_CALLBACK = "faq_back"
FAQ_HOME_CALLBACK = "faq_home"
BACK_BUTTON_TEXT = "⬅️ Орқага"
HOME_BUTTON_TEXT = "🏠 Асосий меню"

# --- Documents (📚 Расмий ҳужжатлар) ----------------------------------------

DOCUMENT_CALLBACK_PREFIX = "doc"
DOCUMENTS_BACK_CALLBACK = "doc_back"
DOCUMENTS_HOME_CALLBACK = "doc_home"
SOURCE_BUTTON_TEXT = "🔗 Расмий манба"


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CONTACT_BUTTON_TEXT, request_contact=True)]],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def region_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for region_id, name in enumerate(REGIONS):
        builder.button(text=name, callback_data=f"{REGION_CALLBACK_PREFIX}:{region_id}")
    builder.adjust(1)
    return builder.as_markup()


def district_keyboard(region_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for district_id, name in enumerate(DISTRICTS[region_id]):
        builder.button(
            text=name, callback_data=f"{DISTRICT_CALLBACK_PREFIX}:{region_id}:{district_id}"
        )
    builder.adjust(1)
    return builder.as_markup()


def admin_reply_keyboard(appeal_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=REPLY_BUTTON_TEXT, callback_data=f"{APPEAL_REPLY_CALLBACK_PREFIX}:{appeal_id}"
    )
    return builder.as_markup()


def admin_contact_reply_keyboard(contact_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text=REPLY_BUTTON_TEXT, callback_data=f"{ADMIN_CONTACT_REPLY_CALLBACK_PREFIX}:{contact_id}"
    )
    return builder.as_markup()


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_FAQ), KeyboardButton(text=MENU_APPEAL)],
            [KeyboardButton(text=MENU_SUGGESTION), KeyboardButton(text=MENU_DOCUMENTS)],
            [KeyboardButton(text=MENU_ADMIN_CONTACT)],
        ],
        resize_keyboard=True,
    )


def faq_categories_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for category in FAQ_CATEGORIES:
        builder.button(
            text=category["title"], callback_data=f"{FAQ_CATEGORY_CALLBACK_PREFIX}:{category['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()


def faq_questions_keyboard(category_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    category = get_category(category_id)

    if category is not None:
        for index, question in enumerate(category["questions"]):
            builder.button(
                text=question["question"],
                callback_data=f"{FAQ_QUESTION_CALLBACK_PREFIX}:{category_id}:{index}",
            )
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text=BACK_BUTTON_TEXT, callback_data=FAQ_BACK_CALLBACK),
        InlineKeyboardButton(text=HOME_BUTTON_TEXT, callback_data=FAQ_HOME_CALLBACK),
    )
    return builder.as_markup()


def faq_answer_keyboard(related_document_ids: list[str] | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for document_id in related_document_ids or []:
        document = get_document(document_id)
        if document is not None:
            builder.button(
                text=f"📚 {document['short_ref']}",
                callback_data=f"{DOCUMENT_CALLBACK_PREFIX}:{document['id']}",
            )
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text=BACK_BUTTON_TEXT, callback_data=FAQ_BACK_CALLBACK),
        InlineKeyboardButton(text=HOME_BUTTON_TEXT, callback_data=FAQ_HOME_CALLBACK),
    )
    return builder.as_markup()


def documents_list_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for document in DOCUMENTS:
        builder.button(
            text=document["short_ref"],
            callback_data=f"{DOCUMENT_CALLBACK_PREFIX}:{document['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def document_detail_keyboard(document: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    source_url = document.get("source_url")
    if source_url:
        builder.row(InlineKeyboardButton(text=SOURCE_BUTTON_TEXT, url=source_url))
    builder.row(
        InlineKeyboardButton(text=BACK_BUTTON_TEXT, callback_data=DOCUMENTS_BACK_CALLBACK),
        InlineKeyboardButton(text=HOME_BUTTON_TEXT, callback_data=DOCUMENTS_HOME_CALLBACK),
    )
    return builder.as_markup()
