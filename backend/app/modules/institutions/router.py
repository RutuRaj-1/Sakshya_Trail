"""
Institutions Module - API Router
Exposes versioned endpoints for institution registry, detail view, creation, update, and status management.
Enforces role-based authorization dependencies and delegates business logic to the service layer.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.auth.dependencies import (
    get_current_active_user,
    require_roles,
    verify_csrf_origin,
)
from app.core.security import ROLE_SYSTEM_ADMIN
from app.modules.institutions.schemas import (
    InstitutionResponse,
    InstitutionCreate,
    InstitutionUpdate,
    InstitutionStatusUpdate,
    InstitutionListResponse,
)
from app.modules.institutions.service import (
    list_institutions,
    get_institution_by_id,
    create_institution,
    update_institution,
    set_institution_status,
)

router = APIRouter(prefix="/institutions", tags=["Institutions"])


@router.get("", response_model=InstitutionListResponse)
def list_registered_institutions(
    search: Optional[str] = Query(None, description="Search by code, legal name, or display name"),
    city: Optional[str] = Query(None, description="Filter by city (e.g. Pune, Mumbai)"),
    state: Optional[str] = Query(None, description="Filter by state"),
    institution_type: Optional[str] = Query(None, description="Filter by institution taxonomy type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_synthetic: Optional[bool] = Query(None, description="Filter by synthetic demonstration status"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List institutions visible to the caller:
    - INSTITUTION_USER: Restricted to reading their own institution record.
    - Internal roles: Full regulatory inspection visibility across the system.
    """
    items, total = list_institutions(
        db=db,
        current_user=current_user,
        search=search,
        city=city,
        state=state,
        institution_type=institution_type,
        is_active=is_active,
        is_synthetic=is_synthetic,
        skip=skip,
        limit=limit,
    )
    return InstitutionListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{institution_id}", response_model=InstitutionResponse)
def retrieve_institution(
    institution_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve one authorized institution record.
    - INSTITUTION_USER: Allowed only if institution_id matches their assigned institution.
    - Inactive institutions remain retrievable for historical/audit continuity.
    """
    return get_institution_by_id(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
    )


@router.post("", response_model=InstitutionResponse, status_code=status.HTTP_201_CREATED)
def register_institution(
    payload: InstitutionCreate,
    request: Request,
    current_admin: User = Depends(require_roles(ROLE_SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Create a new registered institution.
    Authorized for SYSTEM_ADMIN only.
    Validates normalized code, uniqueness, and creates an audit trail entry.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    return create_institution(
        db=db,
        current_user=current_admin,
        payload=payload,
        request_ip=client_ip,
        request_id=request_id,
    )


@router.patch("/{institution_id}", response_model=InstitutionResponse)
def patch_institution(
    institution_id: str,
    payload: InstitutionUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update permitted fields of an institution:
    - SYSTEM_ADMIN: May update institutional, taxonomic, and contact fields.
    - INSTITUTION_USER: May update ONLY authorized contact and address details of their own institution.
    - All other roles: Read-only access; modification attempts are rejected with 403 Forbidden.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    return update_institution(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
        payload=payload,
        request_ip=client_ip,
        request_id=request_id,
    )


@router.post("/{institution_id}/status", response_model=InstitutionResponse)
def update_institution_status(
    institution_id: str,
    payload: InstitutionStatusUpdate,
    request: Request,
    current_admin: User = Depends(require_roles(ROLE_SYSTEM_ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Controlled activation/deactivation of an institution.
    Authorized for SYSTEM_ADMIN only.
    No physical deletions are performed to preserve historical records and audit events.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None
    request_id = request.headers.get("x-request-id")

    return set_institution_status(
        db=db,
        current_user=current_admin,
        institution_id=institution_id,
        is_active=payload.is_active,
        reason=payload.reason,
        request_ip=client_ip,
        request_id=request_id,
    )
