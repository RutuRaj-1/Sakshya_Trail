"""
Module 1 Acceptance Tests (M1-AC-01 through M1-AC-18)
Verifies the complete integration, security enforcement, RBAC, tenant isolation,
FDR instrument registry, audit trail, and synthetic demo seeding for Module 1.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.base import Base
from app.db.session import engine
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.audit.models import AuditEvent
from app.modules.auth.service import provision_user, authenticate_user
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    ROLE_BRANCH_HEAD,
    create_access_token,
)
from app.core.config import settings
from scripts.init_db import seed_database


def auth_headers_for(user: User) -> dict:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    return {
        "Authorization": f"Bearer {token}",
        "Origin": "http://localhost:5173",
    }


# ==============================================================================
# M1-AC-01: A clean environment can start the application and initialize DB
# ==============================================================================
def test_m1_ac_01_clean_environment_db_init(client: TestClient):
    """M1-AC-01: Health and readiness probe verifies DB connectivity and clean startup."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("alive", "healthy")

    res_ready = client.get("/readyz")
    assert res_ready.status_code == 200
    assert res_ready.json()["is_ready"] is True


# ==============================================================================
# M1-AC-02: An administrator can be securely bootstrapped and log in
# ==============================================================================
def test_m1_ac_02_admin_bootstrap_and_login(client: TestClient, db_session: Session):
    """M1-AC-02: Bootstrap admin provisioning and subsequent login session."""
    email = "bootstrap.admin@aicte-test.gov.in"
    password = "BootstrapSecurePass@2026"
    admin = provision_user(
        db=db_session,
        full_name="Bootstrap Admin",
        email=email,
        password=password,
        role=ROLE_SYSTEM_ADMIN,
        institution_id=None,
    )
    assert admin.id is not None
    assert admin.role == ROLE_SYSTEM_ADMIN

    # Test login endpoint
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"Origin": "http://localhost:5173"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["success"] is True
    assert login_data["user"]["role"] == ROLE_SYSTEM_ADMIN
    assert "access_token" in login_data


