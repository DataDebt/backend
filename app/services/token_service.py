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
