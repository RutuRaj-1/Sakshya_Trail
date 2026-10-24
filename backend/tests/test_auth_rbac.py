"""
Test Suite: Identity, Authentication, RBAC, and Database Foundation
Implements all 14 required automated test cases specified in Prompt 2.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.audit.models import AuditEvent
from app.modules.auth.service import provision_user, change_user_password
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    sanitize_dict,
)
from app.common.exceptions import AppException, ConflictException


@pytest.fixture
def sample_institution(db_session: Session) -> Institution:
    inst = Institution(
        code="1-TEST-INST-01",
        legal_name="National Engineering College",
        display_name="NEC Delhi",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar Office",
        contact_email="registrar@nec.ac.in",
        contact_phone="+91-11-20001111",
        address_line1="Campus Lane 1",
        city="New Delhi",
        state="Delhi",
        postal_code="110001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


# ------------------------------------------------------------------------------
# 1. Successful Login
# ------------------------------------------------------------------------------
def test_successful_login(client: TestClient, db_session: Session):
    provision_user(
        db=db_session,
        full_name="AICTE Master Admin",
        email="master.admin@aicte-india.org",
        password="SecurePassword@2026",
        role=ROLE_SYSTEM_ADMIN,
    )

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "master.admin@aicte-india.org", "password": "SecurePassword@2026"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["user"]["email"] == "master.admin@aicte-india.org"
    assert "access_token" in data
    # Check HttpOnly cookie was set
    assert "fdr_session" in res.cookies


# ------------------------------------------------------------------------------
# 2. Invalid Password
# ------------------------------------------------------------------------------
def test_invalid_password(client: TestClient, db_session: Session):
    provision_user(
        db=db_session,
        full_name="Officer Ramesh",
        email="ramesh@aicte-india.org",
        password="CorrectPassword@2026",
        role=ROLE_SCRUTINY_OFFICER,
    )

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "ramesh@aicte-india.org", "password": "WrongPassword!999"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_CREDENTIALS"


# ------------------------------------------------------------------------------
# 3. Unknown User
# ------------------------------------------------------------------------------
def test_unknown_user(client: TestClient):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent.user@aicte-india.org", "password": "SomePassword123"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "INVALID_CREDENTIALS"


# ------------------------------------------------------------------------------
# 4. Inactive Account
# ------------------------------------------------------------------------------
def test_inactive_account(client: TestClient, db_session: Session):
    user = provision_user(
        db=db_session,
        full_name="Deactivated Officer",
        email="deactivated@aicte-india.org",
        password="MySecretPassword@2026",
        role=ROLE_SCRUTINY_OFFICER,
    )
    user.is_active = False
    db_session.commit()

    res = client.post(
        "/api/v1/auth/login",
        json={"email": "deactivated@aicte-india.org", "password": "MySecretPassword@2026"},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "INACTIVE_ACCOUNT"


# ------------------------------------------------------------------------------
# 5. Logout and Session Invalidation/Clearing
# ------------------------------------------------------------------------------
def test_logout_and_session_clearing(client: TestClient, db_session: Session):
    provision_user(
        db=db_session,
        full_name="Auditor Sunita",
        email="sunita.auditor@aicte-india.org",
        password="AuditorSecret@2026",
        role=ROLE_AUDITOR,
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "sunita.auditor@aicte-india.org", "password": "AuditorSecret@2026"},
    )
    assert login_res.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Calling /me without token should now fail
    client.cookies.clear()
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 401


# ------------------------------------------------------------------------------
# 6. Current-User Endpoint (/auth/me)
# ------------------------------------------------------------------------------
def test_current_user_endpoint(client: TestClient, db_session: Session):
    provision_user(
        db=db_session,
        full_name="Dr. H. Patel",
        email="dr.patel@aicte-india.org",
        password="PatelPassword@2026",
        role=ROLE_SYSTEM_ADMIN,
    )

    # Login to set cookie
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "dr.patel@aicte-india.org", "password": "PatelPassword@2026"},
    )
    assert login_res.status_code == 200

    # Call /me
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == "dr.patel@aicte-india.org"
    assert data["role"] == ROLE_SYSTEM_ADMIN
    assert data["is_active"] is True


# ------------------------------------------------------------------------------
# 7. Password Change
# ------------------------------------------------------------------------------
def test_password_change(client: TestClient, db_session: Session):
    provision_user(
        db=db_session,
        full_name="Rotator User",
        email="rotator@aicte-india.org",
        password="OldPassword@2026",
        role=ROLE_SYSTEM_ADMIN,
    )

    client.post(
        "/api/v1/auth/login",
        json={"email": "rotator@aicte-india.org", "password": "OldPassword@2026"},
    )

    # Change password
    change_res = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "OldPassword@2026",
            "new_password": "NewBrandPassword@2026",
            "confirm_new_password": "NewBrandPassword@2026",
        },
    )
    assert change_res.status_code == 200

    # Old password no longer works
    client.cookies.clear()
    old_res = client.post(
        "/api/v1/auth/login",
        json={"email": "rotator@aicte-india.org", "password": "OldPassword@2026"},
    )
    assert old_res.status_code == 401

    # New password works
    new_res = client.post(
        "/api/v1/auth/login",
        json={"email": "rotator@aicte-india.org", "password": "NewBrandPassword@2026"},
    )
    assert new_res.status_code == 200


# ------------------------------------------------------------------------------
# 8. Invalid Role Assignment
# ------------------------------------------------------------------------------
def test_invalid_role_assignment(db_session: Session):
    with pytest.raises(AppException) as excinfo:
        provision_user(
            db=db_session,
            full_name="Bad Role User",
            email="bad.role@aicte-india.org",
            password="SomePassword@2026",
            role="UNAUTHORIZED_SUPER_USER",
        )
    assert excinfo.value.code == "INVALID_ROLE"


# ------------------------------------------------------------------------------
# 9. Institution User Without Institution Association
# ------------------------------------------------------------------------------
def test_institution_user_without_institution(db_session: Session, sample_institution: Institution):
    # Missing institution
    with pytest.raises(AppException) as excinfo:
        provision_user(
            db=db_session,
            full_name="Nodal Officer",
            email="nodal.alone@institute.edu",
            password="NodalPassword@2026",
            role=ROLE_INSTITUTION_USER,
            institution_id=None,
        )
    assert excinfo.value.code == "INSTITUTION_ASSOCIATION_REQUIRED"

    # Internal user assigned institution by accident should be blocked
    with pytest.raises(AppException) as excinfo2:
        provision_user(
            db=db_session,
            full_name="Admin With Inst",
            email="admin.bypass@aicte-india.org",
            password="AdminPassword@2026",
            role=ROLE_SYSTEM_ADMIN,
            institution_id=sample_institution.id,
        )
    assert excinfo2.value.code == "INTERNAL_ROLE_CANNOT_HAVE_INSTITUTION"


# ------------------------------------------------------------------------------
# 10. Unauthorized Role Access
# ------------------------------------------------------------------------------
def test_unauthorized_role_access(client: TestClient, db_session: Session, sample_institution: Institution):
    # Create Institution User
    provision_user(
        db=db_session,
        full_name="Inst Nodal",
        email="nodal.user@college.edu",
        password="CollegePassword@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=sample_institution.id,
    )

    client.post(
        "/api/v1/auth/login",
        json={"email": "nodal.user@college.edu", "password": "CollegePassword@2026"},
    )

    # Attempt to provision users (restricted to SYSTEM_ADMIN)
    res = client.post(
        "/api/v1/auth/users",
        json={
            "full_name": "Injected User",
            "email": "injected@hack.com",
            "password": "Password@123",
            "role": "SYSTEM_ADMIN",
        },
    )
    assert res.status_code == 403


# ------------------------------------------------------------------------------
# 11. CORS and CSRF/Origin Behavior Where Configured
# ------------------------------------------------------------------------------
def test_cors_and_csrf_origin_behavior(client: TestClient, db_session: Session):
    provision_user(
        db=db_session,
        full_name="Cors Admin",
        email="cors.admin@aicte-india.org",
        password="CorsAdminPassword@2026",
        role=ROLE_SYSTEM_ADMIN,
    )

    # Malicious Origin header on state-changing request
    res_bad = client.post(
        "/api/v1/auth/login",
        json={"email": "cors.admin@aicte-india.org", "password": "CorsAdminPassword@2026"},
        headers={"Origin": "https://evil-phishing-site.com"},
    )
    assert res_bad.status_code == 403

    # Permitted Origin header
    res_good = client.post(
        "/api/v1/auth/login",
        json={"email": "cors.admin@aicte-india.org", "password": "CorsAdminPassword@2026"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert res_good.status_code == 200


# ------------------------------------------------------------------------------
# 12. Password Hashes Are Not Plaintext (Argon2)
# ------------------------------------------------------------------------------
def test_password_hashes_are_not_plaintext(db_session: Session):
    raw_secret = "VeryComplexSecretPassword@2026!"
    user = provision_user(
        db=db_session,
        full_name="Argon User",
        email="argon.user@aicte-india.org",
        password=raw_secret,
        role=ROLE_SCRUTINY_OFFICER,
    )

    assert user.password_hash != raw_secret
    assert raw_secret not in user.password_hash
    assert user.password_hash.startswith("$argon2id$")


# ------------------------------------------------------------------------------
# 13. Administrator Bootstrap Refuses Duplicate Accounts
# ------------------------------------------------------------------------------
def test_administrator_bootstrap_refuses_duplicate_accounts(db_session: Session):
    provision_user(
        db=db_session,
        full_name="First Admin",
        email="super.admin@aicte-india.org",
        password="InitialPassword@2026",
        role=ROLE_SYSTEM_ADMIN,
    )

    with pytest.raises(ConflictException):
        provision_user(
            db=db_session,
            full_name="Second Duplicate Admin",
            email="super.admin@aicte-india.org",
            password="AnotherPassword@2026",
            role=ROLE_SYSTEM_ADMIN,
        )


# ------------------------------------------------------------------------------
# 14. Audit Entries Do Not Contain Passwords or Tokens
# ------------------------------------------------------------------------------
def test_audit_entries_do_not_contain_passwords_or_tokens(client: TestClient, db_session: Session):
    secret_pw = "SensitiveAuditPassword@2026"
    provision_user(
        db=db_session,
        full_name="Audit Test User",
        email="audit.check@aicte-india.org",
        password=secret_pw,
        role=ROLE_SYSTEM_ADMIN,
    )

    client.post(
        "/api/v1/auth/login",
        json={"email": "audit.check@aicte-india.org", "password": secret_pw},
    )

    # Query all audit events in DB
    audit_events = db_session.scalars(select(AuditEvent)).all()
    assert len(audit_events) > 0

    for event in audit_events:
        if event.metadata_json:
            assert secret_pw not in event.metadata_json
            assert "token" not in event.metadata_json.lower() or "[REDACTED]" in event.metadata_json
            assert "password" not in event.metadata_json.lower() or "[REDACTED]" in event.metadata_json

    # Test sanitize_dict helper
    dirty_dict = {
        "user_email": "test@aicte-india.org",
        "password": "ClearTextPassword123",
        "access_token": "eyJhbGciOi...",
        "nested": {"secret_key": "mysecret", "action": "LOGIN"},
    }
    clean = sanitize_dict(dirty_dict)
    assert clean["password"] == "[REDACTED]"
    assert clean["access_token"] == "[REDACTED]"
    assert clean["nested"]["secret_key"] == "[REDACTED]"
    assert clean["nested"]["action"] == "LOGIN"
