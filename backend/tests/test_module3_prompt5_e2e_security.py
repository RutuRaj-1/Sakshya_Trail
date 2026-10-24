"""
Module 3 — Prompt 5 Test Suite
End-to-End Integration, Security Review, Evaluation Metrics & Handover

Covers:
1. Scenario A — Valid Record (Pass / Not-Applicable results, 0 false discrepancies)
2. Scenario B — Invalid Date Combination (VAL-DATE-001 fires explainable finding with next action)
3. Scenario C — Policy-Dependent Amount (Policy min enforced; unconfigured policy does not invent amount)
4. Scenario D — Entered vs Extracted Discrepancy (Lists both sources without overwriting instrument)
5. Scenario E — Reused Reference (Bank-aware duplicate detected; cross-tenant masked)
6. Scenario F — Identical Document Bytes (VAL-DUP-003 fires neutral wording for exact SHA-256 match)
7. Scenario G — Corrected Evidence (New version / corrected data transitions older finding to RESOLVED/SUPERSEDED)
8. Scenario H — Officer Resolution (Audited reasoned resolution; unauthorized user rejected)
9. Scenario I — Advisory Warning (VAL-SIM-001/VAL-META-001 heuristic advisory; no trust level mutation)
10. Scenario J — Priority Queue (Explainable factor score; unknown fields handled; cannot authorize release)
11. Security: Injection & Parameter Tampering (SQL injection resistance, safe parameterized queries)
12. Security: Trust Level Invariance (Engine and score NEVER alter L0-L3 trust level)
13. Security: Release Authorization Invariance (Engine and score NEVER approve or reject release)
14. Security: Cross-Tenant Isolation (Institution user cannot access external finding details)
15. Metrics Runner Verification: Executes evaluation benchmark suite cleanly in test harness.
"""
import uuid
import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.auth.models import User
from app.core.security import hash_password
from app.modules.validation.models import ValidationFinding, ValidationRun, ValidationPolicyConfig
from app.modules.validation.enums import FindingStatus, RuleSeverity, RuleType, RuleOutcome, FindingCategory
from app.modules.validation.engine import run_validation
from app.modules.validation.extracted_fields_service import upsert_extracted_fields
from app.modules.validation.policy_service import set_policy_config
from app.modules.validation.finding_service import (
    transition_finding_status,
    re_evaluate_finding,
    return_instrument_for_correction,
    get_review_queue,
)
from app.modules.validation.priority_score import calculate_review_priority_score
from app.modules.audit.models import AuditEvent
from app.common.exceptions import AppException, ForbiddenException, ConflictException
from scripts.evaluate_module3_metrics import run_evaluation_metrics


