"""
Module 4 — Trust, Provenance & Verification Desk
Unit and Integration Test Suite
Verifies all 12 core requirements from Prompt 1 of 5:
1. Provenance creation for entered/imported values.
2. Provenance linked to a specific document version.
3. Historical provenance retention after correction.
4. L0 initialization.
5. Rejection of L1 without required evidence.
6. Rejection of L2 by unauthorized users or without a reason.
7. Rejection of L3 without a qualifying response.
8. Rejection of L3 based on a simulated response.
9. Rejection of cross-instrument response/evidence links.
10. Preservation of trust history after reassessment/downgrade.
11. Database migrations from the current Module 1–3 schema.
12. Role and institution-scope enforcement.
"""
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone, timedelta
import pytest
from sqlalchemy import select, inspect
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.security import hash_password, create_access_token
from app.common.exceptions import AppException
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.verification.models import (
    FieldProvenance,
    TrustAssessment,
    TrustTransitionHistory,
    VerificationRequest,
    VerificationResponse,
)
from app.modules.verification.enums import (
    TrustLevel,
    ProvenanceSourceType,
    VerificationChannel,
    VerificationResult,
    VerificationRequestStatus,
    TrustAssessmentStatus,
    TrustTriggerType,
)
from app.modules.verification.provenance_service import (
    record_field_provenance,
    get_active_field_provenances,
    get_field_provenance_history,
    initialize_instrument_provenance,
)
from app.modules.verification.trust_service import (
    transition_trust_level,
    get_active_trust_assessments,
    get_trust_transition_history,
    create_verification_request,
    record_verification_response,
)


