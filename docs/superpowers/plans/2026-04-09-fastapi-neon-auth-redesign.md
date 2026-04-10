# FastAPI + Neon Auth Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current Flask-based auth app with a FastAPI service backed by Neon PostgreSQL, adding refresh tokens, password reset, typed settings, migrations, async DB access, and a modern test suite.

**Architecture:** Build a modular FastAPI service under `app/` with routers, schemas, services, repositories, ORM models, and infrastructure helpers. Use SQLAlchemy async ORM against Neon, manage schema with Alembic, keep email handling inside the app via background tasks, and retire the old single-file Flask entrypoint after parity is reached. The config module should expose a public `settings` interface, but resolution may be lazy under the hood to avoid import-time failures before required environment variables are present. The database layer may likewise resolve only DB-relevant environment values lazily so importing `app.core.database` does not depend on unrelated auth secrets.

**Tech Stack:** FastAPI, Uvicorn, SQLAlchemy async ORM, asyncpg, Alembic, Pydantic settings, python-jose, passlib with argon2, pytest, pytest-asyncio, httpx

---

## File Structure

Target files to create or modify during implementation:

- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/api/__init__.py`
- Create: `app/api/router.py`
- Create: `app/api/deps.py`
- Create: `app/api/routes/__init__.py`
- Create: `app/api/routes/auth.py`
- Create: `app/api/routes/users.py`
- Create: `app/api/routes/health.py`
- Create: `app/core/__init__.py`
- Create: `app/core/config.py`
- Create: `app/core/database.py`
- Create: `app/core/security.py`
- Create: `app/core/tokens.py`
- Create: `app/models/__init__.py`
- Create: `app/models/base.py`
- Create: `app/models/user.py`
- Create: `app/models/email_verification_token.py`
- Create: `app/models/refresh_token.py`
- Create: `app/models/password_reset_token.py`
- Create: `app/repositories/__init__.py`
- Create: `app/repositories/users.py`
- Create: `app/repositories/email_verifications.py`
- Create: `app/repositories/refresh_tokens.py`
- Create: `app/repositories/password_resets.py`
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/auth.py`
- Create: `app/schemas/users.py`
- Create: `app/schemas/common.py`
- Create: `app/services/__init__.py`
- Create: `app/services/email_service.py`
- Create: `app/services/token_service.py`
- Create: `app/services/auth_service.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/<timestamp>_create_auth_tables.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_security.py`
- Create: `tests/unit/test_token_service.py`
- Create: `tests/integration/test_auth_flow.py`
- Create: `tests/integration/test_password_reset.py`
- Create: `tests/integration/test_users_me.py`
- Modify: `README.md`
- Delete later: `app.py`
- Delete later: `db.py`
- Delete later: `config.py`
- Delete later: `password_utils.py`
- Delete later: `email_service.py`
- Delete later: `test_api.py`

## Task 1: Bootstrap Project Packaging And Settings

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/core/config.py`

- [ ] **Step 1: Write the failing settings test**

```python
# tests/unit/test_settings_placeholder.py
from app.core.config import Settings


def test_settings_reads_database_url_and_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "super-secret-key")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret-key")

    settings = Settings()

    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/app"
    assert settings.secret_key == "super-secret-key"
    assert settings.refresh_token_secret == "refresh-secret-key"
    assert settings.app_name == "Auth Platform API"
    assert settings.environment == "development"
    assert settings.debug is True
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.access_token_expire_minutes == 15
    assert settings.refresh_token_expire_days == 7
    assert settings.verification_token_expire_hours == 24
    assert settings.password_reset_expire_hours == 1
    assert settings.smtp_host == ""
    assert settings.smtp_port == 587
    assert settings.smtp_user == ""
    assert settings.smtp_pass == ""
    assert settings.smtp_from == "noreply@example.com"
    assert settings.smtp_tls is True
    assert settings.capture_emails_to_files is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_settings_placeholder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'` or missing `Settings`

- [ ] **Step 3: Create packaging and typed settings**

