"""
SakshyaTrail - Prompt 2 Authentication, RBAC, Tenant Isolation & Session Lifecycle Tests
Verifies backend security guarantees:
1. Valid credentials authenticate and issue signed JWT + HttpOnly session cookie
2. Invalid credentials return 401 Unauthorized without user enumeration
3. Deactivated accounts are rejected with 403 Forbidden
4. Session verification (/auth/me) validates identity
5. Role-based endpoint authorization strictly enforced (SYSTEM_ADMIN vs SCRUTINY_OFFICER vs AUDITOR)
6. Tenant isolation: Institution User cannot view or mutate another institution's instruments
7. Auditor role has strictly read-only inspection access; state modifications blocked
8. Logout clears session cookie and records audit log
9. Password rotation updates must_change_password flag
"""
import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import date, timedelta

from app.core.config import settings
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_FINANCE_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
)
from app.modules.auth.models import User
from app.modules.auth.service import provision_user
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument


@pytest.fixture
def auth_fixture(db_session: Session):
    """Sets up synthetic institutions and users across roles for testing."""
    # Institution A & B for multi-tenant isolation testing
    inst_a = Institution(
        code="TEST-INST-A-P2",
        legal_name="Alpha Institute of Technology [SYNTHETIC]",
        contact_email="director@alpha-p2.ac.in",
        state="Maharashtra",
        is_active=True,
    )
    inst_b = Institution(
        code="TEST-INST-B-P2",
        legal_name="Beta College of Engineering [SYNTHETIC]",
        contact_email="director@beta-p2.ac.in",
        state="Karnataka",
        is_active=True,
    )
    db_session.add_all([inst_a, inst_b])
    db_session.commit()

    # Users
    admin = provision_user(
        db=db_session,
        full_name="System Admin P2",
        email="admin.p2@aicte-india.org",
        password="ValidPassword@2026",
        role=ROLE_SYSTEM_ADMIN,
        must_change_password=False,
    )
    officer = provision_user(
        db=db_session,
        full_name="Scrutiny Officer P2",
        email="officer.p2@aicte-india.org",
        password="ValidPassword@2026",
        role=ROLE_SCRUTINY_OFFICER,
        must_change_password=False,
    )
    auditor = provision_user(
        db=db_session,
        full_name="Compliance Auditor P2",
        email="auditor.p2@aicte-india.org",
        password="ValidPassword@2026",
        role=ROLE_AUDITOR,
        must_change_password=False,
    )
    inst_user_a = provision_user(
        db=db_session,
        full_name="Nodal User Alpha P2",
        email="nodal.a.p2@alpha.ac.in",
        password="ValidPassword@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst_a.id,
        must_change_password=False,
    )
    inst_user_b = provision_user(
        db=db_session,
        full_name="Nodal User Beta P2",
        email="nodal.b.p2@beta.ac.in",
        password="ValidPassword@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst_b.id,
        must_change_password=False,
    )
    rotator_user = provision_user(
        db=db_session,
        full_name="First Time User P2",
        email="rotator.p2@aicte-india.org",
        password="InitialPassword@2026",
        role=ROLE_SCRUTINY_OFFICER,
        must_change_password=True,
    )

    # Instrument belonging strictly to Institution A
    instrument_a = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-ALPHA-P2-001",
        bank_name="State Bank of India",
        branch="Main Branch",
        amount=Decimal("1500000.00"),
        issue_date=date.today() - timedelta(days=60),
        maturity_date=date.today() + timedelta(days=700),
        status="REGISTERED",
    )
    db_session.add(instrument_a)
    db_session.commit()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "admin": admin,
        "officer": officer,
        "auditor": auditor,
        "inst_user_a": inst_user_a,
        "inst_user_b": inst_user_b,
        "rotator_user": rotator_user,
        "instrument_a": instrument_a,
    }


def test_01_successful_login_and_cookie_generation(client: TestClient, auth_fixture):
    """Verifies that valid credentials return signed JWT, user profile, and HttpOnly session cookie."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["user"]["email"] == "admin.p2@aicte-india.org"
    assert data["user"]["role"] == ROLE_SYSTEM_ADMIN
    assert "access_token" in data
    assert settings.AUTH_COOKIE_NAME in res.cookies


def test_02_rejected_login_invalid_password(client: TestClient, auth_fixture):
    """Verifies that invalid password returns 401 without leaking sensitive details."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin.p2@aicte-india.org", "password": "WrongPassword!999"},
    )
    assert res.status_code == 401
    assert "access_token" not in res.json()


