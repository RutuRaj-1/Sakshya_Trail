"""
Dashboard Schemas
Structured, typed responses for Module 1 executive and operational dashboard.
"""
from typing import Dict
from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    total_active_institutions: int = Field(..., description="Total active institutions within caller scope")
    total_inactive_institutions: int = Field(..., description="Total inactive/historical institutions within caller scope")
    total_instruments: int = Field(..., description="Total registered security deposit instruments within caller scope")
    total_deposit_value: str = Field(..., description="Aggregate monetary deposit value as exact decimal string")
    instruments_by_status: Dict[str, int] = Field(..., description="Instrument count grouped by administrative status")
    instruments_by_trust_level: Dict[str, int] = Field(..., description="Instrument count grouped by evidentiary trust level")
    instruments_approaching_maturity: int = Field(..., description="Instruments maturing within provisional 90-day window")
