from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.data.appeal_categories import APPEAL_CATEGORIES
from app.data.documents import DOCUMENTS, get_document
from app.data.faq import FAQ_CATEGORIES, get_category
from app.data.regions import DISTRICTS, REGIONS
from app.i18n import (
    DEFAULT_LANGUAGE,
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    all_texts,
    appeal_category_text,
    t,
)

LANGUAGE_CALLBACK_PREFIX = "lang"
CONTACT_BUTTON_TEXT = t("button.share_phone", DEFAULT_LANGUAGE)
REGION_CALLBACK_PREFIX = "region"
DISTRICT_CALLBACK_PREFIX = "district"
APPEAL_REPLY_CALLBACK_PREFIX = "appeal_reply"
APPEAL_CATEGORY_CALLBACK_PREFIX = "appeal_cat"
APPEAL_ATTACHMENT_SKIP_CALLBACK = "appeal_attach_skip"
APPEAL_CONFIRM_CALLBACK = "appeal_confirm"
APPEAL_CANCEL_CALLBACK = "appeal_cancel"
ADMIN_CONTACT_REPLY_CALLBACK_PREFIX = "admin_contact_reply"
MY_APPEALS_CALLBACK_PREFIX = "myappeals"
SETTINGS_CALLBACK_PREFIX = "settings"
SETTINGS_LANGUAGE_CALLBACK_PREFIX = "settings_lang"
REPLY_BUTTON_TEXT = "✍️ Жавоб бериш"

# Backward-compatible default labels used by older imports/tests. Handlers now
# match every translated variant via menu_texts().
MENU_FAQ = t("menu.faq", DEFAULT_LANGUAGE)
MENU_APPEAL = t("menu.appeal", DEFAULT_LANGUAGE)
MENU_SUGGESTION = t("menu.suggestion", DEFAULT_LANGUAGE)
MENU_DOCUMENTS = t("menu.documents", DEFAULT_LANGUAGE)
MENU_ADMIN_CONTACT = t("menu.admin_contact", DEFAULT_LANGUAGE)
MENU_MY_APPEALS = t("menu.my_appeals", DEFAULT_LANGUAGE)
MENU_SETTINGS = t("menu.settings", DEFAULT_LANGUAGE)

FAQ_CATEGORY_CALLBACK_PREFIX = "faq_cat"
FAQ_QUESTION_CALLBACK_PREFIX = "faq_q"
FAQ_BACK_CALLBACK = "faq_back"
FAQ_HOME_CALLBACK = "faq_home"
BACK_BUTTON_TEXT = t("button.back", DEFAULT_LANGUAGE)
HOME_BUTTON_TEXT = t("button.home", DEFAULT_LANGUAGE)

DOCUMENT_CALLBACK_PREFIX = "doc"
DOCUMENTS_BACK_CALLBACK = "doc_back"
DOCUMENTS_HOME_CALLBACK = "doc_home"
SOURCE_BUTTON_TEXT = t("button.official_source", DEFAULT_LANGUAGE)


def menu_texts(key: str) -> tuple[str, ...]:
    return all_texts(f"menu.{key}")


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for language_code in SUPPORTED_LANGUAGES:
        builder.button(
            text=LANGUAGE_LABELS[language_code],
            callback_data=f"{LANGUAGE_CALLBACK_PREFIX}:{language_code}",
        )
    builder.adjust(2)
    return builder.as_markup()


def contact_keyboard(language_code: str = DEFAULT_LANGUAGE) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text=t("button.share_phone", language_code), request_contact=True)
        ]],
        resize_keyboard=True,
        one_time_keyboard=True,
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



def appeal_category_keyboard(language_code: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code in APPEAL_CATEGORIES:
        builder.button(
            text=appeal_category_text(code, language_code),
            callback_data=f"{APPEAL_CATEGORY_CALLBACK_PREFIX}:{code}",
        )
    builder.adjust(1)
    builder.row(
        InlineKeyboardButton(
            text=t("appeal.cancel", language_code), callback_data=APPEAL_CANCEL_CALLBACK
        )
    )
    return builder.as_markup()


def appeal_attachment_keyboard(language_code: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("appeal.skip_attachment", language_code),
            callback_data=APPEAL_ATTACHMENT_SKIP_CALLBACK,
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("appeal.cancel", language_code), callback_data=APPEAL_CANCEL_CALLBACK
        )
    )
    return builder.as_markup()


def appeal_confirmation_keyboard(language_code: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t("appeal.confirm", language_code), callback_data=APPEAL_CONFIRM_CALLBACK
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t("appeal.cancel", language_code), callback_data=APPEAL_CANCEL_CALLBACK
        )
    )
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


def main_menu_keyboard(language_code: str = DEFAULT_LANGUAGE) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("menu.faq", language_code)),
                KeyboardButton(text=t("menu.appeal", language_code)),
            ],
            [
                KeyboardButton(text=t("menu.suggestion", language_code)),
                KeyboardButton(text=t("menu.documents", language_code)),
            ],
            [
                KeyboardButton(text=t("menu.my_appeals", language_code)),
                KeyboardButton(text=t("menu.admin_contact", language_code)),
            ],
            [KeyboardButton(text=t("menu.settings", language_code))],
        ],
        resize_keyboard=True,
    )


