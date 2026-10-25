"""
Module 6 — Release / Refund Case Management REST API Router
Exposes case creation, review observations, authorized decisions, release orders, and checklist profiles.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path

from app.db.session import get_db
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_INSTITUTION_USER,
    ALL_ROLES,
)
from app.modules.auth.dependencies import (
    get_current_user,
    require_roles,
)
from app.modules.auth.models import User
from app.modules.release.models import ReleaseChecklistProfile
from app.modules.release.schemas import (
    ReleaseRequestCreate,
    ReleaseRequestResponse,
    ReleaseRequestDetailResponse,
    ChecklistProfileResponse,
    ReviewObservationCreate,
    ReviewObservationResponse,
    ReleaseDecisionCreate,
    ReleaseDecisionResponse,
    ReleaseOrderCreate,
    ReleaseOrderResponse,
)
from app.modules.release.service import (
    create_release_request,
    get_release_request,
    list_release_requests,
    add_review_observation,
    record_release_decision,
    record_release_order,
    resolve_checklist_profile,
    seed_demo_release_profile,
)
from app.common.exceptions import NotFoundException

router = APIRouter(prefix="/release", tags=["Module 6 — Release & Refund"])


@router.post(
    "/requests",
    response_model=ReleaseRequestResponse,
    status_code=201,
    summary="Create a new draft release, discharge, or refund request",
)
def create_release_request_endpoint(
    payload: ReleaseRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_release_request(db=db, payload=payload, current_user=current_user)


@router.get(
    "/requests",
    response_model=List[ReleaseRequestResponse],
    summary="List release requests within user institutional tenancy",
)
def list_release_requests_endpoint(
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _, records = list_release_requests(
        db=db,
        current_user=current_user,
        status=status,
        page=page,
        limit=limit,
    )
    return records


@router.get(
    "/requests/{id}",
    response_model=ReleaseRequestDetailResponse,
    summary="Get comprehensive release case details, assessments, and decision history",
)
def get_release_request_detail_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_release_request(db=db, request_id=id, current_user=current_user)


@router.post(
    "/requests/{id}/observations",
    response_model=ReviewObservationResponse,
    status_code=201,
    summary="Record a scrutiny officer observation or deficiency note",
)
def add_review_observation_endpoint(
    id: str = Path(...),
    payload: ReviewObservationCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY])),
):
    return add_review_observation(db=db, request_id=id, payload=payload, current_user=current_user)


@router.post(
    "/requests/{id}/decisions",
    response_model=ReleaseDecisionResponse,
    status_code=201,
    summary="Record an authorized workflow decision (submit, return, recommend, approve, reject)",
)
def record_release_decision_endpoint(
    id: str = Path(...),
    payload: ReleaseDecisionCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return record_release_decision(db=db, request_id=id, payload=payload, current_user=current_user)


@router.post(
    "/requests/{id}/orders",
    response_model=ReleaseOrderResponse,
    status_code=201,
    summary="Record an official release letter / order tracking entry",
)
def record_release_order_endpoint(
    id: str = Path(...),
    payload: ReleaseOrderCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY])),
):
    return record_release_order(db=db, request_id=id, payload=payload, current_user=current_user)


@router.get(
    "/profiles/active",
    response_model=ChecklistProfileResponse,
    summary="Get active checklist profile for request and case type",
)
def get_active_checklist_profile_endpoint(
    request_type: str = Query("RELEASE"),
    case_type: str = Query("STANDARD_MATURITY_RELEASE"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = resolve_checklist_profile(db=db, request_type=request_type, case_type=case_type)
    if not profile:
        profile = seed_demo_release_profile(db)
    return profile
