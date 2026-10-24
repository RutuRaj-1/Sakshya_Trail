"""
Institutions Module - Pydantic Schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator


class InstitutionBase(BaseModel):
    code: Optional[str] = None
    aicte_id: Optional[str] = None
    legal_name: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    institution_type: Optional[str] = "TECHNICAL_INSTITUTE"
    category: Optional[str] = None
    contact_name: Optional[str] = "Registrar"
    contact_email: EmailStr
    contact_phone: Optional[str] = "+91-11-20000000"
    address_line1: Optional[str] = "Institutional Area"
    city: Optional[str] = "New Delhi"
    state: str
    postal_code: Optional[str] = "110001"
    is_active: bool = True
    status: Optional[str] = "ACTIVE"

    @model_validator(mode="after")
    def unify_identifiers(self):
        if not self.code and self.aicte_id:
            self.code = self.aicte_id
        if not self.aicte_id and self.code:
            self.aicte_id = self.code
        if not self.legal_name and self.name:
            self.legal_name = self.name
        if not self.name and self.legal_name:
            self.name = self.legal_name
        if not self.category and self.institution_type:
            self.category = self.institution_type
        return self


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionRead(InstitutionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
