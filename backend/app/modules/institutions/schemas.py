"""
Institutions Module - Pydantic Schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class InstitutionBase(BaseModel):
    aicte_id: str = Field(..., description="Unique AICTE Institution Permanent ID (e.g. 1-10972341)")
    name: str = Field(..., description="Official Institution Name")
    state: str = Field(..., description="Indian State / UT")
    category: str = Field(default="Technical Institute", description="Discipline Category")
    contact_email: EmailStr = Field(..., description="Official nodal contact email")
    status: str = Field(default="ACTIVE", description="Regulatory Status")


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionRead(InstitutionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
