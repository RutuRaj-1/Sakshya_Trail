"""
Auth Module - Pydantic Request & Response Schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Normalized user email address")
    password: str = Field(..., min_length=1, description="Account password")


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    institution_id: Optional[str] = None


class UserProvisionRequest(UserBase):
    password: str = Field(..., min_length=8, description="Initial account password")
    must_change_password: bool = Field(default=True, description="Force password rotation on first login")


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    success: bool = True
    message: str = "Authentication successful"
    user: UserRead
    token_type: str = "bearer"
    # Note: token is set in HttpOnly cookie; returned in payload for API/SDK clients
    access_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Current plaintext password for verification")
    new_password: str = Field(..., min_length=8, description="New secure password")
    confirm_new_password: str = Field(..., min_length=8, description="Confirm new password")

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("New password and confirmation do not match")
        if self.current_password == self.new_password:
            raise ValueError("New password cannot be identical to current password")
        return self


class RoleInfo(BaseModel):
    name: str
    display_name: str
    description: str
    is_internal: bool
    requires_institution: bool
