"""
Institutions Module - Pydantic Request & Response Schemas
Includes bounds validation, normalization, and structured list responses.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator


class InstitutionBase(BaseModel):
    code: Optional[str] = Field(None, max_length=50, description="Normalized unique institution code")
    aicte_id: Optional[str] = Field(None, max_length=50, description="Legacy/display identifier alias")
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Full registered legal entity name")
    name: Optional[str] = Field(None, max_length=255, description="Alias for legal/display name")
    display_name: Optional[str] = Field(None, max_length=255, description="Common operating name")
    institution_type: Optional[str] = Field("TECHNICAL_INSTITUTE", max_length=100, description="Regulatory classification taxonomy")
    category: Optional[str] = Field(None, max_length=100, description="Alias for institution type")
    contact_name: Optional[str] = Field("Registrar / Nodal Officer", min_length=2, max_length=255)
    contact_email: EmailStr = Field(..., description="Official institutional contact email")
    contact_phone: Optional[str] = Field("+91-11-29581000", max_length=50)
    address_line1: Optional[str] = Field("Institutional Area", min_length=2, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field("New Delhi", min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: Optional[str] = Field("110001", min_length=4, max_length=20)
    assigned_office: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    status: Optional[str] = "ACTIVE"

    @field_validator("legal_name", "display_name", "contact_name", "city", "state", "postal_code", mode="before")
    @classmethod
    def trim_strings(cls, v):
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

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
    code: str = Field(..., min_length=2, max_length=50, description="Unique institution identifier")
    legal_name: str = Field(..., min_length=2, max_length=255, description="Mandatory official legal name")
    state: str = Field(..., min_length=2, max_length=100, description="State of operation")


class InstitutionUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255)
    institution_type: Optional[str] = Field(None, max_length=100)
    contact_name: Optional[str] = Field(None, min_length=2, max_length=255)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    address_line1: Optional[str] = Field(None, min_length=2, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    postal_code: Optional[str] = Field(None, min_length=4, max_length=20)
    assigned_office: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, min_length=2, max_length=50)


class InstitutionStatusUpdate(BaseModel):
    is_active: bool = Field(..., description="Target active status for institution")
    reason: Optional[str] = Field(None, max_length=500, description="Auditable administrative rationale")


class InstitutionResponse(InstitutionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    legal_name: str
    display_name: Optional[str] = None
    institution_type: str
    contact_name: str
    contact_email: EmailStr
    contact_phone: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    assigned_office: Optional[str] = None
    is_active: bool
    is_synthetic: bool
    created_at: datetime
    updated_at: datetime


# Alias for backwards compatibility
InstitutionRead = InstitutionResponse


class InstitutionListResponse(BaseModel):
    items: List[InstitutionResponse]
    total: int
    skip: int
    limit: int
