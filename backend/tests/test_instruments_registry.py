"""
Test Suite: FDR / Instrument Registry (Prompt 4)
Automated verification for all 12 required test cases:
1. Instrument creation.
2. Amount and date validation.
3. Unknown or inactive institution rejection.
4. Institution-user ownership scoping.
5. Cross-institution reads and edits being denied.
6. Trust-level escalation being denied.
7. Unsupported administrative status transitions being denied.
8. Duplicate bank/reference warning.
9. Duplicate detection not silently merging instruments.
10. Pagination, search and filters.
11. Decimal monetary precision.
12. Authorization and audit coverage for creation/update.
"""
from decimal import Decimal
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.audit.models import AuditEvent
from app.modules.auth.service import provision_user
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    create_access_token,
)
from app.core.config import settings


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


@pytest.fixture
def active_institution(db_session: Session) -> Institution:
    inst = Institution(
        code="1-REG-INST-01",
        legal_name="Indian Institute of Technology Bombay",
        display_name="IIT Bombay",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar IITB",
        contact_email="registrar@iitb.ac.in",
        contact_phone="+91-22-25767000",
        address_line1="Powai",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400076",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def inactive_institution(db_session: Session) -> Institution:
    inst = Institution(
        code="1-INACT-INST-02",
        legal_name="Deactivated Engineering College",
        contact_name="Former Dean",
        contact_email="dean@inactive.edu",
        contact_phone="+91-11-20000000",
        address_line1="Old Campus Road",
        city="Nagpur",
        state="Maharashtra",
        postal_code="440001",
        is_active=False,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


# ------------------------------------------------------------------------------
# 1. Instrument creation
# ------------------------------------------------------------------------------
def test_instrument_creation_success(
    client: TestClient, db_session: Session, active_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Registry Admin",
        email="admin.reg@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    payload = {
        "institution_id": active_institution.id,
        "instrument_type": "FDR",
        "bank_name": "State Bank of India",
        "branch": "Powai Campus Branch, Mumbai",
        "reference_number": "FDR-SBI-2026-0001",
        "amount": "3500000.50",
        "currency": "INR",
        "issue_date": str(date.today()),
        "maturity_date": str(date.today() + timedelta(days=1825)),  # 5 years
        "lien_holder": "AICTE Regulation Bureau",
        "lien_details": "Joint holding with Member Secretary AICTE for new campus approval",
        "status": "REGISTERED",
    }
    res = client.post("/api/v1/instruments", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["reference_number"] == "FDR-SBI-2026-0001"
    assert data["bank_name"] == "State Bank of India"
    assert data["amount"] == "3500000.50"
    assert data["trust_level"] == "L0_DECLARED"
    assert data["status"] == "REGISTERED"
    assert data["maturity_indicator"] == "ACTIVE"


# ------------------------------------------------------------------------------
# 2. Amount and date validation
# ------------------------------------------------------------------------------
def test_amount_and_date_validation(
    client: TestClient, db_session: Session, active_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Validator Admin",
        email="admin.val@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # 1. Amount <= 0 rejected
    zero_amount_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Punjab National Bank",
            "reference_number": "FDR-PNB-001",
            "amount": "0.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2028-01-01",
        },
    )
    assert zero_amount_res.status_code == 422

    # 2. Maturity date earlier than or equal to issue date rejected
    invalid_dates_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Punjab National Bank",
            "reference_number": "FDR-PNB-002",
            "amount": "500000.00",
            "issue_date": "2026-06-01",
            "maturity_date": "2026-05-01",  # earlier than issue!
        },
    )
    assert invalid_dates_res.status_code == 422


