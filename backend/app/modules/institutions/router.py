"""
Institutions Module - API Router
Handles institution registry and listing.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.modules.institutions.models import Institution
from app.modules.institutions.schemas import InstitutionRead, InstitutionCreate

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.get("", response_model=List[InstitutionRead])
def list_institutions(
    state: Optional[str] = Query(None, description="Filter by state"),
    db: Session = Depends(get_db),
):
    """List institutions registered under AICTE Regulation Bureau."""
    stmt = select(Institution)
    if state:
        stmt = stmt.where(Institution.state == state)
    results = db.scalars(stmt.limit(50)).all()
    return results


@router.post("", response_model=InstitutionRead, status_code=201)
def create_institution(
    payload: InstitutionCreate,
    db: Session = Depends(get_db),
):
    """Register a new institution for security deposit monitoring."""
    inst = Institution(
        code=payload.code or getattr(payload, "aicte_id", "AICTE-TEMP"),
        legal_name=payload.legal_name or getattr(payload, "name", "Technical Institute"),
        display_name=payload.display_name,
        institution_type=payload.institution_type or getattr(payload, "category", "TECHNICAL_INSTITUTE"),
        contact_name=payload.contact_name or "Registrar",
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone or "+91-11-20000000",
        address_line1=payload.address_line1 or "Institutional Area",
        city=payload.city or "New Delhi",
        state=payload.state,
        postal_code=payload.postal_code or "110001",
        is_active=payload.is_active,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst
