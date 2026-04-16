import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.repositories.users import UserRepository
from app.core.security import hash_password


@pytest.mark.asyncio
async def test_update_username(db_session, verified_user):
    """PATCH /users/me with a new username returns 200 with updated username."""
    user, access_token = verified_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/users/me",
            json={"username": "alice_updated"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 200
    assert response.json()["username"] == "alice_updated"


@pytest.mark.asyncio
async def test_update_username_duplicate_returns_400(db_session, verified_user):
    """PATCH /users/me with an already-taken username returns 400."""
    user, access_token = verified_user

    repo = UserRepository(db_session)
    await repo.create(
        email="bob@example.com",
        username="bob",
        password_hash=hash_password("secret123!"),
        is_verified=True,
    )
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/users/me",
            json={"username": "bob"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 400
    assert "username" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_password_success(db_session, verified_user):
    """PATCH /users/me with correct current_password updates the password."""
    user, access_token = verified_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/users/me",
            json={"current_password": "secret123!", "new_password": "newpass456!"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 200

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "alice@example.com", "password": "newpass456!"},
        )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current_returns_400(db_session, verified_user):
    """PATCH /users/me with wrong current_password returns 400."""
    user, access_token = verified_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/users/me",
            json={"current_password": "wrongpassword!", "new_password": "newpass456!"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 400
    assert "password" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_new_password_without_current_returns_422(db_session, verified_user):
    """PATCH /users/me with new_password but no current_password returns 422."""
    user, access_token = verified_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/users/me",
            json={"new_password": "newpass456!"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 422
