"""
Module 4 — Centralized Trust Transition Service
Enforces strict entry conditions, evidentiary requirements, and durable audit history
for the four-tier trust hierarchy (L0_DECLARED, L1_DOCUMENT_CONSISTENT, L2_OFFICER_VERIFIED, L3_BANK_CONFIRMED).
"""
import json
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.common.exceptions import AppException
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
)
from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.documents.models import DocumentVersion
from app.modules.audit.service import log_audit_event
from app.modules.verification.models import (
    TrustAssessment,
    TrustTransitionHistory,
    VerificationRequest,
    VerificationResponse,
)
from app.modules.verification.enums import (
    TrustLevel,
    TrustAssessmentStatus,
    TrustTriggerType,
    VerificationChannel,
    VerificationResult,
    VerificationRequestStatus,
    TRACKED_FIELDS_SET,
)

# Allowed officer roles for L2 promotions
OFFICER_ROLES = {ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD}

# Valid trust levels
VALID_TRUST_LEVELS = {
    TrustLevel.L0_DECLARED.value,
    TrustLevel.L1_DOCUMENT_CONSISTENT.value,
    TrustLevel.L2_OFFICER_VERIFIED.value,
    TrustLevel.L3_BANK_CONFIRMED.value,
}

# Trust level numeric rank for evaluating upgrades vs downgrades
TRUST_LEVEL_RANK = {
    TrustLevel.L0_DECLARED.value: 0,
    TrustLevel.L1_DOCUMENT_CONSISTENT.value: 1,
    TrustLevel.L2_OFFICER_VERIFIED.value: 2,
    TrustLevel.L3_BANK_CONFIRMED.value: 3,
}


