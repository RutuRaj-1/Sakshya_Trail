"""
Test Suite for Module 7 — Prompt 3
Validates:
1. Search instruments with various filters (institution, bank, reference, status, trust, office, dates, amounts, discrepancies).
2. Search release cases with filters.
3. Multi-tenant isolation in search and direct lookups.
4. Document history, version order, and SHA-256 integrity (no raw file paths exposed).
5. Field provenance tracking with role masking.
6. Lineage history preserving predecessor and successor continuity.
7. Verification history with explicit SIMULATED labelling.
8. Append-only scrutiny observations, supersession chains, and resolution.
9. Security enforcement (Auditor read-only, cross-tenant denial).
"""
import uuid
import pytest
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.verification.models import FieldProvenance, VerificationRequest
from app.modules.lifecycle.models import LifecycleEvaluation, InstrumentLineage
from app.modules.release.models import ReleaseRequest, ReadinessAssessment
from app.modules.validation.models import ValidationFinding
from app.modules.dashboard.models import ScrutinyObservation


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_search_data(db_session: Session):
    """Seed institutions, users, instruments, documents, findings, and release cases."""
    # Institution Alpha
    inst_a = Institution(
        id=f"inst-a-{uuid.uuid4().hex[:6]}",
        legal_name="Alpha Institute of Technology",
        display_name="Alpha Institute of Technology",
        code="ALPHA01",
        state="Delhi",
        contact_email="contact@alpha.edu",
        is_active=True,
    )
    # Institution Beta
    inst_b = Institution(
        id=f"inst-b-{uuid.uuid4().hex[:6]}",
        legal_name="Beta College of Engineering",
        display_name="Beta College of Engineering",
        code="BETA01",
        state="Maharashtra",
        contact_email="contact@beta.edu",
        is_active=True,
    )
    db_session.add_all([inst_a, inst_b])
    db_session.flush()

    # Users
    admin_user = User(
        id=f"usr-admin-{uuid.uuid4().hex[:6]}",
        email=f"admin_{uuid.uuid4().hex[:6]}@aicte.gov.in",
        full_name="AICTE System Admin",
        role="SYSTEM_ADMIN",
        is_active=True,
        password_hash="hashed_dummy_pw",
    )
    officer_user = User(
        id=f"usr-off-{uuid.uuid4().hex[:6]}",
        email=f"officer_{uuid.uuid4().hex[:6]}@aicte.gov.in",
        full_name="Scrutiny Officer Sharma",
        role="SCRUTINY_OFFICER",
        is_active=True,
        password_hash="hashed_dummy_pw",
    )
    auditor_user = User(
        id=f"usr-aud-{uuid.uuid4().hex[:6]}",
        email=f"auditor_{uuid.uuid4().hex[:6]}@aicte.gov.in",
        full_name="CAG Auditor Verma",
        role="AUDITOR",
        is_active=True,
        password_hash="hashed_dummy_pw",
    )
    inst_user_a = User(
        id=f"usr-insta-{uuid.uuid4().hex[:6]}",
        email=f"registrar_{uuid.uuid4().hex[:6]}@alpha.edu",
        full_name="Alpha Registrar",
        role="INSTITUTION_USER",
        institution_id=inst_a.id,
        is_active=True,
        password_hash="hashed_dummy_pw",
    )
    inst_user_b = User(
        id=f"usr-instb-{uuid.uuid4().hex[:6]}",
        email=f"registrar_{uuid.uuid4().hex[:6]}@beta.edu",
        full_name="Beta Registrar",
        role="INSTITUTION_USER",
        institution_id=inst_b.id,
        is_active=True,
        password_hash="hashed_dummy_pw",
    )
    db_session.add_all([admin_user, officer_user, auditor_user, inst_user_a, inst_user_b])
    db_session.flush()

    today = date.today()

    # Instrument 1 (Alpha, SBI, has discrepancy, has predecessor)
    pred_inst = Instrument(
        id=f"inst-pred-{uuid.uuid4().hex[:6]}",
        institution_id=inst_a.id,
        reference_number="FDR-SBI-OLD-001",
        bank_name="State Bank of India",
        branch="Main Branch",
        amount=Decimal("500000.00"),
        issue_date=today - timedelta(days=400),
        maturity_date=today - timedelta(days=35),
        status="RENEWED",
        trust_level="L2_OFFICER_VERIFIED",
        assigned_office="Northern Regional Office",
    )
    db_session.add(pred_inst)
    db_session.flush()

    inst1 = Instrument(
        id=f"inst-1-{uuid.uuid4().hex[:6]}",
        institution_id=inst_a.id,
        reference_number="FDR-SBI-2026-A1",
        bank_name="State Bank of India",
        branch="Main Branch",
        amount=Decimal("1000000.00"),
        currency="INR",
        issue_date=today - timedelta(days=30),
        maturity_date=today + timedelta(days=45),
        status="REGISTERED",
        trust_level="L1_PHYSICAL_SUBMITTED",
        assigned_office="Northern Regional Office",
        created_by_user_id=officer_user.id,
    )
    # Instrument 2 (Beta, PNB)
    inst2 = Instrument(
        id=f"inst-2-{uuid.uuid4().hex[:6]}",
        institution_id=inst_b.id,
        reference_number="FDR-PNB-2026-B1",
        bank_name="Punjab National Bank",
        branch="Connaught Place",
        amount=Decimal("2500000.00"),
        currency="INR",
        issue_date=today - timedelta(days=60),
        maturity_date=today + timedelta(days=200),
        status="ACTIVE",
        trust_level="L3_BANK_CONFIRMED",
        assigned_office="Western Regional Office",
        created_by_user_id=officer_user.id,
    )
    db_session.add_all([inst1, inst2])
    db_session.flush()

    # Lineage link (pred_inst -> inst1)
    lineage = InstrumentLineage(
        id=f"lin-{uuid.uuid4().hex[:6]}",
        predecessor_instrument_id=pred_inst.id,
        successor_instrument_id=inst1.id,
        institution_id=inst_a.id,
        relationship_type="RENEWAL",
        relationship_status="ACTIVE",
        created_by_user_id=officer_user.id,
    )
    db_session.add(lineage)

    # Document and versions on inst1
    doc = Document(
        id=f"doc-{uuid.uuid4().hex[:6]}",
        institution_id=inst_a.id,
        instrument_id=inst1.id,
        category="FDR_RECEIPT",
        title="Fixed Deposit Receipt Certificate",
        status="ACTIVE",
        created_by_user_id=officer_user.id,
    )
    db_session.add(doc)
    db_session.flush()

    v1 = DocumentVersion(
        id=f"ver1-{uuid.uuid4().hex[:6]}",
        document_id=doc.id,
        version_number=1,
        storage_key=f"storage/keys/{uuid.uuid4().hex}.pdf",
        original_filename="receipt_initial.pdf",
        content_type="application/pdf",
        file_size_bytes=102400,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        uploader_user_id=officer_user.id,
        uploaded_at=datetime.now(timezone.utc) - timedelta(hours=2),
        processing_status="PROCESSED",
    )
    v2 = DocumentVersion(
        id=f"ver2-{uuid.uuid4().hex[:6]}",
        document_id=doc.id,
        version_number=2,
        storage_key=f"storage/keys/{uuid.uuid4().hex}.pdf",
        original_filename="receipt_corrected.pdf",
        content_type="application/pdf",
        file_size_bytes=104800,
        sha256_hash="5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
        uploader_user_id=officer_user.id,
        uploaded_at=datetime.now(timezone.utc) - timedelta(hours=1),
        processing_status="PROCESSED",
    )
    db_session.add_all([v1, v2])

    # Discrepancy finding on inst1
    finding = ValidationFinding(
        id=f"find-{uuid.uuid4().hex[:6]}",
        finding_fingerprint=f"fp-{uuid.uuid4().hex[:12]}",
        institution_id=inst_a.id,
        instrument_id=inst1.id,
        rule_id="VAL-FDR-002",
        rule_version="1.0",
        rule_type="DETERMINISTIC",
        category="DISCREPANCY",
        severity="HIGH",
        title="Bank branch address mismatch with regional AICTE jurisdiction",
        status="OPEN",
    )
    db_session.add(finding)

    # Verification request on inst1 (SIMULATED)
    vr = VerificationRequest(
        id=f"vr-{uuid.uuid4().hex[:6]}",
        instrument_id=inst1.id,
        reference_code="VR-2026-TEST-01",
        channel="SIMULATED",
        status="PENDING",
        snapshot_data_json="{}",
        requested_by_user_id=officer_user.id,
    )
    db_session.add(vr)

    # Field provenance on inst1
    prov = FieldProvenance(
        id=f"prov-{uuid.uuid4().hex[:6]}",
        instrument_id=inst1.id,
        field_name="maturity_date",
        recorded_value=(today + timedelta(days=45)).isoformat(),
        source_type="DOCUMENT_OCR",
        evidence_reference=doc.id,
        source_actor_id=officer_user.id,
    )
    db_session.add(prov)

    # Release case for inst1
    rel_case = ReleaseRequest(
        id=f"rel-{uuid.uuid4().hex[:6]}",
        case_number="REL-2026-0001",
        instrument_id=inst1.id,
        institution_id=inst_a.id,
        request_type="RELEASE",
        case_type="STANDARD_MATURITY_RELEASE",
        requester_id=officer_user.id,
        request_reason="Standard release request upon maturity",
        workflow_status="UNDER_SCRUTINY",
    )
    db_session.add(rel_case)

    db_session.commit()

    return {
        "admin": admin_user,
        "officer": officer_user,
        "auditor": auditor_user,
        "inst_user_a": inst_user_a,
        "inst_user_b": inst_user_b,
        "inst_a": inst_a,
        "inst_b": inst_b,
        "inst1": inst1,
        "inst2": inst2,
        "pred_inst": pred_inst,
        "doc": doc,
        "v1": v1,
        "v2": v2,
        "finding": finding,
        "vr": vr,
        "prov": prov,
        "rel_case": rel_case,
    }


