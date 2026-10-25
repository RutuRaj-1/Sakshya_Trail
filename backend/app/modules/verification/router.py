"""
Module 4 — Trust, Provenance & Verification Desk
API Router

Provides versioned REST endpoints for:
- Field-level provenance and history
- Evidentiary trust assessments and transitions (generic + dedicated operations)
- Aggregate trust summary
- Verification requests, dispatches, retries, cancellations
- Manual external evidence recording
- Verification response ingestion and comparison review

Security guarantees:
- No endpoint accepts a bare trust_level field as authorization to promote an instrument.
- Trust history is read-only — no mutation endpoint exists.
- All state-changing operations require authentication and CSRF protection.
- L2 is restricted to officer roles; L3 requires a qualified verification response.
"""
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.common.exceptions import AppException
from app.modules.auth.models import User
from app.modules.auth.dependencies import (
    get_current_active_user,
    verify_csrf_origin,
)
from app.modules.instruments.models import Instrument
from app.modules.verification.schemas import (
    AggregateTrustSummaryResponse,
    FieldProvenanceResponse,
    L1ReassessmentRequest,
    L2OfficerDecisionRequest,
    L3BankConfirmationRequest,
    TrustAssessmentResponse,
    TrustDowngradeRequest,
    TrustTransitionRequest,
    TrustTransitionHistoryResponse,
    VerificationRequestCreate,
    VerificationRequestResponse,
    VerificationResponseOut,
    VerificationDispatchAction,
    ManualVerificationRecordRequest,
    VerificationRetryRequest,
    VerificationCancelRequest,
)
from app.modules.verification.provenance_service import (
    get_active_field_provenances,
    get_field_provenance_history,
)
from app.modules.verification.trust_service import (
    apply_l3_bank_confirmation,
    compute_aggregate_trust_summary,
    get_active_trust_assessments,
    get_trust_transition_history,
    perform_trust_downgrade,
    record_l2_officer_decision,
    request_l1_reassessment,
    transition_trust_level,
)
from app.modules.verification.verification_service import (
    cancel_verification_request,
    create_verification_request,
    dispatch_verification_request,
    get_verification_request_by_id,
    get_verification_response_by_id,
    list_instrument_verification_requests,
    record_manual_verification_result,
    retry_verification_request,
)

router = APIRouter(prefix="/verification", tags=["Trust & Verification"])


def _assert_instrument_tenant_access(instrument: Instrument, current_user: User) -> None:
    """Enforces institution scoping so institution users cannot view another tenant's records."""
    if current_user.role == "INSTITUTION_USER":
        if instrument.institution_id != current_user.institution_id:
            raise AppException(
                message="Access denied to instrument belonging to another institution.",
                status_code=403,
                code="FORBIDDEN_CROSS_TENANT_ACCESS",
            )


def _get_instrument_or_404(db: Session, instrument_id: str) -> Instrument:
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )
    return instrument


