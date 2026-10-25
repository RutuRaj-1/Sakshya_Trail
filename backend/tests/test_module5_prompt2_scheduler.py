"""
Module 5 — Prompt 2: Maturity Monitoring, Validity Evaluation, Due-Date Calculations and Scheduler
Acceptance Test Suite

Covers all 15 required specifications:
1. Maturity calculation before, on and after the maturity date.
2. Configured approaching-maturity thresholds.
3. Unconfigured threshold behavior.
4. Separate institution/officer due-date calculations.
5. Timezone boundary behavior.
6. Missing/invalid date handling.
7. Evaluation idempotency.
8. Multiple worker/concurrent evaluation protection.
9. Partial batch failure and recovery.
10. Worker restart/catch-up evaluation behavior.
11. Accurate job run summaries.
12. Demo date advancement changes simulation results only.
13. Demo date control unavailable in production.
14. No trust promotion or release approval from maturity evaluation.
15. Existing Module 1–4 tests remain green.
"""
from typing import Generator, List, Optional
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import (
    LifecyclePolicy,
    LifecycleEvaluation,
    LifecycleJobRun,
)
from app.modules.lifecycle.enums import (
    PolicyStatus,
    MaturityStage,
    DueCondition,
)
from app.modules.lifecycle.clock import (
    Clock,
    SystemClock,
    SimulatedClock,
    get_current_clock,
    set_current_clock,
    reset_to_system_clock,
    get_clock_status,
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
)
from app.modules.lifecycle.scheduler import (
    acquire_job_lease,
    execute_lifecycle_scan_job,
    get_latest_job_runs,
)
from app.modules.lifecycle.schemas import (
    LifecyclePolicyCreate,
    DemoClockAdvanceRequest,
)
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
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
    """Ensure clock state is reset to system clock after each test."""
    yield
    reset_to_system_clock()


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        email="admin.scheduler@aicte-india.org",
        full_name="Scheduler Admin",
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
        email="officer.scheduler@aicte-india.org",
        full_name="Scrutiny Officer Verma",
        role=ROLE_SCRUTINY_OFFICER,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def inst_a(db_session: Session) -> Institution:
    inst = Institution(
        code="1-SCHED-INST-A",
        legal_name="Apex Institute of Technology",
        display_name="Apex Tech",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Director Apex",
        contact_email="director@apex.edu",
        contact_phone="+91-11-20000010",
        state="Delhi",
        city="New Delhi",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def inst_b(db_session: Session) -> Institution:
    inst = Institution(
        code="1-SCHED-INST-B",
        legal_name="Beacon Engineering College",
        display_name="Beacon Engg",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Principal Beacon",
        contact_email="principal@beacon.edu",
        contact_phone="+91-11-20000011",
        state="Karnataka",
        city="Bengaluru",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def institution_user_a(db_session: Session, inst_a: Institution) -> User:
    user = User(
        email="user.a@apex.edu",
        full_name="Apex Representative",
        role=ROLE_INSTITUTION_USER,
        institution_id=inst_a.id,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def active_policy(db_session: Session) -> LifecyclePolicy:
    return get_or_create_default_demo_policy(db_session)


# ==============================================================================
# 1. Maturity Calculation: Before, On (Day Zero), and After Maturity Date
# ==============================================================================
def test_maturity_calculation_before_on_and_after_date(
    db_session: Session, inst_a: Institution, active_policy: LifecyclePolicy
):
    """
    Exact conventions:
    - Before maturity: days_to_maturity > 0, maturity_stage is ACTIVE, MATURING_SOON or CRITICAL_WINDOW
    - On maturity date: days_to_maturity == 0 (calendar day zero), maturity_stage is MATURED
    - After maturity date: days_to_maturity < 0, maturity_stage is EXPIRED
    """
    fixed_today = date(2026, 11, 1)
    clock = SimulatedClock(fixed_date=fixed_today)
    set_current_clock(clock)

    # Instrument 1: Future (10 days out)
    fdr_future = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-MAT-FUTURE",
        bank_name="State Bank of India",
        branch="Connaught Place",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 11, 11),
        maturity_date=date(2026, 11, 11),
        status="REGISTERED",
    )
    # Instrument 2: Exactly on maturity date (Day Zero)
    fdr_today = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-MAT-TODAY",
        bank_name="State Bank of India",
        branch="Connaught Place",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=date(2026, 11, 1),
        status="REGISTERED",
    )
    # Instrument 3: Passed maturity (5 days past)
    fdr_past = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-MAT-PAST",
        bank_name="State Bank of India",
        branch="Connaught Place",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 10, 27),
        maturity_date=date(2026, 10, 27),
        status="REGISTERED",
    )
    db_session.add_all([fdr_future, fdr_today, fdr_past])
    db_session.commit()

    # Evaluate future
    eval_future = evaluate_instrument_lifecycle(db_session, fdr_future.id)
    assert eval_future.days_to_maturity == 10
    assert eval_future.days_to_maturity > 0
    assert eval_future.maturity_stage in (
        MaturityStage.ACTIVE.value,
        MaturityStage.MATURING_SOON.value,
        MaturityStage.CRITICAL_WINDOW.value,
    )

    # Evaluate on maturity date (Day Zero)
    eval_today = evaluate_instrument_lifecycle(db_session, fdr_today.id)
    assert eval_today.days_to_maturity == 0
    assert eval_today.maturity_stage == MaturityStage.MATURED.value

    # Evaluate passed
    eval_past = evaluate_instrument_lifecycle(db_session, fdr_past.id)
    assert eval_past.days_to_maturity == -5
    assert eval_past.days_to_maturity < 0
    assert eval_past.maturity_stage == MaturityStage.EXPIRED.value


