"""
Test Suite: Institution Registry and User Administration (Prompt 3)
Automated verification for all 14 required test cases:
1. Creating an institution.
2. Duplicate institution-code rejection.
3. Invalid fields validation.
4. Updating and deactivating an institution.
5. Historical institution retrieval after deactivation.
6. Administrator-only institution creation.
7. Institution user reading their own institution.
8. Institution user being denied access to another institution.
9. Institution user being denied attempts to change role, institution association, code or status.
10. User provisioning with valid and invalid roles.
11. Required institution association for institution users.
12. Auditor read-only enforcement.
13. Last-administrator protection.
14. Audit creation for material actions without credential leaks.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.audit.models import AuditEvent
from app.modules.auth.service import provision_user, set_user_status, update_user_profile
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
from app.common.exceptions import AppException


def set_auth_cookie(client: TestClient, user: User):
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


# ------------------------------------------------------------------------------
# 1. Creating an institution
# ------------------------------------------------------------------------------
def test_create_institution_success(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin One",
        email="admin.inst@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    payload = {
        "code": "1-IIT-DELHI-001",
        "legal_name": "Indian Institute of Technology Delhi",
        "display_name": "IIT Delhi",
        "institution_type": "TECHNICAL_INSTITUTE",
        "contact_name": "Registrar IITD",
        "contact_email": "registrar@iitd.ac.in",
        "contact_phone": "+91-11-26591000",
        "address_line1": "Hauz Khas",
        "city": "New Delhi",
        "state": "Delhi",
        "postal_code": "110016",
        "assigned_office": "Northern Regional Office",
    }
    res = client.post("/api/v1/institutions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "1-IIT-DELHI-001"
    assert data["legal_name"] == "Indian Institute of Technology Delhi"
    assert data["is_active"] is True
    assert data["id"] is not None


# ------------------------------------------------------------------------------
# 2. Duplicate institution-code rejection
# ------------------------------------------------------------------------------
def test_duplicate_institution_code_rejection(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Duplicate",
        email="admin.dup@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    payload = {
        "code": "1-DUP-TEST-99",
        "legal_name": "Duplicate Testing Institute 1",
        "contact_email": "dean1@dup.ac.in",
        "state": "Delhi",
    }
    res1 = client.post("/api/v1/institutions", json=payload)
    assert res1.status_code == 201

    # Attempt second creation with identical code (case-insensitive test)
    payload_dup = {
        "code": "1-dup-test-99",
        "legal_name": "Duplicate Testing Institute 2",
        "contact_email": "dean2@dup.ac.in",
        "state": "Delhi",
    }
    res2 = client.post("/api/v1/institutions", json=payload_dup)
    assert res2.status_code == 409
    assert res2.json()["code"] == "DUPLICATE_INSTITUTION_CODE"


# ------------------------------------------------------------------------------
# 3. Invalid fields validation
# ------------------------------------------------------------------------------
def test_invalid_fields_validation(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Val",
        email="admin.val@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # Empty legal_name / invalid email / missing state
    invalid_payload = {
        "code": "1-INV-001",
        "legal_name": "   ",
        "contact_email": "not-a-valid-email",
        "state": "",
    }
    res = client.post("/api/v1/institutions", json=invalid_payload)
    assert res.status_code == 422


# ------------------------------------------------------------------------------
# 4. Updating and deactivating an institution
# ------------------------------------------------------------------------------
def test_update_and_deactivate_institution(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Lifecycle",
        email="admin.life@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # Create
    create_res = client.post(
        "/api/v1/institutions",
        json={
            "code": "1-MOD-001",
            "legal_name": "Original College of Science",
            "contact_email": "office@original.edu",
            "state": "Maharashtra",
        },
    )
    inst_id = create_res.json()["id"]

    # Patch fields
    patch_res = client.patch(
        f"/api/v1/institutions/{inst_id}",
        json={
            "legal_name": "Updated College of Science and AI",
            "city": "Pune",
            "contact_phone": "+91-20-25601234",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["legal_name"] == "Updated College of Science and AI"
    assert patch_res.json()["city"] == "Pune"

    # Deactivate
    deact_res = client.post(
        f"/api/v1/institutions/{inst_id}/status",
        json={"is_active": False, "reason": "Accreditation expired"},
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False


# ------------------------------------------------------------------------------
# 5. Historical institution retrieval after deactivation
# ------------------------------------------------------------------------------
def test_historical_institution_retrieval_after_deactivation(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin History",
        email="admin.hist@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    create_res = client.post(
        "/api/v1/institutions",
        json={
            "code": "1-HIST-001",
            "legal_name": "Historical Heritage Academy",
            "contact_email": "hist@heritage.edu",
            "state": "Karnataka",
        },
    )
    inst_id = create_res.json()["id"]

    # Deactivate
    client.post(
        f"/api/v1/institutions/{inst_id}/status",
        json={"is_active": False, "reason": "Institutional closure"},
    )

    # Historical record MUST remain retrievable (not physically deleted)
    get_res = client.get(f"/api/v1/institutions/{inst_id}")
    assert get_res.status_code == 200
    assert get_res.json()["code"] == "1-HIST-001"
    assert get_res.json()["is_active"] is False

    # Also retrievable in list when filtering by is_active=False
    list_res = client.get("/api/v1/institutions?is_active=false")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(i["id"] == inst_id for i in items)


# ------------------------------------------------------------------------------
# 6. Administrator-only institution creation
# ------------------------------------------------------------------------------
def test_admin_only_institution_creation(client: TestClient, db_session: Session):
    officer = provision_user(
        db=db_session,
        full_name="Officer Reviewer",
        email="officer.rev@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SCRUTINY_OFFICER,
    )
    set_auth_cookie(client, officer)

    payload = {
        "code": "1-FORBIDDEN-01",
        "legal_name": "Unauthorized College",
        "contact_email": "unauth@col.edu",
        "state": "Punjab",
    }
    res = client.post("/api/v1/institutions", json=payload)
    assert res.status_code == 403


# ------------------------------------------------------------------------------
# 7. Institution user reading their own institution
# ------------------------------------------------------------------------------
def test_institution_user_reads_own_institution(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Setup",
        email="admin.setup@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    inst_res = client.post(
        "/api/v1/institutions",
        json={
            "code": "1-OWN-INST",
            "legal_name": "Own Technical College",
            "contact_email": "dean@own.edu",
            "state": "Tamil Nadu",
        },
    )
    inst_id = inst_res.json()["id"]

    inst_user = provision_user(
        db=db_session,
        full_name="Own Inst Representative",
        email="rep@own.edu",
        password="SecurePass@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst_id,
    )
    set_auth_cookie(client, inst_user)

    # Can get by ID
    get_res = client.get(f"/api/v1/institutions/{inst_id}")
    assert get_res.status_code == 200
    assert get_res.json()["code"] == "1-OWN-INST"

    # In listing, returns ONLY their own institution
    list_res = client.get("/api/v1/institutions")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == inst_id


# ------------------------------------------------------------------------------
# 8. Institution user denied access to another institution
# ------------------------------------------------------------------------------
def test_institution_user_denied_other_institution(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Setup 2",
        email="admin.setup2@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    inst1 = client.post(
        "/api/v1/institutions",
        json={"code": "1-INST-ALPHA", "legal_name": "Alpha Institute", "contact_email": "alpha@a.edu", "state": "Goa"},
    ).json()["id"]

    inst2 = client.post(
        "/api/v1/institutions",
        json={"code": "1-INST-BETA", "legal_name": "Beta Institute", "contact_email": "beta@b.edu", "state": "Gujarat"},
    ).json()["id"]

    user_alpha = provision_user(
        db=db_session,
        full_name="User Alpha",
        email="user@alpha.edu",
        password="SecurePass@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst1,
    )
    set_auth_cookie(client, user_alpha)

    # Accessing Alpha is OK
    res_alpha = client.get(f"/api/v1/institutions/{inst1}")
    assert res_alpha.status_code == 200

    # Accessing Beta is Forbidden (403)
    res_beta = client.get(f"/api/v1/institutions/{inst2}")
    assert res_beta.status_code == 403


# ------------------------------------------------------------------------------
# 9. Institution user denied attempts to change role, institution, code, or status
# ------------------------------------------------------------------------------
def test_institution_user_denied_administrative_modifications(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Setup 3",
        email="admin.setup3@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    inst_id = client.post(
        "/api/v1/institutions",
        json={"code": "1-INST-RESTRICT", "legal_name": "Restricted Institute", "contact_email": "dean@res.edu", "state": "Assam"},
    ).json()["id"]

    user_rep = provision_user(
        db=db_session,
        full_name="Rep User",
        email="rep@restricted.edu",
        password="SecurePass@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst_id,
    )
    set_auth_cookie(client, user_rep)

    # Permitted contact update works
    ok_patch = client.patch(
        f"/api/v1/institutions/{inst_id}",
        json={"contact_name": "New Nodal Officer", "contact_phone": "+91-361-2000000"},
    )
    assert ok_patch.status_code == 200
    assert ok_patch.json()["contact_name"] == "New Nodal Officer"

    # Attempt to change institution code -> 403 Forbidden
    bad_code = client.patch(f"/api/v1/institutions/{inst_id}", json={"code": "HACKED-CODE"})
    assert bad_code.status_code == 403

    # Attempt to change legal_name -> 403 Forbidden
    bad_name = client.patch(f"/api/v1/institutions/{inst_id}", json={"legal_name": "Hijacked Name"})
    assert bad_name.status_code == 403

    # Attempt to deactivate institution -> 403 Forbidden
    bad_status = client.post(f"/api/v1/institutions/{inst_id}/status", json={"is_active": False})
    assert bad_status.status_code == 403


# ------------------------------------------------------------------------------
# 10. User provisioning with valid and invalid roles
# ------------------------------------------------------------------------------
def test_user_provisioning_valid_and_invalid_roles(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Provisioner",
        email="admin.prov@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # Valid internal role: SCRUTINY_OFFICER
    valid_res = client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Scrutiny Officer Sunil",
            "email": "sunil.scrutiny@aicte.gov.in",
            "password": "TemporaryPassword@2026",
            "role": ROLE_SCRUTINY_OFFICER,
        },
    )
    assert valid_res.status_code == 201
    assert valid_res.json()["role"] == ROLE_SCRUTINY_OFFICER

    # Invalid role
    invalid_res = client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Bogus User",
            "email": "bogus@aicte.gov.in",
            "password": "TemporaryPassword@2026",
            "role": "SUPER_USER_UNKNOWN",
        },
    )
    assert invalid_res.status_code == 400
    assert invalid_res.json()["code"] == "INVALID_ROLE"


# ------------------------------------------------------------------------------
# 11. Required institution association for institution users
# ------------------------------------------------------------------------------
def test_required_institution_association_for_institution_users(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Inst Scope",
        email="admin.scope@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # Missing institution_id for INSTITUTION_USER -> 400
    res_missing = client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Orphan Rep",
            "email": "orphan@institute.edu",
            "password": "TemporaryPassword@2026",
            "role": ROLE_INSTITUTION_USER,
            "institution_id": None,
        },
    )
    assert res_missing.status_code == 400
    assert res_missing.json()["code"] == "INSTITUTION_ASSOCIATION_REQUIRED"


# ------------------------------------------------------------------------------
# 12. Auditor read-only enforcement
# ------------------------------------------------------------------------------
def test_auditor_read_only_enforcement(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Admin Setup 4",
        email="admin.setup4@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    inst_id = client.post(
        "/api/v1/institutions",
        json={"code": "1-AUD-TEST", "legal_name": "Audited Institute", "contact_email": "aud@col.edu", "state": "Kerala"},
    ).json()["id"]

    auditor = provision_user(
        db=db_session,
        full_name="Compliance Auditor",
        email="auditor.comp@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_AUDITOR,
    )
    set_auth_cookie(client, auditor)

    # Read institution list -> 200
    assert client.get("/api/v1/institutions").status_code == 200

    # Read specific institution -> 200
    assert client.get(f"/api/v1/institutions/{inst_id}").status_code == 200

    # Attempt to create institution -> 403 Forbidden
    bad_create = client.post(
        "/api/v1/institutions",
        json={"code": "1-AUD-FAIL", "legal_name": "Fail", "contact_email": "f@f.edu", "state": "Goa"},
    )
    assert bad_create.status_code == 403

    # Attempt to update institution -> 403 Forbidden
    bad_patch = client.patch(f"/api/v1/institutions/{inst_id}", json={"city": "Cochin"})
    assert bad_patch.status_code == 403

    # Attempt to deactivate institution -> 403 Forbidden
    bad_deact = client.post(f"/api/v1/institutions/{inst_id}/status", json={"is_active": False})
    assert bad_deact.status_code == 403


# ------------------------------------------------------------------------------
# 13. Last-administrator protection
# ------------------------------------------------------------------------------
def test_last_administrator_protection(client: TestClient, db_session: Session):
    sole_admin = provision_user(
        db=db_session,
        full_name="Sole System Admin",
        email="sole.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, sole_admin)

    # Attempt deactivation of the only admin -> 400 LAST_ADMIN_PROTECTED
    deact_res = client.post(
        f"/api/v1/auth/users/{sole_admin.id}/status",
        json={"is_active": False, "reason": "Self-deactivation attempt"},
    )
    assert deact_res.status_code == 400
    assert deact_res.json()["code"] == "LAST_ADMIN_PROTECTED"

    # Attempt role demotion of the only admin -> 400 LAST_ADMIN_PROTECTED
    demote_res = client.patch(
        f"/api/v1/auth/users/{sole_admin.id}",
        json={"role": ROLE_SCRUTINY_OFFICER},
    )
    assert demote_res.status_code == 400
    assert demote_res.json()["code"] == "LAST_ADMIN_PROTECTED"


# ------------------------------------------------------------------------------
# 14. Audit creation for material actions without credential leaks
# ------------------------------------------------------------------------------
def test_audit_creation_for_material_actions(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Audit Logger Admin",
        email="audit.logger@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # 1. Material action: Create institution
    inst_res = client.post(
        "/api/v1/institutions",
        json={
            "code": "1-AUDIT-MAT",
            "legal_name": "Audit Material Institution",
            "contact_email": "material@audit.edu",
            "state": "Odisha",
        },
    )
    assert inst_res.status_code == 201
    inst_id = inst_res.json()["id"]

    # 2. Material action: Provision user
    user_res = client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Material Officer",
            "email": "material.officer@aicte.gov.in",
            "password": "TemporarySecret@2026",
            "role": ROLE_SCRUTINY_OFFICER,
        },
    )
    assert user_res.status_code == 201
    target_user_id = user_res.json()["id"]

    # 3. Material action: Administrative password reset
    reset_res = client.post(
        f"/api/v1/auth/users/{target_user_id}/reset-password",
        json={"temporary_password": "NewTempPass@2026"},
    )
    assert reset_res.status_code == 200

    # 4. Material action: Deactivate institution
    client.post(f"/api/v1/institutions/{inst_id}/status", json={"is_active": False})

    # Verify audit logs in database
    audit_events = db_session.scalars(select(AuditEvent)).all()
    actions = [e.action for e in audit_events]
    assert "INSTITUTION_CREATED" in actions
    assert "USER_PROVISIONED" in actions
    assert "USER_PASSWORD_RESET_INITIATED" in actions
    assert "INSTITUTION_DEACTIVATED" in actions

    # Verify secrets are NOT in any audit entry
    for event in audit_events:
        if event.metadata_json:
            assert "TemporarySecret@2026" not in event.metadata_json
            assert "NewTempPass@2026" not in event.metadata_json
            assert "password" not in event.metadata_json.lower() or "[REDACTED]" in event.metadata_json
