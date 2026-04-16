from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.core.enums import UserRole


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    is_active: bool
    is_verified: bool
    role: UserRole
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}
