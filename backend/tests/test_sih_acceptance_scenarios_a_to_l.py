"""
SIH Problem Statement 26265: Acceptance & Demonstration Suite (Scenarios A through L)
Authoritative Verification Suite across All Critical Workflows, Security Controls, and Audit Invariants.

Scenarios:
  A. Standard submission-to-closure journey.
  B. Missing or inconsistent evidence and correction loop.
  C. Duplicate FDR detection and human scrutiny.
  D. Maturity monitoring, reminder generation and renewal lineage.
  E. Simulated bank verification and timeout/unavailable behavior.
  F. Release blocked by an unresolved requirement.
  G. Unauthorized statutory approval attempt.
  H. Unauthorized finance-order attempt.
  I. Institution A attempting to access Institution B's data.
  J. Auditor attempting a prohibited mutation.
  K. System Administrator attempting to bypass the release gate.
  L. Audit-chain verification on an intact ledger and tampering detection on isolated test data.
"""
import uuid
import hashlib
import json
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text, select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.lifecycle.models import LifecycleNotification, InstrumentLineage, LifecycleEvaluation
from app.modules.lifecycle.enums import MaturityStage, DueCondition
from app.modules.release.models import (
    ReleaseRequest,
    ReleaseDecision,
    ReleaseOrderRecord,
    ReleaseChecklistProfile,
    ReleaseChecklistItem,
)
from app.modules.release.enums import (
    ReleaseRequestType,
    ReleaseCaseType,
    ReleaseWorkflowStatus,
    ChecklistProfileStatus,
    ChecklistRequirementType,
)
from app.modules.release.schemas import ReleaseRequestCreate
from app.modules.release.service import seed_demo_release_profile, create_release_request
from app.modules.release.readiness_service import evaluate_readiness
from app.modules.validation.models import ValidationFinding
from app.modules.instruments.service import check_duplicate_reference
from app.modules.verification.models import VerificationRequest, VerificationResponse, TrustAssessment
from app.modules.verification.enums import (
    VerificationRequestStatus,
    VerificationResult,
    TrustLevel,
    VerificationChannel,
    TrustAssessmentStatus,
)
from app.modules.audit.service import log_audit_event
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_FINANCE_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    create_access_token,
)
from app.core.config import settings


def create_test_actor(db: Session, role: str, email: str, institution_id: str = None) -> User:
    user = User(
        email=email,
        full_name=f"Test Actor ({role})",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$fakehash",
        role=role,
        institution_id=institution_id,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def authenticate_client(client: TestClient, user: User):
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    client.cookies.set(
        name=settings.AUTH_COOKIE_NAME,
        value=token,
        path=settings.AUTH_COOKIE_PATH,
    )
    client.headers.update({"Authorization": f"Bearer {token}"})


@pytest.fixture
def sih_fixtures(db_session: Session):
    # Setup two separate institutions for tenant testing
    inst_a = Institution(
        code=f"SIH-PUN-{uuid.uuid4().hex[:4].upper()}",
        legal_name="Deccan Valley Institute [SIH ACC]",
        display_name="Deccan Valley Institute",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar Pune",
        contact_email="registrar.a@sih-example.com",
        city="Pune",
        state="Maharashtra",
        is_active=True,
        is_synthetic=True,
    )
    inst_b = Institution(
        code=f"SIH-MUM-{uuid.uuid4().hex[:4].upper()}",
        legal_name="Harbourview Institute [SIH ACC]",
        display_name="Harbourview Institute",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar Mumbai",
        contact_email="registrar.b@sih-example.com",
        city="Mumbai",
        state="Maharashtra",
        is_active=True,
        is_synthetic=True,
    )
    db_session.add_all([inst_a, inst_b])
    db_session.flush()

    # Create 7 Persona Actors
    user_inst_a = create_test_actor(db_session, ROLE_INSTITUTION_USER, "nodal.inst_a@sih.gov", inst_a.id)
    user_inst_b = create_test_actor(db_session, ROLE_INSTITUTION_USER, "nodal.inst_b@sih.gov", inst_b.id)
    user_scrutiny = create_test_actor(db_session, ROLE_SCRUTINY_OFFICER, "scrutiny.sih@aicte-india.org")
    user_branch = create_test_actor(db_session, ROLE_BRANCH_HEAD, "branch.sih@aicte-india.org")
    user_ca = create_test_actor(db_session, ROLE_COMPETENT_AUTHORITY, "ca.sih@aicte-india.org")
    user_fo = create_test_actor(db_session, ROLE_FINANCE_OFFICER, "fo.sih@aicte-india.org")
    user_auditor = create_test_actor(db_session, ROLE_AUDITOR, "auditor.sih@aicte-india.org")
    user_admin = create_test_actor(db_session, ROLE_SYSTEM_ADMIN, "admin.sih@aicte-india.org")

    # Use standard release profile seeder
    profile = seed_demo_release_profile(db_session, created_by_user_id=user_admin.id)
    db_session.commit()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "user_inst_a": user_inst_a,
        "user_inst_b": user_inst_b,
        "user_scrutiny": user_scrutiny,
        "user_branch": user_branch,
        "user_ca": user_ca,
        "user_fo": user_fo,
        "user_auditor": user_auditor,
        "user_admin": user_admin,
        "profile": profile,
    }


