from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        normalized_email = normalize_email(email)
        statement = select(User).where(User.email == normalized_email)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        username: str,
        password_hash: str,
        is_active: bool = True,
        is_verified: bool = False,
        last_login_at: datetime | None = None,
    ) -> User:
        user = User(
            email=normalize_email(email),
            username=username,
            password_hash=password_hash,
            is_active=is_active,
            is_verified=is_verified,
            last_login_at=last_login_at,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def count_admins(self) -> int:
        from app.core.enums import UserRole
        statement = select(func.count()).where(User.role == UserRole.admin)
        result = await self.session.execute(statement)
        return result.scalar_one()
