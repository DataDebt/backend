import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_register_email_uses_frontend_confirmation_url(db_session, monkeypatch):
    captured_calls = []

    def fake_send_email(*args, **kwargs):
        captured_calls.append((args, kwargs))

    monkeypatch.setattr("app.api.routes.auth.send_email", fake_send_email)
    monkeypatch.setattr("app.api.routes.auth.settings.frontend_base_url", "https://frontend.example.com")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123!"},
        )

    assert response.status_code == 201
    assert len(captured_calls) == 1

    args, _ = captured_calls[0]
    expected_url_prefix = "https://frontend.example.com/auth/confirm-email?token="
    metadata = args[4]
    assert args[2].startswith("<h1>Welcome, alice</h1>")
    assert expected_url_prefix in args[2]
    assert args[3] == f"Confirm your email: {metadata['confirm_url']}"
    assert metadata["username"] == "alice"
    assert metadata["confirm_url"].startswith(expected_url_prefix)


@pytest.mark.asyncio
async def test_password_reset_email_uses_frontend_reset_url(db_session, monkeypatch):
    captured_calls = []

    def fake_send_email(*args, **kwargs):
        captured_calls.append((args, kwargs))

    monkeypatch.setattr("app.api.routes.auth.send_email", fake_send_email)
    monkeypatch.setattr("app.api.routes.auth.settings.frontend_base_url", "https://frontend.example.com")

    service = AuthService(db_session)
    _, verification_token = await service.register_user("carol", "carol@example.com", "oldpassword123!")
    await service.confirm_email(verification_token)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "carol@example.com"},
        )

    assert response.status_code == 200
    assert len(captured_calls) == 1

    args, _ = captured_calls[0]
    expected_url_prefix = "https://frontend.example.com/auth/reset-password?token="
    metadata = args[4]
    assert args[2].startswith("<h1>Password reset</h1>")
    assert expected_url_prefix in args[2]
    assert args[3] == f"Reset your password: {metadata['reset_url']}"
    assert metadata["username"] == "carol"
    assert metadata["reset_url"].startswith(expected_url_prefix)
