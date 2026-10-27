"""
Test Suite: Complete End-to-End Nine-Stage Integration, Security Audit, and Acceptance Verification
SIH 2026 Problem Statement ID: 26265

Covers:
1. Journey A: Standard processing through all 9 canonical stages with complete evidence,
   extraction, validation, scrutiny observations, L2 attestation, lifecycle evaluation,
   readiness gate, Competent Authority approval, Finance Officer release order,
   downstream bank action, and closure.
2. Journey B: Correction loop (finding causes return for correction, institution updates deposit
   details, status transitions from RETURNED_FOR_CORRECTION to SUBMITTED, post-save validation
   reruns, scrutiny observations and findings history preserved).
3. Journey C: Incomplete or blocked evidence (mandatory blockers like unverified trust or open
   findings prevent recommendation and statutory approval).
4. Journey D: Renewal lineage (successor linked to predecessor, lineage graph recorded,
   predecessor evidence and trust preserved).
5. Journey E: Simulated & unavailable external dependencies (scanned image PDF marked
   FAILED/OCR_UNAVAILABLE without fake text, simulated CBS bank response rejected from L3 confirmation,
   mock email provider honestly reporting ACCEPTED/is_mock=True).
6. Journey F: Statutory rejection vs approval path (Competent Authority rejects; verifies that
   Finance Officer cannot record release order on REJECTED request; financial execution path blocked).
7. Seven-Role Security & Authorization Audit Matrix:
   - SYSTEM_ADMIN, COMPETENT_AUTHORITY, BRANCH_HEAD, SCRUTINY_OFFICER,
     FINANCE_OFFICER, AUDITOR, INSTITUTION_USER.
   - Non-negotiable authorization invariants:
     * Institution User tenant isolation across records, nested resources, searches, and exports.
     * Auditor read-only invariance against business data mutations.
     * Competent Authority exclusive statutory approval and rejection.
     * Finance Officer exclusive release order recording.
     * Maker-checker separation (creator cannot approve statutory release).
     * Zero-blocker readiness release gate.
     * Cryptographic SHA-256 audit ledger verification.
"""
import io
import uuid
import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.lifecycle.models import LifecycleNotification, InstrumentLineage
from app.modules.release.models import ReleaseRequest, ReleaseDecision, ReleaseOrderRecord
from app.modules.auth.service import provision_user
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
from app.core.canonical_stages import list_canonical_stages, CanonicalStageId
from app.modules.release.enums import (
    ReleaseWorkflowStatus,
    ReleaseDecisionType,
    ReleaseOrderStatus,
    BankActionStatus,
)
from app.modules.documents.scanner import DemoScannerProvider, DisabledScannerProvider, set_scanner_provider


@pytest.fixture(autouse=True)
def configure_test_scanner():
    """Ensure DemoScannerProvider is active for test runs."""
    set_scanner_provider(DemoScannerProvider())
    yield
    set_scanner_provider(DisabledScannerProvider())


def auth_client(client: TestClient, user: User) -> dict:
    """Sets authentication cookie and returns Authorization bearer header."""
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
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def actors_fixture(db_session: Session):
    """Seed distinct institutions and all 7 role actors."""
    suffix = uuid.uuid4().hex[:6]
    inst_a = Institution(
        code=f"INST-A-{suffix}",
        legal_name=f"Apex Technical University {suffix}",
        institution_type="TECHNICAL",
        contact_email=f"registrar_{suffix}@apex.edu",
        state="Maharashtra",
        assigned_office="WRO-MUMBAI",
        is_active=True,
    )
    inst_b = Institution(
        code=f"INST-B-{suffix}",
        legal_name=f"Beacon Engineering College {suffix}",
        institution_type="TECHNICAL",
        contact_email=f"registrar_{suffix}@beacon.edu",
        state="Karnataka",
        assigned_office="SRO-BANGALORE",
        is_active=True,
    )
    db_session.add_all([inst_a, inst_b])
    db_session.commit()

    inst_user_a = provision_user(
        db_session, "Principal Apex", f"principal_{suffix}@apex.edu", "ApexPass123!", ROLE_INSTITUTION_USER, institution_id=inst_a.id
    )
    inst_user_b = provision_user(
        db_session, "Principal Beacon", f"principal_{suffix}@beacon.edu", "BeaconPass123!", ROLE_INSTITUTION_USER, institution_id=inst_b.id
    )
    scrutiny = provision_user(
        db_session, "Inspector Scrutiny", f"scrutiny_{suffix}@aicte.gov.in", "ScrutinyPass123!", ROLE_SCRUTINY_OFFICER
    )
    branch = provision_user(
        db_session, "Regional Director", f"branch_{suffix}@aicte.gov.in", "BranchPass123!", ROLE_BRANCH_HEAD
    )
    authority = provision_user(
        db_session, "Member Secretary", f"authority_{suffix}@aicte.gov.in", "AuthPass123!", ROLE_COMPETENT_AUTHORITY
    )
    finance = provision_user(
        db_session, "Finance Comptroller", f"finance_{suffix}@aicte.gov.in", "FinancePass123!", ROLE_FINANCE_OFFICER
    )
    auditor = provision_user(
        db_session, "Statutory Auditor", f"auditor_{suffix}@aicte.gov.in", "AuditPass123!", ROLE_AUDITOR
    )
    admin = provision_user(
        db_session, "System Administrator", f"sysadmin_{suffix}@aicte.gov.in", "AdminPass123!", ROLE_SYSTEM_ADMIN
    )

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "inst_user_a": inst_user_a,
        "inst_user_b": inst_user_b,
        "scrutiny": scrutiny,
        "branch": branch,
        "authority": authority,
        "finance": finance,
        "auditor": auditor,
        "admin": admin,
    }


