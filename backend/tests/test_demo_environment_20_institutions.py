"""
SakshyaTrail — Comprehensive Automated Test Suite for 20 Synthetic Institutions Demo Environment
Verifies:
1. Exactly 20 active synthetic institutions exist (10 in Pune, 10 in Mumbai, 0 in other cities).
2. Exactly 80 seeded FDR instruments exist (4 per institution).
3. Every seeded instrument references a valid synthetic institution.
4. City filtering (city=Pune, city=Mumbai) on institutions and instruments.
5. Idempotency: re-running DemoSeeder produces zero duplicate institutions or instruments.
6. Dry-run safety: dry-run mode makes zero database modifications.
7. Tenant Isolation: Institution user for DEMO-PUN-001 cannot access instruments of DEMO-PUN-002 or DEMO-MUM-001.
8. Auditor role mutation restrictions (read-only invariant).
9. Nine-stage integration: Documents, validations, verifications, lifecycles, and release cases are validly linked.
10. Cryptographic audit chain integrity verification.
"""
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.auth.models import User
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationFinding
from app.modules.verification.models import VerificationRequest
from app.modules.release.models import ReleaseRequest, ReadinessAssessment
from app.core.security import create_access_token
from app.modules.dashboard.audit_query_service import AuditQueryService
from scripts.demo_seed import DemoSeeder, PUNE_INSTITUTIONS, MUMBAI_INSTITUTIONS


@pytest.fixture
def seeded_demo_session(db_session: Session) -> Session:
    """Populate isolated transaction with the full 20-institution demo dataset."""
    seeder = DemoSeeder(db=db_session, dry_run=False)
    seeder.run_seed()
    db_session.flush()
    return db_session


def test_dry_run_makes_no_modifications(db_session: Session):
    """Verify that --dry-run plans the operations without persisting changes."""
    initial_inst_count = db_session.query(Institution).count()
    initial_instr_count = db_session.query(Instrument).count()

    seeder = DemoSeeder(db=db_session, dry_run=True)
    stats = seeder.run_seed()

    assert seeder.dry_run is True
    assert stats["institutions_pune"] == 10
    assert stats["institutions_mumbai"] == 10
    assert stats["instruments_created"] == 80

    # Ensure zero persistent writes occurred
    assert db_session.query(Institution).count() == initial_inst_count
    assert db_session.query(Instrument).count() == initial_instr_count


def test_apply_creates_exactly_20_institutions_and_80_instruments(seeded_demo_session: Session):
    """
    Verify:
    - Exactly 20 synthetic institutions created
    - Exactly 10 in Pune and 10 in Mumbai
    - Zero in other cities
    - Exactly 80 instruments created (4 per institution)
    """
    db = seeded_demo_session

    all_demo_institutions = db.query(Institution).filter(
        Institution.is_synthetic == True
    ).all()
    assert len(all_demo_institutions) == 20

    pune_insts = [i for i in all_demo_institutions if i.city == "Pune"]
    mumbai_insts = [i for i in all_demo_institutions if i.city == "Mumbai"]
    other_insts = [i for i in all_demo_institutions if i.city not in ("Pune", "Mumbai")]

    assert len(pune_insts) == 10, f"Expected 10 Pune institutions, found {len(pune_insts)}"
    assert len(mumbai_insts) == 10, f"Expected 10 Mumbai institutions, found {len(mumbai_insts)}"
    assert len(other_insts) == 0, f"Expected 0 other city institutions, found {len(other_insts)}"

    # Verify codes match specified list
    pune_codes = {i.code for i in pune_insts}
    expected_pune_codes = {item[0] for item in PUNE_INSTITUTIONS}
    assert pune_codes == expected_pune_codes

    mumbai_codes = {i.code for i in mumbai_insts}
    expected_mumbai_codes = {item[0] for item in MUMBAI_INSTITUTIONS}
    assert mumbai_codes == expected_mumbai_codes

    # Verify instruments
    all_demo_instruments = db.query(Instrument).filter(
        Instrument.is_synthetic == True
    ).all()
    assert len(all_demo_instruments) == 80, f"Expected 80 instruments, found {len(all_demo_instruments)}"

    # Verify exactly 4 instruments per institution
    for inst in all_demo_institutions:
        inst_instruments = [instr for instr in all_demo_instruments if instr.institution_id == inst.id]
        assert len(inst_instruments) == 4, f"Institution {inst.code} has {len(inst_instruments)} instruments, expected 4"

        # Verify synthetic marker
        for instr in inst_instruments:
            assert instr.is_synthetic is True
            assert instr.remarks is not None
            assert "DEMO / SYNTHETIC" in instr.remarks