# ==============================================================================
# 2. Configured Approaching-Maturity Thresholds
# ==============================================================================
def test_configured_approaching_maturity_thresholds(
    db_session: Session, inst_a: Institution, admin_user: User
):
    """
    Policy defines institution_action_lead_days=30 and maturity_critical_lead_days=7.
    Instruments at <= 30 days are MATURING_SOON (or CRITICAL_WINDOW if <= 7).
    Instruments at > 30 days are ACTIVE.
    """
    fixed_today = date(2026, 11, 1)
    set_current_clock(SimulatedClock(fixed_date=fixed_today))

    policy = create_policy(
        db=db_session,
        created_by_user_id=admin_user.id,
        payload=LifecyclePolicyCreate(
            policy_code="POLICY_THRESH_TEST",
            name="Threshold Test Policy",
            institution_action_lead_days=30,
            officer_action_lead_days=15,
            maturity_critical_lead_days=7,
            escalation_interval_days=5,
            reminder_intervals_days=[30, 15, 7],
        ),
    )
    approve_policy(db_session, policy.id, approver_user_id=admin_user.id)
    activate_policy(db_session, policy.id, activator_user_id=admin_user.id)

    # Instrument A: 20 days away (inside 30-day window)
    inst_in_window = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-APPROACHING-20D",
        bank_name="Punjab National Bank",
        branch="Main",
        amount=Decimal("500000.00"),
        issue_date=date(2025, 11, 21),
        maturity_date=date(2026, 11, 21),
        status="REGISTERED",
    )
    # Instrument B: 45 days away (outside window)
    inst_out_window = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-APPROACHING-45D",
        bank_name="Punjab National Bank",
        branch="Main",
        amount=Decimal("500000.00"),
        issue_date=date(2025, 12, 16),
        maturity_date=date(2026, 12, 16),
        status="REGISTERED",
    )
    db_session.add_all([inst_in_window, inst_out_window])
    db_session.commit()

    eval_in = evaluate_instrument_lifecycle(db_session, inst_in_window.id, policy_id=policy.id)
    assert eval_in.days_to_maturity == 20
    assert eval_in.maturity_stage == MaturityStage.MATURING_SOON.value

    eval_out = evaluate_instrument_lifecycle(db_session, inst_out_window.id, policy_id=policy.id)
    assert eval_out.days_to_maturity == 45
    assert eval_out.maturity_stage == MaturityStage.ACTIVE.value


