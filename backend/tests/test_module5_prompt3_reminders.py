"""
Module 5 — Prompt 3: Policy-Driven Reminders, Delivery History, Escalation and Failure Recovery
Acceptance Test Suite

Covers all 15 required specifications:
1. Reminders generated at configured milestones.
2. Unconfigured policy does not produce invented intervals.
3. Correct institution recipient resolution.
4. Role-based escalation.
5. Idempotency under rerun/restart.
6. Concurrent dispatch protection.
7. Failed provider retry.
8. Permanent failure and retry exhaustion.
9. Accurate notification history.
10. No false delivered state.
11. Missing-recipient handling.
12. Resolved actions stop escalating appropriately.
13. Cross-tenant notification privacy.
14. Demo/mock labels.
15. No trust/release changes as a reminder side effect.
"""
from typing import Generator, List, Optional
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
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
    LifecycleEvaluation,
    LifecycleNotification,
    NotificationDeliveryAttempt,
)
from app.modules.lifecycle.enums import (
    PolicyStatus,
    MaturityStage,
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
from app.modules.lifecycle.evaluation_service import evaluate_instrument_lifecycle
from app.modules.lifecycle.notification_service import (
    generate_and_dispatch_reminders_for_instrument,
    retry_notification,
    mark_notification_as_read,
    build_idempotency_key,
    resolve_recipients_for_role,
)
from app.modules.lifecycle.schemas import LifecyclePolicyCreate
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
    """Ensure clock state is reset to system clock after each test."""
    yield
    reset_to_system_clock()


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        email="admin.notif@aicte-india.org",
        full_name="Notification Admin",
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
        email="officer.notif@aicte-india.org",
        full_name="Scrutiny Officer Sharma",
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
        email="branchhead.notif@aicte-india.org",
        full_name="Regional Director North",
        role="BRANCH_HEAD",
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_institution(db_session: Session) -> Institution:
    inst = Institution(
        legal_name="Delhi Technological University - Testing College",
        code="DTU-NOTIF-001",
        contact_email="principal@dtu.ac.in",
        state="Delhi",
        institution_type="GOVERNMENT",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def college_b_institution(db_session: Session) -> Institution:
    inst = Institution(
        legal_name="Mumbai Institute of Tech - College B",
        code="MIT-NOTIF-002",
        contact_email="principal@mit-b.ac.in",
        state="Maharashtra",
        institution_type="PRIVATE",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def inst_user(db_session: Session, test_institution: Institution) -> User:
    user = User(
        email="principal@dtu.ac.in",
        full_name="Principal DTU",
        role=ROLE_INSTITUTION_USER,
        institution_id=test_institution.id,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def college_b_user(db_session: Session, college_b_institution: Institution) -> User:
    user = User(
        email="principal@mit-b.ac.in",
        full_name="Principal MIT-B",
        role=ROLE_INSTITUTION_USER,
        institution_id=college_b_institution.id,
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def demo_policy(db_session: Session, admin_user: User) -> LifecyclePolicy:
    """Ensure active demo policy with milestones [30, 15] and permitted channels."""
    policy = get_or_create_default_demo_policy(db_session)
    policy.reminder_milestones_days = [30, 15]
    policy.recipient_roles_by_interval = {
        "30": ["INSTITUTION_USER"],
        "15": ["INSTITUTION_USER"],
    }
    policy.permitted_channels = ["IN_APP", "EMAIL"]
    policy.max_retry_limit = 3
    policy.escalation_delay_days = 7
    policy.escalation_destination_role = "BRANCH_HEAD"
    db_session.commit()
    db_session.refresh(policy)
    return policy


# ---------------------------------------------------------------------------
# TEST 1: Reminders generated at configured milestones
# ---------------------------------------------------------------------------
def test_01_reminders_generated_at_configured_milestones(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    test_institution: Institution,
    inst_user: User,
):
    fixed_today = date(2026, 11, 1)
    # 30 days to maturity -> maturity on 2026-12-01
    maturity_d = fixed_today + timedelta(days=30)
    instrument = Instrument(
        institution_id=test_institution.id,
        bank_name="State Bank of India",
        branch="Main Branch",
        reference_number="FDR-REM-001",
        amount=Decimal("500000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    dispatched = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )

    # With channels IN_APP and EMAIL permitted, both should be dispatched for milestone 30
    assert len(dispatched) >= 2
    milestone_notifs = [n for n in dispatched if n.event_type == "MATURITY_MILESTONE_REMINDER"]
    assert len(milestone_notifs) >= 2
    channels = {n.channel for n in milestone_notifs}
    assert "IN_APP" in channels
    assert "EMAIL" in channels

    for n in milestone_notifs:
        assert n.milestone_days == 30
        assert n.event_type == "MATURITY_MILESTONE_REMINDER"
        assert n.instrument_id == instrument.id
        assert n.recipient_role == "INSTITUTION_USER"


# ---------------------------------------------------------------------------
# TEST 2: Unconfigured policy does not produce invented intervals
# ---------------------------------------------------------------------------
def test_02_unconfigured_policy_does_not_produce_invented_intervals(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    test_institution: Institution,
    inst_user: User,
):
    # Set milestone intervals explicitly empty
    demo_policy.reminder_milestones_days = []
    db_session.commit()

    fixed_today = date(2026, 11, 1)
    maturity_d = fixed_today + timedelta(days=22)  # Arbitrary 22 days
    instrument = Instrument(
        institution_id=test_institution.id,
        bank_name="HDFC Bank",
        branch="Civil Lines",
        reference_number="FDR-REM-UNCONF-002",
        amount=Decimal("750000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    dispatched = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )

    # No maturity milestone reminders should be invented
    milestone_notifs = [n for n in dispatched if n.event_type == "MATURITY_MILESTONE_REMINDER"]
    assert len(milestone_notifs) == 0


# ---------------------------------------------------------------------------
# TEST 3: Correct institution recipient resolution
# ---------------------------------------------------------------------------
def test_03_correct_institution_recipient_resolution(
    db_session: Session,
    test_institution: Institution,
    inst_user: User,
    college_b_institution: Institution,
    college_b_user: User,
):
    # Recipient for test_institution MUST resolve to inst_user, not college_b_user
    recipients = resolve_recipients_for_role(
        db=db_session,
        role="INSTITUTION_USER",
        institution_id=test_institution.id,
    )
    assert len(recipients) == 1
    assert recipients[0].id == inst_user.id
    assert recipients[0].institution_id == test_institution.id
    assert recipients[0].id != college_b_user.id


# ---------------------------------------------------------------------------
# TEST 4: Role-based escalation
# ---------------------------------------------------------------------------
def test_04_role_based_escalation(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    test_institution: Institution,
    inst_user: User,
    branch_head_user: User,
):
    demo_policy.escalation_delay_days = 5
    demo_policy.escalation_destination_role = "BRANCH_HEAD"
    db_session.commit()

    fixed_today = date(2026, 11, 1)
    # Maturity was 30 days ago, overdue by > 5 days
    past_maturity = fixed_today - timedelta(days=20)
    instrument = Instrument(
        institution_id=test_institution.id,
        bank_name="Canara Bank",
        branch="Connaught Place",
        reference_number="FDR-REM-ESC-004",
        amount=Decimal("1000000.00"),
        issue_date=date(2024, 11, 1),
        maturity_date=past_maturity,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    dispatched = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )

    escalations = [n for n in dispatched if n.event_type == "ACTION_ESCALATED"]
    assert len(escalations) > 0
    for esc in escalations:
        assert esc.recipient_role == "BRANCH_HEAD"
        assert esc.recipient_user_id == branch_head_user.id


# ---------------------------------------------------------------------------
# TEST 5: Idempotency under rerun/restart
# ---------------------------------------------------------------------------
def test_05_idempotency_under_rerun_and_restart(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    test_institution: Institution,
    inst_user: User,
):
    fixed_today = date(2026, 11, 1)
    maturity_d = fixed_today + timedelta(days=30)
    instrument = Instrument(
        institution_id=test_institution.id,
        bank_name="Punjab National Bank",
        branch="Karol Bagh",
        reference_number="FDR-REM-IDEM-005",
        amount=Decimal("800000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    # First dispatch run
    first_run = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )
    first_count = len(first_run)
    assert first_count > 0

    # Second immediate run (simulate worker restart or rerun)
    second_run = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )

    # Identical notifications returned with zero duplicates created
    assert {n.id for n in second_run} == {n.id for n in first_run}

    # Total in DB must remain identical
    total_db_count = db_session.scalar(
        select(func.count(LifecycleNotification.id)).where(
            LifecycleNotification.instrument_id == instrument.id
        )
    )
    assert total_db_count == first_count


# ---------------------------------------------------------------------------
# TEST 6: Concurrent dispatch protection
# ---------------------------------------------------------------------------
def test_06_concurrent_dispatch_protection(
    db_session: Session,
    test_institution: Institution,
    inst_user: User,
):
    fixed_today = date(2026, 11, 1)
    key = build_idempotency_key(
        instrument_id="inst-concurrent-test",
        event_type="MATURITY_MILESTONE_REMINDER",
        milestone_days=30,
        trigger_date=fixed_today,
        recipient_id_or_role=inst_user.id,
        channel="IN_APP",
    )

    # First insertion
    notif1 = LifecycleNotification(
        idempotency_key=key,
        instrument_id="inst-concurrent-test",
        institution_id=test_institution.id,
        event_type="MATURITY_MILESTONE_REMINDER",
        milestone_days=30,
        trigger_date=fixed_today,
        recipient_role="INSTITUTION_USER",
        recipient_user_id=inst_user.id,
        channel="IN_APP",
        status="DELIVERED",
        rendered_title="Test Title 1",
        rendered_message="Test Message 1",
    )
    db_session.add(notif1)
    db_session.commit()

    # Second concurrent insertion with identical idempotency_key must raise IntegrityError
    notif2 = LifecycleNotification(
        idempotency_key=key,
        instrument_id="inst-concurrent-test",
        institution_id=test_institution.id,
        event_type="MATURITY_MILESTONE_REMINDER",
        milestone_days=30,
        trigger_date=fixed_today,
        recipient_role="INSTITUTION_USER",
        recipient_user_id=inst_user.id,
        channel="IN_APP",
        status="DELIVERED",
        rendered_title="Test Title 2",
        rendered_message="Test Message 2",
    )
    db_session.add(notif2)
    with pytest.raises(Exception):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# TEST 7: Failed provider retry
# ---------------------------------------------------------------------------
def test_07_failed_provider_retry(
    db_session: Session,
    test_institution: Institution,
    inst_user: User,
    admin_user: User,
):
    fixed_today = date(2026, 11, 1)
    notif = LifecycleNotification(
        idempotency_key=f"failed-retry-test-{fixed_today}",
        instrument_id="inst-failed-retry",
        institution_id=test_institution.id,
        event_type="MATURITY_MILESTONE_REMINDER",
        trigger_date=fixed_today,
        recipient_role="INSTITUTION_USER",
        recipient_user_id=inst_user.id,
        recipient_email=inst_user.email,
        channel="EMAIL",
        status="FAILED",
        rendered_title="Failed Delivery Notice",
        rendered_message="Initial dispatch failure",
        retry_count=1,
        max_retries=3,
        failure_category="PROVIDER_UNAVAILABLE",
        failure_details="Connection refused by remote mail server",
    )
    db_session.add(notif)
    db_session.commit()

    # Administrative retry
    retried = retry_notification(
        db=db_session,
        notification_id=notif.id,
        actor_user_id=admin_user.id,
        actor_email=admin_user.email,
        reason="Manual admin retry after network recovery",
    )

    assert retried.retry_count == 2
    assert retried.status in ("ACCEPTED", "MOCKED")  # Email provider accepts or mocks
    assert len(retried.attempts) >= 1


# ---------------------------------------------------------------------------
# TEST 8: Permanent failure and retry exhaustion
# ---------------------------------------------------------------------------
def test_08_permanent_failure_and_retry_exhaustion(
    db_session: Session,
    test_institution: Institution,
    inst_user: User,
    admin_user: User,
):
    fixed_today = date(2026, 11, 1)
    notif = LifecycleNotification(
        idempotency_key=f"exhausted-retry-test-{fixed_today}",
        instrument_id="inst-exhausted-retry",
        institution_id=test_institution.id,
        event_type="MATURITY_MILESTONE_REMINDER",
        trigger_date=fixed_today,
        recipient_role="INSTITUTION_USER",
        recipient_user_id=inst_user.id,
        channel="EMAIL",
        status="FAILED",
        rendered_title="Exhausted Delivery Notice",
        rendered_message="Retries maxed out",
        retry_count=3,
        max_retries=3,  # Already at limit
        failure_category="RETRY_EXHAUSTED",
        failure_details="Max attempts reached",
    )
    db_session.add(notif)
    db_session.commit()

    with pytest.raises(AppException) as exc_info:
        retry_notification(
            db=db_session,
            notification_id=notif.id,
            actor_user_id=admin_user.id,
            actor_email=admin_user.email,
        )
    assert exc_info.value.code == "RETRY_EXHAUSTED"


# ---------------------------------------------------------------------------
# TEST 9: Accurate notification history
# ---------------------------------------------------------------------------
def test_09_accurate_notification_history(
    db_session: Session,
    test_institution: Institution,
    inst_user: User,
):
    fixed_today = date(2026, 11, 1)
    notif = LifecycleNotification(
        idempotency_key=f"history-accuracy-test-{fixed_today}",
        instrument_id="inst-history-acc",
        institution_id=test_institution.id,
        event_type="MATURITY_MILESTONE_REMINDER",
        trigger_date=fixed_today,
        recipient_role="INSTITUTION_USER",
        recipient_user_id=inst_user.id,
        channel="EMAIL",
        status="ACCEPTED",
        rendered_title="Deposit Notice",
        rendered_message="Deposit Notice Body",
        retry_count=1,
        max_retries=3,
    )
    db_session.add(notif)
    db_session.flush()

    attempt1 = NotificationDeliveryAttempt(
        notification_id=notif.id,
        attempt_number=1,
        attempted_at=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        channel="EMAIL",
        status="FAILED",
        provider_name="SMTP_TLS",
        failure_category="PROVIDER_UNAVAILABLE",
        failure_details="Connection timed out",
        is_mock=False,
    )
    attempt2 = NotificationDeliveryAttempt(
        notification_id=notif.id,
        attempt_number=2,
        attempted_at=datetime(2026, 11, 1, 10, 15, tzinfo=timezone.utc),
        channel="EMAIL",
        status="ACCEPTED",
        provider_name="SMTP_TLS",
        provider_reference="msg-uuid-998877",
        is_mock=False,
    )
    db_session.add_all([attempt1, attempt2])
    db_session.commit()
    db_session.refresh(notif)

    assert len(notif.attempts) == 2
    assert notif.attempts[0].attempt_number == 1
    assert notif.attempts[0].status == "FAILED"
    assert notif.attempts[0].failure_category == "PROVIDER_UNAVAILABLE"
    assert notif.attempts[1].attempt_number == 2
    assert notif.attempts[1].status == "ACCEPTED"
    assert notif.attempts[1].provider_reference == "msg-uuid-998877"


# ---------------------------------------------------------------------------
# TEST 10: No false delivered state
# ---------------------------------------------------------------------------
def test_10_no_false_delivered_state(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    test_institution: Institution,
    inst_user: User,
):
    fixed_today = date(2026, 11, 1)
    maturity_d = fixed_today + timedelta(days=30)
    instrument = Instrument(
        institution_id=test_institution.id,
        bank_name="Axis Bank",
        branch="Rohini",
        reference_number="FDR-REM-HONEST-010",
        amount=Decimal("500000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    dispatched = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )

    for notif in dispatched:
        if notif.channel == "EMAIL":
            # Must NEVER claim DELIVERED without delivery receipt webhook
            assert notif.status in ("ACCEPTED", "MOCKED")
            assert notif.status != "DELIVERED"
        elif notif.channel == "IN_APP":
            # In-App is immediately DELIVERED into database inbox
            assert notif.status == "DELIVERED"


# ---------------------------------------------------------------------------
# TEST 11: Missing-recipient handling
# ---------------------------------------------------------------------------
def test_11_missing_recipient_handling(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    admin_user: User,
):
    # Create institution with ZERO users
    empty_inst = Institution(
        legal_name="Empty Orphan College",
        code="EMPTY-COLLEGE-011",
        contact_email="orphan@college.edu",
        state="Haryana",
        institution_type="PRIVATE",
        is_active=True,
    )
    db_session.add(empty_inst)
    db_session.commit()

    fixed_today = date(2026, 11, 1)
    maturity_d = fixed_today + timedelta(days=30)
    instrument = Instrument(
        institution_id=empty_inst.id,
        bank_name="Bank of Baroda",
        branch="Gurugram",
        reference_number="FDR-REM-NOUSER-011",
        amount=Decimal("400000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    dispatched = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )

    # Should record a FAILED notification with CONFIGURATION_ERROR
    assert len(dispatched) > 0
    failed_notifs = [n for n in dispatched if n.status == "FAILED"]
    assert len(failed_notifs) > 0
    for fn in failed_notifs:
        assert fn.failure_category == "CONFIGURATION_ERROR"
        # Must NOT route to an arbitrary admin
        assert fn.recipient_user_id is None


# ---------------------------------------------------------------------------
# TEST 12: Resolved actions stop escalating appropriately
# ---------------------------------------------------------------------------
def test_12_resolved_actions_stop_escalating_appropriately(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    test_institution: Institution,
    inst_user: User,
    branch_head_user: User,
):
    fixed_today = date(2026, 11, 1)
    # Instrument marked RENEWED / CLOSED (not eligible for lifecycle monitoring)
    instrument = Instrument(
        institution_id=test_institution.id,
        bank_name="Union Bank of India",
        branch="Delhi",
        reference_number="FDR-REM-RESOLVED-012",
        amount=Decimal("600000.00"),
        issue_date=date(2024, 11, 1),
        maturity_date=fixed_today - timedelta(days=50),
        status="CLOSED",  # Resolved/Closed
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    dispatched = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )

    # Ineligible closed instrument should produce 0 notifications and 0 escalations
    assert len(dispatched) == 0


# ---------------------------------------------------------------------------
# TEST 13: Cross-tenant notification privacy
# ---------------------------------------------------------------------------
def test_13_cross_tenant_notification_privacy(
    client: TestClient,
    db_session: Session,
    test_institution: Institution,
    college_b_institution: Institution,
    inst_user: User,
    college_b_user: User,
):
    # Create an actual instrument for College B
    inst_b = Instrument(
        institution_id=college_b_institution.id,
        bank_name="HDFC Bank",
        branch="Nariman Point",
        reference_number="FDR-COLLEGE-B-001",
        amount=Decimal("500000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=date(2026, 12, 1),
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(inst_b)
    db_session.flush()

    # Create notification belonging to College B
    notif_b = LifecycleNotification(
        idempotency_key="privacy-test-key-b",
        instrument_id=inst_b.id,
        institution_id=college_b_institution.id,
        event_type="MATURITY_MILESTONE_REMINDER",
        trigger_date=date(2026, 11, 1),
        recipient_role="INSTITUTION_USER",
        recipient_user_id=college_b_user.id,
        channel="IN_APP",
        status="DELIVERED",
        rendered_title="Private Notice College B",
        rendered_message="Secret institutional communication",
    )
    db_session.add(notif_b)
    db_session.commit()

    # Log in as inst_user from College A
    set_auth(client, inst_user)

    # 1. Accessing College B's instrument notifications must return 403 Forbidden
    resp = client.get(f"/api/v1/lifecycle/instruments/{inst_b.id}/notifications")
    assert resp.status_code == 403

    # 2. Accessing own inbox must NOT reveal College B's notification
    inbox_resp = client.get("/api/v1/lifecycle/notifications/inbox")
    assert inbox_resp.status_code == 200
    inbox_data = inbox_resp.json()
    b_ids = [n["id"] for n in inbox_data["items"] if n["id"] == notif_b.id]
    assert len(b_ids) == 0


# ---------------------------------------------------------------------------
# TEST 14: Demo and mock labels
# ---------------------------------------------------------------------------
def test_14_demo_and_mock_labels(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    test_institution: Institution,
    inst_user: User,
):
    fixed_today = date(2026, 11, 1)
    maturity_d = fixed_today + timedelta(days=30)
    instrument = Instrument(
        institution_id=test_institution.id,
        bank_name="Kotak Mahindra Bank",
        branch="Vasant Kunj",
        reference_number="FDR-REM-MOCK-014",
        amount=Decimal("500000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    # With SMTP unconfigured in dev/test, Email provider operates in local catcher/mock mode
    dispatched = generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )

    email_notifs = [n for n in dispatched if n.channel == "EMAIL"]
    assert len(email_notifs) > 0
    email_notif = email_notifs[0]
    if email_notif.is_mock:
        assert email_notif.status in ("MOCKED", "ACCEPTED")
        assert (
            "LOCAL_MAIL_CATCHER" in (email_notif.mock_disclaimer or "")
            or "MOCKED" in (email_notif.mock_disclaimer or "")
        )


# ---------------------------------------------------------------------------
# TEST 15: No trust or release changes as a reminder side effect
# ---------------------------------------------------------------------------
def test_15_no_trust_or_release_changes_as_reminder_side_effect(
    db_session: Session,
    demo_policy: LifecyclePolicy,
    test_institution: Institution,
    inst_user: User,
    admin_user: User,
):
    fixed_today = date(2026, 11, 1)
    maturity_d = fixed_today + timedelta(days=30)
    instrument = Instrument(
        institution_id=test_institution.id,
        bank_name="ICICI Bank",
        branch="Saket",
        reference_number="FDR-REM-NOTRUST-015",
        amount=Decimal("500000.00"),
        issue_date=date(2025, 11, 1),
        maturity_date=maturity_d,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()

    initial_trust = instrument.trust_level
    initial_status = instrument.status

    # 1. Dispatch milestone reminders
    generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )
    db_session.refresh(instrument)
    assert instrument.trust_level == initial_trust
    assert instrument.status == initial_status

    # 2. Trigger escalation
    instrument.maturity_date = fixed_today - timedelta(days=30)
    db_session.commit()

    generate_and_dispatch_reminders_for_instrument(
        db=db_session,
        instrument_id=instrument.id,
        simulated_date=fixed_today,
    )
    db_session.refresh(instrument)

    # Trust level and status must remain completely unaltered!
    assert instrument.trust_level == initial_trust
    assert instrument.status == initial_status
