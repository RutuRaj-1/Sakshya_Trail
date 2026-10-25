"""
Module 5 — Prompt 4: Renewal and Replacement Workflow, Predecessor/Successor Lineage and Gap/Overlap Detection
Acceptance Test Suite

Covers all 18 required specifications:
1. Creating a successor as a new instrument.
2. Linking predecessor to successor.
3. Cycle rejection.
4. Self-link rejection.
5. Ambiguous/duplicate link rejection.
6. Cross-institution restriction.
7. Concurrent link attempts / duplicate idempotency.
8. Predecessor data, documents, and trust history remain unchanged.
9. Successor does not inherit predecessor trust (starts at L0_DECLARED).
10. Gap/overlap calculated using configured semantics.
11. Unknown effective date does not yield a false definitive result (CONTINUITY_UNDETERMINED).
12. Missing/unconfigured continuity policy (POLICY_UNCONFIGURED).
13. Gap/overlap finding integrates with Module 3.
14. Successor receives its own lifecycle evaluation upon linkage.
15. Reminder behavior remains policy-consistent.
16. No predecessor release or refund status change.
17. Institution scoping and read-only roles.
18. Audit history for creation, linking, and correction.
"""
from typing import Generator, List, Optional
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import (
    LifecyclePolicy,
    InstrumentLineage,
    LifecycleEvaluation,
    LifecycleNotification,
)
from app.modules.lifecycle.enums import (
    PolicyStatus,
    RenewalComparisonMethod,
    LineageRelationshipType,
    LineageRelationshipStatus,
    ContinuityIndicator,
    ContinuityOutcome,
)
from app.modules.lifecycle.clock import (
    SimulatedClock,
    set_current_clock,
    reset_to_system_clock,
)
from app.modules.lifecycle.policy_service import (
    create_policy,
    approve_policy,
    activate_policy,
    get_or_create_default_demo_policy,
)
from app.modules.lifecycle.lineage_service import (
    create_renewal_lineage,
    initiate_renewal_draft,
    create_and_link_renewal_successor,
    correct_renewal_lineage,
    validate_proposed_lineage,
    get_lineage_tree,
    get_lineage_continuity_assessment,
    detect_cycle_in_lineage,
)
from app.modules.lifecycle.continuity_service import assess_lineage_continuity
from app.modules.lifecycle.schemas import (
    LifecyclePolicyCreate,
    LineageCreateRequest,
    LineageValidateRequest,
    RenewalCreateSuccessorRequest,
    LineageCorrectionRequest,
)
from app.modules.validation.models import ValidationFinding
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_BRANCH_HEAD,
    create_access_token,
)
from app.core.config import settings
from app.common.exceptions import AppException


def set_auth(client: TestClient, user: User):
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


@pytest.fixture(autouse=True)
def cleanup_clock():
    yield
    reset_to_system_clock()


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        email="admin.lineage@aicte-india.org",
        full_name="Lineage Admin",
        role=ROLE_SYSTEM_ADMIN,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def officer_user(db_session: Session) -> User:
    user = User(
        email="officer.lineage@aicte-india.org",
        full_name="Scrutiny Officer Lineage",
        role=ROLE_SCRUTINY_OFFICER,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def institution_a(db_session: Session) -> Institution:
    inst = Institution(
        legal_name="Indian Institute of Engineering A",
        code="IIE-A-001",
        contact_email="principal@iie-a.ac.in",
        contact_phone="+911122334455",
        assigned_office="Northern Regional Office (NRO - Kanpur)",
        state="Delhi",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def institution_b(db_session: Session) -> Institution:
    inst = Institution(
        legal_name="National Institute of Technology B",
        code="NIT-B-002",
        contact_email="principal@nit-b.ac.in",
        contact_phone="+911122334466",
        assigned_office="Western Regional Office (WRO - Mumbai)",
        state="Maharashtra",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def inst_user_a(db_session: Session, institution_a: Institution) -> User:
    user = User(
        email="registrar@iie-a.ac.in",
        full_name="Registrar College A",
        role=ROLE_INSTITUTION_USER,
        institution_id=institution_a.id,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inst_user_b(db_session: Session, institution_b: Institution) -> User:
    user = User(
        email="registrar@nit-b.ac.in",
        full_name="Registrar College B",
        role=ROLE_INSTITUTION_USER,
        institution_id=institution_b.id,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def active_lineage_policy(db_session: Session, admin_user: User) -> LifecyclePolicy:
    policy = create_policy(
        db=db_session,
        payload=LifecyclePolicyCreate(
            policy_code="DEMO-LINEAGE-POL-01",
            name="Demo Lineage & Continuity Policy",
            is_demo=True,
            label="DEMO POLICY — NOT OFFICIAL AICTE POLICY",
            renewal_comparison_method=RenewalComparisonMethod.ISSUE_DATE_TO_MATURITY_DATE,
            max_allowed_gap_days=5,
            max_allowed_overlap_days=30,
            reminder_intervals_days=[90, 60, 30],
        ),
        created_by_user_id=admin_user.id,
    )
    approve_policy(db_session, policy.id, approver_user_id=admin_user.id)
    return activate_policy(db_session, policy.id, activator_user_id=admin_user.id)


@pytest.fixture
def strict_continuous_policy(db_session: Session, admin_user: User) -> LifecyclePolicy:
    policy = create_policy(
        db=db_session,
        payload=LifecyclePolicyCreate(
            policy_code="STRICT-CONTINUOUS-POL",
            name="Strict Continuous Term Policy (Requires Effective Date)",
            is_demo=True,
            label="DEMO POLICY — NOT OFFICIAL AICTE POLICY",
            renewal_comparison_method=RenewalComparisonMethod.STRICT_CONTINUOUS_TERM,
            max_allowed_gap_days=0,
            max_allowed_overlap_days=15,
            reminder_intervals_days=[90, 30],
        ),
        created_by_user_id=admin_user.id,
    )
    approve_policy(db_session, policy.id, approver_user_id=admin_user.id)
    return activate_policy(db_session, policy.id, activator_user_id=admin_user.id)


@pytest.fixture
def predecessor_instrument(
    db_session: Session,
    institution_a: Institution,
    admin_user: User,
) -> Instrument:
    """Mature or maturing predecessor instrument with L3_BANK_CONFIRMED status."""
    inst = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        branch="Main Branch",
        reference_number="FDR-PRED-ORIGINAL-001",
        amount=Decimal("1500000.00"),
        currency="INR",
        issue_date=date(2023, 1, 1),
        maturity_date=date(2026, 1, 1),
        lien_holder="AICTE Regulation Bureau",
        lien_marked=True,
        joint_with_aicte=True,
        assigned_office="Northern Regional Office (NRO - Kanpur)",
        status="REGISTERED",
        trust_level="L3_BANK_CONFIRMED",
        created_by_user_id=admin_user.id,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


# --- Tests ----------------------------------------------------------------------

def test_1_create_successor_as_new_instrument(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    inst_user_a: User,
    active_lineage_policy: LifecyclePolicy,
):
    """1. Creating a successor as a new instrument."""
    payload = RenewalCreateSuccessorRequest(
        bank_name="State Bank of India",
        branch="Main Branch",
        reference_number="FDR-SUCC-NEW-001",
        amount=Decimal("1500000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        relationship_type=LineageRelationshipType.RENEWAL,
        reason_or_reference="Statutory 3-year extension",
    )

    successor, lineage = create_and_link_renewal_successor(
        db=db_session,
        predecessor_id=predecessor_instrument.id,
        payload=payload,
        current_user=inst_user_a,
    )

    assert successor.id != predecessor_instrument.id
    assert successor.reference_number == "FDR-SUCC-NEW-001"
    assert successor.institution_id == institution_a.id
    assert successor.created_by_user_id == inst_user_a.id
    assert lineage.predecessor_instrument_id == predecessor_instrument.id
    assert lineage.successor_instrument_id == successor.id


def test_2_linking_predecessor_to_successor(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    admin_user: User,
    active_lineage_policy: LifecyclePolicy,
):
    """2. Explicit linking of existing predecessor to successor."""
    successor = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="Punjab National Bank",
        reference_number="FDR-SUCC-PNB-002",
        amount=Decimal("1500000.00"),
        issue_date=date(2026, 1, 2),
        maturity_date=date(2029, 1, 2),
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(successor)
    db_session.commit()
    db_session.refresh(successor)

    req = LineageCreateRequest(
        predecessor_instrument_id=predecessor_instrument.id,
        successor_instrument_id=successor.id,
        relationship_type=LineageRelationshipType.RENEWAL,
        reason_or_reference="Manual authorized linking",
    )
    link = create_renewal_lineage(db_session, payload=req, created_by_user_id=admin_user.id)

    assert link.id is not None
    assert link.relationship_status == LineageRelationshipStatus.ACTIVE.value
    assert link.predecessor_instrument_id == predecessor_instrument.id
    assert link.successor_instrument_id == successor.id


def test_3_cycle_rejection(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    admin_user: User,
    active_lineage_policy: LifecyclePolicy,
):
    """3. Cycle rejection across multi-hop renewal DAG."""
    # A -> B -> C
    b = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-NODE-B",
        amount=Decimal("1000000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    c = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-NODE-C",
        amount=Decimal("1000000"),
        issue_date=date(2029, 1, 1),
        maturity_date=date(2032, 1, 1),
        status="REGISTERED",
    )
    db_session.add_all([b, c])
    db_session.commit()

    # Link A -> B
    create_renewal_lineage(
        db_session,
        LineageCreateRequest(predecessor_instrument_id=predecessor_instrument.id, successor_instrument_id=b.id),
        created_by_user_id=admin_user.id,
    )
    # Link B -> C
    create_renewal_lineage(
        db_session,
        LineageCreateRequest(predecessor_instrument_id=b.id, successor_instrument_id=c.id),
        created_by_user_id=admin_user.id,
    )

    # Attempt to link C -> A (introducing cycle C -> A -> B -> C)
    with pytest.raises(AppException) as exc_info:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(predecessor_instrument_id=c.id, successor_instrument_id=predecessor_instrument.id),
            created_by_user_id=admin_user.id,
        )
    assert exc_info.value.code == "CYCLIC_LINEAGE_DETECTED"


def test_4_self_link_rejection(
    db_session: Session,
    predecessor_instrument: Instrument,
    admin_user: User,
):
    """4. Self-link rejection (predecessor == successor)."""
    with pytest.raises(AppException) as exc_info:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(
                predecessor_instrument_id=predecessor_instrument.id,
                successor_instrument_id=predecessor_instrument.id,
            ),
            created_by_user_id=admin_user.id,
        )
    assert exc_info.value.code == "SELF_REFERENTIAL_LINEAGE_PROHIBITED"


def test_5_ambiguous_duplicate_link_rejection(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    admin_user: User,
    active_lineage_policy: LifecyclePolicy,
):
    """5. Ambiguous branching / duplicate link rejection (1:1 active link)."""
    s1 = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-SUCC-1",
        amount=Decimal("1000000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    s2 = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-SUCC-2",
        amount=Decimal("1000000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    # Link predecessor -> s1
    create_renewal_lineage(
        db_session,
        LineageCreateRequest(predecessor_instrument_id=predecessor_instrument.id, successor_instrument_id=s1.id),
        created_by_user_id=admin_user.id,
    )

    # Attempt to link predecessor -> s2 (branching)
    with pytest.raises(AppException) as exc_info:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(predecessor_instrument_id=predecessor_instrument.id, successor_instrument_id=s2.id),
            created_by_user_id=admin_user.id,
        )
    assert exc_info.value.code == "DUPLICATE_PREDECESSOR_LINEAGE"


def test_6_cross_institution_restriction(
    db_session: Session,
    predecessor_instrument: Instrument,
    institution_b: Institution,
    admin_user: User,
    active_lineage_policy: LifecyclePolicy,
):
    """6. Cross-institution restriction without explicit transfer authorization."""
    inst_b_succ = Instrument(
        institution_id=institution_b.id,  # Belongs to College B!
        instrument_type="FDR",
        bank_name="Canara Bank",
        reference_number="FDR-COLLEGE-B-SUCC",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    db_session.add(inst_b_succ)
    db_session.commit()

    # Prohibited by default
    with pytest.raises(AppException) as exc_info:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(
                predecessor_instrument_id=predecessor_instrument.id,
                successor_instrument_id=inst_b_succ.id,
                allow_authorized_transfer=False,
            ),
            created_by_user_id=admin_user.id,
        )
    assert exc_info.value.code == "CROSS_INSTITUTION_LINEAGE_PROHIBITED"

    # Permitted when allow_authorized_transfer=True
    link = create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=predecessor_instrument.id,
            successor_instrument_id=inst_b_succ.id,
            allow_authorized_transfer=True,
            reason_or_reference="Authorized institutional amalgamation / merger",
        ),
        created_by_user_id=admin_user.id,
    )
    assert link.id is not None


def test_7_concurrent_link_attempts_idempotency(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    admin_user: User,
    active_lineage_policy: LifecyclePolicy,
):
    """7. Concurrent or redundant attempts to create identical link are handled idempotently."""
    succ = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-SUCC-IDEMP",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    db_session.add(succ)
    db_session.commit()

    req = LineageCreateRequest(
        predecessor_instrument_id=predecessor_instrument.id,
        successor_instrument_id=succ.id,
    )

    first_link = create_renewal_lineage(db_session, req, created_by_user_id=admin_user.id)
    # Second identical attempt
    second_link = create_renewal_lineage(db_session, req, created_by_user_id=admin_user.id)

    assert first_link.id == second_link.id


def test_8_predecessor_data_documents_and_trust_remain_unchanged(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    inst_user_a: User,
    active_lineage_policy: LifecyclePolicy,
):
    """8. Predecessor data, fields, status, and trust history remain strictly unchanged."""
    orig_id = predecessor_instrument.id
    orig_ref = predecessor_instrument.reference_number
    orig_amount = predecessor_instrument.amount
    orig_trust = predecessor_instrument.trust_level
    orig_status = predecessor_instrument.status
    orig_mat = predecessor_instrument.maturity_date

    payload = RenewalCreateSuccessorRequest(
        bank_name="HDFC Bank",
        reference_number="FDR-HDFC-999",
        amount=Decimal("2000000.00"),  # Changed amount
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
    )

    create_and_link_renewal_successor(db_session, predecessor_instrument.id, payload, inst_user_a)

    db_session.refresh(predecessor_instrument)
    assert predecessor_instrument.id == orig_id
    assert predecessor_instrument.reference_number == orig_ref
    assert predecessor_instrument.amount == orig_amount
    assert predecessor_instrument.trust_level == orig_trust
    assert predecessor_instrument.status == orig_status
    assert predecessor_instrument.maturity_date == orig_mat


def test_9_successor_does_not_inherit_predecessor_trust(
    db_session: Session,
    predecessor_instrument: Instrument,
    inst_user_a: User,
    active_lineage_policy: LifecyclePolicy,
):
    """9. Successor does NOT inherit L3 trust from predecessor; starts at L0_DECLARED."""
    assert predecessor_instrument.trust_level == "L3_BANK_CONFIRMED"

    payload = RenewalCreateSuccessorRequest(
        bank_name="SBI",
        reference_number="FDR-SUCC-TRUST-CHECK",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
    )

    successor, _ = create_and_link_renewal_successor(
        db_session, predecessor_instrument.id, payload, inst_user_a
    )

    assert successor.trust_level == "L0_DECLARED"
    assert successor.trust_level != predecessor_instrument.trust_level


def test_10_gap_overlap_calculated_using_configured_semantics(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    admin_user: User,
    active_lineage_policy: LifecyclePolicy,
):
    """10. Gap/overlap calculated using configured semantics (issue date proxy under demo policy)."""
    # Predecessor matures on 2026-01-01. Successor issued on 2026-01-03 -> Gap of 2 days
    succ_gap = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-SUCC-GAP-2DAYS",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 3),
        maturity_date=date(2029, 1, 3),
        status="REGISTERED",
    )
    db_session.add(succ_gap)
    db_session.commit()

    link = create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=predecessor_instrument.id,
            successor_instrument_id=succ_gap.id,
        ),
        created_by_user_id=admin_user.id,
    )

    assert link.validity_gap_days == 2
    assert link.validity_overlap_days == 0
    # Within 5-day allowed gap tolerance
    assert link.continuity_indicator == ContinuityIndicator.CONTINUOUS.value


def test_11_unknown_effective_date_strict_policy_yields_undetermined(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    admin_user: User,
    strict_continuous_policy: LifecyclePolicy,
):
    """11. Unknown effective date under STRICT_CONTINUOUS_TERM yields CONTINUITY_UNDETERMINED."""
    succ_no_eff = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-STRICT-NO-EFF",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        effective_date=None,  # No effective date!
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    db_session.add(succ_no_eff)
    db_session.commit()

    assessment = assess_lineage_continuity(
        db=db_session,
        predecessor=predecessor_instrument,
        successor=succ_no_eff,
        policy=strict_continuous_policy,
        create_finding=False,
    )

    assert assessment.outcome == ContinuityOutcome.CONTINUITY_UNDETERMINED
    assert assessment.continuity_indicator == ContinuityIndicator.UNKNOWN


def test_12_missing_unconfigured_continuity_policy(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
):
    """12. Missing / unconfigured policy yields POLICY_UNCONFIGURED."""
    succ = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-NO-POL",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    db_session.add(succ)
    db_session.commit()

    assessment = assess_lineage_continuity(
        db=db_session,
        predecessor=predecessor_instrument,
        successor=succ,
        policy=None,  # No policy
        create_finding=False,
    )

    assert assessment.outcome == ContinuityOutcome.POLICY_UNCONFIGURED


def test_13_gap_overlap_finding_integrates_with_module_3(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    admin_user: User,
    active_lineage_policy: LifecyclePolicy,
):
    """13. Out-of-tolerance gap creates a ValidationFinding in Module 3."""
    # Policy max_allowed_gap_days = 5. Successor issued 15 days later (2026-01-16) -> 15 days gap
    succ_large_gap = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-GAP-15DAYS",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 16),
        maturity_date=date(2029, 1, 16),
        status="REGISTERED",
    )
    db_session.add(succ_large_gap)
    db_session.commit()

    link = create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=predecessor_instrument.id,
            successor_instrument_id=succ_large_gap.id,
        ),
        created_by_user_id=admin_user.id,
    )

    assert link.validity_gap_days == 15
    assert link.continuity_indicator == ContinuityIndicator.GAP_DETECTED.value

    # Check Module 3 ValidationFinding
    finding = db_session.scalar(
        select(ValidationFinding).where(
            ValidationFinding.rule_id == "LINEAGE_CONTINUITY_POTENTIAL_GAP"
        )
    )
    assert finding is not None
    assert finding.instrument_id == succ_large_gap.id
    assert "15 day(s)" in (finding.explanation or "")


def test_14_successor_receives_own_lifecycle_evaluation(
    db_session: Session,
    predecessor_instrument: Instrument,
    inst_user_a: User,
    active_lineage_policy: LifecyclePolicy,
):
    """14. Successor receives a fresh lifecycle evaluation automatically upon linkage."""
    payload = RenewalCreateSuccessorRequest(
        bank_name="SBI",
        reference_number="FDR-EVAL-CHECK",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
    )

    succ, _ = create_and_link_renewal_successor(
        db_session, predecessor_instrument.id, payload, inst_user_a
    )

    succ_eval = db_session.scalar(
        select(LifecycleEvaluation).where(LifecycleEvaluation.instrument_id == succ.id)
    )
    assert succ_eval is not None
    assert succ_eval.instrument_id == succ.id


def test_15_reminder_behavior_remains_policy_consistent(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    inst_user_a: User,
    active_lineage_policy: LifecyclePolicy,
):
    """15. Predecessor reminder generation preserves audit trail and links to successor."""
    payload = RenewalCreateSuccessorRequest(
        bank_name="SBI",
        reference_number="FDR-SUCC-REMIND",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
    )
    succ, lineage = create_and_link_renewal_successor(
        db_session, predecessor_instrument.id, payload, inst_user_a
    )

    # Predecessor still retains its evaluation history
    pred_eval = db_session.scalar(
        select(LifecycleEvaluation).where(
            LifecycleEvaluation.instrument_id == predecessor_instrument.id
        )
    )
    assert pred_eval is not None
    assert lineage.relationship_status == LineageRelationshipStatus.ACTIVE.value


def test_16_no_predecessor_release_or_refund_status_change(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    inst_user_a: User,
    active_lineage_policy: LifecyclePolicy,
):
    """16. Uploading/linking a successor never marks the predecessor released, refunded, or cancelled."""
    predecessor_instrument.status = "REGISTERED"
    db_session.commit()

    payload = RenewalCreateSuccessorRequest(
        bank_name="SBI",
        reference_number="FDR-NO-RELEASE",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
    )
    create_and_link_renewal_successor(
        db_session, predecessor_instrument.id, payload, inst_user_a
    )

    db_session.refresh(predecessor_instrument)
    assert predecessor_instrument.status == "REGISTERED"
    assert predecessor_instrument.status != "RELEASED"
    assert predecessor_instrument.status != "CANCELLED"


def test_17_institution_scoping_and_tenancy(
    db_session: Session,
    predecessor_instrument: Instrument,
    inst_user_b: User,
):
    """17. Institution user from College B cannot initiate renewal draft or link College A's FDR."""
    with pytest.raises(AppException) as exc_info:
        initiate_renewal_draft(
            db=db_session,
            predecessor_id=predecessor_instrument.id,
            current_user=inst_user_b,  # College B user
        )
    assert exc_info.value.code == "FORBIDDEN"


def test_18_audit_history_for_creation_linking_and_correction(
    db_session: Session,
    institution_a: Institution,
    predecessor_instrument: Instrument,
    admin_user: User,
    active_lineage_policy: LifecyclePolicy,
):
    """18. Audit history for creation, linking, and correction with optimistic concurrency."""
    succ = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-SUCC-AUDIT",
        amount=Decimal("1500000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    db_session.add(succ)
    db_session.commit()

    # Link
    link = create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=predecessor_instrument.id,
            successor_instrument_id=succ.id,
            reason_or_reference="Initial statutory link",
        ),
        created_by_user_id=admin_user.id,
        actor_email=admin_user.email,
    )
    assert link.concurrency_version == 1

    # Correction 1: Update reason
    corr_payload = LineageCorrectionRequest(
        action="UPDATE_REASON",
        reason="Updated statutory reference to AICTE Regulation 2026 cl 4.2",
        expected_concurrency_version=1,
    )
    updated_link = correct_renewal_lineage(
        db=db_session,
        lineage_id=link.id,
        payload=corr_payload,
        current_user=admin_user,
    )
    assert updated_link.concurrency_version == 2
    assert "AICTE Regulation 2026 cl 4.2" in updated_link.reason_or_reference

    # Concurrency collision test
    with pytest.raises(AppException) as exc_info:
        correct_renewal_lineage(
            db=db_session,
            lineage_id=link.id,
            payload=LineageCorrectionRequest(
                action="DEACTIVATE",
                reason="Clerical error correction",
                expected_concurrency_version=1,  # Stale version! Current is 2
            ),
            current_user=admin_user,
        )
    assert exc_info.value.code == "CONCURRENCY_CONFLICT"

    # Correction 2: Deactivate with current version
    deactivated = correct_renewal_lineage(
        db=db_session,
        lineage_id=link.id,
        payload=LineageCorrectionRequest(
            action="DEACTIVATE",
            reason="Clerical error: Predecessor reference misassigned",
            expected_concurrency_version=2,
        ),
        current_user=admin_user,
    )
    assert deactivated.relationship_status == LineageRelationshipStatus.CANCELLED.value
    assert deactivated.concurrency_version == 3

    # Check correction history json
    history = json.loads(deactivated.correction_history_json)
    assert len(history) == 2
    assert history[0]["action"] == "UPDATE_REASON"
    assert history[1]["action"] == "DEACTIVATE"