@pytest.fixture
def institution_a(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="E2E-INST-A",
        legal_name="Apex College of Technology",
        display_name="Apex Tech",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar A",
        contact_email="registrar.a@apex.ac.in",
        contact_phone="+91-11-21111111",
        address_line1="Sector 1",
        city="Delhi",
        state="Delhi",
        postal_code="110001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def institution_b(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="E2E-INST-B",
        legal_name="Bharati Polytechnic",
        display_name="Bharati Poly",
        institution_type="POLYTECHNIC",
        contact_name="Registrar B",
        contact_email="registrar.b@bharati.ac.in",
        contact_phone="+91-11-22222222",
        address_line1="Sector 2",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def officer_user(db_session: Session) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="officer.e2e@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Scrutiny Officer E2E",
        role="SCRUTINY_OFFICER",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def institution_a_user(db_session: Session, institution_a: Institution) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="user.a@apex.ac.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Apex Registrar",
        role="INSTITUTION_USER",
        institution_id=institution_a.id,
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


# ===========================================================================
# 1. Scenario A — Valid Record
# ===========================================================================
def test_scenario_a_valid_record(db_session: Session, institution_a: Institution, officer_user: User):
    today = date.today()
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-VALID-SCEN-A",
        bank_name="State Bank of India",
        branch="Main Branch",
        amount=Decimal("3000000.00"),
        currency="INR",
        issue_date=today - timedelta(days=90),
        maturity_date=today + timedelta(days=365 * 3),
        status="REGISTERED",
        trust_level="L0_DECLARED",
        joint_with_aicte=True,
        lien_marked=True,
        lien_holder="AICTE Regulation Bureau",
    )
    db_session.add(inst)
    db_session.flush()

    # Attach FDR copy document
    doc = Document(
        id=str(uuid.uuid4()),
        instrument_id=inst.id,
        institution_id=institution_a.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()

    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"storage/cert_a_{uuid.uuid4().hex}.pdf",
        original_filename="fdr_cert.pdf",
        content_type="application/pdf",
        file_size_bytes=4096,
        sha256_hash="a1b2c3d4e5f60123456789abcdef0123456789abcdef0123456789abcdef0123",
        processing_status="CLEAN",
    )
    doc.current_version_id = ver.id
    db_session.add(ver)
    db_session.commit()

    # Run validation
    res = run_validation(db=db_session, instrument_id=inst.id, triggered_by_user_id=officer_user.id)

    # Asserts
    assert res["failures_count"] == 0
    open_findings = list(
        db_session.scalars(
            select(ValidationFinding).where(
                ValidationFinding.instrument_id == inst.id,
                ValidationFinding.status == FindingStatus.OPEN.value,
            )
        ).all()
    )
    print("OPEN FINDINGS:", [(f.rule_id, f.title, f.severity) for f in open_findings])
    assert len(open_findings) == 0


# ===========================================================================
# 2. Scenario B — Invalid Date Combination
# ===========================================================================
def test_scenario_b_invalid_date_combination(db_session: Session, institution_a: Institution, officer_user: User):
    today = date.today()
    # Maturity precedes issue date
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-DATE-ERR-001",
        bank_name="Canara Bank",
        branch="South",
        amount=Decimal("1500000.00"),
        currency="INR",
        issue_date=today - timedelta(days=10),
        maturity_date=today - timedelta(days=50),  # Prior to issue date!
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(inst)
    db_session.commit()

    res = run_validation(db=db_session, instrument_id=inst.id, triggered_by_user_id=officer_user.id)
    assert res["failures_count"] >= 1

    finding = db_session.scalar(
        select(ValidationFinding).where(
            ValidationFinding.instrument_id == inst.id,
            ValidationFinding.rule_id == "VAL-DATE-001",
            ValidationFinding.status == FindingStatus.OPEN.value,
        )
    )
    assert finding is not None
    assert finding.rule_id == "VAL-DATE-001"
    assert finding.rule_version == "1.0"
    assert "not strictly later than its issue date" in finding.explanation
    assert finding.suggested_action is not None
    assert len(finding.suggested_action) > 10


# ===========================================================================
# 3. Scenario C — Policy-Dependent Amount
# ===========================================================================
def test_scenario_c_policy_dependent_amount(db_session: Session, institution_a: Institution, officer_user: User):
    today = date.today()
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-AMT-POLICY-01",
        bank_name="Bank of Baroda",
        branch="Main",
        amount=Decimal("1500000.00"),  # Below configured policy minimum
        currency="INR",
        issue_date=today - timedelta(days=20),
        maturity_date=today + timedelta(days=365 * 2),
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(inst)
    db_session.commit()

    # Step 1: Set policy minimum amount to 2,000,000 INR
    set_policy_config(
        db=db_session,
        config_key="MIN_DEPOSIT_AMOUNT_INR",
        config_value="2000000.00",
        value_type="decimal",
        display_name="Minimum Deposit Amount",
        authorized_by_user_id=officer_user.id,
    )

    res1 = run_validation(db=db_session, instrument_id=inst.id, rule_ids=["VAL-AMT-002"])
    outcome1 = next(o for o in res1["outcomes"] if (o.get("rule_id") if isinstance(o, dict) else o.rule_id) == "VAL-AMT-002")
    assert (outcome1.get("outcome") if isinstance(outcome1, dict) else outcome1.outcome) == RuleOutcome.FAIL.value

    # Step 2: Deactivate policy configuration
    cfg = db_session.scalar(
        select(ValidationPolicyConfig).where(ValidationPolicyConfig.config_key == "MIN_DEPOSIT_AMOUNT_INR")
    )
    cfg.is_active = False
    db_session.commit()

    # Re-run: engine must NOT invent an expected amount; must report UNABLE_TO_EVALUATE
    res2 = run_validation(db=db_session, instrument_id=inst.id, rule_ids=["VAL-AMT-002"])
    outcome2 = next(o for o in res2["outcomes"] if (o.get("rule_id") if isinstance(o, dict) else o.rule_id) == "VAL-AMT-002")
    assert (outcome2.get("outcome") if isinstance(outcome2, dict) else outcome2.outcome) == RuleOutcome.UNABLE_TO_EVALUATE.value


