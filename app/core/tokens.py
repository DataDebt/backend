from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from jose import jwt

from app.core.config import settings


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(subject: str, username: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(subject),
        "username": username,
        "type": "access",
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


__all__ = ["generate_opaque_token", "hash_opaque_token", "create_access_token"]