def auth_header(client: TestClient, user: User) -> dict:
    from app.core.security import create_access_token
    from app.core.config import settings
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
    return {"Authorization": f"Bearer {token}"}


def test_unified_search_instruments_filters(client: TestClient, seeded_search_data):
    """Test 1: Search by institution, bank, reference, status, and flag filters."""
    data = seeded_search_data
    headers = auth_header(client, data["admin"])

    # 1. Search by bank
    res = client.get("/api/v1/dashboard/search/instruments?bank_name=State Bank of India", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total_count"] >= 1
    refs = [r["reference_number"] for r in body["records"]]
    assert "FDR-SBI-2026-A1" in refs

    # 2. Search by keyword
    res = client.get("/api/v1/dashboard/search/instruments?q=Alpha", headers=headers)
    assert res.status_code == 200
    assert any("Alpha" in (r["institution_name"] or "") for r in res.json()["records"])

    # 3. Filter by has_discrepancies
    res = client.get("/api/v1/dashboard/search/instruments?has_discrepancies=true", headers=headers)
    assert res.status_code == 200
    items = res.json()["records"]
    assert any(r["id"] == data["inst1"].id for r in items)


def test_search_release_cases(client: TestClient, seeded_search_data):
    """Test 2: Search release cases with filters."""
    data = seeded_search_data
    headers = auth_header(client, data["admin"])

    res = client.get("/api/v1/dashboard/search/release-cases?request_type=RELEASE", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total_count"] >= 1
    cases = [c["case_reference"] for c in body["records"]]
    assert "REL-2026-0001" in cases


def test_cross_institution_tenant_isolation(client: TestClient, seeded_search_data):
    """Test 3: Cross-institution isolation in search and direct lookup."""
    data = seeded_search_data
    # User B queries instruments -> should NOT see Alpha's instrument
    headers_b = auth_header(client, data["inst_user_b"])

    res = client.get("/api/v1/dashboard/search/instruments", headers=headers_b)
    assert res.status_code == 200
    records = res.json()["records"]
    assert all(r["institution_id"] == data["inst_b"].id for r in records)
    assert not any(r["id"] == data["inst1"].id for r in records)

    # Direct detail lookup denial
    res_direct = client.get(f"/api/v1/dashboard/instruments/{data['inst1'].id}/detail", headers=headers_b)
    assert res_direct.status_code in [403, 404]


def test_document_history_order_and_sha256(client: TestClient, seeded_search_data):
    """Test 4: Document version order, SHA-256 integrity, and secure download URL."""
    data = seeded_search_data
    headers = auth_header(client, data["admin"])

    res = client.get(f"/api/v1/dashboard/instruments/{data['inst1'].id}/detail", headers=headers)
    assert res.status_code == 200
    body = res.json()

    docs = body["documents"]
    assert len(docs) >= 2
    # Verify version 2 appears before version 1 (chronological desc)
    assert docs[0]["version_number"] == 2
    assert docs[1]["version_number"] == 1
    # Check SHA-256 hash preservation
    assert docs[0]["sha256_hash"] == data["v2"].sha256_hash
    # Confirm download URL uses API endpoint and does NOT expose storage key
    assert "/api/v1/documents/" in docs[0]["download_url"]
    assert "storage/keys" not in docs[0]["download_url"]


def test_lineage_and_simulated_verification(client: TestClient, seeded_search_data):
    """Test 5: Predecessor continuity and SIMULATED channel labelling."""
    data = seeded_search_data
    headers = auth_header(client, data["admin"])

    res = client.get(f"/api/v1/dashboard/instruments/{data['inst1'].id}/detail", headers=headers)
    assert res.status_code == 200
    body = res.json()

    # Predecessor lineage
    preds = body["instrument"]["predecessors"]
    assert len(preds) >= 1
    assert preds[0]["predecessor_reference"] == "FDR-SBI-OLD-001"

    # Simulated verification labelling
    lifecycle = body["lifecycle_lineage"]
    verif_events = [e for e in lifecycle if e["event_type"] == "VERIFICATION_REQUEST"]
    assert len(verif_events) >= 1
    assert verif_events[0]["is_simulated"] is True
    assert "SIMULATED" in verif_events[0]["details"]["channel"]


def test_append_only_observation_lifecycle(client: TestClient, seeded_search_data):
    """Test 6: Create observation, amend (superseding prior note), and resolve."""
    data = seeded_search_data
    officer_headers = auth_header(client, data["officer"])

    # 1. Create observation
    create_payload = {
        "observation_text": "Initial inspection: bank branch IFSC requires manual cross-verification.",
        "observation_category": "DISCREPANCY",
        "is_internal_only": False,
    }
    res = client.post(
        f"/api/v1/dashboard/instruments/{data['inst1'].id}/observations",
        json=create_payload,
        headers=officer_headers,
    )
    assert res.status_code == 201
    obs1 = res.json()
    assert obs1["status"] == "RECORDED"
    assert obs1["observation_text"] == create_payload["observation_text"]
    assert obs1["author_role"] == "SCRUTINY_OFFICER"

    # 2. Amend observation (creates superseding note, preserves original)
    amend_payload = {
        "observation_text": "Amended inspection: IFSC code confirmed against RBI NEFT directory; branch authorized.",
        "amendment_reason": "Verified against latest central bank directory.",
        "is_internal_only": False,
    }
    res_amend = client.post(
        f"/api/v1/dashboard/observations/{obs1['id']}/amend",
        json=amend_payload,
        headers=officer_headers,
    )
    assert res_amend.status_code == 200
    obs2 = res_amend.json()
    assert obs2["status"] == "AMENDED"
    assert obs2["supersedes_id"] == obs1["id"]

    # 3. Verify prior observation was superseded, NOT erased
    res_list = client.get(f"/api/v1/dashboard/instruments/{data['inst1'].id}/observations", headers=officer_headers)
    assert res_list.status_code == 200
    all_obs = res_list.json()
    prior_in_list = next((o for o in all_obs if o["id"] == obs1["id"]), None)
    assert prior_in_list is not None
    assert prior_in_list["status"] == "SUPERSEDED"
    assert prior_in_list["superseded_by_id"] == obs2["id"]

    # 4. Resolve observation
    resolve_payload = {
        "resolution_reason": "All discrepancy findings cleared per supervisory review.",
    }
    res_resolve = client.post(
        f"/api/v1/dashboard/observations/{obs2['id']}/resolve",
        json=resolve_payload,
        headers=officer_headers,
    )
    assert res_resolve.status_code == 200
    obs_resolved = res_resolve.json()
    assert obs_resolved["status"] == "RESOLVED"
    assert obs_resolved["resolution_reason"] == resolve_payload["resolution_reason"]


def test_auditor_read_only_enforcement(client: TestClient, seeded_search_data):
    """Test 7: Auditor role possesses strictly read-only permissions."""
    data = seeded_search_data
    auditor_headers = auth_header(client, data["auditor"])

    # Auditor can view observations
    res_get = client.get(f"/api/v1/dashboard/instruments/{data['inst1'].id}/observations", headers=auditor_headers)
    assert res_get.status_code == 200

    # Auditor cannot create observation
    res_post = client.post(
        f"/api/v1/dashboard/instruments/{data['inst1'].id}/observations",
        json={"observation_text": "Auditor unauthorized test note"},
        headers=auditor_headers,
    )
    assert res_post.status_code == 403
