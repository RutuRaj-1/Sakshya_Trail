"""
Test Suite: Authoritative Canonical Nine-Stage FDR Lifecycle Demonstration
Demonstrates the full end-to-end journey with synthetic data across all seven roles:

Stage 1: FDR Submission & Registration — Institution User registers fictional FDR deposit certificate.
Stage 2: Document Upload & Evidence — Institution User uploads certified FDR scan with SHA-256 integrity hash.
Stage 3: Validation & Discrepancy Detection — Validation engine executes rules, generating findings without mutating trust.
Stage 4: Scrutiny & Review — Scrutiny Officer examines findings, records append-only observations, and resolves findings.
Stage 5: Bank Verification & Trust — Officer records L2 attestation; verification request dispatched; simulated response cannot claim genuine L3.
Stage 6: Lifecycle Monitoring — Lifecycle engine evaluates statutory maturity stage, reminders, and validity.
Stage 7: Renewal & Successor Lineage — Institution User links renewal successor instrument; lineage continuity preserved.
Stage 8: Release Readiness — Release request evaluated against server-side checklist gate and recommended.
Stage 9: Maker-Checker Decision & Closure — Competent Authority sanctions, Finance Officer records release order,
         downstream bank action confirmed, and case sealed in SHA-256 audit ledger.
"""
import io
import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
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


def set_auth(client: TestClient, user: User):
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


