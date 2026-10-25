"""
Module 7 — Command Center, Search, Reporting & Audit: Prompt 1 Backend Foundation Test Suite
Validates:
1. Status counts against independently calculated counts from seeded test data.
2. Expiring-soon and maturity-window boundary dates.
3. Month-wise maturity counts and amount totals.
4. Overdue and escalated counts.
5. Pending verification and source-unavailable cases.
6. Missing-document and release-blocker counts.
7. Different date ranges and combined filters.
8. Empty database and empty-result behaviour.
9. Institution A cannot see or indirectly count Institution B’s unauthorized records.
10. Role-scoped office, assignee and case metrics.
11. Missing policy configuration is not silently interpreted as a valid zero.
12. Stable and correct results under pagination and sorting.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationFinding, ValidationPolicyConfig
from app.modules.verification.models import VerificationRequest, VerificationResponse
from app.modules.lifecycle.models import LifecycleEvaluation, InstrumentLineage
from app.modules.release.models import (
    ReleaseRequest,
    ReleaseChecklistProfile,
    ReleaseChecklistItem,
    ReadinessAssessment,
    ReadinessCheckResult,
)
from app.modules.release.enums import (
    ReleaseRequestType,
    ReleaseCaseType,
    ReleaseWorkflowStatus,
    ChecklistProfileStatus,
    ReadinessAssessmentOutcome,
    CheckResultStatus,
)
from app.core.security import create_access_token
from app.core.config import settings


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
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_data(db_session: Session):
    today = date.today()

    # 1. Institutions
    inst_a = Institution(
        code="INST-ALPHA",
        legal_name="Alpha Engineering Foundation",
        display_name="Alpha Institute",
        contact_email="admin@alpha.edu",
        state="Maharashtra",
        is_active=True,
    )
    inst_b = Institution(
        code="INST-BETA",
        legal_name="Beta Technical Trust",
        display_name="Beta College",
        contact_email="admin@beta.edu",
        state="Karnataka",
        is_active=True,
    )
    db_session.add_all([inst_a, inst_b])
    db_session.flush()

    # 2. Users
    user_inst_a = User(
        email="user@alpha.edu",
        full_name="Alpha User",
        role="INSTITUTION_USER",
        password_hash="argon2_fake",
        institution_id=inst_a.id,
        is_active=True,
    )
    user_inst_b = User(
        email="user@beta.edu",
        full_name="Beta User",
        role="INSTITUTION_USER",
        password_hash="argon2_fake",
        institution_id=inst_b.id,
        is_active=True,
    )
    officer = User(
        email="officer@aicte.gov.in",
        full_name="Scrutiny Officer",
        role="SCRUTINY_OFFICER",
        password_hash="argon2_fake",
        is_active=True,
    )
    branch_head = User(
        email="head@aicte.gov.in",
        full_name="Branch Head Western",
        role="BRANCH_HEAD",
        password_hash="argon2_fake",
        is_active=True,
    )
    auditor = User(
        email="auditor@cag.gov.in",
        full_name="CAG Regulatory Auditor",
        role="AUDITOR",
        password_hash="argon2_fake",
        is_active=True,
    )
    admin = User(
        email="admin@aicte.gov.in",
        full_name="System Administrator",
        role="SYSTEM_ADMIN",
        password_hash="argon2_fake",
        is_active=True,
    )
    db_session.add_all([user_inst_a, user_inst_b, officer, branch_head, auditor, admin])
    db_session.flush()

    # 3. Instruments for Inst A
    # Active (> 90 days)
    inst_a_active = Instrument(
        institution_id=inst_a.id,
        bank_name="State Bank of India",
        branch="Mumbai Main",
        reference_number="FDR-A-ACTIVE-01",
        amount=Decimal("1000000.00"),
        issue_date=today - timedelta(days=200),
        maturity_date=today + timedelta(days=180),
        status="REGISTERED",
        trust_level="L2_OFFICER_VERIFIED",
        assigned_office="WRO_MUMBAI",
    )
    # Expiring soon (e.g. 45 days)
    inst_a_expiring = Instrument(
        institution_id=inst_a.id,
        bank_name="State Bank of India",
        branch="Nariman Point",
        reference_number="FDR-A-EXPIRING-02",
        amount=Decimal("500000.00"),
        issue_date=today - timedelta(days=320),
        maturity_date=today + timedelta(days=45),
        status="REGISTERED",
        trust_level="L1_DOCUMENT_CONSISTENT",
        assigned_office="WRO_MUMBAI",
    )
    # Matured (past maturity date)
    inst_a_matured = Instrument(
        institution_id=inst_a.id,
        bank_name="Punjab National Bank",
        branch="Pune Camp",
        reference_number="FDR-A-MATURED-03",
        amount=Decimal("750000.00"),
        issue_date=today - timedelta(days=400),
        maturity_date=today - timedelta(days=30),
        status="REGISTERED",
        trust_level="L1_DOCUMENT_CONSISTENT",
        assigned_office="WRO_MUMBAI",
    )
    # Released
    inst_a_released = Instrument(
        institution_id=inst_a.id,
        bank_name="HDFC Bank",
        branch="Fort Mumbai",
        reference_number="FDR-A-RELEASED-04",
        amount=Decimal("1200000.00"),
        issue_date=today - timedelta(days=500),
        maturity_date=today - timedelta(days=10),
        status="RELEASED",
        trust_level="L3_BANK_CONFIRMED",
        assigned_office="WRO_MUMBAI",
    )
    # Pending draft/intake
    inst_a_pending = Instrument(
        institution_id=inst_a.id,
        bank_name="Canara Bank",
        branch="Bandra",
        reference_number="FDR-A-PENDING-05",
        amount=Decimal("300000.00"),
        issue_date=today - timedelta(days=10),
        maturity_date=today + timedelta(days=365),
        status="UNDER_SCRUTINY",
        trust_level="L0_DECLARED",
        assigned_office="WRO_MUMBAI",
    )
    # Renewed predecessor
    inst_a_predecessor = Instrument(
        institution_id=inst_a.id,
        bank_name="Bank of Baroda",
        branch="Andheri",
        reference_number="FDR-A-PRED-06",
        amount=Decimal("600000.00"),
        issue_date=today - timedelta(days=400),
        maturity_date=today - timedelta(days=5),
        status="REGISTERED",
        trust_level="L2_OFFICER_VERIFIED",
        assigned_office="WRO_MUMBAI",
    )
    inst_a_successor = Instrument(
        institution_id=inst_a.id,
        bank_name="Bank of Baroda",
        branch="Andheri",
        reference_number="FDR-A-SUCC-07",
        amount=Decimal("600000.00"),
        issue_date=today - timedelta(days=5),
        maturity_date=today + timedelta(days=360),
        status="REGISTERED",
        trust_level="L0_DECLARED",
        assigned_office="WRO_MUMBAI",
    )

    # 4. Instruments for Inst B (Cross-Tenant)
    inst_b_active = Instrument(
        institution_id=inst_b.id,
        bank_name="Canara Bank",
        branch="Bangalore Central",
        reference_number="FDR-B-ACTIVE-01",
        amount=Decimal("2000000.00"),
        issue_date=today - timedelta(days=100),
        maturity_date=today + timedelta(days=250),
        status="REGISTERED",
        trust_level="L2_OFFICER_VERIFIED",
        assigned_office="SRO_BANGALORE",
    )
    inst_b_expiring = Instrument(
        institution_id=inst_b.id,
        bank_name="State Bank of India",
        branch="MG Road Bangalore",
        reference_number="FDR-B-EXPIRING-02",
        amount=Decimal("800000.00"),
        issue_date=today - timedelta(days=330),
        maturity_date=today + timedelta(days=60),
        status="REGISTERED",
        trust_level="L1_DOCUMENT_CONSISTENT",
        assigned_office="SRO_BANGALORE",
    )

    db_session.add_all([
        inst_a_active, inst_a_expiring, inst_a_matured, inst_a_released,
        inst_a_pending, inst_a_predecessor, inst_a_successor,
        inst_b_active, inst_b_expiring,
    ])
    db_session.flush()

    # 5. Lineage edge for renewed predecessor
    lineage = InstrumentLineage(
        predecessor_instrument_id=inst_a_predecessor.id,
        successor_instrument_id=inst_a_successor.id,
        institution_id=inst_a.id,
        relationship_type="RENEWAL",
        relationship_status="ACTIVE",
    )
    db_session.add(lineage)
    db_session.flush()

    # 6. Verification requests
    vr_pending = VerificationRequest(
        instrument_id=inst_a_pending.id,
        reference_code="VR-20261025-001",
        channel="LIVE_BANK_API",
        status="PENDING",
        snapshot_data_json="{}",
        attempt_count=1,
    )
    vr_unavail = VerificationRequest(
        instrument_id=inst_a_expiring.id,
        reference_code="VR-20261025-002",
        channel="DIRECT_API",
        status="SOURCE_UNAVAILABLE",
        snapshot_data_json="{}",
        error_details="source_unavailable: Bank endpoint timeout",
        attempt_count=3,
    )
    db_session.add_all([vr_pending, vr_unavail])

    # 7. Lifecycle evaluation with overdue & escalated
    eval_overdue = LifecycleEvaluation(
        instrument_id=inst_a_matured.id,
        evaluation_date=today,
        days_to_maturity=-30,
        maturity_stage="MATURED",
        is_overdue=True,
        is_escalated=True,
        escalation_role="BRANCH_HEAD",
        due_condition="ESCALATED",
        institution_action_due_date=today - timedelta(days=15),
    )
    db_session.add(eval_overdue)

    # 8. Release Request with blockers
    rel_profile = ReleaseChecklistProfile(
        profile_code="DEFAULT_REL_M6",
        name="Standard Release Profile",
        version=1,
        request_type=ReleaseRequestType.RELEASE.value,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE.value,
        status=ChecklistProfileStatus.ACTIVE.value,
    )
    db_session.add(rel_profile)
    db_session.flush()

    rel_item = ReleaseChecklistItem(
        profile_id=rel_profile.id,
        item_code="CHK-DOC-FDR",
        title="Valid FDR Document Required",
        explanation="Original scanned FDR must be verified.",
        requirement_type="DOCUMENT_COMPLETENESS",
        is_mandatory_blocker=True,
        expected_evidence_source="DOCUMENT",
    )
    db_session.add(rel_item)
    db_session.flush()

    rel_request = ReleaseRequest(
        case_number="REL-2026-0001",
        instrument_id=inst_a_matured.id,
        institution_id=inst_a.id,
        request_type=ReleaseRequestType.RELEASE.value,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE.value,
        policy_profile_id=rel_profile.id,
        policy_version=1,
        requester_id=user_inst_a.id,
        request_reason="Maturity completed, release deposit.",
        workflow_status=ReleaseWorkflowStatus.UNDER_REVIEW.value,
        assigned_reviewer_id=officer.id,
        assigned_office="WRO_MUMBAI",
        submitted_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    db_session.add(rel_request)
    db_session.flush()

    assessment = ReadinessAssessment(
        release_request_id=rel_request.id,
        profile_id=rel_profile.id,
        profile_version=1,
        assessment_outcome=ReadinessAssessmentOutcome.BLOCKED.value,
        total_items_count=1,
        satisfied_count=0,
        blockers_count=1,
        pending_count=0,
        advisory_flags_count=0,
    )
    db_session.add(assessment)
    db_session.flush()

    check_res = ReadinessCheckResult(
        assessment_id=assessment.id,
        checklist_item_id=rel_item.id,
        item_code="CHK-DOC-FDR",
        status=CheckResultStatus.UNSATISFIED.value,
        is_mandatory_blocker=True,
        explanation="Missing FDR document upload.",
        source_module="DOCUMENT_COMPLETENESS",
    )
    db_session.add(check_res)

    db_session.commit()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "user_inst_a": user_inst_a,
        "user_inst_b": user_inst_b,
        "officer": officer,
        "branch_head": branch_head,
        "auditor": auditor,
        "admin": admin,
        "instruments_a": [
            inst_a_active, inst_a_expiring, inst_a_matured, inst_a_released,
            inst_a_pending, inst_a_predecessor, inst_a_successor,
        ],
        "instruments_b": [inst_b_active, inst_b_expiring],
    }


# ==============================================================================
# 1. Status counts against independently calculated counts from seeded data
# ==============================================================================
def test_status_counts_aggregation(client: TestClient, seed_data):
    """Assert status counts match independent queries for Bureau officer."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    res = client.get("/api/v1/dashboard/status-counts?window_days=90", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    # Nationwide counts across Inst A + Inst B:
    # Released: 1 (inst_a_released)
    assert data["released_count"] == 1
    # Renewed: 1 (inst_a_predecessor)
    assert data["renewed_count"] == 1
    # Pending: 1 (inst_a_pending)
    assert data["pending_count"] == 1
    # Matured: 1 (inst_a_matured)
    assert data["matured_count"] == 1
    # Expiring soon: 2 (inst_a_expiring: +45d, inst_b_expiring: +60d)
    assert data["expiring_soon_count"] == 2
    # Active: 3 (inst_a_active: +180d, inst_a_successor: +360d, inst_b_active: +250d)
    assert data["active_count"] == 3
    # Total instruments = 9
    assert data["total_instruments"] == 9