# ---------------------------------------------------------------------------
# Provenance Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/instruments/{instrument_id}/provenance",
    response_model=List[FieldProvenanceResponse],
    summary="Get active field-level provenance for an instrument",
)
def get_instrument_provenance(
    instrument_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve all current active field-level provenance entries for the specified instrument."""
    instrument = _get_instrument_or_404(db, instrument_id)
    _assert_instrument_tenant_access(instrument, current_user)
    return get_active_field_provenances(db=db, instrument_id=instrument_id)


@router.get(
    "/instruments/{instrument_id}/provenance/{field_name}/history",
    response_model=List[FieldProvenanceResponse],
    summary="Get complete historical provenance for a specific field",
)
def get_field_provenance_chain(
    instrument_id: str,
    field_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve the chronological custody chain for a specific field on an instrument."""
    instrument = _get_instrument_or_404(db, instrument_id)
    _assert_instrument_tenant_access(instrument, current_user)
    return get_field_provenance_history(
        db=db, instrument_id=instrument_id, field_name=field_name
    )


# ---------------------------------------------------------------------------
# Trust State Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/instruments/{instrument_id}/trust",
    response_model=List[TrustAssessmentResponse],
    summary="Get active trust assessments for an instrument",
)
def get_instrument_trust_assessments(
    instrument_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve current active trust assessments (aggregate and field-level)."""
    instrument = _get_instrument_or_404(db, instrument_id)
    _assert_instrument_tenant_access(instrument, current_user)
    return get_active_trust_assessments(db=db, instrument_id=instrument_id)


@router.get(
    "/instruments/{instrument_id}/trust/summary",
    response_model=AggregateTrustSummaryResponse,
    summary="Get computed aggregate trust summary for an instrument",
)
def get_instrument_trust_summary(
    instrument_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Compute and return the aggregate trust summary.
    The aggregate is the MINIMUM trust level across all tracked fields.
    L3 for one field does NOT imply L3 for the entire instrument.
    """
    instrument = _get_instrument_or_404(db, instrument_id)
    _assert_instrument_tenant_access(instrument, current_user)
    return compute_aggregate_trust_summary(db=db, instrument_id=instrument_id)


@router.get(
    "/instruments/{instrument_id}/trust/history",
    response_model=List[TrustTransitionHistoryResponse],
    summary="Get durable audit history of trust transitions",
)
def get_instrument_trust_history(
    instrument_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve the complete, append-only historical audit log of trust state changes."""
    instrument = _get_instrument_or_404(db, instrument_id)
    _assert_instrument_tenant_access(instrument, current_user)
    return get_trust_transition_history(db=db, instrument_id=instrument_id)


@router.post(
    "/instruments/{instrument_id}/trust/transition",
    response_model=TrustAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generic trust level transition (L0-L3) — use dedicated endpoints where possible",
)
def execute_trust_transition(
    instrument_id: str,
    payload: TrustTransitionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """
    Centralized trust transition endpoint.
    Enforces role authorization, mandatory reasons, documentary evidence, and
    verification response validity. The API never accepts a bare trust_level field
    as authorization to promote an instrument.
    """
    client_ip = request.client.host if request.client else None
    return transition_trust_level(
        db=db,
        instrument_id=instrument_id,
        target_trust_level=payload.target_trust_level,
        reason=payload.reason,
        field_name=payload.field_name,
        current_user=current_user,
        supporting_document_version_id=payload.supporting_document_version_id,
        related_verification_response_id=payload.related_verification_response_id,
        evidence_references=payload.evidence_references,
        source_authorization_config=payload.source_authorization_config,
        expected_concurrency_version=payload.expected_concurrency_version,
        request_ip=client_ip,
    )


# ---------------------------------------------------------------------------
# Dedicated Trust Operation Endpoints (Prompt 3 §7)
# ---------------------------------------------------------------------------

@router.post(
    "/instruments/{instrument_id}/trust/l1-reassessment",
    response_model=TrustAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request L1 document-consistent trust reassessment",
)
def request_l1_reassessment_endpoint(
    instrument_id: str,
    payload: L1ReassessmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """
    Request an L1 (Document-Consistent) trust reassessment.
    Requires a specific, clean document version as evidence.
    Rejects unreadable, blocked, quarantined, or stale evidence.
    """
    client_ip = request.client.host if request.client else None
    return request_l1_reassessment(
        db=db,
        instrument_id=instrument_id,
        document_version_id=payload.document_version_id,
        reason=payload.reason,
        current_user=current_user,
        validation_run_id=payload.validation_run_id,
        evidence_references=payload.evidence_references,
        request_ip=client_ip,
        expected_concurrency_version=payload.expected_concurrency_version,
    )


@router.post(
    "/instruments/{instrument_id}/trust/l2-officer-decision",
    response_model=TrustAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an authorized officer L2 verification decision",
)
def record_l2_officer_decision_endpoint(
    instrument_id: str,
    payload: L2OfficerDecisionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """
    Record an authorized scrutiny officer's L2 (Officer-Verified) decision.
    Only SCRUTINY_OFFICER, BRANCH_HEAD, and SYSTEM_ADMIN roles are permitted.
    Institution users and ordinary administrators cannot grant themselves L2.
    Requires an explicit meaningful reason and at least one evidence reference.
    """
    client_ip = request.client.host if request.client else None
    return record_l2_officer_decision(
        db=db,
        instrument_id=instrument_id,
        reason=payload.reason,
        current_user=current_user,
        supporting_document_version_id=payload.supporting_document_version_id,
        evidence_references=payload.evidence_references,
        field_name=payload.field_name,
        request_ip=client_ip,
        expected_concurrency_version=payload.expected_concurrency_version,
    )


@router.post(
    "/instruments/{instrument_id}/trust/l3-bank-confirmation",
    response_model=TrustAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply an eligible bank verification response as L3 confirmation",
)
def apply_l3_bank_confirmation_endpoint(
    instrument_id: str,
    payload: L3BankConfirmationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """
    Apply L3 (Bank-Confirmed) trust status from an eligible bank verification response.

    Strict requirements:
    - source_authorization_config must be provided (policy gate).
    - Response must be non-simulated.
    - Response result must be MATCH.
    - Response source_classification must be AUTHORIZED_BANK_RESPONSE.
    - request_code must match the parent request's reference_code.
    - Field-level correspondences must pass.

    A manual officer note alone does NOT qualify as a received bank confirmation.
    A simulated response CANNOT produce production L3.
    """
    client_ip = request.client.host if request.client else None
    return apply_l3_bank_confirmation(
        db=db,
        instrument_id=instrument_id,
        verification_response_id=payload.verification_response_id,
        reason=payload.reason,
        source_authorization_config=payload.source_authorization_config,
        current_user=current_user,
        field_name=payload.field_name,
        evidence_references=payload.evidence_references,
        requested_fields=payload.requested_fields,
        request_ip=client_ip,
        expected_concurrency_version=payload.expected_concurrency_version,
    )


@router.post(
    "/instruments/{instrument_id}/trust/downgrade",
    response_model=TrustAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Perform an authorized trust downgrade or reassessment",
)
def perform_trust_downgrade_endpoint(
    instrument_id: str,
    payload: TrustDowngradeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """
    Perform an authorized trust downgrade or reassessment.

    Required when:
    - A previously relied-on document becomes invalid or is withdrawn.
    - A new conflicting response appears.
    - An earlier response is found ineligible.
    - A prior officer decision is formally reversed.

    Preserves the previous trust level and evidence.
    Never deletes historical decisions.
    Requires an explicit reason describing the triggering event.
    """
    client_ip = request.client.host if request.client else None
    return perform_trust_downgrade(
        db=db,
        instrument_id=instrument_id,
        target_trust_level=payload.target_trust_level,
        reason=payload.reason,
        current_user=current_user,
        field_name=payload.field_name,
        evidence_references=payload.evidence_references,
        triggering_event=payload.triggering_event,
        request_ip=client_ip,
        expected_concurrency_version=payload.expected_concurrency_version,
    )


# ---------------------------------------------------------------------------
# Verification Request Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/instruments/{instrument_id}/requests",
    response_model=VerificationRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a verification request for an instrument",
)
def create_request_for_instrument(
    instrument_id: str,
    payload: VerificationRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """Dispatches a bank or external verification request for an instrument."""
    client_ip = request.client.host if request.client else None
    return create_verification_request(
        db=db,
        instrument_id=instrument_id,
        channel=payload.channel,
        requested_fields=payload.requested_fields,
        correlation_id=payload.correlation_id,
        notes=payload.notes,
        current_user=current_user,
        request_ip=client_ip,
    )


@router.get(
    "/instruments/{instrument_id}/requests",
    response_model=List[VerificationRequestResponse],
    summary="List verification requests for an instrument",
)
def list_requests_for_instrument(
    instrument_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lists all verification requests associated with the given instrument."""
    return list_instrument_verification_requests(
        db=db, instrument_id=instrument_id, current_user=current_user
    )


@router.get(
    "/requests/{request_id}",
    response_model=VerificationRequestResponse,
    summary="Get verification request details and history",
)
def get_request_details(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieves a specific verification request with its history and associated responses."""
    return get_verification_request_by_id(
        db=db, request_id=request_id, current_user=current_user
    )


@router.post(
    "/requests/{request_id}/dispatch",
    response_model=VerificationResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch a verification request through configured adapter",
)
def dispatch_request(
    request_id: str,
    payload: VerificationDispatchAction,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """Executes the adapter dispatch and ingests the resulting confirmation response."""
    client_ip = request.client.host if request.client else None
    return dispatch_verification_request(
        db=db,
        request_id=request_id,
        current_user=current_user,
        scenario=payload.scenario,
        request_ip=client_ip,
    )


@router.post(
    "/requests/{request_id}/manual-record",
    response_model=VerificationResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record manual external verification evidence",
)
def record_manual_evidence(
    request_id: str,
    payload: ManualVerificationRecordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """Records an authorized officer's external manual verification letter or certificate."""
    client_ip = request.client.host if request.client else None
    return record_manual_verification_result(
        db=db,
        request_id=request_id,
        external_reference=payload.external_reference,
        communication_date=payload.communication_date,
        result=payload.result,
        reason=payload.reason,
        evidence_document_version_id=payload.evidence_document_version_id,
        bank_values=payload.bank_values,
        current_user=current_user,
        request_ip=client_ip,
    )


@router.post(
    "/requests/{request_id}/retry",
    response_model=VerificationResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Retry a timed-out or unavailable verification request",
)
def retry_request(
    request_id: str,
    payload: VerificationRetryRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """Retries a verification request within bounded attempt limits."""
    client_ip = request.client.host if request.client else None
    return retry_verification_request(
        db=db,
        request_id=request_id,
        current_user=current_user,
        scenario=payload.scenario,
        request_ip=client_ip,
    )


@router.post(
    "/requests/{request_id}/cancel",
    response_model=VerificationRequestResponse,
    summary="Cancel or close a verification request",
)
def cancel_request(
    request_id: str,
    payload: VerificationCancelRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """Cancels an active or pending verification request with mandatory officer reason."""
    client_ip = request.client.host if request.client else None
    return cancel_verification_request(
        db=db,
        request_id=request_id,
        reason=payload.reason,
        current_user=current_user,
        request_ip=client_ip,
    )


# ---------------------------------------------------------------------------
# Verification Response Details Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/responses/{response_id}",
    response_model=VerificationResponseOut,
    summary="Get verification response and field comparison details",
)
def get_response_details(
    response_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieves full details of a verification response including field-by-field comparisons."""
    return get_verification_response_by_id(
        db=db, response_id=response_id, current_user=current_user
    )
