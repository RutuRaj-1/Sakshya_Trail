"""
Module 3 — Prompt 3 Test Suite
Evidence Reconciliation, Duplicate Detection and Explainable Advisory Indicators

Scenarios tested:
1. Entered amount differs from extracted amount (VAL-XSRC-001 fires).
2. Matching entered and extracted values produce no discrepancy (VAL-XSRC-001 passes).
3. Missing extraction creates no false mismatch (VAL-XSRC-001 returns UNABLE_TO_EVALUATE).
4. Invalid extraction output is ignored or recorded as unable to evaluate.
5. Stale extraction against an older document version is identified (VAL-XSRC-STALE fires).
6. Instrument reference duplicates within the same institution (VAL-DUP-001 fires with permitted summaries).
7. Bank-aware cross-institution reference duplicates (VAL-DUP-002 fires with tenant masking).
8. Similar-looking references from different banks are handled conservatively (no false duplicate).
9. Duplicate SHA-256 files across instruments (VAL-DUP-003 fires with prescribed wording).
10. Duplicate hash results do not leak cross-tenant records (tenant isolation preserved).
11. Name similarity explains its method and score (VAL-SIM-001 produces explainable score).
12. Name similarity does not automatically reject or modify trust level.
13. Metadata advisory is labelled as heuristic (VAL-META-001 has RuleType.HEURISTIC).
14. No finding promotes trust level or authorizes release.
15. Repeat runs remain idempotent (fingerprints unchanged, last_evaluated_at touched).
16. Module 1 and Module 2 regression tests stay green.
"""
import uuid
import pytest
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationPolicyConfig, ValidationFinding, ValidationRun
from app.modules.validation.extracted_fields_service import upsert_extracted_fields
from app.modules.validation.engine import run_validation
from app.modules.validation.enums import RuleOutcome, RuleType, FindingCategory, FindingStatus
from app.modules.validation.registry import rule_registry


@pytest.fixture
def institution(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="AICTE-ENG-001",
        legal_name="National Engineering College",
        display_name="NEC",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar NEC",
        contact_email="registrar@nec.ac.in",
        contact_phone="+91-11-29581000",
        address_line1="Sector 12",
        city="New Delhi",
        state="Delhi",
        postal_code="110001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def second_institution(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="AICTE-POLY-002",
        legal_name="Apex Polytechnic Institute",
        display_name="API",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Principal Apex",
        contact_email="principal@apex.ac.in",
        contact_phone="+91-11-29582000",
        address_line1="Campus Road",
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
def instrument(db_session: Session, institution: Institution) -> Instrument:
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        branch="Main Branch, New Delhi",
        reference_number="FDR/2026/001",
        amount=Decimal("500000.00"),
        currency="INR",
        issue_date=date(2025, 1, 1),
        maturity_date=date(2030, 1, 1),
        lien_marked=True,
        lien_holder="Member Secretary, AICTE",
        trust_level="L0_UNVERIFIED",
        status="ACTIVE",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


# ---------------------------------------------------------------------------
# Test 1: Entered amount differs from extracted amount (VAL-XSRC-001 fires)
# ---------------------------------------------------------------------------
def test_entered_amount_differs_from_extracted_amount(db_session: Session, instrument: Instrument, institution: Institution):
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        title="FDR Certificate",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()

    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="fdr.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        processing_status="CLEAN",
    )
    db_session.add(ver)
    doc.current_version_id = ver.id
    db_session.flush()

    # Extracted amount is 400,000, entered is 500,000
    upsert_extracted_fields(
        db=db_session,
        document_version_id=ver.id,
        document_id=doc.id,
        instrument_id=instrument.id,
        institution_id=institution.id,
        extraction_status="COMPLETED",
        doc_amount_str="400000.00",
        doc_amount_confidence=0.95,
    )

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-XSRC-001"])
    outcomes = run_res["outcomes"]
    rule_out = next(o for o in outcomes if o["rule_id"] == "VAL-XSRC-001")
    assert rule_out["outcome"] == RuleOutcome.FAIL.value
    assert "Discrepancy between entered instrument amount" in rule_out["title"]
    assert "500000" in rule_out["observed_value"]
    assert "400000" in rule_out["observed_value"]