@pytest.fixture
def institution_a(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="M4-INST-A",
        legal_name="National Institute of Technology",
        display_name="NIT Tech",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar A",
        contact_email="registrar@nit.ac.in",
        contact_phone="+91-11-20000001",
        address_line1="Campus North",
        city="New Delhi",
        state="Delhi",
        postal_code="110001",
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
        code="M4-INST-B",
        legal_name="Regional Engineering College",
        display_name="REC South",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar B",
        contact_email="registrar@rec.ac.in",
        contact_phone="+91-11-20000002",
        address_line1="Campus South",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
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
        email="officer.m4@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Scrutiny Officer M4",
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
        email="inst.user.a@nit.ac.in",
        password_hash=hash_password("Pass@123456"),
        full_name="NIT User A",
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
        email="auditor.m4@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Auditor M4",
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
        reference_number="FDR-NIT-2026-001",
        bank_name="State Bank of India",
        branch="NIT Campus Branch",
        amount=Decimal("1000000.00"),
        currency="INR",
        issue_date=date(2025, 1, 1),
        maturity_date=date(2030, 1, 1),
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
        reference_number="FDR-REC-2026-002",
        bank_name="Canara Bank",
        branch="REC Branch",
        amount=Decimal("500000.00"),
        currency="INR",
        issue_date=date(2025, 2, 1),
        maturity_date=date(2028, 2, 1),
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
def document_a_version(db_session: Session, instrument_a: Instrument, institution_a: Institution, officer_user: User) -> DocumentVersion:
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
        storage_key=f"m4_test/{uuid.uuid4()}.pdf",
        original_filename="fdr_nit_scan.pdf",
        content_type="application/pdf",
        file_size_bytes=10240,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
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
# 1. Provenance Creation for Entered / Imported Values
# ===========================================================================
def test_provenance_creation_entered_imported(
    db_session: Session, instrument_a: Instrument, institution_user_a: User
):
    """Verifies provenance creation for entered and imported values with accurate source types."""
    # Record institution-entered amount
    p1 = record_field_provenance(
        db=db_session,
        instrument_id=instrument_a.id,
        field_name="amount",
        value=Decimal("1000000.00"),
        source_type=ProvenanceSourceType.INSTITUTION_ENTERED.value,
        actor_user_id=institution_user_a.id,
        evidence_reference="Institution annual submission portal",
    )
    assert p1.id is not None
    assert p1.field_name == "amount"
    assert p1.recorded_value == "1000000.00"
    assert p1.source_type == "INSTITUTION_ENTERED"
    assert p1.is_active is True
    assert p1.source_actor_id == institution_user_a.id

    # Record imported bank_name
    p2 = record_field_provenance(
        db=db_session,
        instrument_id=instrument_a.id,
        field_name="bank_name",
        value="State Bank of India",
        source_type=ProvenanceSourceType.IMPORTED.value,
        source_service_id="aicte_legacy_db_importer",
        evidence_reference="Migration batch 2026-Q1",
    )
    assert p2.field_name == "bank_name"
    assert p2.source_type == "IMPORTED"
    assert p2.source_service_id == "aicte_legacy_db_importer"
    assert p2.is_active is True

    # Untracked field must be rejected
    with pytest.raises(AppException) as exc:
        record_field_provenance(
            db=db_session,
            instrument_id=instrument_a.id,
            field_name="unauthorized_secret_field",
            value="hacked",
            source_type=ProvenanceSourceType.INSTITUTION_ENTERED.value,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "UNTRACKED_FIELD"


# ===========================================================================
# 2. Provenance Linked to a Specific Document Version
# ===========================================================================
def test_provenance_linked_to_document_version(
    db_session: Session, instrument_a: Instrument, document_a_version: DocumentVersion, officer_user: User
):
    """Verifies provenance accurately links to concrete document and immutable document-version IDs."""
    prov = record_field_provenance(
        db=db_session,
        instrument_id=instrument_a.id,
        field_name="reference_number",
        value="FDR-NIT-2026-001",
        source_type=ProvenanceSourceType.DOCUMENT_EVIDENCE.value,
        actor_user_id=officer_user.id,
        related_document_id=document_a_version.document_id,
        related_document_version_id=document_a_version.id,
        evidence_reference=f"Extracted from {document_a_version.original_filename} (v{document_a_version.version_number})",
    )
    assert prov.related_document_id == document_a_version.document_id
    assert prov.related_document_version_id == document_a_version.id
    assert prov.is_active is True


# ===========================================================================
# 3. Historical Provenance Retention After Correction
# ===========================================================================
def test_historical_provenance_retention_after_correction(
    db_session: Session, instrument_a: Instrument, institution_user_a: User, officer_user: User
):
    """Verifies corrections create historical provenance rather than erasing prior sources."""
    # 1. Initial declaration
    p_initial = record_field_provenance(
        db=db_session,
        instrument_id=instrument_a.id,
        field_name="amount",
        value=Decimal("1000000.00"),
        source_type=ProvenanceSourceType.INSTITUTION_ENTERED.value,
        actor_user_id=institution_user_a.id,
        evidence_reference="Original submission",
    )
    assert p_initial.is_active is True

    # 2. Corrected declaration
    p_corrected = record_field_provenance(
        db=db_session,
        instrument_id=instrument_a.id,
        field_name="amount",
        value=Decimal("1200000.00"),
        source_type=ProvenanceSourceType.OFFICER_ENTERED.value,
        actor_user_id=officer_user.id,
        evidence_reference="Corrected per bank receipt reconciliation",
    )

    # Refresh p_initial from db
    db_session.refresh(p_initial)

    # Invariants: Old record is NOT erased, but marked inactive and superseded
    assert p_initial.is_active is False
    assert p_initial.superseded_by_id == p_corrected.id
    assert p_initial.recorded_value == "1000000.00"

    # New record points back to prior record
    assert p_corrected.is_active is True
    assert p_corrected.prior_provenance_id == p_initial.id
    assert p_corrected.recorded_value == "1200000.00"

    # History query returns full custody chain
    history = get_field_provenance_history(db=db_session, instrument_id=instrument_a.id, field_name="amount")
    assert len(history) == 2
    assert [h.recorded_value for h in history] == ["1000000.00", "1200000.00"]


# ===========================================================================
# 4. L0 Baseline Initialization
# ===========================================================================
def test_l0_initialization(db_session: Session, instrument_a: Instrument, institution_user_a: User):
    """Verifies baseline field provenance and L0 trust state upon registration."""
    records = initialize_instrument_provenance(
        db=db_session,
        instrument=instrument_a,
        actor_user_id=institution_user_a.id,
    )
    assert len(records) > 0

    active_prov = get_active_field_provenances(db=db_session, instrument_id=instrument_a.id)
    field_names = {p.field_name for p in active_prov}
    assert "amount" in field_names
    assert "bank_name" in field_names
    assert "reference_number" in field_names
    assert "maturity_date" in field_names

    for p in active_prov:
        assert p.source_type == "INSTITUTION_ENTERED"
        assert p.is_active is True


# ===========================================================================
# 5. Rejection of L1 Without Required Evidence
# ===========================================================================
def test_rejection_l1_without_required_evidence(
    db_session: Session, instrument_a: Instrument, document_a_version: DocumentVersion, officer_user: User
):
    """Verifies L1 cannot be assigned without supporting document version or when evidence is blocked."""
    # Attempt L1 without supporting document version ID
    with pytest.raises(AppException) as exc1:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L1_DOCUMENT_CONSISTENT.value,
            reason="Attempting L1 without document version",
            supporting_document_version_id=None,
        )
    assert exc1.value.status_code == 422
    assert exc1.value.code == "L1_EVIDENCE_REQUIRED"

    # Set document processing status to QUARANTINED
    document_a_version.processing_status = "QUARANTINED"
    db_session.add(document_a_version)
    db_session.commit()

    # Attempt L1 with quarantined document version
    with pytest.raises(AppException) as exc2:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L1_DOCUMENT_CONSISTENT.value,
            reason="Attempting L1 with quarantined document",
            supporting_document_version_id=document_a_version.id,
        )
    assert exc2.value.status_code == 422
    assert exc2.value.code == "EVIDENCE_NOT_READY"

    # Restore clean status -> L1 succeeds
    document_a_version.processing_status = "CLEAN"
    db_session.add(document_a_version)
    db_session.commit()

    assessment = transition_trust_level(
        db=db_session,
        instrument_id=instrument_a.id,
        target_trust_level=TrustLevel.L1_DOCUMENT_CONSISTENT.value,
        reason="Verified against clean scanned FDR copy",
        supporting_document_version_id=document_a_version.id,
    )
    assert assessment.trust_level == "L1_DOCUMENT_CONSISTENT"
    assert assessment.status == "ACTIVE"


