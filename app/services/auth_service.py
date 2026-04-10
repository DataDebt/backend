from datetime import UTC, datetime, timezone

from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token, hash_opaque_token
from app.repositories.email_verifications import EmailVerificationRepository
from app.repositories.password_resets import PasswordResetRepository
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository, normalize_email
from app.services.token_service import TokenService


def _ensure_utc(dt: datetime) -> datetime:
    """Return dt as UTC-aware; if naive, assume it is already UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthService:
    def __init__(self, session):
        self.session = session
        self.users = UserRepository(session)
        self.verifications = EmailVerificationRepository(session)
        self.refresh_token_repo = RefreshTokenRepository(session)
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
        user = await self.users.get_by_email(normalize_email(email))
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        if not user.is_verified:
            raise PermissionError("Email not verified")

        raw_refresh, refresh_hash, refresh_expires_at = self.tokens.issue_refresh_token()
        await self.refresh_token_repo.create(user_id=user.id, token_hash=refresh_hash, expires_at=refresh_expires_at)
        user.last_login_at = datetime.now(UTC)
        await self.session.commit()
        access_token = create_access_token(subject=str(user.id), username=user.username)
        return access_token, raw_refresh, user

    async def confirm_email(self, raw_token: str):
        token = await self.verifications.get_by_hash(hash_opaque_token(raw_token))
        if not token or token.consumed_at or _ensure_utc(token.expires_at) < datetime.now(UTC):
            raise ValueError("Invalid or expired token")
        token.user.is_verified = True
        await self.verifications.consume(token)
        await self.session.commit()
        return token.user

    async def refresh_tokens(self, raw_refresh_token: str):
        token_hash = hash_opaque_token(raw_refresh_token)
        token = await self.refresh_token_repo.get_by_hash(token_hash)
        if not token or token.revoked_at or _ensure_utc(token.expires_at) < datetime.now(UTC):
            raise ValueError("Invalid or expired refresh token")

        # Rotate: revoke old token, issue new one
        await self.refresh_token_repo.revoke(token)
        raw_new_refresh, new_refresh_hash, new_refresh_expires_at = self.tokens.issue_refresh_token()
        await self.refresh_token_repo.create(
            user_id=token.user.id,
            token_hash=new_refresh_hash,
            expires_at=new_refresh_expires_at,
        )
        await self.session.commit()
        access_token = create_access_token(subject=str(token.user.id), username=token.user.username)
        return access_token, raw_new_refresh, token.user

    async def request_password_reset(self, email: str):
        # TODO: Timing side-channel — non-existent addresses return faster than existing
        # ones. Mitigate before production by adding a constant-time dummy operation on
        # the not-found path.
        user = await self.users.get_by_email(normalize_email(email))
        if not user:
            # Respond identically regardless of whether email exists
            return None, None
        raw_token, token_hash, expires_at = self.tokens.issue_password_reset_token()
        await self.password_resets.create(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        await self.session.commit()
        return raw_token, user

    async def reset_password(self, raw_token: str, new_password: str):
        token = await self.password_resets.get_by_hash(hash_opaque_token(raw_token))
        if not token or token.consumed_at or _ensure_utc(token.expires_at) < datetime.now(UTC):
            raise ValueError("Invalid or expired reset token")
        token.user.password_hash = hash_password(new_password)
        await self.password_resets.consume(token)
        await self.session.commit()
        return token.user

    async def resend_verification(self, email: str):
        user = await self.users.get_by_email(normalize_email(email))
        if not user or user.is_verified:
            # Return None silently to avoid email enumeration
            return None, None
        raw_token, token_hash, expires_at = self.tokens.issue_verification_token()
        await self.verifications.create(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
        await self.session.commit()
        return user, raw_token
