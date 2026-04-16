import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.repositories.users import UserRepository
from app.core.security import hash_password


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
