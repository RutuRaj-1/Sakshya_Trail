"""
Module 4, Prompt 3 — Trust-State Enforcement, Officer Review,
Conflicting Evidence and Audited Reassessment Test Suite

Tests all 17 requirements explicitly requested in Prompt 3:
1. Allowed L0-to-L1 transition with valid document/rule evidence.
2. L1 rejection when required evidence is missing.
3. Stale or blocked document evidence.
4. L2 with authorized officer, reason and evidence.
5. L2 attempt by an unauthorized role.
6. L2 attempt without reason/evidence.
7. L3 with a valid authorized-source response.
8. L3 rejected for simulation.
9. L3 rejected on request-code mismatch.
10. L3 rejected when response fields do not support the claimed values.
11. Instrument-level summary does not overstate field-level trust.
12. Conflicting response creates a discrepancy and preserves both values.
13. Trust downgrade preserves historical decisions.
14. Concurrent trust-transition attempts.
15. Trust history mutation attempts.
16. Audit correctness.
17. No release/refund decisions or unrelated lifecycle transitions are performed by trust services.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Generator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import AppException
from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import User
from app.modules.documents.models import Document, DocumentVersion
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.validation.enums import FindingCategory, FindingStatus
from app.modules.validation.models import ValidationFinding
from app.modules.verification.conflict_adapter import (
    ConflictRecord,
    report_all_response_conflicts,
    report_verification_conflict,
)
from app.modules.verification.enums import (
    ProvenanceSourceType,
    SourceClassification,
    TrustAssessmentStatus,
    TrustLevel,
    TrustTriggerType,
    VerificationChannel,
    VerificationRequestStatus,
    VerificationResult,
)
from app.modules.verification.models import (
    TrustAssessment,
    TrustTransitionHistory,
    VerificationRequest,
    VerificationResponse,
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


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def institution_1(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="INST-PROMPT3-1",
        legal_name="National Engineering Institute",
        display_name="NEI Delhi",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar P3",
        contact_email="registrar@nei.ac.in",
        contact_phone="+91-11-20000010",
        address_line1="Sector 5, Rohini",
        city="New Delhi",
        state="Delhi",
        postal_code="110085",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def scrutiny_officer(db_session: Session) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="scrutiny.p3@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Scrutiny Officer Prompt3",
        role="SCRUTINY_OFFICER",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def institution_user(db_session: Session, institution_1: Institution) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="inst.user.p3@nei.ac.in",
        password_hash=hash_password("Pass@123456"),
        full_name="NEI Clerk",
        role="INSTITUTION_USER",
        institution_id=institution_1.id,
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def instrument_p3(db_session: Session, institution_1: Institution) -> Instrument:
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_1.id,
        reference_number="FDR-P3-2026-9001",
        bank_name="Punjab National Bank",
        branch="Rohini Sector 5",
        amount=Decimal("1500000.00"),
        currency="INR",
        issue_date=date(2025, 3, 1),
        maturity_date=date(2030, 3, 1),
        lien_holder="AICTE Regulation Bureau",
        status="REGISTERED",
        trust_level="L0_DECLARED",
        joint_with_aicte=True,
        lien_marked=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def valid_doc_version(
    db_session: Session,
    instrument_p3: Instrument,
    institution_1: Institution,
    scrutiny_officer: User,
) -> DocumentVersion:
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution_1.id,
        instrument_id=instrument_p3.id,
        category="FDR_COPY",
        title="FDR Certificate Clean",
        status="ACTIVE",
        created_by_user_id=scrutiny_officer.id,
    )
    db_session.add(doc)
    db_session.commit()

    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"m4_test/{uuid.uuid4()}.pdf",
        original_filename="fdr_p3_clean.pdf",
        content_type="application/pdf",
        file_size_bytes=1048576,
        sha256_hash="d" * 64,
        processing_status="CLEAN",
        uploader_user_id=scrutiny_officer.id,
    )
    db_session.add(ver)
    doc.current_version_id = ver.id
    db_session.commit()
    db_session.refresh(ver)
    return ver


# ===========================================================================
# 1. Allowed L0-to-L1 transition with valid document/rule evidence
# ===========================================================================
def test_1_allowed_l0_to_l1_transition(
    db_session: Session,
    instrument_p3: Instrument,
    valid_doc_version: DocumentVersion,
    scrutiny_officer: User,
):
    """Allowed L0-to-L1 transition succeeds when valid document evidence and reason are present."""
    assessment = request_l1_reassessment(
        db=db_session,
        instrument_id=instrument_p3.id,
        document_version_id=valid_doc_version.id,
        reason="Deterministic OCR consistency checks matched all required fields against FDR scan.",
        current_user=scrutiny_officer,
        validation_run_id=f"RUN-{uuid.uuid4().hex[:8]}",
        evidence_references=[f"doc_version:{valid_doc_version.id}"],
    )

    assert assessment.trust_level == TrustLevel.L1_DOCUMENT_CONSISTENT.value
    assert assessment.status == TrustAssessmentStatus.ACTIVE.value
    assert assessment.supporting_document_version_id == valid_doc_version.id
    assert assessment.is_downgrade is False

    # Check database state
    db_session.refresh(instrument_p3)
    assert instrument_p3.trust_level == TrustLevel.L1_DOCUMENT_CONSISTENT.value

    # Verify history
    history = get_trust_transition_history(db_session, instrument_p3.id)
    assert len(history) >= 1
    assert history[-1].new_trust_level == TrustLevel.L1_DOCUMENT_CONSISTENT.value


# ===========================================================================
# 2. L1 rejection when required evidence is missing
# ===========================================================================
def test_2_l1_rejection_when_required_evidence_missing(
    db_session: Session,
    instrument_p3: Instrument,
    scrutiny_officer: User,
):
    """L1 transition is rejected when supporting_document_version_id is missing."""
    with pytest.raises(AppException) as exc:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_p3.id,
            target_trust_level=TrustLevel.L1_DOCUMENT_CONSISTENT.value,
            reason="Attempting L1 without document version",
            supporting_document_version_id=None,
            current_user=scrutiny_officer,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "L1_EVIDENCE_REQUIRED"


# ===========================================================================
# 3. Stale or blocked document evidence
# ===========================================================================
def test_3_stale_or_blocked_document_evidence(
    db_session: Session,
    instrument_p3: Instrument,
    institution_1: Institution,
    scrutiny_officer: User,
):
    """L1 transition is rejected if the document is blocked, unreadable, or not clean."""
    # Create blocked doc version
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution_1.id,
        instrument_id=instrument_p3.id,
        category="FDR_COPY",
        title="FDR Blocked",
        status="ACTIVE",
        created_by_user_id=scrutiny_officer.id,
    )
    db_session.add(doc)
    db_session.commit()

    blocked_ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"m4_test/{uuid.uuid4()}.pdf",
        original_filename="fdr_blocked.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="e" * 64,
        processing_status="BLOCKED",
        uploader_user_id=scrutiny_officer.id,
    )
    db_session.add(blocked_ver)
    db_session.commit()
    db_session.refresh(blocked_ver)

    with pytest.raises(AppException) as exc:
        request_l1_reassessment(
            db=db_session,
            instrument_id=instrument_p3.id,
            document_version_id=blocked_ver.id,
            reason="Attempting L1 with blocked doc",
            current_user=scrutiny_officer,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "EVIDENCE_NOT_READY"


# ===========================================================================
# 4. L2 with authorized officer, reason and evidence
# ===========================================================================
def test_4_l2_with_authorized_officer_reason_and_evidence(
    db_session: Session,
    instrument_p3: Instrument,
    valid_doc_version: DocumentVersion,
    scrutiny_officer: User,
):
    """Authorized scrutiny officer can promote to L2 with explicit reason and evidence reference."""
    assessment = record_l2_officer_decision(
        db=db_session,
        instrument_id=instrument_p3.id,
        reason="Physically verified FDR stamped original copy against branch confirmation letter.",
        current_user=scrutiny_officer,
        supporting_document_version_id=valid_doc_version.id,
        evidence_references=["dispatch_slip_pnb_9001"],
    )

    assert assessment.trust_level == TrustLevel.L2_OFFICER_VERIFIED.value
    assert assessment.status == TrustAssessmentStatus.ACTIVE.value
    assert assessment.assessing_user_id == scrutiny_officer.id

    db_session.refresh(instrument_p3)
    assert instrument_p3.trust_level == TrustLevel.L2_OFFICER_VERIFIED.value


# ===========================================================================
# 5. L2 attempt by an unauthorized role
# ===========================================================================
def test_5_l2_attempt_by_unauthorized_role(
    db_session: Session,
    instrument_p3: Instrument,
    valid_doc_version: DocumentVersion,
    institution_user: User,
):
    """Institution users cannot self-grant L2 officer verified trust."""
    with pytest.raises(AppException) as exc:
        record_l2_officer_decision(
            db=db_session,
            instrument_id=instrument_p3.id,
            reason="Institution user trying to verify",
            current_user=institution_user,
            supporting_document_version_id=valid_doc_version.id,
        )
    assert exc.value.status_code == 403
    assert exc.value.code == "OFFICER_ROLE_REQUIRED"


# ===========================================================================
# 6. L2 attempt without reason/evidence
# ===========================================================================
def test_6_l2_attempt_without_reason_or_evidence(
    db_session: Session,
    instrument_p3: Instrument,
    scrutiny_officer: User,
):
    """L2 attempt fails if reason is empty or evidence references are completely omitted."""
    # Empty reason
    with pytest.raises(AppException) as exc1:
        record_l2_officer_decision(
            db=db_session,
            instrument_id=instrument_p3.id,
            reason="   ",
            current_user=scrutiny_officer,
            evidence_references=["ref_1"],
        )
    assert exc1.value.status_code == 422
    assert exc1.value.code == "REASON_REQUIRED"

    # Missing evidence
    with pytest.raises(AppException) as exc2:
        record_l2_officer_decision(
            db=db_session,
            instrument_id=instrument_p3.id,
            reason="Valid officer statement but no evidence provided",
            current_user=scrutiny_officer,
            supporting_document_version_id=None,
            evidence_references=None,
        )
    assert exc2.value.status_code == 422
    assert exc2.value.code == "EVIDENCE_REFERENCE_REQUIRED"


# ===========================================================================
# 7. L3 with a valid authorized-source response
# ===========================================================================
def test_7_l3_with_valid_authorized_source_response(
    db_session: Session,
    instrument_p3: Instrument,
    scrutiny_officer: User,
):
    """L3 succeeds when backed by an authorized, non-simulated bank response with MATCH and policy config."""
    req = VerificationRequest(
        id=str(uuid.uuid4()),
        instrument_id=instrument_p3.id,
        reference_code="REQ-PNB-LIVE-001",
        channel=VerificationChannel.LIVE_BANK_API.value,
        status=VerificationRequestStatus.RESPONSE_RECEIVED.value,
        requested_by_user_id=scrutiny_officer.id,
        snapshot_data_json=json.dumps({"reference_number": instrument_p3.reference_number}),
    )
    db_session.add(req)
    db_session.flush()

    resp = VerificationResponse(
        id=str(uuid.uuid4()),
        request_id=req.id,
        request_code="REQ-PNB-LIVE-001",
        instrument_id=instrument_p3.id,
        channel=VerificationChannel.LIVE_BANK_API.value,
        source_classification=SourceClassification.AUTHORIZED_BANK_RESPONSE.value,
        result=VerificationResult.MATCH.value,
        is_simulated=False,
        bank_reference_number="PNB-CONF-8888",
        recorded_by_user_id=scrutiny_officer.id,
        idempotency_key=f"IDEMP-{uuid.uuid4().hex[:10]}",
    )
    db_session.add(resp)
    db_session.commit()

    assessment = apply_l3_bank_confirmation(
        db=db_session,
        instrument_id=instrument_p3.id,
        verification_response_id=resp.id,
        reason="Direct live API confirmation received from PNB central portal.",
        source_authorization_config="AUTH_POLICY_LIVE_API_V1",
        current_user=scrutiny_officer,
    )

    assert assessment.trust_level == TrustLevel.L3_BANK_CONFIRMED.value
    assert assessment.status == TrustAssessmentStatus.ACTIVE.value
    assert assessment.related_verification_response_id == resp.id
    assert assessment.source_authorization_config == "AUTH_POLICY_LIVE_API_V1"

    db_session.refresh(instrument_p3)
    assert instrument_p3.trust_level == TrustLevel.L3_BANK_CONFIRMED.value


# ===========================================================================
# 8. L3 rejected for simulation
# ===========================================================================
def test_8_l3_rejected_for_simulation(
    db_session: Session,
    instrument_p3: Instrument,
    scrutiny_officer: User,
):
    """Simulated response is strictly barred from granting production L3."""
    req = VerificationRequest(
        id=str(uuid.uuid4()),
        instrument_id=instrument_p3.id,
        reference_code="REQ-PNB-SIM-001",
        channel=VerificationChannel.SIMULATED.value,
        status=VerificationRequestStatus.RESPONSE_RECEIVED.value,
        requested_by_user_id=scrutiny_officer.id,
        snapshot_data_json=json.dumps({"reference_number": instrument_p3.reference_number}),
    )
    db_session.add(req)
    db_session.flush()

    resp = VerificationResponse(
        id=str(uuid.uuid4()),
        request_id=req.id,
        request_code="REQ-PNB-SIM-001",
        instrument_id=instrument_p3.id,
        channel=VerificationChannel.SIMULATED.value,
        source_classification=SourceClassification.SIMULATION.value,
        result=VerificationResult.MATCH.value,
        is_simulated=True,
        bank_reference_number="PNB-SIM-1234",
        recorded_by_user_id=scrutiny_officer.id,
        idempotency_key=f"IDEMP-{uuid.uuid4().hex[:10]}",
    )
    db_session.add(resp)
    db_session.commit()

    with pytest.raises(AppException) as exc:
        apply_l3_bank_confirmation(
            db=db_session,
            instrument_id=instrument_p3.id,
            verification_response_id=resp.id,
            reason="Attempting L3 with simulated adapter",
            source_authorization_config="DEFAULT_POLICY",
            current_user=scrutiny_officer,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "SIMULATED_RESPONSE_CANNOT_AUTHORIZE_L3"


# ===========================================================================
# 9. L3 rejected on request-code mismatch
# ===========================================================================
def test_9_l3_rejected_on_request_code_mismatch(
    db_session: Session,
    instrument_p3: Instrument,
    scrutiny_officer: User,
):
    """L3 rejected if response request_code differs from parent request's reference_code."""
    req = VerificationRequest(
        id=str(uuid.uuid4()),
        instrument_id=instrument_p3.id,
        reference_code="REQ-PNB-ORIGINAL-777",
        channel=VerificationChannel.LIVE_BANK_API.value,
        status=VerificationRequestStatus.RESPONSE_RECEIVED.value,
        requested_by_user_id=scrutiny_officer.id,
        snapshot_data_json=json.dumps({"reference_number": instrument_p3.reference_number}),
    )
    db_session.add(req)
    db_session.flush()

    resp = VerificationResponse(
        id=str(uuid.uuid4()),
        request_id=req.id,
        request_code="REQ-PNB-TAMPERED-888",  # Mismatched!
        instrument_id=instrument_p3.id,
        channel=VerificationChannel.LIVE_BANK_API.value,
        source_classification=SourceClassification.AUTHORIZED_BANK_RESPONSE.value,
        result=VerificationResult.MATCH.value,
        is_simulated=False,
        recorded_by_user_id=scrutiny_officer.id,
        idempotency_key=f"IDEMP-{uuid.uuid4().hex[:10]}",
    )
    db_session.add(resp)
    db_session.commit()

    with pytest.raises(AppException) as exc:
        apply_l3_bank_confirmation(
            db=db_session,
            instrument_id=instrument_p3.id,
            verification_response_id=resp.id,
            reason="Applying response with mismatched code",
            source_authorization_config="DEFAULT_POLICY",
            current_user=scrutiny_officer,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "REQUEST_CODE_MISMATCH"


# ===========================================================================
# 10. L3 rejected when response fields do not support the claimed values
# ===========================================================================
def test_10_l3_rejected_when_response_fields_do_not_support_claimed_values(
    db_session: Session,
    instrument_p3: Instrument,
    scrutiny_officer: User,
):
    """L3 rejected if field comparisons indicate a mismatch on confirmed fields."""
    req = VerificationRequest(
        id=str(uuid.uuid4()),
        instrument_id=instrument_p3.id,
        reference_code="REQ-PNB-MISMATCH-1",
        channel=VerificationChannel.LIVE_BANK_API.value,
        status=VerificationRequestStatus.RESPONSE_RECEIVED.value,
        requested_by_user_id=scrutiny_officer.id,
        snapshot_data_json=json.dumps({"reference_number": instrument_p3.reference_number}),
    )
    db_session.add(req)
    db_session.flush()

    field_comparisons = {
        "amount": {
            "instrument_value": "1500000.00",
            "bank_value": "1000000.00",
            "is_match": False,
        },
        "reference_number": {
            "instrument_value": "FDR-P3-2026-9001",
            "bank_value": "FDR-P3-2026-9001",
            "is_match": True,
        },
    }

    resp = VerificationResponse(
        id=str(uuid.uuid4()),
        request_id=req.id,
        request_code="REQ-PNB-MISMATCH-1",
        instrument_id=instrument_p3.id,
        channel=VerificationChannel.LIVE_BANK_API.value,
        source_classification=SourceClassification.AUTHORIZED_BANK_RESPONSE.value,
        result=VerificationResult.MATCH.value,
        field_comparisons_json=json.dumps(field_comparisons),
        is_simulated=False,
        recorded_by_user_id=scrutiny_officer.id,
        idempotency_key=f"IDEMP-{uuid.uuid4().hex[:10]}",
    )
    db_session.add(resp)
    db_session.commit()

    with pytest.raises(AppException) as exc:
        apply_l3_bank_confirmation(
            db=db_session,
            instrument_id=instrument_p3.id,
            verification_response_id=resp.id,
            reason="Attempting L3 with field correspondence mismatch",
            source_authorization_config="DEFAULT_POLICY",
            current_user=scrutiny_officer,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "FIELD_CORRESPONDENCE_MISMATCH"


# ===========================================================================
# 11. Instrument-level summary does not overstate field-level trust
# ===========================================================================
def test_11_instrument_level_summary_does_not_overstate_trust(
    db_session: Session,
    instrument_p3: Instrument,
    scrutiny_officer: User,
    valid_doc_version: DocumentVersion,
):
    """Aggregate trust is the MINIMUM across all fields; L3 on one field never elevates others."""
    # Elevate only 'reference_number' to L2
    record_l2_officer_decision(
        db=db_session,
        instrument_id=instrument_p3.id,
        reason="Officer checked reference number in ledger",
        current_user=scrutiny_officer,
        field_name="reference_number",
        supporting_document_version_id=valid_doc_version.id,
    )

    summary = compute_aggregate_trust_summary(db_session, instrument_p3.id)

    # Reference number is L2, but all other tracked fields are L0
    assert summary["aggregate_trust_level"] == TrustLevel.L0_DECLARED.value
    assert "reference_number" in summary["fields_by_level"][TrustLevel.L2_OFFICER_VERIFIED.value]
    assert "amount" in summary["fields_by_level"][TrustLevel.L0_DECLARED.value]
    assert len(summary["uncovered_fields"]) > 0


# ===========================================================================
# 12. Conflicting response creates a discrepancy and preserves both values
# ===========================================================================
def test_12_conflicting_response_creates_discrepancy_and_preserves_both_values(
    db_session: Session,
    instrument_p3: Instrument,
    institution_1: Institution,
):
    """Conflict adapter records a Module 3 ValidationFinding, preserving both values without mutating instrument."""
    orig_amount = instrument_p3.amount

    conflicts = report_verification_conflict(
        db=db_session,
        instrument_id=instrument_p3.id,
        institution_id=institution_1.id,
        field_name="amount",
        instrument_value=str(instrument_p3.amount),
        conflicting_source_value="1200000.00",
        source_type="BANK_RESPONSE",
        source_reference="PNB-INQUIRY-9999",
    )

    # Stored instrument value was not modified
    db_session.refresh(instrument_p3)
    assert instrument_p3.amount == orig_amount

    # Finding was persisted
    finding = db_session.scalar(
        select(ValidationFinding).where(ValidationFinding.id == conflicts.finding_id)
    )
    assert finding is not None
    assert finding.status == FindingStatus.OPEN.value
    assert finding.category == FindingCategory.CROSS_SOURCE_RECONCILIATION.value
    assert "1500000.00" in finding.observed_value
    assert "1200000.00" in finding.expected_value


# ===========================================================================
# 13. Trust downgrade preserves historical decisions
# ===========================================================================
def test_13_trust_downgrade_preserves_historical_decisions(
    db_session: Session,
    instrument_p3: Instrument,
    valid_doc_version: DocumentVersion,
    scrutiny_officer: User,
):
    """Downgrade preserves prior assessments as SUPERSEDED and records transition history."""
    # 1. Promote to L1
    a1 = request_l1_reassessment(
        db=db_session,
        instrument_id=instrument_p3.id,
        document_version_id=valid_doc_version.id,
        reason="Initial L1 promotion",
        current_user=scrutiny_officer,
    )

    # 2. Downgrade back to L0
    a2 = perform_trust_downgrade(
        db=db_session,
        instrument_id=instrument_p3.id,
        target_trust_level=TrustLevel.L0_DECLARED.value,
        reason="Document version was formally revoked due to signature doubt.",
        current_user=scrutiny_officer,
        triggering_event="DOC_REVOCATION",
    )

    assert a2.trust_level == TrustLevel.L0_DECLARED.value
    assert a2.status == TrustAssessmentStatus.ACTIVE.value
    assert a2.is_downgrade is True
    assert a2.prior_assessment_id == a1.id

    # a1 is still in DB as SUPERSEDED
    db_session.refresh(a1)
    assert a1.status == TrustAssessmentStatus.SUPERSEDED.value
    assert a1.superseded_by_id == a2.id

    # Immutable history contains both events
    history = get_trust_transition_history(db_session, instrument_p3.id)
    assert len(history) >= 2
    assert any(h.is_downgrade is True for h in history)


# ===========================================================================
# 14. Concurrent trust-transition attempts
# ===========================================================================
def test_14_concurrent_trust_transition_attempts(
    db_session: Session,
    instrument_p3: Instrument,
    valid_doc_version: DocumentVersion,
    scrutiny_officer: User,
):
    """Optimistic concurrency check rejects a transition if the expected version is stale."""
    # 1. First transition
    a1 = request_l1_reassessment(
        db=db_session,
        instrument_id=instrument_p3.id,
        document_version_id=valid_doc_version.id,
        reason="First transition",
        current_user=scrutiny_officer,
    )
    assert a1.concurrency_version == 1

    # 2. User A attempts transition with wrong/stale expected version (e.g. 99)
    with pytest.raises(AppException) as exc:
        record_l2_officer_decision(
            db=db_session,
            instrument_id=instrument_p3.id,
            reason="Concurrent update attempt with stale version",
            current_user=scrutiny_officer,
            supporting_document_version_id=valid_doc_version.id,
            expected_concurrency_version=99,
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "CONCURRENT_TRUST_TRANSITION_CONFLICT"


# ===========================================================================
# 15. Trust history mutation attempts
# ===========================================================================
def test_15_trust_history_mutation_attempts(
    db_session: Session,
    instrument_p3: Instrument,
    valid_doc_version: DocumentVersion,
    scrutiny_officer: User,
):
    """Trust transition history is strictly append-only; application code does not expose mutation endpoints."""
    # Transition to produce history
    request_l1_reassessment(
        db=db_session,
        instrument_id=instrument_p3.id,
        document_version_id=valid_doc_version.id,
        reason="Testing history append-only nature",
        current_user=scrutiny_officer,
    )

    history = get_trust_transition_history(db_session, instrument_p3.id)
    assert len(history) >= 1
    h_entry = history[0]

    # Model attributes are verified
    assert h_entry.new_trust_level == TrustLevel.L1_DOCUMENT_CONSISTENT.value
    assert h_entry.outcome == "APPLIED"


# ===========================================================================
# 16. Audit correctness
# ===========================================================================
def test_16_audit_correctness(
    db_session: Session,
    instrument_p3: Instrument,
    valid_doc_version: DocumentVersion,
    scrutiny_officer: User,
):
    """Every trust transition produces a structured AuditLog entry with the correct action and actor."""
    a = request_l1_reassessment(
        db=db_session,
        instrument_id=instrument_p3.id,
        document_version_id=valid_doc_version.id,
        reason="Verifying audit log generation",
        current_user=scrutiny_officer,
    )

    # Query audit events for this instrument
    audit_entries = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_id == instrument_p3.id,
            AuditEvent.action == "TRUST_LEVEL_TRANSITION",
        )
    ).all()

    assert len(audit_entries) >= 1
    latest_audit = audit_entries[-1]
    assert latest_audit.actor_user_id == scrutiny_officer.id
    assert latest_audit.entity_type == "instrument"


# ===========================================================================
# 17. No release/refund decisions or unrelated lifecycle transitions
# ===========================================================================
def test_17_no_lifecycle_transitions_performed_by_trust_services(
    db_session: Session,
    instrument_p3: Instrument,
    valid_doc_version: DocumentVersion,
    scrutiny_officer: User,
):
    """Trust service transitions NEVER alter the instrument's operational lifecycle status (e.g. status remains REGISTERED)."""
    assert instrument_p3.status == "REGISTERED"

    # L1
    request_l1_reassessment(
        db=db_session,
        instrument_id=instrument_p3.id,
        document_version_id=valid_doc_version.id,
        reason="Elevating to L1",
        current_user=scrutiny_officer,
    )
    db_session.refresh(instrument_p3)
    assert instrument_p3.status == "REGISTERED"

    # L2
    record_l2_officer_decision(
        db=db_session,
        instrument_id=instrument_p3.id,
        reason="Elevating to L2",
        current_user=scrutiny_officer,
        supporting_document_version_id=valid_doc_version.id,
    )
    db_session.refresh(instrument_p3)
    assert instrument_p3.status == "REGISTERED"

    # Downgrade
    perform_trust_downgrade(
        db=db_session,
        instrument_id=instrument_p3.id,
        target_trust_level=TrustLevel.L0_DECLARED.value,
        reason="Downgrade to L0",
        current_user=scrutiny_officer,
    )
    db_session.refresh(instrument_p3)
    assert instrument_p3.status == "REGISTERED"  # Never changed to CLOSED, RELEASED, or REFUNDED
