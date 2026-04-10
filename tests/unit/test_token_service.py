from datetime import datetime, timezone
import importlib
import sys

from jose import jwt


def _fresh_tokens_module():
    sys.modules.pop("app.core.config", None)
    sys.modules.pop("app.core.tokens", None)
    return importlib.import_module("app.core.tokens")


def test_generate_opaque_token_and_hash_are_distinct() -> None:
    tokens = _fresh_tokens_module()

    token = tokens.generate_opaque_token()
    hashed = tokens.hash_opaque_token(token)

    assert isinstance(token, str)
    assert isinstance(hashed, str)
    assert token != hashed
    assert hashed == tokens.hash_opaque_token(token)


def test_create_access_token_returns_jwt_string(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/app")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("REFRESH_TOKEN_SECRET", "refresh-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "7")

    tokens = _fresh_tokens_module()

    issued_at = datetime.now(timezone.utc).timestamp()
    token = tokens.create_access_token(subject="user-123", username="alice")
    payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
    verified_at = datetime.now(timezone.utc).timestamp()
    expected_lifetime = 7 * 60

    assert isinstance(token, str)
    assert payload["sub"] == "user-123"
    assert payload["username"] == "alice"
    assert payload["type"] == "access"
    assert tokens.settings.access_token_expire_minutes == 7
    assert issued_at + expected_lifetime - 5 <= payload["exp"] <= verified_at + expected_lifetime + 5