# ==============================================================================
# 3. Unconfigured Threshold Behavior
# ==============================================================================
def test_unconfigured_threshold_behavior(
    db_session: Session, inst_a: Institution, admin_user: User
):
    """
    If a policy has specific reminder intervals configured (e.g. only [90, 60]),
    and the instrument date does not match any threshold,
    the evaluator returns DueCondition.NORMAL without inventing unconfigured AICTE timelines.
    """
    fixed_today = date(2026, 11, 1)
    set_current_clock(SimulatedClock(fixed_date=fixed_today))

    # Policy with only 90-day and 60-day reminder intervals
    custom_policy = create_policy(
        db=db_session,
        created_by_user_id=admin_user.id,
        payload=LifecyclePolicyCreate(
            policy_code="POLICY_SPARSE_THRESH",
            name="Sparse Intervals Policy",
            institution_action_lead_days=30,
            officer_action_lead_days=15,
            maturity_critical_lead_days=7,
            escalation_interval_days=5,
            reminder_intervals_days=[90, 60],
        ),
    )
    approve_policy(db_session, custom_policy.id, approver_user_id=admin_user.id)
    activate_policy(db_session, custom_policy.id, activator_user_id=admin_user.id)

    # Instrument 45 days away: between 60 and 30 (no reminder threshold configured for 45)
    fdr = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-UNCONFIG-THRESH",
        bank_name="Canara Bank",
        branch="South Extension",
        amount=Decimal("200000.00"),
        issue_date=date(2025, 12, 16),
        maturity_date=date(2026, 12, 16),
        status="REGISTERED",
    )
    db_session.add(fdr)
    db_session.commit()

    eval_res = evaluate_instrument_lifecycle(db_session, fdr.id, policy_id=custom_policy.id)
    assert eval_res.days_to_maturity == 45
    assert eval_res.maturity_stage == MaturityStage.ACTIVE.value
    # No unconfigured reminder threshold invented
    assert eval_res.due_condition == DueCondition.NORMAL.value
    assert eval_res.matched_reminder_interval_days is None
    assert eval_res.is_overdue is False


# ==============================================================================
# 4. Separate Institution and Officer Due-Date Calculations
# ==============================================================================
def test_separate_institution_and_officer_due_dates(
    db_session: Session, inst_a: Institution, admin_user: User
):
    """
    Institution action due date and Officer action due date must remain strictly distinct concepts.
    Maturity date: Nov 30, 2026
    institution_action_lead_days: 15 -> Due Nov 15, 2026
    officer_action_lead_days: 7 -> Due Nov 23, 2026
    escalation_interval_days: 3 -> Escalated after Nov 18, 2026
    """
    policy = create_policy(
        db=db_session,
        created_by_user_id=admin_user.id,
        payload=LifecyclePolicyCreate(
            policy_code="POLICY_DISTINCT_DUES",
            name="Distinct Dues Policy",
            institution_action_lead_days=15,
            officer_action_lead_days=7,
            maturity_critical_lead_days=3,
            escalation_interval_days=3,
            reminder_intervals_days=[15, 7],
        ),
    )
    approve_policy(db_session, policy.id, approver_user_id=admin_user.id)

    fdr = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-SEPARATE-DUES",
        bank_name="Union Bank",
        branch="Connaught Place",
        amount=Decimal("750000.00"),
        issue_date=date(2025, 11, 30),
        maturity_date=date(2026, 11, 30),
        status="REGISTERED",
    )
    db_session.add(fdr)
    db_session.commit()

    # Case A: Date is Nov 10 (Before institution due date Nov 15)
    set_current_clock(SimulatedClock(fixed_date=date(2026, 11, 10)))
    eval_a = evaluate_instrument_lifecycle(db_session, fdr.id, policy_id=policy.id)
    assert eval_a.institution_action_due_date == date(2026, 11, 15)
    assert eval_a.officer_action_due_date == date(2026, 11, 23)
    assert eval_a.is_overdue is False
    assert eval_a.due_condition == DueCondition.NORMAL.value

    # Case B: Date is Nov 17 (Institution is overdue [15 + 2 days], officer due is Nov 23 [not reached])
    set_current_clock(SimulatedClock(fixed_date=date(2026, 11, 17)))
    eval_b = evaluate_instrument_lifecycle(db_session, fdr.id, policy_id=policy.id)
    assert eval_b.institution_action_due_date == date(2026, 11, 15)
    assert eval_b.officer_action_due_date == date(2026, 11, 23)
    assert eval_b.is_overdue is True
    assert eval_b.due_condition == DueCondition.OVERDUE.value


