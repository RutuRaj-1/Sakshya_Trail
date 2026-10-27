"""
Module 6 — Release / Refund Case Management REST API Router
Exposes case creation, review observations, authorized decisions, release orders, and checklist profiles.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy import desc, select

from app.db.session import get_db
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_FINANCE_OFFICER,
    ROLE_INSTITUTION_USER,
    ALL_ROLES,
)
from app.modules.auth.dependencies import (
    get_current_user,
    require_roles,
    require_read_only_or_permitted,
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
from app.modules.release.decision_service import (
    start_review,
    return_for_correction,
    recommend_for_authority,
    approve_release_request,
    reject_release_request,
    record_release_order as record_release_order_decision,
    confirm_bank_action,
    close_release_case,
)
from app.modules.release.readiness_service import (
    evaluate_readiness,
    check_release_gate,
    is_assessment_stale,
)
from app.modules.release.schemas import (
    ReadinessAssessmentResponse,
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
    current_user: User = Depends(require_read_only_or_permitted),
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
    current_user: User = Depends(require_roles([ROLE_FINANCE_OFFICER])),
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


@router.post(
    "/requests/{id}/evaluate-readiness",
    response_model=ReadinessAssessmentResponse,
    status_code=200,
    summary="Evaluate readiness for a release request (creates assessment snapshot)",
)
def evaluate_readiness_endpoint(
    id: str = Path(...),
    force_reevaluate: bool = Query(False, description="Force reevaluation even if recent assessment exists"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY])),
):
    """
    Evaluates readiness of a release request against the configured checklist profile.
    Creates a new immutable assessment snapshot. Previous assessments remain intact.
    
    Returns detailed per-item evaluation results with evidence references.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    assessment = evaluate_readiness(db=db, release_request=request, current_user=current_user)
    return assessment


@router.get(
    "/requests/{id}/readiness",
    response_model=ReadinessAssessmentResponse,
    summary="Get latest readiness assessment for a request",
)
def get_latest_readiness_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the most recent readiness assessment for a release request.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    
    from sqlalchemy import desc, select
    from app.modules.release.models import ReadinessAssessment
    
    assessment = db.scalar(
        select(ReadinessAssessment)
        .where(ReadinessAssessment.release_request_id == request.id)
        .order_by(desc(ReadinessAssessment.evaluated_at))
    )
    
    if not assessment:
        raise NotFoundException("No readiness assessment available for this request.")
    
    return assessment


