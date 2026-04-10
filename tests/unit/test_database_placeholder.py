import importlib
import sys

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


def _import_fresh_database_module():
    sys.modules.pop("app.core.config", None)
    sys.modules.pop("app.core.database", None)
    sys.modules.pop("app.models.base", None)
    return importlib.import_module("app.core.database")


def test_database_module_imports_without_unrelated_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("REFRESH_TOKEN_SECRET", raising=False)

    module = _import_fresh_database_module()

    assert module.__name__ == "app.core.database"


@pytest.mark.asyncio
async def test_sessionlocal_and_db_session_produce_async_session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("REFRESH_TOKEN_SECRET", raising=False)

    async def _noop_close(self):
        return None

    monkeypatch.setattr(AsyncSession, "close", _noop_close)

    module = _import_fresh_database_module()

    async with module.SessionLocal() as session:
        assert isinstance(session, AsyncSession)

    async for session in module.get_db_session():
        assert isinstance(session, AsyncSession)
        break
