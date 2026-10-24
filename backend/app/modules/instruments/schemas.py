"""
Instruments Module - Pydantic Request & Response Schemas
Includes strict decimal amounts, separate administrative status, trust level (L0-L3),
date consistency validation, and duplicate reference warning responses.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class InstrumentBase(BaseModel):
    institution_id: str = Field(..., description="Parent institution UUID")
    instrument_type: str = Field("FDR", max_length=50, description="Instrument type (FDR)")
    bank_name: str = Field(..., min_length=2, max_length=200, description="Issuing bank institution name")
    branch: Optional[str] = Field(None, max_length=200, description="Issuing bank branch name or IFSC location")
    reference_number: str = Field(..., min_length=2, max_length=100, description="Certificate / FDR reference number")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Precise statutory deposit principal amount")
    currency: str = Field("INR", max_length=10, description="Monetary currency code")
    issue_date: date = Field(..., description="Instrument issuance date")
    maturity_date: date = Field(..., description="Instrument maturity date")
    lien_holder: Optional[str] = Field("AICTE Regulation Bureau", max_length=255, description="Lien beneficiary")
    lien_details: Optional[str] = Field(None, description="Detailed lien, pledge, or joint-holding clauses")
    assigned_office: Optional[str] = Field(None, max_length=100, description="Regional AICTE bureau office")
    remarks: Optional[str] = Field(None, max_length=500, description="Administrative remarks or observations")
    status: str = Field("REGISTERED", description="Administrative status (DRAFT, REGISTERED)")
    joint_with_aicte: bool = True
    lien_marked: bool = True

    @field_validator("bank_name", "branch", "reference_number", "lien_holder", "assigned_office", mode="before")
    @classmethod
    def trim_strings(cls, v):
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

    @model_validator(mode="after")
    def validate_dates(self):
        if self.maturity_date <= self.issue_date:
            raise ValueError("Maturity date must be strictly later than issue date.")
        return self


class InstrumentCreate(InstrumentBase):
    trust_level: str = Field("L0_DECLARED", description="Starting trust level must be L0_DECLARED")
    confirm_duplicate: bool = Field(
        default=False,
        description="Explicit flag to record instrument even if a potential duplicate warning was raised"
    )

    @field_validator("trust_level")
    @classmethod
    def validate_initial_trust_level(cls, v):
        if v not in ("L0_DECLARED", "L0 — DECLARED", "L0"):
            raise ValueError("New instruments must start at L0 — DECLARED trust level.")
        return "L0_DECLARED"

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, v):
        if v not in ("DRAFT", "REGISTERED", "SUBMITTED"):
            raise ValueError(f"Invalid initial status '{v}'. Initial registry status must be DRAFT, REGISTERED, or SUBMITTED.")
        return "REGISTERED" if v == "SUBMITTED" else v


class InstrumentUpdate(BaseModel):
    bank_name: Optional[str] = Field(None, min_length=2, max_length=200)
    branch: Optional[str] = Field(None, max_length=200)
    reference_number: Optional[str] = Field(None, min_length=2, max_length=100)
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(None, max_length=10)
    issue_date: Optional[date] = None
    maturity_date: Optional[date] = None
    lien_holder: Optional[str] = Field(None, max_length=255)
    lien_details: Optional[str] = None
    assigned_office: Optional[str] = Field(None, max_length=100)
    remarks: Optional[str] = Field(None, max_length=500)
    status: Optional[str] = None
    trust_level: Optional[str] = None
    confirm_duplicate: bool = Field(default=False)

    @field_validator("bank_name", "branch", "reference_number", "lien_holder", "assigned_office", mode="before")
    @classmethod
    def trim_strings(cls, v):
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class DuplicateWarningMatch(BaseModel):
    id: str
    reference_number: str
    bank_name: str
    institution_id: str
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    amount: Decimal
    issue_date: date
    maturity_date: date
    status: str
    trust_level: str
    created_at: datetime


class DuplicateWarningDetail(BaseModel):
    message: str
    matching_records: List[DuplicateWarningMatch]


class InstrumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    institution_code: Optional[str] = None
    institution_name: Optional[str] = None
    instrument_type: str
    bank_name: str
    branch: Optional[str] = None
    reference_number: str
    amount: Decimal
    currency: str
    issue_date: date
    maturity_date: date
    maturity_indicator: str
    lien_holder: Optional[str] = None
    lien_details: Optional[str] = None
    joint_with_aicte: bool
    lien_marked: bool
    assigned_office: Optional[str] = None
    status: str
    trust_level: str
    verification_level: str
    is_synthetic: bool
    created_by_user_id: Optional[str] = None
    updated_by_user_id: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Alias for backward compatibility
InstrumentRead = InstrumentResponse


class InstrumentListResponse(BaseModel):
    items: List[InstrumentResponse]
    total: int
    skip: int
    limit: int


class InstrumentSummary(BaseModel):
    total_instruments: int
    active_count: int
    expiring_soon_count: int
    under_scrutiny_count: int
    released_count: int
    total_deposit_value: Decimal
