from __future__ import annotations

import asyncio

from app.i18n import t
from app.services.appeal_service import claim_appeal, complete_appeal, create_appeal, release_appeal_claim
from app.services.suggestion_service import create_suggestion, review_suggestion
from app.services.user_service import save_user


async def _user(telegram_id: int) -> None:
    await save_user(
        telegram_id=telegram_id,
        telegram_username="stage23",
        full_name="Stage Twenty Three",
        phone="+998901234567",
    )


async def test_appeal_claim_has_timeout_and_can_be_cancelled() -> None:
    telegram_id = 993230001
    await _user(telegram_id)
    appeal = await create_appeal(telegram_id, "Stage 23 appeal text long enough for validation.")

    claimed_appeal, claimed = await claim_appeal(appeal.id, 70001)
    assert claimed is True
    assert claimed_appeal.status == "IN_PROGRESS"
    assert claimed_appeal.admin_id == 70001
    assert claimed_appeal.claim_expires_at is not None

    released = await release_appeal_claim(appeal.id, 70001)
    assert released.status == "NEW"
    assert released.admin_id is None
    assert released.claim_expires_at is None


async def test_only_claim_owner_can_complete() -> None:
    telegram_id = 993230002
    await _user(telegram_id)
    appeal = await create_appeal(telegram_id, "Another Stage 23 appeal text for ownership checks.")
    await claim_appeal(appeal.id, 70011)

    assert await complete_appeal(appeal.id, 70012, "Wrong admin") is None
    completed = await complete_appeal(appeal.id, 70011, "Correct admin")
    assert completed is not None
    assert completed.status == "COMPLETED"
    assert completed.admin_id == 70011
    assert completed.claim_expires_at is None


async def test_suggestion_review_is_atomic_first_click_wins() -> None:
    telegram_id = 993230003
    await _user(telegram_id)
    suggestion = await create_suggestion(telegram_id, "Stage 23 suggestion for atomic review.")

    results = await asyncio.gather(
        review_suggestion(suggestion.id, 80001),
        review_suggestion(suggestion.id, 80002),
    )
    changed = [flag for _row, flag in results]
    assert changed.count(True) == 1
    assert changed.count(False) == 1
    reviewed = next(row for row, flag in results if flag)
    assert reviewed.status == "REVIEWED"
    assert reviewed.reviewed_by in {80001, 80002}
    assert reviewed.reviewed_at is not None


def test_suggestion_reviewed_text_is_localized() -> None:
    assert "ko‘rib chiqildi" in t("suggestion.reviewed", "uz_latn", suggestion_number="TAK-000001")
    assert "кўриб чиқилди" in t("suggestion.reviewed", "uz_cyrl", suggestion_number="TAK-000001").lower()
    assert "рассмотрено" in t("suggestion.reviewed", "ru", suggestion_number="TAK-000001").lower()
    assert "reviewed" in t("suggestion.reviewed", "en", suggestion_number="TAK-000001").lower()
