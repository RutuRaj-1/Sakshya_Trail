"""
Module 4 — Verification Request and Response Workflow Service
Orchestrates outbound verification requests, adapter dispatching, response ingestion,
bounded retries, manual evidence recording, and field-by-field reconciliation.
"""
import json
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.modules.validation.normalization import (
    normalize_reference_number,
    normalize_bank_name,
)
from app.modules.verification.models import (
    VerificationRequest,
    VerificationResponse,
)
from app.modules.verification.enums import (
    VerificationChannel,
    VerificationResult,
    VerificationRequestStatus,
    SourceClassification,
    TRACKED_INSTRUMENT_FIELDS,
)
from app.modules.verification.adapters import (
    get_adapter_for_channel,
    AdapterResponseResult,
)

OFFICER_ROLES = {ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD}


def _assert_officer_access(current_user: User) -> None:
    """Enforce regulatory officer permission."""
    if not current_user or current_user.role not in OFFICER_ROLES:
        raise AppException(
            message="Only authorized regulatory scrutiny officers can initiate or record verification actions.",
            status_code=403,
            code="OFFICER_ROLE_REQUIRED",
        )


def _assert_instrument_scope(instrument: Instrument, current_user: User) -> None:
    """Enforce tenant scoping for institution users."""
    if current_user.role == "INSTITUTION_USER":
        if instrument.institution_id != current_user.institution_id:
            raise AppException(
                message="Access denied to instrument belonging to another institution.",
                status_code=403,
                code="FORBIDDEN_CROSS_TENANT_ACCESS",
            )


def compare_instrument_vs_bank_values(
    instrument: Instrument, bank_values: Dict[str, Any], requested_fields: List[str]
) -> Tuple[str, Dict[str, Any]]:
    """
    Performs deterministic field-by-field reconciliation between instrument facts and bank values.
    Returns (overall_result, itemized_comparisons_dict).
    Does NOT overwrite instrument authoritative fields.
    """
    comparisons = {}
    has_mismatch = False
    compared_count = 0

    for field_name in requested_fields:
        if not hasattr(instrument, field_name):
            continue
        if field_name not in bank_values or bank_values[field_name] is None:
            continue

        compared_count += 1
        raw_inst_val = getattr(instrument, field_name)
        inst_str = str(raw_inst_val) if raw_inst_val is not None else ""
        bank_str = str(bank_values[field_name]).strip()

        # Specific normalization rules for comparisons
        is_match = False
        if field_name == "amount":
            try:
                inst_dec = Decimal(inst_str) if inst_str else Decimal("0")
                bank_dec = Decimal(bank_str) if bank_str else Decimal("0")
                is_match = inst_dec == bank_dec
            except Exception:
                is_match = inst_str == bank_str
        elif field_name == "reference_number":
            is_match = normalize_reference_number(inst_str) == normalize_reference_number(bank_str)
        elif field_name == "bank_name":
            is_match = normalize_bank_name(inst_str) == normalize_bank_name(bank_str)
        elif isinstance(raw_inst_val, bool):
            is_match = inst_str.lower() == bank_str.lower()
        else:
            is_match = inst_str.strip().lower() == bank_str.strip().lower()

        if not is_match:
            has_mismatch = True

        comparisons[field_name] = {
            "instrument_value": inst_str,
            "bank_value": bank_str,
            "is_match": is_match,
        }

    if compared_count == 0:
        overall_result = VerificationResult.INCONCLUSIVE.value
    else:
        overall_result = VerificationResult.MISMATCH.value if has_mismatch else VerificationResult.MATCH.value

    return overall_result, comparisons


