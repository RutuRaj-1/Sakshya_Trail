"""
Module 6 — Release / Refund Case Management Service
Core domain workflows for case management, checklist profiles, decision history, and release orders.
"""
import uuid
import logging
from datetime import date, datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc

from app.db.base import get_utc_now
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.release.models import (
    ReleaseRequest,
    ReleaseChecklistProfile,
    ReleaseChecklistItem,
    ReadinessAssessment,
    ReadinessCheckResult,
    ReleaseReviewObservation,
    ReleaseDecision,
    ReleaseOrderRecord,
)
from app.modules.release.enums import (
    ReleaseRequestType,
    ReleaseCaseType,
    ReleaseWorkflowStatus,
    ChecklistProfileStatus,
    ChecklistRequirementType,
    ChecklistEvaluationType,
    CheckResultStatus,
    ReadinessAssessmentOutcome,
    ReleaseDecisionType,
    ReleaseOrderStatus,
    BankActionStatus,
)
from app.modules.release.schemas import (
    ReleaseRequestCreate,
    ReleaseRequestUpdate,
    ChecklistProfileCreate,
    ReleaseDecisionCreate,
    ReviewObservationCreate,
    ReleaseOrderCreate,
)
from app.modules.audit.service import log_audit_event
from app.common.exceptions import AppException, ForbiddenException, NotFoundException

logger = logging.getLogger(__name__)

DEFAULT_DEMO_PROFILE_CODE = "DEMO_RELEASE_PROFILE"
DEMO_POLICY_DISCLAIMER = "DEMO RELEASE POLICY — NOT OFFICIAL AICTE POLICY"


# --- Safe Case Number Generation -----------------------------------------------

def generate_case_number(db: Session, request_type: str) -> str:
    """
    Safely generates human-readable, collision-resistant case numbers.
    Format: REL-YYYY-XXXXX or REF-YYYY-XXXXX
    """
    year = get_utc_now().year
    prefix = "REF" if request_type == ReleaseRequestType.REFUND.value else "REL"
    pattern = f"{prefix}-{year}-%"

    count = db.scalar(
        select(func.count(ReleaseRequest.id)).where(
            ReleaseRequest.case_number.like(pattern)
        )
    ) or 0

    return f"{prefix}-{year}-{(count + 1):05d}"


# --- Synthetic Demo Checklist Profile ------------------------------------------