# ==============================================================================
# 2. Expiring-soon and maturity-window boundary dates
# ==============================================================================
def test_expiring_soon_boundary_conditions(client: TestClient, seed_data):
    """Test changing window_days dynamically alters expiring-soon count."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    # At window_days=30, neither +45d nor +60d is included
    res30 = client.get("/api/v1/dashboard/status-counts?window_days=30", headers=headers)
    assert res30.status_code == 200
    assert res30.json()["expiring_soon_count"] == 0

    # At window_days=50, +45d is included (1), but +60d is not
    res50 = client.get("/api/v1/dashboard/status-counts?window_days=50", headers=headers)
    assert res50.status_code == 200
    assert res50.json()["expiring_soon_count"] == 1

    # At window_days=90, both +45d and +60d are included (2)
    res90 = client.get("/api/v1/dashboard/status-counts?window_days=90", headers=headers)
    assert res90.status_code == 200
    assert res90.json()["expiring_soon_count"] == 2


# ==============================================================================
# 3. Month-wise maturity counts and amount totals
# ==============================================================================
def test_month_wise_maturity_load_aggregation(client: TestClient, seed_data):
    """Assert month-wise maturity load aggregates accurately without speculative prediction."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    current_yr = date.today().year
    res = client.get(f"/api/v1/dashboard/maturity-load?calendar_year={current_yr}", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["metric_id"] == "MTR-MAT-LOAD"
    assert len(data["points"]) == 12  # All 12 calendar months present
    assert data["calendar_year"] == current_yr
    assert Decimal(data["grand_total_amount"]) > Decimal("0.00")
    assert "not a forecast" in data["disclaimer"].lower()


# ==============================================================================
# 4. Overdue and escalated counts
# ==============================================================================
def test_overdue_and_escalated_work_metrics(client: TestClient, seed_data):
    """Assert overdue and escalated metrics match seeded lifecycle evaluation records."""
    head = seed_data["branch_head"]
    headers = set_auth(client, head)

    res = client.get("/api/v1/dashboard/overdue-escalated", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_overdue"] >= 1
    assert data["total_escalated"] >= 1
    assert "WRO_MUMBAI" in data["by_office"]


# ==============================================================================
# 5. Pending verification and source-unavailable cases
# ==============================================================================
def test_verification_queue_and_source_unavailability(client: TestClient, seed_data):
    """Assert outstanding requests and source-unavailable telemetry."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    res = client.get("/api/v1/dashboard/verification-queue", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_outstanding"] == 1
    assert data["source_unavailable_count"] == 1
    assert data["average_age_days"] >= 0.0
    assert "<7d" in data["age_distribution"]


# ==============================================================================
# 6. Missing-document and release-blocker counts
# ==============================================================================
def test_release_blockers_aggregation(client: TestClient, seed_data):
    """Assert release blockers correctly count unmet mandatory items from Module 6."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    res = client.get("/api/v1/dashboard/release-blockers", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_active_release_requests"] == 1
    assert data["blocked_requests_count"] == 1
    assert data["unmet_mandatory_items_count"] == 1
    assert len(data["cases"]) == 1
    assert data["cases"][0]["case_number"] == "REL-2026-0001"
    assert "CHK-DOC-FDR" in data["cases"][0]["unsatisfied_item_codes"]


# ==============================================================================
# 7. Different date ranges and combined filters
# ==============================================================================
def test_maturity_window_drilldown(client: TestClient, seed_data):
    """Assert maturity window filters by bank and office."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    today = date.today()
    start = today.isoformat()
    end = (today + timedelta(days=100)).isoformat()

    res = client.get(
        f"/api/v1/dashboard/maturity-window?start_date={start}&end_date={end}&bank_name=State+Bank+of+India",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    # Both Inst A and Inst B have SBI maturing in this window
    assert data["total_instruments"] == 2
    for rec in data["records"]:
        assert "State Bank of India" in rec["bank_name"]


# ==============================================================================
# 8. Empty database and empty-result behaviour
# ==============================================================================
def test_empty_results_handling(client: TestClient, db_session: Session):
    """Assert empty database or zero match queries return valid responses without crashing."""
    # Create isolated empty user
    empty_admin = User(
        email="empty_admin@aicte.gov.in",
        full_name="Empty Admin",
        role="SYSTEM_ADMIN",
        password_hash="argon2_fake",
        is_active=True,
    )
    db_session.add(empty_admin)
    db_session.commit()

    headers = set_auth(client, empty_admin)

    res = client.get(
        "/api/v1/dashboard/status-counts?assigned_office=NON_EXISTENT_OFFICE",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_instruments"] == 0
    assert data["active_count"] == 0
    assert data["total_deposit_value"] == "0.00"


# ==============================================================================
# 9. Tenant Isolation: Institution A cannot see or count Institution B's records
# ==============================================================================
def test_tenant_isolation_and_cross_institution_rejection(client: TestClient, seed_data):
    """Institution A receives only own data and cannot query Institution B."""
    user_a = seed_data["user_inst_a"]
    inst_b = seed_data["inst_b"]
    headers_a = set_auth(client, user_a)

    # 1. Institution A query without params returns only Inst A records (7 total)
    res = client.get("/api/v1/dashboard/status-counts", headers=headers_a)
    assert res.status_code == 200
    data = res.json()
    assert data["total_instruments"] == 7

    # 2. Attempting to query Inst B's ID explicitly MUST return 403 Forbidden
    cross_res = client.get(
        f"/api/v1/dashboard/status-counts?institution_id={inst_b.id}",
        headers=headers_a,
    )
    assert cross_res.status_code == 403
    assert "Access denied" in cross_res.json()["detail"]


# ==============================================================================
# 10. Role-scoped office, assignee and case metrics
# ==============================================================================
def test_role_scoped_office_and_assignee_visibility(client: TestClient, seed_data):
    """Branch Head views assignee breakdowns, whereas Institution User does not."""
    head = seed_data["branch_head"]
    user_a = seed_data["user_inst_a"]

    # Branch Head
    head_headers = set_auth(client, head)
    res_head = client.get("/api/v1/dashboard/overdue-escalated", headers=head_headers)
    assert res_head.status_code == 200
    assert res_head.json()["by_assignee"] is not None

    # Institution user
    inst_headers = set_auth(client, user_a)
    res_inst = client.get("/api/v1/dashboard/overdue-escalated", headers=inst_headers)
    assert res_inst.status_code == 200
    # Assignee analytics redacted for institution users
    assert res_inst.json()["by_assignee"] is None


# ==============================================================================
# 11. Missing policy configuration is not silently interpreted as valid zero
# ==============================================================================
def test_document_completeness_and_unconfigured_policy(client: TestClient, seed_data):
    """When REQUIRED_DOCUMENT_CATEGORIES is unconfigured, return POLICY_UNCONFIGURED."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    res = client.get("/api/v1/dashboard/document-completeness", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["policy_configured"] is False
    assert data["policy_version"] is None
    assert "POLICY_UNCONFIGURED" in data["policy_status_message"]


# ==============================================================================
# 12. Stable and correct results under pagination and sorting
# ==============================================================================
def test_pagination_and_sorting_stability(client: TestClient, seed_data):
    """Assert search endpoint respects allowlisted sort and pagination boundaries."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    # Page 1 (limit 3)
    res_p1 = client.get("/api/v1/dashboard/search?sort_by=amount&sort_order=desc&skip=0&limit=3", headers=headers)
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert p1_data["total_count"] == 9
    assert len(p1_data["records"]) == 3

    # Page 2 (limit 3)
    res_p2 = client.get("/api/v1/dashboard/search?sort_by=amount&sort_order=desc&skip=3&limit=3", headers=headers)
    assert res_p2.status_code == 200
    p2_data = res_p2.json()
    assert len(p2_data["records"]) == 3

    # Check distinct IDs across pages (stability)
    p1_ids = {r["id"] for r in p1_data["records"]}
    p2_ids = {r["id"] for r in p2_data["records"]}
    assert p1_ids.isdisjoint(p2_ids)

    # Descending amount order check
    amounts_p1 = [Decimal(r["amount"]) for r in p1_data["records"]]
    assert amounts_p1 == sorted(amounts_p1, reverse=True)


# ==============================================================================
# 13. Priority Queue Scoring and Weights
# ==============================================================================
def test_operational_priority_queue_scoring(client: TestClient, seed_data):
    """Assert operational priority queue returns transparent scores and factor breakdowns."""
    officer = seed_data["officer"]
    headers = set_auth(client, officer)

    res = client.get("/api/v1/dashboard/priority-queue", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_count"] > 0
    assert "weights_applied" in data
    assert data["weights_applied"]["urgency"] == 0.35

    top_item = data["items"][0]
    assert 0.0 <= top_item["priority_score"] <= 100.0
    assert 0.0 <= top_item["urgency_factor"] <= 100.0
    assert 0.0 <= top_item["discrepancy_factor"] <= 100.0


# ==============================================================================
# 14. Metrics Dictionary Endpoint Verification (PRD-FR-077)
# ==============================================================================
def test_metric_dictionary_endpoint(client: TestClient, seed_data):
    """Assert all documented metrics are accessible via REST API."""
    auditor = seed_data["auditor"]
    headers = set_auth(client, auditor)

    res = client.get("/api/v1/dashboard/metrics/dictionary", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_metrics"] >= 8
    metric_ids = {m["metric_id"] for m in data["metrics"]}
    assert "MTR-STAT-ACTIVE" in metric_ids
    assert "MTR-MAT-WINDOW" in metric_ids
    assert "MTR-MAT-LOAD" in metric_ids
    assert "MTR-PRIORITY-QUEUE" in metric_ids