```toml
# pyproject.toml
[project]
name = "auth-platform-api"
version = "0.1.0"
description = "FastAPI auth service backed by Neon PostgreSQL"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.116.0",
  "uvicorn[standard]>=0.35.0",
  "sqlalchemy>=2.0.40",
  "asyncpg>=0.30.0",
  "alembic>=1.16.0",
  "pydantic-settings>=2.10.0",
  "python-jose[cryptography]>=3.5.0",
  "passlib[argon2]>=1.7.4",
  "email-validator>=2.2.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=1.1.0",
  "httpx>=0.28.0",
  "ruff>=0.12.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```python
# app/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_name: str = "Auth Platform API"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(alias="DATABASE_URL")
    secret_key: str = Field(alias="SECRET_KEY")
    refresh_token_secret: str = Field(alias="REFRESH_TOKEN_SECRET")

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    verification_token_expire_hours: int = 24
    password_reset_expire_hours: int = 1

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "noreply@example.com"
    smtp_tls: bool = True
    capture_emails_to_files: bool = True


class _LazySettings:
    def __init__(self) -> None:
        self._instance: Settings | None = None

    def _get_instance(self) -> Settings:
        if self._instance is None:
            self._instance = Settings()
        return self._instance

    def __getattr__(self, name: str) -> object:
        return getattr(self._get_instance(), name)


settings = _LazySettings()
```

```env
# .env.example
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<database>?ssl=require
SECRET_KEY=change-me
REFRESH_TOKEN_SECRET=change-me-too
APP_NAME=Auth Platform API
ENVIRONMENT=development
DEBUG=true
API_V1_PREFIX=/api/v1
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=noreply@example.com
SMTP_TLS=true
CAPTURE_EMAILS_TO_FILES=true
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_settings_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example app/__init__.py app/core/__init__.py app/core/config.py tests/unit/test_settings_placeholder.py
git commit -m "chore: add project packaging and typed settings"
```

## Task 2: Add Async Database Infrastructure

**Files:**
- Create: `app/core/database.py`
- Create: `app/models/base.py`
- Create: `app/models/__init__.py`
- Test: `tests/unit/test_database_placeholder.py`

- [ ] **Step 1: Write the failing database test**

```python
# tests/unit/test_database_placeholder.py
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal


def test_session_factory_creates_async_sessions():
    session = SessionLocal()
    assert isinstance(session, AsyncSession)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_database_placeholder.py -v`
Expected: FAIL because `SessionLocal` does not exist

- [ ] **Step 3: Implement async engine and base model setup**

```python
# app/models/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

```python
# app/core/database.py
from os import getenv

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _coerce_debug(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() in {"1", "true", "yes", "on"}


_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        database_url = getenv("DATABASE_URL")
        if database_url is None:
            raise RuntimeError("DATABASE_URL is required to create the async engine")
        _engine = create_async_engine(
            database_url,
            echo=_coerce_debug(getenv("DEBUG")),
            pool_pre_ping=True,
        )
    return _engine


def SessionLocal() -> AsyncSession:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory()


async def get_db_session():
    async with SessionLocal() as session:
        yield session
```

```python
# app/models/__init__.py
from app.models.base import Base
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_database_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/database.py app/models/base.py app/models/__init__.py tests/unit/test_database_placeholder.py
git commit -m "feat: add async database infrastructure"
```

## Task 3: Define ORM Models For Users And Token Tables

**Files:**
- Create: `app/models/user.py`
- Create: `app/models/email_verification_token.py`
- Create: `app/models/refresh_token.py`
- Create: `app/models/password_reset_token.py`
- Modify: `app/models/__init__.py`
- Test: `tests/unit/test_models_placeholder.py`

- [ ] **Step 1: Write the failing model test**

```python
# tests/unit/test_models_placeholder.py
from app.models.user import User
from app.models.refresh_token import RefreshToken


def test_models_expose_expected_tablenames():
    assert User.__tablename__ == "users"
    assert RefreshToken.__tablename__ == "refresh_tokens"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_models_placeholder.py -v`
Expected: FAIL because model files do not exist

- [ ] **Step 3: Implement ORM models**

```python
# app/models/user.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
```

```python
# app/models/email_verification_token.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="verification_tokens")
```

```python
# app/models/refresh_token.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="refresh_tokens")
```

```python
# app/models/password_reset_token.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="password_reset_tokens")
```

```python
# app/models/__init__.py
from app.models.base import Base
from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_models_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/models/__init__.py app/models/user.py app/models/email_verification_token.py app/models/refresh_token.py app/models/password_reset_token.py tests/unit/test_models_placeholder.py
git commit -m "feat: add auth domain models"
```

