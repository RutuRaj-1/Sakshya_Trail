"""
Auth Module - Pydantic Request & Response Schemas
Includes authentication, profile rotation, user provisioning, and user administration schemas.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator, field_validator


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Normalized user email address")
    password: str = Field(..., min_length=1, description="Account password")


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    institution_id: Optional[str] = None

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_name(cls, v):
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class UserProvisionRequest(UserBase):
    password: str = Field(..., min_length=8, description="Initial account password")
    must_change_password: bool = Field(default=True, description="Force password rotation on first login")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    role: Optional[str] = None
    institution_id: Optional[str] = None

    @field_validator("full_name", mode="before")
    @classmethod
    def trim_name(cls, v):
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class UserStatusUpdate(BaseModel):
    is_active: bool = Field(..., description="Target active account status")
    reason: Optional[str] = Field(None, max_length=500, description="Optional administrative rationale")


class UserResetPasswordRequest(BaseModel):
    temporary_password: Optional[str] = Field(None, min_length=8, description="Optional explicit temporary password")


class UserResetPasswordResponse(BaseModel):
    success: bool = True
    message: str = "Password reset successful"
    temporary_password: str
    must_change_password: bool = True


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: List[UserRead]
    total: int
    skip: int
    limit: int


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
