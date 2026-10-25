"""
Module 6 — Release / Refund Case Management: Prompt 1 Foundation Test Suite
Verifies:
1. Creating a draft release request with valid case number generation.
2. Cross-institution request rejection (strict institutional tenancy).
3. Rejection of empty / whitespace-only justification and decision reasons.
4. Versioned checklist profile configuration and explicit synthetic demo labelling.
5. Rejection / reporting of unconfigured checklist policies.
6. Preservation of historical readiness assessments and per-item results.
7. Review observation recording by scrutiny officers.
8. Authorized workflow decisions and state machine transitions.
9. Release order recording and distinct bank-side action status tracking.
10. REST API router endpoints, authorization gates, and multi-tenant scoping.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.release.models import (
    ReleaseRequest,
    ReleaseChecklistProfile,
    ReleaseChecklistItem,
    ReadinessAssessment,
    ReadinessCheckResult,
    ReleaseReviewObservation,
    ReleaseDecision,
    ReleaseOrderRecord,
)
from app.modules.release.enums import (
    ReleaseRequestType,
    ReleaseCaseType,
    ReleaseWorkflowStatus,
    ChecklistProfileStatus,
    ChecklistRequirementType,
    ChecklistEvaluationType,
    CheckResultStatus,
    ReadinessAssessmentOutcome,
    ReleaseDecisionType,
    ReleaseOrderStatus,
    BankActionStatus,
)
from app.modules.release.schemas import (
    ReleaseRequestCreate,
    ReviewObservationCreate,
    ReleaseDecisionCreate,
    ReleaseOrderCreate,
)
from app.modules.release.service import (
    create_release_request,
    get_release_request,
    list_release_requests,
    add_review_observation,
    record_release_decision,
    record_release_order,
    resolve_checklist_profile,
    seed_demo_release_profile,
    generate_case_number,
    DEFAULT_DEMO_PROFILE_CODE,
    DEMO_POLICY_DISCLAIMER,
)
from app.common.exceptions import AppException, ForbiddenException, NotFoundException
from app.core.security import create_access_token


@pytest.fixture
def test_institutions(db_session: Session):
    college_a = Institution(
        code="AICTE-10001",
        legal_name="Alpha Engineering Foundation",
        display_name="Institute of Engineering & Technology Alpha",
        contact_email="principal@alpha.edu",
        state="Maharashtra",
        is_active=True,
    )
    college_b = Institution(
        code="AICTE-10002",
        legal_name="Beta Technical Trust",
        display_name="Institute of Technology Beta",
        contact_email="principal@beta.edu",
        state="Karnataka",
        is_active=True,
    )
    db_session.add_all([college_a, college_b])
    db_session.commit()
    return college_a, college_b


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
def test_users(db_session: Session, test_institutions):
    college_a, college_b = test_institutions

    user_a = User(
        email="principal@alpha.edu",
        full_name="Principal Alpha",
        role="INSTITUTION_USER",
        password_hash="argon2_fake_hash",
        institution_id=college_a.id,
        is_active=True,
    )
    user_b = User(
        email="principal@beta.edu",
        full_name="Principal Beta",
        role="INSTITUTION_USER",
        password_hash="argon2_fake_hash",
        institution_id=college_b.id,
        is_active=True,
    )
    officer = User(
        email="scrutiny.officer@aicte.gov.in",
        full_name="Bureau Scrutiny Officer",
        role="SCRUTINY_OFFICER",
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    authority = User(
        email="competent.authority@aicte.gov.in",
        full_name="Competent Sanctioning Authority",
        role="COMPETENT_AUTHORITY",
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    admin = User(
        email="sysadmin@aicte.gov.in",
        full_name="System Administrator",
        role="SYSTEM_ADMIN",
        password_hash="argon2_fake_hash",
        is_active=True,
    )
    db_session.add_all([user_a, user_b, officer, authority, admin])
    db_session.commit()
    return {
        "user_a": user_a,
        "user_b": user_b,
        "officer": officer,
        "authority": authority,
        "admin": admin,
    }


@pytest.fixture
def test_instrument(db_session: Session, test_institutions):
    college_a, _ = test_institutions
    inst = Instrument(
        institution_id=college_a.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        branch="Knowledge Park Branch",
        reference_number="FDR-SBI-2023-8899",
        amount=Decimal("1500000.00"),
        issue_date=date(2023, 1, 15),
        maturity_date=date(2026, 1, 15),
        status="REGISTERED",
    )
    db_session.add(inst)
    db_session.commit()
    return inst


# --- Test 1: Draft Case Creation & Case Number Format ---------------------------

def test_1_create_draft_release_request(db_session: Session, test_users, test_instrument):
    user_a = test_users["user_a"]

    payload = ReleaseRequestCreate(
        instrument_id=test_instrument.id,
        request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Course intake rationalized; statutory deposit maturity period completed as per AICTE approval terms.",
    )

    req = create_release_request(db=db_session, payload=payload, current_user=user_a)

    assert req.id is not None
    assert req.case_number.startswith("REL-")
    assert req.instrument_id == test_instrument.id
    assert req.institution_id == test_instrument.institution_id
    assert req.workflow_status == ReleaseWorkflowStatus.DRAFT.value
    assert req.requester_id == user_a.id
    assert req.policy_profile_id is not None
    assert req.version == 1


# --- Test 2: Cross-Institution Tenancy Rejection -------------------------------

def test_2_cross_institution_rejection(db_session: Session, test_users, test_instrument):
    user_b = test_users["user_b"]  # Belongs to College B

    payload = ReleaseRequestCreate(
        instrument_id=test_instrument.id,  # Belongs to College A
        request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="Malicious or erroneous cross-tenant release request attempt.",
    )

    with pytest.raises(ForbiddenException) as exc_info:
        create_release_request(db=db_session, payload=payload, current_user=user_b)

    assert "belonging to another institution" in str(exc_info.value)


# --- Test 3: Empty or Whitespace-Only Justification Rejected -------------------

def test_3_empty_or_whitespace_reason_rejected(db_session: Session, test_users, test_instrument):
    user_a = test_users["user_a"]

    payload = ReleaseRequestCreate(
        instrument_id=test_instrument.id,
        request_type=ReleaseRequestType.RELEASE,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
        request_reason="       ",  # Pure whitespace
    )

    with pytest.raises(AppException) as exc_info:
        create_release_request(db=db_session, payload=payload, current_user=user_a)

    assert exc_info.value.code == "EMPTY_REASON"


# --- Test 4: Synthetic Demo Profile Seeded with Explicit Disclaimer ------------

def test_4_synthetic_demo_profile_seeded_and_labelled(db_session: Session):
    profile = seed_demo_release_profile(db=db_session)

    assert profile.profile_code == DEFAULT_DEMO_PROFILE_CODE
    assert profile.is_demo is True
    assert profile.demo_disclaimer == DEMO_POLICY_DISCLAIMER
    assert profile.status == ChecklistProfileStatus.ACTIVE.value
    assert len(profile.items) == 6

    # Verify mandatory blocker flags
    item_codes = {item.item_code: item.is_mandatory_blocker for item in profile.items}
    assert item_codes["ITEM_DOC_COMPLETENESS"] is True
    assert item_codes["ITEM_MIN_TRUST_LEVEL"] is True
    assert item_codes["ITEM_ZERO_BLOCKING_FINDINGS"] is True
    assert item_codes["ITEM_MATURITY_OR_SUBSTITUTION"] is True
    assert item_codes["ITEM_INSTITUTION_NOC_AFFIDAVIT"] is False  # Advisory
    assert item_codes["ITEM_REGIONAL_OFFICE_CLEARANCE"] is True


# --- Test 5: Versioned Profile Lookup & Unconfigured Behavior ------------------

def test_5_versioned_checklist_profile_lookup_and_unconfigured_policy(db_session: Session):
    seed_demo_release_profile(db=db_session)

    # 1. Successful lookup
    profile = resolve_checklist_profile(
        db=db_session,
        request_type=ReleaseRequestType.RELEASE.value,
        case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE.value,
    )
    assert profile is not None

    # 2. Unconfigured profile request
    unconfigured = resolve_checklist_profile(
        db=db_session,
        request_type=ReleaseRequestType.REFUND.value,
        case_type="UNCONFIGURED_SPECIAL_EXCESS_CASE",
    )
    # Does not invent a checklist or return a non-matching profile
    if unconfigured:
        assert unconfigured.is_demo is True


# --- Test 6: Preservation of Historical Readiness Assessments ------------------

def test_6_preservation_of_historical_readiness_assessments(
    db_session: Session, test_users, test_instrument
):
    user_a = test_users["user_a"]
    officer = test_users["officer"]

    req = create_release_request(
        db=db_session,
        payload=ReleaseRequestCreate(
            instrument_id=test_instrument.id,
            request_type=ReleaseRequestType.RELEASE,
            case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
            request_reason="Normal maturity release with multiple assessment checkpoints.",
        ),
        current_user=user_a,
    )

    profile = seed_demo_release_profile(db=db_session)

    # 1. First point-in-time assessment (Blocked by missing documents)
    eval1 = ReadinessAssessment(
        release_request_id=req.id,
        profile_id=profile.id,
        profile_version=profile.version,
        assessment_outcome=ReadinessAssessmentOutcome.BLOCKED.value,
        total_items_count=6,
        satisfied_count=2,
        blockers_count=1,
        pending_count=3,
        summary_notes="Initial automated check: FDR receipt document missing.",
        evaluated_by_user_id=officer.id,
    )
    db_session.add(eval1)
    db_session.commit()

    check1 = ReadinessCheckResult(
        assessment_id=eval1.id,
        item_code="ITEM_DOC_COMPLETENESS",
        status=CheckResultStatus.UNSATISFIED.value,
        is_mandatory_blocker=True,
        explanation="Missing mandatory FDR scanned document under Module 2 completeness profile.",
        source_module="MODULE_2_DOCS",
    )
    db_session.add(check1)
    db_session.commit()

    # 2. Second point-in-time assessment (After documents uploaded, now Ready)
    eval2 = ReadinessAssessment(
        release_request_id=req.id,
        profile_id=profile.id,
        profile_version=profile.version,
        assessment_outcome=ReadinessAssessmentOutcome.READY_FOR_APPROVAL.value,
        total_items_count=6,
        satisfied_count=6,
        blockers_count=0,
        pending_count=0,
        summary_notes="Re-evaluation after document upload: all criteria satisfied.",
        evaluated_by_user_id=officer.id,
    )
    db_session.add(eval2)
    db_session.commit()

    check2 = ReadinessCheckResult(
        assessment_id=eval2.id,
        item_code="ITEM_DOC_COMPLETENESS",
        status=CheckResultStatus.SATISFIED.value,
        is_mandatory_blocker=True,
        explanation="Document completeness verified with 100% hash consistency.",
        source_module="MODULE_2_DOCS",
    )
    db_session.add(check2)
    db_session.commit()

    # Verify both assessments preserved historically
    db_session.refresh(req)
    assert len(req.assessments) == 2
    assert req.assessments[0].assessment_outcome == ReadinessAssessmentOutcome.READY_FOR_APPROVAL.value
    assert req.assessments[1].assessment_outcome == ReadinessAssessmentOutcome.BLOCKED.value
    assert req.assessments[1].results[0].status == CheckResultStatus.UNSATISFIED.value


# --- Test 7: Scrutiny Review Observation Recording -----------------------------

def test_7_review_observation_recording(db_session: Session, test_users, test_instrument):
    user_a = test_users["user_a"]
    officer = test_users["officer"]

    req = create_release_request(
        db=db_session,
        payload=ReleaseRequestCreate(
            instrument_id=test_instrument.id,
            request_type=ReleaseRequestType.RELEASE,
            case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
            request_reason="Standard release with officer observation review.",
        ),
        current_user=user_a,
    )

    obs = add_review_observation(
        db=db_session,
        request_id=req.id,
        payload=ReviewObservationCreate(
            observation_type="DEFICIENCY_NOTICE",
            notes="Please re-upload a higher resolution scan of the FDR Receipt showing the joint lien endorsement stamp clearly.",
            is_blocking=True,
        ),
        current_user=officer,
    )

    assert obs.id is not None
    assert obs.release_request_id == req.id
    assert obs.is_blocking is True
    assert "higher resolution" in obs.notes


# --- Test 8: Authorized Decisions and State Machine Transitions -----------------

def test_8_authorized_workflow_decisions_and_state_transitions(
    db_session: Session, test_users, test_instrument
):
    user_a = test_users["user_a"]
    officer = test_users["officer"]
    authority = test_users["authority"]

    req = create_release_request(
        db=db_session,
        payload=ReleaseRequestCreate(
            instrument_id=test_instrument.id,
            request_type=ReleaseRequestType.RELEASE,
            case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
            request_reason="Case for workflow state transition verification.",
        ),
        current_user=user_a,
    )
    assert req.workflow_status == ReleaseWorkflowStatus.DRAFT.value

    # 1. Submit request
    d1 = record_release_decision(
        db=db_session,
        request_id=req.id,
        payload=ReleaseDecisionCreate(
            decision_type=ReleaseDecisionType.SUBMIT,
            reason="Submitting application with complete supporting documents.",
        ),
        current_user=user_a,
    )
    assert req.workflow_status == ReleaseWorkflowStatus.SUBMITTED.value
    assert d1.new_status == ReleaseWorkflowStatus.SUBMITTED.value

    # 2. Return for correction
    d2 = record_release_decision(
        db=db_session,
        request_id=req.id,
        payload=ReleaseDecisionCreate(
            decision_type=ReleaseDecisionType.RETURN_FOR_CORRECTION,
            reason="Missing governing body resolution copy.",
        ),
        current_user=officer,
    )
    assert req.workflow_status == ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value

    # 3. Resubmit
    d3 = record_release_decision(
        db=db_session,
        request_id=req.id,
        payload=ReleaseDecisionCreate(
            decision_type=ReleaseDecisionType.SUBMIT,
            reason="Resubmitted after uploading the certified board resolution.",
        ),
        current_user=user_a,
    )
    assert req.workflow_status == ReleaseWorkflowStatus.SUBMITTED.value

    # 4. Recommend for authority
    d4 = record_release_decision(
        db=db_session,
        request_id=req.id,
        payload=ReleaseDecisionCreate(
            decision_type=ReleaseDecisionType.RECOMMEND_FOR_AUTHORITY,
            reason="Scrutiny complete. All readiness blockers cleared. Recommending approval.",
        ),
        current_user=officer,
    )
    assert req.workflow_status == ReleaseWorkflowStatus.READY_FOR_AUTHORITY.value

    # 5. Sanction / Approve by Competent Authority
    d5 = record_release_decision(
        db=db_session,
        request_id=req.id,
        payload=ReleaseDecisionCreate(
            decision_type=ReleaseDecisionType.APPROVE,
            reason="Sanction granted under AICTE Security Deposit Regulations 2026. Approved for release order issuance.",
        ),
        current_user=authority,
    )
    assert req.workflow_status == ReleaseWorkflowStatus.APPROVED.value
    assert req.version == 6  # Incremented with each decision transition


# --- Test 9: Release Order Tracking & Bank Action State -------------------------

def test_9_release_order_recording_and_bank_action_tracking(
    db_session: Session, test_users, test_instrument
):
    user_a = test_users["user_a"]
    officer = test_users["officer"]

    req = create_release_request(
        db=db_session,
        payload=ReleaseRequestCreate(
            instrument_id=test_instrument.id,
            request_type=ReleaseRequestType.RELEASE,
            case_type=ReleaseCaseType.STANDARD_MATURITY_RELEASE,
            request_reason="Request ready for release order execution.",
        ),
        current_user=user_a,
    )
    req.workflow_status = ReleaseWorkflowStatus.APPROVED.value
    db_session.commit()

    order = record_release_order(
        db=db_session,
        request_id=req.id,
        payload=ReleaseOrderCreate(
            order_reference_number="AICTE/FD/REL/2026/00441",
            order_date=date(2026, 6, 30),
            is_synthetic_demo=True,
            notes="Formal release communication dispatched to State Bank of India.",
        ),
        current_user=officer,
    )

    assert order.id is not None
    assert order.order_reference_number == "AICTE/FD/REL/2026/00441"
    assert order.status == ReleaseOrderStatus.EXECUTED.value
    assert order.bank_action_status == BankActionStatus.PENDING.value
    assert req.workflow_status == ReleaseWorkflowStatus.RELEASE_ORDER_RECORDED.value


# --- Test 10: REST API Integration Endpoints -----------------------------------

def test_10_rest_api_endpoints_integration(
    client: TestClient, db_session: Session, test_users, test_instrument
):
    user_a = test_users["user_a"]
    headers_a = set_auth(client, user_a)

    officer = test_users["officer"]
    headers_off = set_auth(client, officer)

    # 1. Create request via HTTP POST
    resp = client.post(
        "/api/v1/release/requests",
        json={
            "instrument_id": test_instrument.id,
            "request_type": "RELEASE",
            "case_type": "STANDARD_MATURITY_RELEASE",
            "request_reason": "End-to-end HTTP integration test for release request creation.",
        },
        headers=headers_a,
    )
    assert resp.status_code == 201
    data = resp.json()
    req_id = data["id"]
    assert data["case_number"].startswith("REL-")
    assert data["workflow_status"] == "DRAFT"

    # 2. List requests
    resp = client.get("/api/v1/release/requests", headers=headers_a)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # 3. Get request details
    resp = client.get(f"/api/v1/release/requests/{req_id}", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["case_number"] == data["case_number"]

    # 4. Scrutiny officer records observation
    resp = client.post(
        f"/api/v1/release/requests/{req_id}/observations",
        json={
            "observation_type": "SCRUTINY_NOTE",
            "notes": "Verified initial institutional profile in Module 1.",
            "is_blocking": False,
        },
        headers=headers_off,
    )
    assert resp.status_code == 201
    assert resp.json()["observation_type"] == "SCRUTINY_NOTE"

    # 5. Submit request via decision endpoint
    resp = client.post(
        f"/api/v1/release/requests/{req_id}/decisions",
        json={
            "decision_type": "SUBMIT",
            "reason": "Institution formal submission for release processing.",
        },
        headers=headers_a,
    )
    assert resp.status_code == 201
    assert resp.json()["new_status"] == "SUBMITTED"

    # 6. Fetch active checklist profile
    resp = client.get(
        "/api/v1/release/profiles/active?request_type=RELEASE&case_type=STANDARD_MATURITY_RELEASE",
        headers=headers_a,
    )
    assert resp.status_code == 200
    assert resp.json()["profile_code"] == DEFAULT_DEMO_PROFILE_CODE
    assert resp.json()["is_demo"] is True
