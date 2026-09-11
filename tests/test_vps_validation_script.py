"""Exercise smoke-script operations and cleanup locally; not PostgreSQL validation."""
from sqlalchemy import func, select
from app.database import async_session
from app.models import User, Appeal, Suggestion, AdminContact
from scripts.validate_postgres import validate_services
import pytest
from unittest.mock import AsyncMock


async def counts():
    async with async_session() as session:
        return [await session.scalar(select(func.count()).select_from(model))
                for model in (User, Appeal, Suggestion, AdminContact)]


async def test_smoke_script_service_operations_clean_up_only_test_records():
    before = await counts()
    await validate_services()
    assert await counts() == before


async def test_smoke_script_cleans_up_after_failure(monkeypatch):
    import scripts.validate_postgres as script
    before = await counts()
    monkeypatch.setattr(script, "create_suggestion", AsyncMock(side_effect=RuntimeError("Injected")))
    with pytest.raises(RuntimeError, match="Injected"):
        await script.validate_services()
    assert await counts() == before