def seed_demo_release_profile(db: Session, created_by_user_id: Optional[str] = None) -> ReleaseChecklistProfile:
    """
    Seeds the standard synthetic demo checklist profile for prototype verification.
    Clearly labelled with DEMO DISCLAIMER. Not official AICTE policy.
    """
    existing = db.scalar(
        select(ReleaseChecklistProfile).where(
            and_(
                ReleaseChecklistProfile.profile_code == DEFAULT_DEMO_PROFILE_CODE,
                ReleaseChecklistProfile.version == 1,
            )
        )
    )
    if existing:
        return existing

    profile = ReleaseChecklistProfile(
        profile_code=DEFAULT_DEMO_PROFILE_CODE,
        name="Demo FDR Release & Discharge Policy (Synthetic Prototype)",
        version=1,
        request_type=ReleaseRequestType.RELEASE.value,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE.value,
        status=ChecklistProfileStatus.ACTIVE.value,
        is_demo=True,
        demo_disclaimer=DEMO_POLICY_DISCLAIMER,
        description="Synthetic release criteria profile for prototype evaluation and testing. Not official AICTE policy.",
        created_by_user_id=created_by_user_id,
        approved_by_user_id=created_by_user_id,
        audit_reference="SEED-M6-DEMO-PROFILE-V1",
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    items = [
        ReleaseChecklistItem(
            profile_id=profile.id,
            item_code="ITEM_DOC_COMPLETENESS",
            title="Document Completeness Profile Satisfied",
            explanation="Requires mandatory FDR Receipt and Sanction Order uploaded and validated under Module 2.",
            requirement_type=ChecklistRequirementType.DOCUMENT_COMPLETENESS.value,
            is_mandatory_blocker=True,
            evaluation_type=ChecklistEvaluationType.AUTOMATED.value,
            expected_evidence_source="MODULE_2_DOCS",
            sort_order=10,
        ),
        ReleaseChecklistItem(
            profile_id=profile.id,
            item_code="ITEM_MIN_TRUST_LEVEL",
            title="Evidentiary Trust Level Verified (Minimum L2)",
            explanation="Requires instrument trust assessment to be at least L2 (Document Verified) or L3 (Bank Confirmed) under Module 4.",
            requirement_type=ChecklistRequirementType.TRUST_LEVEL.value,
            is_mandatory_blocker=True,
            evaluation_type=ChecklistEvaluationType.AUTOMATED.value,
            expected_evidence_source="MODULE_4_TRUST",
            sort_order=20,
        ),
        ReleaseChecklistItem(
            profile_id=profile.id,
            item_code="ITEM_ZERO_BLOCKING_FINDINGS",
            title="No Open Blocking Discrepancy Findings",
            explanation="Requires zero active blocking or high-severity discrepancy findings registered in Module 3.",
            requirement_type=ChecklistRequirementType.VALIDATION_FINDINGS.value,
            is_mandatory_blocker=True,
            evaluation_type=ChecklistEvaluationType.AUTOMATED.value,
            expected_evidence_source="MODULE_3_FINDINGS",
            sort_order=30,
        ),
        ReleaseChecklistItem(
            profile_id=profile.id,
            item_code="ITEM_MATURITY_OR_SUBSTITUTION",
            title="Maturity Reached or Active Successor Rollover",
            explanation="Requires FDR to have reached or passed statutory maturity date, OR have an approved active successor FDR linked under Module 5.",
            requirement_type=ChecklistRequirementType.LIFECYCLE_MATURITY.value,
            is_mandatory_blocker=True,
            evaluation_type=ChecklistEvaluationType.AUTOMATED.value,
            expected_evidence_source="MODULE_5_LIFECYCLE",
            sort_order=40,
        ),
        ReleaseChecklistItem(
            profile_id=profile.id,
            item_code="ITEM_INSTITUTION_NOC_AFFIDAVIT",
            title="Institutional Board Resolution & Undertaking",
            explanation="Advisory check verifying that the institution has uploaded governing body clearance.",
            requirement_type=ChecklistRequirementType.AFFIDAVIT_OR_NOC.value,
            is_mandatory_blocker=False,
            evaluation_type=ChecklistEvaluationType.HUMAN_REVIEW.value,
            expected_evidence_source="MODULE_2_DOCS",
            sort_order=50,
        ),
        ReleaseChecklistItem(
            profile_id=profile.id,
            item_code="ITEM_REGIONAL_OFFICE_CLEARANCE",
            title="Regional Bureau Scrutiny Officer Clearance",
            explanation="Mandatory officer administrative sign-off certifying no outstanding liabilities or penalties.",
            requirement_type=ChecklistRequirementType.MANUAL_CLEARANCE.value,
            is_mandatory_blocker=True,
            evaluation_type=ChecklistEvaluationType.HUMAN_REVIEW.value,
            expected_evidence_source="MANUAL_OFFICER_REVIEW",
            sort_order=60,
        ),
    ]
    for item in items:
        db.add(item)
    db.commit()
    db.refresh(profile)
    return profile


def resolve_checklist_profile(
    db: Session,
    request_type: str,
    case_type: str,
    profile_id: Optional[str] = None,
) -> Optional[ReleaseChecklistProfile]:
    """
    Deterministically resolves the active checklist profile for a given case.
    Reports None if unconfigured. Never invents an unconfigured policy.
    """
    if profile_id:
        return db.scalar(
            select(ReleaseChecklistProfile).where(
                and_(
                    ReleaseChecklistProfile.id == profile_id,
                    ReleaseChecklistProfile.status == ChecklistProfileStatus.ACTIVE.value,
                )
            )
        )

    # Resolve by criteria
    profile = db.scalar(
        select(ReleaseChecklistProfile)
        .where(
            and_(
                ReleaseChecklistProfile.request_type == request_type,
                ReleaseChecklistProfile.case_type == case_type,
                ReleaseChecklistProfile.status == ChecklistProfileStatus.ACTIVE.value,
            )
        )
        .order_by(desc(ReleaseChecklistProfile.version))
    )
    if profile:
        return profile

    # Fallback to demo profile if matching request_type
    demo = db.scalar(
        select(ReleaseChecklistProfile).where(
            and_(
                ReleaseChecklistProfile.profile_code == DEFAULT_DEMO_PROFILE_CODE,
                ReleaseChecklistProfile.status == ChecklistProfileStatus.ACTIVE.value,
            )
        )
    )
    return demo


# --- Release Request Case Operations -------------------------------------------

def create_release_request(
    db: Session,
    payload: ReleaseRequestCreate,
    current_user: User,
) -> ReleaseRequest:
    """
    Creates a new draft release/discharge/refund case.
    Business Invariants:
    1. Instrument must exist.
    2. Instrument's institution MUST match user's institution (if institution user).
    3. Reason must be non-empty.
    4. Active checklist profile must be resolved or validated.
    """
    instrument = db.scalar(select(Instrument).where(Instrument.id == payload.instrument_id))
    if not instrument:
        raise NotFoundException(f"Instrument '{payload.instrument_id}' not found.")

    # Auditor read-only restriction
    if current_user.role == "AUDITOR":
        raise ForbiddenException("Auditor role has strictly read-only inspection authority and cannot initiate release requests.")

    # Institutional tenancy check
    if current_user.role == "INSTITUTION_USER" and instrument.institution_id != current_user.institution_id:
        raise ForbiddenException("Access denied: You cannot create a release request for an instrument belonging to another institution.")

    reason = payload.request_reason.strip()
    if not reason:
        raise AppException(
            status_code=400,
            message="Request justification/reason cannot be empty or whitespace.",
            code="EMPTY_REASON",
        )

    # Resolve applicable checklist profile
    profile = resolve_checklist_profile(
        db=db,
        request_type=payload.request_type.value,
        case_type=payload.case_type.value,
        profile_id=payload.policy_profile_id,
    )

    if not profile:
        # Check if demo profile exists; if not, seed it for development/demo
        profile = seed_demo_release_profile(db, created_by_user_id=current_user.id)

    case_num = generate_case_number(db, payload.request_type.value)

    req = ReleaseRequest(
        case_number=case_num,
        instrument_id=instrument.id,
        institution_id=instrument.institution_id,
        request_type=payload.request_type.value,
        case_type=payload.case_type.value,
        policy_profile_id=profile.id if profile else None,
        policy_version=profile.version if profile else None,
        requester_id=current_user.id,
        request_reason=reason,
        workflow_status=ReleaseWorkflowStatus.DRAFT.value,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    log_audit_event(
        db=db,
        action="RELEASE_REQUEST_CREATED",
        entity_type="RELEASE_REQUEST",
        entity_id=req.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": req.case_number,
            "instrument_id": req.instrument_id,
            "institution_id": req.institution_id,
            "request_type": req.request_type,
        },
    )

    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="RELEASE_REQUEST_SUBMITTED",
            entity_type="RELEASE_CASE",
            entity_id=req.id,
            actor_user=current_user,
            instrument_id=req.instrument_id,
            institution_id=req.institution_id,
            resulting_state=req.workflow_status,
            details={
                "case_id": req.case_number,
                "request_type": req.request_type,
                "reason": req.request_reason,
            },
        )
        db.commit()
    except Exception:
        pass

    return req


