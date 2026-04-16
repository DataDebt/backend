import os

# Set required environment variables before any app modules are imported.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-tests")
os.environ.setdefault("REFRESH_TOKEN_SECRET", "test-refresh-secret-for-tests")
os.environ.setdefault("CAPTURE_EMAILS_TO_FILES", "false")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db_session
from app.core.security import hash_password
from app.main import app as fastapi_app
from app.models.base import Base
from app.repositories.users import UserRepository

# Import all models to ensure they are registered with Base.metadata
import app.models.user  # noqa: F401
import app.models.email_verification_token  # noqa: F401
import app.models.refresh_token  # noqa: F401
import app.models.password_reset_token  # noqa: F401

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture()
async def db_engine():
    """Create a fresh in-memory SQLite engine per test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture()
async def db_session(db_engine):
    """Provide a transactional session that rolls back after each test."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
async def override_db_session(db_session):
    """Override FastAPI's get_db_session dependency with the test SQLite session."""

    async def _get_test_session():
        yield db_session

    fastapi_app.dependency_overrides[get_db_session] = _get_test_session
    yield
    fastapi_app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture()
async def verified_user(db_session):
    """Create a verified user and return (user, access_token)."""
    repo = UserRepository(db_session)
    user = await repo.create(
        email="alice@example.com",
        username="alice",
        password_hash=hash_password("secret123!"),
        is_verified=True,
    )
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "secret123!"},
        )
    tokens = resp.json()
    return user, tokens["access_token"]
