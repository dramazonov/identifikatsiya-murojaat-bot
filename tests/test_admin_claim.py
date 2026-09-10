"""Tests for the atomic first-claim-wins appeal/admin-contact claim.

MVP audit CRITICAL #2 / instruction #5: two admins racing to claim the same
appeal or admin-contact message must not both end up "handling" it (the old
unconditional UPDATE was last-write-wins). Uses the real (isolated, see
tests/conftest.py) test database -- this exercises the actual SQL, not a mock.
"""

from __future__ import annotations

import asyncio

from app.services.admin_contact_service import claim_admin_contact, create_admin_contact
from app.services.appeal_service import claim_appeal, create_appeal
from app.services.user_service import save_user

ADMIN_A = 5100001
ADMIN_B = 5100002


async def _make_appeal(telegram_id: int) -> int:
    await save_user(
        telegram_id=telegram_id,
        telegram_username="claimtester",
        full_name="Claim Test Testov",
        phone="+998901234567",
    )
    appeal = await create_appeal(telegram_id=telegram_id, appeal_text="Appeal text for claim tests.")
    return appeal.id


async def _make_admin_contact(telegram_id: int) -> int:
    contact = await create_admin_contact(
        telegram_id=telegram_id, telegram_username="claimtester", message_text="Contact message."
    )
    return contact.id


# --- Appeal claim ------------------------------------------------------------


async def test_first_admin_claims_appeal_second_is_rejected() -> None:
    appeal_id = await _make_appeal(telegram_id=920000001)

    appeal1, claimed1 = await claim_appeal(appeal_id, admin_id=ADMIN_A)
    assert claimed1 is True
    assert appeal1.admin_id == ADMIN_A
    assert appeal1.status == "IN_PROGRESS"

    appeal2, claimed2 = await claim_appeal(appeal_id, admin_id=ADMIN_B)
    assert claimed2 is False
    # Last-write-wins would show ADMIN_B here -- it must still be ADMIN_A.
    assert appeal2.admin_id == ADMIN_A
    assert appeal2.status == "IN_PROGRESS"


async def test_same_admin_reclaiming_appeal_is_idempotent() -> None:
    appeal_id = await _make_appeal(telegram_id=920000002)

    appeal1, claimed1 = await claim_appeal(appeal_id, admin_id=ADMIN_A)
    assert claimed1 is True

    # Simulates a redelivered Telegram callback_query for the same click
    # (instruction #4's idempotency requirement).
    appeal2, claimed2 = await claim_appeal(appeal_id, admin_id=ADMIN_A)
    assert claimed2 is False  # no second write happened...
    assert appeal2.admin_id == ADMIN_A  # ...but it's still "mine", not an error


async def test_claim_appeal_not_found_returns_none() -> None:
    appeal, claimed = await claim_appeal(appeal_id=999_999_999, admin_id=ADMIN_A)

    assert appeal is None
    assert claimed is False


async def test_concurrent_appeal_claims_only_one_wins() -> None:
    appeal_id = await _make_appeal(telegram_id=920000003)

    results = await asyncio.gather(
        claim_appeal(appeal_id, admin_id=ADMIN_A),
        claim_appeal(appeal_id, admin_id=ADMIN_B),
    )

    claimed_flags = [claimed for _, claimed in results]
    assert claimed_flags.count(True) == 1
    assert claimed_flags.count(False) == 1

    winner_admin_id = next(appeal.admin_id for appeal, claimed in results if claimed)
    for appeal, _claimed in results:
        # Both calls' returned rows agree on who actually won -- no split-brain.
        assert appeal.admin_id == winner_admin_id


# --- Admin-contact claim (mirrors the appeal claim above) --------------------


async def test_first_admin_claims_contact_second_is_rejected() -> None:
    contact_id = await _make_admin_contact(telegram_id=920000004)

    contact1, claimed1 = await claim_admin_contact(contact_id, admin_id=ADMIN_A)
    assert claimed1 is True
    assert contact1.admin_id == ADMIN_A

    contact2, claimed2 = await claim_admin_contact(contact_id, admin_id=ADMIN_B)
    assert claimed2 is False
    assert contact2.admin_id == ADMIN_A


async def test_concurrent_contact_claims_only_one_wins() -> None:
    contact_id = await _make_admin_contact(telegram_id=920000005)

    results = await asyncio.gather(
        claim_admin_contact(contact_id, admin_id=ADMIN_A),
        claim_admin_contact(contact_id, admin_id=ADMIN_B),
    )

    claimed_flags = [claimed for _, claimed in results]
    assert claimed_flags.count(True) == 1
    assert claimed_flags.count(False) == 1