def get_release_request(
    db: Session,
    request_id: str,
    current_user: User,
) -> ReleaseRequest:
    """
    Retrieves a release request case with tenancy verification.
    """
    req = db.scalar(select(ReleaseRequest).where(ReleaseRequest.id == request_id))
    if not req:
        raise NotFoundException(f"Release request '{request_id}' not found.")

    if current_user.role == "INSTITUTION_USER" and req.institution_id != current_user.institution_id:
        raise ForbiddenException("Access denied: Release request belongs to another institution.")

    return req


def list_release_requests(
    db: Session,
    current_user: User,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
) -> Tuple[int, List[ReleaseRequest]]:
    """
    Lists release request cases scoped by user tenancy and optional status filter.
    """
    stmt = select(ReleaseRequest)
    if current_user.role == "INSTITUTION_USER":
        stmt = stmt.where(ReleaseRequest.institution_id == current_user.institution_id)

    if status:
        stmt = stmt.where(ReleaseRequest.workflow_status == status)

    total = db.scalar(
        select(func.count(ReleaseRequest.id)).where(
            ReleaseRequest.institution_id == current_user.institution_id
            if current_user.role == "INSTITUTION_USER"
            else True
        )
    ) or 0

    records = list(
        db.scalars(
            stmt.order_by(desc(ReleaseRequest.created_at))
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return total, records


# --- Review Observations -------------------------------------------------------

def add_review_observation(
    db: Session,
    request_id: str,
    payload: ReviewObservationCreate,
    current_user: User,
) -> ReleaseReviewObservation:
    """
    Records scrutiny review notes or return instructions.
    """
    req = get_release_request(db, request_id, current_user)
    obs = ReleaseReviewObservation(
        release_request_id=req.id,
        officer_user_id=current_user.id,
        observation_type=payload.observation_type,
        notes=payload.notes.strip(),
        is_blocking=payload.is_blocking,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)

    log_audit_event(
        db=db,
        action="RELEASE_OBSERVATION_RECORDED",
        entity_type="RELEASE_OBSERVATION",
        entity_id=obs.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "release_request_id": req.id,
            "case_number": req.case_number,
            "observation_type": obs.observation_type,
            "is_blocking": obs.is_blocking,
        },
    )
    return obs


# --- Authorized Decisions ------------------------------------------------------

def record_release_decision(
    db: Session,
    request_id: str,
    payload: ReleaseDecisionCreate,
    current_user: User,
) -> ReleaseDecision:
    """
    Records an authorized workflow decision (SUBMIT, RETURN_FOR_CORRECTION, APPROVE, REJECT, etc.).
    Business Invariants:
    1. Reason must be non-empty.
    2. Previous and new workflow statuses must be captured.
    3. Status transition is updated on ReleaseRequest.
    """
    req = get_release_request(db, request_id, current_user)
    reason = payload.reason.strip()
    if not reason:
        raise AppException(
            status_code=400,
            message="Decision reason cannot be empty or whitespace.",
            code="EMPTY_DECISION_REASON",
        )

    # Defense-in-depth: Auditor cannot record decisions
    if current_user.role == "AUDITOR":
        raise ForbiddenException("Auditor role has strictly read-only access and cannot record decisions.")

    # Role-based decision permissions
    if payload.decision_type in (ReleaseDecisionType.APPROVE, ReleaseDecisionType.REJECT):
        if current_user.role != "COMPETENT_AUTHORITY":
            log_audit_event(
                db=db,
                action="RELEASE_DECISION_DENIED",
                entity_type="RELEASE_REQUEST",
                entity_id=req.id,
                actor_user_id=current_user.id,
                actor_email=current_user.email,
                actor_role=current_user.role,
                outcome="DENIED",
                metadata={
                    "case_number": req.case_number,
                    "attempted_decision": payload.decision_type.value,
                    "reason": f"Only Competent Authority may make statutory release decisions ({payload.decision_type.value}). Attempted by {current_user.role}.",
                },
            )
            raise ForbiddenException(
                f"Only Competent Authority may make statutory release decisions ({payload.decision_type.value}). Attempted by {current_user.role}."
            )

    elif payload.decision_type in (ReleaseDecisionType.RETURN_FOR_CORRECTION, ReleaseDecisionType.RECOMMEND_FOR_AUTHORITY):
        if current_user.role not in ("SCRUTINY_OFFICER", "BRANCH_HEAD"):
            raise ForbiddenException(
                f"Only scrutiny officers may review or recommend release requests. Attempted by {current_user.role}."
            )

    elif payload.decision_type in (ReleaseDecisionType.SUBMIT, ReleaseDecisionType.CANCEL):
        if current_user.role not in ("INSTITUTION_USER",):
            raise ForbiddenException(
                f"Action restricted to institution users. Attempted by {current_user.role}."
            )

    prev_status = req.workflow_status
    new_status = prev_status

    if payload.decision_type == ReleaseDecisionType.SUBMIT:
        if prev_status not in (ReleaseWorkflowStatus.DRAFT.value, ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value):
            raise AppException(status_code=400, message=f"Cannot submit request from status '{prev_status}'.", code="INVALID_TRANSITION")
        new_status = ReleaseWorkflowStatus.SUBMITTED.value
        req.submitted_at = get_utc_now()

    elif payload.decision_type == ReleaseDecisionType.RETURN_FOR_CORRECTION:
        if prev_status not in (ReleaseWorkflowStatus.SUBMITTED.value, ReleaseWorkflowStatus.UNDER_REVIEW.value):
            raise AppException(status_code=400, message=f"Cannot return for correction from status '{prev_status}'.", code="INVALID_TRANSITION")
        new_status = ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value

    elif payload.decision_type == ReleaseDecisionType.RECOMMEND_FOR_AUTHORITY:
        if prev_status not in (ReleaseWorkflowStatus.UNDER_REVIEW.value, ReleaseWorkflowStatus.SUBMITTED.value):
            raise AppException(status_code=400, message=f"Cannot recommend for authority from status '{prev_status}'.", code="INVALID_TRANSITION")
        new_status = ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value

    elif payload.decision_type == ReleaseDecisionType.APPROVE:
        if prev_status != ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value:
            raise AppException(status_code=400, message=f"Can only approve from READY_FOR_AUTHORITY status; currently '{prev_status}'", code="INVALID_APPROVAL_STATE")
        
        # Enforce maker-checker: current user cannot be creator or primary reviewer
        from app.modules.release.decision_service import check_maker_checker_separation
        separation_ok, separation_reason = check_maker_checker_separation(
            db=db,
            release_request=req,
            current_user=current_user,
            decision_type=ReleaseDecisionType.APPROVE.value,
        )
        if not separation_ok:
            raise AppException(
                status_code=403,
                message=f"Approval denied: {separation_reason}",
                code="MAKER_CHECKER_VIOLATION",
            )
        new_status = ReleaseWorkflowStatus.APPROVED.value

    elif payload.decision_type == ReleaseDecisionType.REJECT:
        if prev_status != ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value:
            raise AppException(status_code=400, message=f"Can only reject from READY_FOR_AUTHORITY status; currently '{prev_status}'", code="INVALID_REJECTION_STATE")
        new_status = ReleaseWorkflowStatus.REJECTED.value

    elif payload.decision_type == ReleaseDecisionType.CANCEL:
        if prev_status not in (ReleaseWorkflowStatus.DRAFT.value, ReleaseWorkflowStatus.SUBMITTED.value):
            raise AppException(status_code=400, message=f"Cannot cancel request from status '{prev_status}'.", code="INVALID_TRANSITION")
        new_status = ReleaseWorkflowStatus.CANCELLED.value

    req.workflow_status = new_status
    req.version += 1

    decision = ReleaseDecision(
        release_request_id=req.id,
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        decision_type=payload.decision_type.value,
        reason=reason,
        policy_version=req.policy_version,
        readiness_assessment_id=req.latest_assessment_id,
        evidence_references_json=payload.evidence_references_json,
        previous_status=prev_status,
        new_status=new_status,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    log_audit_event(
        db=db,
        action="RELEASE_DECISION_RECORDED",
        entity_type="RELEASE_DECISION",
        entity_id=decision.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome=new_status,
        metadata={
            "case_number": req.case_number,
            "decision_type": decision.decision_type,
            "previous_status": prev_status,
            "new_status": new_status,
        },
    )

    # Emit material event notification
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        event_type_map = {
            ReleaseDecisionType.APPROVE: "STATUTORY_RELEASE_SANCTIONED",
            ReleaseDecisionType.REJECT: "RELEASE_CASE_REJECTED",
            ReleaseDecisionType.RETURN_FOR_CORRECTION: "RELEASE_RETURNED_FOR_CORRECTION",
            ReleaseDecisionType.SUBMIT: "RELEASE_PETITION_SUBMITTED",
        }
        evt = event_type_map.get(payload.decision_type)
        if evt:
            emit_material_event(
                db=db,
                event_type=evt,
                entity_type="RELEASE_CASE",
                entity_id=req.id,
                actor_user=current_user,
                instrument_id=req.instrument_id,
                institution_id=req.institution_id,
                resulting_state=new_status,
                details={"case_id": req.case_number, "reason": reason},
            )
            db.commit()
    except Exception:
        pass

    return decision


# --- Release Order Records -----------------------------------------------------

def record_release_order(
    db: Session,
    request_id: str,
    payload: ReleaseOrderCreate,
    current_user: User,
) -> ReleaseOrderRecord:
    """
    Records an official release letter/order and sets bank action state.
    Distinct from approval: an approved case is not completed until release order
    is recorded and bank confirmation is tracked.
    """
    req = get_release_request(db, request_id, current_user)

    # Authorization: strictly restricted to FINANCE_OFFICER
    if current_user.role != "FINANCE_OFFICER":
        log_audit_event(
            db=db,
            action="RELEASE_ORDER_RECORDING_DENIED",
            entity_type="RELEASE_REQUEST",
            entity_id=req.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="DENIED",
            metadata={
                "case_number": req.case_number,
                "reason": f"Only Finance Officer is authorized to record release orders. Attempted by {current_user.role}.",
            },
        )
        raise ForbiddenException(f"Action forbidden for role '{current_user.role}'. Required: ['FINANCE_OFFICER']")

    # State validation: order can only be recorded for approved cases
    if req.workflow_status != ReleaseWorkflowStatus.APPROVED.value:
        raise AppException(
            status_code=400,
            message=f"Can only record release order after APPROVED status; currently '{req.workflow_status}'",
            code="INVALID_ORDER_RECORDING_STATE",
        )

    # Idempotency / duplicate order check
    existing_order = db.scalar(
        select(ReleaseOrderRecord).where(
            ReleaseOrderRecord.release_request_id == req.id
        )
    )
    if existing_order:
        raise AppException(
            status_code=400,
            message=f"Release order already recorded for request '{req.id}'",
            code="DUPLICATE_RELEASE_ORDER",
        )

    order = ReleaseOrderRecord(
        release_request_id=req.id,
        order_reference_number=payload.order_reference_number.strip(),
        order_date=payload.order_date,
        responsible_officer_id=current_user.id,
        supporting_document_id=payload.supporting_document_id,
        status=ReleaseOrderStatus.EXECUTED.value,
        bank_action_status=BankActionStatus.PENDING.value,
        is_synthetic_demo=payload.is_synthetic_demo,
        notes=payload.notes,
    )
    db.add(order)

    # Advance workflow status
    req.workflow_status = ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value
    req.version += 1

    db.commit()
    db.refresh(order)

    log_audit_event(
        db=db,
        action="RELEASE_ORDER_RECORDED",
        entity_type="RELEASE_ORDER",
        entity_id=order.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        outcome="SUCCESS",
        metadata={
            "case_number": req.case_number,
            "order_reference_number": order.order_reference_number,
            "order_date": order.order_date.isoformat(),
            "bank_action_status": order.bank_action_status,
        },
    )
    return order
