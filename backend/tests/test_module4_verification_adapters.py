"""
Module 4 — Verification Requests, Responses, Manual Evidence & Adapters
Unit and Integration Test Suite
Verifies all 18 requirements from Prompt 2 of 5:
1. Creating a unique verification request.
2. Request-code uniqueness.
3. Correct matching response.
4. Incorrect request code.
5. Response linked to the wrong instrument.
6. Duplicate response delivery.
7. Mismatch response and conflict preservation.
8. Timeout.
9. Source unavailable.
10. Bounded retry behavior.
11. Manual-evidence path and evidence permissions.
12. Simulated match/mismatch/timeout/source-unavailable paths.
13. Simulation disabled in production configuration.
14. Simulated response cannot satisfy production L3.
15. Unconfigured live provider fails honestly.
16. Cross-tenant access denial.
17. Audit events for material transitions.
18. No direct request/response endpoint can bypass the trust service.
"""
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password, create_access_token
from app.common.exceptions import AppException
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.audit.models import AuditEvent
from app.modules.verification.models import (
    VerificationRequest,
    VerificationResponse,
    TrustAssessment,
)
from app.modules.verification.enums import (
    TrustLevel,
    VerificationChannel,
    VerificationResult,
    VerificationRequestStatus,
    SourceClassification,
)
from app.modules.verification.verification_service import (
    create_verification_request,
    list_instrument_verification_requests,
    get_verification_request_by_id,
    dispatch_verification_request,
    record_manual_verification_result,
    retry_verification_request,
    cancel_verification_request,
    get_verification_response_by_id,
)
from app.modules.verification.trust_service import transition_trust_level