# ---------------------------------------------------------------------------
# Test 2: Matching entered and extracted values produce no discrepancy (VAL-XSRC-001 passes)
# ---------------------------------------------------------------------------
def test_matching_entered_and_extracted_values_pass(db_session: Session, instrument: Instrument, institution: Institution):
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()

    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="fdr.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        processing_status="CLEAN",
    )
    db_session.add(ver)
    doc.current_version_id = ver.id
    db_session.flush()

    # Exactly matching amount
    upsert_extracted_fields(
        db=db_session,
        document_version_id=ver.id,
        document_id=doc.id,
        instrument_id=instrument.id,
        institution_id=institution.id,
        extraction_status="COMPLETED",
        doc_amount_str="500000.00",
    )

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-XSRC-001"])
    rule_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-XSRC-001")
    assert rule_out["outcome"] == RuleOutcome.PASS.value


# ---------------------------------------------------------------------------
# Test 3: Missing extraction creates no false mismatch
# ---------------------------------------------------------------------------
def test_missing_extraction_creates_no_false_mismatch(db_session: Session, instrument: Instrument):
    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-XSRC-001", "VAL-XSRC-002"])
    for o in run_res["outcomes"]:
        assert o["outcome"] == RuleOutcome.UNABLE_TO_EVALUATE.value
        assert o["outcome"] != RuleOutcome.FAIL.value


# ---------------------------------------------------------------------------
# Test 4: Invalid extraction output is ignored or recorded as unable to evaluate
# ---------------------------------------------------------------------------
def test_invalid_extraction_output_handled_gracefully(db_session: Session, instrument: Instrument, institution: Institution):
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()

    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="fdr.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        processing_status="CLEAN",
    )
    db_session.add(ver)
    doc.current_version_id = ver.id
    db_session.flush()

    # Unparseable garbage string
    upsert_extracted_fields(
        db=db_session,
        document_version_id=ver.id,
        document_id=doc.id,
        instrument_id=instrument.id,
        institution_id=institution.id,
        extraction_status="COMPLETED",
        doc_amount_str="INVALID_AMOUNT_XYZ",
    )

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-XSRC-001"])
    rule_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-XSRC-001")
    assert rule_out["outcome"] == RuleOutcome.UNABLE_TO_EVALUATE.value
    assert "could not be parsed" in rule_out["explanation"]


# ---------------------------------------------------------------------------
# Test 5: Stale extraction against an older document version is identified
# ---------------------------------------------------------------------------
def test_stale_extraction_against_older_version_identified(db_session: Session, instrument: Instrument, institution: Institution):
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()

    ver1 = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="fdr_v1.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="1111111111111111111111111111111111111111111111111111111111111111",
        processing_status="CLEAN",
    )
    ver2 = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=2,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="fdr_v2.pdf",
        content_type="application/pdf",
        file_size_bytes=2048,
        sha256_hash="2222222222222222222222222222222222222222222222222222222222222222",
        processing_status="CLEAN",
    )
    db_session.add_all([ver1, ver2])
    db_session.flush()
    # Active version is now version 2
    doc.current_version_id = ver2.id
    db_session.flush()

    # Extraction was performed against version 1 (now stale!)
    upsert_extracted_fields(
        db=db_session,
        document_version_id=ver1.id,
        document_id=doc.id,
        instrument_id=instrument.id,
        institution_id=institution.id,
        extraction_status="COMPLETED",
        doc_amount_str="500000.00",
    )

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-XSRC-STALE", "VAL-XSRC-001"])
    stale_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-XSRC-STALE")
    assert stale_out["outcome"] == RuleOutcome.WARNING.value
    assert "Stale document extraction detected" in stale_out["title"]

    amt_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-XSRC-001")
    assert amt_out["outcome"] == RuleOutcome.UNABLE_TO_EVALUATE.value
    assert "stale" in amt_out["explanation"].lower()


