"""
Module 4 — Trust, Provenance & Verification Desk
API Router
Provides endpoints for field-level provenance, trust state assessments,
durable transition history, and verification requests/responses.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
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
    FieldProvenanceResponse,
    RecordFieldProvenanceRequest,
    TrustAssessmentResponse,
    TrustTransitionRequest,
    TrustTransitionHistoryResponse,
    VerificationRequestCreate,
    VerificationRequestResponse,
    VerificationResponseCreate,
    VerificationResponseOut,
)
from app.modules.verification.provenance_service import (
    record_field_provenance,
    get_active_field_provenances,
    get_field_provenance_history,
)
from app.modules.verification.trust_service import (
    transition_trust_level,
    get_active_trust_assessments,
    get_trust_transition_history,
    create_verification_request,
    record_verification_response,
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
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )
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
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )
    _assert_instrument_tenant_access(instrument, current_user)
    return get_field_provenance_history(db=db, instrument_id=instrument_id, field_name=field_name)


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
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )
    _assert_instrument_tenant_access(instrument, current_user)
    return get_active_trust_assessments(db=db, instrument_id=instrument_id)


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
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            message=f"Instrument '{instrument_id}' not found.",
            status_code=404,
            code="INSTRUMENT_NOT_FOUND",
        )
    _assert_instrument_tenant_access(instrument, current_user)
    return get_trust_transition_history(db=db, instrument_id=instrument_id)


@router.post(
    "/instruments/{instrument_id}/trust/transition",
    response_model=TrustAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Transition trust level (L0-L3)",
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
    Enforces role authorization, mandatory reasons, documentary evidence, and verification response validity.
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
        request_ip=client_ip,
    )


@router.post(
    "/requests",
    response_model=VerificationRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a verification request",
)
def create_request(
    payload: VerificationRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """Dispatches a bank or external verification request."""
    return create_verification_request(
        db=db,
        instrument_id=payload.instrument_id,
        channel=payload.channel,
        requested_by_user=current_user,
        notes=payload.notes,
    )


@router.post(
    "/responses",
    response_model=VerificationResponseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a verification response",
)
def record_response(
    payload: VerificationResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _csrf: None = Depends(verify_csrf_origin),
):
    """Records an incoming bank or adapter verification response with simulation flag integrity."""
    return record_verification_response(
        db=db,
        request_id=payload.request_id,
        channel=payload.channel,
        result=payload.result,
        is_simulated=payload.is_simulated,
        idempotency_key=payload.idempotency_key,
        recorded_by_user=current_user,
        bank_reference_number=payload.bank_reference_number,
        bank_values=payload.bank_values,
        evidence_document_id=payload.evidence_document_id,
        evidence_document_version_id=payload.evidence_document_version_id,
        notes=payload.notes,
    )
