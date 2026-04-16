import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.repositories.users import UserRepository
from app.core.security import hash_password
from app.core.enums import UserRole


@pytest.mark.asyncio
async def test_non_admin_cannot_make_admin(db_session, verified_user):
    """A regular user gets 403 when calling make-admin."""
    user, access_token = verified_user

    repo = UserRepository(db_session)
    target = await repo.create(
        email="bob@example.com",
        username="bob",
        password_hash=hash_password("secret123!"),
        is_verified=True,
    )
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/users/{target.id}/make-admin",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    assert response.status_code == 403


async def _make_admin_user(db_session, email: str, username: str):
    """Helper: create a verified user with admin role, return (user, access_token)."""
    repo = UserRepository(db_session)
    user = await repo.create(
        email=email,
        username=username,
        password_hash=hash_password("secret123!"),
        is_verified=True,
    )
    user.role = UserRole.admin
    await db_session.commit()
    await db_session.refresh(user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "secret123!"},
        )
    return user, resp.json()["access_token"]


@pytest.mark.asyncio
async def test_admin_can_promote_user_to_admin(db_session, verified_user):
    """Admin promoting a regular user returns 200 with role='admin'."""
    user, _ = verified_user
    admin, admin_token = await _make_admin_user(db_session, "admin@example.com", "adminuser")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/users/{user.id}/make-admin",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_admin_can_demote_admin(db_session, verified_user):
    """Admin demoting another admin returns 200 with role='user'."""
    _, _ = verified_user
    admin, admin_token = await _make_admin_user(db_session, "admin@example.com", "adminuser")
    second_admin, _ = await _make_admin_user(db_session, "admin2@example.com", "adminuser2")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/api/v1/users/{second_admin.id}/admin-role",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 200
    assert response.json()["role"] == "user"


@pytest.mark.asyncio
async def test_last_admin_cannot_be_demoted(db_session):
    """Removing the only admin returns 400."""
    admin, admin_token = await _make_admin_user(db_session, "admin@example.com", "adminuser")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete(
            f"/api/v1/users/{admin.id}/admin-role",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 400
    assert "last admin" in response.json()["detail"].lower()