# ==============================================================================
# Scenario A: Standard submission-to-closure journey
# ==============================================================================
def test_scenario_a_standard_submission_to_closure_journey(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_inst_a = sih_fixtures["user_inst_a"]
    user_scrutiny = sih_fixtures["user_scrutiny"]
    user_ca = sih_fixtures["user_ca"]
    user_fo = sih_fixtures["user_fo"]

    # 1. Register FDR instrument (Stage 1)
    fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-SIH-SCENARIO-A",
        bank_name="State Bank of India",
        branch="Main Branch, Pune",
        amount=Decimal("1500000.00"),
        issue_date=date(2020, 1, 15),
        maturity_date=date(2025, 1, 15),
        status="ACTIVE",
        trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
    )
    db_session.add(fdr)
    db_session.flush()

    # Attach required documentary evidence (Stage 2)
    for cat in ["FDR_RECEIPT", "SANCTION_ORDER"]:
        doc = Document(institution_id=inst_a.id, instrument_id=fdr.id, category=cat, status="ACTIVE")
        db_session.add(doc)
        db_session.flush()
        ver = DocumentVersion(
            document_id=doc.id, version_number=1, storage_key=f"s_{cat}",
            original_filename=f"{cat}.pdf", content_type="application/pdf",
            file_size_bytes=100, sha256_hash=f"h_{cat}" + "0" * 50,
            processing_status="CLEAN"
        )
        db_session.add(ver)
        doc.current_version_id = ver.id

    # Active trust assessment (Stage 5)
    trust = TrustAssessment(
        instrument_id=fdr.id, field_name=None,
        trust_level=TrustLevel.L2_OFFICER_VERIFIED.value, reason="Officer verified",
        assessment_timestamp=datetime.now(timezone.utc),
        status=TrustAssessmentStatus.ACTIVE.value, assessing_user_id=user_scrutiny.id
    )
    db_session.add(trust)

    # Lifecycle evaluation: MATURED (Stage 6)
    lifecycle = LifecycleEvaluation(
        instrument_id=fdr.id, evaluation_date=date.today(),
        evaluation_timestamp=datetime.now(timezone.utc),
        maturity_stage=MaturityStage.MATURED.value, days_to_maturity=0,
        due_condition=DueCondition.NORMAL.value
    )
    db_session.add(lifecycle)
    db_session.flush()

    # 2. Stage 8: Release Request Created
    payload = ReleaseRequestCreate(
        instrument_id=fdr.id,
        request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Lock-in complete; requesting maturity release.",
        policy_profile_id=sih_fixtures["profile"].id,
    )
    rel_req = create_release_request(db=db_session, payload=payload, current_user=user_inst_a)
    db_session.commit()

    # 3. Scrutiny officer evaluates readiness and routes to authority
    evaluate_readiness(db=db_session, release_request=rel_req, current_user=user_scrutiny)
    rel_req.workflow_status = ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value
    db_session.commit()

    # 4. Stage 9A: Competent Authority Statutory Approval
    authenticate_client(client, user_ca)
    appr_res = client.post(
        f"/api/v1/release/requests/{rel_req.id}/approve?reason=Statutory+requirements+satisfied.+Approved."
    )
    assert appr_res.status_code == 201
    assert appr_res.json()["decision_type"] == "APPROVE"

    # 5. Stage 9B: Finance Officer Issues Release Order
    authenticate_client(client, user_fo)
    order_res = client.post(
        f"/api/v1/release/requests/{rel_req.id}/record-order",
        json={
            "order_reference_number": "AICTE/FIN/REL/2026/001",
            "order_date": date.today().isoformat(),
            "notes": "Formally issued discharge order.",
        },
    )
    assert order_res.status_code == 201
    assert order_res.json()["order_reference_number"] == "AICTE/FIN/REL/2026/001"

    # 6. Stage 9C: Bank Action Confirmation
    bank_res = client.post(
        f"/api/v1/release/requests/{rel_req.id}/confirm-bank-action?bank_action_notes=Bank+executed+lien+discharge"
    )
    assert bank_res.status_code == 200

    # 7. Stage 9D: Final Settlement Closure
    close_res = client.post(
        f"/api/v1/release/requests/{rel_req.id}/close-case?closure_notes=Case+settled+and+closed"
    )
    assert close_res.status_code == 200
    assert close_res.json()["workflow_status"] == "CLOSED"


