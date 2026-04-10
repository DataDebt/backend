from collections.abc import AsyncGenerator
from os import getenv

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _coerce_debug(value: str | None) -> bool:
    if value is None:
        return True

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", "release"}:
        return False
    return True


def _get_engine() -> AsyncEngine:
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


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


def SessionLocal() -> AsyncSession:
    return _get_session_factory()()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


__all__ = ["SessionLocal", "get_db_session"]