def transition_trust_level(
    db: Session,
    instrument_id: str,
    target_trust_level: str,
    reason: str,
    field_name: Optional[str] = None,
    current_user: Optional[User] = None,
    service_name: Optional[str] = None,
    supporting_document_version_id: Optional[str] = None,
    related_verification_response_id: Optional[str] = None,
    related_validation_run_id: Optional[str] = None,
    evidence_references: Optional[List[str]] = None,
    trigger_type: Optional[str] = None,
    request_ip: Optional[str] = None,
) -> TrustAssessment:
    """
    Centralized gatekeeper for all trust transitions.
    Validates entry preconditions, role permissions, evidence linkage, and records immutable history.
    """
    # 1. Validate target trust level
    if target_trust_level not in VALID_TRUST_LEVELS:
        raise AppException(
            message=f"Invalid trust level '{target_trust_level}'. Must be one of: {sorted(list(VALID_TRUST_LEVELS))}",
            status_code=422,
            code="INVALID_TRUST_LEVEL",
        )

    # 2. Validate field name if field-level
    if field_name is not None and field_name not in TRACKED_FIELDS_SET:
        raise AppException(
            message=f"Field '{field_name}' is not in the tracked provenance allow-list.",
            status_code=422,
            code="UNTRACKED_FIELD",
        )

    # 3. Retrieve target instrument
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )

    # 4. Find prior active assessment for this scope (aggregate or field)
    stmt = (
        select(TrustAssessment)
        .where(
            and_(
                TrustAssessment.instrument_id == instrument_id,
                TrustAssessment.field_name == field_name,
                TrustAssessment.status == TrustAssessmentStatus.ACTIVE.value,
            )
        )
    )
    prior_assessment = db.scalars(stmt).first()
    prior_level = (
        prior_assessment.trust_level
        if prior_assessment
        else instrument.trust_level or TrustLevel.L0_DECLARED.value
    )

    prior_rank = TRUST_LEVEL_RANK.get(prior_level, 0)
    target_rank = TRUST_LEVEL_RANK.get(target_trust_level, 0)
    is_downgrade = target_rank < prior_rank

    # Clean reason
    clean_reason = reason.strip() if reason else ""

    # 5. Enforce Trust Entry Conditions
    # -------------------------------------------------------------
    # L0 — Declared
    # -------------------------------------------------------------
    if target_trust_level == TrustLevel.L0_DECLARED.value:
        if not clean_reason:
            clean_reason = "Initial declaration or baseline reset"

    # -------------------------------------------------------------
    # L1 — Document-consistent
    # -------------------------------------------------------------
    elif target_trust_level == TrustLevel.L1_DOCUMENT_CONSISTENT.value:
        if not supporting_document_version_id:
            raise AppException(
                message="Trust level L1_DOCUMENT_CONSISTENT requires reference to a specific document version.",
                status_code=422,
                code="L1_EVIDENCE_REQUIRED",
            )
        doc_ver = db.scalar(
            select(DocumentVersion).where(DocumentVersion.id == supporting_document_version_id)
        )
        if not doc_ver:
            raise AppException(
                message=f"Document version '{supporting_document_version_id}' does not exist.",
                status_code=404,
                code="DOCUMENT_VERSION_NOT_FOUND",
            )
        # Verify document version belongs to this instrument
        if doc_ver.document.instrument_id != instrument.id:
            raise AppException(
                message="Supporting document version belongs to a different instrument.",
                status_code=422,
                code="CROSS_INSTRUMENT_EVIDENCE_REJECTED",
            )
        # Check scan / processing status
        allowed_statuses = {"CLEAN", "PROCESSED", "ACCEPTED"}
        if doc_ver.processing_status not in allowed_statuses:
            raise AppException(
                message=(
                    f"Document version '{doc_ver.version_number}' has processing status "
                    f"'{doc_ver.processing_status}'. L1 cannot be assigned while evidence is unreadable, "
                    "quarantined, or unverified."
                ),
                status_code=422,
                code="EVIDENCE_NOT_READY",
            )
        if not clean_reason:
            clean_reason = f"Document consistency verified against document version {doc_ver.version_number}"

    # -------------------------------------------------------------
    # L2 — Officer-verified
    # -------------------------------------------------------------
    elif target_trust_level == TrustLevel.L2_OFFICER_VERIFIED.value:
        if not current_user or current_user.role not in OFFICER_ROLES:
            raise AppException(
                message="Only authorized regulatory scrutiny officers (SCRUTINY_OFFICER, BRANCH_HEAD, SYSTEM_ADMIN) can verify trust level L2.",
                status_code=403,
                code="OFFICER_ROLE_REQUIRED",
            )
        if not clean_reason:
            raise AppException(
                message="A meaningful reason is strictly mandatory for officer verification (L2).",
                status_code=422,
                code="REASON_REQUIRED",
            )
        # Must have at least one documentary or manual evidence reference
        has_evidence = bool(supporting_document_version_id or evidence_references)
        if not has_evidence:
            raise AppException(
                message="L2 officer verification requires at least one documentary or manual evidence reference.",
                status_code=422,
                code="EVIDENCE_REFERENCE_REQUIRED",
            )

    # -------------------------------------------------------------
    # L3 — Bank-confirmed
    # -------------------------------------------------------------
    elif target_trust_level == TrustLevel.L3_BANK_CONFIRMED.value:
        if not related_verification_response_id:
            raise AppException(
                message="Trust level L3_BANK_CONFIRMED strictly requires a qualifying bank verification response record.",
                status_code=422,
                code="L3_RESPONSE_REQUIRED",
            )
        response = db.scalar(
            select(VerificationResponse).where(VerificationResponse.id == related_verification_response_id)
        )
        if not response:
            raise AppException(
                message=f"Verification response '{related_verification_response_id}' not found.",
                status_code=404,
                code="VERIFICATION_RESPONSE_NOT_FOUND",
            )
        # Instrument matching constraint
        if response.instrument_id != instrument.id:
            raise AppException(
                message=(
                    f"Verification response '{response.id}' belongs to instrument '{response.instrument_id}', "
                    f"not target instrument '{instrument.id}'. Cross-instrument confirmation is forbidden."
                ),
                status_code=422,
                code="CROSS_INSTRUMENT_RESPONSE_REJECTED",
            )
        # Simulated responses CANNOT satisfy L3
        if response.is_simulated:
            raise AppException(
                message="Simulated verification responses CANNOT promote trust to L3_BANK_CONFIRMED.",
                status_code=422,
                code="SIMULATED_RESPONSE_CANNOT_AUTHORIZE_L3",
            )
        # Matching outcome required
        if response.result != VerificationResult.MATCH.value:
            raise AppException(
                message=(
                    f"Verification response outcome is '{response.result}'. "
                    "Only a successful 'MATCH' result satisfies L3_BANK_CONFIRMED."
                ),
                status_code=422,
                code="RESPONSE_NOT_MATCHED",
            )
        if not clean_reason:
            clean_reason = f"Bank confirmation received via response {response.id}"

    # Downgrade check
    if is_downgrade and not clean_reason:
        raise AppException(
            message="Reason is strictly mandatory when performing a trust reassessment or downgrade.",
            status_code=422,
            code="DOWNGRADE_REASON_REQUIRED",
        )

    # 6. Instantiate new TrustAssessment
    new_assessment = TrustAssessment(
        instrument_id=instrument.id,
        field_name=field_name,
        trust_level=target_trust_level,
        supporting_evidence_references_json=json.dumps(evidence_references) if evidence_references else None,
        supporting_document_version_id=supporting_document_version_id,
        related_validation_run_id=related_validation_run_id,
        related_verification_response_id=related_verification_response_id,
        assessing_user_id=current_user.id if current_user else None,
        assessing_service=service_name,
        reason=clean_reason,
        status=TrustAssessmentStatus.ACTIVE.value,
        is_downgrade=is_downgrade,
    )
    db.add(new_assessment)
    db.flush()

    # 7. Supersede prior assessment if active
    if prior_assessment:
        prior_assessment.status = TrustAssessmentStatus.SUPERSEDED.value
        prior_assessment.superseded_by_id = new_assessment.id
        db.add(prior_assessment)

    # 8. Record in durable TrustTransitionHistory
    computed_trigger = trigger_type or (
        TrustTriggerType.REASSESSMENT_DOWNGRADE.value
        if is_downgrade
        else TrustTriggerType.INITIAL_REGISTRATION.value
        if target_trust_level == TrustLevel.L0_DECLARED.value
        else TrustTriggerType.DOCUMENT_VALIDATION.value
        if target_trust_level == TrustLevel.L1_DOCUMENT_CONSISTENT.value
        else TrustTriggerType.OFFICER_REVIEW.value
        if target_trust_level == TrustLevel.L2_OFFICER_VERIFIED.value
        else TrustTriggerType.BANK_CONFIRMATION.value
    )

    history_entry = TrustTransitionHistory(
        instrument_id=instrument.id,
        field_name=field_name,
        prior_trust_level=prior_level,
        new_trust_level=target_trust_level,
        actor_user_id=current_user.id if current_user else None,
        actor_service=service_name,
        reason=clean_reason,
        evidence_references_json=json.dumps(evidence_references) if evidence_references else None,
        trigger_type=computed_trigger,
        related_verification_response_id=related_verification_response_id,
        outcome="APPLIED",
        is_downgrade=is_downgrade,
    )
    db.add(history_entry)

    # 9. If aggregate assessment (field_name is None), update instrument.trust_level
    if field_name is None:
        instrument.trust_level = target_trust_level
        db.add(instrument)

    db.commit()
    db.refresh(new_assessment)

    # 10. Audit Event
    log_audit_event(
        db=db,
        action="TRUST_LEVEL_TRANSITION",
        entity_type="instrument",
        entity_id=instrument.id,
        actor_user_id=current_user.id if current_user else None,
        actor_email=current_user.email if current_user else None,
        actor_role=current_user.role if current_user else (service_name or "SYSTEM"),
        outcome="SUCCESS",
        ip_address=request_ip,
        metadata={
            "prior_trust_level": prior_level,
            "new_trust_level": target_trust_level,
            "field_name": field_name,
            "is_downgrade": is_downgrade,
            "trigger_type": computed_trigger,
            "reason": clean_reason,
            "supporting_document_version_id": supporting_document_version_id,
            "related_verification_response_id": related_verification_response_id,
        },
    )

    return new_assessment


