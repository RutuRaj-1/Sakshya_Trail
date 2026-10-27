"""
Module 7 — Prompt 4 Automated Acceptance Tests:
Operational Reports, Consistent Drill-Down, and Secure CSV & PDF Exports
"""
import uuid
import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationFinding
from app.modules.verification.models import VerificationRequest, FieldProvenance
from app.modules.lifecycle.models import LifecycleEvaluation, InstrumentLineage
from app.modules.release.models import ReleaseRequest
from app.modules.audit.models import AuditEvent




@pytest.fixture
def test_data(db_session):
    """Seed synthetic institutions, users, instruments, findings, and verifications for reporting tests."""
    suffix = uuid.uuid4().hex[:6]

    # 1. Institutions
    inst_a = Institution(
        id=f"inst-rep-a-{suffix}",
        legal_name=f"IIT Rep A {suffix}",
        display_name=f"IIT Rep A {suffix}",
        code=f"REP-A-{suffix}",
        state="Maharashtra",
        contact_email=f"repa_{suffix}@example.com",
    )
    inst_b = Institution(
        id=f"inst-rep-b-{suffix}",
        legal_name=f"NIT Rep B {suffix}",
        display_name=f"NIT Rep B {suffix}",
        code=f"REP-B-{suffix}",
        state="Delhi",
        contact_email=f"repb_{suffix}@example.com",
    )
    db_session.add_all([inst_a, inst_b])
    db_session.commit()

    # 2. Users (Admin, Officer, Auditor, Institution User A)
    user_admin = User(
        id=f"usr-adm-{suffix}",
        email=f"admin_{suffix}@sentinel.gov.in",
        full_name="Admin Test",
        role="SYSTEM_ADMIN",
        password_hash=hash_password("Pass@123"),
        is_active=True,
    )
    user_officer = User(
        id=f"usr-off-{suffix}",
        email=f"officer_{suffix}@sentinel.gov.in",
        full_name="Officer Test",
        role="SCRUTINY_OFFICER",
        password_hash=hash_password("Pass@123"),
        is_active=True,
    )
    user_auditor = User(
        id=f"usr-aud-{suffix}",
        email=f"auditor_{suffix}@sentinel.gov.in",
        full_name="Auditor Test",
        role="AUDITOR",
        password_hash=hash_password("Pass@123"),
        is_active=True,
    )
    user_inst_a = User(
        id=f"usr-insta-{suffix}",
        email=f"inst_a_{suffix}@college.edu",
        full_name="College Registrar A",
        role="INSTITUTION_USER",
        institution_id=inst_a.id,
        password_hash=hash_password("Pass@123"),
        is_active=True,
    )
    db_session.add_all([user_admin, user_officer, user_auditor, user_inst_a])
    db_session.commit()

    today = date.today()

    # 3. Instruments
    # Inst 1: Awaiting verification, has discrepancy, formula injection in bank name
    inst1 = Instrument(
        id=f"fdr-rep-1-{suffix}",
        institution_id=inst_a.id,
        reference_number=f"FDR-REP-01-{suffix}",
        bank_name="=CMD|' /C calc'!A0",  # Test CSV formula injection defense
        branch="Main Branch",
        amount=Decimal("1500000.00"),
        issue_date=today - timedelta(days=60),
        maturity_date=today + timedelta(days=45),  # Upcoming maturity (within 90d)
        status="ACTIVE",
        trust_level="L1_DOCUMENT_CONSISTENT",
        assigned_office="Western Regional Office",
    )
    # Inst 2: Maturing in 20 days with linked renewal
    inst2 = Instrument(
        id=f"fdr-rep-2-{suffix}",
        institution_id=inst_a.id,
        reference_number=f"FDR-REP-02-{suffix}",
        bank_name="State Bank of India",
        branch="Nariman Point",
        amount=Decimal("2500000.00"),
        issue_date=today - timedelta(days=340),
        maturity_date=today + timedelta(days=20),
        status="ACTIVE",
        trust_level="L3_BANK_CONFIRMED",
        assigned_office="Western Regional Office",
    )
    # Inst 3: Overdue and escalated (Institution B)
    inst3 = Instrument(
        id=f"fdr-rep-3-{suffix}",
        institution_id=inst_b.id,
        reference_number=f"FDR-REP-03-{suffix}",
        bank_name="Punjab National Bank",
        branch="Connaught Place",
        amount=Decimal("5000000.00"),
        issue_date=today - timedelta(days=400),
        maturity_date=today - timedelta(days=15),  # Overdue
        status="EXPIRED",
        trust_level="L0_DECLARED",
        assigned_office="Northern Regional Office",
    )
    db_session.add_all([inst1, inst2, inst3])
    db_session.commit()

    # 4. Verification Requests
    # Simulated verification on Inst 1
    vr1 = VerificationRequest(
        id=f"vr-1-{suffix}",
        instrument_id=inst1.id,
        channel="SIMULATED",
        reference_code=f"VR-SIM-{suffix}",
        status="PENDING",
        snapshot_data_json="{}",
        requested_by_user_id=user_officer.id,
    )
    # Failed verification on Inst 3
    vr3 = VerificationRequest(
        id=f"vr-3-{suffix}",
        instrument_id=inst3.id,
        channel="SFMS_GATEWAY",
        reference_code=f"VR-FAIL-{suffix}",
        status="SOURCE_UNAVAILABLE",
        snapshot_data_json="{}",
        requested_by_user_id=user_officer.id,
    )
    db_session.add_all([vr1, vr3])
    db_session.commit()

    # 5. Validation Finding (Missing document on Inst 1)
    vf1 = ValidationFinding(
        id=f"vf-1-{suffix}",
        instrument_id=inst1.id,
        institution_id=inst_a.id,
        finding_fingerprint=f"fp-rep-1-{suffix}",
        rule_id="RULE-DOC-001",
        rule_version="1.0",
        rule_type="DETERMINISTIC",
        category="DOCUMENT_COMPLETENESS",
        severity="HIGH",
        title="Missing FDR physical scan certificate",
        status="OPEN",
        policy_version_ref="1",
    )
    db_session.add(vf1)
    db_session.commit()

    # 6. Renewal Lineage (Inst 2 renewal linked)
    lineage2 = InstrumentLineage(
        id=f"lin-2-{suffix}",
        institution_id=inst_a.id,
        predecessor_instrument_id=inst2.id,
        successor_instrument_id=inst1.id,
        relationship_type="RENEWAL",
        relationship_status="ACTIVE",
        created_by_user_id=user_admin.id,
    )
    db_session.add(lineage2)
    db_session.commit()

    # 7. Lifecycle Evaluation (Inst 3 overdue & escalated)
    eval3 = LifecycleEvaluation(
        id=f"ev-3-{suffix}",
        instrument_id=inst3.id,
        evaluation_date=today,
        days_to_maturity=-15,
        maturity_stage="OVERDUE",
        due_condition="OVERDUE_15D",
        is_overdue=True,
        is_escalated=True,
        escalation_role="BRANCH_HEAD",
        evaluation_timestamp=datetime.now(timezone.utc),
    )
    db_session.add(eval3)
    db_session.commit()

    # 8. Document & Version for Evidence Pack
    doc1 = Document(
        id=f"doc-rep-1-{suffix}",
        institution_id=inst_a.id,
        instrument_id=inst1.id,
        category="FDR_CERTIFICATE",
        status="ACTIVE",
        created_by_user_id=user_admin.id,
    )
    db_session.add(doc1)
    db_session.commit()

    doc_ver1 = DocumentVersion(
        id=f"docver-rep-1-{suffix}",
        document_id=doc1.id,
        version_number=1,
        storage_key=f"storage/key/{suffix}/fdr_scan.pdf",
        original_filename="fdr_scan.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        uploader_user_id=user_admin.id,
    )
    db_session.add(doc_ver1)
    db_session.commit()

    return {
        "suffix": suffix,
        "inst_a": inst_a,
        "inst_b": inst_b,
        "user_admin": user_admin,
        "user_officer": user_officer,
        "user_auditor": user_auditor,
        "user_inst_a": user_inst_a,
        "inst1": inst1,
        "inst2": inst2,
        "inst3": inst3,
    }


