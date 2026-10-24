"""
Module Functional Integration Tests
Tests initial modular domain boundaries: Auth roles, Institutions, Instruments, and Audit trails.
"""
from fastapi.testclient import TestClient


def test_auth_roles_endpoint(client: TestClient):
    response = client.get("/api/v1/auth/roles")
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) >= 4
    role_names = [r["name"] for r in roles]
    assert "aicte_admin" in role_names
    assert "scrutiny_officer" in role_names


def test_auth_session_bootstrap(client: TestClient):
    response = client.get("/api/v1/auth/session/bootstrap")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "aicte_admin" in data["available_roles"]


def test_create_and_list_institution(client: TestClient):
    payload = {
        "aicte_id": "1-99887766",
        "name": "Delhi Institute of Advanced Technology",
        "state": "Delhi",
        "category": "Engineering & Technology",
        "contact_email": "registrar@diat.ac.in",
        "status": "ACTIVE",
    }
    create_res = client.post("/api/v1/institutions", json=payload)
    assert create_res.status_code == 201
    inst = create_res.json()
    assert inst["id"] is not None
    assert inst["aicte_id"] == "1-99887766"

    # List institutions
    list_res = client.get("/api/v1/institutions")
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(i["aicte_id"] == "1-99887766" for i in items)


def test_create_and_summarize_instruments(client: TestClient):
    # First create institution
    inst_res = client.post(
        "/api/v1/institutions",
        json={
            "aicte_id": "1-55443322",
            "name": "Mumbai Technical Campus",
            "state": "Maharashtra",
            "category": "Pharmacy",
            "contact_email": "dean@mtc.edu.in",
            "status": "ACTIVE",
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


def test_audit_trail_listing(client: TestClient):
    res = client.get("/api/v1/audit")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