# ------------------------------------------------------------------------------
# 3. Unknown or inactive institution rejection
# ------------------------------------------------------------------------------
def test_unknown_or_inactive_institution_rejection(
    client: TestClient, db_session: Session, inactive_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Institution Check Admin",
        email="admin.instchk@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # Unknown institution ID -> 404
    unknown_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": "00000000-0000-0000-0000-000000000000",
            "bank_name": "Canara Bank",
            "reference_number": "FDR-CAN-001",
            "amount": "1000000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
        },
    )
    assert unknown_res.status_code == 404

    # Inactive institution -> 400 rejection
    inactive_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": inactive_institution.id,
            "bank_name": "Canara Bank",
            "reference_number": "FDR-CAN-002",
            "amount": "1000000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
        },
    )
    assert inactive_res.status_code == 400
    assert inactive_res.json()["code"] == "INACTIVE_INSTITUTION_REGISTRATION_BLOCKED"


# ------------------------------------------------------------------------------
# 4. Institution-user ownership scoping
# ------------------------------------------------------------------------------
def test_institution_user_ownership_scoping(
    client: TestClient, db_session: Session, active_institution: Institution
):
    inst_user = provision_user(
        db=db_session,
        full_name="IITB Nodal Officer",
        email="nodal@iitb.ac.in",
        password="SecurePass@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=active_institution.id,
    )
    set_auth_cookie(client, inst_user)

    # Creating for own institution succeeds
    create_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Bank of Baroda",
            "reference_number": "BOB-2026-IITB-100",
            "amount": "1500000.00",
            "issue_date": "2026-02-01",
            "maturity_date": "2031-02-01",
            "status": "DRAFT",
        },
    )
    assert create_res.status_code == 201
    instru_id = create_res.json()["id"]

    # In list query, institution user sees their own instrument
    list_res = client.get("/api/v1/instruments")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(i["id"] == instru_id for i in items)


# ------------------------------------------------------------------------------
# 5. Cross-institution reads and edits being denied
# ------------------------------------------------------------------------------
def test_cross_institution_reads_and_edits_denied(
    client: TestClient, db_session: Session, active_institution: Institution
):
    # Create second institution
    other_inst = Institution(
        code="1-OTHER-INST",
        legal_name="Other State Technical College",
        contact_name="Registrar Other",
        contact_email="dean@other.edu",
        contact_phone="+91-11-20002222",
        address_line1="Other Street",
        city="Bhopal",
        state="Madhya Pradesh",
        postal_code="462001",
        is_active=True,
    )
    db_session.add(other_inst)
    db_session.commit()
    db_session.refresh(other_inst)

    # Admin creates an instrument for other_inst
    admin = provision_user(
        db=db_session,
        full_name="Setup Admin",
        email="setup.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)
    other_instru = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": other_inst.id,
            "bank_name": "HDFC Bank",
            "reference_number": "HDFC-OTHER-999",
            "amount": "2000000.00",
            "issue_date": "2026-01-10",
            "maturity_date": "2031-01-10",
        },
    ).json()["id"]

    # Now login as institution user of active_institution
    inst_user = provision_user(
        db=db_session,
        full_name="IITB Rep User",
        email="rep@iitb.ac.in",
        password="SecurePass@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=active_institution.id,
    )
    set_auth_cookie(client, inst_user)

    # Attempting to read other institution's instrument -> 403 Forbidden
    read_res = client.get(f"/api/v1/instruments/{other_instru}")
    assert read_res.status_code == 403

    # Attempting to edit other institution's instrument -> 403 Forbidden
    edit_res = client.patch(
        f"/api/v1/instruments/{other_instru}",
        json={"remarks": "Malicious edit attempt"},
    )
    assert edit_res.status_code == 403

    # Attempting to register instrument for other institution -> 403 Forbidden
    cross_create_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": other_inst.id,
            "bank_name": "HDFC Bank",
            "reference_number": "HDFC-INJECTED-001",
            "amount": "1000000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
        },
    )
    assert cross_create_res.status_code == 403