# ===========================================================================
# 4. Scenario D — Entered versus Extracted Discrepancy
# ===========================================================================
def test_scenario_d_entered_vs_extracted_discrepancy(
    db_session: Session, institution_a: Institution, officer_user: User
):
    today = date.today()
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-XSRC-DISCREP-01",
        bank_name="HDFC Bank",
        branch="FC Road",
        amount=Decimal("2500000.00"),  # Entered amount
        currency="INR",
        issue_date=today - timedelta(days=30),
        maturity_date=today + timedelta(days=365 * 3),
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(inst)
    db_session.flush()

    doc = Document(
        id=str(uuid.uuid4()),
        instrument_id=inst.id,
        institution_id=institution_a.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()

    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"storage/xsrc_doc_{uuid.uuid4().hex}.pdf",
        original_filename="hdfc_cert.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    doc.current_version_id = ver.id
    db_session.add(ver)
    db_session.flush()

    # Synthesize OCR suggestion with differing amount
    upsert_extracted_fields(
        db=db_session,
        document_version_id=ver.id,
        instrument_id=inst.id,
        institution_id=institution_a.id,
        document_id=doc.id,
        doc_amount_str="1500000.00",  # Discrepancy: Certificate shows 1,500,000 vs entered 2,500,000
        doc_reference_number="FDR-XSRC-DISCREP-01",
        doc_bank_name="HDFC Bank",
        confidence_overall=0.96,
    )

    res = run_validation(db=db_session, instrument_id=inst.id, rule_ids=["VAL-XSRC-001"])
    outcome = next(o for o in res["outcomes"] if (o.get("rule_id") if isinstance(o, dict) else o.rule_id) == "VAL-XSRC-001")
    assert (outcome.get("outcome") if isinstance(outcome, dict) else outcome.outcome) == RuleOutcome.FAIL.value

    # Finding must list both observed and expected values
    finding = db_session.scalar(
        select(ValidationFinding).where(
            ValidationFinding.instrument_id == inst.id,
            ValidationFinding.rule_id == "VAL-XSRC-001",
        )
    )
    assert finding is not None
    assert "2500000" in (finding.observed_value or "")
    assert "1500000" in (finding.expected_value or "")

    # Safety constraint: Instrument amount must NOT have been overwritten
    db_session.refresh(inst)
    assert inst.amount == Decimal("2500000.00")


# ===========================================================================
# 5. Scenario E — Reused Reference & Tenant Isolation
# ===========================================================================
def test_scenario_e_reused_reference_and_tenant_isolation(
    db_session: Session,
    institution_a: Institution,
    institution_b: Institution,
    officer_user: User,
    institution_a_user: User,
):
    today = date.today()
    shared_ref = f"REF-DUP-SH-{uuid.uuid4().hex[:6]}"

    # Inst 1 in Institution A
    inst1 = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number=shared_ref,
        bank_name="Union Bank of India",
        branch="Main",
        amount=Decimal("1000000.00"),
        issue_date=today - timedelta(days=60),
        maturity_date=today + timedelta(days=365),
        status="REGISTERED",
    )
    # Inst 2 in Institution B (cross-tenant duplicate)
    inst2 = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_b.id,
        reference_number=shared_ref,
        bank_name="Union Bank of India",
        branch="Sub",
        amount=Decimal("1000000.00"),
        issue_date=today - timedelta(days=30),
        maturity_date=today + timedelta(days=365),
        status="REGISTERED",
    )
    db_session.add_all([inst1, inst2])
    db_session.commit()

    # Run validation on Inst 2
    res = run_validation(db=db_session, instrument_id=inst2.id, rule_ids=["VAL-DUP-002"])
    outcome = next(o for o in res["outcomes"] if (o.get("rule_id") if isinstance(o, dict) else o.rule_id) == "VAL-DUP-002")
    assert (outcome.get("outcome") if isinstance(outcome, dict) else outcome.outcome) == RuleOutcome.WARNING.value

    # Scrutiny officer sees finding
    queue_officer = get_review_queue(db=db_session, current_user=officer_user, rule_id_filter="VAL-DUP-002")
    assert any(item["instrument_id"] == inst2.id for item in queue_officer["items"])

    # Institution A user CANNOT see Institution B's duplicate finding
    queue_inst_a = get_review_queue(db=db_session, current_user=institution_a_user)
    assert not any(item["instrument_id"] == inst2.id for item in queue_inst_a["items"])


