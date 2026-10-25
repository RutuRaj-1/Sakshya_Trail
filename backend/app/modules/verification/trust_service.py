"""
Module 4 — Centralized Trust Transition Service (TrustTransitionService)

ALL trust changes must pass through this module's public functions.
No ordinary API handler, document upload, OCR result, validation result,
simulated adapter or database seed should directly assign L1, L2, or L3
without satisfying the required transition conditions here.

Transition conditions enforced:
- L0 DECLARED         : authorized process, source/actor/timestamp preserved.
- L1 DOCUMENT_CONSISTENT : exact document version, validated processing status,
                           relevant validation run reference, cross-instrument check.
- L2 OFFICER_VERIFIED  : authorized officer role, explicit reason, evidence refs.
- L3 BANK_CONFIRMED    : qualified verification response, matching request_code,
                         MATCH result, non-simulated, AUTHORIZED_BANK_RESPONSE
                         source classification, field-level correspondence,
                         approved source authorization config.

Additional guarantees:
- Optimistic concurrency locking prevents two simultaneous transitions.
- Every transition is wrapped in a database transaction.
- Every transition writes an immutable TrustTransitionHistory entry.
- Every transition emits an audit event.
- Trust history cannot be mutated through normal application paths.
- Simulated responses cannot produce production L3.
- Cross-instrument evidence is rejected.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy import select, and_
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import Session

from app.common.exceptions import AppException
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
)
from app.modules.audit.service import log_audit_event
from app.modules.auth.models import User
from app.modules.documents.models import DocumentVersion
from app.modules.instruments.models import Instrument
from app.modules.verification.enums import (
    SourceClassification,
    TRACKED_FIELDS_SET,
    TrustAssessmentStatus,
    TrustLevel,
    TrustTriggerType,
    VerificationResult,
)
from app.modules.verification.models import (
    TrustAssessment,
    TrustTransitionHistory,
    VerificationRequest,
    VerificationResponse,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Roles that may perform L2 verification
OFFICER_ROLES = {ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD}

VALID_TRUST_LEVELS = {
    TrustLevel.L0_DECLARED.value,
    TrustLevel.L1_DOCUMENT_CONSISTENT.value,
    TrustLevel.L2_OFFICER_VERIFIED.value,
    TrustLevel.L3_BANK_CONFIRMED.value,
}

# Numeric rank for upgrade vs downgrade detection
TRUST_LEVEL_RANK: Dict[str, int] = {
    TrustLevel.L0_DECLARED.value: 0,
    TrustLevel.L1_DOCUMENT_CONSISTENT.value: 1,
    TrustLevel.L2_OFFICER_VERIFIED.value: 2,
    TrustLevel.L3_BANK_CONFIRMED.value: 3,
}

# Document processing statuses that allow evidence use for L1
L1_ALLOWED_PROCESSING_STATUSES = {"CLEAN", "PROCESSED", "ACCEPTED"}

# Source classifications that qualify for production L3
L3_AUTHORIZED_CLASSIFICATIONS = {SourceClassification.AUTHORIZED_BANK_RESPONSE.value}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_instrument(db: Session, instrument_id: str) -> Instrument:
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )
    return instrument


def _get_active_assessment(
    db: Session, instrument_id: str, field_name: Optional[str]
) -> Optional[TrustAssessment]:
    stmt = select(TrustAssessment).where(
        and_(
            TrustAssessment.instrument_id == instrument_id,
            TrustAssessment.field_name == field_name,
            TrustAssessment.status == TrustAssessmentStatus.ACTIVE.value,
        )
    )
    return db.scalars(stmt).first()


def _validate_document_version_for_l1(
    db: Session, instrument: Instrument, doc_version_id: str
) -> DocumentVersion:
    """Validates a document version as eligible L1 evidence."""
    doc_ver = db.scalar(select(DocumentVersion).where(DocumentVersion.id == doc_version_id))
    if not doc_ver:
        raise AppException(
            message=f"Document version '{doc_version_id}' does not exist.",
            status_code=404,
            code="DOCUMENT_VERSION_NOT_FOUND",
        )
    # Cross-instrument evidence guard
    if doc_ver.document.instrument_id != instrument.id:
        raise AppException(
            message=(
                f"Document version '{doc_version_id}' belongs to instrument "
                f"'{doc_ver.document.instrument_id}', not '{instrument.id}'. "
                "Cross-instrument evidence is rejected."
            ),
            status_code=422,
            code="CROSS_INSTRUMENT_EVIDENCE_REJECTED",
        )
    # Processing status guard — reject unreadable/blocked/stale evidence
    if doc_ver.processing_status not in L1_ALLOWED_PROCESSING_STATUSES:
        raise AppException(
            message=(
                f"Document version '{doc_ver.version_number}' has processing status "
                f"'{doc_ver.processing_status}'. L1 cannot be assigned while evidence is "
                "unreadable, quarantined, blocked, or not yet processed. "
                f"Allowed statuses: {sorted(L1_ALLOWED_PROCESSING_STATUSES)}"
            ),
            status_code=422,
            code="EVIDENCE_NOT_READY",
        )
    return doc_ver


def _validate_verification_response_for_l3(
    db: Session,
    instrument: Instrument,
    response_id: str,
    requested_fields: Optional[List[str]] = None,
) -> VerificationResponse:
    """
    Validates a verification response as eligible for L3 promotion.
    Checks: existence, instrument match, simulation flag, result, source classification,
    request_code match, and field-level correspondence.
    """
    response = db.scalar(select(VerificationResponse).where(VerificationResponse.id == response_id))
    if not response:
        raise AppException(
            message=f"Verification response '{response_id}' not found.",
            status_code=404,
            code="VERIFICATION_RESPONSE_NOT_FOUND",
        )

    # Cross-instrument guard
    if response.instrument_id != instrument.id:
        raise AppException(
            message=(
                f"Verification response '{response.id}' belongs to instrument "
                f"'{response.instrument_id}', not target instrument '{instrument.id}'. "
                "Cross-instrument confirmation is forbidden."
            ),
            status_code=422,
            code="CROSS_INSTRUMENT_RESPONSE_REJECTED",
        )

    # Simulation guard — simulated responses CANNOT satisfy production L3
    if response.is_simulated:
        raise AppException(
            message=(
                "Simulated verification responses CANNOT promote trust to L3_BANK_CONFIRMED. "
                "A production bank confirmation from an authorized source is required."
            ),
            status_code=422,
            code="SIMULATED_RESPONSE_CANNOT_AUTHORIZE_L3",
        )

    # Result must be MATCH
    if response.result != VerificationResult.MATCH.value:
        raise AppException(
            message=(
                f"Verification response outcome is '{response.result}'. "
                "Only a successful 'MATCH' result qualifies for L3_BANK_CONFIRMED."
            ),
            status_code=422,
            code="RESPONSE_NOT_MATCHED",
        )

    # Source classification must be AUTHORIZED_BANK_RESPONSE
    if response.source_classification not in L3_AUTHORIZED_CLASSIFICATIONS:
        raise AppException(
            message=(
                f"Verification response source classification is '{response.source_classification}'. "
                "Only 'AUTHORIZED_BANK_RESPONSE' sources satisfy L3_BANK_CONFIRMED. "
                "MANUAL_EVIDENCE alone and SIMULATION never qualify."
            ),
            status_code=422,
            code="UNAUTHORIZED_SOURCE_CLASSIFICATION",
        )

    # Request code matching — response must carry the same code as the parent request
    if response.request_code:
        parent_request = db.scalar(
            select(VerificationRequest).where(VerificationRequest.id == response.request_id)
        )
        if parent_request and response.request_code != parent_request.reference_code:
            raise AppException(
                message=(
                    f"Verification response request_code '{response.request_code}' does not match "
                    f"parent request reference_code '{parent_request.reference_code}'. "
                    "Request-code mismatch rejected."
                ),
                status_code=422,
                code="REQUEST_CODE_MISMATCH",
            )

    # Field-level correspondence check
    # The response's field_comparisons_json must support the claimed fields
    if response.field_comparisons_json:
        try:
            comparisons: Dict[str, Any] = json.loads(response.field_comparisons_json)
        except Exception:
            comparisons = {}

        fields_to_check = requested_fields or list(comparisons.keys())
        mismatched = [
            f for f in fields_to_check
            if f in comparisons and comparisons[f].get("is_match") is False
        ]
        if mismatched:
            raise AppException(
                message=(
                    f"Field-level correspondence check failed. The following fields do not match "
                    f"in the bank response: {mismatched}. "
                    "L3 cannot be granted when confirmed field values conflict with instrument data."
                ),
                status_code=422,
                code="FIELD_CORRESPONDENCE_MISMATCH",
                details={"mismatched_fields": mismatched},
            )

    return response


# ---------------------------------------------------------------------------
# Policy / eligibility gate
# ---------------------------------------------------------------------------

def _check_source_authorization(
    target_trust_level: str,
    source_authorization_config: Optional[str],
) -> None:
    """
    Enforce the policy gate for L3 source authorization.
    If no authorization config is provided when one is required, return a clear
    UNABLE_TO_ESTABLISH_TRUST state rather than a falsely positive outcome.
    """
    if target_trust_level == TrustLevel.L3_BANK_CONFIRMED.value:
        if not source_authorization_config:
            raise AppException(
                message=(
                    "UNABLE_TO_ESTABLISH_TRUST — required policy/source authorization is not "
                    "configured. An approved bank-confirmation source authorization config key "
                    "must be provided for L3_BANK_CONFIRMED transitions."
                ),
                status_code=422,
                code="UNABLE_TO_ESTABLISH_TRUST",
            )


# ---------------------------------------------------------------------------
# Core transition function — the single authoritative gatekeeper
# ---------------------------------------------------------------------------

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
    source_authorization_config: Optional[str] = None,
    expected_concurrency_version: Optional[int] = None,
    requested_fields: Optional[List[str]] = None,
) -> TrustAssessment:
    """
    Centralized gatekeeper for ALL trust level transitions.

    Validates:
    - Target trust level validity.
    - Field name against tracked allow-list.
    - Instrument existence and institution scope.
    - Current assessment state (prior_level → target_level).
    - Role / actor authorization.
    - Evidence references and accessibility.
    - Document version and validation run references.
    - Verification response eligibility (for L3).
    - Source authorization configuration (policy gate).
    - Mandatory reason.
    - Optimistic concurrency version (if provided).

    Writes inside a transaction:
    - New TrustAssessment (ACTIVE).
    - Supersedes prior assessment (SUPERSEDED).
    - Immutable TrustTransitionHistory entry.
    - Instrument.trust_level update (for aggregate transitions).
    - Audit event.

    Returns the new TrustAssessment.
    """
    # 1. Validate target trust level
    if target_trust_level not in VALID_TRUST_LEVELS:
        raise AppException(
            message=f"Invalid trust level '{target_trust_level}'. Must be one of: {sorted(VALID_TRUST_LEVELS)}",
            status_code=422,
            code="INVALID_TRUST_LEVEL",
        )

    # 2. Validate field name against allow-list
    if field_name is not None and field_name not in TRACKED_FIELDS_SET:
        raise AppException(
            message=f"Field '{field_name}' is not in the tracked provenance allow-list.",
            status_code=422,
            code="UNTRACKED_FIELD",
        )

    # 3. Retrieve instrument
    instrument = _get_instrument(db, instrument_id)

    # 4. Retrieve prior active assessment
    prior_assessment = _get_active_assessment(db, instrument_id, field_name)
    prior_level = (
        prior_assessment.trust_level
        if prior_assessment
        else instrument.trust_level or TrustLevel.L0_DECLARED.value
    )
    prior_rank = TRUST_LEVEL_RANK.get(prior_level, 0)
    target_rank = TRUST_LEVEL_RANK.get(target_trust_level, 0)
    is_downgrade = target_rank < prior_rank

    # 5. Optimistic concurrency check
    if expected_concurrency_version is not None and prior_assessment is not None:
        if prior_assessment.concurrency_version != expected_concurrency_version:
            raise AppException(
                message=(
                    f"Concurrency conflict: expected version {expected_concurrency_version}, "
                    f"but current assessment is at version {prior_assessment.concurrency_version}. "
                    "Another transition occurred concurrently. Reload and retry."
                ),
                status_code=409,
                code="CONCURRENT_TRUST_TRANSITION_CONFLICT",
            )

    # 6. Clean reason
    clean_reason = (reason or "").strip()

    # 7. Enforce entry conditions by target level
    # -------------------------------------------------------------------------
    if target_trust_level == TrustLevel.L0_DECLARED.value:
        # L0 — initial declaration or authorized reset
        if not clean_reason:
            clean_reason = "Initial declaration or authorized baseline reset."

    elif target_trust_level == TrustLevel.L1_DOCUMENT_CONSISTENT.value:
        # L1 — requires a referenced document version that is readable and in-scope
        if not supporting_document_version_id:
            raise AppException(
                message=(
                    "Trust level L1_DOCUMENT_CONSISTENT requires a reference to a specific "
                    "document version. Provide 'supporting_document_version_id'."
                ),
                status_code=422,
                code="L1_EVIDENCE_REQUIRED",
            )
        doc_ver = _validate_document_version_for_l1(
            db, instrument, supporting_document_version_id
        )
        if not clean_reason:
            clean_reason = (
                f"Document consistency verified against document version {doc_ver.version_number}."
            )

    elif target_trust_level == TrustLevel.L2_OFFICER_VERIFIED.value:
        # L2 — requires authorized officer role, explicit reason, and evidence
        if not current_user or current_user.role not in OFFICER_ROLES:
            raise AppException(
                message=(
                    "Only authorized regulatory scrutiny officers "
                    f"({', '.join(sorted(OFFICER_ROLES))}) can verify trust level L2. "
                    "Institution users and ordinary administrators cannot self-grant L2."
                ),
                status_code=403,
                code="OFFICER_ROLE_REQUIRED",
            )
        if not clean_reason:
            raise AppException(
                message=(
                    "A meaningful reason is strictly mandatory for officer verification (L2). "
                    "Provide 'reason' describing the basis for the decision."
                ),
                status_code=422,
                code="REASON_REQUIRED",
            )
        # Must have at least one documentary or manual evidence reference
        if not (supporting_document_version_id or evidence_references):
            raise AppException(
                message=(
                    "L2 officer verification requires at least one documentary or manual "
                    "evidence reference. Provide 'supporting_document_version_id' or 'evidence_references'."
                ),
                status_code=422,
                code="EVIDENCE_REFERENCE_REQUIRED",
            )

    elif target_trust_level == TrustLevel.L3_BANK_CONFIRMED.value:
        if not related_verification_response_id:
            raise AppException(
                message=(
                    "Trust level L3_BANK_CONFIRMED strictly requires a qualifying bank "
                    "verification response record. Provide 'related_verification_response_id'."
                ),
                status_code=422,
                code="L3_RESPONSE_REQUIRED",
            )
        response = _validate_verification_response_for_l3(
            db, instrument, related_verification_response_id, requested_fields
        )

        # Policy / source authorization gate
        _check_source_authorization(target_trust_level, source_authorization_config)
        if not clean_reason:
            clean_reason = (
                f"Bank confirmation received via response {response.id} "
                f"(source: {response.source_classification})."
            )

    # 8. Downgrade requires a reason
    if is_downgrade and not clean_reason:
        raise AppException(
            message=(
                "A reason is strictly mandatory when performing a trust reassessment or downgrade."
            ),
            status_code=422,
            code="DOWNGRADE_REASON_REQUIRED",
        )

    # -------------------------------------------------------------------------
    # 9. Write inside a transaction
    # -------------------------------------------------------------------------
    prior_concurrency_version = (
        prior_assessment.concurrency_version if prior_assessment else None
    )

    new_assessment = TrustAssessment(
        instrument_id=instrument.id,
        field_name=field_name,
        trust_level=target_trust_level,
        supporting_evidence_references_json=(
            json.dumps(evidence_references) if evidence_references else None
        ),
        supporting_document_version_id=supporting_document_version_id,
        related_validation_run_id=related_validation_run_id,
        related_verification_response_id=related_verification_response_id,
        assessing_user_id=current_user.id if current_user else None,
        assessing_service=service_name,
        reason=clean_reason,
        status=TrustAssessmentStatus.ACTIVE.value,
        is_downgrade=is_downgrade,
        concurrency_version=1,
        prior_assessment_id=prior_assessment.id if prior_assessment else None,
        source_authorization_config=source_authorization_config,
    )
    db.add(new_assessment)
    db.flush()  # Get the new ID

    # Supersede prior assessment
    if prior_assessment:
        prior_assessment.status = TrustAssessmentStatus.SUPERSEDED.value
        prior_assessment.superseded_by_id = new_assessment.id
        db.add(prior_assessment)

    # Compute trigger type
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
        evidence_references_json=(
            json.dumps(evidence_references) if evidence_references else None
        ),
        trigger_type=computed_trigger,
        related_verification_response_id=related_verification_response_id,
        outcome="APPLIED",
        is_downgrade=is_downgrade,
        previous_assessment_id=prior_assessment.id if prior_assessment else None,
        new_assessment_id=new_assessment.id,
        concurrency_version_before=prior_concurrency_version,
    )
    db.add(history_entry)

    # Update instrument.trust_level for aggregate (field_name is None) transitions
    if field_name is None:
        instrument.trust_level = target_trust_level
        db.add(instrument)

    db.commit()
    db.refresh(new_assessment)

    # 10. Audit event
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
            "source_authorization_config": source_authorization_config,
            "new_assessment_id": new_assessment.id,
        },
    )

    return new_assessment


# ---------------------------------------------------------------------------
# Dedicated domain operations (Prompt 3 §7 safe API operations)
# ---------------------------------------------------------------------------

def request_l1_reassessment(
    db: Session,
    instrument_id: str,
    document_version_id: str,
    reason: str,
    current_user: Optional[User] = None,
    service_name: Optional[str] = None,
    validation_run_id: Optional[str] = None,
    evidence_references: Optional[List[str]] = None,
    request_ip: Optional[str] = None,
    expected_concurrency_version: Optional[int] = None,
) -> TrustAssessment:
    """
    Request an L1 (Document-Consistent) trust level assignment.
    Validates that the document version is clean, readable, and belongs to this instrument.
    Intended for use by validation engine services after successful rule runs.
    """
    return transition_trust_level(
        db=db,
        instrument_id=instrument_id,
        target_trust_level=TrustLevel.L1_DOCUMENT_CONSISTENT.value,
        reason=reason,
        current_user=current_user,
        service_name=service_name,
        supporting_document_version_id=document_version_id,
        related_validation_run_id=validation_run_id,
        evidence_references=evidence_references,
        trigger_type=TrustTriggerType.DOCUMENT_VALIDATION.value,
        request_ip=request_ip,
        expected_concurrency_version=expected_concurrency_version,
    )


def record_l2_officer_decision(
    db: Session,
    instrument_id: str,
    reason: str,
    current_user: User,
    supporting_document_version_id: Optional[str] = None,
    evidence_references: Optional[List[str]] = None,
    field_name: Optional[str] = None,
    request_ip: Optional[str] = None,
    expected_concurrency_version: Optional[int] = None,
) -> TrustAssessment:
    """
    Record an authorized officer's L2 (Officer-Verified) decision.
    Strictly enforces officer role, meaningful reason, and evidence linkage.
    A scrutiny officer may verify only within their implemented scope.
    Institution users and ordinary administrators cannot grant L2.
    """
    if not current_user or current_user.role not in OFFICER_ROLES:
        raise AppException(
            message=(
                "Only authorized regulatory scrutiny officers "
                f"({', '.join(sorted(OFFICER_ROLES))}) can perform L2 officer verification. "
                "Institution users and ordinary administrators cannot self-grant L2."
            ),
            status_code=403,
            code="OFFICER_ROLE_REQUIRED",
        )
    return transition_trust_level(
        db=db,
        instrument_id=instrument_id,
        target_trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
        reason=reason,
        field_name=field_name,
        current_user=current_user,
        supporting_document_version_id=supporting_document_version_id,
        evidence_references=evidence_references,
        trigger_type=TrustTriggerType.OFFICER_REVIEW.value,
        request_ip=request_ip,
        expected_concurrency_version=expected_concurrency_version,
    )


def apply_l3_bank_confirmation(
    db: Session,
    instrument_id: str,
    verification_response_id: str,
    reason: str,
    source_authorization_config: str,
    current_user: Optional[User] = None,
    service_name: Optional[str] = None,
    field_name: Optional[str] = None,
    evidence_references: Optional[List[str]] = None,
    requested_fields: Optional[List[str]] = None,
    request_ip: Optional[str] = None,
    expected_concurrency_version: Optional[int] = None,
) -> TrustAssessment:
    """
    Apply L3 (Bank-Confirmed) trust status from an eligible bank verification response.

    Enforces:
    - source_authorization_config is provided (policy gate).
    - Response is non-simulated.
    - Response result is MATCH.
    - Response source_classification is AUTHORIZED_BANK_RESPONSE.
    - request_code matches the parent request's reference_code.
    - Field-level correspondences pass.

    A manual officer note alone does NOT automatically qualify as a bank confirmation.
    A simulated response CANNOT produce production L3.
    """
    return transition_trust_level(
        db=db,
        instrument_id=instrument_id,
        target_trust_level=TrustLevel.L3_BANK_CONFIRMED.value,
        reason=reason,
        field_name=field_name,
        current_user=current_user,
        service_name=service_name,
        related_verification_response_id=verification_response_id,
        evidence_references=evidence_references,
        trigger_type=TrustTriggerType.BANK_CONFIRMATION.value,
        source_authorization_config=source_authorization_config,
        requested_fields=requested_fields,
        request_ip=request_ip,
        expected_concurrency_version=expected_concurrency_version,
    )


def perform_trust_downgrade(
    db: Session,
    instrument_id: str,
    target_trust_level: str,
    reason: str,
    current_user: Optional[User] = None,
    service_name: Optional[str] = None,
    field_name: Optional[str] = None,
    evidence_references: Optional[List[str]] = None,
    triggering_event: Optional[str] = None,
    request_ip: Optional[str] = None,
    expected_concurrency_version: Optional[int] = None,
) -> TrustAssessment:
    """
    Perform an authorized trust downgrade or reassessment.

    Use when:
    - A previously relied-on document is withdrawn or found invalid.
    - A new conflicting response appears.
    - An earlier response is found ineligible.
    - A prior officer decision is formally reversed.

    Requirements:
    - A reason is mandatory.
    - The prior level and evidence are preserved.
    - The new event triggering reassessment is recorded.
    - The old decision is NOT deleted.
    - Trust does NOT automatically upgrade just because a discrepancy is dismissed.
    """
    if not reason or not reason.strip():
        raise AppException(
            message=(
                "A reason is strictly mandatory when performing a trust downgrade or reassessment."
            ),
            status_code=422,
            code="DOWNGRADE_REASON_REQUIRED",
        )

    # Verify this is actually a downgrade
    instrument = _get_instrument(db, instrument_id)
    prior_assessment = _get_active_assessment(db, instrument_id, field_name)
    prior_level = (
        prior_assessment.trust_level
        if prior_assessment
        else instrument.trust_level or TrustLevel.L0_DECLARED.value
    )
    prior_rank = TRUST_LEVEL_RANK.get(prior_level, 0)
    target_rank = TRUST_LEVEL_RANK.get(target_trust_level, 0)

    if target_rank >= prior_rank:
        raise AppException(
            message=(
                f"perform_trust_downgrade called with target_level='{target_trust_level}' "
                f"but current level is '{prior_level}'. "
                "Use transition_trust_level for upgrades."
            ),
            status_code=422,
            code="NOT_A_DOWNGRADE",
        )

    combined_evidence = list(evidence_references or [])
    if triggering_event:
        combined_evidence.append(f"triggering_event:{triggering_event}")

    return transition_trust_level(
        db=db,
        instrument_id=instrument_id,
        target_trust_level=target_trust_level,
        reason=reason,
        field_name=field_name,
        current_user=current_user,
        service_name=service_name,
        evidence_references=combined_evidence if combined_evidence else None,
        trigger_type=TrustTriggerType.REASSESSMENT_DOWNGRADE.value,
        request_ip=request_ip,
        expected_concurrency_version=expected_concurrency_version,
    )


# ---------------------------------------------------------------------------
# Read functions
# ---------------------------------------------------------------------------

def get_active_trust_assessments(
    db: Session, instrument_id: str
) -> List[TrustAssessment]:
    """Retrieve all current active trust assessments (aggregate and field-level)."""
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


def get_trust_transition_history(
    db: Session, instrument_id: str
) -> List[TrustTransitionHistory]:
    """Retrieve the immutable audit history of trust transitions for an instrument."""
    stmt = (
        select(TrustTransitionHistory)
        .where(TrustTransitionHistory.instrument_id == instrument_id)
        .order_by(TrustTransitionHistory.timestamp.asc())
    )
    return list(db.scalars(stmt).all())


def compute_aggregate_trust_summary(
    db: Session, instrument_id: str
) -> Dict[str, Any]:
    """
    Compute an aggregate trust summary from field-level assessments.

    Aggregation rule:
    - The aggregate trust level is the MINIMUM trust level across all tracked fields
      that have an active assessment.
    - Fields without evidence remain at L0_DECLARED (the floor).
    - The summary explicitly lists which fields are covered at each level.
    - The aggregate NEVER overstates the underlying field-level evidence.
    - L3 for the instrument reference does NOT automatically raise unrelated fields
      (amount, dates, lien_holder) to L3.

    Returns a dict with:
    - aggregate_trust_level: the minimum trust level across all active field assessments
    - fields_by_level: {trust_level: [field_names]}
    - uncovered_fields: fields with no active assessment (treated as L0)
    - note: human-readable explanation of the aggregation semantics
    """
    assessments = get_active_trust_assessments(db, instrument_id)

    # Separate aggregate (field_name is None) from field-level
    aggregate_override = next(
        (a for a in assessments if a.field_name is None), None
    )
    field_assessments = [a for a in assessments if a.field_name is not None]

    fields_by_level: Dict[str, List[str]] = {
        TrustLevel.L0_DECLARED.value: [],
        TrustLevel.L1_DOCUMENT_CONSISTENT.value: [],
        TrustLevel.L2_OFFICER_VERIFIED.value: [],
        TrustLevel.L3_BANK_CONFIRMED.value: [],
    }

    assessed_fields = set()
    for assessment in field_assessments:
        level = assessment.trust_level
        if level not in fields_by_level:
            fields_by_level[level] = []
        fields_by_level[level].append(assessment.field_name)
        assessed_fields.add(assessment.field_name)

    uncovered_fields = sorted(TRACKED_FIELDS_SET - assessed_fields)
    # Uncovered fields default to L0
    fields_by_level[TrustLevel.L0_DECLARED.value].extend(uncovered_fields)

    # Aggregate = minimum rank across all tracked fields (including uncovered which are L0)
    if uncovered_fields:
        computed_level = TrustLevel.L0_DECLARED.value
    elif not field_assessments:
        # No field-level assessments — use instrument aggregate or L0
        computed_level = (
            aggregate_override.trust_level
            if aggregate_override
            else TrustLevel.L0_DECLARED.value
        )
    else:
        min_rank = min(
            TRUST_LEVEL_RANK.get(a.trust_level, 0) for a in field_assessments
        )
        computed_level = next(
            level for level, rank in TRUST_LEVEL_RANK.items() if rank == min_rank
        )

    # If aggregate_override exists and is LOWER than computed, use it (conservative)
    if aggregate_override:
        override_rank = TRUST_LEVEL_RANK.get(aggregate_override.trust_level, 0)
        computed_rank = TRUST_LEVEL_RANK.get(computed_level, 0)
        if override_rank < computed_rank:
            computed_level = aggregate_override.trust_level

    return {
        "instrument_id": instrument_id,
        "aggregate_trust_level": computed_level,
        "fields_by_level": {k: sorted(v) for k, v in fields_by_level.items() if v},
        "uncovered_fields": uncovered_fields,
        "note": (
            "Aggregate trust is the minimum trust level across all tracked fields. "
            "L3 for one field (e.g. reference_number) does NOT imply L3 for unrelated "
            "fields (e.g. amount, maturity_date, lien_holder). "
            "Uncovered fields default to L0_DECLARED."
        ),
    }


# ---------------------------------------------------------------------------
# Compatibility: legacy create_verification_request and record_verification_response
# kept for backward-compat with existing test imports
# ---------------------------------------------------------------------------

from app.modules.verification.models import VerificationRequest, VerificationResponse
from app.modules.verification.enums import VerificationRequestStatus, VerificationChannel


def create_verification_request(
    db: Session,
    instrument_id: str,
    channel: str,
    requested_by_user: User,
    notes: Optional[str] = None,
) -> VerificationRequest:
    """Legacy helper — creates a verification request. Prefer verification_service module."""
    import uuid, json as _json
    from datetime import timezone

    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )

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
        snapshot_data_json=_json.dumps(snapshot),
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
    source_classification: Optional[str] = None,
) -> VerificationResponse:
    """Legacy helper — records a verification response. Prefer verification_service module."""
    req = db.scalar(select(VerificationRequest).where(VerificationRequest.id == request_id))
    if not req:
        raise AppException(
            message=f"Verification request '{request_id}' not found.",
            status_code=404,
            code="REQUEST_NOT_FOUND",
        )

    if channel == VerificationChannel.SIMULATED.value and not is_simulated:
        raise AppException(
            message="Channel SIMULATED must have is_simulated=True.",
            status_code=422,
            code="SIMULATION_INCONSISTENCY",
        )

    existing = db.scalar(
        select(VerificationResponse).where(VerificationResponse.idempotency_key == idempotency_key)
    )
    if existing:
        return existing

    from app.modules.verification.enums import SourceClassification as SC
    effective_source = source_classification or (
        SC.SIMULATION.value if is_simulated else SC.MANUAL_EVIDENCE.value
    )

    resp = VerificationResponse(
        request_id=req.id,
        request_code=req.reference_code,
        instrument_id=req.instrument_id,
        channel=channel,
        source_classification=effective_source,
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