# ------------------------------------------------------------------------------
# 6. Trust-level escalation being denied
# ------------------------------------------------------------------------------
def test_trust_level_escalation_denied(
    client: TestClient, db_session: Session, active_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Security Admin",
        email="sec.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # 1. New instrument creation attempting to start at L2 or L3 -> 422
    fake_start_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "ICICI Bank",
            "reference_number": "ICICI-TRUST-TEST",
            "amount": "1000000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
            "trust_level": "L3_BANK_CONFIRMED",  # Prohibited!
        },
    )
    assert fake_start_res.status_code == 422

    # 2. Existing instrument starting at L0
    ok_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "ICICI Bank",
            "reference_number": "ICICI-TRUST-OK",
            "amount": "1000000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
        },
    )
    instru_id = ok_res.json()["id"]

    # Ordinary PATCH endpoint attempting to upgrade trust level -> 403 Forbidden
    escalate_res = client.patch(
        f"/api/v1/instruments/{instru_id}",
        json={"trust_level": "L2_OFFICER_VERIFIED"},
    )
    assert escalate_res.status_code == 403


# ------------------------------------------------------------------------------
# 7. Unsupported administrative status transitions being denied
# ------------------------------------------------------------------------------
def test_unsupported_administrative_status_transitions_denied(
    client: TestClient, db_session: Session, active_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Status Admin",
        email="status.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    ok_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Axis Bank",
            "reference_number": "AXIS-STATUS-TEST",
            "amount": "1200000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
            "status": "DRAFT",
        },
    )
    instru_id = ok_res.json()["id"]

    # Attempt transition to future workflow module status (e.g. RELEASED or MATURED) -> 400
    premature_release_res = client.patch(
        f"/api/v1/instruments/{instru_id}",
        json={"status": "RELEASED"},
    )
    assert premature_release_res.status_code == 400
    assert premature_release_res.json()["code"] == "UNSUPPORTED_STATUS_TRANSITION"


# ------------------------------------------------------------------------------
# 8. Duplicate bank/reference warning
# ------------------------------------------------------------------------------
def test_duplicate_bank_reference_warning(
    client: TestClient, db_session: Session, active_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Dup Admin",
        email="dup.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # Create initial instrument
    res1 = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Union Bank of India",
            "reference_number": "UBI-DUP-1001",
            "amount": "2500000.00",
            "issue_date": "2026-03-01",
            "maturity_date": "2031-03-01",
        },
    )
    assert res1.status_code == 201

    # Attempt second registration with matching normalized bank & reference without confirmation
    res_warn = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "  union bank of india  ",  # case-insensitive, whitespace
            "reference_number": "ubi-dup-1001",
            "amount": "2500000.00",
            "issue_date": "2026-03-01",
            "maturity_date": "2031-03-01",
            "confirm_duplicate": False,
        },
    )
    assert res_warn.status_code == 409
    data = res_warn.json()
    assert data["code"] == "DUPLICATE_REFERENCE_WARNING"
    assert "details" in data
    assert len(data["details"]["matching_records"]) >= 1


# ------------------------------------------------------------------------------
# 9. Duplicate detection not silently merging instruments
# ------------------------------------------------------------------------------
def test_duplicate_detection_not_silently_merging(
    client: TestClient, db_session: Session, active_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Merge Guard Admin",
        email="merge.guard@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # First instrument
    res1 = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Central Bank of India",
            "reference_number": "CBI-RECORD-2026",
            "amount": "3000000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
        },
    )
    instru_id_1 = res1.json()["id"]

    # Second instrument with confirm_duplicate=True
    res2 = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Central Bank of India",
            "reference_number": "CBI-RECORD-2026",
            "amount": "3000000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
            "confirm_duplicate": True,  # Explicitly confirmed for scrutiny review
        },
    )
    assert res2.status_code == 201
    instru_id_2 = res2.json()["id"]

    # Two distinct instrument records MUST exist in the database; neither merged nor deleted
    assert instru_id_1 != instru_id_2

    db_items = db_session.scalars(
        select(Instrument).where(Instrument.reference_number == "CBI-RECORD-2026")
    ).all()
    assert len(db_items) == 2


