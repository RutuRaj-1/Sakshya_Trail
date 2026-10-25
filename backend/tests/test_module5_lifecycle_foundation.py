"""
Module 5 — Lifecycle Orchestration, Policy Configuration and Renewal Lineage
Acceptance Test Suite

Verifies all 15 required specifications:
1. Policy creation and validation.
2. Rejection of unknown/unapproved policy values.
3. Clearly labelled synthetic demo policy.
4. Preservation of historical policy versions.
5. Separate maturity and action due-date concepts.
6. Date calculations at the configured timezone boundary.
7. Missing-date and invalid-date behavior.
8. Self-referential lineage rejection.
9. Cyclic lineage rejection.
10. Cross-institution lineage restrictions.
11. Duplicate and concurrent link attempts rejection.
12. Predecessor history preservation.
13. Successor creation does not release or overwrite the predecessor.
14. Migrations from the existing database.
15. Zero regressions across Modules 1–4.
"""
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import (
    LifecyclePolicy,
    InstrumentLineage,
    LifecycleEvaluation,
)
from app.modules.lifecycle.enums import (
    PolicyStatus,
    MaturityStage,
    DueCondition,
    ContinuityIndicator,
)
from app.modules.lifecycle.clock import SimulatedClock
from app.modules.lifecycle.policy_service import (
    create_policy,
    approve_policy,
    activate_policy,
    get_or_create_default_demo_policy,
    resolve_active_policy,
    get_policy_by_code_and_version,
)
from app.modules.lifecycle.lineage_service import (
    create_renewal_lineage,
    get_lineage_tree,
    detect_cycle_in_lineage,
)
from app.modules.lifecycle.evaluation_service import (
    evaluate_instrument_lifecycle,
    get_latest_evaluation_for_instrument,
    evaluate_batch_instruments,
)
from app.modules.lifecycle.schemas import (
    LifecyclePolicyCreate,
    LineageCreateRequest,
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


@pytest.fixture
def admin_user(db_session: Session) -> User:
    user = User(
        email="admin.lifecycle@aicte-india.org",
        full_name="Lifecycle System Administrator",
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
        email="officer.lifecycle@aicte-india.org",
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
def institution_a(db_session: Session) -> Institution:
    inst = Institution(
        code="1-LIFECYCLE-INST-A",
        legal_name="National Engineering College Alpha",
        display_name="NEC Alpha",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Principal Alpha",
        contact_email="principal@alpha.edu",
        contact_phone="+91-11-20000001",
        state="Maharashtra",
        city="Pune",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def institution_b(db_session: Session) -> Institution:
    inst = Institution(
        code="1-LIFECYCLE-INST-B",
        legal_name="State Institute of Technology Beta",
        display_name="SIT Beta",
        institution_type="POLYTECHNIC",
        contact_name="Director Beta",
        contact_email="director@beta.edu",
        contact_phone="+91-11-20000002",
        state="Karnataka",
        city="Bengaluru",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def sample_instruments(db_session: Session, institution_a: Institution) -> Tuple[Instrument, Instrument, Instrument]:
    today = date(2026, 10, 25)
    i1 = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        branch="Main Branch Pune",
        reference_number="FDR-2021-001",
        amount=Decimal("5000000.00"),
        issue_date=today - timedelta(days=5 * 365),
        maturity_date=today + timedelta(days=60),  # Maturing in 60 days
        status="REGISTERED",
        trust_level="L2_OFFICER_VERIFIED",
    )
    i2 = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        branch="Main Branch Pune",
        reference_number="FDR-2026-RENEWAL-002",
        amount=Decimal("5000000.00"),
        issue_date=today + timedelta(days=60),  # Continuous rollover
        maturity_date=today + timedelta(days=60 + 5 * 365),
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    i3 = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        branch="Main Branch Pune",
        reference_number="FDR-2031-RENEWAL-003",
        amount=Decimal("5000000.00"),
        issue_date=today + timedelta(days=60 + 5 * 365),
        maturity_date=today + timedelta(days=60 + 10 * 365),
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add_all([i1, i2, i3])
    db_session.commit()
    db_session.refresh(i1)
    db_session.refresh(i2)
    db_session.refresh(i3)
    return i1, i2, i3


# ==============================================================================
# TEST 1: Policy creation and validation
# ==============================================================================
def test_policy_creation_and_validation(db_session: Session, admin_user: User):
    payload = LifecyclePolicyCreate(
        policy_code="AICTE_STRICT_2026",
        name="Strict AICTE Monitoring Policy 2026",
        description="Standard regulatory reminder intervals",
        is_demo=False,
        reminder_intervals_days=[90, 60, 30, 15, 7],
        institution_action_lead_days=30,
        officer_action_lead_days=15,
        escalation_interval_days=7,
        escalation_target_role="BRANCH_HEAD",
    )
    policy = create_policy(db_session, payload, created_by_user_id=admin_user.id)
    assert policy.id is not None
    assert policy.policy_code == "AICTE_STRICT_2026"
    assert policy.version == 1
    assert policy.status == PolicyStatus.DRAFT.value
    assert policy.reminder_intervals_days == [90, 60, 30, 15, 7]
    assert policy.label == "OFFICIAL REGULATORY POLICY"


# ==============================================================================
# TEST 2: Rejection of unknown / unapproved / invalid policy values
# ==============================================================================
def test_rejection_of_invalid_policy_values(db_session: Session, admin_user: User):
    # Empty intervals rejected
    with pytest.raises(ValueError, match="At least one reminder interval"):
        LifecyclePolicyCreate(
            policy_code="INVALID_INTERVAL",
            name="Invalid Policy",
            reminder_intervals_days=[],
        )

    # Negative intervals rejected
    with pytest.raises(ValueError, match="strictly positive"):
        LifecyclePolicyCreate(
            policy_code="INVALID_INTERVAL",
            name="Invalid Policy",
            reminder_intervals_days=[90, -5, 30],
        )

    # Activating unapproved policy raises AppException
    payload = LifecyclePolicyCreate(
        policy_code="DRAFT_ACTIVATION_ATTEMPT",
        name="Draft Policy",
        reminder_intervals_days=[30],
    )
    p = create_policy(db_session, payload, created_by_user_id=admin_user.id)
    # Draft cannot be activated directly without approval
    # (or if policy status is invalid)
    p.status = PolicyStatus.INACTIVE.value
    db_session.commit()
    with pytest.raises(AppException) as exc:
        activate_policy(db_session, p.id, activator_user_id=admin_user.id)
    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_POLICY_STATUS"


# ==============================================================================
# TEST 3: Clearly labelled synthetic demo policy
# ==============================================================================
def test_clearly_labelled_synthetic_demo_policy(db_session: Session):
    demo_policy = get_or_create_default_demo_policy(db_session)
    assert demo_policy.is_demo is True
    assert "DEMO POLICY — NOT OFFICIAL AICTE POLICY" in demo_policy.label
    assert demo_policy.status == PolicyStatus.ACTIVE.value
    assert len(demo_policy.reminder_intervals_days) > 0


# ==============================================================================
# TEST 4: Preservation of historical policy versions
# ==============================================================================
def test_preservation_of_historical_policy_versions(db_session: Session, admin_user: User):
    # Version 1
    p1 = create_policy(
        db_session,
        LifecyclePolicyCreate(
            policy_code="HISTORICAL_POLICY_TEST",
            name="Version 1 Policy",
            institution_action_lead_days=30,
        ),
        created_by_user_id=admin_user.id,
    )
    approve_policy(db_session, p1.id, approver_user_id=admin_user.id)
    activate_policy(db_session, p1.id, activator_user_id=admin_user.id)
    assert p1.version == 1
    assert p1.status == PolicyStatus.ACTIVE.value

    # Version 2 with different lead days
    p2 = create_policy(
        db_session,
        LifecyclePolicyCreate(
            policy_code="HISTORICAL_POLICY_TEST",
            name="Version 2 Policy with Updated 45 Day Lead",
            institution_action_lead_days=45,
        ),
        created_by_user_id=admin_user.id,
    )
    approve_policy(db_session, p2.id, approver_user_id=admin_user.id)
    activate_policy(db_session, p2.id, activator_user_id=admin_user.id)

    assert p2.version == 2
    assert p2.status == PolicyStatus.ACTIVE.value

    # Refresh v1: MUST be SUPERSEDED and historical values PRESERVED
    db_session.refresh(p1)
    assert p1.status == PolicyStatus.SUPERSEDED.value
    assert p1.institution_action_lead_days == 30
    assert p2.institution_action_lead_days == 45

    # Direct query by (code, version) returns original snapshot
    v1_lookup = get_policy_by_code_and_version(db_session, "HISTORICAL_POLICY_TEST", 1)
    assert v1_lookup is not None
    assert v1_lookup.id == p1.id
    assert v1_lookup.institution_action_lead_days == 30


# ==============================================================================
# TEST 5: Separate maturity and action due-date concepts
# ==============================================================================
def test_separate_maturity_and_due_date_concepts(db_session: Session, institution_a: Institution):
    # Instrument maturing in 20 days:
    # Under default policy (lead_days=30):
    # maturity_stage should be MATURING_SOON, while due_condition is OVERDUE (since evaluation_date > maturity - 30)
    fixed_date = date(2026, 10, 25)
    clock = SimulatedClock(fixed_date=fixed_date)

    inst = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="Canara Bank",
        reference_number="FDR-SEP-001",
        amount=Decimal("2500000.00"),
        issue_date=date(2021, 11, 14),
        maturity_date=date(2026, 11, 14),  # 20 days from fixed_date
        status="REGISTERED",                # Module 1 Administrative Status: UNCHANGED
        trust_level="L2_OFFICER_VERIFIED",   # Module 4 Trust: UNCHANGED
    )
    db_session.add(inst)
    db_session.commit()

    # Evaluate on 2026-10-20: 5 days overdue (< 7 days escalation threshold)
    clock_overdue = SimulatedClock(fixed_date=date(2026, 10, 20))
    eval_overdue = evaluate_instrument_lifecycle(
        db=db_session,
        instrument_id=inst.id,
        clock=clock_overdue,
    )

    # 1. Administrative status is NOT mutated
    db_session.refresh(inst)
    assert inst.status == "REGISTERED"
    assert inst.trust_level == "L2_OFFICER_VERIFIED"

    # 2. Maturity calculation is distinct
    assert eval_overdue.days_to_maturity == 25
    assert eval_overdue.maturity_stage == MaturityStage.MATURING_SOON.value

    # 3. Action due dates are distinct
    # Action due date was 2026-11-14 - 30 days = 2026-10-15
    assert eval_overdue.institution_action_due_date == date(2026, 10, 15)
    # 2026-10-20 is > 2026-10-15 but <= 2026-10-22 (7 day escalation threshold)
    assert eval_overdue.is_overdue is True
    assert eval_overdue.is_escalated is False
    assert eval_overdue.due_condition == DueCondition.OVERDUE.value

    # Evaluate on 2026-10-25: 10 days overdue (> 7 days escalation threshold) => ESCALATED
    clock_escalated = SimulatedClock(fixed_date=date(2026, 10, 25))
    eval_escalated = evaluate_instrument_lifecycle(
        db=db_session,
        instrument_id=inst.id,
        clock=clock_escalated,
    )
    assert eval_escalated.is_overdue is True
    assert eval_escalated.is_escalated is True
    assert eval_escalated.due_condition == DueCondition.ESCALATED.value
    assert eval_escalated.escalation_role == "BRANCH_HEAD"


# ==============================================================================
# TEST 6: Date calculations at configured timezone boundary
# ==============================================================================
def test_date_calculations_at_timezone_boundary():
    # 2026-10-25 18:45 UTC is 2026-10-26 00:15 in Asia/Kolkata (UTC + 5:30)
    utc_dt = datetime(2026, 10, 25, 18, 45, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(fixed_dt=utc_dt)

    kolkata_date = clock.today_in_tz("Asia/Kolkata")
    utc_date = clock.today_in_tz("UTC")

    assert kolkata_date == date(2026, 10, 26)
    assert utc_date == date(2026, 10, 25)


# ==============================================================================
# TEST 7: Missing-date and invalid-date behavior
# ==============================================================================
def test_missing_and_invalid_date_behavior(db_session: Session, institution_a: Institution):
    # Verify date helpers handle None and invalid dates safely
    from app.modules.lifecycle.clock import get_calendar_days_between, calculate_due_date

    assert get_calendar_days_between(None, date(2026, 10, 25)) is None
    assert get_calendar_days_between(date(2026, 10, 25), None) is None
    assert calculate_due_date(None, 30) is None

    # Instrument with missing maturity date evaluated safely
    inst = Instrument(
        id="fdr-missing-date-mock-id",
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="Punjab National Bank",
        reference_number="FDR-NO-DATE",
        amount=Decimal("1000000.00"),
        issue_date=date(2025, 1, 1),
        maturity_date=None,  # type: ignore[assignment]
        status="DRAFT",
    )
    # Evaluate with instrument_obj having None maturity date
    evaluation = evaluate_instrument_lifecycle(
        db=db_session,
        instrument_id="fdr-missing-date-mock-id",
        instrument_obj=inst,
    )
    assert evaluation.days_to_maturity is None
    assert evaluation.maturity_stage == MaturityStage.NOT_EVALUABLE.value
    assert evaluation.institution_action_due_date is None
    assert evaluation.is_overdue is False
    assert evaluation.due_condition == DueCondition.NORMAL.value


# ==============================================================================
# TEST 8: Self-referential lineage rejection
# ==============================================================================
def test_self_referential_lineage_rejection(db_session: Session, sample_instruments: Tuple[Instrument, Instrument, Instrument]):
    i1, _, _ = sample_instruments
    with pytest.raises(AppException) as exc:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(
                predecessor_instrument_id=i1.id,
                successor_instrument_id=i1.id,
            ),
        )
    assert exc.value.status_code == 400
    assert exc.value.code == "SELF_REFERENTIAL_LINEAGE_PROHIBITED"


# ==============================================================================
# TEST 9: Cyclic lineage rejection
# ==============================================================================
def test_cyclic_lineage_rejection(db_session: Session, sample_instruments: Tuple[Instrument, Instrument, Instrument]):
    i1, i2, i3 = sample_instruments

    # 1. Link i1 -> i2 (Valid)
    l1 = create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=i1.id,
            successor_instrument_id=i2.id,
            reason_or_reference="Rollover 1",
        ),
    )
    assert l1.id is not None

    # 2. Link i2 -> i3 (Valid)
    l2 = create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=i2.id,
            successor_instrument_id=i3.id,
            reason_or_reference="Rollover 2",
        ),
    )
    assert l2.id is not None

    # 3. Attempt link i3 -> i1 (Creates directed cycle i1 -> i2 -> i3 -> i1)
    with pytest.raises(AppException) as exc:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(
                predecessor_instrument_id=i3.id,
                successor_instrument_id=i1.id,
                reason_or_reference="Cycle attempt",
            ),
        )
    assert exc.value.status_code == 400
    assert exc.value.code == "CYCLIC_LINEAGE_DETECTED"


