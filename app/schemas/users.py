from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, model_validator

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


class UpdateProfileRequest(BaseModel):
    username: str | None = None
    current_password: str | None = None
    new_password: str | None = None

    @model_validator(mode="after")
    def password_fields_consistent(self) -> "UpdateProfileRequest":
        if self.new_password and not self.current_password:
            raise ValueError("current_password is required when setting a new password")
        return self
