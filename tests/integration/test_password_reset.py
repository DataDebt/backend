import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_request_password_reset_always_returns_200(db_session):
    """Endpoint returns 200 regardless of whether email exists (prevents enumeration)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "nonexistent@example.com"},
        )
    assert response.status_code == 200
    assert "email has been sent" in response.json()["message"]


@pytest.mark.asyncio
async def test_reset_password_with_invalid_token_returns_400(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalidtoken1234567890", "new_password": "newpassword123!"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_password_reset_flow(db_session):
    """Full happy-path: register -> verify -> request reset -> reset -> login with new password."""
    service = AuthService(db_session)

    # Register and verify a user via the service
    _, verification_token = await service.register_user("carol", "carol@example.com", "oldpassword123!")
    await service.confirm_email(verification_token)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request a password reset
        reset_request_response = await client.post(
            "/api/v1/auth/request-password-reset",
            json={"email": "carol@example.com"},
        )
        assert reset_request_response.status_code == 200

    # Get the reset token directly via the service
    raw_reset_token, _ = await service.request_password_reset("carol@example.com")
    assert raw_reset_token is not None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Reset the password
        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_reset_token, "new_password": "newpassword123!"},
        )
        assert reset_response.status_code == 200

        # Old password should no longer work
        old_login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "carol@example.com", "password": "oldpassword123!"},
        )
        assert old_login_response.status_code == 401

        # New password should work
        new_login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "carol@example.com", "password": "newpassword123!"},
        )
        assert new_login_response.status_code == 200
        assert "access_token" in new_login_response.json()


@pytest.mark.asyncio
async def test_resend_verification_returns_200(db_session):
    """Resend endpoint always returns 200 to avoid email enumeration."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register a user
        await client.post(
            "/api/v1/auth/register",
            json={"username": "dave", "email": "dave@example.com", "password": "password123!"},
        )
        # Resend verification email
        response = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "dave@example.com"},
        )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_resend_verification_already_verified_returns_200(db_session):
    """Resend on an already-verified account returns 200 (no enumeration)."""
    service = AuthService(db_session)
    _, verification_token = await service.register_user("eve", "eve@example.com", "password123!")
    await service.confirm_email(verification_token)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/resend-verification",
            json={"email": "eve@example.com"},
        )
    assert response.status_code == 200