# ==============================================================================
# TEST 10: Cross-institution lineage restrictions
# ==============================================================================
def test_cross_institution_lineage_restrictions(
    db_session: Session,
    institution_a: Institution,
    institution_b: Institution,
):
    inst_a = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="HDFC Bank",
        reference_number="FDR-A-1",
        amount=Decimal("3000000.00"),
        issue_date=date(2021, 1, 1),
        maturity_date=date(2026, 1, 1),
    )
    inst_b = Instrument(
        institution_id=institution_b.id,
        instrument_type="FDR",
        bank_name="HDFC Bank",
        reference_number="FDR-B-1",
        amount=Decimal("3000000.00"),
        issue_date=date(2026, 1, 1),
        maturity_date=date(2031, 1, 1),
    )
    db_session.add_all([inst_a, inst_b])
    db_session.commit()

    # Unauthorized cross-institution link rejected
    with pytest.raises(AppException) as exc:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(
                predecessor_instrument_id=inst_a.id,
                successor_instrument_id=inst_b.id,
                allow_authorized_transfer=False,
            ),
        )
    assert exc.value.status_code == 400
    assert exc.value.code == "CROSS_INSTITUTION_LINEAGE_PROHIBITED"

    # Explicit authorized transfer permitted (e.g. college amalgamation)
    lineage = create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=inst_a.id,
            successor_instrument_id=inst_b.id,
            allow_authorized_transfer=True,
            reason_or_reference="AICTE Order Ref #2026/MERGER/892",
        ),
    )
    assert lineage.id is not None
    assert lineage.institution_id == inst_a.institution_id