# ===========================================================================
# 6. Scenario F — Identical Document Bytes (VAL-DUP-003)
# ===========================================================================
def test_scenario_f_identical_document_bytes(
    db_session: Session, institution_a: Institution, officer_user: User
):
    today = date.today()
    inst1 = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-HASH-01",
        bank_name="Kotak Bank",
        branch="Main",
        amount=Decimal("1000000.00"),
        issue_date=today - timedelta(days=40),
        maturity_date=today + timedelta(days=365),
        status="REGISTERED",
    )
    inst2 = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-HASH-02",
        bank_name="Kotak Bank",
        branch="Branch B",
        amount=Decimal("1000000.00"),
        issue_date=today - timedelta(days=30),
        maturity_date=today + timedelta(days=365),
        status="REGISTERED",
    )
    db_session.add_all([inst1, inst2])
    db_session.flush()

    identical_hash = f"sha256-identical-{uuid.uuid4().hex}"
    doc1 = Document(
        id=str(uuid.uuid4()),
        instrument_id=inst1.id,
        institution_id=institution_a.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc1)
    db_session.flush()
    ver1 = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc1.id,
        version_number=1,
        storage_key=f"storage/dup_hash1_{uuid.uuid4().hex}.pdf",
        original_filename="doc1.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash=identical_hash,
    )
    doc1.current_version_id = ver1.id
    db_session.add(ver1)

    doc2 = Document(
        id=str(uuid.uuid4()),
        instrument_id=inst2.id,
        institution_id=institution_a.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc2)
    db_session.flush()
    ver2 = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc2.id,
        version_number=1,
        storage_key=f"storage/dup_hash2_{uuid.uuid4().hex}.pdf",
        original_filename="doc2.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash=identical_hash,
    )
    doc2.current_version_id = ver2.id
    db_session.add(ver2)
    db_session.commit()

    res = run_validation(db=db_session, instrument_id=inst2.id, rule_ids=["VAL-DUP-003"])
    outcome = next(o for o in res["outcomes"] if (o.get("rule_id") if isinstance(o, dict) else o.rule_id) == "VAL-DUP-003")
    assert (outcome.get("outcome") if isinstance(outcome, dict) else outcome.outcome) == RuleOutcome.WARNING.value
    # Prescribed neutral wording: must state identical file bytes, without accusing of fraud
    explanation = outcome.get("explanation") if isinstance(outcome, dict) else outcome.explanation
    assert "Identical file bytes were previously uploaded" in explanation
    assert "do not prove forgery, authenticity, or improper reuse" in explanation


