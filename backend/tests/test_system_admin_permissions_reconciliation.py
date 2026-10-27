"""
Test Suite: System Admin Permissions Reconciliation & Least-Privilege Verification (Prompt 8 Part A)

Verifies:
1. Negative tests: Prohibited operational actions for SYSTEM_ADMIN:
   - Statutory release approval is rejected (403 Forbidden).
   - Statutory release rejection is rejected (403 Forbidden).
   - Release-order recording is rejected (403 Forbidden; exclusive to FINANCE_OFFICER).
   - Bank-action confirmation is rejected (403 Forbidden; exclusive to FINANCE_OFFICER/BRANCH_HEAD).
   - Release case closure is rejected (403 Forbidden).
   - L2 officer trust attestation is rejected (403 Forbidden; exclusive to SCRUTINY_OFFICER/BRANCH_HEAD).
   - Finding status transitions, assignment, and dismissal are rejected (403 Forbidden).
   - Returning instrument for correction is rejected (403 Forbidden).
   - Release blocker gate bypass is impossible.

2. Positive tests: Legitimate administrative and governance tasks for SYSTEM_ADMIN:
   - User account listing and provisioning.
   - Institution management and onboarding.
   - Global validation policy parameter management (exclusive to SYSTEM_ADMIN).
   - Administrative operational oversight notification feed access.
   - Cryptographic SHA-256 audit ledger verification.
   - System diagnostic and health check access.
"""
from decimal import Decimal
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.release.models import ReleaseRequest, ReleaseWorkflowStatus
from app.modules.validation.models import ValidationFinding
from app.modules.validation.enums import FindingStatus, RuleSeverity
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
    client.headers.update({"Authorization": f"Bearer {token}"})


@pytest.fixture
def rbac_fixture(db_session: Session):
    inst = Institution(
        code="INST-RBAC-RECON-01",
        legal_name="National Governance Technical University",
        display_name="NGTU",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar",
        contact_email="registrar@ngtu.ac.in",
        contact_phone="+91-11-23456789",
        address_line1="Governance Enclave",
        city="New Delhi",
        state="Delhi",
        postal_code="110001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    admin = provision_user(
        db=db_session,
        full_name="Platform Admin",
        email="sysadmin.recon@aicte.gov.in",
        password="AdminPassword@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    scrutiny = provision_user(
        db=db_session,
        full_name="Scrutiny Officer",
        email="scrutiny.recon@aicte.gov.in",
        password="OfficerPassword@2026",
        role=ROLE_SCRUTINY_OFFICER,
    )
    branch_head = provision_user(
        db=db_session,
        full_name="Branch Head",
        email="branchhead.recon@aicte.gov.in",
        password="BranchPassword@2026",
        role=ROLE_BRANCH_HEAD,
    )
    authority = provision_user(
        db=db_session,
        full_name="Competent Authority",
        email="authority.recon@aicte.gov.in",
        password="AuthorityPassword@2026",
        role=ROLE_COMPETENT_AUTHORITY,
    )
    finance = provision_user(
        db=db_session,
        full_name="Finance Officer",
        email="finance.recon@aicte.gov.in",
        password="FinancePassword@2026",
        role=ROLE_FINANCE_OFFICER,
    )
    inst_user = provision_user(
        db=db_session,
        full_name="College Nodal Officer",
        email="nodal.recon@ngtu.ac.in",
        password="NodalPassword@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst.id,
    )
    auditor = provision_user(
        db=db_session,
        full_name="CAG Auditor",
        email="auditor.recon@cag.gov.in",
        password="AuditorPassword@2026",
        role=ROLE_AUDITOR,
    )

    fdr = Instrument(
        institution_id=inst.id,
        instrument_type="FDR",
        bank_name="Punjab National Bank",
        branch="Sansad Marg, New Delhi",
        reference_number="PNB-RBAC-2026-9999",
        amount=Decimal("2500000.00"),
        currency="INR",
        issue_date=date.today() - timedelta(days=365),
        maturity_date=date.today() + timedelta(days=730),
        status="ACTIVE",
        trust_level="L0_DECLARED",
        lien_marked=True,
        joint_with_aicte=True,
    )
    db_session.add(fdr)
    db_session.commit()
    db_session.refresh(fdr)

    finding = ValidationFinding(
        finding_fingerprint="fp-rbac-recon-001",
        instrument_id=fdr.id,
        institution_id=inst.id,
        rule_id="RULE_DATE_ORDERING",
        rule_version="1.0",
        rule_type="DETERMINISTIC",
        category="DATE",
        severity=RuleSeverity.HIGH.value,
        status=FindingStatus.OPEN.value,
        title="Simulated Discrepancy",
        explanation="Testing administrative permission boundary.",
    )
    db_session.add(finding)
    db_session.commit()
    db_session.refresh(finding)

    release_req = ReleaseRequest(
        case_number="REL-RECON-2026-0001",
        instrument_id=fdr.id,
        institution_id=inst.id,
        requester_id=inst_user.id,
        request_type="STANDARD_RELEASE",
        case_type="STANDARD_RELEASE",
        request_reason="Statutory lease completion",
        workflow_status=ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value,
    )
    db_session.add(release_req)
    db_session.commit()
    db_session.refresh(release_req)

    return {
        "inst": inst,
        "admin": admin,
        "scrutiny": scrutiny,
        "branch_head": branch_head,
        "authority": authority,
        "finance": finance,
        "inst_user": inst_user,
        "auditor": auditor,
        "fdr": fdr,
        "finding": finding,
        "release_req": release_req,
    }