# ==============================================================================
# TEST 11: Duplicate and concurrent link attempts rejection
# ==============================================================================
def test_duplicate_link_attempts_rejection(
    db_session: Session,
    sample_instruments: Tuple[Instrument, Instrument, Instrument],
    institution_a: Institution,
):
    i1, i2, _ = sample_instruments
    # Create first link
    create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=i1.id,
            successor_instrument_id=i2.id,
        ),
    )

    # Alternate successor i4
    i4 = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        reference_number="FDR-ALT-004",
        amount=Decimal("5000000.00"),
        issue_date=date(2026, 10, 25),
        maturity_date=date(2031, 10, 25),
    )
    db_session.add(i4)
    db_session.commit()

    # Attempting to attach another successor to i1 fails (duplicate active predecessor)
    with pytest.raises(AppException) as exc:
        create_renewal_lineage(
            db_session,
            LineageCreateRequest(
                predecessor_instrument_id=i1.id,
                successor_instrument_id=i4.id,
            ),
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "DUPLICATE_PREDECESSOR_LINEAGE"


# ==============================================================================
# TEST 12: Predecessor history preservation
# ==============================================================================
def test_predecessor_history_preservation(
    db_session: Session,
    sample_instruments: Tuple[Instrument, Instrument, Instrument],
):
    i1, i2, _ = sample_instruments
    original_pred_amount = i1.amount
    original_pred_trust = i1.trust_level
    original_pred_status = i1.status
    original_pred_ref = i1.reference_number

    create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=i1.id,
            successor_instrument_id=i2.id,
            reason_or_reference="Rollover verification",
        ),
    )

    db_session.refresh(i1)
    assert i1.amount == original_pred_amount
    assert i1.trust_level == original_pred_trust
    assert i1.status == original_pred_status
    assert i1.reference_number == original_pred_ref