def get_active_trust_assessments(db: Session, instrument_id: str) -> List[TrustAssessment]:
    """Retrieve all current active trust assessments for an instrument (aggregate and field-level)."""
    stmt = (
        select(TrustAssessment)
        .where(
            and_(
                TrustAssessment.instrument_id == instrument_id,
                TrustAssessment.status == TrustAssessmentStatus.ACTIVE.value,
            )
        )
        .order_by(TrustAssessment.field_name.nullsfirst())
    )
    return list(db.scalars(stmt).all())


def get_trust_transition_history(db: Session, instrument_id: str) -> List[TrustTransitionHistory]:
    """Retrieve the durable audit history of trust transitions for an instrument."""
    stmt = (
        select(TrustTransitionHistory)
        .where(TrustTransitionHistory.instrument_id == instrument_id)
        .order_by(TrustTransitionHistory.timestamp.asc())
    )
    return list(db.scalars(stmt).all())


def create_verification_request(
    db: Session,
    instrument_id: str,
    channel: str,
    requested_by_user: User,
    notes: Optional[str] = None,
) -> VerificationRequest:
    """Creates a new traceable verification request for an instrument."""
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )

    # Freeze snapshot
    snapshot = {
        "reference_number": instrument.reference_number,
        "bank_name": instrument.bank_name,
        "branch": instrument.branch,
        "amount": str(instrument.amount),
        "currency": instrument.currency,
        "issue_date": str(instrument.issue_date),
        "maturity_date": str(instrument.maturity_date),
        "lien_holder": instrument.lien_holder,
    }

    ref_code = f"VR-{uuid.uuid4().hex[:12].upper()}"

    req = VerificationRequest(
        instrument_id=instrument.id,
        reference_code=ref_code,
        channel=channel,
        status=VerificationRequestStatus.REQUESTED.value,
        snapshot_data_json=json.dumps(snapshot),
        requested_by_user_id=requested_by_user.id,
        notes=notes,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def record_verification_response(
    db: Session,
    request_id: str,
    channel: str,
    result: str,
    is_simulated: bool,
    idempotency_key: str,
    recorded_by_user: Optional[User] = None,
    bank_reference_number: Optional[str] = None,
    bank_values: Optional[Dict[str, Any]] = None,
    evidence_document_id: Optional[str] = None,
    evidence_document_version_id: Optional[str] = None,
    notes: Optional[str] = None,
) -> VerificationResponse:
    """Records a bank verification response with simulation flag integrity."""
    req = db.scalar(select(VerificationRequest).where(VerificationRequest.id == request_id))
    if not req:
        raise AppException(
            message=f"Verification request '{request_id}' not found.",
            status_code=404,
            code="REQUEST_NOT_FOUND",
        )

    # Enforce channel simulation consistency
    if channel == VerificationChannel.SIMULATED.value and not is_simulated:
        raise AppException(
            message="Channel SIMULATED must have is_simulated=True.",
            status_code=422,
            code="SIMULATION_INCONSISTENCY",
        )

    # Check for existing idempotency key
    existing = db.scalar(
        select(VerificationResponse).where(VerificationResponse.idempotency_key == idempotency_key)
    )
    if existing:
        return existing

    resp = VerificationResponse(
        request_id=req.id,
        instrument_id=req.instrument_id,
        channel=channel,
        result=result,
        bank_reference_number=bank_reference_number,
        bank_values_json=json.dumps(bank_values) if bank_values else None,
        evidence_document_id=evidence_document_id,
        evidence_document_version_id=evidence_document_version_id,
        is_simulated=is_simulated,
        idempotency_key=idempotency_key,
        recorded_by_user_id=recorded_by_user.id if recorded_by_user else None,
        notes=notes,
    )
    db.add(resp)
    req.status = VerificationRequestStatus.COMPLETED.value
    db.add(req)
    db.commit()
    db.refresh(resp)
    return resp
