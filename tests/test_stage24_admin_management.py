from __future__ import annotations

from app.services import admin_service
from app.services.appeal_service import claim_appeal, create_appeal, get_appeal_by_id
from app.services.user_service import save_user


async def test_dynamic_admin_and_superadmin_roles(monkeypatch):
    monkeypatch.setattr(admin_service, "SUPERADMIN_IDS", [910000001])
    monkeypatch.setattr(admin_service, "ADMIN_IDS", [])

    assert await admin_service.get_admin_role(910000001) == admin_service.ROLE_SUPERADMIN
    assert await admin_service.is_superadmin(910000001)

    admin = await admin_service.add_or_update_admin(910000002, admin_service.ROLE_ADMIN, 910000001)
    superadmin = await admin_service.add_or_update_admin(
        910000003, admin_service.ROLE_SUPERADMIN, 910000001
    )
    assert admin.role == admin_service.ROLE_ADMIN
    assert superadmin.role == admin_service.ROLE_SUPERADMIN
    assert await admin_service.is_admin(910000002)
    assert not await admin_service.is_superadmin(910000002)
    assert await admin_service.is_superadmin(910000003)
    assert set(await admin_service.all_admin_ids()) >= {910000001, 910000002, 910000003}
    assert set(await admin_service.all_superadmin_ids()) >= {910000001, 910000003}


async def test_root_superadmin_is_not_removable(monkeypatch):
    monkeypatch.setattr(admin_service, "SUPERADMIN_IDS", [920000001])
    monkeypatch.setattr(admin_service, "ADMIN_IDS", [])
    assert not await admin_service.remove_dynamic_admin(920000001, 920000001)
    assert await admin_service.is_superadmin(920000001)


async def test_removing_dynamic_admin_releases_unfinished_appeal(monkeypatch):
    monkeypatch.setattr(admin_service, "SUPERADMIN_IDS", [930000001])
    monkeypatch.setattr(admin_service, "ADMIN_IDS", [])
    await admin_service.add_or_update_admin(930000002, admin_service.ROLE_ADMIN, 930000001)

    citizen_id = 930100001
    await save_user(citizen_id, "stage24", "Stage 24 Citizen", "+998901234567")
    appeal = await create_appeal(citizen_id, "Stage 24 removal release appeal")
    _, claimed = await claim_appeal(appeal.id, 930000002)
    assert claimed

    assert await admin_service.remove_dynamic_admin(930000002, 930000001)
    assert not await admin_service.is_admin(930000002)
    refreshed = await get_appeal_by_id(appeal.id)
    assert refreshed.status == "NEW"
    assert refreshed.admin_id is None
    assert refreshed.claim_expires_at is None


async def test_dynamic_superadmin_cannot_remove_self(monkeypatch):
    monkeypatch.setattr(admin_service, "SUPERADMIN_IDS", [940000001])
    monkeypatch.setattr(admin_service, "ADMIN_IDS", [])
    await admin_service.add_or_update_admin(940000002, admin_service.ROLE_SUPERADMIN, 940000001)
    assert not await admin_service.remove_dynamic_admin(940000002, 940000002)
    assert await admin_service.is_superadmin(940000002)