def create_verification_request(
    db: Session,
    instrument_id: str,
    channel: str,
    current_user: User,
    requested_fields: Optional[List[str]] = None,
    correlation_id: Optional[str] = None,
    notes: Optional[str] = None,
    request_ip: Optional[str] = None,
) -> VerificationRequest:
    """
    Initiates a new verification request for an instrument.
    Generates a secure, non-guessable request reference code and freezes snapshot data.
    """
    _assert_officer_access(current_user)

    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )

    # Clean requested fields subset
    fields_to_track = requested_fields or TRACKED_INSTRUMENT_FIELDS

    # Generate non-guessable traceable reference code
    ref_code = f"VR-SEC-{uuid.uuid4().hex[:12].upper()}"

    # Frozen snapshot of current instrument facts
    snapshot = {
        "reference_number": instrument.reference_number,
        "bank_name": instrument.bank_name,
        "branch": instrument.branch,
        "amount": str(instrument.amount),
        "currency": instrument.currency,
        "issue_date": instrument.issue_date.isoformat(),
        "maturity_date": instrument.maturity_date.isoformat(),
        "lien_holder": instrument.lien_holder,
        "lien_marked": instrument.lien_marked,
        "joint_with_aicte": instrument.joint_with_aicte,
    }

    req = VerificationRequest(
        instrument_id=instrument.id,
        reference_code=ref_code,
        channel=channel,
        status=VerificationRequestStatus.PENDING.value,
        snapshot_data_json=json.dumps(snapshot),
        requested_fields_json=json.dumps(fields_to_track),
        correlation_id=correlation_id,
        attempt_count=1,
        last_attempt_at=datetime.now(timezone.utc),
        requested_by_user_id=current_user.id,
        notes=notes,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    log_audit_event(
        db=db,
        action="VERIFICATION_REQUEST_CREATED",
        entity_type="verification_request",
        entity_id=req.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS",
        ip_address=request_ip,
        metadata={
            "reference_code": req.reference_code,
            "instrument_id": instrument.id,
            "channel": channel,
            "requested_fields": fields_to_track,
        },
    )

    return req


def list_instrument_verification_requests(
    db: Session, instrument_id: str, current_user: User
) -> List[VerificationRequest]:
    """Retrieve all verification requests for an instrument, enforcing institution tenant scoping."""
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )
    _assert_instrument_scope(instrument, current_user)

    stmt = (
        select(VerificationRequest)
        .where(VerificationRequest.instrument_id == instrument_id)
        .order_by(desc(VerificationRequest.created_at))
    )
    return list(db.scalars(stmt).all())


def get_verification_request_by_id(
    db: Session, request_id: str, current_user: User
) -> VerificationRequest:
    """Retrieve a specific verification request with its associated responses and history."""
    req = db.scalar(select(VerificationRequest).where(VerificationRequest.id == request_id))
    if not req:
        raise AppException(
            message=f"Verification request '{request_id}' not found.",
            status_code=404,
            code="REQUEST_NOT_FOUND",
        )
    _assert_instrument_scope(req.instrument, current_user)
    return req


def dispatch_verification_request(
    db: Session,
    request_id: str,
    current_user: User,
    scenario: Optional[str] = None,
    request_ip: Optional[str] = None,
) -> VerificationResponse:
    """
    Dispatches a verification request through its configured adapter.
    Ingests response, executes field-by-field comparison, and updates request lifecycle state.
    """
    _assert_officer_access(current_user)

    req = db.scalar(select(VerificationRequest).where(VerificationRequest.id == request_id))
    if not req:
        raise AppException(
            message=f"Verification request '{request_id}' not found.",
            status_code=404,
            code="REQUEST_NOT_FOUND",
        )

    if req.status in {VerificationRequestStatus.CANCELLED.value, VerificationRequestStatus.CLOSED.value}:
        raise AppException(
            message=f"Cannot dispatch request '{req.reference_code}' because it is {req.status}.",
            status_code=422,
            code="REQUEST_ALREADY_CLOSED",
        )

    instrument = req.instrument
    req.last_attempt_at = datetime.now(timezone.utc)

    # 1. Select adapter
    adapter = get_adapter_for_channel(req.channel)

    # 2. Execute adapter check/receive
    adapter_res: AdapterResponseResult = adapter.check_or_receive_response(
        request=req, instrument=instrument, scenario=scenario
    )

    # 3. Determine requested fields
    requested_fields = (
        json.loads(req.requested_fields_json)
        if req.requested_fields_json
        else TRACKED_INSTRUMENT_FIELDS
    )

    # 4. Field comparison if bank values are available
    field_comparisons = {}
    final_result = adapter_res.result

    if adapter_res.result in {VerificationResult.MATCH.value, VerificationResult.MISMATCH.value}:
        computed_result, field_comparisons = compare_instrument_vs_bank_values(
            instrument=instrument,
            bank_values=adapter_res.bank_values,
            requested_fields=requested_fields,
        )
        # Reconciled result
        final_result = computed_result

    # 5. Record VerificationResponse
    idempotency_token = f"IDEMP-{req.reference_code}-{req.attempt_count}"

    # Check for existing response with same idempotency token
    existing_resp = db.scalar(
        select(VerificationResponse).where(VerificationResponse.idempotency_key == idempotency_token)
    )
    if existing_resp:
        return existing_resp

    resp = VerificationResponse(
        request_id=req.id,
        request_code=req.reference_code,
        instrument_id=instrument.id,
        channel=req.channel,
        source_classification=adapter_res.source_classification,
        source_identifier=adapter_res.source_identifier,
        result=final_result,
        bank_reference_number=adapter_res.bank_reference_number,
        bank_values_json=json.dumps(adapter_res.bank_values) if adapter_res.bank_values else None,
        field_comparisons_json=json.dumps(field_comparisons) if field_comparisons else None,
        is_simulated=adapter_res.is_simulated,
        idempotency_key=idempotency_token,
        recorded_by_user_id=current_user.id,
        recorded_by_service=adapter_res.source_identifier,
        raw_metadata_json=json.dumps(adapter_res.raw_metadata) if adapter_res.raw_metadata else None,
        notes=adapter_res.disclaimer,
    )
    db.add(resp)

    # 6. Update Request lifecycle state
    if final_result == VerificationResult.MATCH.value:
        req.status = VerificationRequestStatus.MATCH.value
    elif final_result == VerificationResult.MISMATCH.value:
        req.status = VerificationRequestStatus.MISMATCH.value
    elif final_result == VerificationResult.TIMEOUT.value:
        req.status = VerificationRequestStatus.TIMEOUT.value
        req.error_details = adapter_res.error_details
    elif final_result == VerificationResult.SOURCE_UNAVAILABLE.value:
        req.status = VerificationRequestStatus.SOURCE_UNAVAILABLE.value
        req.error_details = adapter_res.error_details
    else:
        req.status = VerificationRequestStatus.RESPONSE_RECEIVED.value

    db.add(req)
    db.commit()
    db.refresh(resp)

    # 7. Audit log
    log_audit_event(
        db=db,
        action="VERIFICATION_RESPONSE_RECEIVED",
        entity_type="verification_response",
        entity_id=resp.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS",
        ip_address=request_ip,
        metadata={
            "request_code": req.reference_code,
            "channel": req.channel,
            "result": final_result,
            "is_simulated": adapter_res.is_simulated,
            "attempt_count": req.attempt_count,
        },
    )

    return resp