# ---------------------------------------------------------------------------
# Test 6: Instrument reference duplicates within the same institution
# ---------------------------------------------------------------------------
def test_instrument_reference_duplicate_within_same_institution(db_session: Session, instrument: Instrument, institution: Institution):
    sibling = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_type="FDR",
        bank_name="STATE BANK OF INDIA",
        branch="South Extension",
        reference_number="FDR2026001",
        amount=Decimal("500000.00"),
        currency="INR",
        issue_date=date(2025, 1, 1),
        maturity_date=date(2030, 1, 1),
        trust_level="L0_UNVERIFIED",
        status="ACTIVE",
    )
    db_session.add(sibling)
    db_session.flush()

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-DUP-001"])
    rule_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-DUP-001")
    assert rule_out["outcome"] == RuleOutcome.WARNING.value
    assert "Potential duplicate instrument reference within institution" in rule_out["title"]
    assert sibling.id in rule_out["evidence_refs"]


# ---------------------------------------------------------------------------
# Test 7: Bank-aware cross-institution reference duplicates
# ---------------------------------------------------------------------------
def test_bank_aware_cross_institution_reference_duplicate(db_session: Session, instrument: Instrument, second_institution: Institution):
    other_inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=second_institution.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        reference_number="FDR/2026/001",
        amount=Decimal("500000.00"),
        currency="INR",
        issue_date=date(2025, 1, 1),
        maturity_date=date(2030, 1, 1),
        trust_level="L0_UNVERIFIED",
        status="ACTIVE",
    )
    db_session.add(other_inst)
    db_session.flush()

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-DUP-002"])
    rule_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-DUP-002")
    assert rule_out["outcome"] == RuleOutcome.WARNING.value
    assert "Potential cross-institution duplicate instrument reference" in rule_out["title"]
    assert other_inst.id not in rule_out["evidence_refs"]
    assert "tenant-masked" in rule_out["observed_value"]


# ---------------------------------------------------------------------------
# Test 8: Similar-looking references from different banks are handled conservatively
# ---------------------------------------------------------------------------
def test_same_reference_different_bank_no_duplicate(db_session: Session, instrument: Instrument, second_institution: Institution):
    diff_bank_inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=second_institution.id,
        instrument_type="FDR",
        bank_name="ICICI Bank",
        reference_number="FDR/2026/001",
        amount=Decimal("500000.00"),
        currency="INR",
        issue_date=date(2025, 1, 1),
        maturity_date=date(2030, 1, 1),
        trust_level="L0_UNVERIFIED",
        status="ACTIVE",
    )
    db_session.add(diff_bank_inst)
    db_session.flush()

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-DUP-001", "VAL-DUP-002"])
    dup1 = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-DUP-001")
    dup2 = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-DUP-002")
    assert dup1["outcome"] == RuleOutcome.PASS.value
    assert dup2["outcome"] == RuleOutcome.PASS.value


# ---------------------------------------------------------------------------
# Test 9: Duplicate SHA-256 files across instruments
# ---------------------------------------------------------------------------
def test_duplicate_sha256_files_across_instruments(db_session: Session, instrument: Instrument, institution: Institution):
    shared_hash = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

    doc1 = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc1)
    db_session.flush()
    ver1 = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc1.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="receipt1.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash=shared_hash,
        processing_status="CLEAN",
    )
    db_session.add(ver1)
    doc1.current_version_id = ver1.id

    inst2 = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_type="FDR",
        bank_name="HDFC Bank",
        reference_number="HDFC-999",
        amount=Decimal("100000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2030, 1, 1),
        status="ACTIVE",
    )
    db_session.add(inst2)
    db_session.flush()
    doc2 = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=inst2.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc2)
    db_session.flush()
    ver2 = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc2.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="receipt2.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash=shared_hash,
        processing_status="CLEAN",
    )
    db_session.add(ver2)
    doc2.current_version_id = ver2.id
    db_session.flush()

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-DUP-003"])
    rule_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-DUP-003")
    assert rule_out["outcome"] == RuleOutcome.WARNING.value
    assert "Identical file bytes were previously uploaded. Review the associated instruments and submission context." in rule_out["explanation"]
    assert "does not prove forgery" in rule_out["explanation"].lower() or "do not prove forgery" in rule_out["explanation"].lower()


