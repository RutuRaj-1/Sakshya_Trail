"""
Instruments Module - API Router
Provides listing, registration, and administrative dashboard metrics for FDRs.
"""
from typing import List, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.session import get_db
from app.modules.instruments.models import Instrument
from app.modules.instruments.schemas import (
    InstrumentRead,
    InstrumentCreate,
    InstrumentSummary,
)

router = APIRouter(prefix="/instruments", tags=["Instruments"])


@router.get("", response_model=List[InstrumentRead])
def list_instruments(
    institution_id: Optional[str] = Query(None, description="Filter by institution"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
):
    """Retrieve financial instruments / FDR records."""
    stmt = select(Instrument)
    if institution_id:
        stmt = stmt.where(Instrument.institution_id == institution_id)
    if status_filter:
        stmt = stmt.where(Instrument.status == status_filter)
    results = db.scalars(stmt.limit(100)).all()
    return results


@router.post("", response_model=InstrumentRead, status_code=status.HTTP_201_CREATED)
def create_instrument(
    payload: InstrumentCreate,
    db: Session = Depends(get_db),
):
    """Record an initial Fixed Deposit Receipt (FDR) deposit."""
    inst = Instrument(
        institution_id=payload.institution_id,
        reference_number=payload.reference_number,
        bank_name=payload.bank_name,
        branch=payload.branch,
        amount=payload.amount,
        currency=payload.currency,
        issue_date=payload.issue_date,
        maturity_date=payload.maturity_date,
        status=payload.status,
        verification_level=payload.verification_level,
        joint_with_aicte=payload.joint_with_aicte,
        lien_marked=payload.lien_marked,
        remarks=payload.remarks,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


@router.get("/summary", response_model=InstrumentSummary)
def get_instruments_summary(db: Session = Depends(get_db)):
    """Executive KPI metrics for administrative oversight."""
    today = date.today()
    in_90_days = today + timedelta(days=90)

    total_count = db.scalar(select(func.count(Instrument.id))) or 0
    active_count = db.scalar(
        select(func.count(Instrument.id)).where(Instrument.status.in_(["SUBMITTED", "VERIFIED", "ACTIVE"]))
    ) or 0
    expiring_soon = db.scalar(
        select(func.count(Instrument.id)).where(
            Instrument.maturity_date >= today,
            Instrument.maturity_date <= in_90_days,
            Instrument.status != "RELEASED",
        )
    ) or 0
    scrutiny_count = db.scalar(
        select(func.count(Instrument.id)).where(Instrument.status.in_(["UNDER_SCRUTINY", "SUBMITTED"]))
    ) or 0
    released_count = db.scalar(
        select(func.count(Instrument.id)).where(Instrument.status == "RELEASED")
    ) or 0
    total_val = db.scalar(select(func.coalesce(func.sum(Instrument.amount), 0.0))) or 0.0

    return InstrumentSummary(
        total_instruments=total_count,
        active_count=active_count,
        expiring_soon_count=expiring_soon,
        under_scrutiny_count=scrutiny_count,
        released_count=released_count,
        total_deposit_value=float(total_val),
    )