def auth_client(client, user):
    """Sets auth cookie on client for the specified user."""
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        institution_id=user.institution_id,
    )
    client.cookies.set(settings.AUTH_COOKIE_NAME, token)
    return client


# ==============================================================================
# TESTS
# ==============================================================================

def test_pending_verification_report_simulation_flag(client, test_data):
    """1. Test Pending Verification report returns records, pending age, and flags simulated requests."""
    cl = auth_client(client, test_data["user_officer"])
    res = cl.get("/api/v1/dashboard/reports/pending-verification")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["report_type"] == "PENDING_VERIFICATION"
    rows = data["rows"]
    matched = [r for r in rows if r["instrument_id"] == test_data["inst1"].id]
    assert len(matched) == 1
    r1 = matched[0]
    assert r1["verification_status"] == "PENDING"
    assert r1["is_simulated"] is True
    assert r1["has_discrepancies"] is True
    assert r1["drill_down_path"] == f"/instruments/{test_data['inst1'].id}"


def test_upcoming_maturities_report_renewal_status(client, test_data):
    """2. Test Upcoming Maturities report adheres to monitoring window and identifies renewal linkage."""
    cl = auth_client(client, test_data["user_officer"])
    res = cl.get("/api/v1/dashboard/reports/upcoming-maturities?window_days=60")
    assert res.status_code == 200
    data = res.json()

    assert data["report_type"] == "UPCOMING_MATURITIES"
    assert "regulatory_notice" in data
    rows = data["rows"]

    # Inst 2 matures in 20 days and has renewal linked
    m2 = next((r for r in rows if r["instrument_id"] == test_data["inst2"].id), None)
    assert m2 is not None
    assert m2["days_to_maturity"] == 20
    assert m2["renewal_status"] == "RENEWAL_LINKED"
    assert m2["successor_instrument_id"] == test_data["inst1"].id

    # Inst 3 is already expired, so must not appear in upcoming maturities (maturity_date >= today)
    m3 = next((r for r in rows if r["instrument_id"] == test_data["inst3"].id), None)
    assert m3 is None


