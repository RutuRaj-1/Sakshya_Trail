"""
Instruments Module - API Router
Versioned endpoints for instrument registry, search, retrieval, creation, and updating.
Enforces role-based authorization dependencies and delegates business logic to the service layer.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.auth.dependencies import (
    get_current_active_user,
    verify_csrf_origin,
)
from app.modules.instruments.schemas import (
    InstrumentResponse,
    InstrumentCreate,
    InstrumentUpdate,
    InstrumentListResponse,
    InstrumentSummary,
)
from app.modules.instruments.service import (
    list_instruments,
    get_instrument_by_id,
    create_instrument,
    update_instrument,
    get_instruments_summary,
)

router = APIRouter(prefix="/instruments", tags=["Instruments"])


@router.get("", response_model=InstrumentListResponse)
def list_registered_instruments(
    search: Optional[str] = Query(None, description="Search by reference, bank name, or institution"),
    institution_id: Optional[str] = Query(None, description="Filter by parent institution ID"),
    city: Optional[str] = Query(None, description="Filter by institution city (e.g. Pune, Mumbai)"),
    is_synthetic: Optional[bool] = Query(None, description="Filter by synthetic demonstration status"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by administrative status"),
    trust_level: Optional[str] = Query(None, description="Filter by trust level (L0-L3)"),
    maturity_start: Optional[date] = Query(None, description="Filter instruments maturing on or after date"),
    maturity_end: Optional[date] = Query(None, description="Filter instruments maturing on or before date"),
    maturity_indicator: Optional[str] = Query(None, description="Filter by derived maturity indicator (ACTIVE, EXPIRING_SOON, MATURED)"),
    sort_by: str = Query("created_at", description="Sort field: created_at, maturity_date, issue_date, amount, reference_number, bank_name"),
    sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve registered financial instruments with pagination, search, filters, and allow-listed sorting.
    Enforces record scoping for INSTITUTION_USER.
    """
    items, total = list_instruments(
        db=db,
        current_user=current_user,
        search=search,
        institution_id=institution_id,
        city=city,
        is_synthetic=is_synthetic,
        status_filter=status_filter,
        trust_level=trust_level,
        maturity_start=maturity_start,
        maturity_end=maturity_end,
        maturity_indicator=maturity_indicator,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    return InstrumentListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/summary", response_model=InstrumentSummary)
def get_summary_metrics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Executive summary metrics for statutory deposit oversight.
    """
    summary = get_instruments_summary(db=db, current_user=current_user)
    return InstrumentSummary(**summary)


@router.get("/{instrument_id}", response_model=InstrumentResponse)
def retrieve_instrument(
    instrument_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve one authorized instrument by ID.
    Scoped for INSTITUTION_USER.
    """
    return get_instrument_by_id(
        db=db,
        current_user=current_user,
        instrument_id=instrument_id,
    )


@router.post("", response_model=InstrumentResponse, status_code=status.HTTP_201_CREATED)
def record_instrument(
    payload: InstrumentCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Record an initial Fixed Deposit Receipt (FDR) deposit.
    - Enforces ownership scoping for INSTITUTION_USER.
    - Requires active institution.
    - Validates amount and date boundaries.
    - Rejects trust escalation; starts at L0_DECLARED.
    - Conservative duplicate warning path.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    return create_instrument(
        db=db,
        current_user=current_user,
        payload=payload,
        request_ip=client_ip,
        request_id=request_id,
    )


@router.patch("/{instrument_id}", response_model=InstrumentResponse)
def patch_instrument(
    instrument_id: str,
    payload: InstrumentUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update permitted registry fields on an instrument:
    - Scoped for INSTITUTION_USER to their own draft/registered instruments.
    - Scrutiny Officer can make registry corrections, with audit trail.
    - Modifying parent institution_id is prohibited.
    - Trust level escalation is prohibited.
    - Unsupported status transitions are rejected.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    return update_instrument(
        db=db,
        current_user=current_user,
        instrument_id=instrument_id,
        payload=payload,
        request_ip=client_ip,
        request_id=request_id,
    )