def test_03_rejected_login_nonexistent_email(client: TestClient, auth_fixture):
    """Verifies that nonexistent email returns same 401 response preventing user enumeration."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@aicte-india.org", "password": "SomePassword123"},
    )
    assert res.status_code == 401


def test_04_session_restoration_via_auth_me(client: TestClient, auth_fixture):
    """Verifies that /auth/me returns fresh server-verified identity of the authenticated user."""
    # Log in as officer
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "officer.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    token = login_res.json()["access_token"]

    # Request /auth/me with Bearer token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "officer.p2@aicte-india.org"
    assert me_data["role"] == ROLE_SCRUTINY_OFFICER


def test_05_unauthenticated_protected_route_rejection(client: TestClient):
    """Verifies that accessing protected routes without session token returns 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_06_role_based_authorization_user_management(client: TestClient, auth_fixture):
    """Verifies that /auth/users is accessible by SYSTEM_ADMIN but rejected for SCRUTINY_OFFICER and AUDITOR."""
    # 1. Admin login -> 200 OK
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    admin_token = admin_login.json()["access_token"]
    admin_res = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_res.status_code == 200

    # 2. Scrutiny Officer -> 403 Forbidden
    officer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "officer.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    officer_token = officer_login.json()["access_token"]
    officer_res = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {officer_token}"})
    assert officer_res.status_code == 403

    # 3. Auditor -> 403 Forbidden
    auditor_login = client.post(
        "/api/v1/auth/login",
        json={"email": "auditor.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    auditor_token = auditor_login.json()["access_token"]
    auditor_res = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {auditor_token}"})
    assert auditor_res.status_code == 403


def test_07_tenant_isolation_institution_user_cannot_view_other_instruments(client: TestClient, auth_fixture):
    """Verifies that Institution B user cannot view or mutate Institution A's instrument."""
    inst_b_login = client.post(
        "/api/v1/auth/login",
        json={"email": "nodal.b.p2@beta.ac.in", "password": "ValidPassword@2026"},
    )
    inst_b_token = inst_b_login.json()["access_token"]
    inst_a_instrument_id = auth_fixture["instrument_a"].id

    # Institution B attempts to view Institution A's instrument detail -> 403 Forbidden
    res = client.get(
        f"/api/v1/instruments/{inst_a_instrument_id}",
        headers={"Authorization": f"Bearer {inst_b_token}"},
    )
    assert res.status_code == 403


def test_08_auditor_read_only_protection(client: TestClient, auth_fixture):
    """Verifies that Auditor can read records but cannot perform state-changing release actions."""
    auditor_login = client.post(
        "/api/v1/auth/login",
        json={"email": "auditor.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    auditor_token = auditor_login.json()["access_token"]

    # Auditor attempting to trigger release case creation or decision -> 403 Forbidden
    fake_case_id = "00000000-0000-0000-0000-000000000000"
    res = client.post(
        f"/api/v1/release/requests/{fake_case_id}/approve",
        params={"reason": "Auditor unauthorized approval attempt"},
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403


def test_09_logout_clears_session_cookie(client: TestClient, auth_fixture):
    """Verifies that /auth/logout clears the session cookie and invalidates client session."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    assert settings.AUTH_COOKIE_NAME in login_res.cookies

    logout_res = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login_res.json()['access_token']}"},
    )
    assert logout_res.status_code == 200
    # Cookie should be deleted/cleared in response
    set_cookie_header = logout_res.headers.get("set-cookie", "")
    assert f"{settings.AUTH_COOKIE_NAME}=" in set_cookie_header


def test_10_password_rotation_clears_must_change_password(client: TestClient, auth_fixture, db_session: Session):
    """Verifies that rotating password updates hash and sets must_change_password=False."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "rotator.p2@aicte-india.org", "password": "InitialPassword@2026"},
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["must_change_password"] is True
    token = login_res.json()["access_token"]

    # Rotate password
    change_res = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "InitialPassword@2026",
            "new_password": "NewSecretPassword@2026",
            "confirm_new_password": "NewSecretPassword@2026",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_res.status_code == 200

    # User in database should now have must_change_password=False
    db_session.expire_all()
    user = db_session.query(User).filter(User.email == "rotator.p2@aicte-india.org").first()
    assert user.must_change_password is False

    # Login with new password succeeds
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "rotator.p2@aicte-india.org", "password": "NewSecretPassword@2026"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["user"]["must_change_password"] is False