def record_manual_verification_result(
    db: Session,
    request_id: str,
    external_reference: str,
    communication_date: datetime,
    result: str,
    reason: str,
    current_user: User,
    evidence_document_version_id: Optional[str] = None,
    bank_values: Optional[Dict[str, Any]] = None,
    request_ip: Optional[str] = None,
) -> VerificationResponse:
    """
    Records an authorized officer's manual verification performed outside the automated platform.
    Requires an explicit non-empty reason and links to Module 2 documentary evidence.
    """
    _assert_officer_access(current_user)

    if not reason or not reason.strip():
        raise AppException(
            message="Reason and review justification are strictly mandatory when recording manual verification.",
            status_code=422,
            code="REASON_REQUIRED",
        )

    if not external_reference or not external_reference.strip():
        raise AppException(
            message="External bank communication reference is strictly mandatory.",
            status_code=422,
            code="EXTERNAL_REFERENCE_REQUIRED",
        )

    req = db.scalar(select(VerificationRequest).where(VerificationRequest.id == request_id))
    if not req:
        raise AppException(
            message=f"Verification request '{request_id}' not found.",
            status_code=404,
            code="REQUEST_NOT_FOUND",
        )

    instrument = req.instrument

    # Validate supporting document version from Module 2 if provided
    doc_ver = None
    if evidence_document_version_id:
        doc_ver = db.scalar(
            select(DocumentVersion).where(DocumentVersion.id == evidence_document_version_id)
        )
        if not doc_ver:
            raise AppException(
                message=f"Evidence document version '{evidence_document_version_id}' not found.",
                status_code=404,
                code="DOCUMENT_VERSION_NOT_FOUND",
            )
        if doc_ver.document.instrument_id != instrument.id:
            raise AppException(
                message="Evidence document version belongs to a different instrument.",
                status_code=422,
                code="CROSS_INSTRUMENT_EVIDENCE_REJECTED",
            )

    # Field-by-field comparison
    requested_fields = (
        json.loads(req.requested_fields_json)
        if req.requested_fields_json
        else TRACKED_INSTRUMENT_FIELDS
    )
    final_result = result.upper()
    field_comparisons = {}

    if bank_values:
        computed_result, field_comparisons = compare_instrument_vs_bank_values(
            instrument=instrument,
            bank_values=bank_values,
            requested_fields=requested_fields,
        )
        final_result = computed_result

    idempotency_token = f"IDEMP-MANUAL-{req.reference_code}-{uuid.uuid4().hex[:6]}"

    resp = VerificationResponse(
        request_id=req.id,
        request_code=req.reference_code,
        instrument_id=instrument.id,
        channel=VerificationChannel.MANUAL.value,
        source_classification=SourceClassification.MANUAL_EVIDENCE.value,
        source_identifier=f"Officer Manual Verification ({current_user.full_name})",
        result=final_result,
        bank_reference_number=external_reference.strip(),
        bank_values_json=json.dumps(bank_values) if bank_values else None,
        field_comparisons_json=json.dumps(field_comparisons) if field_comparisons else None,
        responded_at=communication_date,
        evidence_document_id=doc_ver.document_id if doc_ver else None,
        evidence_document_version_id=doc_ver.id if doc_ver else None,
        is_simulated=False,
        idempotency_key=idempotency_token,
        recorded_by_user_id=current_user.id,
        notes=f"Manual verification: {reason.strip()}",
    )
    db.add(resp)

    # Update request lifecycle
    if final_result == VerificationResult.MATCH.value:
        req.status = VerificationRequestStatus.MATCH.value
    elif final_result == VerificationResult.MISMATCH.value:
        req.status = VerificationRequestStatus.MISMATCH.value
    else:
        req.status = VerificationRequestStatus.RESPONSE_RECEIVED.value

    db.add(req)
    db.commit()
    db.refresh(resp)

    log_audit_event(
        db=db,
        action="MANUAL_VERIFICATION_RECORDED",
        entity_type="verification_response",
        entity_id=resp.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS",
        ip_address=request_ip,
        metadata={
            "request_code": req.reference_code,
            "external_reference": external_reference,
            "result": final_result,
            "reason": reason,
            "evidence_document_version_id": evidence_document_version_id,
        },
    )

    return resp


