from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.handlers import start
from app.services.user_service import (
    PHONE_VERIFICATION_SOURCE_TELEGRAM,
    TELEGRAM_STATUS_ACTIVE,
    TELEGRAM_STATUS_UNREACHABLE,
    get_user_by_telegram_id,
    is_registration_complete,
    mark_user_active,
    mark_user_unreachable,
    save_user,
    save_user_location,
    set_user_language,
)


async def test_language_is_persisted_without_overwriting_profile():
    telegram_id = 950100001
    await save_user(
        telegram_id,
        "security",
        "Security Test User",
        "+998901111111",
        phone_verified=True,
        phone_verification_source=PHONE_VERIFICATION_SOURCE_TELEGRAM,
        language_code="uz_cyrl",
    )
    await save_user_location(telegram_id, "Toshkent", "Chilonzor")
    updated = await set_user_language(telegram_id, "security2", "en")
    assert updated.language_code == "en"
    assert updated.full_name == "Security Test User"
    assert updated.phone == "+998901111111"
    assert updated.phone_verified is True
    assert (updated.region, updated.district) == ("Toshkent", "Chilonzor")


async def test_registration_is_incomplete_until_phone_is_verified():
    telegram_id = 950100002
    user = await save_user(telegram_id, "legacy", "Legacy User", "+998902222222")
    await save_user_location(telegram_id, "Samarqand", "Samarqand shahri")
    user = await get_user_by_telegram_id(telegram_id)
    assert user.phone_verified is False
    assert not is_registration_complete(user)

    user = await save_user(
        telegram_id,
        "legacy",
        "Legacy User",
        "+998902222222",
        phone_verified=True,
        phone_verification_source=PHONE_VERIFICATION_SOURCE_TELEGRAM,
        language_code="uz_latn",
    )
    assert is_registration_complete(user)
    assert user.phone_verification_source == PHONE_VERIFICATION_SOURCE_TELEGRAM
    assert user.phone_verified_at is not None


async def test_unreachable_user_becomes_active_again():
    telegram_id = 950100003
    await save_user(
        telegram_id,
        "lifecycle",
        "Lifecycle User",
        "+998903333333",
        phone_verified=True,
        phone_verification_source=PHONE_VERIFICATION_SOURCE_TELEGRAM,
    )
    await mark_user_unreachable(telegram_id)
    user = await get_user_by_telegram_id(telegram_id)
    assert user.telegram_status == TELEGRAM_STATUS_UNREACHABLE
    assert user.unreachable_at is not None

    await mark_user_active(telegram_id)
    user = await get_user_by_telegram_id(telegram_id)
    assert user.telegram_status == TELEGRAM_STATUS_ACTIVE
    assert user.unreachable_at is None


async def test_manual_phone_text_is_never_accepted(monkeypatch):
    finish = AsyncMock()
    monkeypatch.setattr(start, "_finish_verified_phone", finish)
    monkeypatch.setattr(start, "_language_for_user", AsyncMock(return_value="uz_latn"))
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=950100004),
        answer=AsyncMock(),
        text="+998901234567",
    )
    state = AsyncMock()
    await start.process_phone_text(message, state)
    finish.assert_not_awaited()
    message.answer.assert_awaited_once()


async def test_foreign_contact_is_rejected(monkeypatch):
    finish = AsyncMock()
    monkeypatch.setattr(start, "_finish_verified_phone", finish)
    monkeypatch.setattr(start, "_language_for_user", AsyncMock(return_value="ru"))
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=950100005),
        contact=SimpleNamespace(user_id=999999999, phone_number="+998901234567"),
        answer=AsyncMock(),
    )
    state = AsyncMock()
    await start.process_phone_contact(message, state)
    finish.assert_not_awaited()
    message.answer.assert_awaited_once()


async def test_generic_profile_update_does_not_downgrade_verified_phone_or_language():
    telegram_id = 950100006
    await save_user(
        telegram_id,
        "verified",
        "Verified User",
        "+998906666666",
        phone_verified=True,
        phone_verification_source=PHONE_VERIFICATION_SOURCE_TELEGRAM,
        language_code="en",
    )
    updated = await save_user(
        telegram_id,
        "verified2",
        "Verified User Updated",
        "+998906666667",
    )
    assert updated.phone_verified is True
    assert updated.phone_verification_source == PHONE_VERIFICATION_SOURCE_TELEGRAM
    assert updated.language_code == "en"