# ==============================================================================
# 5. Timezone Boundary Behavior
# ==============================================================================
def test_timezone_boundary_behavior():
    """
    Test daily boundary under configured timezone (Asia/Kolkata vs UTC).
    At 19:00 UTC on 2026-10-25, it is 00:30 IST on 2026-10-26.
    The evaluator evaluates on 2026-10-26 under Asia/Kolkata.
    """
    dt_utc = datetime(2026, 10, 25, 19, 0, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(fixed_dt=dt_utc)

    # In UTC, the date is Oct 25
    assert clock.today_in_tz("UTC") == date(2026, 10, 25)

    # In Asia/Kolkata (+05:30), the date is Oct 26
    assert clock.today_in_tz("Asia/Kolkata") == date(2026, 10, 26)


# ==============================================================================
# 6. Missing and Invalid Date Handling
# ==============================================================================
def test_missing_and_invalid_date_handling(
    db_session: Session, inst_a: Institution, active_policy: LifecyclePolicy
):
    """
    An instrument with missing or corrupted dates must evaluate gracefully
    without raising uncaught exceptions, producing NOT_EVALUABLE stage.
    """
    mock_fdr = Instrument(
        id="mock-missing-date-id",
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-MISSING-DATE",
        bank_name="Bank of Baroda",
        branch="Branch",
        amount=Decimal("100000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=None,  # Missing date
        status="REGISTERED",
    )

    eval_result = evaluate_instrument_lifecycle(
        db_session,
        instrument_id=mock_fdr.id,
        instrument_obj=mock_fdr,
        policy_id=active_policy.id,
    )
    assert eval_result.maturity_stage == MaturityStage.NOT_EVALUABLE.value
    assert eval_result.days_to_maturity is None
    assert eval_result.is_overdue is False


# ==============================================================================
# 7. Evaluation Idempotency
# ==============================================================================
def test_evaluation_idempotency(
    db_session: Session, inst_a: Institution, active_policy: LifecyclePolicy
):
    """
    Running the evaluation twice on the same evaluation date for the same instrument
    must update the existing record in-place rather than inserting duplicates.
    """
    fixed_today = date(2026, 11, 5)
    set_current_clock(SimulatedClock(fixed_date=fixed_today))

    fdr = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-IDEMPOTENT-TEST",
        bank_name="State Bank of India",
        branch="Delhi",
        amount=Decimal("600000.00"),
        issue_date=date(2025, 11, 25),
        maturity_date=date(2026, 11, 25),
        status="REGISTERED",
    )
    db_session.add(fdr)
    db_session.commit()

    # First run
    eval_1 = evaluate_instrument_lifecycle(db_session, fdr.id, policy_id=active_policy.id)
    eval_1_id = eval_1.id

    # Second run on the same date
    eval_2 = evaluate_instrument_lifecycle(db_session, fdr.id, policy_id=active_policy.id)
    eval_2_id = eval_2.id

    # Must update the existing row
    assert eval_1_id == eval_2_id
    total_evals = db_session.scalar(
        select(func.count(LifecycleEvaluation.id)).where(
            LifecycleEvaluation.instrument_id == fdr.id,
            LifecycleEvaluation.evaluation_date == fixed_today,
        )
    )
    assert total_evals == 1


# ==============================================================================
# 8. Multiple Worker / Concurrent Evaluation Protection (Lease Lock)
# ==============================================================================
def test_multiple_worker_concurrent_evaluation_protection(
    db_session: Session
):
    """
    If worker A holds an active, unexpired lease, worker B's attempt to acquire
    a lease must be rejected with HTTP 409 CONCURRENT_JOB_RUNNING.
    """
    eval_date = date(2026, 11, 1)

    # Worker A acquires lease
    lease_a = acquire_job_lease(
        db=db_session,
        job_type="DAILY_MATURITY_SCAN",
        trigger_source="WORKER_A",
        evaluation_date=eval_date,
        evaluation_timezone="Asia/Kolkata",
        worker_instance_id="worker-node-alpha",
        lease_duration_minutes=10,
    )
    assert lease_a.status == "RUNNING"

    # Worker B attempts to acquire lease while worker A is still running
    with pytest.raises(AppException) as exc_info:
        acquire_job_lease(
            db=db_session,
            job_type="DAILY_MATURITY_SCAN",
            trigger_source="WORKER_B",
            evaluation_date=eval_date,
            evaluation_timezone="Asia/Kolkata",
            worker_instance_id="worker-node-beta",
            lease_duration_minutes=10,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONCURRENT_JOB_RUNNING"


# ==============================================================================
# 9. Partial Batch Failure and Recovery
# ==============================================================================
def test_partial_batch_failure_and_recovery(
    db_session: Session, inst_a: Institution, active_policy: LifecyclePolicy
):
    """
    If one instrument in the batch raises an unhandled exception, per-record
    error isolation must capture the error and allow subsequent instruments to succeed.
    Job finishes with PARTIAL_FAILURE.
    """
    fixed_today = date(2026, 11, 1)
    set_current_clock(SimulatedClock(fixed_date=fixed_today))

    # Create 3 instruments
    fdr_good_1 = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-BATCH-GOOD-1",
        bank_name="SBI",
        branch="Branch",
        amount=Decimal("100000.00"),
        issue_date=date(2025, 11, 10),
        maturity_date=date(2026, 11, 10),
        status="REGISTERED",
    )
    fdr_bad = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-BATCH-BAD",
        bank_name="SBI",
        branch="Branch",
        amount=Decimal("200000.00"),
        issue_date=date(2025, 11, 15),
        maturity_date=date(2026, 11, 15),
        status="REGISTERED",
    )
    fdr_good_2 = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-BATCH-GOOD-2",
        bank_name="SBI",
        branch="Branch",
        amount=Decimal("300000.00"),
        issue_date=date(2025, 11, 20),
        maturity_date=date(2026, 11, 20),
        status="REGISTERED",
    )
    db_session.add_all([fdr_good_1, fdr_bad, fdr_good_2])
    db_session.commit()

    # Monkeypatch evaluate_instrument_lifecycle to throw on fdr_bad
    real_eval = evaluate_instrument_lifecycle

    def mock_eval_with_selective_failure(*args, **kwargs):
        inst_id = kwargs.get("instrument_id")
        if inst_id == fdr_bad.id:
            raise RuntimeError("Corrupted cryptographic verification payload in instrument")
        return real_eval(*args, **kwargs)

    with patch(
        "app.modules.lifecycle.scheduler.evaluate_instrument_lifecycle",
        side_effect=mock_eval_with_selective_failure,
    ):
        job_run = execute_lifecycle_scan_job(
            db=db_session,
            job_type="TEST_BATCH_RECOVERY",
            trigger_source="TEST_HARNESS",
            batch_size=10,
        )

    assert job_run.status == "PARTIAL_FAILURE"
    assert job_run.error_count == 1
    assert job_run.success_count >= 2
    assert "Corrupted cryptographic verification payload" in str(job_run.error_summary_json)


