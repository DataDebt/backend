import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_register_returns_201(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123!"},
        )
    assert response.status_code == 201
    assert response.json()["message"] == "Registration successful. Please check your email."


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123!"},
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice2", "email": "alice@example.com", "password": "secret123!"},
        )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_duplicate_username_returns_409(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123!"},
        )
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice2@example.com", "password": "secret123!"},
        )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_unverified_user_returns_403(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123!"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "secret123!"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123!"},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "wrongpassword!"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_confirm_email_with_invalid_token_returns_400(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/confirm-email?token=invalidtoken12345678")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_login_refresh_flow(db_session):
    """Full happy-path: register -> confirm email -> login -> refresh."""
    service = AuthService(db_session)

    # Register directly via service to obtain the raw verification token
    _, raw_token = await service.register_user("bob", "bob@example.com", "password123!")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Confirm the email via HTTP
        confirm_response = await client.get(f"/api/v1/auth/confirm-email?token={raw_token}")
        assert confirm_response.status_code == 200

        # Login with confirmed account
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "bob@example.com", "password": "password123!"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # Refresh tokens
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        # Tokens should be rotated (different refresh token)
        assert new_tokens["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_get_me_returns_role(db_session, verified_user):
    user, access_token = verified_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 200
    assert response.json()["role"] == "user"


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_reused(db_session):
    # Set up: register, confirm, login to get tokens
    service = AuthService(db_session)
    user, verification_token = await service.register_user("replay_user", "replay@example.com", "secret123!")
    await service.confirm_email(verification_token)
    _, refresh_token, _ = await service.login("replay@example.com", "secret123!")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Use the refresh token once — should succeed
        first_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert first_response.status_code == 200

        # Try to use the same refresh token again — should fail (it was rotated/revoked)
        second_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert second_response.status_code == 401