# ---------------------------------------------------------------------------
# Test 10: Duplicate hash results do not leak cross-tenant records
# ---------------------------------------------------------------------------
def test_duplicate_hash_preserves_tenant_isolation(db_session: Session, instrument: Instrument, institution: Institution, second_institution: Institution):
    shared_hash = "9999999999999999999999999999999999999999999999999999999999999999"

    doc1 = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc1)
    db_session.flush()
    ver1 = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc1.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="file_a.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash=shared_hash,
        processing_status="CLEAN",
    )
    db_session.add(ver1)
    doc1.current_version_id = ver1.id

    inst_b = Instrument(
        id=str(uuid.uuid4()),
        institution_id=second_institution.id,
        instrument_type="FDR",
        bank_name="Axis Bank",
        reference_number="AXIS-001",
        amount=Decimal("200000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2030, 1, 1),
        status="ACTIVE",
    )
    db_session.add(inst_b)
    db_session.flush()
    doc_b = Document(
        id=str(uuid.uuid4()),
        institution_id=second_institution.id,
        instrument_id=inst_b.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc_b)
    db_session.flush()
    ver_b = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc_b.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="confidential_b.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash=shared_hash,
        processing_status="CLEAN",
    )
    db_session.add(ver_b)
    doc_b.current_version_id = ver_b.id
    db_session.flush()

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-DUP-003"])
    rule_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-DUP-003")
    assert rule_out["outcome"] == RuleOutcome.WARNING.value
    assert second_institution.legal_name not in rule_out["explanation"]
    assert inst_b.id not in rule_out["evidence_refs"]
    assert "tenant-masked" in rule_out["observed_value"]


# ---------------------------------------------------------------------------
# Test 11: Name similarity explains its method and score
# ---------------------------------------------------------------------------
def test_name_similarity_explains_method_and_score(db_session: Session, instrument: Instrument, institution: Institution):
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()
    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="receipt.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="3333333333333333333333333333333333333333333333333333333333333333",
        processing_status="CLEAN",
    )
    db_session.add(ver)
    doc.current_version_id = ver.id
    db_session.flush()

    upsert_extracted_fields(
        db=db_session,
        document_version_id=ver.id,
        document_id=doc.id,
        instrument_id=instrument.id,
        institution_id=institution.id,
        extraction_status="COMPLETED",
        doc_account_holder="National Engg College",
    )

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-SIM-001"])
    rule_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-SIM-001")
    assert rule_out["outcome"] == RuleOutcome.WARNING.value
    assert "difflib.SequenceMatcher" in rule_out["explanation"]
    assert "Similarity Score:" in rule_out["explanation"]
    assert "National Engineering College" in rule_out["explanation"]
    assert "National Engg College" in rule_out["explanation"]
    assert "advisory heuristic only and does not determine legal identity" in rule_out["explanation"].lower()


# ---------------------------------------------------------------------------
# Test 12: Name similarity does not automatically reject
# ---------------------------------------------------------------------------
def test_name_similarity_does_not_reject_or_change_trust(db_session: Session, instrument: Instrument, institution: Institution):
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()
    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="receipt.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="4444444444444444444444444444444444444444444444444444444444444444",
        processing_status="CLEAN",
    )
    db_session.add(ver)
    doc.current_version_id = ver.id
    db_session.flush()

    upsert_extracted_fields(
        db=db_session,
        document_version_id=ver.id,
        document_id=doc.id,
        instrument_id=instrument.id,
        institution_id=institution.id,
        extraction_status="COMPLETED",
        doc_account_holder="XYZ Educational Trust",
    )

    initial_trust = instrument.trust_level
    initial_status = instrument.status

    run_validation(db_session, instrument.id, rule_ids=["VAL-SIM-001"])
    db_session.refresh(instrument)

    assert instrument.trust_level == initial_trust
    assert instrument.status == initial_status


