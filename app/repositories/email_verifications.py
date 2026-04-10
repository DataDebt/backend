from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.email_verification_token import EmailVerificationToken


class EmailVerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        consumed_at: datetime | None = None,
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            consumed_at=consumed_at,
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        statement = (
            select(EmailVerificationToken)
            .options(selectinload(EmailVerificationToken.user))
            .where(EmailVerificationToken.token_hash == token_hash)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def consume(
        self,
        token: EmailVerificationToken,
        consumed_at: datetime | None = None,
    ) -> EmailVerificationToken:
        if token.consumed_at is not None:
            return token
        token.consumed_at = consumed_at or datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(token)
        return token


EmailVerificationTokenRepository = EmailVerificationRepository