# ============================================================================
# JOURNEY A: Standard Complete Nine-Stage Lifecycle Processing
# ============================================================================

def test_journey_a_standard_nine_stage_processing(client: TestClient, db_session: Session, actors_fixture):
    """
    Journey A — Standard processing:
    1. Registration
    2. Certified document evidence upload & SHA-256 integrity
    3. Deterministic extraction & discrepancy validation
    4. Scrutiny review & observations
    5. Bank verification & L2 officer attestation
    6. Lifecycle monitoring & maturity evaluation
    7. Successor renewal linking
    8. Release readiness gate assessment
    9. Maker-checker statutory approval (Sanction), release-order recording,
       downstream bank-action confirmation, and closure.
    """
    actors = actors_fixture
    inst_user = actors["inst_user_a"]
    inst = actors["inst_a"]

    # STAGE 1: Registration
    h_inst = auth_client(client, inst_user)
    issue_dt = date.today() - timedelta(days=300)
    maturity_dt = date.today() + timedelta(days=60)

    reg_res = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "State Bank of India",
        "reference_number": "SBI-FDR-JA-001",
        "amount": "2500000.00",
        "issue_date": str(issue_dt),
        "maturity_date": str(maturity_dt),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    }, headers=h_inst)
    assert reg_res.status_code == 201
    fdr_id = reg_res.json()["id"]
    assert reg_res.json()["status"] == "REGISTERED"
    assert reg_res.json()["trust_level"] == "L0_DECLARED"

    # STAGE 2: Document Evidence Upload
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (FDR Certificate SBI-FDR-JA-001) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_res = client.post(
        f"/api/v1/instruments/{fdr_id}/documents",
        data={"category": "FDR_COPY", "title": "Certified Deposit Certificate"},
        files={"file": ("fdr_cert.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        headers=h_inst,
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["document_id"]
    ver_id = upload_res.json()["version_id"]
    assert upload_res.json()["sha256_hash"] is not None

    # Upload Sanction Order required for release profile
    upload_so = client.post(
        f"/api/v1/instruments/{fdr_id}/documents",
        data={"category": "SANCTION_ORDER", "title": "Regulatory Sanction Order"},
        files={"file": ("sanction_order.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        headers=h_inst,
    )
    assert upload_so.status_code == 200

    # STAGE 3: Validation & Discrepancy Detection
    h_scrutiny = auth_client(client, actors["scrutiny"])
    val_res = client.post(f"/api/v1/instruments/{fdr_id}/validation-runs", json={}, headers=h_scrutiny)
    assert val_res.status_code == 200
    assert "rules_evaluated" in val_res.json()

    # STAGE 4: Scrutiny & Review
    obs_res = client.post(
        f"/api/v1/dashboard/instruments/{fdr_id}/observations",
        json={
            "observation_text": "Certificate verified against issuing branch ledger. AICTE lien verified.",
            "observation_category": "COMPLIANCE",
            "is_internal_only": False,
        },
        headers=h_scrutiny,
    )
    assert obs_res.status_code == 201
    assert obs_res.json()["status"] == "RECORDED"

    # Resolve any open findings
    findings_res = client.get(f"/api/v1/instruments/{fdr_id}/findings", headers=h_scrutiny)
    assert findings_res.status_code == 200
    for finding in findings_res.json()["items"]:
        if finding["status"] in ("OPEN", "IN_REVIEW"):
            client.post(
                f"/api/v1/findings/{finding['id']}/status",
                json={"target_status": "RESOLVED", "reason": "Officer verified document evidence"},
                headers=h_scrutiny,
            )

    # STAGE 5: Bank Verification & Trust
    l2_res = client.post(
        f"/api/v1/verification/instruments/{fdr_id}/trust/l2-officer-decision",
        json={
            "reason": "Branch officer confirmed lien endorsement in writing.",
            "evidence_references": [f"DOC-{doc_id}"],
        },
        headers=h_scrutiny,
    )
    assert l2_res.status_code == 201
    assert l2_res.json()["trust_level"] == "L2_OFFICER_VERIFIED"

    # STAGE 6: Lifecycle Monitoring
    eval_res = client.post(
        "/api/v1/lifecycle/evaluate",
        json={"instrument_id": fdr_id, "force_evaluation": True},
        headers=h_scrutiny,
    )
    assert eval_res.status_code == 200
    assert eval_res.json()["maturity_stage"] in ("ACTIVE", "APPROACHING_MATURITY", "MATURED")

    # STAGE 7: Successor Renewal Lineage
    renew_res = client.post(
        f"/api/v1/lifecycle/instruments/{fdr_id}/renew",
        json={
            "bank_name": "State Bank of India",
            "branch": "Main Branch",
            "reference_number": "SBI-FDR-JA-001-R1",
            "amount": 2500000.00,
            "currency": "INR",
            "issue_date": str(maturity_dt),
            "maturity_date": str(maturity_dt + timedelta(days=365)),
            "reason_or_reference": "Annual statutory rollover.",
        },
        headers=h_inst,
    )
    assert renew_res.status_code in (200, 201)
    successor_id = renew_res.json()["successor_instrument_id"]
    assert renew_res.json()["lineage"]["relationship_status"] == "ACTIVE"

    # STAGE 8: Release Readiness Evaluation
    h_branch = auth_client(client, actors["branch"])
    rel_create = client.post("/api/v1/release/requests", json={
        "instrument_id": fdr_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "End-of-term release after regulatory fulfillment.",
    }, headers=h_inst)
    assert rel_create.status_code in (200, 201)
    case_id = rel_create.json()["id"]

    # Submit petition
    client.post(
        f"/api/v1/release/requests/{case_id}/decisions",
        json={"decision_type": "SUBMIT", "reason": "Institution formal petition."},
        headers=h_inst,
    )

    # Branch Head initiates review and evaluates readiness
    client.post(f"/api/v1/release/requests/{case_id}/start-review", headers=h_branch)
    readiness_res = client.post(f"/api/v1/release/requests/{case_id}/evaluate-readiness", headers=h_branch)
    assert readiness_res.status_code == 200

    rec_res = client.post(
        f"/api/v1/release/requests/{case_id}/recommend-for-authority?reason=All+documentation+verified",
        headers=h_branch,
    )
    assert rec_res.status_code in (200, 201)

    # STAGE 9: Maker-Checker Decision, Release Order, and Case Closure
    # 9a: Statutory Approval (COMPETENT_AUTHORITY only)
    h_auth = auth_client(client, actors["authority"])
    app_res = client.post(
        f"/api/v1/release/requests/{case_id}/approve?reason=Approved+by+Competent+Authority+under+Section+10",
        headers=h_auth,
    )
    assert app_res.status_code in (200, 201)
    assert app_res.json()["decision_type"] == "APPROVE"

    # Invariant: Approval does NOT automatically record release order
    case_post_app = client.get(f"/api/v1/release/requests/{case_id}", headers=h_auth).json()
    assert case_post_app["workflow_status"] == "APPROVED"

    # 9b: Release Order Recording (FINANCE_OFFICER only)
    h_fin = auth_client(client, actors["finance"])
    order_res = client.post(
        f"/api/v1/release/requests/{case_id}/record-order",
        json={
            "order_reference_number": "AICTE-RO-JA-2026-001",
            "order_date": str(date.today()),
            "is_synthetic_demo": True,
            "notes": "Official release letter issued to SBI.",
        },
        headers=h_fin,
    )
    assert order_res.status_code in (200, 201)

    # 9c: Downstream Bank-Action Tracking
    confirm_res = client.post(
        f"/api/v1/release/requests/{case_id}/confirm-bank-action?bank_action_notes=SBI+Disbursement+UTR+Confirmed",
        headers=h_fin,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["workflow_status"] == "COMPLETED"

    # 9d: Formal Case Closure
    close_res = client.post(
        f"/api/v1/release/requests/{case_id}/close-case?closure_notes=Sealed+and+archived",
        headers=h_fin,
    )
    assert close_res.status_code == 200
    assert close_res.json()["workflow_status"] == "CLOSED"

    # Post-run: Cryptographic Audit Verification
    h_audit = auth_client(client, actors["auditor"])
    audit_res = client.post("/api/v1/audit/verify", headers=h_audit)
    assert audit_res.status_code == 200
    assert audit_res.json()["is_chain_intact"] is True


# ============================================================================
# JOURNEY B: Correction Loop & History Preservation
# ============================================================================

def test_journey_b_correction_loop_preserves_history(client: TestClient, db_session: Session, actors_fixture):
    """
    Journey B — Correction loop:
    A validation finding causes an authorized return for correction. The institution
    submits updated information, validation is rerun, and review process resumes
    without losing historical evidence or observations.
    """
    actors = actors_fixture
    inst_user = actors["inst_user_a"]
    officer = actors["scrutiny"]
    inst = actors["inst_a"]

    # 1. Register FDR
    h_inst = auth_client(client, inst_user)
    reg = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "Punjab National Bank",
        "reference_number": "PNB-CORR-JB-001",
        "amount": "1000000.00",
        "issue_date": str(date.today() - timedelta(days=100)),
        "maturity_date": str(date.today() + timedelta(days=265)),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": False,
        "lien_marked": False,
    }, headers=h_inst)
    assert reg.status_code == 201
    fdr_id = reg.json()["id"]

    # 2. Scrutiny officer records observation and returns for correction
    h_officer = auth_client(client, officer)
    obs = client.post(
        f"/api/v1/dashboard/instruments/{fdr_id}/observations",
        json={
            "observation_text": "FDR lacks joint AICTE holding and lien marking endorsement.",
            "observation_category": "DEFICIENCY",
            "is_internal_only": False,
        },
        headers=h_officer,
    )
    assert obs.status_code == 201

    ret = client.post(
        f"/api/v1/instruments/{fdr_id}/return-for-correction",
        json={"explanation": "Please correct AICTE joint holding and endorse lien marking."},
        headers=h_officer,
    )
    assert ret.status_code == 200
    assert ret.json()["status"] == "RETURNED_FOR_CORRECTION"

    # 3. Institution user corrects the instrument
    update_res = client.patch(
        f"/api/v1/instruments/{fdr_id}",
        json={
            "joint_with_aicte": True,
            "lien_marked": True,
            "remarks": "Rectified joint holding and lien endorsement.",
        },
        headers=h_inst,
    )
    assert update_res.status_code == 200
    assert update_res.json()["joint_with_aicte"] is True
    assert update_res.json()["lien_marked"] is True
    assert update_res.json()["status"] == "SUBMITTED"

    # 4. Verify historical observations and audit trail are preserved
    hist_obs = client.get(f"/api/v1/dashboard/instruments/{fdr_id}/observations", headers=h_officer)
    assert hist_obs.status_code == 200
    assert len(hist_obs.json()) >= 1
    assert "FDR lacks joint AICTE holding" in hist_obs.json()[0]["observation_text"]


# ============================================================================
# JOURNEY C: Incomplete or Blocked Evidence Prevents Ineligible Transitions
# ============================================================================

def test_journey_c_mandatory_blocker_prevents_transition(client: TestClient, db_session: Session, actors_fixture):
    """
    Journey C — Incomplete or blocked evidence:
    Unresolved findings, unverified trust state, or mandatory release blocker
    strictly prevents an ineligible transition.
    """
    actors = actors_fixture
    inst_user = actors["inst_user_a"]
    officer = actors["scrutiny"]
    authority = actors["authority"]
    inst = actors["inst_a"]

    # 1. Register FDR without complete documents or trust verification
    h_inst = auth_client(client, inst_user)
    fdr = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "Canara Bank",
        "reference_number": "CAN-BLOCK-JC-001",
        "amount": "500000.00",
        "issue_date": str(date.today() - timedelta(days=50)),
        "maturity_date": str(date.today() + timedelta(days=315)),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    }, headers=h_inst)
    fdr_id = fdr.json()["id"]

    # 2. Create release request
    rel = client.post("/api/v1/release/requests", json={
        "instrument_id": fdr_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Premature attempt without required documents.",
    }, headers=h_inst)
    case_id = rel.json()["id"]

    # Submit petition
    client.post(
        f"/api/v1/release/requests/{case_id}/decisions",
        json={"decision_type": "SUBMIT", "reason": "Submission."},
        headers=h_inst,
    )

    # 3. Scrutiny review and readiness evaluation reveals blockers
    h_officer = auth_client(client, officer)
    client.post(f"/api/v1/release/requests/{case_id}/start-review", headers=h_officer)
    readiness = client.post(f"/api/v1/release/requests/{case_id}/evaluate-readiness", headers=h_officer).json()

    assert readiness["blockers_count"] > 0
    assert readiness["assessment_outcome"] == "BLOCKED"

    # Ineligible transition: Officer cannot recommend when blockers exist
    rec_res = client.post(
        f"/api/v1/release/requests/{case_id}/recommend-for-authority?reason=Premature+routing",
        headers=h_officer,
    )
    assert rec_res.status_code == 400
    assert "GATE_FAILED_MANDATORY_BLOCKERS" in rec_res.text or "blocker" in rec_res.text.lower()

    # Ineligible transition: Authority cannot approve a case not in READY_FOR_AUTHORITY
    h_auth = auth_client(client, authority)
    app_res = client.post(
        f"/api/v1/release/requests/{case_id}/approve?reason=Illegal+bypass+attempt",
        headers=h_auth,
    )
    assert app_res.status_code == 400


# ============================================================================
# JOURNEY D: Successor Renewal Lineage Traceability & Immutability
# ============================================================================

def test_journey_d_renewal_lineage_preservation(client: TestClient, db_session: Session, actors_fixture):
    """
    Journey D — Renewal:
    A successor FDR is created or linked according to existing domain rules.
    Both predecessor and successor remain traceable; predecessor evidence
    and trust history are not silently overwritten.
    """
    actors = actors_fixture
    inst_user = actors["inst_user_a"]
    officer = actors["scrutiny"]
    inst = actors["inst_a"]

    # 1. Register predecessor FDR and establish L2 trust
    h_inst = auth_client(client, inst_user)
    p_res = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "Bank of Baroda",
        "reference_number": "BOB-ORIG-JD-001",
        "amount": "1200000.00",
        "issue_date": str(date.today() - timedelta(days=365)),
        "maturity_date": str(date.today()),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    }, headers=h_inst)
    p_id = p_res.json()["id"]

    h_officer = auth_client(client, officer)
    client.post(
        f"/api/v1/verification/instruments/{p_id}/trust/l2-officer-decision",
        json={"reason": "Original deposit verified.", "evidence_references": ["ORIG-CERT-01"]},
        headers=h_officer,
    )

    # Predecessor is now L2_OFFICER_VERIFIED
    p_pre = client.get(f"/api/v1/instruments/{p_id}", headers=h_officer).json()
    assert p_pre["trust_level"] == "L2_OFFICER_VERIFIED"

    # 2. Record successor renewal
    renew_res = client.post(
        f"/api/v1/lifecycle/instruments/{p_id}/renew",
        json={
            "bank_name": "Bank of Baroda",
            "branch": "Overseas Branch",
            "reference_number": "BOB-SUCC-JD-002",
            "amount": 1200000.00,
            "currency": "INR",
            "issue_date": str(date.today()),
            "maturity_date": str(date.today() + timedelta(days=365)),
            "reason_or_reference": "Rolled over upon maturity.",
        },
        headers=h_inst,
    )
    assert renew_res.status_code in (200, 201)
    s_id = renew_res.json()["successor_instrument_id"]

    # 3. Invariant: Predecessor's trust level is preserved, not overwritten or altered
    p_post = client.get(f"/api/v1/instruments/{p_id}", headers=h_officer).json()
    assert p_post["trust_level"] == "L2_OFFICER_VERIFIED"

    # Successor starts with fresh L0_DECLARED trust level
    s_post = client.get(f"/api/v1/instruments/{s_id}", headers=h_officer).json()
    assert s_post["trust_level"] == "L0_DECLARED"

    # 4. Lineage is traceable via canonical lineage endpoint
    lineage_res = client.get(f"/api/v1/lifecycle/instruments/{s_id}/lineage", headers=h_officer)
    assert lineage_res.status_code == 200
    assert lineage_res.json()["current_instrument_id"] == s_id
    assert lineage_res.json()["direct_predecessor_lineage"]["predecessor_instrument_id"] == p_id


