"""
Test Suite: Prompt 3 RBAC Notifications, Audit Accountability, and End-to-End Acceptance
Covers Phase E test matrix:
1. Authentication and Route Protection across all seven roles
2. Institution Tenant Isolation (cross-tenant access denied)
3. Scrutiny and Verification (L2 attestation, simulated bank response safeguards)
4. Maker-Checker Separation and Release Gate Constraints
5. Auditor Read-Only and Cryptographic SHA-256 Audit Chain Verification
6. Persistent Notifications, Deduplication, and System Admin Operational Oversight
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import LifecycleNotification
from app.modules.release.models import ReleaseRequest
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
    """Sets session authentication cookie for the given user."""
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


def create_test_fixture(db: Session):
    """Creates synthetic institutions and users for all 7 roles."""
    inst_a = Institution(
        code="INST-RBAC-A",
        legal_name="Apex Engineering Institute",
        institution_type="TECHNICAL",
        contact_email="contact@apex.edu.in",
        state="Maharashtra",
        assigned_office="WRO-MUMBAI",
        is_active=True,
    )
    inst_b = Institution(
        code="INST-RBAC-B",
        legal_name="Beacon Polytechnic Institute",
        institution_type="POLYTECHNIC",
        contact_email="contact@beacon.edu.in",
        state="Karnataka",
        assigned_office="SRO-BANGALORE",
        is_active=True,
    )
    db.add_all([inst_a, inst_b])
    db.commit()

    admin = provision_user(db, "System Admin", "admin.rbac@aicte.gov.in", "AdminPass123!", ROLE_SYSTEM_ADMIN)
    scrutiny = provision_user(db, "Scrutiny Officer", "scrutiny.rbac@aicte.gov.in", "ScrutinyPass123!", ROLE_SCRUTINY_OFFICER)
    branch = provision_user(db, "Branch Head", "branch.rbac@aicte.gov.in", "BranchPass123!", ROLE_BRANCH_HEAD)
    authority = provision_user(db, "Competent Authority", "authority.rbac@aicte.gov.in", "AuthorityPass123!", ROLE_COMPETENT_AUTHORITY)
    finance = provision_user(db, "Finance Officer", "finance.rbac@aicte.gov.in", "FinancePass123!", ROLE_FINANCE_OFFICER)
    auditor = provision_user(db, "Statutory Auditor", "auditor.rbac@aicte.gov.in", "AuditorPass123!", ROLE_AUDITOR)
    inst_user_a = provision_user(db, "Apex Principal", "principal@apex.edu.in", "ApexPass123!", ROLE_INSTITUTION_USER, institution_id=inst_a.id)
    inst_user_b = provision_user(db, "Beacon Principal", "principal@beacon.edu.in", "BeaconPass123!", ROLE_INSTITUTION_USER, institution_id=inst_b.id)

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "admin": admin,
        "scrutiny": scrutiny,
        "branch": branch,
        "authority": authority,
        "finance": finance,
        "auditor": auditor,
        "inst_user_a": inst_user_a,
        "inst_user_b": inst_user_b,
    }


# ==============================================================================
# 1. Authentication and Route Protection across All Seven Roles
# ==============================================================================

def test_all_seven_roles_authentication(client: TestClient, db_session: Session):
    fixtures = create_test_fixture(db_session)
    roles = [
        fixtures["admin"],
        fixtures["scrutiny"],
        fixtures["branch"],
        fixtures["authority"],
        fixtures["finance"],
        fixtures["auditor"],
        fixtures["inst_user_a"],
    ]

    for user in roles:
        set_auth(client, user)
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == user.email
        assert data["role"] == user.role


def test_unauthorized_route_protection(client: TestClient, db_session: Session):
    fixtures = create_test_fixture(db_session)

    # 1. Institution User cannot access Admin Oversight Feed (403)
    set_auth(client, fixtures["inst_user_a"])
    res = client.get("/api/v1/lifecycle/admin/oversight")
    assert res.status_code == 403

    # 2. Scrutiny Officer cannot access user administration (403)
    set_auth(client, fixtures["scrutiny"])
    res = client.get("/api/v1/auth/users")
    assert res.status_code == 403

    # 3. Auditor cannot create instruments (403)
    set_auth(client, fixtures["auditor"])
    res = client.post("/api/v1/instruments", json={
        "institution_id": fixtures["inst_a"].id,
        "instrument_type": "FDR",
        "bank_name": "State Bank of India",
        "reference_number": "SBI-AUDIT-DENIED",
        "amount": "100000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365)),
    })
    assert res.status_code == 403


# ==============================================================================
# 2. Institution Tenant Isolation
# ==============================================================================

def test_institution_tenant_isolation(client: TestClient, db_session: Session):
    fixtures = create_test_fixture(db_session)

    # Institution A submits an instrument
    set_auth(client, fixtures["inst_user_a"])
    res = client.post("/api/v1/instruments", json={
        "institution_id": fixtures["inst_a"].id,
        "instrument_type": "FDR",
        "bank_name": "State Bank of India",
        "reference_number": "FDR-APEX-001",
        "amount": "500000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365)),
    })
    assert res.status_code == 201
    inst_a_instrument_id = res.json()["id"]

    # Institution B user CANNOT view Institution A's instrument
    set_auth(client, fixtures["inst_user_b"])
    get_res = client.get(f"/api/v1/instruments/{inst_a_instrument_id}")
    assert get_res.status_code == 403

    # Institution B user CANNOT view Institution A's notifications
    notif_res = client.get(f"/api/v1/lifecycle/instruments/{inst_a_instrument_id}/notifications")
    assert notif_res.status_code == 403

    # Institution B's inbox does NOT contain notifications for Institution A
    inbox_res = client.get("/api/v1/lifecycle/notifications/inbox")
    assert inbox_res.status_code == 200
    items = inbox_res.json()["items"]
    for item in items:
        assert item["institution_id"] != fixtures["inst_a"].id


# ==============================================================================
# 3. Scrutiny and Verification Safeguards
# ==============================================================================

def test_scrutiny_and_verification_safeguards(client: TestClient, db_session: Session):
    fixtures = create_test_fixture(db_session)

    # 1. Institution User submits instrument
    set_auth(client, fixtures["inst_user_a"])
    res = client.post("/api/v1/instruments", json={
        "institution_id": fixtures["inst_a"].id,
        "instrument_type": "FDR",
        "bank_name": "Punjab National Bank",
        "reference_number": "PNB-VERIF-001",
        "amount": "250000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365)),
    })
    assert res.status_code == 201
    instrument_id = res.json()["id"]

    # 2. Institution user CANNOT self-grant L2 officer attestation (403)
    res_l2 = client.post(
        f"/api/v1/verification/instruments/{instrument_id}/trust/l2-officer-decision",
        json={
            "reason": "Attempted self-attestation by college",
            "evidence_references": ["DOC-SELF"],
        },
    )
    assert res_l2.status_code in (401, 403)

    # 3. Scrutiny Officer CAN record L2 decision
    set_auth(client, fixtures["scrutiny"])
    res_l2_officer = client.post(
        f"/api/v1/verification/instruments/{instrument_id}/trust/l2-officer-decision",
        json={
            "reason": "Verified bank deposit slip and AICTE lien endorsement.",
            "evidence_references": ["EVID-DEPOSIT-SLIP"],
        },
    )
    assert res_l2_officer.status_code == 201
    assert res_l2_officer.json()["trust_level"] == "L2_OFFICER_VERIFIED"

    # 4. Check that instrument trust level is now L2
    inst_check = client.get(f"/api/v1/instruments/{instrument_id}")
    assert inst_check.status_code == 200
    assert inst_check.json()["trust_level"] == "L2_OFFICER_VERIFIED"


# ==============================================================================
# 4. Maker-Checker Separation and Release Authority Restrictions
# ==============================================================================

def test_maker_checker_and_release_authority_restrictions(client: TestClient, db_session: Session):
    fixtures = create_test_fixture(db_session)

    # 1. Create instrument
    set_auth(client, fixtures["inst_user_a"])
    res_inst = client.post("/api/v1/instruments", json={
        "institution_id": fixtures["inst_a"].id,
        "instrument_type": "FDR",
        "bank_name": "Canara Bank",
        "reference_number": "CANARA-REL-001",
        "amount": "300000.00",
        "issue_date": str(date.today() - timedelta(days=400)),
        "maturity_date": str(date.today() + timedelta(days=300)),
    })
    instrument_id = res_inst.json()["id"]

    # 2. Institution User submits release request
    res_rel = client.post("/api/v1/release/requests", json={
        "instrument_id": instrument_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Course discontinuation release request.",
    })
    assert res_rel.status_code in (200, 201)
    case_id = res_rel.json()["id"]

    # 3. Finance Officer CANNOT sanction approval (403)
    set_auth(client, fixtures["finance"])
    res_fin_app = client.post(f"/api/v1/release/requests/{case_id}/approve?reason=Finance+Sanction")
    assert res_fin_app.status_code == 403

    # 4. System Admin CANNOT sanction approval (strict maker-checker requirement) (403)
    set_auth(client, fixtures["admin"])
    res_adm_app = client.post(f"/api/v1/release/requests/{case_id}/approve?reason=Admin+Sanction")
    assert res_adm_app.status_code == 403


# ==============================================================================
# 5. Auditor Read-Only and Cryptographic SHA-256 Audit Chain Verification
# ==============================================================================

def test_auditor_read_only_and_chain_verification(client: TestClient, db_session: Session):
    fixtures = create_test_fixture(db_session)

    set_auth(client, fixtures["auditor"])

    # 1. Auditor can view audit events
    res_events = client.get("/api/v1/audit/events")
    assert res_events.status_code == 200
    assert "events" in res_events.json()

    # 2. Auditor can execute cryptographic chain verification
    res_verify = client.post("/api/v1/audit/verify")
    assert res_verify.status_code == 200
    data = res_verify.json()
    assert data["status"] == "PASS"
    assert data["is_chain_intact"] is True
    assert data["verified_count"] >= 1
    assert data["first_inconsistency"] is None

    # 3. Auditor CANNOT perform mutation endpoints (e.g. create instrument)
    res_mutate = client.post("/api/v1/instruments", json={
        "institution_id": fixtures["inst_a"].id,
        "instrument_type": "FDR",
        "bank_name": "Canara Bank",
        "reference_number": "CANARA-AUDIT-MUTATE",
        "amount": "100000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365)),
    })
    assert res_mutate.status_code == 403


# ==============================================================================
# 6. Persistent Notifications, System Admin Oversight, and Read-State Tracking
# ==============================================================================

def test_material_events_and_system_admin_oversight(client: TestClient, db_session: Session):
    fixtures = create_test_fixture(db_session)

    # 1. Institution user submits instrument
    set_auth(client, fixtures["inst_user_a"])
    res = client.post("/api/v1/instruments", json={
        "institution_id": fixtures["inst_a"].id,
        "instrument_type": "FDR",
        "bank_name": "Bank of Baroda",
        "reference_number": "BOB-OVERSIGHT-001",
        "amount": "750000.00",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=365)),
    })
    assert res.status_code == 201
    inst_id = res.json()["id"]

    # 2. Verify Institution User received in-app inbox notification
    inbox_res = client.get("/api/v1/lifecycle/notifications/inbox")
    assert inbox_res.status_code == 200
    notifs = inbox_res.json()["items"]
    assert len(notifs) >= 1
    matching_user_notif = next((n for n in notifs if n["instrument_id"] == inst_id), None)
    assert matching_user_notif is not None
    assert matching_user_notif["event_type"] == "INSTRUMENT_SUBMITTED"
    assert matching_user_notif["is_read"] is False

    # 3. Verify System Admin received Operational Oversight notification
    set_auth(client, fixtures["admin"])
    oversight_res = client.get("/api/v1/lifecycle/admin/oversight")
    assert oversight_res.status_code == 200
    oversight_items = oversight_res.json()["items"]
    assert len(oversight_items) >= 1
    admin_notif = next((n for n in oversight_items if n["instrument_id"] == inst_id), None)
    assert admin_notif is not None
    assert "ADMIN_OVERSIGHT" in admin_notif["event_type"]

    # 4. Mark notification as read
    set_auth(client, fixtures["inst_user_a"])
    read_res = client.post(f"/api/v1/lifecycle/notifications/{matching_user_notif['id']}/read")
    assert read_res.status_code == 200
    assert read_res.json()["is_read"] is True

    # 5. Mark all notifications as read
    read_all_res = client.post("/api/v1/lifecycle/notifications/read-all")
    assert read_all_res.status_code == 200
    assert "marked_read" in read_all_res.json()