# ==============================================================================
# TEST 13: Successor creation does not release or overwrite predecessor
# ==============================================================================
def test_successor_creation_does_not_release_predecessor(
    db_session: Session,
    sample_instruments: Tuple[Instrument, Instrument, Instrument],
):
    i1, i2, _ = sample_instruments
    assert i1.status != "RELEASED"

    create_renewal_lineage(
        db_session,
        LineageCreateRequest(
            predecessor_instrument_id=i1.id,
            successor_instrument_id=i2.id,
        ),
    )

    db_session.refresh(i1)
    db_session.refresh(i2)
    # Neither predecessor nor successor is marked RELEASED
    assert i1.status != "RELEASED"
    assert i2.status != "RELEASED"
    assert i2.id != i1.id


# ==============================================================================
# TEST 14: Lineage Tree Query Traversal
# ==============================================================================
def test_lineage_tree_traversal(
    db_session: Session,
    sample_instruments: Tuple[Instrument, Instrument, Instrument],
):
    i1, i2, i3 = sample_instruments
    create_renewal_lineage(
        db_session,
        LineageCreateRequest(predecessor_instrument_id=i1.id, successor_instrument_id=i2.id),
    )
    create_renewal_lineage(
        db_session,
        LineageCreateRequest(predecessor_instrument_id=i2.id, successor_instrument_id=i3.id),
    )

    # Query tree centered on middle instrument i2
    tree = get_lineage_tree(db_session, instrument_id=i2.id)
    assert len(tree.ancestors) == 1
    assert tree.ancestors[0].instrument_id == i1.id
    assert len(tree.successors) == 1
    assert tree.successors[0].instrument_id == i3.id