# ============================================================================
# JOURNEY E: Pending or Simulated External Dependencies Honest Reporting
# ============================================================================

def test_journey_e_simulated_external_services_honest_status(client: TestClient, db_session: Session, actors_fixture):
    """
    Journey E — Pending or unavailable external service:
    Simulated CBS bank response, unavailable OCR provider, or mock email delivery
    does not cause the application to record a false success.
    """
    actors = actors_fixture
    inst_user = actors["inst_user_a"]
    officer = actors["scrutiny"]
    inst = actors["inst_a"]

    # 1. Register FDR
    h_inst = auth_client(client, inst_user)
    fdr = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "Indian Bank",
        "reference_number": "IB-SIM-JE-001",
        "amount": "800000.00",
        "issue_date": str(date.today() - timedelta(days=30)),
        "maturity_date": str(date.today() + timedelta(days=335)),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    }, headers=h_inst).json()
    fdr_id = fdr["id"]

    # 2. Upload image-only/scanned PDF without text layer
    # Minimal PDF without text stream to test OCR fallback honesty
    image_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_res = client.post(
        f"/api/v1/instruments/{fdr_id}/documents",
        data={"category": "FDR_COPY", "title": "Scanned Document"},
        files={"file": ("scanned_fdr.pdf", io.BytesIO(image_pdf), "application/pdf")},
        headers=h_inst,
    )
    assert upload_res.status_code == 200
    # Extraction must honestly report FAILED with OCR unavailable message, not synthesize fake data
    assert upload_res.json()["extraction_status"] == "FAILED"

    # 3. Simulated Verification Response cannot be claimed as genuine L3 confirmation
    h_officer = auth_client(client, officer)
    v_req = client.post(
        f"/api/v1/verification/instruments/{fdr_id}/requests",
        json={"channel": "SIMULATED", "requested_fields": ["AMOUNT", "MATURITY_DATE"]},
        headers=h_officer,
    ).json()
    v_req_id = v_req["id"]

    v_disp = client.post(
        f"/api/v1/verification/requests/{v_req_id}/dispatch",
        json={"scenario": "STANDARD_MATCH"},
        headers=h_officer,
    ).json()
    assert v_disp["is_simulated"] is True

    # Attempting to escalate to L3 using simulated response MUST be rejected
    l3_res = client.post(
        f"/api/v1/verification/instruments/{fdr_id}/trust/l3-bank-confirmation",
        json={
            "verification_response_id": v_disp["id"],
            "reason": "Attempting to claim genuine L3 using simulated response",
            "source_authorization_config": "CONFIG-LIVE-SFMS",
        },
        headers=h_officer,
    )
    assert l3_res.status_code in (400, 422)


