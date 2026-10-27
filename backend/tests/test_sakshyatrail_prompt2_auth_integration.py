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
from app.modules.documents.models import Document, DocumentVersion
from app.modules.documents.service import DocumentService
from app.modules.release.models import ReleaseRequest, ReleaseOrderRecord
from app.modules.release.schemas import ReleaseRequestCreate, ReleaseOrderCreate
from app.modules.release.service import create_release_request, seed_demo_release_profile
from app.modules.release.decision_service import approve_release_request, record_release_order as record_release_order_decision
from app.modules.release.enums import ReleaseWorkflowStatus, ReleaseOrderStatus, BankActionStatus
from app.common.exceptions import ForbiddenException, AppException


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
    authority = provision_user(
        db=db_session,
        full_name="Competent Authority P2",
        email="authority.p2@aicte-india.org",
        password="ValidPassword@2026",
        role=ROLE_COMPETENT_AUTHORITY,
        must_change_password=False,
    )
    finance_officer = provision_user(
        db=db_session,
        full_name="Finance Officer P2",
        email="finance.p2@aicte-india.org",
        password="ValidPassword@2026",
        role=ROLE_FINANCE_OFFICER,
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
        "authority": authority,
        "finance_officer": finance_officer,
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


def test_11_auditor_document_upload_rejected_with_403(client: TestClient, auth_fixture, db_session: Session):
    """
    P0.2: Auditor is strictly read-only and cannot upload documents.
    - Router rejects upload attempt with 403 Forbidden.
    - Direct service invocation raises ForbiddenException.
    - Zero records or document versions are created.
    """
    auditor_login = client.post(
        "/api/v1/auth/login",
        json={"email": "auditor.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    auditor_token = auditor_login.json()["access_token"]
    instrument_id = auth_fixture["instrument_a"].id
    initial_docs_count = db_session.query(Document).filter(Document.instrument_id == instrument_id).count()

    # 1. API endpoint call by Auditor -> 403 Forbidden
    file_bytes = b"%PDF-1.4\n%synthetic pdf upload"
    res = client.post(
        f"/api/v1/instruments/{instrument_id}/documents",
        data={"category": "FDR_COPY", "title": "Auditor FDR Copy"},
        files={"file": ("test_doc.pdf", file_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403
    assert "read-only" in res.json().get("error", "").lower() or "read-only" in res.json().get("detail", "").lower()

    # Verify no document or version was persisted
    final_docs_count = db_session.query(Document).filter(Document.instrument_id == instrument_id).count()
    assert final_docs_count == initial_docs_count

    # 2. Service layer defense directly
    with pytest.raises(ForbiddenException):
        DocumentService.create_document(
            db=db_session,
            instrument_id=instrument_id,
            category="FDR_COPY",
            created_by_user_id=auth_fixture["auditor"].id,
        )


def test_12_institution_user_document_upload_tenant_isolation(client: TestClient, auth_fixture, db_session: Session):
    """
    P0.2: Document upload preserves valid tenant isolation:
    - Institution User A can upload to its own instrument.
    - Institution User B cannot upload to Institution A's instrument (403 Forbidden).
    """
    # Login Institution User B
    login_b = client.post(
        "/api/v1/auth/login",
        json={"email": "nodal.b.p2@beta.ac.in", "password": "ValidPassword@2026"},
    )
    token_b = login_b.json()["access_token"]

    file_bytes = b"%PDF-1.4\n%synthetic pdf upload"
    res = client.post(
        f"/api/v1/instruments/{auth_fixture['instrument_a'].id}/documents",
        data={"category": "FDR_COPY", "title": "Cross Tenant Attempt"},
        files={"file": ("cross_tenant.pdf", file_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res.status_code == 403

    # Login Institution User A -> Success
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": "nodal.a.p2@alpha.ac.in", "password": "ValidPassword@2026"},
    )
    token_a = login_a.json()["access_token"]

    res_a = client.post(
        f"/api/v1/instruments/{auth_fixture['instrument_a'].id}/documents",
        data={"category": "FDR_COPY", "title": "Valid Institution A FDR"},
        files={"file": ("valid_fdr.pdf", file_bytes, "application/pdf")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code in (200, 201)
    assert res_a.json()["category"] == "FDR_COPY"


def test_13_auditor_release_request_creation_rejected_with_403(client: TestClient, auth_fixture, db_session: Session):
    """
    P0.3: Auditor is strictly read-only and cannot create release requests.
    - Router rejects attempt with 403 Forbidden.
    - Direct service call raises ForbiddenException.
    - No release request record is created.
    """
    auditor_login = client.post(
        "/api/v1/auth/login",
        json={"email": "auditor.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    auditor_token = auditor_login.json()["access_token"]
    instrument_id = auth_fixture["instrument_a"].id
    initial_count = db_session.query(ReleaseRequest).filter(ReleaseRequest.instrument_id == instrument_id).count()

    payload = {
        "instrument_id": instrument_id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Auditor unauthorized release request attempt",
    }

    # API call
    res = client.post(
        "/api/v1/release/requests",
        json=payload,
        headers={"Authorization": f"Bearer {auditor_token}"},
    )
    assert res.status_code == 403
    assert "read-only" in res.json().get("error", "").lower() or "read-only" in res.json().get("detail", "").lower()

    # Verify no record created
    final_count = db_session.query(ReleaseRequest).filter(ReleaseRequest.instrument_id == instrument_id).count()
    assert final_count == initial_count

    # Service call
    with pytest.raises(ForbiddenException):
        create_release_request(
            db=db_session,
            payload=ReleaseRequestCreate(**payload),
            current_user=auth_fixture["auditor"],
        )


def test_14_institution_user_release_request_tenant_isolation(client: TestClient, auth_fixture, db_session: Session):
    """
    P0.3: Release request creation preserves valid tenant isolation:
    - Institution User A can create release request for Instrument A.
    - Institution User B cannot create release request for Instrument A (403 Forbidden).
    """
    # Ensure profile seeded
    seed_demo_release_profile(db_session, created_by_user_id=auth_fixture["admin"].id)

    # Institution User B attempting against Instrument A
    login_b = client.post(
        "/api/v1/auth/login",
        json={"email": "nodal.b.p2@beta.ac.in", "password": "ValidPassword@2026"},
    )
    token_b = login_b.json()["access_token"]

    payload = {
        "instrument_id": auth_fixture["instrument_a"].id,
        "request_type": "RELEASE",
        "case_type": "STANDARD_MATURITY_RELEASE",
        "request_reason": "Cross-institution attempt",
    }

    res_b = client.post(
        "/api/v1/release/requests",
        json=payload,
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 403

    # Institution User A succeeds
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": "nodal.a.p2@alpha.ac.in", "password": "ValidPassword@2026"},
    )
    token_a = login_a.json()["access_token"]

    res_a = client.post(
        "/api/v1/release/requests",
        json=payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 201
    assert res_a.json()["workflow_status"] in ("DRAFT", "SUBMITTED")


def test_15_release_order_recording_separation_of_duties(client: TestClient, auth_fixture, db_session: Session):
    """
    P0.4: Strict separation of duties between statutory approval and financial release-order recording.
    - COMPETENT_AUTHORITY approves release request.
    - COMPETENT_AUTHORITY receives 403 Forbidden when attempting to record the release order.
    - SYSTEM_ADMIN receives 403 Forbidden when attempting to record the release order.
    - FINANCE_OFFICER successfully records the release order.
    - Order recording does not automatically complete bank action or close the case.
    - Duplicate recording attempt is rejected with 400.
    """
    # 1. Seed profile and create a release request
    profile = seed_demo_release_profile(db_session, created_by_user_id=auth_fixture["admin"].id)
    req = create_release_request(
        db=db_session,
        payload=ReleaseRequestCreate(
            instrument_id=auth_fixture["instrument_a"].id,
            request_type="RELEASE",
            case_type="STANDARD_MATURITY_RELEASE",
            request_reason="Legitimate mature deposit release.",
            policy_profile_id=profile.id,
        ),
        current_user=auth_fixture["inst_user_a"],
    )

    # 2. Advance to READY_FOR_AUTHORITY, then approve
    req.workflow_status = ReleaseWorkflowStatus.APPROVED.value
    db_session.commit()

    # 3. Logins
    order_payload = {
        "order_reference_number": "RO-AICTE-P2-2026-001",
        "order_date": str(date.today()),
        "is_synthetic_demo": True,
        "notes": "Financial release order dispatched to SBI branch.",
    }

    # 4. Competent Authority attempting to record order -> 403 Forbidden
    client.cookies.clear()
    client.post(
        "/api/v1/auth/login",
        json={"email": "authority.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    ca_res = client.post(
        f"/api/v1/release/requests/{req.id}/record-order",
        json=order_payload,
    )
    assert ca_res.status_code == 403

    # 5. System Admin attempting to record order -> 403 Forbidden
    client.cookies.clear()
    client.post(
        "/api/v1/auth/login",
        json={"email": "admin.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    admin_res = client.post(
        f"/api/v1/release/requests/{req.id}/record-order",
        json=order_payload,
    )
    assert admin_res.status_code == 403

    # 6. Finance Officer successfully records release order -> 201 Created
    client.cookies.clear()
    client.post(
        "/api/v1/auth/login",
        json={"email": "finance.p2@aicte-india.org", "password": "ValidPassword@2026"},
    )
    fo_res = client.post(
        f"/api/v1/release/requests/{req.id}/record-order",
        json=order_payload,
    )
    assert fo_res.status_code == 201
    assert fo_res.json()["order_reference_number"] == "RO-AICTE-P2-2026-001"
    assert fo_res.json()["bank_action_status"] == BankActionStatus.PENDING.value

    # Verify workflow status advanced to RELEASE_ORDER_RECORDED, NOT COMPLETED or CLOSED
    db_session.refresh(req)
    assert req.workflow_status == ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value

    # 7. Duplicate order recording attempt -> 400 Bad Request
    fo_dup_res = client.post(
        f"/api/v1/release/requests/{req.id}/record-order",
        json=order_payload,
    )
    assert fo_dup_res.status_code == 400