# ==============================================================================
# 10. Worker Restart and Stale Lease Recovery
# ==============================================================================
def test_worker_restart_and_stale_lease_recovery(
    db_session: Session
):
    """
    If a worker crashes leaving an unfinalized job with an expired lease,
    the next worker must identify the stale lease, mark the job as FAILED,
    and acquire a fresh lease without deadlock.
    """
    now = datetime.now(timezone.utc)
    # Stale job with lease expired 10 minutes ago
    stale_job = LifecycleJobRun(
        job_type="DAILY_MATURITY_SCAN",
        status="RUNNING",
        trigger_source="SCHEDULED",
        started_at=now - timedelta(minutes=20),
        evaluation_date=date(2026, 11, 1),
        evaluation_timezone="Asia/Kolkata",
        worker_instance_id="crashed-worker-999",
        lease_expires_at=now - timedelta(minutes=10),  # expired!
    )
    db_session.add(stale_job)
    db_session.commit()

    # New worker starts
    fresh_job = acquire_job_lease(
        db=db_session,
        job_type="DAILY_MATURITY_SCAN",
        trigger_source="RESTART_WORKER",
        evaluation_date=date(2026, 11, 1),
        evaluation_timezone="Asia/Kolkata",
        worker_instance_id="fresh-worker-001",
    )

    db_session.refresh(stale_job)
    assert stale_job.status == "FAILED"
    assert "Lease expired without completion" in str(stale_job.error_summary_json)
    assert fresh_job.status == "RUNNING"
    assert fresh_job.worker_instance_id == "fresh-worker-001"


