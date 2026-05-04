from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_admin
from app.core.enums import UserRole
from app.core.security import hash_password, verify_password
from app.repositories.users import UserRepository
from app.schemas.users import UpdateProfileRequest, UserResponse

router = APIRouter(tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
):
    repo = UserRepository(session)
    return await repo.get_all()


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user=Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    repo = UserRepository(session)

    if body.username is not None and body.username != current_user.username:
        existing = await repo.get_by_username(body.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        current_user.username = body.username

    if body.new_password:
        if not verify_password(body.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )
        current_user.password_hash = hash_password(body.new_password)

    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.post("/{user_id}/make-admin", response_model=UserResponse)
async def make_admin(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = UserRole.admin
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/{user_id}/admin-role", response_model=UserResponse)
async def remove_admin_role(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
):
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == UserRole.admin:
        admin_count = await repo.count_admins()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last admin",
            )
    user.role = UserRole.user
    await session.commit()
    await session.refresh(user)
    return user
