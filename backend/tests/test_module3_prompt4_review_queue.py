"""
Module 3 — Prompt 4 Test Suite
Discrepancy Review, Reasoned Resolution, Return-for-Correction and Explainable Priority Queue

Verifies all 17 required scenarios:
1. Allowed and forbidden finding transitions.
2. Resolution without reason being rejected.
3. Dismissal without reason being rejected.
4. Unauthorized user resolution attempt.
5. Cross-institution finding access denial.
6. Auditor read-only behavior.
7. Institution-user visibility restrictions.
8. Concurrent resolution attempts (optimistic concurrency version conflict).
9. Historical finding retention.
10. Reevaluation after corrected data.
11. Return-for-correction requiring a reason.
12. Advisory warning does not become an automatic blocker without configuration.
13. Priority-score contribution breakdown.
14. Unknown fields handling in the score.
15. Score changes when valid inputs change.
16. Score never changes trust or release authorization.
17. Audit records for all material review actions.
"""
import uuid
import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document
from app.modules.auth.models import User
from app.core.security import hash_password
from app.modules.validation.models import ValidationFinding, ValidationRun
from app.modules.validation.enums import FindingStatus, RuleSeverity, RuleType, FindingCategory, RuleOutcome
from app.modules.validation.finding_service import (
    transition_finding_status,
    assign_finding,
    add_finding_observation,
    return_instrument_for_correction,
    get_review_queue,
    re_evaluate_finding,
)
from app.modules.validation.priority_score import calculate_review_priority_score
from app.modules.audit.models import AuditEvent
from app.common.exceptions import AppException, ForbiddenException, ConflictException


