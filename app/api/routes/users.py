from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_admin
from app.core.enums import UserRole
from app.repositories.users import UserRepository
from app.schemas.users import UserResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user=Depends(get_current_user)):
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
