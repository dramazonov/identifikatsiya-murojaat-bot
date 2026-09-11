from app.services.admin_contact_service import complete_admin_contact, create_admin_contact
from app.services.appeal_service import complete_appeal, create_appeal
from app.services.user_service import (
    PHONE_VERIFICATION_SOURCE_TELEGRAM,
    save_user,
)


async def test_failed_appeal_delivery_is_persisted_with_admin_answer():
    telegram_id = 950200001
    await save_user(
        telegram_id,
        "delivery",
        "Delivery User",
        "+998904444444",
        phone_verified=True,
        phone_verification_source=PHONE_VERIFICATION_SOURCE_TELEGRAM,
    )
    appeal = await create_appeal(telegram_id, "Delivery lifecycle test")
    completed = await complete_appeal(
        appeal.id,
        123456,
        "Stored answer",
        delivery_status="FAILED",
        delivery_error_code="TelegramForbiddenError",
    )
    assert completed.status == "COMPLETED"
    assert completed.admin_answer == "Stored answer"
    assert completed.delivery_status == "FAILED"
    assert completed.delivery_attempted_at is not None
    assert completed.delivery_error_code == "TelegramForbiddenError"


async def test_admin_contact_delivery_status_is_persisted():
    telegram_id = 950200002
    contact = await create_admin_contact(telegram_id, "contact_delivery", "Hello admin")
    completed = await complete_admin_contact(
        contact.id,
        123456,
        "Answer",
        delivery_status="DELIVERED",
    )
    assert completed.status == "COMPLETED"
    assert completed.delivery_status == "DELIVERED"
    assert completed.delivery_attempted_at is not None
    assert completed.delivery_error_code is None
