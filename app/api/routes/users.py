from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, require_admin
from app.schemas.users import UserResponse

router = APIRouter(tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user=Depends(get_current_user)):
    return current_user


@router.post("/{user_id}/make-admin", response_model=UserResponse)
async def make_admin(
    user_id: UUID,
    _admin=Depends(require_admin),
):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not yet implemented")