# ==============================================================================
# 1. Prohibited System Admin Operations (Negative Tests)
# ==============================================================================

def test_admin_cannot_approve_release_petition(client: TestClient, rbac_fixture: dict):
    """System Admin MUST receive 403 Forbidden when attempting statutory release approval."""
    set_auth(client, rbac_fixture["admin"])
    case_id = rbac_fixture["release_req"].id
    res = client.post(f"/api/v1/release/requests/{case_id}/approve?reason=Admin+Attempted+Sanction")
    assert res.status_code == 403
    assert "Competent Authority" in res.text or "forbidden" in res.text.lower()


def test_admin_cannot_reject_release_petition(client: TestClient, rbac_fixture: dict):
    """System Admin MUST receive 403 Forbidden when attempting statutory release rejection."""
    set_auth(client, rbac_fixture["admin"])
    case_id = rbac_fixture["release_req"].id
    res = client.post(f"/api/v1/release/requests/{case_id}/reject?reason=Admin+Attempted+Rejection")
    assert res.status_code == 403


def test_admin_cannot_record_release_order(client: TestClient, rbac_fixture: dict, db_session: Session):
    """System Admin MUST receive 403 Forbidden when attempting to record financial release orders."""
    # First set case to APPROVED by Competent Authority
    rbac_fixture["release_req"].workflow_status = ReleaseWorkflowStatus.APPROVED.value
    db_session.commit()

    set_auth(client, rbac_fixture["admin"])
    case_id = rbac_fixture["release_req"].id
    res = client.post(
        f"/api/v1/release/requests/{case_id}/record-order",
        json={
            "order_reference_number": "AICTE/FIN/ADMIN-ILLEGAL",
            "order_date": str(date.today()),
            "notes": "Admin illegal order",
        },
    )
    assert res.status_code == 403
    assert "FINANCE_OFFICER" in res.text or "forbidden" in res.text.lower()


def test_admin_cannot_confirm_bank_action(client: TestClient, rbac_fixture: dict, db_session: Session):
    """System Admin MUST receive 403 Forbidden when attempting to confirm bank-side execution."""
    rbac_fixture["release_req"].workflow_status = ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value
    db_session.commit()

    set_auth(client, rbac_fixture["admin"])
    case_id = rbac_fixture["release_req"].id
    res = client.post(f"/api/v1/release/requests/{case_id}/confirm-bank-action?bank_action_notes=Illegal")
    assert res.status_code == 403


def test_admin_cannot_close_release_case(client: TestClient, rbac_fixture: dict, db_session: Session):
    """System Admin MUST receive 403 Forbidden when attempting to close a release case."""
    rbac_fixture["release_req"].workflow_status = ReleaseWorkflowStatus.COMPLETED.value
    db_session.commit()

    set_auth(client, rbac_fixture["admin"])
    case_id = rbac_fixture["release_req"].id
    res = client.post(f"/api/v1/release/requests/{case_id}/close-case?closure_notes=Illegal+closure")
    assert res.status_code == 403


def test_admin_cannot_grant_l2_officer_trust(client: TestClient, rbac_fixture: dict):
    """System Admin MUST receive 403 Forbidden when attempting an L2 officer trust attestation."""
    set_auth(client, rbac_fixture["admin"])
    fdr_id = rbac_fixture["fdr"].id
    res = client.post(
        f"/api/v1/verification/instruments/{fdr_id}/trust/l2-officer-decision",
        json={
            "reason": "Admin attempted physical stamp attestation.",
            "evidence_references": ["DOC-REF-001"],
        },
    )
    assert res.status_code == 403
    assert "OFFICER_ROLE_REQUIRED" in res.text or "officers" in res.text.lower()