def test_missing_documents_report(client, test_data):
    """3. Test Missing Documents report returns findings with checklist outcomes."""
    cl = auth_client(client, test_data["user_officer"])
    res = cl.get("/api/v1/dashboard/reports/missing-documents")
    assert res.status_code == 200
    data = res.json()

    assert data["report_type"] == "MISSING_DOCUMENTS"
    rows = data["rows"]
    m = next((r for r in rows if r["instrument_id"] == test_data["inst1"].id), None)
    assert m is not None
    assert m["checklist_outcome"] == "MISSING"
    assert m["severity"] == "HIGH"
    assert m["drill_down_path"] == f"/instruments/{test_data['inst1'].id}"


def test_interventions_report_overdue_and_failed(client, test_data):
    """4. Test Interventions report identifies overdue lifecycle and failed/source-unavailable verifications."""
    cl = auth_client(client, test_data["user_admin"])
    res = cl.get("/api/v1/dashboard/reports/interventions")
    assert res.status_code == 200
    data = res.json()

    assert data["report_type"] == "INTERVENTIONS"
    rows = data["rows"]

    # Verify Inst 3 overdue lifecycle escalation appears
    m_overdue = next((r for r in rows if r["entity_id"] == test_data["inst3"].id and r["intervention_type"] == "OVERDUE_ESCALATION"), None)
    assert m_overdue is not None
    assert m_overdue["severity"] in ["HIGH", "CRITICAL"]
    assert "renewal overdue" in m_overdue["reason_description"].lower()

    # Verify Inst 3 source unavailable verification appears
    m_verif = next((r for r in rows if r["entity_id"] == test_data["inst3"].id and r["intervention_type"] == "VERIFICATION_FAILED"), None)
    assert m_verif is not None