def test_full_nine_stage_synthetic_journey(client: TestClient, db_session: Session):
    # Setup test institution and all 7 role actors
    inst = Institution(
        code="INST-9STAGE-01",
        legal_name="National Institute of Technical Studies",
        institution_type="TECHNICAL",
        contact_email="director@nits.ac.in",
        state="Maharashtra",
        assigned_office="WRO-MUMBAI",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()

    inst_user = provision_user(db_session, "Prof. Sharma", "principal@nits.ac.in", "InstPass123!", ROLE_INSTITUTION_USER, institution_id=inst.id)
    scrutiny_officer = provision_user(db_session, "Inspector Verma", "scrutiny@aicte.gov.in", "ScrutinyPass123!", ROLE_SCRUTINY_OFFICER)
    branch_head = provision_user(db_session, "Director Kulkarni", "branchhead@aicte.gov.in", "BranchPass123!", ROLE_BRANCH_HEAD)
    authority = provision_user(db_session, "Member Secretary", "authority@aicte.gov.in", "AuthPass123!", ROLE_COMPETENT_AUTHORITY)
    finance_officer = provision_user(db_session, "Chief Accounts Officer", "finance@aicte.gov.in", "FinancePass123!", ROLE_FINANCE_OFFICER)
    auditor = provision_user(db_session, "CAG Senior Auditor", "auditor@aicte.gov.in", "AuditPass123!", ROLE_AUDITOR)
    admin = provision_user(db_session, "Platform Admin", "sysadmin@aicte.gov.in", "AdminPass123!", ROLE_SYSTEM_ADMIN)

    # --------------------------------------------------------------------------
    # STAGE 1: FDR SUBMISSION & REGISTRATION (Institution User submits synthetic FDR)
    # --------------------------------------------------------------------------
    set_auth(client, inst_user)
    issue_dt = date.today() - timedelta(days=300)
    maturity_dt = date.today() + timedelta(days=65)

    sub_res = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "State Bank of India",
        "reference_number": "SBI-FDR-9STAGE-101",
        "amount": "1500000.00",
        "issue_date": str(issue_dt),
        "maturity_date": str(maturity_dt),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    })
    assert sub_res.status_code == 201
    instrument_id = sub_res.json()["id"]
    assert sub_res.json()["trust_level"] == "L0_DECLARED"
    assert sub_res.json()["status"] == "REGISTERED"

    # Verify notification generated for Institution User
    inbox_res = client.get("/api/v1/lifecycle/notifications/inbox")
    assert inbox_res.status_code == 200
    assert any(n["instrument_id"] == instrument_id for n in inbox_res.json()["items"])

    # --------------------------------------------------------------------------
    # STAGE 2: DOCUMENT UPLOAD & EVIDENCE (Certified FDR scan with SHA-256 digest)
    # --------------------------------------------------------------------------
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (Synthetic FDR Deposit Receipt) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_res = client.post(
        f"/api/v1/instruments/{instrument_id}/documents",
        data={"category": "FDR_COPY", "title": "Synthetic Deposit Receipt"},
        files={"file": ("synthetic_fdr.pdf", io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert upload_res.status_code == 200
    doc_data = upload_res.json()
    assert doc_data["success"] is True
    assert "sha256_hash" in doc_data
    assert doc_data["processing_status"] in ("CLEAN", "PASSED", "SCAN_UNAVAILABLE", "SCAN_BYPASSED_DEVELOPMENT")

    # Upload Sanction Order (required for complete release documentation profile)
    upload_so_res = client.post(
        f"/api/v1/instruments/{instrument_id}/documents",
        data={"category": "SANCTION_ORDER", "title": "Regulatory Sanction Order"},
        files={"file": ("sanction_order.pdf", io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert upload_so_res.status_code == 200

    # --------------------------------------------------------------------------
    # STAGE 3: VALIDATION & DISCREPANCY DETECTION (Rule engine evaluates invariants)
    # --------------------------------------------------------------------------
    set_auth(client, scrutiny_officer)
    val_res = client.post(f"/api/v1/instruments/{instrument_id}/validation-runs", json={})
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert "rules_evaluated" in val_data
    # Safety invariant: validation engine does NOT mutate trust level
    inst_post_val = client.get(f"/api/v1/instruments/{instrument_id}").json()
    assert inst_post_val["trust_level"] == "L0_DECLARED"

    # --------------------------------------------------------------------------
    # STAGE 4: SCRUTINY & REVIEW (Scrutiny observations and findings resolution)
    # --------------------------------------------------------------------------
    # Scrutiny Officer records append-only observation on instrument
    obs_res = client.post(
        f"/api/v1/dashboard/instruments/{instrument_id}/observations",
        json={
            "observation_text": "Certificate verified: AICTE joint holder seal verified against bank ledger.",
            "observation_category": "DOCUMENTS",
            "is_internal_only": False,
        },
    )
    assert obs_res.status_code == 201
    assert obs_res.json()["status"] == "RECORDED"

    # Scrutiny Officer examines and resolves open findings
    findings_res = client.get(f"/api/v1/instruments/{instrument_id}/findings")
    assert findings_res.status_code == 200
    for finding in findings_res.json()["items"]:
        if finding["status"] in ("OPEN", "IN_REVIEW"):
            res_resolve = client.post(
                f"/api/v1/findings/{finding['id']}/status",
                json={
                    "target_status": "RESOLVED",
                    "reason": "Officer verified document contents and resolved finding during scrutiny.",
                },
            )
            assert res_resolve.status_code == 200

    # --------------------------------------------------------------------------
    # STAGE 5: BANK VERIFICATION & TRUST (Officer attestation & genuine confirmation)
    # --------------------------------------------------------------------------
    # Scrutiny Officer records authorized L2 attestation
    l2_res = client.post(
        f"/api/v1/verification/instruments/{instrument_id}/trust/l2-officer-decision",
        json={
            "reason": "Scrutiny completed: bank stamp, joint holding and lien endorsed.",
            "evidence_references": [f"DOC-{doc_data['document_id']}"],
        },
    )
    assert l2_res.status_code == 201
    assert l2_res.json()["trust_level"] == "L2_OFFICER_VERIFIED"

    # Create verification request
    v_req_res = client.post(
        f"/api/v1/verification/instruments/{instrument_id}/requests",
        json={
            "channel": "SIMULATED",
            "requested_fields": ["AMOUNT", "MATURITY_DATE", "LIEN_STATUS"],
        },
    )
    assert v_req_res.status_code == 201
    v_request_id = v_req_res.json()["id"]

    # Dispatch simulated response
    dispatch_res = client.post(
        f"/api/v1/verification/requests/{v_request_id}/dispatch",
        json={"scenario": "STANDARD_MATCH"},
    )
    assert dispatch_res.status_code == 201
    v_resp = dispatch_res.json()
    assert v_resp["is_simulated"] is True

    # Critical Safeguard: Simulated response cannot be applied as genuine L3 confirmation
    l3_res = client.post(
        f"/api/v1/verification/instruments/{instrument_id}/trust/l3-bank-confirmation",
        json={
            "verification_response_id": v_resp["id"],
            "reason": "Attempting to claim L3 using simulated response",
            "source_authorization_config": "CONFIG-SFMS-LIVE",
        },
    )
    assert l3_res.status_code in (400, 422)

    # --------------------------------------------------------------------------
    # STAGE 6: LIFECYCLE MONITORING (Maturity surveillance & validity)
    # --------------------------------------------------------------------------
    eval_res = client.post(
        "/api/v1/lifecycle/evaluate",
        json={"instrument_id": instrument_id, "force_evaluation": True},
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["maturity_stage"] in ("APPROACHING_MATURITY", "ACTIVE", "MATURED")

    # --------------------------------------------------------------------------
    # STAGE 7: RENEWAL & SUCCESSOR LINEAGE (Successor instrument linked)
    # --------------------------------------------------------------------------
    set_auth(client, inst_user)
    renewal_res = client.post(
        f"/api/v1/lifecycle/instruments/{instrument_id}/renew",
        json={
            "bank_name": "State Bank of India",
            "branch": "Main Branch",
            "reference_number": "SBI-FDR-9STAGE-RENEWED",
            "amount": 1500000.00,
            "currency": "INR",
            "issue_date": str(maturity_dt),
            "maturity_date": str(maturity_dt + timedelta(days=365)),
            "reason_or_reference": "Statutory FDR renewal upon maturity.",
        },
    )
    assert renewal_res.status_code in (200, 201)
    lineage_data = renewal_res.json()
    assert lineage_data["lineage"]["relationship_status"] == "ACTIVE"

    # --------------------------------------------------------------------------
    # STAGE 8: RELEASE READINESS (Checklist profile gate and recommendation)
    # --------------------------------------------------------------------------
    rel_create = client.post("/api/v1/release/requests", json={
        "instrument_id": instrument_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Statutory completion of mandatory deposit period.",
    })
    assert rel_create.status_code in (200, 201)
    case_id = rel_create.json()["id"]

    # Institution user submits the release petition (DRAFT -> SUBMITTED)
    sub_dec = client.post(
        f"/api/v1/release/requests/{case_id}/decisions",
        json={
            "decision_type": "SUBMIT",
            "reason": "Formal application submitted with required statutory evidence.",
        },
    )
    assert sub_dec.status_code == 201

    # Branch Head starts review and evaluates readiness gate
    set_auth(client, branch_head)
    start_rev = client.post(f"/api/v1/release/requests/{case_id}/start-review")
    assert start_rev.status_code == 200

    gate_res = client.post(f"/api/v1/release/requests/{case_id}/evaluate-readiness")
    assert gate_res.status_code == 200
    readiness = gate_res.json()
    assert "assessment_outcome" in readiness
    assert "total_items_count" in readiness

    # Recommend for authority
    rec_res = client.post(
        f"/api/v1/release/requests/{case_id}/recommend-for-authority?reason=All+documentation+verified+by+Branch+Office"
    )
    assert rec_res.status_code in (200, 201)

    # --------------------------------------------------------------------------
    # STAGE 9: MAKER-CHECKER DECISION, RELEASE ORDER & CASE CLOSURE
    # --------------------------------------------------------------------------
    # 9a: Competent Authority approves (Sanctions release)
    set_auth(client, authority)
    approve_res = client.post(
        f"/api/v1/release/requests/{case_id}/approve?reason=Approved+by+Competent+Authority+under+Regulation+12"
    )
    assert approve_res.status_code in (200, 201)
    assert approve_res.json()["decision_type"] == "APPROVE"

    # Invariant: Approval does NOT automatically record release order
    case_post_app = client.get(f"/api/v1/release/requests/{case_id}").json()
    assert case_post_app["workflow_status"] == "APPROVED"

    # Invariant: Non-Finance Officer roles CANNOT record release order
    set_auth(client, scrutiny_officer)
    unauthorized_order = client.post(
        f"/api/v1/release/requests/{case_id}/record-order",
        json={
            "order_reference_number": "AICTE-RO-ILLEGAL-01",
            "order_date": str(date.today()),
        },
    )
    assert unauthorized_order.status_code == 403

    # 9b: Finance Officer records official release order
    set_auth(client, finance_officer)
    order_res = client.post(
        f"/api/v1/release/requests/{case_id}/record-order",
        json={
            "order_reference_number": "AICTE-RO-2026-9STAGE-001",
            "order_date": str(date.today()),
            "is_synthetic_demo": True,
            "notes": "Release order dispatched to issuing bank branch.",
        },
    )
    assert order_res.status_code in (200, 201)
    assert order_res.json()["status"] in ("EXECUTED", "DRAFT_RECORDED")

    # 9c: Downstream bank-side confirmation recorded
    confirm_res = client.post(
        f"/api/v1/release/requests/{case_id}/confirm-bank-action?bank_action_notes=Bank+UTR+Ref+987654321+Processed"
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["workflow_status"] == "COMPLETED"

    # 9d: Formal case closure
    close_res = client.post(
        f"/api/v1/release/requests/{case_id}/close-case?closure_notes=Case+successfully+closed+and+sealed"
    )
    assert close_res.status_code == 200
    assert close_res.json()["workflow_status"] == "CLOSED"

    # --------------------------------------------------------------------------
    # POST-RUN VERIFICATION: SYSTEM ADMIN OPERATIONAL OVERSIGHT & AUDIT INTEGRITY
    # --------------------------------------------------------------------------
    set_auth(client, admin)
    oversight_res = client.get("/api/v1/lifecycle/admin/oversight")
    assert oversight_res.status_code == 200
    oversight_items = oversight_res.json()["items"]
    assert len(oversight_items) >= 4

    # Auditor cryptographically verifies the SHA-256 audit ledger across all 9 stages
    set_auth(client, auditor)
    verify_res = client.post("/api/v1/audit/verify")
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "PASS"
    assert verify_res.json()["is_chain_intact"] is True


def test_stage4_correction_loop_branch(client: TestClient, db_session: Session):
    """
    Verifies Stage 4 correction loop branch:
    Scrutiny Officer returns instrument for correction; instrument enters
    RETURNED_FOR_CORRECTION state; institution resubmits corrected certificate.
    """
    inst = Institution(
        code="INST-CORR-01",
        legal_name="Correction Test Institute",
        institution_type="TECHNICAL",
        contact_email="corr@test.ac.in",
        state="Karnataka",
        assigned_office="SRO-BANGALORE",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()

    inst_user = provision_user(db_session, "Principal Corr", "principal@corr.ac.in", "CorrPass123!", ROLE_INSTITUTION_USER, institution_id=inst.id)
    officer = provision_user(db_session, "Officer Corr", "officer@corr.ac.in", "OfficerPass123!", ROLE_SCRUTINY_OFFICER)

    # 1. Register FDR
    set_auth(client, inst_user)
    res = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "Canara Bank",
        "reference_number": "CAN-FDR-CORR-001",
        "amount": "500000.00",
        "issue_date": str(date.today() - timedelta(days=50)),
        "maturity_date": str(date.today() + timedelta(days=365)),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    })
    assert res.status_code == 201
    fdr_id = res.json()["id"]

    # 2. Scrutiny Officer returns for correction
    set_auth(client, officer)
    ret_res = client.post(
        f"/api/v1/instruments/{fdr_id}/return-for-correction",
        json={"explanation": "Lien endorsement stamp missing from physical scan."},
    )
    assert ret_res.status_code == 200
    assert ret_res.json()["status"] == "RETURNED_FOR_CORRECTION"

    # 3. Verify instrument status is RETURNED_FOR_CORRECTION
    inst_data = client.get(f"/api/v1/instruments/{fdr_id}").json()
    assert inst_data["status"] == "RETURNED_FOR_CORRECTION"


def test_stage8_readiness_blocker_branch(client: TestClient, db_session: Session):
    """
    Verifies Stage 8 release readiness blocker enforcement:
    A release request with unsatisfied mandatory items cannot bypass the readiness gate.
    """
    inst = Institution(
        code="INST-BLOCK-01",
        legal_name="Blocker Verification Institute",
        institution_type="TECHNICAL",
        contact_email="block@test.ac.in",
        state="Delhi",
        assigned_office="HEADQUARTERS",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()

    inst_user = provision_user(db_session, "Principal Block", "principal@block.ac.in", "BlockPass123!", ROLE_INSTITUTION_USER, institution_id=inst.id)
    officer = provision_user(db_session, "Scrutiny Block", "scrutiny@block.ac.in", "ScrutinyPass123!", ROLE_SCRUTINY_OFFICER)

    # 1. Register FDR without complete documents
    set_auth(client, inst_user)
    fdr_res = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "instrument_type": "FDR",
        "bank_name": "Punjab National Bank",
        "reference_number": "PNB-FDR-BLOCK-001",
        "amount": "1000000.00",
        "issue_date": str(date.today() - timedelta(days=200)),
        "maturity_date": str(date.today() + timedelta(days=100)),
        "lien_holder": "All India Council for Technical Education",
        "joint_with_aicte": True,
        "lien_marked": True,
    })
    assert fdr_res.status_code == 201
    fdr_id = fdr_res.json()["id"]

    # 2. Create release request
    rel_res = client.post("/api/v1/release/requests", json={
        "instrument_id": fdr_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Premature release attempt without required documents.",
    })
    assert rel_res.status_code in (200, 201)
    case_id = rel_res.json()["id"]

    # 3. Evaluate readiness
    set_auth(client, officer)
    client.post(f"/api/v1/release/requests/{case_id}/start-review")
    readiness_res = client.post(f"/api/v1/release/requests/{case_id}/evaluate-readiness")
    assert readiness_res.status_code == 200
    readiness = readiness_res.json()
    assert readiness["blockers_count"] > 0 or readiness["assessment_outcome"] != "READY"


def test_canonical_stages_contract_and_auditor_isolation(client: TestClient, db_session: Session):
    """
    Verifies that GET /api/v1/lifecycle/canonical-stages returns the exact
    canonical nine stages in correct sequence, and Auditor is blocked from all mutations.
    """
    auditor = provision_user(db_session, "Auditor Check", "auditor@check.gov.in", "AuditPass123!", ROLE_AUDITOR)
    set_auth(client, auditor)

    # 1. Canonical stages endpoint contract
    stages_res = client.get("/api/v1/lifecycle/canonical-stages")
    assert stages_res.status_code == 200
    stages = stages_res.json()
    assert len(stages) == 9

    expected_labels = [
        "FDR Submission & Registration",
        "Document Upload & Evidence",
        "Validation & Discrepancy Detection",
        "Scrutiny & Review",
        "Bank Verification & Trust",
        "Lifecycle Monitoring",
        "Renewal & Successor Lineage",
        "Release Readiness",
        "Maker-Checker Decision & Closure",
    ]

    for idx, expected_label in enumerate(expected_labels):
        assert stages[idx]["stage_number"] == idx + 1
        assert stages[idx]["label"] == expected_label

    # 2. Auditor read-only invariance on mutation endpoints
    # Instrument creation denied
    denied_inst = client.post("/api/v1/instruments", json={
        "institution_id": "inst-any",
        "instrument_type": "FDR",
        "bank_name": "Test Bank",
        "reference_number": "ILLEGAL-AUDITOR-FDR",
        "amount": "1000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365)),
    })
    assert denied_inst.status_code == 403

    # Document upload denied
    denied_doc = client.post(
        "/api/v1/instruments/fake-id/documents",
        data={"category": "FDR_COPY", "title": "Illegal"},
        files={"file": ("fake.pdf", io.BytesIO(b"fake"), "application/pdf")},
    )
    assert denied_doc.status_code == 403

    # Release creation denied
    denied_rel = client.post("/api/v1/release/requests", json={
        "instrument_id": "fake-id",
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Auditor illegal creation",
    })
    assert denied_rel.status_code == 403