## Task 4: Configure Alembic And Initial Migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/<timestamp>_create_auth_tables.py`
- Modify: `app/models/__init__.py`
- Test: `tests/unit/test_migration_placeholder.py`

- [ ] **Step 1: Write the failing migration test**

```python
# tests/unit/test_migration_placeholder.py
from pathlib import Path


def test_alembic_files_exist():
    assert Path("alembic.ini").exists()
    assert Path("alembic/env.py").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_migration_placeholder.py -v`
Expected: FAIL because Alembic files do not exist

- [ ] **Step 3: Add Alembic configuration and initial migration**

```python
# alembic/env.py
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def run():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    import asyncio
    asyncio.run(run())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

```python
# alembic/versions/<timestamp>_create_auth_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "<timestamp>"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash"),
    )


def downgrade():
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_table("users")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_migration_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add alembic.ini alembic/env.py alembic/script.py.mako alembic/versions app/models/__init__.py tests/unit/test_migration_placeholder.py
git commit -m "feat: add alembic migrations for auth schema"
```

## Task 5: Implement Security And Token Helpers

**Files:**
- Create: `app/core/security.py`
- Create: `app/core/tokens.py`
- Create: `tests/unit/test_security.py`
- Create: `tests/unit/test_token_service.py`

- [ ] **Step 1: Write the failing security tests**

```python
# tests/unit/test_security.py
from app.core.security import hash_password, verify_password


def test_hash_password_round_trip():
    password = "secret123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False
```

```python
# tests/unit/test_token_service.py
from app.core.tokens import create_access_token, hash_opaque_token, generate_opaque_token


def test_token_helpers_return_values():
    raw_token = generate_opaque_token()
    hashed = hash_opaque_token(raw_token)
    jwt_token = create_access_token(subject="user-123", username="alice")

    assert raw_token
    assert hashed != raw_token
    assert isinstance(jwt_token, str)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_security.py tests/unit/test_token_service.py -v`
Expected: FAIL because helper modules do not exist

- [ ] **Step 3: Implement password hashing and token helpers**

```python
# app/core/security.py
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
```

```python
# app/core/tokens.py
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import secrets

from jose import jwt