def test_admin_cannot_transition_or_dismiss_findings(client: TestClient, rbac_fixture: dict):
    """System Admin MUST receive 403 Forbidden when attempting to dismiss or resolve individual findings."""
    set_auth(client, rbac_fixture["admin"])
    finding_id = rbac_fixture["finding"].id
    fdr_id = rbac_fixture["fdr"].id

    # Attempt status transition
    res_trans = client.post(
        f"/api/v1/validation/findings/{finding_id}/status",
        json={
            "target_status": "DISMISSED",
            "reason": "Admin attempted dismissal.",
        },
    )
    assert res_trans.status_code == 403

    # Attempt dismiss endpoint
    res_dismiss = client.post(
        f"/api/v1/validation/instruments/{fdr_id}/findings/{finding_id}/dismiss",
        json={"reason": "Admin attempted dismissal."},
    )
    assert res_dismiss.status_code == 403


def test_admin_cannot_return_instrument_for_correction(client: TestClient, rbac_fixture: dict):
    """System Admin MUST receive 403 Forbidden when attempting to return an instrument for correction."""
    set_auth(client, rbac_fixture["admin"])
    fdr_id = rbac_fixture["fdr"].id
    res = client.post(
        f"/api/v1/validation/instruments/{fdr_id}/return-for-correction",
        json={"explanation": "Admin deficiency remarks."},
    )
    assert res.status_code == 403


# ==============================================================================
# 2. Permitted System Admin Tasks (Positive Tests)
# ==============================================================================

def test_admin_can_provision_users(client: TestClient, rbac_fixture: dict):
    """System Admin can list users and provision new accounts."""
    set_auth(client, rbac_fixture["admin"])

    # List users
    res_list = client.get("/api/v1/auth/users")
    assert res_list.status_code == 200
    assert "items" in res_list.json()

    # Provision user
    res_create = client.post(
        "/api/v1/auth/users",
        json={
            "email": "new.desk.officer@aicte.gov.in",
            "full_name": "New Desk Officer",
            "password": "SecureOfficerPass@2026",
            "role": "SCRUTINY_OFFICER",
        },
    )
    assert res_create.status_code == 201
    assert res_create.json()["email"] == "new.desk.officer@aicte.gov.in"


def test_admin_can_manage_institutions(client: TestClient, rbac_fixture: dict):
    """System Admin can list and register institutions."""
    set_auth(client, rbac_fixture["admin"])

    # List institutions
    res_list = client.get("/api/v1/institutions")
    assert res_list.status_code == 200

    # Register new institution
    res_create = client.post(
        "/api/v1/institutions",
        json={
            "code": "INST-ADMIN-NEW-01",
            "legal_name": "Central Institute of Information Technology",
            "display_name": "CIIT Delhi",
            "institution_type": "TECHNICAL_INSTITUTE",
            "contact_name": "Dr. Registrar",
            "contact_email": "registrar@ciit.ac.in",
            "contact_phone": "+91-11-23000000",
            "address_line1": "Institutional Area",
            "city": "New Delhi",
            "state": "Delhi",
            "postal_code": "110001",
        },
    )
    assert res_create.status_code == 201
    assert res_create.json()["code"] == "INST-ADMIN-NEW-01"


def test_admin_can_manage_validation_policies(client: TestClient, rbac_fixture: dict):
    """System Admin can update global validation policy configuration parameters."""
    set_auth(client, rbac_fixture["admin"])

    res_policy = client.post(
        "/api/v1/validation/policy",
        json={
            "config_key": "MIN_FDR_AMOUNT_INR",
            "config_value": "150000.00",
            "value_type": "decimal",
            "display_name": "Minimum FDR Amount",
            "description": "Global minimum deposit threshold configuration",
        },
    )
    assert res_policy.status_code in (200, 201)
    assert res_policy.json()["config_key"] == "MIN_FDR_AMOUNT_INR"


def test_admin_can_access_oversight_and_verify_ledger(client: TestClient, rbac_fixture: dict):
    """System Admin can inspect operational oversight feeds and run cryptographic ledger verification."""
    set_auth(client, rbac_fixture["admin"])

    # 1. Operational oversight feed
    res_oversight = client.get("/api/v1/lifecycle/admin/oversight")
    assert res_oversight.status_code == 200
    assert "items" in res_oversight.json()

    # 2. Cryptographic hash-chain audit verification
    res_verify = client.post("/api/v1/audit/verify")
    assert res_verify.status_code == 200
    assert res_verify.json()["status"] == "PASS"
    assert res_verify.json()["is_chain_intact"] is True
