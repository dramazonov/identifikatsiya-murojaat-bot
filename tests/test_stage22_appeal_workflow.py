from __future__ import annotations

from app.data.appeal_categories import APPEAL_CATEGORIES
from app.handlers.account import _status_text
from app.handlers.admin import _build_appeal_footer_text
from app.i18n import SUPPORTED_LANGUAGES, appeal_category_text, appeal_status_text, t
from app.keyboards import appeal_category_keyboard, appeal_confirmation_keyboard
from app.models import Appeal
from app.services.appeal_service import create_appeal
from app.services.user_service import save_user
from app.states import AppealSubmissionStates


def test_categories_have_four_language_labels_and_callbacks():
    assert len(APPEAL_CATEGORIES) == 8
    for language in SUPPORTED_LANGUAGES:
        keyboard = appeal_category_keyboard(language)
        callbacks = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.callback_data and button.callback_data.startswith("appeal_cat:")
        ]
        assert callbacks == [f"appeal_cat:{code}" for code in APPEAL_CATEGORIES]
        for code in APPEAL_CATEGORIES:
            assert appeal_category_text(code, language).strip()


def test_confirmation_keyboard_has_confirm_and_cancel():
    keyboard = appeal_confirmation_keyboard("uz_latn")
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    ]
    assert callbacks == ["appeal_confirm", "appeal_cancel"]


def test_stage24_flow_has_no_subject_state_and_pdf_only_prompt():
    assert not hasattr(AppealSubmissionStates, "waiting_for_subject")
    prompt = t("appeal.attachment_prompt", "uz_latn").lower()
    assert "pdf" in prompt
    assert "foto" not in prompt
    confirmation = t(
        "appeal.confirmation",
        "uz_latn",
        category="Elektron baza",
        attachment="Yo‘q",
        appeal_text="Test murojaat",
    )
    assert "Mavzu" not in confirmation
    assert "Test murojaat" in confirmation


async def test_create_appeal_persists_simplified_metadata():
    telegram_id = 970220001
    await save_user(
        telegram_id,
        "stage24",
        "Stage Twenty Four",
        "+998901234567",
    )
    appeal = await create_appeal(
        telegram_id,
        "Detailed appeal body.",
        category_code="DATABASE",
        attachment_type="PDF",
        attachment_file_id="telegram-file-id",
        attachment_file_unique_id="unique-file-id",
        attachment_name="evidence.pdf",
        attachment_size=12345,
    )
    assert appeal.category_code == "DATABASE"
    assert appeal.subject is None
    assert appeal.attachment_type == "PDF"
    assert appeal.attachment_file_id == "telegram-file-id"
    assert appeal.attachment_file_unique_id == "unique-file-id"
    assert appeal.attachment_name == "evidence.pdf"
    assert appeal.attachment_size == 12345
    assert appeal.status == "NEW"


async def test_pre_stage22_create_appeal_call_remains_backward_compatible():
    telegram_id = 970220002
    await save_user(
        telegram_id,
        "legacy-stage22",
        "Legacy Stage Twenty Two",
        "+998901234568",
    )
    appeal = await create_appeal(telegram_id, "Legacy direct appeal body")
    assert appeal.category_code is None
    assert appeal.subject is None
    assert appeal.attachment_type is None
    assert appeal.status == "NEW"


def test_internal_status_codes_never_leak_to_uzbek_citizen_ui():
    expected = {
        "NEW": ("Yangi", "Янги"),
        "IN_PROGRESS": ("Ko‘rib chiqilmoqda", "Кўриб чиқилмоқда"),
        "WAITING_FOR_USER": ("Foydalanuvchi javobi kutilmoqda", "Фойдаланувчи жавоби кутилмоқда"),
        "COMPLETED": ("Yakunlangan", "Якунланган"),
        "REJECTED": ("Rad etilgan", "Рад этилган"),
    }
    for code, (latn, cyrl) in expected.items():
        assert appeal_status_text(code, "uz_latn") == latn
        assert appeal_status_text(code, "uz_cyrl") == cyrl
        assert _status_text(code, "uz_latn") == latn
        assert code not in latn
        assert code not in cyrl
    assert appeal_status_text("SOMETHING_NEW", "uz_latn") == "Noma’lum"


def test_admin_footer_uses_uzbek_status_not_internal_code():
    appeal = Appeal(
        appeal_number="MUR-000001",
        user_id=1,
        appeal_text="test",
        status="NEW",
    )
    from datetime import datetime
    appeal.created_at = datetime(2026, 9, 11, 10, 0, 0)
    footer = _build_appeal_footer_text(appeal, completed=False)
    assert "Янги" in footer
    assert ">NEW<" not in footer
    assert "Ҳолат" in footer


def test_stage24_translation_keys_are_complete():
    keys = (
        "appeal.category_prompt",
        "appeal.text_prompt",
        "appeal.attachment_prompt",
        "appeal.attachment_invalid",
        "appeal.confirmation",
        "appeal.confirm",
        "appeal.cancel",
        "appeal.skip_attachment",
        "appeal.success_v2",
        "appeal.status_changed",
    )
    from app.i18n import all_texts
    for key in keys:
        values = all_texts(key)
        assert len(values) == 4
        assert all(value.strip() for value in values)