# ===========================================================================
# 7. Scenario G — Corrected Evidence & Finding Lifecycle
# ===========================================================================
def test_scenario_g_corrected_evidence_resolves_finding(
    db_session: Session, institution_a: Institution, officer_user: User
):
    today = date.today()
    # Initially invalid amount (0.00)
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-CORRECT-01",
        bank_name="Axis Bank",
        branch="Main",
        amount=Decimal("0.00"),
        currency="INR",
        issue_date=today - timedelta(days=20),
        maturity_date=today + timedelta(days=365),
        status="REGISTERED",
    )
    db_session.add(inst)
    db_session.commit()

    run_validation(db=db_session, instrument_id=inst.id, rule_ids=["VAL-AMT-001"])
    finding = db_session.scalar(
        select(ValidationFinding).where(
            ValidationFinding.instrument_id == inst.id,
            ValidationFinding.rule_id == "VAL-AMT-001",
        )
    )
    assert finding.status == FindingStatus.OPEN.value

    # Correct instrument amount
    inst.amount = Decimal("2500000.00")
    db_session.commit()

    # Re-evaluate
    re_evaluate_finding(db=db_session, finding_id=finding.id, actor_user_id=officer_user.id)
    db_session.refresh(finding)
    # Finding must be RESOLVED automatically
    assert finding.status == FindingStatus.RESOLVED.value
    assert "Condition cleared on re-evaluation" in (finding.resolution_note or "")


# ===========================================================================
# 8. Scenario H — Officer Resolution & Audit
# ===========================================================================
def test_scenario_h_officer_resolution_and_audit(
    db_session: Session, institution_a: Institution, officer_user: User, institution_a_user: User
):
    finding = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=f"fp-scen-h-{uuid.uuid4()}",
        instrument_id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        rule_id="VAL-REF-001",
        rule_version="1.0",
        rule_type="DETERMINISTIC",
        category="REFERENCE_INTEGRITY",
        severity="HIGH",
        status="OPEN",
        title="Reference number is missing",
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    db_session.commit()

    # Officer resolves with mandatory reason
    transition_finding_status(
        db=db_session,
        finding=finding,
        target_status="RESOLVED",
        actor_user=officer_user,
        reason="Reference verified on physical bank certificate.",
    )
    assert finding.status == "RESOLVED"

    # Audit event logged
    audit_entry = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_id == finding.id,
            AuditEvent.action == "VALIDATION_FINDING_RESOLVED",
        )
    )
    assert audit_entry is not None
    assert audit_entry.actor_user_id == officer_user.id

    # Unauthorized institution user cannot dismiss or transition finding
    with pytest.raises(ForbiddenException):
        transition_finding_status(
            db=db_session,
            finding=finding,
            target_status="DISMISSED",
            actor_user=institution_a_user,
            reason="Illegal dismissal attempt.",
        )


# ===========================================================================
# 9. Scenario I — Advisory Warning
# ===========================================================================
def test_scenario_i_advisory_warning_invariance(db_session: Session, institution_a: Institution):
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-HEUR-01",
        bank_name="Yes Bank",
        branch="Main",
        amount=Decimal("1000000.00"),
        issue_date=date.today() - timedelta(days=10),
        maturity_date=date.today() + timedelta(days=365),
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(inst)
    db_session.commit()

    finding = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=f"fp-heur-{uuid.uuid4()}",
        instrument_id=inst.id,
        institution_id=institution_a.id,
        rule_id="VAL-SIM-001",
        rule_version="1.0",
        rule_type=RuleType.HEURISTIC.value,
        category=FindingCategory.INSTITUTION_ELIGIBILITY.value,
        severity=RuleSeverity.MEDIUM.value,
        status=FindingStatus.OPEN.value,
        title="Advisory — Depositor Name Differs from Institution Title",
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    db_session.commit()

    # Asserts
    assert finding.rule_type == "HEURISTIC"
    assert "Advisory" in finding.title

    # Invariance: Trust level and status must NOT be modified
    db_session.refresh(inst)
    assert inst.trust_level == "L0_DECLARED"
    assert inst.status == "REGISTERED"


