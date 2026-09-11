from app.i18n import LANGUAGE_LABELS, SUPPORTED_LANGUAGES, all_texts, t


def test_four_supported_languages_and_menu_translations_are_complete():
    assert SUPPORTED_LANGUAGES == ("uz_latn", "uz_cyrl", "ru", "en")
    assert set(LANGUAGE_LABELS) == set(SUPPORTED_LANGUAGES)
    for key in ("faq", "appeal", "suggestion", "documents", "my_appeals", "admin_contact", "settings"):
        values = all_texts(f"menu.{key}")
        assert len(values) == 4
        assert all(value.strip() for value in values)


def test_translations_interpolate_public_numbers():
    for language in SUPPORTED_LANGUAGES:
        text = t("appeal.success", language, appeal_number="MUR-000123")
        assert "MUR-000123" in text


def test_stage21_account_and_status_translations_are_complete():
    keys = (
        "my_appeals.title",
        "my_appeals.empty",
        "my_appeals.detail",
        "settings.title",
        "settings.profile_text",
        "settings.language_changed",
        "settings.phone_changed",
        "status.new",
        "status.in_progress",
        "status.waiting_for_user",
        "status.completed",
        "status.rejected",
        "status.unknown",
        "appeal.category_prompt",
        "appeal.subject_prompt",
        "appeal.attachment_prompt",
        "appeal.confirmation",
    )
    for key in keys:
        values = all_texts(key)
        assert len(values) == 4
        assert all(value.strip() for value in values)
