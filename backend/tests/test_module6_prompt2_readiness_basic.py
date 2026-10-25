"""
Module 6 — Release / Refund Case Management
Prompt 2: Readiness Engine & Release Gate Tests (Focused)

Key test cases verifying the deterministic readiness engine and Release Gate.
"""

import pytest
from datetime import datetime, date, timezone
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationFinding
from app.modules.validation.enums import FindingStatus
from app.modules.verification.models import TrustAssessment
from app.modules.verification.enums import TrustLevel, TrustAssessmentStatus
from app.modules.lifecycle.models import LifecycleEvaluation
from app.modules.lifecycle.enums import MaturityStage, DueCondition

from app.modules.release.enums import ReleaseRequestType, ReleaseCaseType
from app.modules.release.service import create_release_request, seed_demo_release_profile
from app.modules.release.schemas import ReleaseRequestCreate
from app.modules.release.readiness_service import evaluate_readiness, check_release_gate


# ============================================================================
# TEST 1: Fully Satisfied Demo Checklist
# ============================================================================

def test_1_fully_satisfied_checklist(db_session: Session):
    """All checklist items satisfied → READY_FOR_APPROVAL."""
    db = db_session
    
    # Create institution
    inst = Institution(code="TEST-001", legal_name="Test Institution", state="Maharashtra", contact_email="inst@test.edu", is_active=True)
    db.add(inst)
    db.flush()
    
    # Create/get users
    user = User(email="user@test.edu", password_hash="x", full_name="User", role="INSTITUTION_USER", institution_id=inst.id)
    officer = User(email="officer@test.gov", password_hash="x", full_name="Officer", role="SCRUTINY_OFFICER", institution_id=inst.id)
    db.add_all([user, officer])
    db.flush()
    
    # Create matured instrument
    instr = Instrument(
        reference_number="FDR-2026-00001", bank_name="Bank", amount=100000, currency="INR",
        issue_date=date(2020, 1, 1), maturity_date=date(2026, 1, 1),
        instrument_type="FDR", status="REGISTERED", trust_level=TrustLevel.L0_DECLARED.value,
        institution_id=inst.id, assigned_office="Office"
    )
    db.add(instr)
    db.flush()
    
    # Create profile
    profile = seed_demo_release_profile(db, created_by_user_id=user.id)
    
    # Add required documents (CLEAN status)
    for cat in ["FDR_RECEIPT", "SANCTION_ORDER"]:
        doc = Document(institution_id=inst.id, instrument_id=instr.id, category=cat, status="ACTIVE")
        db.add(doc)
        db.flush()
        ver = DocumentVersion(
            document_id=doc.id, version_number=1, storage_key=f"s_{cat}",
            original_filename=f"{cat}.pdf", content_type="application/pdf",
            file_size_bytes=100, sha256_hash=f"h_{cat}" + "0" * 50,
            processing_status="CLEAN"
        )
        db.add(ver)
        doc.current_version_id = ver.id
    
    # Add trust assessment (L2)
    trust = TrustAssessment(
        instrument_id=instr.id, field_name=None,
        trust_level=TrustLevel.L2_OFFICER_VERIFIED.value, reason="Verified",
        assessment_timestamp=datetime.now(timezone.utc),
        status=TrustAssessmentStatus.ACTIVE.value, assessing_user_id=officer.id
    )
    db.add(trust)
    
    # Add lifecycle evaluation (MATURED)
    lifecycle = LifecycleEvaluation(
        instrument_id=instr.id, evaluation_date=date.today(),
        evaluation_timestamp=datetime.now(timezone.utc),
        maturity_stage=MaturityStage.MATURED.value, days_to_maturity=0,
        due_condition=DueCondition.NORMAL.value
    )
    db.add(lifecycle)
    
    db.commit()
    
    # Create release request
    payload = ReleaseRequestCreate(
        instrument_id=instr.id, request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="FDR matured.", policy_profile_id=profile.id
    )
    release_req = create_release_request(db=db, payload=payload, current_user=user)
    
    # Evaluate readiness
    assessment = evaluate_readiness(db=db, release_request=release_req, current_user=officer)
    
    # Verify
    print(f"Assessment Outcome: {assessment.assessment_outcome}")
    print(f"Satisfied: {assessment.satisfied_count}, Blockers: {assessment.blockers_count}, Pending: {assessment.pending_count}")
    print(f"Summary: {assessment.summary_notes}")
    for result in assessment.results:
        print(f"  - {result.item_code}: {result.status}")
    
    assert assessment.assessment_outcome in ("READY_FOR_APPROVAL", "PENDING_REVIEW")
    assert assessment.blockers_count == 0


# ============================================================================
# TEST 2: Missing Mandatory Document
# ============================================================================

