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


@router.post("/{institution_id}/verify-external")
def verify_institution_externally(
    institution_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Verify an institution against the external AICTE / AISHE regulatory registry provider.
    - Uses configured provider (Mock, Sandbox, or Live).
    - Preserves correlation ID, verified vs mismatched attributes, and audit evidence.
    - Does not overwrite authoritative institution identity directly without statutory review.
    """
    verify_csrf_origin(request)
    client_ip = request.client.host if request.client else None

    # Fetch institution
    inst = get_institution_by_id(db=db, current_user=current_user, institution_id=institution_id)

    # Call integration provider
    from app.modules.institutions.integrations.factory import get_institution_verification_provider
    from app.modules.audit.service import log_audit_event

    provider = get_institution_verification_provider()
    correlation_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id")
    result = provider.verify_institution(
        institution_code=inst.code,
        legal_name=inst.legal_name,
        expected_state=inst.state,
        correlation_id=correlation_id,
    )

    # Log immutable audit event
    log_audit_event(
        db=db,
        action="INSTITUTION_REGISTRY_VERIFIED",
        entity_type="institution",
        entity_id=inst.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS" if result.is_verified else "MISMATCH",
        ip_address=client_ip,
        metadata={
            "institution_code": inst.code,
            "provider_name": result.provider_name,
            "environment": result.environment,
            "correlation_id": result.correlation_id,
            "status": result.status,
            "official_approval_status": result.official_approval_status,
            "verified_fields": list(result.verified_fields.keys()),
            "mismatched_fields": list(result.mismatched_fields.keys()),
        },
    )

    return {
        "institution_id": inst.id,
        "institution_code": inst.code,
        "is_verified": result.is_verified,
        "status": result.status,
        "provider_name": result.provider_name,
        "environment": result.environment,
        "correlation_id": result.correlation_id,
        "timestamp": result.timestamp.isoformat(),
        "official_approval_status": result.official_approval_status,
        "handbook_year": result.handbook_year,
        "verified_fields": result.verified_fields,
        "mismatched_fields": result.mismatched_fields,
        "unsupported_fields": result.unsupported_fields,
        "notes": result.notes,
    }