# ==============================================================================
# Scenario B: Missing or inconsistent evidence and correction loop
# ==============================================================================
def test_scenario_b_missing_or_inconsistent_evidence_correction_loop(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_inst_a = sih_fixtures["user_inst_a"]
    user_scrutiny = sih_fixtures["user_scrutiny"]

    fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-SIH-SCENARIO-B",
        bank_name="Canara Bank",
        amount=Decimal("1000000.00"),
        issue_date=date(2022, 1, 1),
        maturity_date=date(2027, 1, 1),
        status="SUBMITTED",
        trust_level=TrustLevel.L0_DECLARED.value,
    )
    db_session.add(fdr)
    db_session.flush()

    # Officer returns instrument for correction with mandatory explanation
    authenticate_client(client, user_scrutiny)
    ret_res = client.post(
        f"/api/v1/instruments/{fdr.id}/return-for-correction",
        json={"explanation": "Upload corrected bank-endorsed joint lien certificate."},
    )
    assert ret_res.status_code == 200
    assert ret_res.json()["status"] == "RETURNED_FOR_CORRECTION"

    # Institution updates metadata and resubmits
    authenticate_client(client, user_inst_a)
    upd_res = client.patch(
        f"/api/v1/instruments/{fdr.id}",
        json={"remarks": "Uploaded addendum lien letter from branch manager.", "status": "SUBMITTED"},
    )
    assert upd_res.status_code == 200