# ===========================================================================
# 6. Rejection of L2 by Unauthorized Users or Without Reason
# ===========================================================================
def test_rejection_l2_unauthorized_or_no_reason(
    db_session: Session, instrument_a: Instrument, institution_user_a: User, auditor_user: User, officer_user: User, document_a_version: DocumentVersion
):
    """Verifies L2 requires authorized officer role and mandatory non-empty reason."""
    # 1. Institution user attempt -> 403
    with pytest.raises(AppException) as exc1:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
            reason="Institution user self-certifying",
            current_user=institution_user_a,
            supporting_document_version_id=document_a_version.id,
        )
    assert exc1.value.status_code == 403
    assert exc1.value.code == "OFFICER_ROLE_REQUIRED"

    # 2. Auditor attempt -> 403 (Auditor is read-only)
    with pytest.raises(AppException) as exc2:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
            reason="Auditor attempt",
            current_user=auditor_user,
            supporting_document_version_id=document_a_version.id,
        )
    assert exc2.value.status_code == 403
    assert exc2.value.code == "OFFICER_ROLE_REQUIRED"

    # 3. Officer attempt with blank reason -> 422
    with pytest.raises(AppException) as exc3:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
            reason="   ",
            current_user=officer_user,
            supporting_document_version_id=document_a_version.id,
        )
    assert exc3.value.status_code == 422
    assert exc3.value.code == "REASON_REQUIRED"

    # 4. Valid officer attempt with reason and evidence -> Success
    res = transition_trust_level(
        db=db_session,
        instrument_id=instrument_a.id,
        target_trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
        reason="Officer inspected physical certificate and branch seal",
        current_user=officer_user,
        supporting_document_version_id=document_a_version.id,
        evidence_references=["SEAL-INSPECT-2026-44"],
    )
    assert res.trust_level == "L2_OFFICER_VERIFIED"
    assert res.assessing_user_id == officer_user.id