@router.get(
    "/requests/{id}/readiness/history",
    response_model=List[ReadinessAssessmentResponse],
    summary="Get assessment history for a request",
)
def get_readiness_history_endpoint(
    id: str = Path(...),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves historical readiness assessments for a release request.
    Assessments are returned in reverse chronological order (newest first).
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    
    from sqlalchemy import desc, select
    from app.modules.release.models import ReadinessAssessment
    
    assessments = list(
        db.scalars(
            select(ReadinessAssessment)
            .where(ReadinessAssessment.release_request_id == request.id)
            .order_by(desc(ReadinessAssessment.evaluated_at))
            .limit(limit)
        ).all()
    )
    
    return assessments


@router.post(
    "/requests/{id}/check-gate",
    status_code=200,
    summary="Check Release Gate before approval or routing",
)
def check_release_gate_endpoint(
    id: str = Path(...),
    target_status: str = Query("READY_FOR_AUTHORITY", description="Target workflow status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY])),
):
    """
    Server-side validation before state transitions.
    Checks readiness, staleness, and mandatory blockers.
    
    Returns:
        {
            "gate_passes": bool,
            "denial_reason": Optional[str],
            "assessment": ReadinessAssessmentResponse
        }
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    
    gate_passes, denial_reason, assessment = check_release_gate(
        db=db,
        release_request=request,
        target_status=target_status,
        current_user=current_user,
    )
    
    return {
        "gate_passes": gate_passes,
        "denial_reason": denial_reason,
        "assessment": assessment,
    }


# ============================================================================
# Module 6 Prompt 3: Officer Review & Authorized Decisions
# ============================================================================

@router.post(
    "/requests/{id}/start-review",
    response_model=ReleaseRequestResponse,
    status_code=200,
    summary="Officer accepts release request for scrutiny review (SUBMITTED → UNDER_REVIEW)",
)
def start_review_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    """
    Transitions request to UNDER_REVIEW state when officer begins scrutiny.
    No approval reason required at this stage.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    updated_request = start_review(db=db, release_request=request, current_user=current_user)
    return updated_request


@router.post(
    "/requests/{id}/return-for-correction",
    response_model=ReleaseDecisionResponse,
    status_code=201,
    summary="Officer identifies deficiencies and returns request to institution (→ RETURNED_FOR_CORRECTION)",
)
def return_for_correction_endpoint(
    id: str = Path(...),
    reason: str = Query(..., min_length=3, description="Mandatory deficiency notes"),
    deficiency_references: Optional[str] = Query(None, description="JSON references to deficiency findings"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    """
    Officer returns request for correction, recording the specific deficiencies.
    Request transitions SUBMITTED/UNDER_REVIEW → RETURNED_FOR_CORRECTION.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    decision = return_for_correction(
        db=db,
        release_request=request,
        reason=reason,
        current_user=current_user,
        deficiency_references=deficiency_references,
    )
    return decision


@router.post(
    "/requests/{id}/recommend-for-authority",
    response_model=ReleaseDecisionResponse,
    status_code=201,
    summary="Officer recommends release request for competent authority (UNDER_REVIEW → READY_FOR_AUTHORITY)",
)
def recommend_for_authority_endpoint(
    id: str = Path(...),
    reason: str = Query(..., min_length=3, description="Mandatory recommendation notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    """
    Officer completes scrutiny and recommends for authority approval.
    Validates Release Gate (no mandatory blockers).
    Transitions UNDER_REVIEW → READY_FOR_AUTHORITY.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    decision = recommend_for_authority(
        db=db,
        release_request=request,
        reason=reason,
        current_user=current_user,
    )
    return decision


@router.post(
    "/requests/{id}/approve",
    response_model=ReleaseDecisionResponse,
    status_code=201,
    summary="Competent authority approves release request (READY_FOR_AUTHORITY → APPROVED)",
)
def approve_release_request_endpoint(
    id: str = Path(...),
    reason: str = Query(..., min_length=3, description="Mandatory approval justification"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_COMPETENT_AUTHORITY])),
):
    """
    Competent authority grants final approval for release.
    Enforces maker-checker: current_user cannot be the original requester/reviewer.
    Validates Release Gate before approval.
    Transitions READY_FOR_AUTHORITY → APPROVED.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    decision = approve_release_request(
        db=db,
        release_request=request,
        reason=reason,
        current_user=current_user,
    )
    return decision


@router.post(
    "/requests/{id}/reject",
    response_model=ReleaseDecisionResponse,
    status_code=201,
    summary="Authority rejects release request (READY_FOR_AUTHORITY → REJECTED)",
)
def reject_release_request_endpoint(
    id: str = Path(...),
    reason: str = Query(..., min_length=3, description="Mandatory rejection rationale"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_COMPETENT_AUTHORITY])),
):
    """
    Authority rejects request, recording the decision rationale.
    Transitions READY_FOR_AUTHORITY → REJECTED.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    decision = reject_release_request(
        db=db,
        release_request=request,
        reason=reason,
        current_user=current_user,
    )
    return decision


@router.post(
    "/requests/{id}/record-order",
    response_model=ReleaseOrderResponse,
    status_code=201,
    summary="Record official release letter/order and bank routing (APPROVED → RELEASE_ORDER_RECORDED)",
)
def record_release_order_endpoint_decision(
    id: str = Path(...),
    payload: ReleaseOrderCreate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_FINANCE_OFFICER])),
):
    """
    Records official release letter (order reference, date, supporting docs).
    Transitions APPROVED → RELEASE_ORDER_RECORDED.
    Bank action status initialized to PENDING.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    order = record_release_order_decision(
        db=db,
        release_request=request,
        payload=payload,
        current_user=current_user,
    )
    return order


@router.post(
    "/requests/{id}/confirm-bank-action",
    response_model=ReleaseRequestResponse,
    status_code=200,
    summary="Confirm bank-side action on release order (BANK_SIDE_ACTION_PENDING → COMPLETED)",
)
def confirm_bank_action_endpoint(
    id: str = Path(...),
    bank_action_notes: Optional[str] = Query(None, description="Bank confirmation notes"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY, ROLE_FINANCE_OFFICER])),
):
    """
    Confirms that bank has executed the release order.
    Transitions BANK_SIDE_ACTION_PENDING → COMPLETED.
    Records confirmation timestamp and notes.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    updated_request = confirm_bank_action(
        db=db,
        release_request=request,
        bank_action_notes=bank_action_notes,
        current_user=current_user,
    )
    return updated_request


@router.post(
    "/requests/{id}/close-case",
    response_model=ReleaseRequestResponse,
    status_code=200,
    summary="Close release case (COMPLETED → CLOSED)",
)
def close_release_case_endpoint(
    id: str = Path(...),
    closure_notes: Optional[str] = Query(None, description="Case closure summary"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY, ROLE_FINANCE_OFFICER])),
):
    """
    Closes release case after completion.
    Transitions COMPLETED → CLOSED.
    Records closure notes and timestamp.
    """
    request = get_release_request(db=db, request_id=id, current_user=current_user)
    updated_request = close_release_case(
        db=db,
        release_request=request,
        closure_notes=closure_notes,
        current_user=current_user,
    )
    return updated_request

