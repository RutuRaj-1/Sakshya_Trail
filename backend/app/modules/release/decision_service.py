"""
Module 6 — Release / Refund Case Management
Decision Service: Officer Review, Maker-Checker, and Authorized Transitions

Implements the official workflow for scrutiny review, officer observations,
authorized decisions, maker-checker separation of duties, and state machine
enforcement. Every material transition must be authorized and recorded.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from app.db.base import get_utc_now
from app.modules.auth.models import User
from app.modules.release.models import (
    ReleaseRequest,
    ReleaseChecklistProfile,
    ReadinessAssessment,
    ReleaseReviewObservation,
    ReleaseDecision,
    ReleaseOrderRecord,
)
from app.modules.release.enums import (
    ReleaseWorkflowStatus,
    ReleaseDecisionType,
    ReleaseOrderStatus,
    BankActionStatus,
)
from app.modules.release.schemas import (
    ReleaseDecisionCreate,
    ReviewObservationCreate,
    ReleaseOrderCreate,
)
from app.modules.release.readiness_service import (
    evaluate_readiness,
    check_release_gate,
)
from app.modules.audit.service import log_audit_event
from app.common.exceptions import (
    AppException,
    ForbiddenException,
    NotFoundException,
)

logger = logging.getLogger(__name__)


# ============================================================================
# State Machine & Transition Rules
# ============================================================================

class TransitionRule:
    """Defines allowed state transitions and their requirements."""
    
    def __init__(
        self,
        from_status: str,
        to_status: str,
        decision_type: str,
        required_roles: list[str],
        requires_readiness: bool = False,
        allows_blockers: bool = False,
        requires_reason: bool = True,
        description: str = "",
    ):
        self.from_status = from_status
        self.to_status = to_status
        self.decision_type = decision_type
        self.required_roles = required_roles
        self.requires_readiness = requires_readiness
        self.allows_blockers = allows_blockers
        self.requires_reason = requires_reason
        self.description = description


# Official state transition matrix
TRANSITION_MATRIX = [
    # Institution: Submit draft → submitted
    TransitionRule(
        from_status=ReleaseWorkflowStatus.DRAFT.value,
        to_status=ReleaseWorkflowStatus.SUBMITTED.value,
        decision_type=ReleaseDecisionType.SUBMIT.value,
        required_roles=["INSTITUTION_USER"],
        requires_reason=True,
        description="Institution submits release request for review",
    ),
    
    # Officer: Accept for review
    TransitionRule(
        from_status=ReleaseWorkflowStatus.SUBMITTED.value,
        to_status=ReleaseWorkflowStatus.UNDER_REVIEW.value,
        decision_type="START_REVIEW",
        required_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
        requires_reason=False,
        description="Officer begins scrutiny review",
    ),
    
    # Officer: Return for correction (from SUBMITTED or UNDER_REVIEW)
    TransitionRule(
        from_status=ReleaseWorkflowStatus.SUBMITTED.value,
        to_status=ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value,
        decision_type=ReleaseDecisionType.RETURN_FOR_CORRECTION.value,
        required_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
        requires_reason=True,
        description="Officer returns request to institution for deficiency correction",
    ),
    
    TransitionRule(
        from_status=ReleaseWorkflowStatus.UNDER_REVIEW.value,
        to_status=ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value,
        decision_type=ReleaseDecisionType.RETURN_FOR_CORRECTION.value,
        required_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
        requires_reason=True,
        description="Officer returns request to institution for deficiency correction",
    ),
    
    # Institution: Resubmit after correction
    TransitionRule(
        from_status=ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value,
        to_status=ReleaseWorkflowStatus.SUBMITTED.value,
        decision_type=ReleaseDecisionType.SUBMIT.value,
        required_roles=["INSTITUTION_USER"],
        requires_reason=True,
        description="Institution resubmits after corrections",
    ),
    
    # Officer: Route to authority (readiness checks pass)
    TransitionRule(
        from_status=ReleaseWorkflowStatus.UNDER_REVIEW.value,
        to_status=ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value,
        decision_type=ReleaseDecisionType.RECOMMEND_FOR_AUTHORITY.value,
        required_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
        requires_readiness=True,
        allows_blockers=False,
        requires_reason=True,
        description="Officer confirms readiness and routes to authority for approval",
    ),
    
    # Authority: Approve
    TransitionRule(
        from_status=ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value,
        to_status=ReleaseWorkflowStatus.APPROVED.value,
        decision_type=ReleaseDecisionType.APPROVE.value,
        required_roles=["COMPETENT_AUTHORITY"],
        requires_readiness=True,
        allows_blockers=False,
        requires_reason=True,
        description="Authorized competent authority approves release",
    ),
    
    # Authority: Reject
    TransitionRule(
        from_status=ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value,
        to_status=ReleaseWorkflowStatus.REJECTED.value,
        decision_type=ReleaseDecisionType.REJECT.value,
        required_roles=["COMPETENT_AUTHORITY"],
        requires_reason=True,
        description="Authorized competent authority rejects release",
    ),
    
    # Record release order after approval
    TransitionRule(
        from_status=ReleaseWorkflowStatus.APPROVED.value,
        to_status=ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value,
        decision_type="RECORD_RELEASE_ORDER",
        required_roles=["FINANCE_OFFICER"],
        requires_reason=False,
        description="Release order recorded after approval",
    ),
    
    # Bank action pending
    TransitionRule(
        from_status=ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value,
        to_status=ReleaseWorkflowStatus.BANK_SIDE_ACTION_PENDING.value,
        decision_type="PENDING_BANK_ACTION",
        required_roles=["FINANCE_OFFICER", "SYSTEM_ADMIN"],
        requires_reason=False,
        description="Awaiting bank-side action confirmation",
    ),
    
    # Completed when bank confirms
    TransitionRule(
        from_status=ReleaseWorkflowStatus.BANK_SIDE_ACTION_PENDING.value,
        to_status=ReleaseWorkflowStatus.COMPLETED.value,
        decision_type="CONFIRM_BANK_ACTION",
        required_roles=["FINANCE_OFFICER", "SYSTEM_ADMIN"],
        requires_reason=False,
        description="Bank action confirmed, case completed",
    ),
    
    # Close after completion
    TransitionRule(
        from_status=ReleaseWorkflowStatus.COMPLETED.value,
        to_status=ReleaseWorkflowStatus.CLOSED.value,
        decision_type="CLOSE_CASE",
        required_roles=["FINANCE_OFFICER", "SYSTEM_ADMIN"],
        requires_reason=False,
        description="Case formally closed",
    ),
    
    # Cancel from draft or submitted
    TransitionRule(
        from_status=ReleaseWorkflowStatus.DRAFT.value,
        to_status=ReleaseWorkflowStatus.CANCELLED.value,
        decision_type=ReleaseDecisionType.CANCEL.value,
        required_roles=["INSTITUTION_USER", "SYSTEM_ADMIN"],
        requires_reason=True,
        description="Institution cancels draft request",
    ),
    
    TransitionRule(
        from_status=ReleaseWorkflowStatus.SUBMITTED.value,
        to_status=ReleaseWorkflowStatus.CANCELLED.value,
        decision_type=ReleaseDecisionType.CANCEL.value,
        required_roles=["INSTITUTION_USER", "SYSTEM_ADMIN"],
        requires_reason=True,
        description="Institution cancels submitted request",
    ),
]


def find_transition_rule(
    from_status: str,
    to_status: str,
) -> Optional[TransitionRule]:
    """Finds the transition rule for a given state change."""
    for rule in TRANSITION_MATRIX:
        if rule.from_status == from_status and rule.to_status == to_status:
            return rule
    return None


# ============================================================================
# Authorization & Permission Checks
# ============================================================================

def check_user_authority(
    user: User,
    required_roles: list[str],
) -> Tuple[bool, Optional[str]]:
    """
    Checks if user has required role for an action.
    
    Returns:
        Tuple of (authorized: bool, denial_reason: Optional[str])
    """
    if not user:
        return False, "User not authenticated"
    
    if not user.is_active:
        return False, "User account is inactive"
    
    if user.role not in required_roles:
        return False, f"User role '{user.role}' not authorized. Required: {required_roles}"
    
    return True, None


def check_maker_checker_separation(
    db: Session,
    release_request: ReleaseRequest,
    current_user: User,
    decision_type: str,
) -> Tuple[bool, Optional[str]]:
    """
    Verifies maker-checker separation of duties constraints.
    
    Prevents:
    - Requester approving own request
    - Reviewer also being final approver
    - Same user performing prohibited role combinations
    
    Returns:
        Tuple of (allowed: bool, violation_reason: Optional[str])
    """
    # Get prior decisions
    prior_decisions = db.scalars(
        select(ReleaseDecision).where(
            ReleaseDecision.release_request_id == release_request.id
        ).order_by(ReleaseDecision.created_at.desc())
    ).all()
    
    # Check: Institution requester cannot approve
    if decision_type == ReleaseDecisionType.APPROVE.value:
        if current_user.id == release_request.requester_id:
            return False, "Requester cannot approve their own request"
        
        # Check if current user was the primary reviewer
        reviewer_decisions = [
            d for d in prior_decisions
            if d.decision_type in (
                ReleaseDecisionType.RETURN_FOR_CORRECTION.value,
                ReleaseDecisionType.RECOMMEND_FOR_AUTHORITY.value,
            )
        ]
        
        # If this user was the reviewer and approval requires separation, deny
        if reviewer_decisions:
            for rev_decision in reviewer_decisions:
                if rev_decision.actor_user_id == current_user.id:
                    # Approval by reviewer (no separation)
                    return False, "Reviewer cannot also be the final approver (separation of duties required)"
    
    return True, None


def check_maker_checker_allowed_for_policy(
    db: Session,
    release_request: ReleaseRequest,
) -> bool:
    """
    Checks if the applicable policy allows maker-checker separation.
    For now, returns True (separation always required in demo).
    Future: Consult policy configuration.
    """
    # Demo policy: separation always required
    return True


# ============================================================================
# Officer Review Operations
# ============================================================================

def start_review(
    db: Session,
    release_request: ReleaseRequest,
    current_user: User,
) -> ReleaseRequest:
    """
    Marks a submitted request as UNDER_REVIEW.
    Requires SCRUTINY_OFFICER role.
    """
    # Authorization
    auth_ok, auth_reason = check_user_authority(
        current_user,
        ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
    )
    if not auth_ok:
        raise ForbiddenException(auth_reason)
    
    # State validation
    if release_request.workflow_status != ReleaseWorkflowStatus.SUBMITTED.value:
        raise AppException(
            status_code=400,
            message=f"Cannot start review from status '{release_request.workflow_status}'",
            code="INVALID_TRANSITION",
        )
    
    # Transition
    release_request.workflow_status = ReleaseWorkflowStatus.UNDER_REVIEW.value
    release_request.assigned_reviewer_id = current_user.id
    release_request.version += 1
    db.commit()
    db.refresh(release_request)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_REVIEW_STARTED",
        entity_type="RELEASE_REQUEST",
        entity_id=release_request.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "old_status": ReleaseWorkflowStatus.SUBMITTED.value,
            "new_status": ReleaseWorkflowStatus.UNDER_REVIEW.value,
        },
    )
    
    return release_request


def add_review_observation(
    db: Session,
    release_request: ReleaseRequest,
    payload: ReviewObservationCreate,
    current_user: User,
) -> ReleaseReviewObservation:
    """
    Records a scrutiny observation (deficiency, note, blocking concern).
    Requires SCRUTINY_OFFICER role.
    """
    # Authorization
    auth_ok, auth_reason = check_user_authority(
        current_user,
        ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
    )
    if not auth_ok:
        raise ForbiddenException(auth_reason)
    
    # Create observation
    obs = ReleaseReviewObservation(
        release_request_id=release_request.id,
        officer_user_id=current_user.id,
        observation_type=payload.observation_type,
        notes=payload.notes.strip(),
        is_blocking=payload.is_blocking,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_OBSERVATION_RECORDED",
        entity_type="RELEASE_OBSERVATION",
        entity_id=obs.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "observation_type": obs.observation_type,
            "is_blocking": obs.is_blocking,
        },
    )
    
    return obs


def return_for_correction(
    db: Session,
    release_request: ReleaseRequest,
    reason: str,
    current_user: User,
    deficiency_references: Optional[list[str]] = None,
) -> ReleaseDecision:
    """
    Returns request to institution for correction.
    Requires officer role and valid reason.
    """
    # Authorization
    auth_ok, auth_reason = check_user_authority(
        current_user,
        ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
    )
    if not auth_ok:
        raise ForbiddenException(auth_reason)
    
    # Validate reason
    clean_reason = (reason or "").strip()
    if not clean_reason:
        raise AppException(
            status_code=400,
            message="Return-for-correction requires a meaningful reason",
            code="EMPTY_RETURN_REASON",
        )
    
    # State validation
    if release_request.workflow_status not in (
        ReleaseWorkflowStatus.SUBMITTED.value,
        ReleaseWorkflowStatus.UNDER_REVIEW.value,
    ):
        raise AppException(
            status_code=400,
            message=f"Cannot return for correction from status '{release_request.workflow_status}'",
            code="INVALID_TRANSITION",
        )
    
    # Get current readiness if available
    current_assessment = db.scalar(
        select(ReadinessAssessment).where(
            ReadinessAssessment.release_request_id == release_request.id
        ).order_by(desc(ReadinessAssessment.evaluated_at))
    )
    
    # Transition
    old_status = release_request.workflow_status
    release_request.workflow_status = ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value
    release_request.version += 1
    
    # Record decision
    decision = ReleaseDecision(
        release_request_id=release_request.id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        decision_type=ReleaseDecisionType.RETURN_FOR_CORRECTION.value,
        reason=clean_reason,
        policy_version=release_request.policy_version,
        readiness_assessment_id=current_assessment.id if current_assessment else None,
        evidence_references_json=json.dumps(deficiency_references) if deficiency_references else None,
        previous_status=old_status,
        new_status=ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_RETURNED_FOR_CORRECTION",
        entity_type="RELEASE_DECISION",
        entity_id=decision.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "old_status": old_status,
            "new_status": ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value,
            "deficiency_count": len(deficiency_references) if deficiency_references else 0,
        },
    )
    
    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="RELEASE_CASE_RETURNED",
            entity_type="RELEASE_CASE",
            entity_id=release_request.id,
            actor_user=current_user,
            instrument_id=release_request.instrument_id,
            institution_id=release_request.institution_id,
            resulting_state=ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value,
            details={
                "case_id": release_request.case_number,
                "reason": clean_reason,
            },
        )
        db.commit()
    except Exception:
        pass

    return decision


def recommend_for_authority(
    db: Session,
    release_request: ReleaseRequest,
    reason: str,
    current_user: User,
) -> ReleaseDecision:
    """
    Officer recommends request as ready for authority approval.
    Runs readiness gate check; blocks if mandatory blockers present.
    """
    # Authorization
    auth_ok, auth_reason = check_user_authority(
        current_user,
        ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
    )
    if not auth_ok:
        raise ForbiddenException(auth_reason)
    
    # Validate reason
    clean_reason = (reason or "").strip()
    if not clean_reason:
        raise AppException(
            status_code=400,
            message="Recommendation to authority requires a reason",
            code="EMPTY_REASON",
        )
    
    # State validation
    if release_request.workflow_status != ReleaseWorkflowStatus.UNDER_REVIEW.value:
        raise AppException(
            status_code=400,
            message=f"Cannot recommend for authority from status '{release_request.workflow_status}'",
            code="INVALID_TRANSITION",
        )
    
    # Gate check: Verify readiness
    gate_passes, gate_denial, assessment = check_release_gate(
        db=db,
        release_request=release_request,
        target_status=ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value,
        current_user=current_user,
    )
    
    if not gate_passes:
        raise AppException(
            status_code=400,
            message=f"Cannot route to authority: {gate_denial}",
            code="GATE_FAILED_MANDATORY_BLOCKERS",
        )
    
    # Transition
    old_status = release_request.workflow_status
    release_request.workflow_status = ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value
    release_request.version += 1
    
    # Record decision
    decision = ReleaseDecision(
        release_request_id=release_request.id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        decision_type=ReleaseDecisionType.RECOMMEND_FOR_AUTHORITY.value,
        reason=clean_reason,
        policy_version=release_request.policy_version,
        readiness_assessment_id=assessment.id if assessment else None,
        previous_status=old_status,
        new_status=ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_RECOMMENDED_FOR_AUTHORITY",
        entity_type="RELEASE_DECISION",
        entity_id=decision.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "old_status": old_status,
            "new_status": ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value,
        },
    )
    
    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="RELEASE_CASE_RECOMMENDED",
            entity_type="RELEASE_CASE",
            entity_id=release_request.id,
            actor_user=current_user,
            instrument_id=release_request.instrument_id,
            institution_id=release_request.institution_id,
            resulting_state=ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value,
            details={
                "case_id": release_request.case_number,
                "reason": clean_reason,
            },
        )
        db.commit()
    except Exception:
        pass

    return decision


# ============================================================================
# Authorized Approval / Rejection
# ============================================================================

def approve_release_request(
    db: Session,
    release_request: ReleaseRequest,
    reason: str,
    current_user: User,
) -> ReleaseDecision:
    """
    Authorized competent authority approves release.
    Verifies maker-checker separation and current readiness.
    """
    # Authorization: Release approval strictly restricted to Competent Authority (Admin denied approval authority)
    auth_ok, auth_reason = check_user_authority(
        current_user,
        ["COMPETENT_AUTHORITY"],
    )
    if not auth_ok:
        raise ForbiddenException("System Administrator role does not possess release approval authority. Approval strictly reserved for Competent Authority.")
    
    # Validate reason
    clean_reason = (reason or "").strip()
    if not clean_reason:
        raise AppException(
            status_code=400,
            message="Approval requires a meaningful reason",
            code="EMPTY_APPROVAL_REASON",
        )
    
    # State validation
    if release_request.workflow_status != ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value:
        raise AppException(
            status_code=400,
            message=f"Can only approve from READY_FOR_AUTHORITY status; currently '{release_request.workflow_status}'",
            code="INVALID_APPROVAL_STATE",
        )
    
    # Maker-checker check
    separation_ok, separation_reason = check_maker_checker_separation(
        db=db,
        release_request=release_request,
        current_user=current_user,
        decision_type=ReleaseDecisionType.APPROVE.value,
    )
    if not separation_ok:
        # Log denied attempt
        log_audit_event(
            db=db,
            action="RELEASE_APPROVAL_DENIED_MAKER_CHECKER",
            entity_type="RELEASE_REQUEST",
            entity_id=release_request.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            outcome="DENIED",
            metadata={
                "case_number": release_request.case_number,
                "reason": separation_reason,
            },
        )
        raise AppException(
            status_code=403,
            message=f"Approval denied: {separation_reason}",
            code="MAKER_CHECKER_VIOLATION",
        )
    
    # Gate check
    gate_passes, gate_denial, assessment = check_release_gate(
        db=db,
        release_request=release_request,
        target_status=ReleaseWorkflowStatus.APPROVED.value,
        current_user=current_user,
    )
    
    if not gate_passes:
        log_audit_event(
            db=db,
            action="RELEASE_APPROVAL_DENIED_GATE",
            entity_type="RELEASE_REQUEST",
            entity_id=release_request.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            outcome="DENIED",
            metadata={
                "case_number": release_request.case_number,
                "gate_denial": gate_denial,
            },
        )
        raise AppException(
            status_code=400,
            message=f"Approval blocked by Release Gate: {gate_denial}",
            code="GATE_FAILED_APPROVAL",
        )
    
    # Transition
    old_status = release_request.workflow_status
    release_request.workflow_status = ReleaseWorkflowStatus.APPROVED.value
    release_request.version += 1
    
    # Record decision
    decision = ReleaseDecision(
        release_request_id=release_request.id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        decision_type=ReleaseDecisionType.APPROVE.value,
        reason=clean_reason,
        policy_version=release_request.policy_version,
        readiness_assessment_id=assessment.id if assessment else None,
        previous_status=old_status,
        new_status=ReleaseWorkflowStatus.APPROVED.value,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_APPROVED",
        entity_type="RELEASE_DECISION",
        entity_id=decision.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "old_status": old_status,
            "new_status": ReleaseWorkflowStatus.APPROVED.value,
        },
    )
    
    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="RELEASE_CASE_APPROVED",
            entity_type="RELEASE_CASE",
            entity_id=release_request.id,
            actor_user=current_user,
            instrument_id=release_request.instrument_id,
            institution_id=release_request.institution_id,
            resulting_state=ReleaseWorkflowStatus.APPROVED.value,
            details={
                "case_id": release_request.case_number,
                "reason": clean_reason,
            },
        )
        db.commit()
    except Exception:
        pass

    return decision


def reject_release_request(
    db: Session,
    release_request: ReleaseRequest,
    reason: str,
    current_user: User,
) -> ReleaseDecision:
    """
    Authorized competent authority rejects release.
    """
    # Authorization: strictly restricted to COMPETENT_AUTHORITY
    auth_ok, auth_reason = check_user_authority(
        current_user,
        ["COMPETENT_AUTHORITY"],
    )
    if not auth_ok:
        raise ForbiddenException(auth_reason)
    
    # Validate reason
    clean_reason = (reason or "").strip()
    if not clean_reason:
        raise AppException(
            status_code=400,
            message="Rejection requires a meaningful reason",
            code="EMPTY_REJECTION_REASON",
        )
    
    # State validation
    if release_request.workflow_status != ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value:
        raise AppException(
            status_code=400,
            message=f"Can only reject from READY_FOR_AUTHORITY status; currently '{release_request.workflow_status}'",
            code="INVALID_REJECTION_STATE",
        )
    
    # Transition
    old_status = release_request.workflow_status
    release_request.workflow_status = ReleaseWorkflowStatus.REJECTED.value
    release_request.version += 1
    
    # Record decision
    decision = ReleaseDecision(
        release_request_id=release_request.id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        decision_type=ReleaseDecisionType.REJECT.value,
        reason=clean_reason,
        policy_version=release_request.policy_version,
        previous_status=old_status,
        new_status=ReleaseWorkflowStatus.REJECTED.value,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_REJECTED",
        entity_type="RELEASE_DECISION",
        entity_id=decision.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "old_status": old_status,
            "new_status": ReleaseWorkflowStatus.REJECTED.value,
        },
    )
    
    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="RELEASE_CASE_REJECTED",
            entity_type="RELEASE_CASE",
            entity_id=release_request.id,
            actor_user=current_user,
            instrument_id=release_request.instrument_id,
            institution_id=release_request.institution_id,
            resulting_state=ReleaseWorkflowStatus.REJECTED.value,
            details={
                "case_id": release_request.case_number,
                "reason": clean_reason,
            },
        )
        db.commit()
    except Exception:
        pass

    return decision


# ============================================================================
# Release Order Recording
# ============================================================================

def record_release_order(
    db: Session,
    release_request: ReleaseRequest,
    payload: ReleaseOrderCreate,
    current_user: User,
) -> ReleaseOrderRecord:
    """
    Records official release order after approval.
    Requires FINANCE_OFFICER role and verified metadata.
    """
    # Authorization: strictly restricted to FINANCE_OFFICER
    if current_user.role != "FINANCE_OFFICER":
        log_audit_event(
            db=db,
            action="RELEASE_ORDER_RECORDING_DENIED",
            entity_type="RELEASE_REQUEST",
            entity_id=release_request.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="DENIED",
            metadata={
                "case_number": release_request.case_number,
                "reason": f"Only Finance Officer is authorized to record release orders. Attempted by {current_user.role}.",
            },
        )
        raise ForbiddenException(f"Action forbidden for role '{current_user.role}'. Required: ['FINANCE_OFFICER']")
    
    # State validation
    if release_request.workflow_status != ReleaseWorkflowStatus.APPROVED.value:
        raise AppException(
            status_code=400,
            message="Can only record release order after APPROVED status",
            code="INVALID_ORDER_RECORDING_STATE",
        )
    
    # Idempotency / duplicate order check
    existing_order = db.scalar(
        select(ReleaseOrderRecord).where(
            ReleaseOrderRecord.release_request_id == release_request.id
        )
    )
    if existing_order:
        raise AppException(
            status_code=400,
            message=f"Release order already recorded for request '{release_request.id}'",
            code="DUPLICATE_RELEASE_ORDER",
        )
    
    # Create order record
    order = ReleaseOrderRecord(
        release_request_id=release_request.id,
        order_reference_number=payload.order_reference_number,
        order_date=payload.order_date,
        responsible_officer_id=current_user.id,
        supporting_document_id=payload.supporting_document_id,
        status=ReleaseOrderStatus.DRAFT_RECORDED.value,
        bank_action_status=BankActionStatus.PENDING.value,
        is_synthetic_demo=payload.is_synthetic_demo,
        notes=payload.notes,
    )
    db.add(order)
    
    # Transition request
    release_request.workflow_status = ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value
    release_request.version += 1
    
    db.commit()
    db.refresh(order)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_ORDER_RECORDED",
        entity_type="RELEASE_ORDER_RECORD",
        entity_id=order.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "order_reference": payload.order_reference_number,
            "order_date": payload.order_date.isoformat(),
        },
    )
    
    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="RELEASE_ORDER_RECORDED",
            entity_type="RELEASE_ORDER",
            entity_id=order.id,
            actor_user=current_user,
            instrument_id=release_request.instrument_id,
            institution_id=release_request.institution_id,
            resulting_state=ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value,
            details={
                "case_id": release_request.case_number,
                "release_order_number": payload.order_reference_number,
            },
        )
        db.commit()
    except Exception:
        pass

    return order


def confirm_bank_action(
    db: Session,
    release_request: ReleaseRequest,
    bank_action_notes: Optional[str],
    current_user: User,
) -> ReleaseRequest:
    """
    Confirms bank-side action completion.
    Transitions to COMPLETED.
    """
    # Authorization
    auth_ok, auth_reason = check_user_authority(
        current_user,
        ["FINANCE_OFFICER", "SYSTEM_ADMIN"],
    )
    if not auth_ok:
        raise ForbiddenException(auth_reason)
    
    # State validation
    if release_request.workflow_status not in (
        ReleaseWorkflowStatus.BANK_SIDE_ACTION_PENDING.value,
        ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value,
    ):
        raise AppException(
            status_code=400,
            message=f"Cannot confirm bank action from status '{release_request.workflow_status}'",
            code="INVALID_BANK_ACTION_STATE",
        )
    
    # Get release order
    order = db.scalar(
        select(ReleaseOrderRecord).where(
            ReleaseOrderRecord.release_request_id == release_request.id
        ).order_by(desc(ReleaseOrderRecord.created_at))
    )
    
    if order:
        order.bank_action_status = BankActionStatus.CONFIRMED.value
        order.bank_action_notes = bank_action_notes
        order.bank_action_confirmed_at = get_utc_now()
    
    # Transition
    old_status = release_request.workflow_status
    release_request.workflow_status = ReleaseWorkflowStatus.COMPLETED.value
    release_request.version += 1
    
    db.commit()
    db.refresh(release_request)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_BANK_ACTION_CONFIRMED",
        entity_type="RELEASE_REQUEST",
        entity_id=release_request.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "old_status": old_status,
            "new_status": ReleaseWorkflowStatus.COMPLETED.value,
        },
    )
    
    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="DOWNSTREAM_BANK_ACTION_RECORDED",
            entity_type="RELEASE_CASE",
            entity_id=release_request.id,
            actor_user=current_user,
            instrument_id=release_request.instrument_id,
            institution_id=release_request.institution_id,
            resulting_state=ReleaseWorkflowStatus.COMPLETED.value,
            details={
                "case_id": release_request.case_number,
                "bank_disbursement_reference": bank_action_notes or "CONFIRMED",
            },
        )
        db.commit()
    except Exception:
        pass

    return release_request


def close_release_case(
    db: Session,
    release_request: ReleaseRequest,
    closure_notes: Optional[str],
    current_user: User,
) -> ReleaseRequest:
    """
    Formally closes a completed case.
    Records closure metadata.
    """
    # Authorization
    auth_ok, auth_reason = check_user_authority(
        current_user,
        ["FINANCE_OFFICER", "SYSTEM_ADMIN"],
    )
    if not auth_ok:
        raise ForbiddenException(auth_reason)
    
    # State validation
    if release_request.workflow_status != ReleaseWorkflowStatus.COMPLETED.value:
        raise AppException(
            status_code=400,
            message=f"Can only close from COMPLETED status; currently '{release_request.workflow_status}'",
            code="INVALID_CLOSURE_STATE",
        )
    
    # Transition
    old_status = release_request.workflow_status
    release_request.workflow_status = ReleaseWorkflowStatus.CLOSED.value
    release_request.closed_at = get_utc_now()
    release_request.closure_notes = closure_notes
    release_request.version += 1
    
    db.commit()
    db.refresh(release_request)
    
    # Audit
    log_audit_event(
        db=db,
        action="RELEASE_CASE_CLOSED",
        entity_type="RELEASE_REQUEST",
        entity_id=release_request.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": release_request.case_number,
            "old_status": old_status,
            "new_status": ReleaseWorkflowStatus.CLOSED.value,
        },
    )

    # Module 5: Emit material event notification
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="RELEASE_CASE_CLOSED",
            entity_type="RELEASE_CASE",
            entity_id=release_request.id,
            actor_user=current_user,
            instrument_id=release_request.instrument_id,
            institution_id=release_request.institution_id,
            resulting_state=ReleaseWorkflowStatus.CLOSED.value,
            details={
                "case_number": release_request.case_number,
                "closure_notes": closure_notes,
            },
        )
        db.commit()
    except Exception:
        pass
    
    return release_request