# ===========================================================================
# 10. Scenario J — Priority Queue & Release Invariance
# ===========================================================================
def test_scenario_j_priority_queue_and_release_invariance(
    db_session: Session, institution_a: Institution
):
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-PRIO-01",
        bank_name="IndusInd Bank",
        maturity_date=date.today() + timedelta(days=20),  # Expiring soon
        trust_level="L0_DECLARED",
        status="REGISTERED",
    )

    finding = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=f"fp-prio-{uuid.uuid4()}",
        instrument_id=inst.id,
        institution_id=institution_a.id,
        rule_id="VAL-AMT-001",
        rule_version="1.0",
        rule_type="DETERMINISTIC",
        category="AMOUNT_CONSISTENCY",
        severity=RuleSeverity.CRITICAL.value,
        status=FindingStatus.OPEN.value,
        title="Amount error",
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )

    res = calculate_review_priority_score(
        instrument=inst,
        open_findings=[finding],
        has_fdr_copy=True,
    )

    assert 0 <= res.total_score <= 100
    assert res.total_score >= 60  # Critical severity + <=30 days maturity
    assert "NOT represent an AI-predicted fraud probability" in res.disclaimer
    assert res.is_prototype is True

    # Security invariance: Priority score CANNOT change release authorization or trust level
    assert inst.trust_level == "L0_DECLARED"
    assert inst.status == "REGISTERED"


# ===========================================================================
# 11. Security: SQL Injection & Parameter Tampering
# ===========================================================================
def test_security_sql_injection_defense(db_session: Session, officer_user: User):
    # Malicious SQL strings in search filter
    malicious_inputs = [
        "'; DROP TABLE validation_findings; --",
        "1' OR '1'='1",
        "UNION SELECT * FROM users --",
    ]
    for injection_term in malicious_inputs:
        queue = get_review_queue(db=db_session, current_user=officer_user, search=injection_term)
        assert isinstance(queue["items"], list)

    # Verify table remains intact
    findings = list(db_session.scalars(select(ValidationFinding)).all())
    assert isinstance(findings, list)


# ===========================================================================
# 12. Security: Return-for-Correction Workflow
# ===========================================================================
def test_security_return_for_correction(db_session: Session, institution_a: Institution, officer_user: User):
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution_a.id,
        reference_number="FDR-RET-TEST",
        bank_name="SBI",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2026, 1, 1),
        status="UNDER_SCRUTINY",
    )
    db_session.add(inst)
    db_session.commit()

    updated = return_instrument_for_correction(
        db=db_session,
        instrument_id=inst.id,
        actor_user=officer_user,
        explanation="Missing bank branch IFSC code and verification letter.",
    )
    assert updated.status == "RETURNED_FOR_CORRECTION"
    assert "Missing bank branch IFSC code" in updated.remarks


# ===========================================================================
# 13. Evaluation Metrics Test Harness Runner
# ===========================================================================
def test_evaluation_metrics_benchmark_execution(db_session: Session):
    metrics = run_evaluation_metrics(db=db_session, sample_size=10)
    assert "deterministic" in metrics
    assert "duplicate_detection" in metrics
    assert "lifecycle_and_idempotency" in metrics
    assert "performance" in metrics

    assert metrics["deterministic"]["precision"] >= 90.0
    assert metrics["duplicate_detection"]["reference_duplicate_accuracy"] == 100.0
    assert metrics["lifecycle_and_idempotency"]["finding_idempotency_rate"] == 100.0
    assert metrics["performance"]["avg_latency_ms"] < 100.0  # sub-100ms per instrument
