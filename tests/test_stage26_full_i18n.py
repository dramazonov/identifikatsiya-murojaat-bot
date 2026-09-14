from __future__ import annotations

import re

from app.data.documents import DOCUMENTS, document_text, format_basis_line, format_document_text
from app.data.faq import FAQ_CATEGORIES, answer_text, category_title, question_text
from app.data.regions import DISTRICTS, REGIONS, district_label, localize_location_value, region_label

LANGUAGES = ("uz_latn", "uz_cyrl", "ru", "en")
CYRILLIC = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]")


def test_region_and_district_labels_exist_for_all_four_languages():
    assert len(REGIONS) == 14
    assert sum(len(items) for items in DISTRICTS.values()) > 190
    for region_id, canonical_region in enumerate(REGIONS):
        for language in LANGUAGES:
            assert region_label(region_id, language).strip()
        assert localize_location_value(canonical_region, "uz_cyrl") == canonical_region
        for district_id, canonical_district in enumerate(DISTRICTS[region_id]):
            for language in LANGUAGES:
                assert district_label(region_id, district_id, language).strip()
            assert localize_location_value(canonical_district, "uz_cyrl") == canonical_district


def test_english_and_uzbek_latin_location_labels_do_not_leak_cyrillic():
    for region_id in range(len(REGIONS)):
        for language in ("uz_latn", "en"):
            assert not CYRILLIC.search(region_label(region_id, language))
        for district_id in range(len(DISTRICTS[region_id])):
            for language in ("uz_latn", "en"):
                assert not CYRILLIC.search(district_label(region_id, district_id, language))


def test_documents_are_fully_localized_without_changing_source_urls():
    expected_urls = {
        "orq_1079": "https://lex.uz/uz/docs/-7670550",
        "qm_748": "https://lex.uz/uz/docs/-3359038",
        "pq_285": "https://lex.uz/uz/docs/-6583141",
    }
    for document in DOCUMENTS:
        assert document["source_url"] == expected_urls[document["id"]]
        for language in LANGUAGES:
            for field in ("header", "number", "title", "short_ref"):
                assert document_text(document, field, language).strip()
            assert format_document_text(document, language).strip()
        for language in ("uz_latn", "en"):
            assert not CYRILLIC.search(document_text(document, "short_ref", language))
            assert not CYRILLIC.search(document_text(document, "title", language))

    assert format_basis_line(["qm_748"], "uz_latn").startswith("📌 Asos:")
    assert format_basis_line(["qm_748"], "uz_cyrl").startswith("📌 Асос:")
    assert format_basis_line(["qm_748"], "ru").startswith("📌 Основание:")
    assert format_basis_line(["qm_748"], "en").startswith("📌 Basis:")


def test_faq_categories_questions_and_answers_are_complete_in_all_languages():
    assert FAQ_CATEGORIES
    for category in FAQ_CATEGORIES:
        for language in LANGUAGES:
            assert category_title(category, language).strip()
        for question in category["questions"]:
            for language in LANGUAGES:
                assert question_text(question, language).strip()
                assert answer_text(question, language).strip()
            for language in ("uz_latn", "en"):
                assert not CYRILLIC.search(question_text(question, language))
                assert not CYRILLIC.search(answer_text(question, language))


def test_known_examples_match_selected_language():
    registration = next(c for c in FAQ_CATEGORIES if c["id"] == "registration")
    dead_animal = registration["questions"][1]
    assert category_title(registration, "en") == "📋 Registration and deregistration"
    assert question_text(dead_animal, "en") == "What should I do if an animal dies?"
    assert question_text(dead_animal, "uz_latn") == "Hayvon nobud bo‘lsa nima qilish kerak?"
    assert "Ж" not in answer_text(dead_animal, "en")
    assert region_label(10, "en") == "Tashkent Region"
    assert localize_location_value("Юнусобод тумани", "en") == "Yunusobod District"