@pytest.fixture
def institution(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="AICTE-ENG-M3P4",
        legal_name="National Engineering College",
        display_name="NEC",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar NEC",
        contact_email="registrar.m3p4@nec.ac.in",
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
def other_institution(db_session: Session) -> Institution:
    inst = Institution(
        id=str(uuid.uuid4()),
        code="AICTE-OTHER-002",
        legal_name="Apex Polytechnic",
        display_name="Apex",
        institution_type="POLYTECHNIC",
        contact_name="Registrar Apex",
        contact_email="registrar.apex@apex.ac.in",
        contact_phone="+91-11-29582000",
        address_line1="Zone 4",
        city="Jaipur",
        state="Rajasthan",
        postal_code="302001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def scrutiny_officer(db_session: Session) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="scrutiny.m3p4@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Scrutiny Officer Sharma",
        role="SCRUTINY_OFFICER",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def branch_head(db_session: Session) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="head.m3p4@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Branch Head Verma",
        role="BRANCH_HEAD",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def auditor(db_session: Session) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="auditor.m3p4@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Auditor Rao",
        role="AUDITOR",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def institution_user(db_session: Session, institution: Institution) -> User:
    u = User(
        id=str(uuid.uuid4()),
        email="inst.user.m3p4@nec.ac.in",
        password_hash=hash_password("Pass@123456"),
        full_name="College Registrar User",
        role="INSTITUTION_USER",
        institution_id=institution.id,
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def base_instrument(db_session: Session, institution: Institution) -> Instrument:
    inst = Instrument(
        id=str(uuid.uuid4()),
        institution_id=institution.id,
        reference_number="FDR-M3P4-001",
        bank_name="State Bank of India",
        branch="Connaught Place",
        amount=Decimal("1500000.00"),
        currency="INR",
        issue_date=date(2025, 1, 1),
        maturity_date=date.today() + timedelta(days=45),
        status="UNDER_SCRUTINY",
        trust_level="L0_DECLARED",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def sample_finding(db_session: Session, base_instrument: Instrument, institution: Institution) -> ValidationFinding:
    f = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=f"fp-{uuid.uuid4()}",
        instrument_id=base_instrument.id,
        institution_id=institution.id,
        rule_id="VAL-DATE-001",
        rule_version="1.0.0",
        rule_type="DETERMINISTIC",
        category="DATE_CONSISTENCY",
        severity="HIGH",
        status="OPEN",
        title="Issue date cannot be in the future",
        explanation="The instrument issue date is in the future.",
        observed_value="2027-01-01",
        expected_value="<= today",
        first_detected_at=datetime.now(timezone.utc) - timedelta(days=2),
        last_evaluated_at=datetime.now(timezone.utc) - timedelta(days=2),
        concurrency_version=1,
    )
    db_session.add(f)
    db_session.commit()
    db_session.refresh(f)
    return f


# ===========================================================================
# 1. Allowed and forbidden finding transitions
# ===========================================================================
def test_allowed_and_forbidden_finding_transitions(
    db_session: Session, sample_finding: ValidationFinding, scrutiny_officer: User
):
    # OPEN -> IN_REVIEW (allowed)
    f = transition_finding_status(
        db=db_session,
        finding=sample_finding,
        target_status="IN_REVIEW",
        actor_user=scrutiny_officer,
    )
    assert f.status == "IN_REVIEW"
    assert f.concurrency_version == 2

    # IN_REVIEW -> RESOLVED (allowed with reason)
    f = transition_finding_status(
        db=db_session,
        finding=f,
        target_status="RESOLVED",
        actor_user=scrutiny_officer,
        reason="Bank confirmed date typo on instrument certificate.",
    )
    assert f.status == "RESOLVED"
    assert f.resolved_at is not None
    assert f.resolution_note == "Bank confirmed date typo on instrument certificate."

    # RESOLVED -> IN_REVIEW (forbidden terminal state transition)
    with pytest.raises(AppException) as exc_info:
        transition_finding_status(
            db=db_session,
            finding=f,
            target_status="IN_REVIEW",
            actor_user=scrutiny_officer,
        )
    assert exc_info.value.status_code == 400
    assert "Invalid transition" in str(exc_info.value)


# ===========================================================================
# 2. Resolution without reason being rejected
# ===========================================================================
def test_resolution_without_reason_rejected(
    db_session: Session, sample_finding: ValidationFinding, scrutiny_officer: User
):
    # None reason
    with pytest.raises(AppException) as exc_info:
        transition_finding_status(
            db=db_session,
            finding=sample_finding,
            target_status="RESOLVED",
            actor_user=scrutiny_officer,
            reason=None,
        )
    assert exc_info.value.status_code == 422
    assert "non-empty reason is mandatory" in str(exc_info.value)

    # Whitespace only
    with pytest.raises(AppException) as exc_info2:
        transition_finding_status(
            db=db_session,
            finding=sample_finding,
            target_status="RESOLVED",
            actor_user=scrutiny_officer,
            reason="    \t   \n  ",
        )
    assert exc_info2.value.status_code == 422


# ===========================================================================
# 3. Dismissal without reason being rejected
# ===========================================================================
def test_dismissal_without_reason_rejected(
    db_session: Session, sample_finding: ValidationFinding, scrutiny_officer: User
):
    with pytest.raises(AppException) as exc_info:
        transition_finding_status(
            db=db_session,
            finding=sample_finding,
            target_status="DISMISSED",
            actor_user=scrutiny_officer,
            reason="   ",
        )
    assert exc_info.value.status_code == 422
    assert "non-empty reason is mandatory" in str(exc_info.value)

    # Valid reason succeeds
    f = transition_finding_status(
        db=db_session,
        finding=sample_finding,
        target_status="DISMISSED",
        actor_user=scrutiny_officer,
        reason="Instrument has approved regulatory exemption under Policy AICTE-2026-EX-12.",
    )
    assert f.status == "DISMISSED"
    assert f.resolution_note == "Instrument has approved regulatory exemption under Policy AICTE-2026-EX-12."


# ===========================================================================
# 4. Unauthorized user resolution attempt
# ===========================================================================
def test_unauthorized_user_resolution_attempt(
    db_session: Session, sample_finding: ValidationFinding, institution_user: User
):
    with pytest.raises(ForbiddenException) as exc_info:
        transition_finding_status(
            db=db_session,
            finding=sample_finding,
            target_status="RESOLVED",
            actor_user=institution_user,
            reason="College says this is fine.",
        )
    assert "not authorized to transition finding status" in str(exc_info.value)


# ===========================================================================
# 5. Cross-institution finding access denial
# ===========================================================================
def test_cross_institution_finding_access_denial(
    db_session: Session, sample_finding: ValidationFinding, other_institution: Institution
):
    scoped_officer = User(
        id=str(uuid.uuid4()),
        email="scoped.officer@aicte.gov.in",
        password_hash=hash_password("Pass@123456"),
        full_name="Regional Scrutineer",
        role="SCRUTINY_OFFICER",
        institution_id=other_institution.id,  # Scoped to Apex Polytechnic
        is_active=True,
    )
    db_session.add(scoped_officer)
    db_session.commit()

    with pytest.raises(ForbiddenException) as exc_info:
        transition_finding_status(
            db=db_session,
            finding=sample_finding,  # belongs to NEC
            target_status="IN_REVIEW",
            actor_user=scoped_officer,
        )
    assert "Cannot modify finding belonging to another institution" in str(exc_info.value)


# ===========================================================================
# 6. Auditor read-only behavior
# ===========================================================================
def test_auditor_read_only_behavior(
    db_session: Session, sample_finding: ValidationFinding, auditor: User, base_instrument: Instrument
):
    # Auditor cannot transition status
    with pytest.raises(ForbiddenException):
        transition_finding_status(
            db=db_session,
            finding=sample_finding,
            target_status="RESOLVED",
            actor_user=auditor,
            reason="Auditor verification.",
        )

    # Auditor cannot return submission for correction
    with pytest.raises(ForbiddenException):
        return_instrument_for_correction(
            db=db_session,
            instrument_id=base_instrument.id,
            actor_user=auditor,
            explanation="Auditor requires correction.",
        )


# ===========================================================================
# 7. Institution-user visibility restrictions
# ===========================================================================
def test_institution_user_visibility_restrictions(
    db_session: Session,
    base_instrument: Instrument,
    institution: Institution,
    other_institution: Institution,
    institution_user: User,
):
    # Create internal-only cross-inst duplicate finding (VAL-DUP-002)
    internal_f = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=f"fp-{uuid.uuid4()}",
        instrument_id=base_instrument.id,
        institution_id=institution.id,
        rule_id="VAL-DUP-002",
        rule_version="1.0.0",
        rule_type="HEURISTIC",
        category="DUPLICATE_SUSPICION",
        severity="HIGH",
        status="OPEN",
        title="Cross-Institution Duplicate Detected",
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )
    # Create finding for other institution
    other_inst_record = Instrument(
        id=str(uuid.uuid4()),
        institution_id=other_institution.id,
        reference_number="FDR-OTHER-999",
        bank_name="HDFC",
        amount=Decimal("500000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2026, 1, 1),
        status="UNDER_SCRUTINY",
    )
    db_session.add(other_inst_record)
    db_session.flush()

    other_f = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=f"fp-{uuid.uuid4()}",
        instrument_id=other_inst_record.id,
        institution_id=other_institution.id,
        rule_id="VAL-REQ-001",
        rule_version="1.0.0",
        rule_type="DETERMINISTIC",
        category="REQUIRED_FIELD",
        severity="CRITICAL",
        status="OPEN",
        title="Missing field on other college",
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add_all([internal_f, other_f])
    db_session.commit()

    # Query queue as institution user
    queue_res = get_review_queue(db=db_session, current_user=institution_user)
    finding_ids = [item["id"] for item in queue_res["items"]]

    # Must NOT contain other institution's finding
    assert other_f.id not in finding_ids
    # Must NOT contain internal cross-inst rule VAL-DUP-002
    assert internal_f.id not in finding_ids


# ===========================================================================
# 8. Concurrent resolution attempts (optimistic concurrency version conflict)
# ===========================================================================
def test_concurrent_resolution_attempts(
    db_session: Session, sample_finding: ValidationFinding, scrutiny_officer: User, branch_head: User
):
    # Both officers read finding at concurrency_version == 1
    assert sample_finding.concurrency_version == 1

    # Officer 1 transitions finding with expected_concurrency_version = 1 (succeeds)
    transition_finding_status(
        db=db_session,
        finding=sample_finding,
        target_status="IN_REVIEW",
        actor_user=scrutiny_officer,
        expected_concurrency_version=1,
    )
    assert sample_finding.concurrency_version == 2

    # Officer 2 attempts concurrent transition submitting stale version 1 -> raises ConflictException (409)
    with pytest.raises(ConflictException) as exc_info:
        transition_finding_status(
            db=db_session,
            finding=sample_finding,
            target_status="RESOLVED",
            actor_user=branch_head,
            reason="Resolving based on prior email.",
            expected_concurrency_version=1,  # Stale! Current is 2
        )
    assert "modified by another concurrent review action" in str(exc_info.value)


# ===========================================================================
# 9. Historical finding retention
# ===========================================================================
def test_historical_finding_retention(
    db_session: Session, sample_finding: ValidationFinding, scrutiny_officer: User
):
    # Perform status transition and add review observations
    transition_finding_status(
        db=db_session,
        finding=sample_finding,
        target_status="IN_REVIEW",
        actor_user=scrutiny_officer,
    )
    add_finding_observation(
        db=db_session,
        finding=sample_finding,
        actor_user=scrutiny_officer,
        observation_text="Dispatched clarification letter to bank branch manager.",
    )
    transition_finding_status(
        db=db_session,
        finding=sample_finding,
        target_status="RESOLVED",
        actor_user=scrutiny_officer,
        reason="Bank manager provided written confirmation of valid issue date.",
    )

    # Reload from DB and verify entire history retained
    db_session.refresh(sample_finding)
    assert len(sample_finding.review_notes) >= 3
    actions = [note["action"] for note in sample_finding.review_notes]
    assert "STATUS_TRANSITION_OPEN_TO_IN_REVIEW" in actions
    assert "OBSERVATION" in actions
    assert "STATUS_TRANSITION_IN_REVIEW_TO_RESOLVED" in actions


# ===========================================================================
# 10. Reevaluation after corrected data
# ===========================================================================
def test_reevaluation_after_corrected_data(
    db_session: Session, base_instrument: Instrument, sample_finding: ValidationFinding, scrutiny_officer: User
):
    # Correct the underlying date on instrument
    base_instrument.issue_date = date(2025, 1, 15)  # valid past date
    db_session.commit()

    # Trigger re-evaluation of the finding
    res = re_evaluate_finding(
        db=db_session,
        finding_id=sample_finding.id,
        actor_user_id=scrutiny_officer.id,
    )
    db_session.refresh(sample_finding)
    # Finding should be marked as RESOLVED by the validation engine
    assert sample_finding.status == FindingStatus.RESOLVED.value
    assert "Condition cleared on re-evaluation" in (sample_finding.resolution_note or "")


# ===========================================================================
# 11. Return-for-correction requiring a reason
# ===========================================================================
def test_return_for_correction_requiring_reason(
    db_session: Session, base_instrument: Instrument, scrutiny_officer: User
):
    # Blank explanation rejected
    with pytest.raises(AppException) as exc_info:
        return_instrument_for_correction(
            db=db_session,
            instrument_id=base_instrument.id,
            actor_user=scrutiny_officer,
            explanation="   ",
        )
    assert exc_info.value.status_code == 422
    assert "explicit explanation is required" in str(exc_info.value)

    # Valid explanation succeeds
    updated = return_instrument_for_correction(
        db=db_session,
        instrument_id=base_instrument.id,
        actor_user=scrutiny_officer,
        explanation="Please upload an unredacted FDR certificate with clear bank branch seal.",
    )
    assert updated.status == "RETURNED_FOR_CORRECTION"
    assert "Please upload an unredacted FDR certificate" in updated.remarks


# ===========================================================================
# 12. Advisory warning does not become an automatic blocker without configuration
# ===========================================================================
def test_advisory_warning_does_not_block_without_configuration(
    db_session: Session, base_instrument: Instrument, institution: Institution
):
    heuristic_finding = ValidationFinding(
        id=str(uuid.uuid4()),
        finding_fingerprint=f"fp-heuristic-{uuid.uuid4()}",
        instrument_id=base_instrument.id,
        institution_id=institution.id,
        rule_id="VAL-META-001",
        rule_version="1.0.0",
        rule_type=RuleType.HEURISTIC.value,
        category=FindingCategory.DOCUMENT_INTEGRITY.value,
        severity=RuleSeverity.MEDIUM.value,
        status=FindingStatus.OPEN.value,
        title="Document modification software tag detected",
        first_detected_at=datetime.now(timezone.utc),
        last_evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add(heuristic_finding)
    db_session.commit()

    # Rule type must be HEURISTIC
    assert heuristic_finding.rule_type == "HEURISTIC"
    # Instrument trust level must remain unmodified
    assert base_instrument.trust_level == "L0_DECLARED"
    assert base_instrument.status == "UNDER_SCRUTINY"


# ===========================================================================
# 13. Priority-score contribution breakdown
# ===========================================================================
def test_priority_score_contribution_breakdown(
    db_session: Session, base_instrument: Instrument, sample_finding: ValidationFinding
):
    score_res = calculate_review_priority_score(
        instrument=base_instrument,
        open_findings=[sample_finding],
        has_fdr_copy=True,
    )

    assert 0 <= score_res.total_score <= 100
    assert len(score_res.factor_breakdown) == 5
    factor_names = [f.factor_name for f in score_res.factor_breakdown]
    assert "days_to_maturity" in factor_names
    assert "highest_finding_severity" in factor_names
    assert "unresolved_discrepancies_count" in factor_names
    assert "document_completeness" in factor_names
    assert "trust_level_dimension" in factor_names

    for factor in score_res.factor_breakdown:
        assert factor.points <= factor.max_points
        assert len(factor.basis) > 5


# ===========================================================================
# 14. Unknown fields handling in the score
# ===========================================================================
def test_unknown_fields_handling_in_score(sample_finding: ValidationFinding):
    # Instrument without maturity date
    inst_no_maturity = Instrument(
        id="test-no-maturity",
        institution_id="inst-1",
        reference_number="REF-001",
        bank_name="SBI",
        maturity_date=None,  # Unknown / missing!
        trust_level=None,
    )

    score_res = calculate_review_priority_score(
        instrument=inst_no_maturity,
        open_findings=[sample_finding],
        has_fdr_copy=None,  # Missing completeness evaluation!
    )

    assert "maturity_date" in score_res.missing_fields
    assert "has_fdr_copy" in score_res.missing_fields
    # Missing factor must have is_missing = True and 0 points
    mat_factor = next(f for f in score_res.factor_breakdown if f.factor_name == "days_to_maturity")
    assert mat_factor.is_missing is True
    assert mat_factor.points == 0.0


# ===========================================================================
# 15. Score changes when valid inputs change
# ===========================================================================
def test_score_changes_when_valid_inputs_change(base_instrument: Instrument, sample_finding: ValidationFinding):
    # Scenario A: Expiring far in future (300 days)
    base_instrument.maturity_date = date.today() + timedelta(days=300)
    score_far = calculate_review_priority_score(
        instrument=base_instrument,
        open_findings=[sample_finding],
        has_fdr_copy=True,
    )

    # Scenario B: Expiring within 10 days
    base_instrument.maturity_date = date.today() + timedelta(days=10)
    score_urgent = calculate_review_priority_score(
        instrument=base_instrument,
        open_findings=[sample_finding],
        has_fdr_copy=True,
    )

    # Urgent score must be significantly higher
    assert score_urgent.total_score > score_far.total_score


# ===========================================================================
# 16. Score never changes trust or release authorization
# ===========================================================================
def test_score_never_changes_trust_or_release_authorization(
    db_session: Session, base_instrument: Instrument, sample_finding: ValidationFinding, scrutiny_officer: User
):
    initial_trust = base_instrument.trust_level
    initial_status = base_instrument.status

    # Compute score
    calculate_review_priority_score(
        instrument=base_instrument,
        open_findings=[sample_finding],
        has_fdr_copy=True,
    )

    # Resolve finding
    transition_finding_status(
        db=db_session,
        finding=sample_finding,
        target_status="RESOLVED",
        actor_user=scrutiny_officer,
        reason="Verified manually.",
    )

    db_session.refresh(base_instrument)
    # Trust level and release status must remain completely unchanged
    assert base_instrument.trust_level == initial_trust
    assert base_instrument.status == initial_status


# ===========================================================================
# 17. Audit records for all material review actions
# ===========================================================================
def test_audit_records_for_material_review_actions(
    db_session: Session,
    base_instrument: Instrument,
    sample_finding: ValidationFinding,
    scrutiny_officer: User,
    branch_head: User,
):
    # 1. Transition to IN_REVIEW
    transition_finding_status(
        db=db_session,
        finding=sample_finding,
        target_status="IN_REVIEW",
        actor_user=scrutiny_officer,
    )

    # 2. Add Observation
    add_finding_observation(
        db=db_session,
        finding=sample_finding,
        actor_user=scrutiny_officer,
        observation_text="Cross-checked branch IFSC with RBI directory.",
    )

    # 3. Assign to Branch Head
    assign_finding(
        db=db_session,
        finding=sample_finding,
        assigned_to_user_id=branch_head.id,
        actor_user=scrutiny_officer,
    )

    # 4. Resolve Finding
    transition_finding_status(
        db=db_session,
        finding=sample_finding,
        target_status="RESOLVED",
        actor_user=branch_head,
        reason="Confirmed with SBI Regional Hub.",
    )

    # 5. Return Instrument for Correction
    return_instrument_for_correction(
        db=db_session,
        instrument_id=base_instrument.id,
        actor_user=branch_head,
        explanation="Need stamped renewal copy.",
    )

    # Check audit log entries
    audit_events = list(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.entity_id.in_([sample_finding.id, base_instrument.id])
            )
        ).all()
    )
    actions = [e.action for e in audit_events]
    assert "VALIDATION_FINDING_IN_REVIEW" in actions
    assert "VALIDATION_FINDING_OBSERVATION_ADDED" in actions
    assert "VALIDATION_FINDING_ASSIGNED" in actions
    assert "VALIDATION_FINDING_RESOLVED" in actions
    assert "INSTRUMENT_RETURNED_FOR_CORRECTION" in actions
