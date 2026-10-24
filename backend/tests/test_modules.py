"""
Module Functional Integration Tests
Tests initial modular domain boundaries: Auth roles, Institutions, Instruments, and Audit trails.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.modules.auth.service import provision_user
from app.core.security import ROLE_SYSTEM_ADMIN, create_access_token
from app.core.config import settings


def set_admin_cookie(client: TestClient, db_session: Session):
    admin = provision_user(
        db=db_session,
        full_name="Integration Admin",
        email="integration.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )
    token = create_access_token(
        user_id=admin.id,
        email=admin.email,
        role=admin.role,
    )
    client.cookies.set(
        name=settings.AUTH_COOKIE_NAME,
        value=token,
        path=settings.AUTH_COOKIE_PATH,
    )
    return admin


def test_auth_roles_endpoint(client: TestClient):
    response = client.get("/api/v1/auth/roles")
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) == 7
    role_names = [r["name"] for r in roles]
    assert "SYSTEM_ADMIN" in role_names
    assert "SCRUTINY_OFFICER" in role_names
    assert "INSTITUTION_USER" in role_names


def test_create_and_list_institution(client: TestClient, db_session: Session):
    set_admin_cookie(client, db_session)
    payload = {
        "code": "1-99887766",
        "legal_name": "Delhi Institute of Advanced Technology",
        "state": "Delhi",
        "institution_type": "Engineering & Technology",
        "contact_email": "registrar@diat.ac.in",
        "is_active": True,
    }
    create_res = client.post("/api/v1/institutions", json=payload)
    assert create_res.status_code == 201
    inst = create_res.json()
    assert inst["id"] is not None
    assert inst["code"] == "1-99887766"

    # List institutions
    list_res = client.get("/api/v1/institutions")
    assert list_res.status_code == 200
    data = list_res.json()
    items = data["items"]
    assert any(i["code"] == "1-99887766" for i in items)


def test_create_and_summarize_instruments(client: TestClient, db_session: Session):
    set_admin_cookie(client, db_session)
    # First create institution
    inst_res = client.post(
        "/api/v1/institutions",
        json={
            "code": "1-55443322",
            "legal_name": "Mumbai Technical Campus",
            "state": "Maharashtra",
            "institution_type": "Pharmacy",
            "contact_email": "dean@mtc.edu.in",
            "is_active": True,
        },
    )
    inst_id = inst_res.json()["id"]

    # Create instrument
    instru_payload = {
        "institution_id": inst_id,
        "reference_number": "FDR-SBI-2026-9901",
        "bank_name": "State Bank of India",
        "branch": "Nariman Point, Mumbai",
        "amount": 2500000.00,
        "currency": "INR",
        "issue_date": "2026-01-15",
        "maturity_date": "2031-01-15",
        "status": "SUBMITTED",
        "verification_level": "L1_DECLARED",
        "joint_with_aicte": True,
        "lien_marked": True,
        "remarks": "Initial security deposit for AICTE new institute approval",
    }
    create_instru = client.post("/api/v1/instruments", json=instru_payload)
    assert create_instru.status_code == 201
    instru_data = create_instru.json()
    assert instru_data["reference_number"] == "FDR-SBI-2026-9901"
    assert instru_data["amount"] == 2500000.00

    # Summary
    sum_res = client.get("/api/v1/instruments/summary")
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["total_instruments"] >= 1
    assert summary["total_deposit_value"] >= 2500000.00


def test_audit_trail_listing(client: TestClient, db_session: Session):
    set_admin_cookie(client, db_session)
    res = client.get("/api/v1/audit")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
