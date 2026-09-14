"""Localized static content for the official-documents section.

Document ids and source URLs are stable internal values.  All citizen-facing
labels are resolved at render time for the user's selected language.
"""

from __future__ import annotations

from app.i18n import DEFAULT_LANGUAGE, normalize_language

Localized = dict[str, str]

DOCUMENTS: list[dict] = [
    {
        "id": "orq_1079",
        "header": {
            "uz_latn": "📜 O‘zbekiston Respublikasining Qonuni",
            "uz_cyrl": "📜 Ўзбекистон Республикасининг Қонуни",
            "ru": "📜 Закон Республики Узбекистан",
            "en": "📜 Law of the Republic of Uzbekistan",
        },
        "number": {
            "uz_latn": "№ O‘RQ-1079",
            "uz_cyrl": "№ ЎРҚ-1079",
            "ru": "№ ЗРУ-1079",
            "en": "No. O‘RQ-1079",
        },
        "date": "06.08.2025",
        "title": {
            "uz_latn": "Hayvonlarni identifikatsiya qilish, ro‘yxatga olish va kuzatish to‘g‘risida",
            "uz_cyrl": "Ҳайвонларни идентификация қилиш, рўйхатга олиш ва кузатиш тўғрисида",
            "ru": "Об идентификации, регистрации и отслеживании животных",
            "en": "On the identification, registration and traceability of animals",
        },
        "short_ref": {
            "uz_latn": "O‘RQ-1079-son Qonun",
            "uz_cyrl": "ЎРҚ-1079-сон Қонун",
            "ru": "Закон № ЗРУ-1079",
            "en": "Law No. O‘RQ-1079",
        },
        "source_url": "https://lex.uz/uz/docs/-7670550",
    },
    {
        "id": "qm_748",
        "header": {
            "uz_latn": "📜 O‘zbekiston Respublikasi Vazirlar Mahkamasining qarori",
            "uz_cyrl": "📜 Ўзбекистон Республикаси Вазирлар Маҳкамасининг қарори",
            "ru": "📜 Постановление Кабинета Министров Республики Узбекистан",
            "en": "📜 Resolution of the Cabinet of Ministers of the Republic of Uzbekistan",
        },
        "number": {"uz_latn": "№ 748", "uz_cyrl": "№ 748", "ru": "№ 748", "en": "No. 748"},
        "date": "22.09.2017",
        "title": {
            "uz_latn": "Hayvonlarni identifikatsiya qilish, ularni hisobga olish, hisobdan chiqarish va saqlash tartibini takomillashtirish to‘g‘risida",
            "uz_cyrl": "Ҳайвонларни идентификация қилиш, уларни ҳисобга олиш, ҳисобдан чиқариш ва сақлаш тартибини такомиллаштириш тўғрисида",
            "ru": "О совершенствовании порядка идентификации животных, их учета, снятия с учета и содержания",
            "en": "On improving the procedure for animal identification, registration, deregistration and keeping",
        },
        "short_ref": {
            "uz_latn": "748-son Qaror",
            "uz_cyrl": "748-сон Қарор",
            "ru": "Постановление № 748",
            "en": "Resolution No. 748",
        },
        "source_url": "https://lex.uz/uz/docs/-3359038",
    },
    {
        "id": "pq_285",
        "header": {
            "uz_latn": "📜 O‘zbekiston Respublikasi Prezidentining qarori",
            "uz_cyrl": "📜 Ўзбекистон Республикаси Президентининг қарори",
            "ru": "📜 Постановление Президента Республики Узбекистан",
            "en": "📜 Resolution of the President of the Republic of Uzbekistan",
        },
        "number": {
            "uz_latn": "№ PQ-285",
            "uz_cyrl": "№ ПҚ-285",
            "ru": "№ ПП-285",
            "en": "No. PQ-285",
        },
        "date": "24.08.2023",
        "title": {
            "uz_latn": "Chorvachilikda identifikatsiya qilish tizimi va naslchilik sohasini takomillashtirishga oid qo‘shimcha chora-tadbirlar to‘g‘risida",
            "uz_cyrl": "Чорвачиликда идентификация қилиш тизими ва наслчилик соҳасини такомиллаштиришга оид қўшимча чора-тадбирлар тўғрисида",
            "ru": "О дополнительных мерах по совершенствованию системы идентификации в животноводстве и сферы племенного дела",
            "en": "On additional measures to improve the identification system in livestock farming and the breeding sector",
        },
        "short_ref": {
            "uz_latn": "PQ-285-son Qaror",
            "uz_cyrl": "ПҚ-285-сон Қарор",
            "ru": "Постановление Президента № ПП-285",
            "en": "Presidential Resolution No. PQ-285",
        },
        "source_url": "https://lex.uz/uz/docs/-6583141",
    },
]


def _localized(value: object, language_code: str | None) -> str:
    if not isinstance(value, dict):
        return str(value)
    language = normalize_language(language_code)
    return value.get(language) or value.get(DEFAULT_LANGUAGE) or next(iter(value.values()), "")


def document_text(document: dict, field: str, language_code: str | None = None) -> str:
    return _localized(document.get(field, ""), language_code)


def get_document(document_id: str) -> dict | None:
    for document in DOCUMENTS:
        if document["id"] == document_id:
            return document
    return None


def get_documents(document_ids: list[str]) -> list[dict]:
    return [doc for document_id in document_ids if (doc := get_document(document_id)) is not None]


def format_document_text(document: dict, language_code: str | None = None) -> str:
    return (
        f"{document_text(document, 'header', language_code)}\n\n"
        f"{document_text(document, 'number', language_code)}\n"
        f"📅 {document['date']}\n\n"
        f"{document_text(document, 'title', language_code)}"
    )


def format_basis_line(document_ids: list[str], language_code: str | None = None) -> str:
    refs = [document_text(doc, "short_ref", language_code) for doc in get_documents(document_ids)]
    if not refs:
        return ""
    labels = {
        "uz_latn": "📌 Asos:",
        "uz_cyrl": "📌 Асос:",
        "ru": "📌 Основание:",
        "en": "📌 Basis:",
    }
    language = normalize_language(language_code)
    return f"{labels[language]} {', '.join(refs)}."