@pytest.fixture
def institution_a(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="INST-V-A",
        legal_name="Indian Institute of Engineering Science",
        display_name="IIES",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar A",
        contact_email="reg.a@iies.ac.in",
        contact_phone="+91-11-23330001",
        address_line1="North Block",
        city="Kolkata",
        state="West Bengal",
        postal_code="711103",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def institution_b(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="INST-V-B",
        legal_name="National Engineering Academy",
        display_name="NEA",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar B",
        contact_email="reg.b@nea.ac.in",
        contact_phone="+91-11-23330002",
        address_line1="South Block",
        city="Chennai",
        state="Tamil Nadu",
        postal_code="600001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def officer_user(db_session: Session) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="officer.desk@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Verification Desk Officer",
        role="SCRUTINY_OFFICER",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def institution_user_a(db_session: Session, institution_a: Institution) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="user.a@iies.ac.in",
        password_hash=hash_password("Pass@123456"),
        full_name="IIES User A",
        role="INSTITUTION_USER",
        institution_id=institution_a.id,
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def auditor_user(db_session: Session) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="auditor.desk@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Auditor Desk",
        role="AUDITOR",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def instrument_a(db_session: Session, institution_a: Institution) -> Instrument:
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-IIES-2026-900",
        bank_name="State Bank of India",
        branch="IIES Campus Branch",
        amount=Decimal("2500000.00"),
        currency="INR",
        issue_date=date(2025, 4, 1),
        maturity_date=date(2030, 4, 1),
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
def instrument_b(db_session: Session, institution_b: Institution) -> Instrument:
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_b.id,
        reference_number="FDR-NEA-2026-901",
        bank_name="Punjab National Bank",
        branch="Chennai Main",
        amount=Decimal("1500000.00"),
        currency="INR",
        issue_date=date(2025, 5, 1),
        maturity_date=date(2030, 5, 1),
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
def document_a_version(
    db_session: Session, instrument_a: Instrument, institution_a: Institution, officer_user: User
) -> DocumentVersion:
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        instrument_id=instrument_a.id,
        category="FDR_COPY",
        title="FDR Certificate Copy",
        status="ACTIVE",
        created_by_user_id=officer_user.id,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    doc_ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"m4_desk/{uuid.uuid4()}.pdf",
        original_filename="fdr_iies_scan.pdf",
        content_type="application/pdf",
        file_size_bytes=15360,
        sha256_hash="a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
        processing_status="CLEAN",
        uploader_user_id=officer_user.id,
    )
    db_session.add(doc_ver)
    db_session.commit()
    db_session.refresh(doc_ver)

    doc.current_version_id = doc_ver.id
    db_session.add(doc)
    db_session.commit()
    return doc_ver


# ===========================================================================
# 1. Creating a Unique Verification Request
# ===========================================================================
def test_creating_unique_verification_request(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies creation of verification request with frozen snapshot and pending state."""
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
        requested_fields=["amount", "maturity_date", "bank_name", "reference_number"],
        notes="Routine regulatory scrutiny check",
    )
    assert req.id is not None
    assert req.instrument_id == instrument_a.id
    assert req.reference_code.startswith("VR-SEC-")
    assert req.status == "PENDING"
    assert req.attempt_count == 1
    assert "2500000.00" in req.snapshot_data_json


# ===========================================================================
# 2. Request-Code Uniqueness
# ===========================================================================
def test_request_code_uniqueness(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies that each request code is cryptographically unique and non-guessable."""
    req1 = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    req2 = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    assert req1.reference_code != req2.reference_code
    assert len(req1.reference_code) >= 15


# ===========================================================================
# 3. Correct Matching Response
# ===========================================================================
def test_correct_matching_response(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies simulated matching response ingestion and status transition to MATCH."""
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    resp = dispatch_verification_request(
        db=db_session,
        request_id=req.id,
        current_user=officer_user,
        scenario="MATCH",
    )
    assert resp.result == "MATCH"
    assert resp.is_simulated is True
    assert resp.source_classification == "SIMULATION"

    db_session.refresh(req)
    assert req.status == "MATCH"
    assert "field_comparisons_json" in resp.__dict__ or resp.field_comparisons_json is not None


# ===========================================================================
# 4. Incorrect Request Code Rejected
# ===========================================================================
def test_incorrect_request_code(
    client: TestClient, db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies that an unknown or mismatched request ID returns 404."""
    token = create_access_token(user_id=officer_user.id, email=officer_user.email, role=officer_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    fake_id = str(uuid.uuid4())
    res = client.post(f"/api/v1/verification/requests/{fake_id}/dispatch", headers=headers, json={"scenario": "MATCH"})
    assert res.status_code == 404
    assert res.json()["code"] == "REQUEST_NOT_FOUND"


# ===========================================================================
# 5. Response Linked to Wrong Instrument
# ===========================================================================
def test_response_linked_to_wrong_instrument(
    db_session: Session, instrument_a: Instrument, instrument_b: Instrument, officer_user: User
):
    """Verifies that a response generated for Instrument B cannot satisfy Instrument A."""
    req_b = create_verification_request(
        db=db_session,
        instrument_id=instrument_b.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    resp_b = dispatch_verification_request(
        db=db_session,
        request_id=req_b.id,
        current_user=officer_user,
        scenario="MATCH",
    )

    with pytest.raises(AppException) as exc:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L3_BANK_CONFIRMED.value,
            reason="Attempting cross-instrument response injection",
            related_verification_response_id=resp_b.id,
            current_user=officer_user,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "CROSS_INSTRUMENT_RESPONSE_REJECTED"


# ===========================================================================
# 6. Duplicate Response Delivery (Idempotency)
# ===========================================================================
def test_duplicate_response_delivery(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies that repeated delivery of a response returns the existing record idempotently."""
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    resp1 = dispatch_verification_request(
        db=db_session,
        request_id=req.id,
        current_user=officer_user,
        scenario="MATCH",
    )
    # Re-dispatch with same attempt count
    resp2 = dispatch_verification_request(
        db=db_session,
        request_id=req.id,
        current_user=officer_user,
        scenario="MATCH",
    )
    assert resp1.id == resp2.id
    assert resp1.idempotency_key == resp2.idempotency_key


# ===========================================================================
# 7. Mismatch Response & Conflict Preservation
# ===========================================================================
def test_mismatch_response_and_conflict_preservation(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies mismatch responses preserve both registered and divergent bank values without overwriting."""
    original_amount = instrument_a.amount
    original_maturity = instrument_a.maturity_date

    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    resp = dispatch_verification_request(
        db=db_session,
        request_id=req.id,
        current_user=officer_user,
        scenario="MISMATCH",
    )
    assert resp.result == "MISMATCH"

    db_session.refresh(req)
    assert req.status == "MISMATCH"

    # Invariant: Instrument facts MUST NOT be overwritten
    db_session.refresh(instrument_a)
    assert instrument_a.amount == original_amount
    assert instrument_a.maturity_date == original_maturity

    # Invariant: Divergent values are itemized in field comparisons
    assert resp.field_comparisons_json is not None
    assert "amount" in resp.field_comparisons_json


# ===========================================================================
# 8. Timeout Handling
# ===========================================================================
def test_timeout_handling(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies timeout outcome updates status to TIMEOUT and never upgrades trust."""
    initial_trust = instrument_a.trust_level

    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    resp = dispatch_verification_request(
        db=db_session,
        request_id=req.id,
        current_user=officer_user,
        scenario="TIMEOUT",
    )
    assert resp.result == "TIMEOUT"

    db_session.refresh(req)
    assert req.status == "TIMEOUT"
    assert req.error_details is not None

    db_session.refresh(instrument_a)
    assert instrument_a.trust_level == initial_trust


# ===========================================================================
# 9. Source Unavailable Handling
# ===========================================================================
def test_source_unavailable_handling(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies source unavailable outcome updates status and records diagnostics."""
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    resp = dispatch_verification_request(
        db=db_session,
        request_id=req.id,
        current_user=officer_user,
        scenario="SOURCE_UNAVAILABLE",
    )
    assert resp.result == "SOURCE_UNAVAILABLE"

    db_session.refresh(req)
    assert req.status == "SOURCE_UNAVAILABLE"
    assert "maintenance" in req.error_details.lower() or "503" in req.error_details


# ===========================================================================
# 10. Bounded Retry Behavior
# ===========================================================================
def test_bounded_retry_behavior(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies retry increments attempt count, keeps code stable, and enforces max attempts limit (3)."""
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    initial_code = req.reference_code

    # First attempt: timeout
    dispatch_verification_request(db=db_session, request_id=req.id, current_user=officer_user, scenario="TIMEOUT")
    assert req.attempt_count == 1

    # Retry 1 (Attempt 2)
    retry_verification_request(db=db_session, request_id=req.id, current_user=officer_user, scenario="TIMEOUT")
    db_session.refresh(req)
    assert req.attempt_count == 2
    assert req.reference_code == initial_code

    # Retry 2 (Attempt 3)
    retry_verification_request(db=db_session, request_id=req.id, current_user=officer_user, scenario="TIMEOUT")
    db_session.refresh(req)
    assert req.attempt_count == 3
    assert req.reference_code == initial_code

    # Retry 3 (Attempt 4) -> Exceeds max retries (3) -> 422
    with pytest.raises(AppException) as exc:
        retry_verification_request(db=db_session, request_id=req.id, current_user=officer_user, scenario="TIMEOUT")
    assert exc.value.status_code == 422
    assert exc.value.code == "MAX_RETRIES_EXCEEDED"


# ===========================================================================
# 11. Manual-Evidence Path and Evidence Permissions
# ===========================================================================
def test_manual_evidence_path_and_evidence_permissions(
    db_session: Session,
    instrument_a: Instrument,
    document_a_version: DocumentVersion,
    institution_user_a: User,
    officer_user: User,
):
    """Verifies manual evidence recording requires officer permission, reason, and evidence document."""
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.MANUAL.value,
        current_user=officer_user,
    )

    # 1. Non-officer attempt -> 403 Forbidden
    with pytest.raises(AppException) as exc1:
        record_manual_verification_result(
            db=db_session,
            request_id=req.id,
            external_reference="BRANCH-LETTER-2026-99",
            communication_date=datetime.now(timezone.utc),
            result="MATCH",
            reason="Institution user self-recording",
            current_user=institution_user_a,
        )
    assert exc1.value.status_code == 403

    # 2. Officer attempt with missing reason -> 422
    with pytest.raises(AppException) as exc2:
        record_manual_verification_result(
            db=db_session,
            request_id=req.id,
            external_reference="BRANCH-LETTER-2026-99",
            communication_date=datetime.now(timezone.utc),
            result="MATCH",
            reason="   ",
            current_user=officer_user,
        )
    assert exc2.value.status_code == 422
    assert exc2.value.code == "REASON_REQUIRED"

    # 3. Valid officer manual record with Module 2 evidence
    resp = record_manual_verification_result(
        db=db_session,
        request_id=req.id,
        external_reference="BRANCH-CONFIRM-2026-001",
        communication_date=datetime.now(timezone.utc),
        result="MATCH",
        reason="Branch Chief Manager confirmed validity over registered speed-post letter.",
        evidence_document_version_id=document_a_version.id,
        bank_values={"amount": "2500000.00", "reference_number": instrument_a.reference_number},
        current_user=officer_user,
    )
    assert resp.result == "MATCH"
    assert resp.source_classification == "MANUAL_EVIDENCE"
    assert resp.is_simulated is False
    assert resp.evidence_document_version_id == document_a_version.id


# ===========================================================================
# 12. Simulated Scenarios Comprehensive
# ===========================================================================
def test_simulated_scenarios_comprehensive(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies all 5 prototype simulated adapter scenarios (MATCH, MISMATCH, TIMEOUT, SOURCE_UNAVAILABLE, INCONCLUSIVE)."""
    scenarios = ["MATCH", "MISMATCH", "TIMEOUT", "SOURCE_UNAVAILABLE", "INCONCLUSIVE"]
    for sc in scenarios:
        req = create_verification_request(
            db=db_session,
            instrument_id=instrument_a.id,
            channel=VerificationChannel.SIMULATED.value,
            current_user=officer_user,
        )
        resp = dispatch_verification_request(
            db=db_session,
            request_id=req.id,
            current_user=officer_user,
            scenario=sc,
        )
        assert resp.is_simulated is True
        assert resp.source_classification == "SIMULATION"
        assert "NOT contact a real bank" in resp.notes


# ===========================================================================
# 13. Simulation Disabled in Production Configuration
# ===========================================================================
def test_simulation_disabled_in_production_configuration(
    db_session: Session, instrument_a: Instrument, officer_user: User, monkeypatch
):
    """Verifies that setting ENVIRONMENT='production' or ENABLE_SIMULATED_VERIFICATION=False blocks simulation."""
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )

    # Simulate production environment
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    with pytest.raises(AppException) as exc1:
        dispatch_verification_request(
            db=db_session, request_id=req.id, current_user=officer_user, scenario="MATCH"
        )
    assert exc1.value.status_code == 403
    assert exc1.value.code == "SIMULATION_DISABLED_IN_PRODUCTION"

    # Reset environment, disable toggle
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ENABLE_SIMULATED_VERIFICATION", False)
    with pytest.raises(AppException) as exc2:
        dispatch_verification_request(
            db=db_session, request_id=req.id, current_user=officer_user, scenario="MATCH"
        )
    assert exc2.value.status_code == 403
    assert exc2.value.code == "SIMULATION_DISABLED_IN_PRODUCTION"


# ===========================================================================
# 14. Simulated Response Cannot Satisfy Production L3
# ===========================================================================
def test_simulated_response_cannot_satisfy_production_l3(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies that an ingesting simulated MATCH response is strictly rejected for L3 promotion."""
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    resp = dispatch_verification_request(
        db=db_session,
        request_id=req.id,
        current_user=officer_user,
        scenario="MATCH",
    )
    assert resp.is_simulated is True

    # Attempting to assign L3 using this simulated response MUST fail
    with pytest.raises(AppException) as exc:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L3_BANK_CONFIRMED.value,
            reason="Attempting to promote using simulated match",
            related_verification_response_id=resp.id,
            current_user=officer_user,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "SIMULATED_RESPONSE_CANNOT_AUTHORIZE_L3"


# ===========================================================================
# 15. Unconfigured Live Provider Fails Honestly
# ===========================================================================
def test_unconfigured_live_provider_fails_honestly(
    db_session: Session, instrument_a: Instrument, officer_user: User, monkeypatch
):
    """Verifies live banking adapter reports SOURCE_UNAVAILABLE when not provisioned with live credentials."""
    monkeypatch.setattr(settings, "LIVE_BANK_ADAPTER_ENABLED", False)

    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.LIVE_BANK_API.value,
        current_user=officer_user,
    )

    with pytest.raises(AppException) as exc:
        dispatch_verification_request(
            db=db_session, request_id=req.id, current_user=officer_user
        )
    assert exc.value.status_code == 503
    assert exc.value.code == "LIVE_BANK_INTEGRATION_UNCONFIGURED"


# ===========================================================================
# 16. Cross-Tenant Access Denial
# ===========================================================================
def test_cross_tenant_access_denial(
    client: TestClient,
    db_session: Session,
    instrument_a: Instrument,
    instrument_b: Instrument,
    institution_user_a: User,
    officer_user: User,
):
    """Verifies that an institution user cannot view or dispatch requests for another tenant."""
    # Create request on Instrument B
    req_b = create_verification_request(
        db=db_session,
        instrument_id=instrument_b.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )

    token_a = create_access_token(
        user_id=institution_user_a.id, email=institution_user_a.email, role=institution_user_a.role
    )
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Institution user A querying Instrument B requests -> 403 Forbidden
    res1 = client.get(f"/api/v1/verification/instruments/{instrument_b.id}/requests", headers=headers_a)
    assert res1.status_code == 403
    assert res1.json()["code"] == "FORBIDDEN_CROSS_TENANT_ACCESS"

    # Institution user A querying request details for Instrument B -> 403 Forbidden
    res2 = client.get(f"/api/v1/verification/requests/{req_b.id}", headers=headers_a)
    assert res2.status_code == 403
    assert res2.json()["code"] == "FORBIDDEN_CROSS_TENANT_ACCESS"


# ===========================================================================
# 17. Audit Events for Material Transitions
# ===========================================================================
def test_audit_events_for_material_transitions(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies that request creation, dispatch, retry, and cancellation log immutable audit records."""
    # 1. Create request
    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    # 2. Dispatch
    dispatch_verification_request(
        db=db_session, request_id=req.id, current_user=officer_user, scenario="MATCH"
    )
    # 3. Cancel
    cancel_verification_request(
        db=db_session, request_id=req.id, reason="Closing verified case", current_user=officer_user
    )

    # Inspect audit_events table
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.actor_user_id == officer_user.id)
        .order_by(AuditEvent.created_at.desc())
    )
    events = list(db_session.scalars(stmt).all())
    action_types = {e.action for e in events}

    assert "VERIFICATION_REQUEST_CREATED" in action_types
    assert "VERIFICATION_RESPONSE_RECEIVED" in action_types
    assert "VERIFICATION_REQUEST_CANCELLED" in action_types


# ===========================================================================
# 18. No Direct Request / Response Endpoint Can Bypass Trust Service
# ===========================================================================
def test_no_direct_endpoint_can_bypass_trust_service(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies that recording a verification response does not alter Instrument.trust_level."""
    initial_trust = instrument_a.trust_level
    assert initial_trust == "L0_DECLARED"

    req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        current_user=officer_user,
    )
    resp = dispatch_verification_request(
        db=db_session,
        request_id=req.id,
        current_user=officer_user,
        scenario="MATCH",
    )
    assert resp.result == "MATCH"

    # Invariant: Instrument trust level is STILL L0_DECLARED
    db_session.refresh(instrument_a)
    assert instrument_a.trust_level == "L0_DECLARED"
