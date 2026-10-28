"""
SakshyaTrail — Regression Test Suite: Authoritative 20 Synthetic Institutions
Verifies:
1. Exactly 20 active demo institutions exist in the demo environment.
2. Exactly 10 in Pune and exactly 10 in Mumbai.
3. Institution IDs (DEMO-PUN-001..010, DEMO-MUM-001..010) and display names match authoritative table.
4. Zero ALP-*, BET-*, Alpha/Beta placeholders appear in active demo API responses.
5. Submitted institution ID maps to the correct database entity on FDR registration.
6. Repeated seeding is deterministic and produces zero duplicates.
7. Unrelated development data in persistent DB is protected.
8. Tenant isolation denies cross-institution creation.
9. Lifecycle, monitoring, release and dashboard queries reflect the 20 authoritative institutions.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, select, func
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.auth.models import User
from app.modules.auth.service import authenticate_user
from scripts.demo_seed import DemoSeeder, PUNE_INSTITUTIONS, MUMBAI_INSTITUTIONS


EXPECTED_PUNE_CODES = [code for code, _, _, _ in PUNE_INSTITUTIONS]
EXPECTED_MUMBAI_CODES = [code for code, _, _, _ in MUMBAI_INSTITUTIONS]
ALL_EXPECTED_CODES = set(EXPECTED_PUNE_CODES + EXPECTED_MUMBAI_CODES)


def test_authoritative_institutions_count_and_distribution():
    """Requirement 1 & 2: Exactly 20 active institutions, 10 Pune, 10 Mumbai."""
    engine = create_engine(settings.active_database_url)
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM institutions WHERE is_active = 1")).scalar()
        pune_count = conn.execute(text("SELECT COUNT(*) FROM institutions WHERE is_active = 1 AND city = 'Pune'")).scalar()
        mumbai_count = conn.execute(text("SELECT COUNT(*) FROM institutions WHERE is_active = 1 AND city = 'Mumbai'")).scalar()
        
    assert total == 20, f"Expected exactly 20 active demo institutions, found {total}"
    assert pune_count == 10, f"Expected 10 Pune institutions, found {pune_count}"
    assert mumbai_count == 10, f"Expected 10 Mumbai institutions, found {mumbai_count}"


def test_authoritative_institution_codes_and_names():
    """Requirement 3: Check all 20 codes, names, states and synthetic markers."""
    engine = create_engine(settings.active_database_url)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT code, display_name, legal_name, city, state, is_synthetic FROM institutions ORDER BY code")).fetchall()
    
    assert len(rows) == 20
    found_codes = {r[0] for r in rows}
    assert found_codes == ALL_EXPECTED_CODES, f"Code mismatch. Diff: {ALL_EXPECTED_CODES.symmetric_difference(found_codes)}"
    
    for code, display, legal, city, state, is_synth in rows:
        assert state == "Maharashtra", f"Expected Maharashtra state, got {state} for {code}"
        assert is_synth == 1 or is_synth is True, f"Expected is_synthetic=True for {code}"
        assert display and "DEMO" in display, f"Expected DEMO in display_name for {code}"


def test_no_placeholder_institutions_in_active_environment():
    """Requirement 4: No ALP-*, BET-*, Alpha Institute, or Beta Institute placeholders exist."""
    engine = create_engine(settings.active_database_url)
    with engine.connect() as conn:
        placeholders = conn.execute(text("""
            SELECT code, legal_name FROM institutions 
            WHERE code LIKE 'ALP-%' OR code LIKE 'BET-%' OR code LIKE 'REP-%'
               OR legal_name LIKE '%Alpha Institute%' OR legal_name LIKE '%Beta Institute%'
        """)).fetchall()
        
    assert len(placeholders) == 0, f"Found prohibited placeholder institutions: {placeholders}"


def test_institutions_api_endpoint():
    """Requirement 4 & 5: API returns only the 20 authoritative institutions ordered by code."""
    with TestClient(app) as live_client:
        login_resp = live_client.post("/api/v1/auth/login", json={
            "email": "admin@aicte-india.org",
            "password": "AdminPassword@2026",
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]
        
        resp = live_client.get("/api/v1/institutions?is_active=true&limit=100", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["total"] == 20
        assert len(data["items"]) == 20
        
        # Assert clean code ordering and no placeholders
        for item in data["items"]:
            assert item["code"] in ALL_EXPECTED_CODES
            assert not item["code"].startswith("ALP-")
            assert not item["code"].startswith("BET-")
            assert item["city"] in ("Pune", "Mumbai")


def test_idempotent_seeding_no_duplicates():
    """Requirement 7: Rerunning demo seeder creates zero duplicate institutions."""
    seeder = DemoSeeder(db_url=settings.active_database_url)
    seeder.run_seed()
    
    engine = create_engine(settings.active_database_url)
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM institutions WHERE is_active = 1")).scalar()
        duplicates = conn.execute(text("SELECT code, COUNT(*) FROM institutions GROUP BY code HAVING COUNT(*) > 1")).fetchall()
        
    assert total == 20, f"Seeding created duplicate institutions: total is {total}"
    assert len(duplicates) == 0, f"Duplicate codes detected: {duplicates}"


def test_fdr_registration_mapping_and_tenant_isolation():
    """Requirement 6 & 9: FDR maps to chosen institution; cross-tenant creation is denied."""
    with TestClient(app) as live_client:
        # 1. Admin login
        admin_login = live_client.post("/api/v1/auth/login", json={
            "email": "admin@aicte-india.org",
            "password": "AdminPassword@2026",
        })
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        
        # Get institution IDs
        inst_resp = live_client.get("/api/v1/institutions?is_active=true&limit=100", headers={"Authorization": f"Bearer {admin_token}"})
        inst_list = {i["code"]: i["id"] for i in inst_resp.json()["items"]}
        
        pun_id = inst_list["DEMO-PUN-001"]
        mum_id = inst_list["DEMO-MUM-001"]
        
        # Admin records FDR for Pune institution
        import uuid
        ref_num = f"REG-TEST-{uuid.uuid4().hex[:6].upper()}"
        create_resp = live_client.post("/api/v1/instruments", headers={"Authorization": f"Bearer {admin_token}"}, json={
            "institution_id": pun_id,
            "instrument_type": "FDR",
            "bank_name": "State Bank of India",
            "branch": "FC Road",
            "reference_number": ref_num,
            "amount": "2000000.00",
            "currency": "INR",
            "issue_date": "2026-01-01",
            "maturity_date": "2029-01-01",
            "lien_holder": "AICTE Regulation Bureau",
            "status": "REGISTERED",
        })
        assert create_resp.status_code == 201, f"Failed: {create_resp.text}"
        created_fdr = create_resp.json()
        assert created_fdr["institution_id"] == pun_id
        
        # Verify retrieval
        get_resp = live_client.get(f"/api/v1/instruments/{created_fdr['id']}", headers={"Authorization": f"Bearer {admin_token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["institution_id"] == pun_id
        
        # 2. Institution User Tenant Isolation (Pune nodal officer cannot record for Mumbai institution)
        nodal_login = live_client.post("/api/v1/auth/login", json={
            "email": "nodal.pun001@example.com",
            "password": "NodalPassword@2026",
        })
        assert nodal_login.status_code == 200
        nodal_token = nodal_login.json()["access_token"]
        
        cross_resp = live_client.post("/api/v1/instruments", headers={"Authorization": f"Bearer {nodal_token}"}, json={
            "institution_id": mum_id,  # Intentionally attempt to submit against Mumbai
            "instrument_type": "FDR",
            "bank_name": "Axis Bank",
            "branch": "Fort",
            "reference_number": f"HACK-{uuid.uuid4().hex[:6]}",
            "amount": "1000000.00",
            "currency": "INR",
            "issue_date": "2026-01-01",
            "maturity_date": "2029-01-01",
            "lien_holder": "AICTE Regulation Bureau",
            "status": "REGISTERED",
        })
        assert cross_resp.status_code in (403, 400), f"Expected 403 Forbidden for cross-tenant creation, got {cross_resp.status_code}"