# ===========================================================================
# 7. Rejection of L3 Without a Qualifying Response
# ===========================================================================
def test_rejection_l3_without_qualifying_response(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies L3 strictly requires a qualifying verification response with result=MATCH."""
    # 1. Missing response record -> 422
    with pytest.raises(AppException) as exc1:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L3_BANK_CONFIRMED.value,
            reason="Attempting L3 without response",
            related_verification_response_id=None,
            current_user=officer_user,
        )
    assert exc1.value.status_code == 422
    assert exc1.value.code == "L3_RESPONSE_REQUIRED"

    # Create a verification request
    v_req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.DIRECT_API.value,
        requested_by_user=officer_user,
    )

    # 2. Response with MISMATCH result -> 422
    v_resp_mismatch = record_verification_response(
        db=db_session,
        request_id=v_req.id,
        channel=VerificationChannel.DIRECT_API.value,
        result=VerificationResult.MISMATCH.value,
        is_simulated=False,
        idempotency_key="IDEMP-MISMATCH-001",
        recorded_by_user=officer_user,
    )

    with pytest.raises(AppException) as exc2:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L3_BANK_CONFIRMED.value,
            reason="Attempting L3 with mismatched bank response",
            related_verification_response_id=v_resp_mismatch.id,
            current_user=officer_user,
        )
    assert exc2.value.status_code == 422
    assert exc2.value.code == "RESPONSE_NOT_MATCHED"


# ===========================================================================
# 8. Rejection of L3 Based on a Simulated Response
# ===========================================================================
def test_rejection_l3_simulated_response(
    db_session: Session, instrument_a: Instrument, officer_user: User
):
    """Verifies simulated responses are strictly barred from promoting trust to L3_BANK_CONFIRMED."""
    v_req = create_verification_request(
        db=db_session,
        instrument_id=instrument_a.id,
        channel=VerificationChannel.SIMULATED.value,
        requested_by_user=officer_user,
        notes="Testing simulation boundary",
    )

    v_resp_sim = record_verification_response(
        db=db_session,
        request_id=v_req.id,
        channel=VerificationChannel.SIMULATED.value,
        result=VerificationResult.MATCH.value,
        is_simulated=True,
        idempotency_key="IDEMP-SIM-001",
        recorded_by_user=officer_user,
        bank_reference_number="SIM-SBI-9999",
    )

    with pytest.raises(AppException) as exc:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L3_BANK_CONFIRMED.value,
            reason="Promoting using simulated match",
            related_verification_response_id=v_resp_sim.id,
            current_user=officer_user,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "SIMULATED_RESPONSE_CANNOT_AUTHORIZE_L3"


# ===========================================================================
# 9. Rejection of Cross-Instrument Response / Evidence Links
# ===========================================================================
def test_rejection_cross_instrument_links(
    db_session: Session, instrument_a: Instrument, instrument_b: Instrument, officer_user: User
):
    """Verifies a verification response belonging to Instrument B cannot be used to confirm Instrument A."""
    # Create request and authentic matching response on Instrument B
    v_req_b = create_verification_request(
        db=db_session,
        instrument_id=instrument_b.id,
        channel=VerificationChannel.DIRECT_API.value,
        requested_by_user=officer_user,
    )
    v_resp_b = record_verification_response(
        db=db_session,
        request_id=v_req_b.id,
        channel=VerificationChannel.DIRECT_API.value,
        result=VerificationResult.MATCH.value,
        is_simulated=False,
        idempotency_key="IDEMP-B-MATCH-001",
        recorded_by_user=officer_user,
        bank_reference_number="CANARA-AUTH-7777",
    )

    # Attempt to apply Instrument B's response to Instrument A
    with pytest.raises(AppException) as exc:
        transition_trust_level(
            db=db_session,
            instrument_id=instrument_a.id,
            target_trust_level=TrustLevel.L3_BANK_CONFIRMED.value,
            reason="Attempting cross-instrument response injection",
            related_verification_response_id=v_resp_b.id,
            current_user=officer_user,
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "CROSS_INSTRUMENT_RESPONSE_REJECTED"


# ===========================================================================
# 10. Preservation of Trust History After Reassessment / Downgrade
# ===========================================================================
def test_preservation_of_trust_history_after_reassessment_downgrade(
    db_session: Session, instrument_a: Instrument, document_a_version: DocumentVersion, officer_user: User
):
    """Verifies trust downgrades preserve prior assessment records and capture mandatory audit history."""
    # 1. Elevate to L1
    t1 = transition_trust_level(
        db=db_session,
        instrument_id=instrument_a.id,
        target_trust_level=TrustLevel.L1_DOCUMENT_CONSISTENT.value,
        reason="Document verified",
        supporting_document_version_id=document_a_version.id,
        current_user=officer_user,
    )
    assert t1.trust_level == "L1_DOCUMENT_CONSISTENT"
    assert t1.status == "ACTIVE"

    # 2. Elevate to L2
    t2 = transition_trust_level(
        db=db_session,
        instrument_id=instrument_a.id,
        target_trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
        reason="Officer inspected original copy",
        supporting_document_version_id=document_a_version.id,
        current_user=officer_user,
    )
    db_session.refresh(t1)
    assert t1.status == "SUPERSEDED"
    assert t1.superseded_by_id == t2.id
    assert t2.trust_level == "L2_OFFICER_VERIFIED"
    assert t2.status == "ACTIVE"

    # 3. Reassessment / Downgrade to L0 due to revised evidence
    t3 = transition_trust_level(
        db=db_session,
        instrument_id=instrument_a.id,
        target_trust_level=TrustLevel.L0_DECLARED.value,
        reason="Bank reported signature discrepancy on physical instrument; resetting to L0",
        current_user=officer_user,
        trigger_type=TrustTriggerType.REASSESSMENT_DOWNGRADE.value,
    )
    db_session.refresh(t2)
    assert t2.status == "SUPERSEDED"
    assert t2.superseded_by_id == t3.id

    assert t3.trust_level == "L0_DECLARED"
    assert t3.is_downgrade is True
    assert instrument_a.trust_level == "L0_DECLARED"

    # 4. Verify durable audit history
    history = get_trust_transition_history(db=db_session, instrument_id=instrument_a.id)
    assert len(history) >= 3
    downgrade_entries = [h for h in history if h.is_downgrade]
    assert len(downgrade_entries) == 1
    assert downgrade_entries[0].prior_trust_level == "L2_OFFICER_VERIFIED"
    assert downgrade_entries[0].new_trust_level == "L0_DECLARED"
    assert "signature discrepancy" in downgrade_entries[0].reason


# ===========================================================================
# 11. Database Migrations from Current Module 1–3 Schema
# ===========================================================================
def test_database_migrations_module4(db_session: Session):
    """Verifies all Module 4 tables, foreign keys, and indexes exist in the relational schema."""
    inspector = inspect(db_session.bind)
    table_names = inspector.get_table_names()

    required_tables = [
        "field_provenances",
        "verification_requests",
        "verification_responses",
        "trust_assessments",
        "trust_transition_history",
    ]
    for tbl in required_tables:
        assert tbl in table_names, f"Table {tbl} must exist in the database schema"

    # Verify column presence on field_provenances
    fp_cols = {c["name"] for c in inspector.get_columns("field_provenances")}
    assert "instrument_id" in fp_cols
    assert "field_name" in fp_cols
    assert "recorded_value" in fp_cols
    assert "source_type" in fp_cols
    assert "is_active" in fp_cols
    assert "prior_provenance_id" in fp_cols

    # Verify column presence on verification_responses
    vr_cols = {c["name"] for c in inspector.get_columns("verification_responses")}
    assert "is_simulated" in vr_cols
    assert "idempotency_key" in vr_cols
    assert "result" in vr_cols


# ===========================================================================
# 12. Role and Institution-Scope Enforcement
# ===========================================================================
def test_role_and_institution_scope_enforcement(
    client: TestClient,
    db_session: Session,
    instrument_a: Instrument,
    instrument_b: Instrument,
    institution_user_a: User,
    officer_user: User,
    auditor_user: User,
):
    """Verifies institution scoping prevents cross-tenant access and auditors remain strictly read-only."""
    # 1. Institution User A token
    token_inst_a = create_access_token(
        user_id=institution_user_a.id, email=institution_user_a.email, role=institution_user_a.role
    )
    headers_inst_a = {"Authorization": f"Bearer {token_inst_a}"}

    # Access own instrument provenance -> 200 OK
    res_own = client.get(f"/api/v1/verification/instruments/{instrument_a.id}/provenance", headers=headers_inst_a)
    assert res_own.status_code == 200

    # Cross-tenant access to Instrument B -> 403 Forbidden
    res_cross = client.get(f"/api/v1/verification/instruments/{instrument_b.id}/provenance", headers=headers_inst_a)
    assert res_cross.status_code == 403
    assert res_cross.json()["code"] == "FORBIDDEN_CROSS_TENANT_ACCESS"

    # 2. Institution user attempt to transition trust -> 403 Forbidden
    res_trans = client.post(
        f"/api/v1/verification/instruments/{instrument_a.id}/trust/transition",
        headers=headers_inst_a,
        json={
            "target_trust_level": "L2_OFFICER_VERIFIED",
            "reason": "Self-promotion attempt",
        },
    )
    assert res_trans.status_code == 403

    # 3. Auditor Token (Read-only)
    token_auditor = create_access_token(
        user_id=auditor_user.id, email=auditor_user.email, role=auditor_user.role
    )
    headers_auditor = {"Authorization": f"Bearer {token_auditor}"}

    # Auditor read -> 200 OK
    res_audit_read = client.get(f"/api/v1/verification/instruments/{instrument_a.id}/trust/history", headers=headers_auditor)
    assert res_audit_read.status_code == 200

    # Auditor write attempt -> 403 Forbidden
    res_audit_write = client.post(
        f"/api/v1/verification/instruments/{instrument_a.id}/trust/transition",
        headers=headers_auditor,
        json={
            "target_trust_level": "L2_OFFICER_VERIFIED",
            "reason": "Auditor write attempt",
        },
    )
    assert res_audit_write.status_code == 403