from app.core.config import settings


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_access_token(*, subject: str, username: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "username": username, "type": "access", "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_security.py tests/unit/test_token_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/security.py app/core/tokens.py tests/unit/test_security.py tests/unit/test_token_service.py
git commit -m "feat: add security and token helpers"
```

## Task 6: Add Repositories For Users And Tokens

**Files:**
- Create: `app/repositories/__init__.py`
- Create: `app/repositories/users.py`
- Create: `app/repositories/email_verifications.py`
- Create: `app/repositories/refresh_tokens.py`
- Create: `app/repositories/password_resets.py`
- Test: `tests/unit/test_repositories_placeholder.py`

- [ ] **Step 1: Write the failing repository test**

```python
# tests/unit/test_repositories_placeholder.py
from app.repositories.users import normalize_email


def test_normalize_email_lowercases_and_trims():
    assert normalize_email("  Alice@Example.com ") == "alice@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_repositories_placeholder.py -v`
Expected: FAIL because repository module does not exist

- [ ] **Step 3: Implement repositories**

```python
# app/repositories/users.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == normalize_email(email)))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id):
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> User:
        user = User(**kwargs)
        self.session.add(user)
        await self.session.flush()
        return user
```

```python
# app/repositories/email_verifications.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification_token import EmailVerificationToken


class EmailVerificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> EmailVerificationToken:
        token = EmailVerificationToken(**kwargs)
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()
```

```python
# app/repositories/refresh_tokens.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> RefreshToken:
        token = RefreshToken(**kwargs)
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        return result.scalar_one_or_none()
```

```python
# app/repositories/password_resets.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


class PasswordResetRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> PasswordResetToken:
        token = PasswordResetToken(**kwargs)
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self.session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_repositories_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/repositories/__init__.py app/repositories/users.py app/repositories/email_verifications.py app/repositories/refresh_tokens.py app/repositories/password_resets.py tests/unit/test_repositories_placeholder.py
git commit -m "feat: add repositories for users and tokens"
```

## Task 7: Add Pydantic Schemas For API Contracts

**Files:**
- Create: `app/schemas/__init__.py`
- Create: `app/schemas/common.py`
- Create: `app/schemas/auth.py`
- Create: `app/schemas/users.py`
- Test: `tests/unit/test_schemas_placeholder.py`

- [ ] **Step 1: Write the failing schema test**

```python
# tests/unit/test_schemas_placeholder.py
from app.schemas.auth import RegisterRequest


def test_register_schema_normalizes_email():
    model = RegisterRequest(username="alice", email=" Alice@Example.com ", password="secret123!")
    assert model.email == "alice@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_schemas_placeholder.py -v`
Expected: FAIL because schema module does not exist

- [ ] **Step 3: Implement request and response schemas**

```python
# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class MessageResponse(BaseModel):
    message: str


class AuthTokensResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

```python
# app/schemas/users.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_schemas_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas/__init__.py app/schemas/common.py app/schemas/auth.py app/schemas/users.py tests/unit/test_schemas_placeholder.py
git commit -m "feat: add pydantic schemas for auth api"
```

## Task 8: Implement Email Service With SMTP And Dev Capture

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/email_service.py`
- Test: `tests/unit/test_email_service_placeholder.py`

- [ ] **Step 1: Write the failing email service test**

```python
# tests/unit/test_email_service_placeholder.py
from app.services.email_service import build_email_verification_html


def test_verification_email_contains_link():
    html = build_email_verification_html("alice", "https://example.com/confirm")
    assert "alice" in html
    assert "https://example.com/confirm" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_email_service_placeholder.py -v`
Expected: FAIL because email service module does not exist

- [ ] **Step 3: Implement email service**

```python
# app/services/email_service.py
from datetime import UTC, datetime
import json
from pathlib import Path
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def build_email_verification_html(username: str, confirm_url: str) -> str:
    return f"<h1>Welcome, {username}</h1><p>Confirm your email: <a href='{confirm_url}'>{confirm_url}</a></p>"


def build_password_reset_html(username: str, reset_url: str) -> str:
    return f"<h1>Password reset</h1><p>{username}, reset your password: <a href='{reset_url}'>{reset_url}</a></p>"


def capture_email(to_email: str, subject: str, html: str, metadata: dict):
    emails_dir = Path("emails")
    emails_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    stem = f"{timestamp}_{to_email.replace('@', '_at_')}"
    (emails_dir / f"{stem}.json").write_text(json.dumps({"to": to_email, "subject": subject, **metadata}, indent=2))
    (emails_dir / f"{stem}.html").write_text(html)


def send_email(to_email: str, subject: str, html: str, text: str, metadata: dict | None = None):
    metadata = metadata or {}
    if settings.smtp_host and settings.smtp_user and settings.smtp_pass:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            if settings.smtp_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.sendmail(settings.smtp_from, to_email, msg.as_string())
    elif settings.capture_emails_to_files:
        capture_email(to_email, subject, html, metadata)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_email_service_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/__init__.py app/services/email_service.py tests/unit/test_email_service_placeholder.py
git commit -m "feat: add smtp email service with dev capture"
```

## Task 9: Implement Auth Service For Register, Verify, Login, Refresh, And Reset

**Files:**
- Create: `app/services/token_service.py`
- Create: `app/services/auth_service.py`
- Test: `tests/unit/test_auth_service_placeholder.py`

- [ ] **Step 1: Write the failing auth service test**

```python
# tests/unit/test_auth_service_placeholder.py
from app.services.auth_service import AuthService


def test_auth_service_class_exists():
    service = AuthService(session=None)
    assert service is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_auth_service_placeholder.py -v`
Expected: FAIL because auth service module does not exist

- [ ] **Step 3: Implement token and auth services**

```python
# app/services/token_service.py
from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.core.tokens import generate_opaque_token, hash_opaque_token


class TokenService:
    def issue_refresh_token(self):
        raw = generate_opaque_token()
        hashed = hash_opaque_token(raw)
        expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
        return raw, hashed, expires_at

    def issue_verification_token(self):
        raw = generate_opaque_token()
        hashed = hash_opaque_token(raw)
        expires_at = datetime.now(UTC) + timedelta(hours=settings.verification_token_expire_hours)
        return raw, hashed, expires_at

    def issue_password_reset_token(self):
        raw = generate_opaque_token()
        hashed = hash_opaque_token(raw)
        expires_at = datetime.now(UTC) + timedelta(hours=settings.password_reset_expire_hours)
        return raw, hashed, expires_at
```

```python
# app/services/auth_service.py
from datetime import UTC, datetime

from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token, hash_opaque_token
from app.repositories.email_verifications import EmailVerificationRepository
from app.repositories.password_resets import PasswordResetRepository
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository, normalize_email
from app.services.token_service import TokenService


class AuthService:
    def __init__(self, session):
        self.session = session
        self.users = UserRepository(session)
        self.verifications = EmailVerificationRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.password_resets = PasswordResetRepository(session)
        self.tokens = TokenService()

    async def register_user(self, username: str, email: str, password: str):
        normalized_email = normalize_email(email)
        if await self.users.get_by_email(normalized_email):
            raise ValueError("Email already registered")
        if await self.users.get_by_username(username):
            raise ValueError("Username already taken")

        user = await self.users.create(
            username=username,
            email=normalized_email,
            password_hash=hash_password(password),
            is_active=True,
            is_verified=False,
        )
        raw_token, token_hash, expires_at = self.tokens.issue_verification_token()
        await self.verifications.create(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        await self.session.commit()
        return user, raw_token

    async def login(self, email: str, password: str):
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        if not user.is_verified:
            raise PermissionError("Email not verified")

        raw_refresh, refresh_hash, refresh_expires_at = self.tokens.issue_refresh_token()
        await self.refresh_tokens.create(user_id=user.id, token_hash=refresh_hash, expires_at=refresh_expires_at)
        user.last_login_at = datetime.now(UTC)
        await self.session.commit()
        access_token = create_access_token(subject=str(user.id), username=user.username)
        return access_token, raw_refresh, user

    async def confirm_email(self, raw_token: str):
        token = await self.verifications.get_by_hash(hash_opaque_token(raw_token))
        if not token or token.consumed_at or token.expires_at < datetime.now(UTC):
            raise ValueError("Invalid or expired token")
        token.user.is_verified = True
        token.consumed_at = datetime.now(UTC)
        await self.session.commit()
        return token.user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_auth_service_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/token_service.py app/services/auth_service.py tests/unit/test_auth_service_placeholder.py
git commit -m "feat: add auth service workflows"
```

## Task 10: Add FastAPI Routers, Dependencies, And Application Entry Point

**Files:**
- Create: `app/api/__init__.py`
- Create: `app/api/router.py`
- Create: `app/api/deps.py`
- Create: `app/api/routes/__init__.py`
- Create: `app/api/routes/auth.py`
- Create: `app/api/routes/users.py`
- Create: `app/api/routes/health.py`
- Create: `app/main.py`
- Test: `tests/integration/test_health_placeholder.py`

- [ ] **Step 1: Write the failing health route test**

```python
# tests/integration/test_health_placeholder.py
from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_health_placeholder.py -v`
Expected: FAIL because FastAPI app and route files do not exist

- [ ] **Step 3: Implement FastAPI app and routers**

```python
# app/api/deps.py
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.repositories.users import UserRepository


async def get_session(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    return session


async def get_current_user(session: AsyncSession = Depends(get_session), authorization: str | None = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user = await UserRepository(session).get_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
```

```python
# app/api/routes/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck():
    return {"status": "ok"}
```

```python
# app/api/router.py
from fastapi import APIRouter

from app.api.routes import auth, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router, prefix="/users")
```

```python
# app/main.py
from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.include_router(api_router, prefix=settings.api_v1_prefix)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_health_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/__init__.py app/api/router.py app/api/deps.py app/api/routes/__init__.py app/api/routes/health.py app/api/routes/auth.py app/api/routes/users.py app/main.py tests/integration/test_health_placeholder.py
git commit -m "feat: add fastapi app and routers"
```

## Task 11: Implement Integration Tests And Complete Auth Endpoints

**Files:**
- Modify: `app/api/routes/auth.py`
- Modify: `app/api/routes/users.py`
- Create: `tests/conftest.py`
- Create: `tests/integration/test_auth_flow.py`
- Create: `tests/integration/test_password_reset.py`
- Create: `tests/integration/test_users_me.py`

- [ ] **Step 1: Write the failing integration tests**

```python
# tests/integration/test_auth_flow.py
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_register_login_refresh_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123!"},
        )
    assert register_response.status_code == 201
```

```python
# tests/integration/test_password_reset.py
def test_password_reset_flow_placeholder():
    assert False
```

```python
# tests/integration/test_users_me.py
def test_users_me_placeholder():
    assert False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_auth_flow.py tests/integration/test_password_reset.py tests/integration/test_users_me.py -v`
Expected: FAIL because endpoint implementations are incomplete and placeholder assertions fail

- [ ] **Step 3: Implement auth and user routes with service wiring**

```python
# app/api/routes/auth.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.auth import AuthTokensResponse, LoginRequest, MessageResponse, RefreshRequest, RegisterRequest
from app.services.auth_service import AuthService
from app.services.email_service import build_email_verification_html, send_email

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    try:
        user, raw_token = await service.register_user(payload.username, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    confirm_url = f"http://localhost:8000/api/v1/auth/confirm-email?token={raw_token}"
    html = build_email_verification_html(user.username, confirm_url)
    background_tasks.add_task(
        send_email,
        user.email,
        "Confirm your email",
        html,
        f"Confirm your email: {confirm_url}",
        {"confirm_url": confirm_url, "username": user.username},
    )
    return MessageResponse(message="Registration successful. Please check your email.")


@router.post("/login", response_model=AuthTokensResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    try:
        access_token, refresh_token, _ = await service.login(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return AuthTokensResponse(access_token=access_token, refresh_token=refresh_token)
```

```python
# app/api/routes/users.py
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.users import UserResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_auth_flow.py tests/integration/test_password_reset.py tests/integration/test_users_me.py -v`
Expected: PASS after replacing placeholder tests with real end-to-end cases and finishing route coverage for refresh and reset

- [ ] **Step 5: Commit**

```bash
git add app/api/routes/auth.py app/api/routes/users.py tests/conftest.py tests/integration/test_auth_flow.py tests/integration/test_password_reset.py tests/integration/test_users_me.py
git commit -m "feat: add auth endpoints and integration coverage"
```

## Task 12: Update Docs And Retire Legacy Flask Files

**Files:**
- Modify: `README.md`
- Delete: `app.py`
- Delete: `db.py`
- Delete: `config.py`
- Delete: `password_utils.py`
- Delete: `email_service.py`
- Delete: `test_api.py`

- [ ] **Step 1: Write the failing documentation check**

```python
# tests/unit/test_readme_placeholder.py
from pathlib import Path


def test_readme_mentions_fastapi():
    readme = Path("README.md").read_text()
    assert "FastAPI" in readme
    assert "Neon" in readme
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_readme_placeholder.py -v`
Expected: FAIL because README still describes Flask and the old stack

- [ ] **Step 3: Update docs and remove legacy files**

```markdown
# README.md
- Replace the old Flask + single-file setup instructions with FastAPI + Uvicorn commands.
- Document required env vars for Neon and SMTP.
- Document Alembic migration commands.
- Document core auth endpoints under `/api/v1`.
- Document test commands using `pytest`.
```

```bash
rm app.py db.py config.py password_utils.py email_service.py test_api.py
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_readme_placeholder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md tests/unit/test_readme_placeholder.py
git rm app.py db.py config.py password_utils.py email_service.py test_api.py
git commit -m "refactor: retire legacy flask app"
```

## Task 13: Final Verification

**Files:**
- Verify: `app/`
- Verify: `alembic/`
- Verify: `tests/`
- Verify: `README.md`

- [ ] **Step 1: Run lint and tests**

Run: `pytest -v`
Expected: PASS with all unit and integration tests green

- [ ] **Step 2: Run migration command**

Run: `alembic upgrade head`
Expected: PASS and auth tables created in the configured Neon database

- [ ] **Step 3: Run the app locally**

Run: `uvicorn app.main:app --reload`
Expected: server starts and `/api/v1/health` returns `{"status": "ok"}`

- [ ] **Step 4: Smoke test auth flow**

Run:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","email":"alice@example.com","password":"secret123!"}'
```

Expected: `201` with a message response and captured email or SMTP delivery

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "chore: verify fastapi neon auth redesign"
```