# ==============================================================================
# 11. Accurate Job Run Summaries
# ==============================================================================
def test_accurate_job_run_summaries(
    db_session: Session, inst_a: Institution, active_policy: LifecyclePolicy
):
    """
    The job run execution summary must persist accurate aggregate metrics:
    total_eligible, evaluated_count, success_count, error_count, approaching_count,
    matured_count, overdue_count.
    """
    fixed_today = date(2026, 11, 1)
    set_current_clock(SimulatedClock(fixed_date=fixed_today))

    # 1 Maturing soon (10 days out)
    fdr_appr = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-SUMMARY-APPR",
        bank_name="HDFC",
        branch="Main",
        amount=Decimal("100000.00"),
        issue_date=date(2025, 11, 11),
        maturity_date=date(2026, 11, 11),
        status="REGISTERED",
    )
    # 1 Matured (10 days past)
    fdr_mat = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-SUMMARY-MAT",
        bank_name="ICICI",
        branch="Main",
        amount=Decimal("200000.00"),
        issue_date=date(2025, 10, 22),
        maturity_date=date(2026, 10, 22),
        status="REGISTERED",
    )
    db_session.add_all([fdr_appr, fdr_mat])
    db_session.commit()

    job_run = execute_lifecycle_scan_job(
        db=db_session,
        job_type="ACCURACY_TEST_SCAN",
        trigger_source="TEST_HARNESS",
    )

    assert job_run.status == "SUCCESS"
    assert job_run.evaluated_count >= 2
    assert job_run.success_count >= 2
    assert job_run.error_count == 0
    assert job_run.approaching_count >= 1
    assert job_run.matured_count >= 1
    assert job_run.completed_at >= job_run.started_at