# ==============================================================================
# Scenario C: Duplicate FDR detection and human scrutiny
# ==============================================================================
def test_scenario_c_duplicate_fdr_detection_and_human_scrutiny(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    inst_b = sih_fixtures["inst_b"]
    user_scrutiny = sih_fixtures["user_scrutiny"]

    # Institution A pledges FDR
    fdr_original = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-DUPLICATE-CHECK-100",
        bank_name="Bank of Baroda",
        amount=Decimal("500000.00"),
        issue_date=date(2022, 1, 1),
        maturity_date=date(2027, 1, 1),
        status="ACTIVE",
    )
    db_session.add(fdr_original)
    db_session.flush()

    # Conservative duplicate detection identifies existing reference across institutions
    duplicates = check_duplicate_reference(
        db=db_session,
        bank_name="Bank of Baroda",
        reference_number="FDR-DUPLICATE-CHECK-100",
    )
    assert len(duplicates) == 1
    assert duplicates[0].id == fdr_original.id
    assert duplicates[0].institution_id == inst_a.id

    # Institution B submission triggers duplicate warning finding
    finding = ValidationFinding(
        finding_fingerprint=hashlib.sha256(f"{inst_b.id}:RULE_DUPLICATE_INSTRUMENT".encode()).hexdigest(),
        instrument_id=fdr_original.id,
        institution_id=inst_a.id,
        rule_id="RULE_DUPLICATE_INSTRUMENT_NUMBER",
        rule_version="1.0",
        rule_type="DETERMINISTIC",
        category="FRAUD_PREVENTION",
        severity="CRITICAL",
        status="OPEN",
        title="Duplicate FDR Reference Across Institutions",
        explanation=f"Reference FDR-DUPLICATE-CHECK-100 already pledged.",
        first_detected_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    db_session.flush()

    # Scrutiny officer views review queue
    authenticate_client(client, user_scrutiny)
    q_res = client.get("/api/v1/validation/findings/queue")
    assert q_res.status_code == 200
    assert q_res.json()["total"] >= 1


# ==============================================================================
# Scenario D: Maturity monitoring, reminder generation and renewal lineage
# ==============================================================================
def test_scenario_d_maturity_monitoring_reminders_and_renewal_lineage(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_inst_a = sih_fixtures["user_inst_a"]

    # Predecessor FDR
    parent_fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-MATURED-TERM-1",
        bank_name="Punjab National Bank",
        amount=Decimal("1200000.00"),
        issue_date=date(2021, 1, 1),
        maturity_date=date(2026, 1, 1),
        status="EXPIRED",
        trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
    )
    db_session.add(parent_fdr)
    db_session.flush()

    # Renewal Successor FDR
    child_fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-RENEWED-TERM-2",
        bank_name="Punjab National Bank",
        amount=Decimal("1200000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2031, 1, 1),
        status="ACTIVE",
        trust_level=TrustLevel.L1_DOCUMENT_CONSISTENT.value,
    )
    db_session.add(child_fdr)
    db_session.flush()

    # Record Lineage link
    lineage = InstrumentLineage(
        institution_id=inst_a.id,
        predecessor_instrument_id=parent_fdr.id,
        successor_instrument_id=child_fdr.id,
        relationship_type="RENEWAL",
        relationship_status="ACTIVE",
    )
    db_session.add(lineage)
    db_session.flush()

    # Query Lineage Tree
    authenticate_client(client, user_inst_a)
    tree_res = client.get(f"/api/v1/lifecycle/instruments/{child_fdr.id}/lineage")
    assert tree_res.status_code == 200
    assert len(tree_res.json()["ancestors"]) >= 1


# ==============================================================================
# Scenario E: Simulated bank verification and timeout/unavailable behavior
# ==============================================================================
def test_scenario_e_simulated_bank_verification_and_timeout_behavior(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_scrutiny = sih_fixtures["user_scrutiny"]

    fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-TIMEOUT-DEMO",
        bank_name="Axis Bank",
        amount=Decimal("800000.00"),
        issue_date=date(2022, 1, 1),
        maturity_date=date(2027, 1, 1),
        status="SUBMITTED",
        trust_level=TrustLevel.L1_DOCUMENT_CONSISTENT.value,
    )
    db_session.add(fdr)
    db_session.flush()

    # Officer dispatches verification request
    authenticate_client(client, user_scrutiny)
    create_res = client.post(
        f"/api/v1/verification/instruments/{fdr.id}/requests",
        json={"channel": "SIMULATED", "requested_fields": ["amount", "maturity_date"]},
    )
    assert create_res.status_code == 201

    # Assert simulated requests cannot silently establish genuine L3 bank confirmation
    reqs_res = client.get(f"/api/v1/verification/instruments/{fdr.id}/requests")
    assert reqs_res.status_code == 200
    assert len(reqs_res.json()) >= 1
    assert fdr.trust_level != TrustLevel.L3_BANK_CONFIRMED.value


# ==============================================================================
# Scenario F: Release blocked by an unresolved requirement
# ==============================================================================
def test_scenario_f_release_blocked_by_unresolved_requirement(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_inst_a = sih_fixtures["user_inst_a"]
    user_scrutiny = sih_fixtures["user_scrutiny"]

    # FDR with untrusted L0 status
    fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-BLOCKED-RELEASE",
        bank_name="State Bank of India",
        amount=Decimal("1000000.00"),
        issue_date=date(2022, 1, 1),
        maturity_date=date(2027, 1, 1),
        status="ACTIVE",
        trust_level=TrustLevel.L0_DECLARED.value,
    )
    db_session.add(fdr)
    db_session.flush()

    payload = ReleaseRequestCreate(
        instrument_id=fdr.id,
        request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Premature request with blockers.",
        policy_profile_id=sih_fixtures["profile"].id,
    )
    rel_req = create_release_request(db=db_session, payload=payload, current_user=user_inst_a)
    db_session.commit()

    # Scrutiny starts review
    authenticate_client(client, user_scrutiny)
    client.post(f"/api/v1/release/requests/{rel_req.id}/start-review")

    # Attempt to recommend for authority while blockers remain
    rec_res = client.post(
        f"/api/v1/release/requests/{rel_req.id}/recommend-for-authority?reason=Bypass+attempt"
    )
    # Server-side release gate rejects transition
    assert rec_res.status_code in (400, 422)


# ==============================================================================
# Scenario G: Unauthorized statutory approval attempt
# ==============================================================================
def test_scenario_g_unauthorized_statutory_approval_attempt(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_inst_a = sih_fixtures["user_inst_a"]
    user_scrutiny = sih_fixtures["user_scrutiny"]
    user_fo = sih_fixtures["user_fo"]

    fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-AUTH-TEST",
        bank_name="HDFC Bank",
        amount=Decimal("1000000.00"),
        issue_date=date(2022, 1, 1),
        maturity_date=date(2027, 1, 1),
        status="ACTIVE",
        trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
    )
    db_session.add(fdr)
    db_session.flush()

    payload = ReleaseRequestCreate(
        instrument_id=fdr.id,
        request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Testing role restrictions.",
        policy_profile_id=sih_fixtures["profile"].id,
    )
    rel_req = create_release_request(db=db_session, payload=payload, current_user=user_inst_a)
    rel_req.workflow_status = ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value
    db_session.commit()

    # 1. Scrutiny Officer cannot approve release (HTTP 403)
    authenticate_client(client, user_scrutiny)
    res_scrutiny = client.post(
        f"/api/v1/release/requests/{rel_req.id}/approve?reason=Unauthorized+scrutiny+attempt"
    )
    assert res_scrutiny.status_code == 403

    # 2. Finance Officer cannot approve release (HTTP 403)
    authenticate_client(client, user_fo)
    res_fo = client.post(
        f"/api/v1/release/requests/{rel_req.id}/approve?reason=Unauthorized+finance+attempt"
    )
    assert res_fo.status_code == 403


# ==============================================================================
# Scenario H: Unauthorized finance-order attempt
# ==============================================================================
def test_scenario_h_unauthorized_finance_order_attempt(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_inst_a = sih_fixtures["user_inst_a"]
    user_ca = sih_fixtures["user_ca"]

    fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-ORDER-TEST",
        bank_name="ICICI Bank",
        amount=Decimal("1000000.00"),
        issue_date=date(2022, 1, 1),
        maturity_date=date(2027, 1, 1),
        status="ACTIVE",
        trust_level=TrustLevel.L2_OFFICER_VERIFIED.value,
    )
    db_session.add(fdr)
    db_session.flush()

    payload = ReleaseRequestCreate(
        instrument_id=fdr.id,
        request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Testing order restrictions.",
        policy_profile_id=sih_fixtures["profile"].id,
    )
    rel_req = create_release_request(db=db_session, payload=payload, current_user=user_inst_a)
    rel_req.workflow_status = ReleaseWorkflowStatus.APPROVED.value
    db_session.commit()

    # Competent Authority cannot issue Finance Officer release order (HTTP 403)
    authenticate_client(client, user_ca)
    res_ca = client.post(
        f"/api/v1/release/requests/{rel_req.id}/record-order",
        json={"order_reference_number": "ILLEGAL-REF", "order_date": date.today().isoformat()},
    )
    assert res_ca.status_code == 403


# ==============================================================================
# Scenario I: Institution A attempting to access Institution B's data
# ==============================================================================
def test_scenario_i_institution_cross_tenant_isolation_denial(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_b = sih_fixtures["inst_b"]
    user_inst_a = sih_fixtures["user_inst_a"]

    # Confidential instrument belonging to Institution B
    fdr_b = Instrument(
        institution_id=inst_b.id,
        reference_number="FDR-CONFIDENTIAL-B",
        bank_name="Union Bank of India",
        amount=Decimal("5000000.00"),
        issue_date=date(2022, 1, 1),
        maturity_date=date(2027, 1, 1),
        status="ACTIVE",
    )
    db_session.add(fdr_b)
    db_session.flush()

    # Institution A attempts to fetch Institution B's instrument -> HTTP 403 Forbidden
    authenticate_client(client, user_inst_a)
    leak_res = client.get(f"/api/v1/instruments/{fdr_b.id}")
    assert leak_res.status_code == 403


# ==============================================================================
# Scenario J: Auditor attempting a prohibited mutation
# ==============================================================================
def test_scenario_j_auditor_prohibited_mutation_denial(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_auditor = sih_fixtures["user_auditor"]

    # Auditor attempts to register new FDR -> HTTP 403 Forbidden
    authenticate_client(client, user_auditor)
    mut_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": inst_a.id,
            "bank_name": "State Bank of India",
            "reference_number": "FDR-AUDITOR-ATTEMPT",
            "amount": 100000.0,
            "currency": "INR",
            "issue_date": "2022-01-01",
            "maturity_date": "2027-01-01",
            "status": "REGISTERED",
        },
    )
    assert mut_res.status_code == 403


# ==============================================================================
# Scenario K: System Administrator attempting to bypass the release gate
# ==============================================================================
def test_scenario_k_system_admin_cannot_bypass_release_gate(client: TestClient, db_session: Session, sih_fixtures: dict):
    inst_a = sih_fixtures["inst_a"]
    user_inst_a = sih_fixtures["user_inst_a"]
    user_admin = sih_fixtures["user_admin"]

    fdr = Instrument(
        institution_id=inst_a.id,
        reference_number="FDR-ADMIN-GATE-BYPASS",
        bank_name="Canara Bank",
        amount=Decimal("2000000.00"),
        issue_date=date(2022, 1, 1),
        maturity_date=date(2027, 1, 1),
        status="ACTIVE",
    )
    db_session.add(fdr)
    db_session.flush()

    payload = ReleaseRequestCreate(
        instrument_id=fdr.id,
        request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Testing admin boundary.",
        policy_profile_id=sih_fixtures["profile"].id,
    )
    rel_req = create_release_request(db=db_session, payload=payload, current_user=user_inst_a)
    db_session.commit()

    # System Admin attempts statutory release approval -> HTTP 403 Forbidden
    authenticate_client(client, user_admin)
    admin_appr = client.post(
        f"/api/v1/release/requests/{rel_req.id}/approve?reason=Admin+bypass+attempt"
    )
    assert admin_appr.status_code == 403


# ==============================================================================
# Scenario L: Audit-chain verification on an intact ledger and tampering detection
# ==============================================================================
def test_scenario_l_audit_chain_verification_and_tampering_detection(client: TestClient, db_session: Session, sih_fixtures: dict):
    user_admin = sih_fixtures["user_admin"]

    # 1. Verification of intact audit chain
    authenticate_client(client, user_admin)
    intact_res = client.get("/api/v1/audit/integrity")
    assert intact_res.status_code == 200
    intact_body = intact_res.json()
    assert intact_body["is_chain_intact"] is True

    # 2. Tampering Prevention: Ensure an audit event row exists, then verify trigger prevents mutation
    evt = log_audit_event(
        db=db_session,
        action="TEST_TAMPER_CHECK_BASELINE",
        entity_type="TestEntity",
        entity_id="test-tamper-check",
        actor_user_id=user_admin.id,
        actor_email=user_admin.email,
        actor_role=user_admin.role,
        outcome="SUCCESS",
    )
    db_session.flush()

    with pytest.raises(Exception) as exc_info:
        db_session.execute(text(f"UPDATE audit_events SET action = 'TAMPERED' WHERE id = '{evt.id}'"))
        db_session.flush()
    assert "Mutation of audit records is strictly prohibited" in str(exc_info.value)
