"""
Instruments Module - Pydantic Schemas
"""
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict


class InstrumentBase(BaseModel):
    institution_id: str
    reference_number: str = Field(..., description="FDR / Receipt Certificate Number")
    bank_name: str = Field(..., description="Issuing Bank Name")
    branch: Optional[str] = None
    amount: float = Field(..., gt=0, description="Principal Deposit Amount")
    currency: str = "INR"
    issue_date: date
    maturity_date: date
    status: str = "SUBMITTED"
    verification_level: str = "L1_DECLARED"
    joint_with_aicte: bool = True
    lien_marked: bool = True
    remarks: Optional[str] = None


class InstrumentCreate(InstrumentBase):
    pass


class InstrumentRead(InstrumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class InstrumentSummary(BaseModel):
    total_instruments: int
    active_count: int
    expiring_soon_count: int
    under_scrutiny_count: int
    released_count: int
    total_deposit_value: float