# ------------------------------------------------------------------------------
# 10. Pagination, search and filters
# ------------------------------------------------------------------------------
def test_pagination_search_and_filters(
    client: TestClient, db_session: Session, active_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Filter Admin",
        email="filter.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # Seed 3 instruments
    for i in range(1, 4):
        client.post(
            "/api/v1/instruments",
            json={
                "institution_id": active_institution.id,
                "bank_name": f"SearchBank {i}",
                "reference_number": f"SEARCH-REF-00{i}",
                "amount": f"{i * 1000000}.00",
                "issue_date": f"2026-0{i}-01",
                "maturity_date": f"203{i}-01-01",
                "status": "REGISTERED",
            },
        )

    # Search filter
    search_res = client.get("/api/v1/instruments?search=SEARCH-REF-002")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["reference_number"] == "SEARCH-REF-002"

    # Pagination: limit=1, skip=0
    page_res = client.get("/api/v1/instruments?limit=1&skip=0")
    assert page_res.status_code == 200
    assert len(page_res.json()["items"]) == 1
    assert page_res.json()["total"] >= 3


# ------------------------------------------------------------------------------
# 11. Decimal monetary precision
# ------------------------------------------------------------------------------
def test_decimal_monetary_precision(
    client: TestClient, db_session: Session, active_institution: Institution
):
    admin = provision_user(
        db=db_session,
        full_name="Decimal Admin",
        email="decimal.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    set_auth_cookie(client, admin)

    # Exact paise amount
    exact_amount = "78912345.67"
    res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Reserve Bank of India",
            "reference_number": "RBI-PRECISION-01",
            "amount": exact_amount,
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
        },
    )
    assert res.status_code == 201
    inst_id = res.json()["id"]

    # Verify database model stores Decimal, not float
    db_inst = db_session.scalar(select(Instrument).where(Instrument.id == inst_id))
    assert isinstance(db_inst.amount, Decimal)
    assert str(db_inst.amount) == exact_amount


# ------------------------------------------------------------------------------
# 12. Authorization and audit coverage for creation/update
# ------------------------------------------------------------------------------
def test_authorization_and_audit_coverage(
    client: TestClient, db_session: Session, active_institution: Institution
):
    # 1. Auditor read-only test
    auditor = provision_user(
        db=db_session,
        full_name="Auditor Inspect",
        email="auditor.insp@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_AUDITOR,
    )
    set_auth_cookie(client, auditor)

    # Auditor read -> 200
    assert client.get("/api/v1/instruments").status_code == 200

    # Auditor write -> 403 Forbidden
    auditor_create = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Auditor Forbidden Bank",
            "reference_number": "AUD-FORBIDDEN-01",
            "amount": "1000000.00",
            "issue_date": "2026-01-01",
            "maturity_date": "2031-01-01",
        },
    )
    assert auditor_create.status_code == 403

    # 2. Scrutiny officer registry correction with audit trail
    officer = provision_user(
        db=db_session,
        full_name="Scrutiny Reviewer",
        email="scrutiny.rev@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SCRUTINY_OFFICER,
    )
    set_auth_cookie(client, officer)

    # Scrutiny officer creates instrument (e.g. data correction/entry)
    create_res = client.post(
        "/api/v1/instruments",
        json={
            "institution_id": active_institution.id,
            "bank_name": "Indian Overseas Bank",
            "reference_number": "IOB-AUDIT-TEST",
            "amount": "4000000.00",
            "issue_date": "2026-01-15",
            "maturity_date": "2031-01-15",
        },
    )
    assert create_res.status_code == 201
    inst_id = create_res.json()["id"]

    # Scrutiny officer corrects remarks
    patch_res = client.patch(
        f"/api/v1/instruments/{inst_id}",
        json={"remarks": "Scrutiny registry verification correction completed"},
    )
    assert patch_res.status_code == 200

    # Verify audit events
    audit_events = db_session.scalars(
        select(AuditEvent).where(AuditEvent.entity_id == inst_id)
    ).all()
    actions = [e.action for e in audit_events]
    assert "INSTRUMENT_CREATED" in actions
    assert "INSTRUMENT_UPDATED" in actions