def test_cross_institution_isolation(client, test_data):
    """5. Test Institution user cannot view or query records belonging to another institution."""
    cl = auth_client(client, test_data["user_inst_a"])

    # Institution A queries upcoming maturities
    res = cl.get("/api/v1/dashboard/reports/upcoming-maturities")
    assert res.status_code == 200
    data = res.json()
    for row in data["rows"]:
        assert row["institution_id"] == test_data["inst_a"].id

    # Institution A attempts to query interventions for Institution B -> 403 Forbidden & audited
    res2 = cl.get(f"/api/v1/dashboard/reports/interventions?institution_id={test_data['inst_b'].id}")
    assert res2.status_code == 403


def test_secure_csv_export_with_formula_injection_defense(client, test_data, db_session):
    """6. Test CSV export prevents formula injection by prefixing '=...' with single quote and logs audit event."""
    cl = auth_client(client, test_data["user_officer"])
    res = cl.get("/api/v1/dashboard/reports/pending-verification/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "attachment;" in res.headers["content-disposition"]

    csv_text = res.content.decode("utf-8-sig")

    # Header metadata block verification
    assert "# Report Type: PENDING_VERIFICATION" in csv_text
    assert "# Security Classification: CONFIDENTIAL" in csv_text

    # Formula injection defense verification:
    # Inst 1 bank_name is "=CMD|' /C calc'!A0" -> should be encoded as "'=CMD|' /C calc'!A0"
    assert "'=CMD|" in csv_text

    # Audit event verification
    audit = db_session.scalars(
        select(AuditEvent)
        .where(AuditEvent.action == "REPORT_EXPORT_CSV_PENDING_VERIFICATION")
        .order_by(AuditEvent.created_at.desc())
    ).first()
    assert audit is not None
    assert audit.actor_user_id == test_data["user_officer"].id


def test_secure_pdf_export_generation(client, test_data, db_session):
    """7. Test PDF export generates valid PDF bytes with ReportLab layout and logs audit event."""
    cl = auth_client(client, test_data["user_auditor"])
    res = cl.get("/api/v1/dashboard/reports/upcoming-maturities/export/pdf?window_days=90")
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert "attachment;" in res.headers["content-disposition"]

    # Verify standard PDF header magic bytes
    pdf_bytes = res.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000

    # Audit event verification
    audit = db_session.scalars(
        select(AuditEvent)
        .where(AuditEvent.action == "REPORT_EXPORT_PDF_UPCOMING_MATURITIES")
        .order_by(AuditEvent.created_at.desc())
    ).first()
    assert audit is not None
    assert audit.actor_user_id == test_data["user_auditor"].id


def test_audit_evidence_pack_extract(client, test_data):
    """8. Test Audit Evidence Pack extract returns document hashes, observation count, and uncertified disclaimer."""
    cl = auth_client(client, test_data["user_officer"])
    res = cl.get(f"/api/v1/dashboard/reports/evidence-pack/{test_data['inst1'].id}")
    assert res.status_code == 200
    data = res.json()

    assert data["report_type"] == "AUDIT_EVIDENCE_PACK"
    assert data["instrument_id"] == test_data["inst1"].id
    assert len(data["documents"]) >= 1
    assert data["documents"][0]["sha256_hash"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert "certification_disclaimer" in data
    assert "Does not constitute certified external judicial evidence" in data["certification_disclaimer"]
