from __future__ import annotations

from app.i18n import SUPPORTED_LANGUAGES, t
from app.keyboards import main_menu_keyboard, settings_language_keyboard
from app.services.appeal_service import (
    count_user_appeals,
    create_appeal,
    get_user_appeal_by_id,
    list_user_appeals,
)
from app.services.user_service import (
    PHONE_VERIFICATION_SOURCE_TELEGRAM,
    get_user_by_telegram_id,
    save_user,
    save_user_location,
    update_verified_phone,
)


async def _registered_user(telegram_id: int, *, language: str = "uz_latn"):
    await save_user(
        telegram_id,
        f"user{telegram_id}",
        f"Stage21 User {telegram_id}",
        "+998901234567",
        phone_verified=True,
        phone_verification_source=PHONE_VERIFICATION_SOURCE_TELEGRAM,
        language_code=language,
    )
    return await save_user_location(telegram_id, "Toshkent", "Chilonzor")


def test_main_menu_contains_stage21_sections_in_all_languages():
    for language in SUPPORTED_LANGUAGES:
        keyboard = main_menu_keyboard(language)
        texts = [button.text for row in keyboard.keyboard for button in row]
        assert t("menu.my_appeals", language) in texts
        assert t("menu.settings", language) in texts
        assert len(texts) == 7


def test_settings_language_keyboard_has_exactly_four_language_callbacks():
    keyboard = settings_language_keyboard("uz_latn")
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data and button.callback_data.startswith("settings_lang:")
    ]
    assert callbacks == [f"settings_lang:{language}" for language in SUPPORTED_LANGUAGES]


async def test_user_appeal_list_is_scoped_and_newest_first():
    owner = 960100001
    other = 960100002
    await _registered_user(owner)
    await _registered_user(other)

    created = [await create_appeal(owner, f"Owner appeal {i} long enough") for i in range(7)]
    foreign = await create_appeal(other, "Other user's private appeal")

    assert await count_user_appeals(owner) == 7
    first_page = await list_user_appeals(owner, offset=0, limit=5)
    second_page = await list_user_appeals(owner, offset=5, limit=5)

    assert [a.id for a in first_page] == [a.id for a in reversed(created[-5:])]
    assert [a.id for a in second_page] == [a.id for a in reversed(created[:2])]
    assert all(a.user_id != foreign.user_id for a in first_page + second_page)


async def test_forged_appeal_id_cannot_cross_user_boundary():
    owner = 960100003
    attacker = 960100004
    await _registered_user(owner)
    await _registered_user(attacker)
    appeal = await create_appeal(owner, "Private owner appeal that must stay private")

    assert await get_user_appeal_by_id(owner, appeal.id) is not None
    assert await get_user_appeal_by_id(attacker, appeal.id) is None


async def test_verified_phone_update_changes_only_phone_identity_fields():
    telegram_id = 960100005
    before = await _registered_user(telegram_id, language="en")
    old_created_at = before.created_at

    updated = await update_verified_phone(telegram_id, "new_username", "+998909999999")
    assert updated is not None
    assert updated.telegram_username == "new_username"
    assert updated.phone == "+998909999999"
    assert updated.phone_verified is True
    assert updated.phone_verification_source == PHONE_VERIFICATION_SOURCE_TELEGRAM
    assert updated.phone_verified_at is not None
    assert updated.full_name == before.full_name
    assert updated.region == "Toshkent"
    assert updated.district == "Chilonzor"
    assert updated.language_code == "en"
    assert updated.created_at == old_created_at


async def test_verified_phone_update_never_creates_unknown_user():
    telegram_id = 960199999
    assert await get_user_by_telegram_id(telegram_id) is None
    assert await update_verified_phone(telegram_id, "ghost", "+998901111111") is None
    assert await get_user_by_telegram_id(telegram_id) is None


async def test_settings_manual_phone_text_is_rejected(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.handlers import account

    update_phone = AsyncMock()
    monkeypatch.setattr(account, "update_verified_phone", update_phone)
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=960100006),
        answer=AsyncMock(),
        text="+998901234567",
    )
    state = AsyncMock()
    state.get_data.return_value = {"language_code": "uz_latn"}

    await account.settings_phone_text(message, state)

    update_phone.assert_not_awaited()
    message.answer.assert_awaited_once()


async def test_settings_foreign_contact_is_rejected(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from app.handlers import account

    update_phone = AsyncMock()
    monkeypatch.setattr(account, "update_verified_phone", update_phone)
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=960100007, username="owner"),
        contact=SimpleNamespace(user_id=960199999, phone_number="+998901234567"),
        answer=AsyncMock(),
    )
    state = AsyncMock()
    state.get_data.return_value = {"language_code": "ru"}

    await account.settings_phone_contact(message, state)

    update_phone.assert_not_awaited()
    message.answer.assert_awaited_once()