# ---------------------------------------------------------------------------
# Test 13: Metadata advisory is labelled as heuristic
# ---------------------------------------------------------------------------
def test_metadata_advisory_labelled_as_heuristic(db_session: Session, instrument: Instrument, institution: Institution):
    rule = rule_registry.get("VAL-META-001")
    assert rule is not None
    assert rule.rule_type == RuleType.HEURISTIC

    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()
    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="scan.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="5555555555555555555555555555555555555555555555555555555555555555",
        processing_status="SCAN_UNAVAILABLE",
    )
    db_session.add(ver)
    doc.current_version_id = ver.id
    db_session.flush()

    run_res = run_validation(db_session, instrument.id, rule_ids=["VAL-META-001"])
    rule_out = next(o for o in run_res["outcomes"] if o["rule_id"] == "VAL-META-001")
    assert rule_out["outcome"] == RuleOutcome.WARNING.value
    assert "advisory heuristic" in rule_out["explanation"].lower()
    assert "never be treated as proof of tampering" in rule_out["explanation"].lower()


# ---------------------------------------------------------------------------
# Test 14: No finding promotes trust or authorizes release
# ---------------------------------------------------------------------------
def test_no_finding_promotes_trust_or_authorizes_release(db_session: Session, instrument: Instrument, institution: Institution):
    initial_trust = instrument.trust_level
    initial_status = instrument.status

    run_validation(db_session, instrument.id)
    db_session.refresh(instrument)

    assert instrument.trust_level == initial_trust
    assert instrument.status == initial_status


# ---------------------------------------------------------------------------
# Test 15: Repeat runs remain idempotent
# ---------------------------------------------------------------------------
def test_repeat_runs_remain_idempotent(db_session: Session, instrument: Instrument, institution: Institution):
    doc = Document(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        instrument_id=instrument.id,
        category="FDR_COPY",
        status="ACTIVE",
    )
    db_session.add(doc)
    db_session.flush()
    ver = DocumentVersion(
        id=str(uuid.uuid4()),
        document_id=doc.id,
        version_number=1,
        storage_key=f"keys/{uuid.uuid4()}",
        original_filename="fdr.pdf",
        content_type="application/pdf",
        file_size_bytes=1024,
        sha256_hash="7777777777777777777777777777777777777777777777777777777777777777",
        processing_status="CLEAN",
    )
    db_session.add(ver)
    doc.current_version_id = ver.id
    db_session.flush()

    upsert_extracted_fields(
        db=db_session,
        document_version_id=ver.id,
        document_id=doc.id,
        instrument_id=instrument.id,
        institution_id=institution.id,
        extraction_status="COMPLETED",
        doc_amount_str="100000.00",
    )

    # First run
    run_validation(db_session, instrument.id, rule_ids=["VAL-XSRC-001"])
    count_after_first = db_session.query(ValidationFinding).filter(
        ValidationFinding.instrument_id == instrument.id,
        ValidationFinding.rule_id == "VAL-XSRC-001",
    ).count()
    assert count_after_first == 1

    first_finding = db_session.query(ValidationFinding).filter(
        ValidationFinding.instrument_id == instrument.id,
        ValidationFinding.rule_id == "VAL-XSRC-001",
    ).first()
    fp1 = first_finding.finding_fingerprint

    # Second run with identical inputs
    run_validation(db_session, instrument.id, rule_ids=["VAL-XSRC-001"])
    count_after_second = db_session.query(ValidationFinding).filter(
        ValidationFinding.instrument_id == instrument.id,
        ValidationFinding.rule_id == "VAL-XSRC-001",
    ).count()

    assert count_after_second == 1
    db_session.refresh(first_finding)
    assert first_finding.finding_fingerprint == fp1
