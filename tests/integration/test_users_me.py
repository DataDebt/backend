import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_users_me_without_token_returns_401(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_users_me_with_invalid_token_returns_401(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer notavalidtoken"},
        )
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.asyncio
async def test_users_me_with_valid_token_returns_user(db_session):
    """Register, verify, login, then GET /users/me returns the user's profile."""
    service = AuthService(db_session)

    # Register and verify a user via service
    _, verification_token = await service.register_user("frank", "frank@example.com", "password123!")
    await service.confirm_email(verification_token)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "frank@example.com", "password": "password123!"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Call /users/me with the access token
        me_response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200
        data = me_response.json()
        assert data["username"] == "frank"
        assert data["email"] == "frank@example.com"
        assert data["is_active"] is True
        assert data["is_verified"] is True
        assert "id" in data
        assert "created_at" in data