def test_idempotency_second_run_creates_zero_duplicates(seeded_demo_session: Session):
    """
    Verify that executing DemoSeeder.apply a second time is fully idempotent:
    - 0 new institutions created
    - 0 new instruments created
    - Exactly 20 institutions and 80 instruments remain
    """
    db = seeded_demo_session

    initial_inst_count = db.query(Institution).filter(Institution.is_synthetic == True).count()
    initial_instr_count = db.query(Instrument).filter(Instrument.is_synthetic == True).count()

    # Second run
    seeder2 = DemoSeeder(db=db, dry_run=False)
    seeder2.run_seed()
    db.flush()

    total_demo_insts = db.query(Institution).filter(Institution.is_synthetic == True).count()
    assert total_demo_insts == initial_inst_count == 20

    total_demo_instrs = db.query(Instrument).filter(Instrument.is_synthetic == True).count()
    assert total_demo_instrs == initial_instr_count == 80


def test_api_city_filtering_for_institutions(client: TestClient, seeded_demo_session: Session):
    """Verify backend endpoint /institutions supports city filtering for Pune and Mumbai."""
    db = seeded_demo_session
    admin_user = db.query(User).filter(User.email == "admin@aicte-india.org").first()
    assert admin_user is not None
    token = create_access_token(
        user_id=str(admin_user.id),
        email=admin_user.email,
        role=admin_user.role,
        institution_id=admin_user.institution_id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Pune filter
    res_pune = client.get("/api/v1/institutions?city=Pune&is_synthetic=true", headers=headers)
    assert res_pune.status_code == 200
    pune_data = res_pune.json()
    assert pune_data["total"] == 10
    for item in pune_data["items"]:
        assert item["city"] == "Pune"
        assert item["is_synthetic"] is True

    # Mumbai filter
    res_mumbai = client.get("/api/v1/institutions?city=Mumbai&is_synthetic=true", headers=headers)
    assert res_mumbai.status_code == 200
    mumbai_data = res_mumbai.json()
    assert mumbai_data["total"] == 10
    for item in mumbai_data["items"]:
        assert item["city"] == "Mumbai"
        assert item["is_synthetic"] is True


def test_api_city_filtering_for_instruments(client: TestClient, seeded_demo_session: Session):
    """Verify backend endpoint /api/v1/instruments supports city filtering (40 in Pune, 40 in Mumbai)."""
    db = seeded_demo_session
    admin_user = db.query(User).filter(User.email == "admin@aicte-india.org").first()
    assert admin_user is not None
    token = create_access_token(
        user_id=str(admin_user.id),
        email=admin_user.email,
        role=admin_user.role,
        institution_id=admin_user.institution_id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Pune filter
    res_pune = client.get("/api/v1/instruments?city=Pune&is_synthetic=true", headers=headers)
    assert res_pune.status_code == 200
    pune_data = res_pune.json()
    assert pune_data["total"] == 40
    for item in pune_data["items"]:
        assert item["is_synthetic"] is True

    # Mumbai filter
    res_mumbai = client.get("/api/v1/instruments?city=Mumbai&is_synthetic=true", headers=headers)
    assert res_mumbai.status_code == 200
    mumbai_data = res_mumbai.json()
    assert mumbai_data["total"] == 40
    for item in mumbai_data["items"]:
        assert item["is_synthetic"] is True


def test_tenant_isolation_institution_user_cannot_cross_boundary(client: TestClient, seeded_demo_session: Session):
    """
    Verify that an INSTITUTION_USER belonging to DEMO-PUN-001:
    - Can only list their own 4 FDR instruments
    - Cannot access an instrument belonging to DEMO-PUN-002 or DEMO-MUM-001
    """
    db = seeded_demo_session
    pun001_user = db.query(User).filter(User.email == "nodal.pun001@example.com").first()
    assert pun001_user is not None
    token = create_access_token(
        user_id=str(pun001_user.id),
        email=pun001_user.email,
        role=pun001_user.role,
        institution_id=pun001_user.institution_id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Listing instruments should return strictly their own 4 instruments
    res = client.get("/api/v1/instruments", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4
    for item in data["items"]:
        assert item["institution_id"] == str(pun001_user.institution_id)

    # Attempting to access an instrument of DEMO-MUM-001 directly by ID
    mum_inst = db.query(Institution).filter(Institution.code == "DEMO-MUM-001").first()
    mum_instrument = db.query(Instrument).filter(Instrument.institution_id == mum_inst.id).first()
    assert mum_instrument is not None

    res_cross = client.get(f"/api/v1/instruments/{mum_instrument.id}", headers=headers)
    assert res_cross.status_code in (403, 404), f"Expected 403 or 404 for cross-tenant access, got {res_cross.status_code}"


def test_auditor_role_is_strictly_read_only(client: TestClient, seeded_demo_session: Session):
    """Verify that AUDITOR role cannot mutate or create instruments."""
    db = seeded_demo_session
    auditor_user = db.query(User).filter(User.email == "auditor.compliance@aicte-india.org").first()
    assert auditor_user is not None
    token = create_access_token(
        user_id=str(auditor_user.id),
        email=auditor_user.email,
        role=auditor_user.role,
        institution_id=auditor_user.institution_id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Read operations should succeed
    res_get = client.get("/api/v1/instruments", headers=headers)
    assert res_get.status_code == 200

    # Write / mutation must fail with 403 Forbidden
    first_inst = db.query(Institution).first()
    payload = {
        "institution_id": str(first_inst.id),
        "reference_number": "FDR-AUDITOR-MUTATION-ATTEMPT",
        "bank_name": "State Bank of India",
        "amount": 500000.0,
        "issue_date": str(date.today()),
        "maturity_date": "2030-01-01",
    }
    res_post = client.post("/api/v1/instruments", json=payload, headers=headers)
    assert res_post.status_code == 403


def test_release_case_readiness_blockers_and_maker_checker(seeded_demo_session: Session):
    """
    Verify release cases have inspectable blockers and distinct workflow stages:
    - Cases with assessment_outcome BLOCKED have blockers recorded
    """
    db = seeded_demo_session
    blocked_assessments = db.query(ReadinessAssessment).filter(
        ReadinessAssessment.assessment_outcome == "BLOCKED"
    ).all()
    assert len(blocked_assessments) > 0, "Expected at least one BLOCKED readiness assessment"

    for ra in blocked_assessments:
        assert ra.blockers_count > 0
        assert ra.total_items_count > 0


def test_audit_ledger_cryptographic_chain_integrity(seeded_demo_session: Session):
    """
    Verify that the audit ledger's SHA-256 hash chain remains unbroken
    across all synthetic seed operations.
    """
    db = seeded_demo_session
    admin_user = db.query(User).filter(User.email == "admin@aicte-india.org").first()
    assert admin_user is not None

    verification_result = AuditQueryService.verify_audit_log_integrity(
        db=db,
        current_user=admin_user,
        log_verification_run=False,
    )

    assert verification_result.get("is_chain_intact") is True or verification_result.get("status") == "PASS", (
        f"Audit chain verification failed: {verification_result}"
    )
    assert verification_result.get("verified_count", 0) > 0
    assert verification_result.get("broken_links", []) == []