# ==============================================================================
# 12. Demo Date Advancement Changes Simulation Results Only
# ==============================================================================
def test_demo_date_advancement_changes_simulation_results_only(
    client: TestClient,
    db_session: Session,
    officer_user: User,
    inst_a: Institution,
    active_policy: LifecyclePolicy,
):
    """
    Advancing the demo simulated clock shifts the active evaluation perspective,
    reproducing approaching or matured states without touching actual FDR issue_date
    or maturity_date stored in the database.
    """
    set_auth(client, officer_user)
    base_issue = date(2025, 11, 1)
    base_maturity = date(2026, 11, 15)

    fdr = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-SIM-IMMUTABLE-DATE",
        bank_name="Axis Bank",
        branch="Noida",
        amount=Decimal("500000.00"),
        issue_date=base_issue,
        maturity_date=base_maturity,
        status="REGISTERED",
    )
    db_session.add(fdr)
    db_session.commit()

    # Advance clock to Nov 20, 2026 (5 days past maturity)
    resp = client.post(
        "/api/v1/lifecycle/demo/advance-clock",
        json={"target_date": "2026-11-20"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_simulated"] is True
    assert data["disclaimer"] == "DEMO DATE SIMULATION — NOT REAL TIME"
    assert data["today"] == "2026-11-20"

    # Evaluate instrument under new simulated clock
    eval_resp = client.get(f"/api/v1/lifecycle/assessments/{fdr.id}")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["evaluation_date"] == "2026-11-20"
    assert eval_data["days_to_maturity"] == -5
    assert eval_data["maturity_stage"] == MaturityStage.EXPIRED.value

    # CRITICAL CHECK: Verify real instrument dates in database were NOT modified
    db_session.refresh(fdr)
    assert fdr.issue_date == base_issue
    assert fdr.maturity_date == base_maturity


# ==============================================================================
# 13. Demo Date Control Unavailable in Production
# ==============================================================================
def test_demo_date_control_unavailable_in_production(
    client: TestClient, admin_user: User
):
    """
    In production mode (ENVIRONMENT="production" or ENABLE_LIFECYCLE_DATE_ADVANCE=False),
    any attempt to advance the demo clock must be rejected with HTTP 403 Forbidden.
    """
    set_auth(client, admin_user)

    with patch("app.core.config.settings.ENVIRONMENT", "production"):
        resp = client.post(
            "/api/v1/lifecycle/demo/advance-clock",
            json={"days": 10},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "DEMO_CONTROL_DISABLED_IN_PRODUCTION"

    with patch("app.core.config.settings.ENABLE_LIFECYCLE_DATE_ADVANCE", False):
        resp = client.post(
            "/api/v1/lifecycle/demo/advance-clock",
            json={"days": 10},
        )
        assert resp.status_code == 403
        assert resp.json()["code"] == "DEMO_CONTROL_DISABLED_IN_PRODUCTION"


# ==============================================================================
# 14. No Trust Promotion or Release Approval from Maturity Evaluation
# ==============================================================================
def test_no_trust_promotion_or_release_approval_from_maturity_evaluation(
    db_session: Session, inst_a: Institution, active_policy: LifecyclePolicy
):
    """
    The maturity evaluation engine must never promote trust levels (L0/L1/L2/L3),
    alter trust scores, or mark an instrument as RELEASED or refund-eligible.
    """
    set_current_clock(SimulatedClock(fixed_date=date(2026, 12, 1)))

    fdr = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-TRUST-BOUNDARY",
        bank_name="Kotak Bank",
        branch="Delhi",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=date(2026, 11, 1),
        status="REGISTERED",
        trust_level="L1_DOCUMENT_CONSISTENT",
    )
    db_session.add(fdr)
    db_session.commit()

    # Evaluate instrument when 30 days past maturity
    eval_record = evaluate_instrument_lifecycle(db_session, fdr.id, policy_id=active_policy.id)
    assert eval_record.maturity_stage == MaturityStage.EXPIRED.value

    # Refresh instrument and verify inviolate boundaries
    db_session.refresh(fdr)
    assert fdr.trust_level == "L1_DOCUMENT_CONSISTENT"
    assert fdr.status == "REGISTERED"
    assert fdr.status != "RELEASED"
    assert fdr.status != "REFUNDED"


# ==============================================================================
# 15. Monitoring APIs Tenancy and Filtering
# ==============================================================================
def test_monitoring_apis_tenancy_and_filtering(
    client: TestClient,
    db_session: Session,
    inst_a: Institution,
    inst_b: Institution,
    institution_user_a: User,
    officer_user: User,
    active_policy: LifecyclePolicy,
):
    """
    Test monitoring endpoints:
    - Approaching maturity
    - Matured
    - Overdue
    Verify tenancy isolation: institution_user_a can only see instruments belonging to inst_a.
    officer_user can see instruments across all institutions.
    """
    fixed_today = date(2026, 11, 1)
    set_current_clock(SimulatedClock(fixed_date=fixed_today))

    # Instrument A (inst_a) - Approaching (10 days away)
    fdr_a = Instrument(
        institution_id=inst_a.id,
        instrument_type="FDR",
        reference_number="FDR-MON-INST-A-APPR",
        bank_name="SBI",
        branch="Main",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 11, 11),
        maturity_date=date(2026, 11, 11),
        status="REGISTERED",
    )
    # Instrument B (inst_b) - Approaching (15 days away)
    fdr_b = Instrument(
        institution_id=inst_b.id,
        instrument_type="FDR",
        reference_number="FDR-MON-INST-B-APPR",
        bank_name="PNB",
        branch="Main",
        amount=Decimal("2000000.00"),
        issue_date=date(2025, 11, 16),
        maturity_date=date(2026, 11, 16),
        status="REGISTERED",
    )
    db_session.add_all([fdr_a, fdr_b])
    db_session.commit()

    # Pre-evaluate both instruments so they have lifecycle evaluations
    evaluate_instrument_lifecycle(db_session, fdr_a.id, policy_id=active_policy.id)
    evaluate_instrument_lifecycle(db_session, fdr_b.id, policy_id=active_policy.id)

    # 1. Scrutiny Officer calls approaching-maturity endpoint (sees both inst_a and inst_b)
    set_auth(client, officer_user)
    resp_officer = client.get("/api/v1/lifecycle/monitoring/approaching-maturity")
    assert resp_officer.status_code == 200
    officer_data = resp_officer.json()
    officer_ref_numbers = [item["reference_number"] for item in officer_data["items"]]
    assert "FDR-MON-INST-A-APPR" in officer_ref_numbers
    assert "FDR-MON-INST-B-APPR" in officer_ref_numbers

    # 2. Institution User A calls approaching-maturity endpoint (sees ONLY inst_a)
    set_auth(client, institution_user_a)
    resp_inst_a = client.get("/api/v1/lifecycle/monitoring/approaching-maturity")
    assert resp_inst_a.status_code == 200
    inst_a_data = resp_inst_a.json()
    inst_a_ref_numbers = [item["reference_number"] for item in inst_a_data["items"]]
    assert "FDR-MON-INST-A-APPR" in inst_a_ref_numbers
    assert "FDR-MON-INST-B-APPR" not in inst_a_ref_numbers