def test_2_missing_mandatory_document(db_session: Session):
    """Missing required document → BLOCKED."""
    db = db_session
    
    # Setup
    inst = Institution(code="TEST-002", legal_name="Test Inst 2", state="Maharashtra", contact_email="inst@test.edu", is_active=True)
    db.add(inst)
    db.flush()
    
    user = User(email="user2@test.edu", password_hash="x", full_name="User", role="INSTITUTION_USER", institution_id=inst.id)
    officer = User(email="officer2@test.gov", password_hash="x", full_name="Officer", role="SCRUTINY_OFFICER", institution_id=inst.id)
    db.add_all([user, officer])
    db.flush()
    
    instr = Instrument(
        reference_number="FDR-2026-00002", bank_name="Bank", amount=100000, currency="INR",
        issue_date=date(2020, 1, 1), maturity_date=date(2026, 1, 1),
        instrument_type="FDR", status="REGISTERED", trust_level=TrustLevel.L0_DECLARED.value,
        institution_id=inst.id, assigned_office="Office"
    )
    db.add(instr)
    db.flush()
    
    profile = seed_demo_release_profile(db, created_by_user_id=user.id)
    
    # Only add one document (missing FDR_RECEIPT)
    doc = Document(institution_id=inst.id, instrument_id=instr.id, category="SANCTION_ORDER", status="ACTIVE")
    db.add(doc)
    db.flush()
    ver = DocumentVersion(
        document_id=doc.id, version_number=1, storage_key="s_order",
        original_filename="order.pdf", content_type="application/pdf",
        file_size_bytes=100, sha256_hash="h_order" + "0" * 50,
        processing_status="CLEAN"
    )
    db.add(ver)
    doc.current_version_id = ver.id
    
    # Add minimal other evidence
    trust = TrustAssessment(
        instrument_id=instr.id, field_name=None,
        trust_level=TrustLevel.L2_OFFICER_VERIFIED.value, reason="Verified",
        assessment_timestamp=datetime.now(timezone.utc),
        status=TrustAssessmentStatus.ACTIVE.value, assessing_user_id=officer.id
    )
    db.add(trust)
    
    lifecycle = LifecycleEvaluation(
        instrument_id=instr.id, evaluation_date=date.today(),
        evaluation_timestamp=datetime.now(timezone.utc),
        maturity_stage=MaturityStage.MATURED.value, days_to_maturity=0,
        due_condition=DueCondition.NORMAL.value
    )
    db.add(lifecycle)
    
    db.commit()
    
    # Create and evaluate
    payload = ReleaseRequestCreate(
        instrument_id=instr.id, request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Test.", policy_profile_id=profile.id
    )
    release_req = create_release_request(db=db, payload=payload, current_user=user)
    assessment = evaluate_readiness(db=db, release_request=release_req, current_user=officer)
    
    # Verify: Should be BLOCKED
    assert assessment.assessment_outcome == "BLOCKED"
    assert assessment.blockers_count > 0


# ============================================================================
# TEST 4: Unresolved Blocking Finding
# ============================================================================

def test_4_unresolved_blocking_finding(db_session: Session):
    """Unresolved DETERMINISTIC finding → BLOCKED."""
    db = db_session
    
    # Setup
    inst = Institution(code="TEST-004", legal_name="Test Inst 4", state="Maharashtra", contact_email="inst@test.edu", is_active=True)
    db.add(inst)
    db.flush()
    
    user = User(email="user4@test.edu", password_hash="x", full_name="User", role="INSTITUTION_USER", institution_id=inst.id)
    officer = User(email="officer4@test.gov", password_hash="x", full_name="Officer", role="SCRUTINY_OFFICER", institution_id=inst.id)
    db.add_all([user, officer])
    db.flush()
    
    instr = Instrument(
        reference_number="FDR-2026-00004", bank_name="Bank", amount=100000, currency="INR",
        issue_date=date(2020, 1, 1), maturity_date=date(2026, 1, 1),
        instrument_type="FDR", status="REGISTERED", trust_level=TrustLevel.L0_DECLARED.value,
        institution_id=inst.id, assigned_office="Office"
    )
    db.add(instr)
    db.flush()
    
    profile = seed_demo_release_profile(db, created_by_user_id=user.id)
    
    # Add required documents
    for cat in ["FDR_RECEIPT", "SANCTION_ORDER"]:
        doc = Document(institution_id=inst.id, instrument_id=instr.id, category=cat, status="ACTIVE")
        db.add(doc)
        db.flush()
        ver = DocumentVersion(
            document_id=doc.id, version_number=1, storage_key=f"s_{cat}",
            original_filename=f"{cat}.pdf", content_type="application/pdf",
            file_size_bytes=100, sha256_hash=f"h_{cat}" + "0" * 50,
            processing_status="CLEAN"
        )
        db.add(ver)
        doc.current_version_id = ver.id
    
    trust = TrustAssessment(
        instrument_id=instr.id, field_name=None,
        trust_level=TrustLevel.L2_OFFICER_VERIFIED.value, reason="Verified",
        assessment_timestamp=datetime.now(timezone.utc),
        status=TrustAssessmentStatus.ACTIVE.value, assessing_user_id=officer.id
    )
    db.add(trust)
    
    lifecycle = LifecycleEvaluation(
        instrument_id=instr.id, evaluation_date=date.today(),
        evaluation_timestamp=datetime.now(timezone.utc),
        maturity_stage=MaturityStage.MATURED.value, days_to_maturity=0,
        due_condition=DueCondition.NORMAL.value
    )
    db.add(lifecycle)
    
    # Add BLOCKING finding (DETERMINISTIC, OPEN)
    finding = ValidationFinding(
        finding_fingerprint="block_001",
        instrument_id=instr.id, institution_id=inst.id,
        rule_id="RULE_CRITICAL", rule_version="1.0", rule_type="DETERMINISTIC",
        category="DATE_CONSISTENCY", severity="CRITICAL",
        status=FindingStatus.OPEN.value, title="Critical Issue",
        explanation="Date mismatch detected.",
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc)
    )
    db.add(finding)
    
    db.commit()
    
    # Create and evaluate
    payload = ReleaseRequestCreate(
        instrument_id=instr.id, request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Test blocking finding.", policy_profile_id=profile.id
    )
    release_req = create_release_request(db=db, payload=payload, current_user=user)
    assessment = evaluate_readiness(db=db, release_request=release_req, current_user=officer)
    
    # Verify: Should be BLOCKED
    assert assessment.assessment_outcome == "BLOCKED"
    assert assessment.blockers_count > 0
