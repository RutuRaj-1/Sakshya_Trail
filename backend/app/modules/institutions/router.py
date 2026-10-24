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
from app.common.schemas import StandardResponse

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
        aicte_id=payload.aicte_id,
        name=payload.name,
        state=payload.state,
        category=payload.category,
        contact_email=payload.contact_email,
        status=payload.status,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst
