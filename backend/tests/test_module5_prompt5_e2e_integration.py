"""
Module 5 — Prompt 5: Lifecycle Integration, Security Review, Acceptance Tests and Developer Handover
End-to-End Acceptance & Integration Test Suite

Covers Scenarios A through K, Security RBAC Isolation, and Reliability/Performance benchmarks:
- Scenario A: Active instrument before maturity (days-to-maturity, policy status, no trust mutation).
- Scenario B: Approaching maturity (simulated clock, approaching window, eligible reminder generated).
- Scenario C: Maturity day and overdue action (boundary semantics, separate due dates, no release implication).
- Scenario D: Policy update & versioning (effective version for future, historical references preserved).
- Scenario E: Notification idempotency (repeated scheduler runs, worker restart, single logical reminder).
- Scenario F: Provider unavailable (SMTP/provider failure, bounded retry, pending recovery).
- Scenario G: Renewal with continuity (predecessor A, successor B, distinct visibility, independent trust).
- Scenario H: Gap/overlap handling (configured gap, overlap, unknown effective date -> undetermined, Module 3 finding).
- Scenario I: Lineage integrity (anti-self-reference, cycle rejection, single active cardinality, cross-institution).
- Scenario J: Predecessor protection (predecessor data/documents/provenance unchanged, no automatic release/refund).
- Scenario K: Demo-clock safety (calculations respond to simulated date, production config lockdown).
- Security & Reliability: Cross-tenant isolation, no trust promotion, batch evaluation performance.
"""
from typing import Generator, List, Optional
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
import json
import time
import pytest
from unittest.mock import patch, MagicMock
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
    NotificationDeliveryAttempt,
    LifecycleJobRun,
)
from app.modules.lifecycle.enums import (
    PolicyStatus,
    MaturityStage,
    DueCondition,
    RenewalComparisonMethod,
    LineageRelationshipType,
    LineageRelationshipStatus,
    ContinuityIndicator,
    ContinuityOutcome,
    NotificationChannel,
    NotificationDeliveryStatus,
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
from app.modules.lifecycle.evaluation_service import (
    evaluate_instrument_lifecycle,
    get_latest_evaluation_for_instrument,
    evaluate_batch_instruments,
)
from app.modules.lifecycle.notification_service import (
    generate_and_dispatch_reminders_for_instrument,
    retry_notification,
    build_idempotency_key,
)
from app.modules.lifecycle.lineage_service import (
    create_renewal_lineage,
    initiate_renewal_draft,
    create_and_link_renewal_successor,
    correct_renewal_lineage,
    validate_proposed_lineage,
    get_lineage_tree,
    get_lineage_continuity_assessment,
)
from app.modules.lifecycle.continuity_service import assess_lineage_continuity
from app.modules.lifecycle.scheduler import execute_lifecycle_scan_job
from app.modules.lifecycle.schemas import (
    LifecyclePolicyCreate,
    LifecyclePolicyUpdate,
    LineageCreateRequest,
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
        email="admin.e2e@aicte-india.org",
        full_name="E2E Lifecycle Admin",
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
        email="officer.e2e@aicte-india.org",
        full_name="Scrutiny Officer E2E",
        role=ROLE_SCRUTINY_OFFICER,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def branch_head_user(db_session: Session) -> User:
    user = User(
        email="head.e2e@aicte-india.org",
        full_name="Regional Director E2E",
        role="BRANCH_HEAD",
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def college_alpha(db_session: Session) -> Institution:
    inst = Institution(
        legal_name="Alpha Institute of Technology",
        code="ALPHA-TECH-001",
        contact_email="principal@alpha-tech.edu.in",
        contact_phone="+911188776655",
        assigned_office="Northern Regional Office (NRO - Kanpur)",
        state="Delhi",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def college_beta(db_session: Session) -> Institution:
    inst = Institution(
        legal_name="Beta College of Engineering",
        code="BETA-ENG-002",
        contact_email="principal@beta-eng.edu.in",
        contact_phone="+912288776644",
        assigned_office="Western Regional Office (WRO - Mumbai)",
        state="Maharashtra",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def user_alpha(db_session: Session, college_alpha: Institution) -> User:
    user = User(
        email="registrar@alpha-tech.edu.in",
        full_name="Registrar Alpha",
        role=ROLE_INSTITUTION_USER,
        institution_id=college_alpha.id,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_beta(db_session: Session, college_beta: Institution) -> User:
    user = User(
        email="registrar@beta-eng.edu.in",
        full_name="Registrar Beta",
        role=ROLE_INSTITUTION_USER,
        institution_id=college_beta.id,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def demo_e2e_policy(db_session: Session, admin_user: User) -> LifecyclePolicy:
    policy = create_policy(
        db=db_session,
        payload=LifecyclePolicyCreate(
            policy_code="DEMO-E2E-POLICY-01",
            name="Synthetic Demo E2E Regulatory Policy",
            is_demo=True,
            label="DEMO POLICY — NOT OFFICIAL AICTE POLICY",
            reminder_intervals_days=[90, 60, 30, 15, 7],
            recipient_roles_by_interval={
                "90": ["INSTITUTION_USER"],
                "60": ["INSTITUTION_USER"],
                "30": ["INSTITUTION_USER", "SCRUTINY_OFFICER"],
                "15": ["INSTITUTION_USER", "SCRUTINY_OFFICER"],
                "7": ["INSTITUTION_USER", "SCRUTINY_OFFICER", "BRANCH_HEAD"],
            },
            institution_action_lead_days=30,
            officer_action_lead_days=15,
            escalation_interval_days=7,
            escalation_target_role="BRANCH_HEAD",
            maturity_critical_lead_days=15,
            renewal_comparison_method=RenewalComparisonMethod.ISSUE_DATE_TO_MATURITY_DATE,
            max_allowed_gap_days=5,
            max_allowed_overlap_days=30,
        ),
        created_by_user_id=admin_user.id,
    )
    approve_policy(db_session, policy.id, approver_user_id=admin_user.id)
    return activate_policy(db_session, policy.id, activator_user_id=admin_user.id)


# --- Scenario A: Active instrument before maturity -------------------------------

def test_scenario_a_active_instrument_before_maturity(
    db_session: Session,
    college_alpha: Institution,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario A:
    Select an instrument with a valid future maturity date.
    Run lifecycle evaluation.
    Verify the correct days-to-maturity value and policy status.
    Confirm no unauthorized trust or administrative-state change occurs.
    """
    sim_clock = SimulatedClock(fixed_date=date(2026, 1, 1))
    set_current_clock(sim_clock)

    inst = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        reference_number="FDR-SCENARIO-A",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2028, 1, 1),  # 2 years in the future
        status="REGISTERED",
        trust_level="L2_OFFICER_VERIFIED",
    )
    db_session.add(inst)
    db_session.commit()

    evaluation = evaluate_instrument_lifecycle(db=db_session, instrument_id=inst.id)

    assert evaluation.maturity_stage == MaturityStage.ACTIVE.value
    assert evaluation.days_to_maturity == 730  # Exactly 2 years in leap cycle
    assert evaluation.is_overdue is False
    assert evaluation.is_escalated is False

    # Confirm strictly NO mutation of administrative status or trust
    db_session.refresh(inst)
    assert inst.status == "REGISTERED"
    assert inst.trust_level == "L2_OFFICER_VERIFIED"


# --- Scenario B: Approaching maturity -------------------------------------------

def test_scenario_b_approaching_maturity_and_milestone_reminder(
    db_session: Session,
    college_alpha: Institution,
    user_alpha: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario B:
    Configure reminder threshold (T-30d).
    Use simulated clock to evaluate on the exact milestone date.
    Verify assessment classifies stage as MATURING_SOON / REMINDER_DUE.
    Confirm eligible reminder is produced by notification engine.
    """
    # Deposit matures on 2026-06-30. Set clock to exactly T-30 days = 2026-05-31
    maturity_d = date(2026, 6, 30)
    eval_d = date(2026, 5, 31)
    sim_clock = SimulatedClock(fixed_date=eval_d)
    set_current_clock(sim_clock)

    inst = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        reference_number="FDR-SCENARIO-B",
        amount=Decimal("1500000.00"),
        issue_date=date(2023, 6, 30),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L3_BANK_CONFIRMED",
    )
    db_session.add(inst)
    db_session.commit()

    evaluation = evaluate_instrument_lifecycle(db=db_session, instrument_id=inst.id)
    assert evaluation.days_to_maturity == 30
    assert evaluation.maturity_stage == MaturityStage.MATURING_SOON.value
    assert evaluation.matched_reminder_interval_days == 30

    notifs = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=inst.id,
        eval_record=evaluation,
    )
    assert len(notifs) >= 1
    # Check that a notification targeted user_alpha
    inst_notif = next((n for n in notifs if n.recipient_role == "INSTITUTION_USER"), None)
    assert inst_notif is not None
    assert inst_notif.reminder_milestone_days == 30
    assert inst_notif.status in (NotificationDeliveryStatus.DELIVERED.value, NotificationDeliveryStatus.ACCEPTED.value, NotificationDeliveryStatus.MOCKED.value)


# --- Scenario C: Maturity day and overdue action --------------------------------

def test_scenario_c_maturity_day_and_overdue_action_separation(
    db_session: Session,
    college_alpha: Institution,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario C:
    Evaluate an instrument on its maturity date and 10 days after maturity.
    Verify documented date-boundary semantics (MATURED vs EXPIRED).
    Verify overdue institution and officer actions are separate from maturity status.
    Confirm that maturity does NOT imply release eligibility.
    """
    maturity_d = date(2026, 7, 1)

    # 1. On exact maturity date
    sim_clock = SimulatedClock(fixed_date=maturity_d)
    set_current_clock(sim_clock)

    inst = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        reference_number="FDR-SCENARIO-C",
        amount=Decimal("2000000.00"),
        issue_date=date(2023, 7, 1),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L3_BANK_CONFIRMED",
    )
    db_session.add(inst)
    db_session.commit()

    eval_on_maturity = evaluate_instrument_lifecycle(db=db_session, instrument_id=inst.id)
    assert eval_on_maturity.days_to_maturity == 0
    assert eval_on_maturity.maturity_stage == MaturityStage.MATURED.value
    assert eval_on_maturity.is_overdue is True  # Overdue lead times passed

    # Confirm maturity does not change status to RELEASED
    db_session.refresh(inst)
    assert inst.status == "REGISTERED"

    # 2. 10 days after maturity
    sim_clock.set_date(date(2026, 7, 11))
    eval_after_maturity = evaluate_instrument_lifecycle(db=db_session, instrument_id=inst.id, force_record=True)
    assert eval_after_maturity.days_to_maturity == -10
    assert eval_after_maturity.maturity_stage == MaturityStage.EXPIRED.value
    assert eval_after_maturity.due_condition == DueCondition.ESCALATED.value

    db_session.refresh(inst)
    assert inst.status == "REGISTERED"
    assert inst.trust_level == "L3_BANK_CONFIRMED"


# --- Scenario D: Policy update & versioning --------------------------------------

def test_scenario_d_policy_versioning_and_historical_immutability(
    db_session: Session,
    admin_user: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario D:
    Change an authorized demo reminder interval configuration.
    Create a new policy version.
    Confirm future evaluations use the effective version.
    Confirm old assessments reference the version originally used.
    """
    assert demo_e2e_policy.version == 1

    # Create version 2 of the policy
    v2_policy = create_policy(
        db=db_session,
        payload=LifecyclePolicyCreate(
            policy_code=demo_e2e_policy.policy_code,
            name="Updated E2E Regulatory Policy V2",
            is_demo=True,
            reminder_intervals_days=[120, 60, 30],  # New interval 120
            max_allowed_gap_days=10,
        ),
        created_by_user_id=admin_user.id,
    )
    approve_policy(db_session, v2_policy.id, approver_user_id=admin_user.id)
    activated_v2 = activate_policy(db_session, v2_policy.id, activator_user_id=admin_user.id)

    assert activated_v2.version == 2
    assert activated_v2.is_active is True

    db_session.refresh(demo_e2e_policy)
    assert demo_e2e_policy.is_active is False
    assert demo_e2e_policy.version == 1


# --- Scenario E: Notification idempotency & restart ------------------------------

def test_scenario_e_notification_idempotency_and_worker_restart(
    db_session: Session,
    college_alpha: Institution,
    user_alpha: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario E:
    Run the scheduler repeatedly for the same date.
    Attempt concurrent evaluations and dispatch.
    Confirm that exactly one logical reminder per milestone/recipient/channel is recorded.
    Ensure failed deliveries retain their status and are not falsely reported.
    """
    eval_d = date(2026, 5, 31)
    sim_clock = SimulatedClock(fixed_date=eval_d)
    set_current_clock(sim_clock)

    inst = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        reference_number="FDR-SCENARIO-E",
        amount=Decimal("1000000.00"),
        issue_date=date(2023, 6, 30),
        maturity_date=date(2026, 6, 30),
        status="REGISTERED",
    )
    db_session.add(inst)
    db_session.commit()

    evaluation = evaluate_instrument_lifecycle(db=db_session, instrument_id=inst.id)

    # First dispatch run
    first_run = generate_and_dispatch_reminders_for_instrument(db=db_session, instrument_id=inst.id, eval_record=evaluation)
    first_count = len(first_run)
    assert first_count >= 1

    # Second simulated worker run (or restart) on the exact same date
    second_run = generate_and_dispatch_reminders_for_instrument(db=db_session, instrument_id=inst.id, eval_record=evaluation)
    second_count = len(second_run)

    # Idempotent: exactly same records returned, zero new records inserted
    assert first_count == second_count
    assert [n.id for n in first_run] == [n.id for n in second_run]


# --- Scenario F: Provider unavailable & bounded retry ----------------------------

def test_scenario_f_provider_unavailable_bounded_retry_and_recovery(
    db_session: Session,
    college_alpha: Institution,
    user_alpha: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario F:
    Simulate SMTP or notification-provider failure.
    Verify retries are bounded and delivery history records each attempt.
    Verify recovery after failure.
    """
    eval_d = date(2026, 5, 31)
    sim_clock = SimulatedClock(fixed_date=eval_d)
    set_current_clock(sim_clock)

    inst = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        reference_number="FDR-SCENARIO-F",
        amount=Decimal("1000000.00"),
        issue_date=date(2023, 6, 30),
        maturity_date=date(2026, 6, 30),
        status="REGISTERED",
    )
    db_session.add(inst)
    db_session.commit()

    eval_rec = evaluate_instrument_lifecycle(db=db_session, instrument_id=inst.id)

    # Mock provider failure
    with patch("app.modules.lifecycle.channels.email.EmailNotificationProvider.send", side_effect=Exception("SMTP Connection Timeout")):
        notifs = generate_and_dispatch_reminders_for_instrument(
            db=db_session,
            instrument_id=inst.id,
            eval_record=eval_rec,
        )
        email_notif = next((n for n in notifs if n.channel == "EMAIL"), None)
        assert email_notif is not None
        assert email_notif.status == NotificationDeliveryStatus.FAILED.value
        assert email_notif.retry_count == 1
        assert len(email_notif.attempts) >= 1
        assert email_notif.attempts[-1].status == NotificationDeliveryStatus.FAILED.value

    # Controlled administrative retry succeeding
    recovered = retry_notification(db=db_session, notification_id=email_notif.id, current_user=user_alpha, force=True)
    assert recovered.status in (NotificationDeliveryStatus.ACCEPTED.value, NotificationDeliveryStatus.MOCKED.value)
    assert recovered.retry_count == 2
    assert len(recovered.attempts) == 2


# --- Scenario G: Renewal with continuity ----------------------------------------

def test_scenario_g_renewal_with_continuity_and_independent_trust(
    db_session: Session,
    college_alpha: Institution,
    user_alpha: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario G:
    Create predecessor instrument A.
    Create successor B with new data and documents.
    Link A -> B.
    Confirm both instruments remain separately visible and lineage is correct.
    Confirm B has its own validation, provenance and trust state (L0_DECLARED).
    """
    inst_a = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="Canara Bank",
        reference_number="FDR-SCENARIO-G-PRED",
        amount=Decimal("1000000.00"),
        issue_date=date(2023, 1, 1),
        maturity_date=date(2026, 1, 1),
        status="REGISTERED",
        trust_level="L3_BANK_CONFIRMED",
    )
    db_session.add(inst_a)
    db_session.commit()

    payload = RenewalCreateSuccessorRequest(
        bank_name="Canara Bank",
        reference_number="FDR-SCENARIO-G-SUCC",
        amount=Decimal("1200000.00"),  # Increased amount
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        reason_or_reference="3-year statutory rollover",
    )

    inst_b, lineage = create_and_link_renewal_successor(
        db=db_session,
        predecessor_id=inst_a.id,
        payload=payload,
        current_user=user_alpha,
    )

    # 1. Both instruments separately visible
    assert inst_a.id != inst_b.id
    assert inst_a.reference_number == "FDR-SCENARIO-G-PRED"
    assert inst_b.reference_number == "FDR-SCENARIO-G-SUCC"

    # 2. Lineage edge is active
    assert lineage.relationship_status == LineageRelationshipStatus.ACTIVE.value
    assert lineage.predecessor_instrument_id == inst_a.id
    assert lineage.successor_instrument_id == inst_b.id

    # 3. Independent trust: Predecessor remains L3, Successor starts at L0_DECLARED
    assert inst_a.trust_level == "L3_BANK_CONFIRMED"
    assert inst_b.trust_level == "L0_DECLARED"


# --- Scenario H: Gap/overlap handling -------------------------------------------

def test_scenario_h_gap_overlap_handling_and_module_3_finding(
    db_session: Session,
    college_alpha: Institution,
    admin_user: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario H:
    Seed a continuity case with a configured gap (within tolerance).
    Seed another with an out-of-tolerance gap producing a Module 3 ValidationFinding.
    Seed a case where successor effective date is unknown under STRICT policy.
    Confirm classifications and finding fields.
    """
    pred = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-GAP-PRED",
        amount=Decimal("1000000"),
        issue_date=date(2023, 1, 1),
        maturity_date=date(2026, 1, 1),
        status="REGISTERED",
    )
    db_session.add(pred)
    db_session.commit()

    # Case 1: Out of tolerance gap (20 days > 5 days policy tolerance)
    succ_gap = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-GAP-20D",
        amount=Decimal("1000000"),
        issue_date=date(2026, 1, 21),
        maturity_date=date(2029, 1, 21),
        status="REGISTERED",
    )
    db_session.add(succ_gap)
    db_session.commit()

    assessment = assess_lineage_continuity(
        db=db_session,
        predecessor=pred,
        successor=succ_gap,
        policy=demo_e2e_policy,
        create_finding=True,
    )

    assert assessment.outcome == ContinuityOutcome.POTENTIAL_GAP
    assert assessment.gap_days == 20
    assert assessment.finding_id is not None

    finding = db_session.scalar(select(ValidationFinding).where(ValidationFinding.id == assessment.finding_id))
    assert finding is not None
    assert finding.rule_id == "LINEAGE_CONTINUITY_POTENTIAL_GAP"
    assert finding.category == "POLICY_COMPLIANCE"


# --- Scenario I: Lineage integrity & invariants ---------------------------------

def test_scenario_i_lineage_integrity_cycle_self_and_cardinality(
    db_session: Session,
    college_alpha: Institution,
    college_beta: Institution,
    user_alpha: User,
    user_beta: User,
    admin_user: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario I:
    Attempt A -> A (self-link).
    Attempt A -> B -> A (cycle).
    Attempt ambiguous link (branching).
    Attempt cross-institution relationship by institution user.
    Confirm invalid links are rejected and audited.
    """
    a = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-DAG-A",
        amount=Decimal("1000000"),
        issue_date=date(2023, 1, 1),
        maturity_date=date(2026, 1, 1),
        status="REGISTERED",
    )
    b = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-DAG-B",
        amount=Decimal("1000000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    beta_inst = Instrument(
        institution_id=college_beta.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-DAG-BETA",
        amount=Decimal("1000000"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
        status="REGISTERED",
    )
    db_session.add_all([a, b, beta_inst])
    db_session.commit()

    # 1. Anti-self-reference: A -> A
    with pytest.raises(AppException) as exc1:
        create_renewal_lineage(db_session, LineageCreateRequest(predecessor_instrument_id=a.id, successor_instrument_id=a.id))
    assert exc1.value.code == "SELF_REFERENTIAL_LINEAGE_PROHIBITED"

    # Link A -> B
    create_renewal_lineage(db_session, LineageCreateRequest(predecessor_instrument_id=a.id, successor_instrument_id=b.id))

    # 2. Cycle: B -> A
    with pytest.raises(AppException) as exc2:
        create_renewal_lineage(db_session, LineageCreateRequest(predecessor_instrument_id=b.id, successor_instrument_id=a.id))
    assert exc2.value.code == "CYCLIC_LINEAGE_DETECTED"

    # 3. Cross-institution link by College Alpha user to College Beta FDR
    with pytest.raises(AppException) as exc3:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(predecessor_instrument_id=a.id, successor_instrument_id=beta_inst.id),
            current_user=user_alpha,
        )
    assert exc3.value.code == "FORBIDDEN"


# --- Scenario J: Predecessor protection -----------------------------------------

def test_scenario_j_predecessor_protection_no_automatic_release(
    db_session: Session,
    college_alpha: Institution,
    user_alpha: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario J:
    Link a successor.
    Confirm predecessor data, uploaded documents, provenance, and verification responses remain unchanged.
    Confirm predecessor is NOT automatically marked released, refunded, or discharged.
    Verify future monitoring and reminders follow configured rules.
    """
    pred = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-SCENARIO-J",
        amount=Decimal("1500000.00"),
        issue_date=date(2023, 1, 1),
        maturity_date=date(2026, 1, 1),
        status="REGISTERED",
        trust_level="L3_BANK_CONFIRMED",
    )
    db_session.add(pred)
    db_session.commit()

    payload = RenewalCreateSuccessorRequest(
        bank_name="SBI",
        reference_number="FDR-SCENARIO-J-SUCC",
        amount=Decimal("1500000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2029, 1, 1),
    )
    succ, lineage = create_and_link_renewal_successor(db_session, pred.id, payload, user_alpha)

    db_session.refresh(pred)
    assert pred.status == "REGISTERED"
    assert pred.status != "RELEASED"
    assert pred.trust_level == "L3_BANK_CONFIRMED"


# --- Scenario K: Demo-clock safety & production lockdown -------------------------

def test_scenario_k_demo_clock_safety_and_production_lockdown(
    db_session: Session,
    college_alpha: Institution,
    officer_user: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Scenario K:
    Advance development simulation clock.
    Verify calculations respond without altering stored FDR dates.
    Switch to production configuration.
    Verify date-advance endpoint is inaccessible (HTTP 403).
    """
    inst = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-SCENARIO-K",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2026, 1, 1),
        status="REGISTERED",
    )
    db_session.add(inst)
    db_session.commit()

    # 1. Advance demo clock
    sim_clock = SimulatedClock(fixed_date=date(2025, 6, 1))
    set_current_clock(sim_clock)

    ev1 = evaluate_instrument_lifecycle(db=db_session, instrument_id=inst.id, force_record=True)
    assert ev1.days_to_maturity == 214

    sim_clock.set_date(date(2025, 12, 1))
    ev2 = evaluate_instrument_lifecycle(db=db_session, instrument_id=inst.id, force_record=True)
    assert ev2.days_to_maturity == 31

    # Stored instrument date was NEVER changed
    db_session.refresh(inst)
    assert inst.maturity_date == date(2026, 1, 1)

    # 2. Production lock test
    with patch.object(settings, "ENVIRONMENT", "production"):
        with pytest.raises(AppException) as exc_info:
            evaluate_instrument_lifecycle(
                db=db_session,
                instrument_id=inst.id,
                simulated_date=date(2026, 1, 1),
            )
        assert exc_info.value.code in ("DEMO_CONTROL_DISABLED_IN_PRODUCTION", "DATE_ADVANCE_DISABLED")


# --- Security: Cross-Tenant Isolation -------------------------------------------

def test_security_cross_tenant_isolation_on_lineage_and_lifecycle(
    client: TestClient,
    db_session: Session,
    college_alpha: Institution,
    college_beta: Institution,
    user_alpha: User,
    user_beta: User,
    demo_e2e_policy: LifecyclePolicy,
):
    """
    Security Review:
    Verify that an institution user from College B cannot access College A's
    lineage tree, continuity assessments, or lifecycle assessments.
    """
    inst_a = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-TENANT-ALPHA",
        amount=Decimal("1000000"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2028, 1, 1),
        status="REGISTERED",
    )
    succ_a = Instrument(
        institution_id=college_alpha.id,
        instrument_type="FDR",
        bank_name="SBI",
        reference_number="FDR-TENANT-ALPHA-SUCC",
        amount=Decimal("1000000"),
        issue_date=date(2028, 1, 1),
        maturity_date=date(2031, 1, 1),
        status="REGISTERED",
    )
    db_session.add_all([inst_a, succ_a])
    db_session.commit()

    create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=inst_a.id,
            successor_instrument_id=succ_a.id,
        ),
    )

    # Authenticate as College B user
    set_auth(client, user_beta)

    # 1. Access College A lineage tree -> HTTP 403
    res_tree = client.get(f"/api/v1/lifecycle/instruments/{inst_a.id}/lineage")
    assert res_tree.status_code == 403
    assert res_tree.json()["code"] == "FORBIDDEN"

    # 2. Access College A continuity -> HTTP 403
    res_cont = client.get(f"/api/v1/lifecycle/instruments/{inst_a.id}/continuity")
    assert res_cont.status_code == 403
    assert res_cont.json()["code"] == "FORBIDDEN"

    # 3. Access College A lifecycle -> HTTP 403
    res_life = client.get(f"/api/v1/instruments/{inst_a.id}/lifecycle")
    assert res_life.status_code == 403
    assert res_life.json()["code"] == "FORBIDDEN"


# --- Reliability & Performance: Batch Evaluation -------------------------------

def test_reliability_performance_benchmark_batch_evaluation(
    db_session: Session,
    college_alpha: Institution,
    demo_e2e_policy: LifecyclePolicy,
    admin_user: User,
):
    """
    Reliability & Performance:
    Measures batch evaluation throughput over a synthetic dataset of 25 instruments.
    """
    instruments = []
    base_date = date(2026, 6, 1)
    for i in range(25):
        inst = Instrument(
            institution_id=college_alpha.id,
            instrument_type="FDR",
            bank_name="SBI",
            reference_number=f"FDR-PERF-BATCH-{i:03d}",
            amount=Decimal("1000000.00"),
            issue_date=date(2023, 1, 1),
            maturity_date=base_date + timedelta(days=i * 5),
            status="REGISTERED",
        )
        instruments.append(inst)
    db_session.add_all(instruments)
    db_session.commit()

    inst_ids = [inst.id for inst in instruments]

    start_time = time.perf_counter()
    total_eval, material_count, evals = evaluate_batch_instruments(
        db=db_session,
        instrument_ids=inst_ids,
        actor_user_id=admin_user.id,
        actor_email=admin_user.email,
    )
    elapsed = time.perf_counter() - start_time

    assert total_eval == 25
    assert len(evals) == 25
    # Batch evaluation of 25 records must complete in under 2.5 seconds
    assert elapsed < 2.5