def retry_verification_request(
    db: Session,
    request_id: str,
    current_user: User,
    scenario: Optional[str] = None,
    request_ip: Optional[str] = None,
) -> VerificationResponse:
    """
    Retries an unavailable or timed-out verification request within bounded retry limits.
    Preserves request code stability and records incremented attempt count.
    """
    _assert_officer_access(current_user)

    req = db.scalar(select(VerificationRequest).where(VerificationRequest.id == request_id))
    if not req:
        raise AppException(
            message=f"Verification request '{request_id}' not found.",
            status_code=404,
            code="REQUEST_NOT_FOUND",
        )

    # Enforce bounded retry limit
    max_retries = settings.MAX_VERIFICATION_RETRY_ATTEMPTS
    if req.attempt_count >= max_retries:
        raise AppException(
            message=(
                f"Maximum retry attempts reached ({req.attempt_count}/{max_retries}). "
                "Request must be closed or investigated via manual correspondence."
            ),
            status_code=422,
            code="MAX_RETRIES_EXCEEDED",
            details={"attempt_count": req.attempt_count, "max_retries": max_retries},
        )

    # Increment attempt count
    req.attempt_count += 1
    req.status = VerificationRequestStatus.SENT.value
    db.add(req)
    db.commit()

    log_audit_event(
        db=db,
        action="VERIFICATION_REQUEST_RETRIED",
        entity_type="verification_request",
        entity_id=req.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS",
        ip_address=request_ip,
        metadata={
            "reference_code": req.reference_code,
            "attempt_count": req.attempt_count,
            "channel": req.channel,
        },
    )

    # Re-dispatch with incremented attempt
    return dispatch_verification_request(
        db=db,
        request_id=req.id,
        current_user=current_user,
        scenario=scenario,
        request_ip=request_ip,
    )


def cancel_verification_request(
    db: Session,
    request_id: str,
    reason: str,
    current_user: User,
    request_ip: Optional[str] = None,
) -> VerificationRequest:
    """Cancels or closes a verification request with a mandatory reason."""
    _assert_officer_access(current_user)

    if not reason or not reason.strip():
        raise AppException(
            message="Reason is strictly mandatory when cancelling or closing a verification request.",
            status_code=422,
            code="REASON_REQUIRED",
        )

    req = db.scalar(select(VerificationRequest).where(VerificationRequest.id == request_id))
    if not req:
        raise AppException(
            message=f"Verification request '{request_id}' not found.",
            status_code=404,
            code="REQUEST_NOT_FOUND",
        )

    req.status = VerificationRequestStatus.CANCELLED.value
    req.closed_at = datetime.now(timezone.utc)
    req.closed_reason = reason.strip()
    db.add(req)
    db.commit()
    db.refresh(req)

    log_audit_event(
        db=db,
        action="VERIFICATION_REQUEST_CANCELLED",
        entity_type="verification_request",
        entity_id=req.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        outcome="SUCCESS",
        ip_address=request_ip,
        metadata={
            "reference_code": req.reference_code,
            "closed_reason": req.closed_reason,
        },
    )

    return req


def get_verification_response_by_id(
    db: Session, response_id: str, current_user: User
) -> VerificationResponse:
    """Retrieve a verification response and its field comparisons, enforcing tenant scoping."""
    resp = db.scalar(select(VerificationResponse).where(VerificationResponse.id == response_id))
    if not resp:
        raise AppException(
            message=f"Verification response '{response_id}' not found.",
            status_code=404,
            code="RESPONSE_NOT_FOUND",
        )
    _assert_instrument_scope(resp.instrument, current_user)
    return resp