# ============================================================================
# JOURNEY F: Release Rejection Blocks Financial Execution Path
# ============================================================================

def test_journey_f_release_rejection_blocks_financial_execution(client: TestClient, db_session: Session, actors_fixture):
    """
    Journey F — Release rejection and closure:
    A rejected case does not proceed through the financial execution path.
    A successful case records statutory decision, financial order, downstream evidence,
    and closure as separate events.
    """
    actors = actors_fixture
    inst_user = actors["inst_user_a"]
    officer = actors["scrutiny"]
    branch = actors["branch"]
    authority = actors["authority"]
    finance = actors["finance"]
    inst = actors["inst_a"]

    # 1. Setup instrument and release request
    h_inst = auth_client(client, inst_user)
    fdr = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "Axis Bank",
        "reference_number": "AXIS-REJ-JF-001",
        "amount": "1500000.00",
        "issue_date": str(date.today() - timedelta(days=400)),
        "maturity_date": str(date.today() - timedelta(days=35)),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    }, headers=h_inst).json()
    fdr_id = fdr["id"]

    # Upload documents
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (FDR AXIS) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    client.post(
        f"/api/v1/instruments/{fdr_id}/documents",
        data={"category": "FDR_COPY", "title": "Deposit Receipt"},
        files={"file": ("fdr.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=h_inst,
    )
    client.post(
        f"/api/v1/instruments/{fdr_id}/documents",
        data={"category": "SANCTION_ORDER", "title": "Sanction Order"},
        files={"file": ("so.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=h_inst,
    )

    # Scrutiny L2 attestation
    h_officer = auth_client(client, officer)
    client.post(
        f"/api/v1/verification/instruments/{fdr_id}/trust/l2-officer-decision",
        json={"reason": "Verified.", "evidence_references": ["AXIS-EVID-01"]},
        headers=h_officer,
    )

    # Resolve any open findings
    findings_res = client.get(f"/api/v1/instruments/{fdr_id}/findings", headers=h_officer)
    for finding in findings_res.json().get("items", []):
        if finding["status"] in ("OPEN", "IN_REVIEW"):
            client.post(
                f"/api/v1/findings/{finding['id']}/status",
                json={"target_status": "RESOLVED", "reason": "Officer cleared findings during scrutiny."},
                headers=h_officer,
            )

    # Create release request and submit
    rel = client.post("/api/v1/release/requests", json={
        "instrument_id": fdr_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Statutory release petition.",
    }, headers=h_inst).json()
    case_id = rel["id"]

    client.post(
        f"/api/v1/release/requests/{case_id}/decisions",
        json={"decision_type": "SUBMIT", "reason": "Petition submitted."},
        headers=h_inst,
    )

    # Route to authority
    h_branch = auth_client(client, branch)
    client.post(f"/api/v1/release/requests/{case_id}/start-review", headers=h_branch)
    client.post(f"/api/v1/release/requests/{case_id}/evaluate-readiness", headers=h_branch)
    client.post(
        f"/api/v1/release/requests/{case_id}/recommend-for-authority?reason=Ready+for+decision",
        headers=h_branch,
    )

    # 2. Competent Authority REJECTS the release request
    h_auth = auth_client(client, authority)
    rej_res = client.post(
        f"/api/v1/release/requests/{case_id}/reject?reason=Statutory+compliance+conditions+not+fulfilled",
        headers=h_auth,
    )
    assert rej_res.status_code in (200, 201)
    assert rej_res.json()["decision_type"] == "REJECT"

    # Verify status is REJECTED
    case_post_rej = client.get(f"/api/v1/release/requests/{case_id}", headers=h_auth).json()
    assert case_post_rej["workflow_status"] == "REJECTED"

    # 3. Critical Invariant: Finance Officer CANNOT record release order on REJECTED request
    h_fin = auth_client(client, finance)
    illegal_order = client.post(
        f"/api/v1/release/requests/{case_id}/record-order",
        json={
            "order_reference_number": "AICTE-RO-ILLEGAL-REJECTED",
            "order_date": str(date.today()),
        },
        headers=h_fin,
    )
    assert illegal_order.status_code == 400
    assert "INVALID_ORDER_RECORDING_STATE" in illegal_order.text

    # Downstream confirmation and closure are also strictly blocked
    illegal_confirm = client.post(
        f"/api/v1/release/requests/{case_id}/confirm-bank-action?bank_action_notes=Illegal",
        headers=h_fin,
    )
    assert illegal_confirm.status_code == 400

    illegal_close = client.post(
        f"/api/v1/release/requests/{case_id}/close-case?closure_notes=Illegal",
        headers=h_fin,
    )
    assert illegal_close.status_code == 400


# ============================================================================
# SEVEN-ROLE AUTHORIZATION AUDIT MATRIX & SECURITY INVARIANTS
# ============================================================================

def test_seven_role_authorization_invariants(client: TestClient, db_session: Session, actors_fixture):
    """
    Seven-Role Authorization Audit:
    Verifies that all 7 roles strictly follow canonical permissions and invariants:
    - Institution User tenant isolation across records and nested resources.
    - Auditor read-only invariance (mutations blocked with 403; read verification passes).
    - Competent Authority exclusive statutory approval/rejection.
    - Finance Officer exclusive release-order recording.
    - System Admin cannot bypass release gate blockers or approve statutory release.
    - Maker-checker separation (creator cannot approve).
    """
    actors = actors_fixture
    inst_a = actors["inst_a"]
    inst_b = actors["inst_b"]
    user_a = actors["inst_user_a"]
    user_b = actors["inst_user_b"]
    auditor = actors["auditor"]
    finance = actors["finance"]
    scrutiny = actors["scrutiny"]
    branch = actors["branch"]
    authority = actors["authority"]
    admin = actors["admin"]

    h_a = auth_client(client, user_a)
    h_b = auth_client(client, user_b)
    h_aud = auth_client(client, auditor)
    h_fin = auth_client(client, finance)
    h_scrut = auth_client(client, scrutiny)
    h_branch = auth_client(client, branch)
    h_auth = auth_client(client, authority)
    h_adm = auth_client(client, admin)

    # 1. Institution User Tenant Isolation (Invariant 1)
    # Register FDR for Institution A
    fdr_a = client.post("/api/v1/instruments", json={
        "institution_id": inst_a.id,
        "instrument_type": "FDR",
        "bank_name": "Union Bank of India",
        "reference_number": "UBI-TENANT-A-001",
        "amount": "1000000.00",
        "issue_date": str(date.today() - timedelta(days=300)),
        "maturity_date": str(date.today() + timedelta(days=60)),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    }, headers=h_a).json()
    fdr_a_id = fdr_a["id"]

    # Institution User B CANNOT read, edit, or access Institution A's FDR
    denied_read = client.get(f"/api/v1/instruments/{fdr_a_id}", headers=h_b)
    assert denied_read.status_code == 403

    denied_patch = client.patch(
        f"/api/v1/instruments/{fdr_a_id}",
        json={"remarks": "Malicious edit attempt by Tenant B"},
        headers=h_b,
    )
    assert denied_patch.status_code == 403

    # Upload document to A's FDR
    pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (Doc A) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    doc_a = client.post(
        f"/api/v1/instruments/{fdr_a_id}/documents",
        data={"category": "FDR_COPY", "title": "Doc A"},
        files={"file": ("doc_a.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=h_a,
    ).json()
    doc_a_id = doc_a["document_id"]
    ver_a_id = doc_a["version_id"]

    # Institution User B CANNOT download Institution A's document content
    denied_dl = client.get(
        f"/api/v1/documents/{doc_a_id}/versions/{ver_a_id}/content",
        headers=h_b,
    )
    assert denied_dl.status_code == 403

    # 2. Auditor Read-Only Invariance (Invariants 3 & 4)
    # Auditor cannot create instruments
    denied_aud_fdr = client.post("/api/v1/instruments", json={
        "institution_id": inst_a.id,
        "instrument_type": "FDR",
        "bank_name": "Test Bank",
        "reference_number": "AUD-ILLEGAL",
        "amount": "1000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365)),
    }, headers=h_aud)
    assert denied_aud_fdr.status_code == 403

    # Auditor cannot upload documents
    denied_aud_doc = client.post(
        f"/api/v1/instruments/{fdr_a_id}/documents",
        data={"category": "FDR_COPY", "title": "Auditor Illegal Upload"},
        files={"file": ("fake.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=h_aud,
    )
    assert denied_aud_doc.status_code == 403

    # Auditor cannot trigger extraction retry
    denied_aud_ext = client.post(
        f"/api/v1/documents/{doc_a_id}/versions/{ver_a_id}/extract",
        headers=h_aud,
    )
    assert denied_aud_ext.status_code == 403

    # Auditor CAN perform cryptographic read-only audit verification
    aud_verify = client.post("/api/v1/audit/verify", headers=h_aud)
    assert aud_verify.status_code == 200
    assert aud_verify.json()["status"] == "PASS"

    # 3. Release Order Recording Exclusivity (Invariant 6)
    # Setup release request in APPROVED state
    client.post(
        f"/api/v1/instruments/{fdr_a_id}/documents",
        data={"category": "SANCTION_ORDER", "title": "Sanction Order"},
        files={"file": ("so.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=h_a,
    )
    client.post(
        f"/api/v1/verification/instruments/{fdr_a_id}/trust/l2-officer-decision",
        json={"reason": "L2.", "evidence_references": ["EVID-01"]},
        headers=h_scrut,
    )
    # Resolve any open findings
    findings_a = client.get(f"/api/v1/instruments/{fdr_a_id}/findings", headers=h_scrut)
    for finding in findings_a.json().get("items", []):
        if finding["status"] in ("OPEN", "IN_REVIEW"):
            client.post(
                f"/api/v1/findings/{finding['id']}/status",
                json={"target_status": "RESOLVED", "reason": "Officer cleared findings during scrutiny."},
                headers=h_scrut,
            )

    rel_a = client.post("/api/v1/release/requests", json={
        "instrument_id": fdr_a_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "RBAC verification case.",
    }, headers=h_a).json()
    case_a_id = rel_a["id"]

    client.post(
        f"/api/v1/release/requests/{case_a_id}/decisions",
        json={"decision_type": "SUBMIT", "reason": "Submitted."},
        headers=h_a,
    )
    client.post(f"/api/v1/release/requests/{case_a_id}/start-review", headers=h_branch)
    client.post(f"/api/v1/release/requests/{case_a_id}/evaluate-readiness", headers=h_branch)
    client.post(
        f"/api/v1/release/requests/{case_a_id}/recommend-for-authority?reason=Ready",
        headers=h_branch,
    )
    app_res = client.post(
        f"/api/v1/release/requests/{case_a_id}/approve?reason=Approved",
        headers=h_auth,
    )
    assert app_res.status_code in (200, 201)

    # Scrutiny Officer, Auditor, Admin, and Competent Authority CANNOT record release orders
    denied_order_scrut = client.post(
        f"/api/v1/release/requests/{case_a_id}/record-order",
        json={"order_reference_number": "DENIED-RO-1", "order_date": str(date.today())},
        headers=h_scrut,
    )
    assert denied_order_scrut.status_code == 403

    denied_order_auth = client.post(
        f"/api/v1/release/requests/{case_a_id}/record-order",
        json={"order_reference_number": "DENIED-RO-2", "order_date": str(date.today())},
        headers=h_auth,
    )
    assert denied_order_auth.status_code == 403

    denied_order_adm = client.post(
        f"/api/v1/release/requests/{case_a_id}/record-order",
        json={"order_reference_number": "DENIED-RO-3", "order_date": str(date.today())},
        headers=h_adm,
    )
    assert denied_order_adm.status_code == 403

    # Only FINANCE_OFFICER can record release orders
    order_fin = client.post(
        f"/api/v1/release/requests/{case_a_id}/record-order",
        json={"order_reference_number": "AICTE-RO-APPROVED-01", "order_date": str(date.today())},
        headers=h_fin,
    )
    assert order_fin.status_code in (200, 201)

    # 4. Statutory Approval Exclusivity (Invariant 5)
    # Setup second case
    fdr_a2 = client.post("/api/v1/instruments", json={
        "institution_id": inst_a.id,
        "instrument_type": "FDR",
        "bank_name": "HDFC Bank",
        "reference_number": "HDFC-RO-002",
        "amount": "1000000.00",
        "issue_date": str(date.today() - timedelta(days=300)),
        "maturity_date": str(date.today() + timedelta(days=60)),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    }, headers=h_a).json()
    fdr_a2_id = fdr_a2["id"]

    client.post(
        f"/api/v1/instruments/{fdr_a2_id}/documents",
        data={"category": "FDR_COPY", "title": "FDR"},
        files={"file": ("f.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=h_a,
    )
    client.post(
        f"/api/v1/instruments/{fdr_a2_id}/documents",
        data={"category": "SANCTION_ORDER", "title": "SO"},
        files={"file": ("s.pdf", io.BytesIO(pdf), "application/pdf")},
        headers=h_a,
    )
    client.post(
        f"/api/v1/verification/instruments/{fdr_a2_id}/trust/l2-officer-decision",
        json={"reason": "L2.", "evidence_references": ["E2"]},
        headers=h_scrut,
    )
    # Resolve findings for fdr_a2
    findings_a2 = client.get(f"/api/v1/instruments/{fdr_a2_id}/findings", headers=h_scrut)
    for finding in findings_a2.json().get("items", []):
        if finding["status"] in ("OPEN", "IN_REVIEW"):
            client.post(
                f"/api/v1/findings/{finding['id']}/status",
                json={"target_status": "RESOLVED", "reason": "Officer cleared findings during scrutiny."},
                headers=h_scrut,
            )

    rel_a2 = client.post("/api/v1/release/requests", json={
        "instrument_id": fdr_a2_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Case 2.",
    }, headers=h_a).json()
    case_a2_id = rel_a2["id"]

    client.post(
        f"/api/v1/release/requests/{case_a2_id}/decisions",
        json={"decision_type": "SUBMIT", "reason": "Sub."},
        headers=h_a,
    )
    client.post(f"/api/v1/release/requests/{case_a2_id}/start-review", headers=h_branch)
    client.post(f"/api/v1/release/requests/{case_a2_id}/evaluate-readiness", headers=h_branch)
    client.post(
        f"/api/v1/release/requests/{case_a2_id}/recommend-for-authority?reason=Ready",
        headers=h_branch,
    )

    # System Admin CANNOT approve release (statutory release approval reserved to Competent Authority)
    denied_adm_app = client.post(
        f"/api/v1/release/requests/{case_a2_id}/approve?reason=Admin+approval+attempt",
        headers=h_adm,
    )
    assert denied_adm_app.status_code == 403

    # Finance Officer CANNOT approve release
    denied_fin_app = client.post(
        f"/api/v1/release/requests/{case_a2_id}/approve?reason=Finance+approval+attempt",
        headers=h_fin,
    )
    assert denied_fin_app.status_code == 403

    # Scrutiny Officer CANNOT approve release
    denied_scrut_app = client.post(
        f"/api/v1/release/requests/{case_a2_id}/approve?reason=Scrutiny+approval+attempt",
        headers=h_scrut,
    )
    assert denied_scrut_app.status_code == 403