def my_appeals_keyboard(
    appeals,
    *,
    page: int,
    total_pages: int,
    language_code: str = DEFAULT_LANGUAGE,
    status_emoji=None,
    status_text=None,
    detail_back_only: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if detail_back_only:
        builder.row(
            InlineKeyboardButton(
                text=t("button.back", language_code),
                callback_data=f"{MY_APPEALS_CALLBACK_PREFIX}:back",
            ),
            InlineKeyboardButton(
                text=t("button.home", language_code),
                callback_data=f"{MY_APPEALS_CALLBACK_PREFIX}:home",
            ),
        )
        return builder.as_markup()

    for appeal in appeals:
        emoji = status_emoji(appeal.status) if status_emoji else "📌"
        label = status_text(appeal.status, language_code) if status_text else ""
        suffix = f" — {label}" if label else ""
        builder.button(
            text=f"{emoji} {appeal.appeal_number}{suffix}",
            callback_data=f"{MY_APPEALS_CALLBACK_PREFIX}:item:{appeal.id}",
        )
    builder.adjust(1)

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text=t("button.previous", language_code),
                callback_data=f"{MY_APPEALS_CALLBACK_PREFIX}:page:{page - 1}",
            )
        )
    if page + 1 < total_pages:
        nav.append(
            InlineKeyboardButton(
                text=t("button.next", language_code),
                callback_data=f"{MY_APPEALS_CALLBACK_PREFIX}:page:{page + 1}",
            )
        )
    if nav:
        builder.row(*nav)
    builder.row(
        InlineKeyboardButton(
            text=t("button.home", language_code),
            callback_data=f"{MY_APPEALS_CALLBACK_PREFIX}:home",
        )
    )
    return builder.as_markup()


def settings_keyboard(
    language_code: str = DEFAULT_LANGUAGE, *, back_only: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not back_only:
        builder.button(
            text=t("settings.profile", language_code),
            callback_data=f"{SETTINGS_CALLBACK_PREFIX}:profile",
        )
        builder.button(
            text=t("settings.language", language_code),
            callback_data=f"{SETTINGS_CALLBACK_PREFIX}:language",
        )
        builder.button(
            text=t("settings.phone", language_code),
            callback_data=f"{SETTINGS_CALLBACK_PREFIX}:phone",
        )
        builder.adjust(1)
    if back_only:
        builder.row(
            InlineKeyboardButton(
                text=t("button.back", language_code),
                callback_data=f"{SETTINGS_CALLBACK_PREFIX}:back",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text=t("button.home", language_code),
            callback_data=f"{SETTINGS_CALLBACK_PREFIX}:home",
        )
    )
    return builder.as_markup()


def settings_language_keyboard(language_code: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code in SUPPORTED_LANGUAGES:
        builder.button(
            text=LANGUAGE_LABELS[code],
            callback_data=f"{SETTINGS_LANGUAGE_CALLBACK_PREFIX}:{code}",
        )
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(
            text=t("button.back", language_code),
            callback_data=f"{SETTINGS_CALLBACK_PREFIX}:back",
        )
    )
    return builder.as_markup()


def faq_categories_keyboard(language_code: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
    # FAQ legal/knowledge-base content remains the official Uzbek-Cyrillic
    # source in Stage 18A; Stage 18B will translate the knowledge-base itself.
    builder = InlineKeyboardBuilder()
    for category in FAQ_CATEGORIES:
        builder.button(
            text=category["title"], callback_data=f"{FAQ_CATEGORY_CALLBACK_PREFIX}:{category['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()


def faq_questions_keyboard(category_id: str, language_code: str = DEFAULT_LANGUAGE) -> InlineKeyboardMarkup:
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
        InlineKeyboardButton(text=t("button.back", language_code), callback_data=FAQ_BACK_CALLBACK),
        InlineKeyboardButton(text=t("button.home", language_code), callback_data=FAQ_HOME_CALLBACK),
    )
    return builder.as_markup()


def faq_answer_keyboard(
    related_document_ids: list[str] | None = None,
    language_code: str = DEFAULT_LANGUAGE,
) -> InlineKeyboardMarkup:
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
        InlineKeyboardButton(text=t("button.back", language_code), callback_data=FAQ_BACK_CALLBACK),
        InlineKeyboardButton(text=t("button.home", language_code), callback_data=FAQ_HOME_CALLBACK),
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


def document_detail_keyboard(
    document: dict, language_code: str = DEFAULT_LANGUAGE
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    source_url = document.get("source_url")
    if source_url:
        builder.row(
            InlineKeyboardButton(text=t("button.official_source", language_code), url=source_url)
        )
    builder.row(
        InlineKeyboardButton(
            text=t("button.back", language_code), callback_data=DOCUMENTS_BACK_CALLBACK
        ),
        InlineKeyboardButton(
            text=t("button.home", language_code), callback_data=DOCUMENTS_HOME_CALLBACK
        ),
    )
    return builder.as_markup()