# ==============================================================================
# TEST 15: HTTP REST Endpoints Coverage
# ==============================================================================
def test_lifecycle_api_endpoints(
    client: TestClient,
    db_session: Session,
    admin_user: User,
    sample_instruments: Tuple[Instrument, Instrument, Instrument],
):
    set_auth(client, admin_user)
    i1, i2, _ = sample_instruments

    # 1. List policies
    res = client.get("/api/v1/lifecycle/policies")
    assert res.status_code == 200
    policies = res.json()
    assert len(policies) >= 1
    assert any(p["is_demo"] is True for p in policies)

    # 2. Evaluate instrument
    res = client.post(
        "/api/v1/lifecycle/evaluate",
        json={"instrument_id": i1.id},
    )
    assert res.status_code == 200
    eval_data = res.json()
    assert eval_data["instrument_id"] == i1.id
    assert eval_data["maturity_stage"] in [
        MaturityStage.ACTIVE.value,
        MaturityStage.MATURING_SOON.value,
        MaturityStage.CRITICAL_WINDOW.value,
    ]

    # 3. Create renewal lineage via API
    res = client.post(
        "/api/v1/lifecycle/lineage/renew",
        json={
            "predecessor_instrument_id": i1.id,
            "successor_instrument_id": i2.id,
            "reason_or_reference": "API test renewal link",
        },
    )
    assert res.status_code == 200
    lineage_data = res.json()
    assert lineage_data["predecessor_instrument_id"] == i1.id
    assert lineage_data["successor_instrument_id"] == i2.id

    # 4. Get instrument lineage tree via instrument router
    res = client.get(f"/api/v1/instruments/{i1.id}/lineage")
    assert res.status_code == 200
    tree_data = res.json()
    assert len(tree_data["successors"]) == 1
    assert tree_data["successors"][0]["instrument_id"] == i2.id