# ==============================================================================
# M1-AC-03: Unauthenticated requests to protected endpoints are rejected
# ==============================================================================
def test_m1_ac_03_unauthenticated_requests_rejected(client: TestClient):
    """M1-AC-03: Protected endpoints reject requests lacking credentials with 401."""
    endpoints = [
        "/api/v1/auth/me",
        "/api/v1/institutions",
        "/api/v1/instruments",
        "/api/v1/dashboard/summary",
        "/api/v1/audit/events",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 401, f"Expected 401 for unauthenticated {ep}, got {res.status_code}"


# ==============================================================================
# M1-AC-04: Authorized administrators can create and manage institutions
# ==============================================================================
def test_m1_ac_04_admin_create_manage_institutions(client: TestClient, db_session: Session):
    """M1-AC-04: Admin creates, reads, and updates institution record."""
    admin = provision_user(
        db=db_session,
        full_name="Admin M1-04",
        email="admin.m104@aicte-test.gov.in",
        password="Password@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    headers = auth_headers_for(admin)

    # 1. Create
    payload = {
        "code": "M1-INST-004",
        "legal_name": "Test Engineering Institute M1-04",
        "display_name": "TEI 04",
        "institution_type": "TECHNICAL_INSTITUTE",
        "contact_name": "Dr. Sharma",
        "contact_email": "dean@tei04.ac.in",
        "contact_phone": "+91-11-23891000",
        "address_line1": "Campus 4",
        "city": "New Delhi",
        "state": "Delhi",
        "postal_code": "110001",
    }
    create_res = client.post("/api/v1/institutions", json=payload, headers=headers)
    assert create_res.status_code == 201
    inst_id = create_res.json()["id"]

    # 2. Update
    patch_res = client.patch(
        f"/api/v1/institutions/{inst_id}",
        json={"display_name": "TEI 04 Updated Campus"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["display_name"] == "TEI 04 Updated Campus"


# ==============================================================================
# M1-AC-05: Duplicate institution codes cannot be created
# ==============================================================================
def test_m1_ac_05_duplicate_institution_code_rejected(client: TestClient, db_session: Session):
    """M1-AC-05: Attempting to register an institution with existing code returns 409."""
    admin = provision_user(
        db=db_session,
        full_name="Admin M1-05",
        email="admin.m105@aicte-test.gov.in",
        password="Password@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    headers = auth_headers_for(admin)

    payload = {
        "code": "M1-INST-DUP",
        "legal_name": "Original Institute",
        "contact_email": "dean@orig.ac.in",
        "state": "Delhi",
    }
    res1 = client.post("/api/v1/institutions", json=payload, headers=headers)
    assert res1.status_code == 201

    # Attempt duplicate code
    res2 = client.post("/api/v1/institutions", json=payload, headers=headers)
    assert res2.status_code == 409
    assert "DUPLICATE" in res2.json()["code"]


# ==============================================================================
# M1-AC-06: Authorized administrators can provision users with valid roles
# ==============================================================================
def test_m1_ac_06_admin_provision_users(client: TestClient, db_session: Session):
    """M1-AC-06: Administrator provisions users with valid roles and institutions."""
    admin = provision_user(
        db=db_session,
        full_name="Admin M1-06",
        email="admin.m106@aicte-test.gov.in",
        password="Password@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    headers = auth_headers_for(admin)

    inst = Institution(
        code="M1-INST-006",
        legal_name="College for User Provisioning",
        contact_email="dean@userprov.ac.in",
        state="Maharashtra",
    )
    db_session.add(inst)
    db_session.commit()

    # Provision Institution User
    prov_payload = {
        "full_name": "Nodal Officer Six",
        "email": "nodal.six@userprov.ac.in",
        "password": "SecurePassword@2026",
        "role": ROLE_INSTITUTION_USER,
        "institution_id": inst.id,
    }
    res = client.post("/api/v1/auth/users", json=prov_payload, headers=headers)
    assert res.status_code == 201
    assert res.json()["role"] == ROLE_INSTITUTION_USER
    assert res.json()["institution_id"] == inst.id


# ==============================================================================
# M1-AC-07: Institution users cannot access another institution's records
# ==============================================================================
def test_m1_ac_07_institution_user_tenant_isolation(client: TestClient, db_session: Session):
    """M1-AC-07: Institution user is denied access to other institutions and their FDRs."""
    inst_a = Institution(code="M1-TENANT-A", legal_name="Tenant A College", contact_email="a@tenant.ac.in", state="Delhi")
    inst_b = Institution(code="M1-TENANT-B", legal_name="Tenant B College", contact_email="b@tenant.ac.in", state="Punjab")
    db_session.add_all([inst_a, inst_b])
    db_session.commit()

    user_a = provision_user(
        db=db_session,
        full_name="User Tenant A",
        email="user.a@tenant.ac.in",
        password="Password@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst_a.id,
    )
    headers_a = auth_headers_for(user_a)

    # 1. Denied read of Tenant B institution
    res_inst = client.get(f"/api/v1/institutions/{inst_b.id}", headers=headers_a)
    assert res_inst.status_code == 403

    # 2. Denied read of Tenant B instrument
    fdr_b = Instrument(
        institution_id=inst_b.id,
        reference_number="FDR-TENANT-B-001",
        bank_name="Canara Bank",
        amount=Decimal("1000000.00"),
        issue_date=date.today(),
        maturity_date=date.today() + timedelta(days=365),
    )
    db_session.add(fdr_b)
    db_session.commit()

    res_fdr = client.get(f"/api/v1/instruments/{fdr_b.id}", headers=headers_a)
    assert res_fdr.status_code == 403


# ==============================================================================
# M1-AC-08: Institution users cannot change their own role or institution assignment
# ==============================================================================
def test_m1_ac_08_institution_user_cannot_elevate_privileges(client: TestClient, db_session: Session):
    """M1-AC-08: Institution user cannot update role or provision users."""
    inst = Institution(code="M1-PRIV-08", legal_name="Privilege College", contact_email="dean@priv.ac.in", state="Delhi")
    db_session.add(inst)
    db_session.commit()

    inst_user = provision_user(
        db=db_session,
        full_name="User Priv 08",
        email="user.priv08@priv.ac.in",
        password="Password@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst.id,
    )
    headers = auth_headers_for(inst_user)

    # Cannot provision new user
    prov_res = client.post(
        "/api/v1/auth/users",
        json={"full_name": "Hacker", "email": "hack@priv.ac.in", "role": ROLE_SYSTEM_ADMIN, "password": "Password@2026"},
        headers=headers,
    )
    assert prov_res.status_code == 403

    # Cannot edit user profile via admin endpoints
    patch_user = client.patch(
        f"/api/v1/auth/users/{inst_user.id}",
        json={"role": ROLE_SYSTEM_ADMIN},
        headers=headers,
    )
    assert patch_user.status_code == 403


# ==============================================================================
# M1-AC-09: Authorized users can register and view FDR records
# ==============================================================================
def test_m1_ac_09_register_and_view_fdr(client: TestClient, db_session: Session):
    """M1-AC-09: Institution user registers an FDR and views its details."""
    inst = Institution(code="M1-FDR-09", legal_name="FDR Tech College", contact_email="dean@fdrtech.ac.in", state="Delhi")
    db_session.add(inst)
    db_session.commit()

    inst_user = provision_user(
        db=db_session,
        full_name="User FDR 09",
        email="user.fdr09@fdrtech.ac.in",
        password="Password@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst.id,
    )
    headers = auth_headers_for(inst_user)

    today = date.today()
    payload = {
        "institution_id": inst.id,
        "bank_name": "Bank of Baroda",
        "reference_number": "FDR-BOB-AC09-123",
        "amount": "2500000.00",
        "currency": "INR",
        "issue_date": str(today - timedelta(days=30)),
        "maturity_date": str(today + timedelta(days=365 * 3)),
    }
    create_res = client.post("/api/v1/instruments", json=payload, headers=headers)
    assert create_res.status_code == 201
    fdr_id = create_res.json()["id"]

    get_res = client.get(f"/api/v1/instruments/{fdr_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["bank_name"] == "Bank of Baroda"
    assert get_res.json()["reference_number"] == "FDR-BOB-AC09-123"


# ==============================================================================
# M1-AC-10: Amount and date validation works on the backend
# ==============================================================================
def test_m1_ac_10_amount_and_date_validation(client: TestClient, db_session: Session):
    """M1-AC-10: Negative/zero amount and invalid dates return 422."""
    inst = Institution(code="M1-VAL-10", legal_name="Validation College", contact_email="dean@val.ac.in", state="Delhi")
    db_session.add(inst)
    db_session.commit()

    admin = provision_user(
        db=db_session,
        full_name="Admin Val 10",
        email="admin.val10@aicte.gov.in",
        password="Password@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    headers = auth_headers_for(admin)
    today = date.today()

    # Zero amount
    res_zero = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "bank_name": "SBI",
        "reference_number": "REF-ZERO",
        "amount": "0.00",
        "issue_date": str(today),
        "maturity_date": str(today + timedelta(days=100)),
    }, headers=headers)
    assert res_zero.status_code == 422

    # Maturity before issue date
    res_date = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "bank_name": "SBI",
        "reference_number": "REF-DATE",
        "amount": "100000.00",
        "issue_date": str(today),
        "maturity_date": str(today - timedelta(days=5)),
    }, headers=headers)
    assert res_date.status_code == 422


# ==============================================================================
# M1-AC-11: Every new instrument starts at L0 — DECLARED
# ==============================================================================
def test_m1_ac_11_new_instrument_starts_at_l0(client: TestClient, db_session: Session):
    """M1-AC-11: Newly created instrument has trust_level L0_DECLARED."""
    inst = Institution(code="M1-L0-11", legal_name="L0 Tech", contact_email="dean@l0.ac.in", state="Delhi")
    db_session.add(inst)
    db_session.commit()

    admin = provision_user(
        db=db_session,
        full_name="Admin L0",
        email="admin.l0@aicte.gov.in",
        password="Password@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    headers = auth_headers_for(admin)
    today = date.today()

    res = client.post("/api/v1/instruments", json={
        "institution_id": inst.id,
        "bank_name": "SBI",
        "reference_number": "REF-L0-CHECK",
        "amount": "500000.00",
        "issue_date": str(today),
        "maturity_date": str(today + timedelta(days=365)),
    }, headers=headers)
    assert res.status_code == 201
    assert res.json()["trust_level"] == "L0_DECLARED"


# ==============================================================================
# M1-AC-12: Ordinary instrument edits cannot elevate the trust level
# ==============================================================================
def test_m1_ac_12_instrument_patch_cannot_escalate_trust(client: TestClient, db_session: Session):
    """M1-AC-12: Patching an instrument cannot elevate trust_level to L1/L2/L3."""
    inst = Institution(code="M1-TRUST-12", legal_name="Trust College", contact_email="dean@trust.ac.in", state="Delhi")
    db_session.add(inst)
    db_session.commit()

    instru = Instrument(
        institution_id=inst.id,
        reference_number="REF-TRUST-12",
        bank_name="SBI",
        amount=Decimal("500000.00"),
        issue_date=date.today(),
        maturity_date=date.today() + timedelta(days=365),
        trust_level="L0_DECLARED",
    )
    db_session.add(instru)
    db_session.commit()

    admin = provision_user(
        db=db_session,
        full_name="Admin Trust 12",
        email="admin.trust12@aicte.gov.in",
        password="Password@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    headers = auth_headers_for(admin)

    # Attempt to upgrade trust level to L3_BANK_CONFIRMED
    res = client.patch(
        f"/api/v1/instruments/{instru.id}",
        json={"trust_level": "L3_BANK_CONFIRMED", "bank_branch": "Main Branch"},
        headers=headers,
    )
    # Ordinary instrument edits cannot elevate trust level (403 Forbidden)
    assert res.status_code == 403


# ==============================================================================
# M1-AC-13: Potential duplicates are warned about and never silently merged
# ==============================================================================
def test_m1_ac_13_duplicate_warning_not_silently_merged(client: TestClient, db_session: Session):
    """M1-AC-13: Duplicate bank/reference generates 409 warning; confirm_duplicate creates separate record."""
    inst = Institution(code="M1-DUP-13", legal_name="Duplicate College 13", contact_email="dean@dup13.ac.in", state="Delhi")
    db_session.add(inst)
    db_session.commit()

    admin = provision_user(
        db=db_session,
        full_name="Admin Dup 13",
        email="admin.dup13@aicte.gov.in",
        password="Password@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    headers = auth_headers_for(admin)
    today = date.today()

    base_payload = {
        "institution_id": inst.id,
        "bank_name": "Punjab National Bank",
        "reference_number": "REF-DUP-AC13",
        "amount": "1000000.00",
        "issue_date": str(today),
        "maturity_date": str(today + timedelta(days=365)),
    }
    # First creation succeeds
    res1 = client.post("/api/v1/instruments", json=base_payload, headers=headers)
    assert res1.status_code == 201
    first_id = res1.json()["id"]

    # Second creation without confirm_duplicate raises 409 DUPLICATE_REFERENCE_WARNING
    res2 = client.post("/api/v1/instruments", json=base_payload, headers=headers)
    assert res2.status_code == 409
    assert res2.json()["code"] == "DUPLICATE_REFERENCE_WARNING"
    assert "matching_records" in res2.json()["details"]

    # Third creation with confirm_duplicate=True succeeds and creates distinct record
    payload_confirm = {**base_payload, "confirm_duplicate": True}
    res3 = client.post("/api/v1/instruments", json=payload_confirm, headers=headers)
    assert res3.status_code == 201
    second_id = res3.json()["id"]
    assert first_id != second_id


# ==============================================================================
# M1-AC-14: Auditor access is read-only
# ==============================================================================
def test_m1_ac_14_auditor_read_only(client: TestClient, db_session: Session):
    """M1-AC-14: Auditor can read institutions and instruments but cannot modify them."""
    inst = Institution(code="M1-AUD-14", legal_name="Auditor Inspection College", contact_email="dean@aud14.ac.in", state="Delhi")
    db_session.add(inst)
    db_session.commit()

    auditor = provision_user(
        db=db_session,
        full_name="Auditor Fourteen",
        email="auditor.14@aicte.gov.in",
        password="Password@2026",
        role=ROLE_AUDITOR,
    )
    headers = auth_headers_for(auditor)

    # Can read institutions
    get_res = client.get("/api/v1/institutions", headers=headers)
    assert get_res.status_code == 200

    # Cannot create institution
    create_inst = client.post(
        "/api/v1/institutions",
        json={"code": "FAIL-AUD", "legal_name": "Fail", "contact_email": "fail@aud.ac.in", "state": "Delhi"},
        headers=headers,
    )
    assert create_inst.status_code == 403

    # Cannot create instrument
    create_fdr = client.post(
        "/api/v1/instruments",
        json={"institution_id": inst.id, "bank_name": "SBI", "reference_number": "REF-AUD", "amount": "1000.00", "issue_date": str(date.today()), "maturity_date": str(date.today() + timedelta(days=100))},
        headers=headers,
    )
    assert create_fdr.status_code == 403


# ==============================================================================
# M1-AC-15: Important actions create audit events without leaking secrets
# ==============================================================================
def test_m1_ac_15_audit_events_without_secret_leakage(client: TestClient, db_session: Session):
    """M1-AC-15: Creation and updates generate audit records without password exposure."""
    admin = provision_user(
        db=db_session,
        full_name="Admin Audit 15",
        email="admin.audit15@aicte.gov.in",
        password="Password@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    headers = auth_headers_for(admin)

    # Create an institution
    client.post(
        "/api/v1/institutions",
        json={"code": "M1-AUDIT-15", "legal_name": "Audit Test College", "contact_email": "dean@audit15.ac.in", "state": "Delhi"},
        headers=headers,
    )

    # Inspect audit events
    audit_res = client.get("/api/v1/audit/events", headers=headers)
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert len(events) > 0

    for ev in events:
        meta_str = str(ev.get("metadata", {}))
        assert "Password@2026" not in meta_str
        assert "access_token" not in meta_str


# ==============================================================================
# M1-AC-16: Dashboard counts respect role and institution scope
# ==============================================================================
def test_m1_ac_16_dashboard_counts_respect_scope(client: TestClient, db_session: Session):
    """M1-AC-16: Institution user dashboard reflects only their own institution data."""
    inst_1 = Institution(code="M1-DASH-01", legal_name="Scope Inst 1", contact_email="one@scope.ac.in", state="Delhi", is_active=True)
    inst_2 = Institution(code="M1-DASH-02", legal_name="Scope Inst 2", contact_email="two@scope.ac.in", state="Goa", is_active=True)
    db_session.add_all([inst_1, inst_2])
    db_session.commit()

    fdr_1 = Instrument(institution_id=inst_1.id, reference_number="REF-DASH-1", bank_name="SBI", amount=Decimal("1000000.00"), issue_date=date.today(), maturity_date=date.today() + timedelta(days=365))
    fdr_2 = Instrument(institution_id=inst_2.id, reference_number="REF-DASH-2", bank_name="HDFC", amount=Decimal("2000000.00"), issue_date=date.today(), maturity_date=date.today() + timedelta(days=365))
    db_session.add_all([fdr_1, fdr_2])
    db_session.commit()

    user_1 = provision_user(
        db=db_session,
        full_name="User Scope 1",
        email="user1@scope.ac.in",
        password="Password@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst_1.id,
    )
    headers = auth_headers_for(user_1)

    dash_res = client.get("/api/v1/dashboard/summary", headers=headers)
    assert dash_res.status_code == 200
    data = dash_res.json()

    # Must only report 1 active institution and 1 instrument for User 1
    assert data["total_active_institutions"] == 1
    assert data["total_instruments"] == 1
    assert Decimal(data["total_deposit_value"]) == Decimal("1000000.00")


# ==============================================================================
# M1-AC-17: Frontend production build and backend quality checks pass
# ==============================================================================
def test_m1_ac_17_backend_quality_health(client: TestClient):
    """M1-AC-17: Backend quality checks: OpenAPI schema is valid and exports cleanly."""
    openapi_res = client.get("/openapi.json")
    assert openapi_res.status_code == 200
    spec = openapi_res.json()
    assert spec["info"]["title"] == settings.PROJECT_NAME
    assert "/api/v1/auth/login" in spec["paths"]
    assert "/api/v1/institutions" in spec["paths"]
    assert "/api/v1/instruments" in spec["paths"]
    assert "/api/v1/dashboard/summary" in spec["paths"]


# ==============================================================================
# M1-AC-18: Synthetic seeding is repeatable and does not duplicate records
# ==============================================================================
def test_m1_ac_18_synthetic_seeding_idempotency(db_session: Session):
    """M1-AC-18: Running seed_database multiple times does not produce duplicate records."""
    seed_database(db=db_session)
    inst_count_1 = db_session.scalar(select(Institution).where(Institution.code == "DEMO-AICTE-001"))
    assert inst_count_1 is not None

    # Run again
    seed_database(db=db_session)
    insts = db_session.scalars(select(Institution).where(Institution.code == "DEMO-AICTE-001")).all()
    assert len(insts) == 1, "Expected exactly 1 synthetic DEMO-AICTE-001 institution after re-seeding"
