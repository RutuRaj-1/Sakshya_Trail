"""
Auth Module - Pydantic Schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "institution_user"
    institution_id: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoleInfo(BaseModel):
    name: str
    display_name: str
    description: str
