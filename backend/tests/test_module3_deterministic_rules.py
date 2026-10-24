"""
Test Suite: Module 3 — Deterministic Rules, Validation Execution & Explainable Findings API
Tests cover all requirements from Prompt 2:

1.  Each required-field rule (Rule A: VAL-REQ-001)
2.  Positive amount validation (Rule B: VAL-AMT-001)
3.  Missing or unconfigured policy amount (Rule B: VAL-AMT-002)
4.  Date ordering and bounds (Rule C: VAL-DATE-001)
5.  Configured validity rule (Rule C: VAL-DATE-003)
6.  Institution mismatch detection (Rule D: VAL-INST-001)
7.  Module 2 completeness result integration (Rule E: VAL-DOC-002)
8.  Unavailable checklist/profile behavior (Rule E: VAL-DOC-002)
9.  Basic data consistency (Rule F: VAL-CONS-001)
10. Finding explanation fields and evidence
11. Idempotent repeated evaluation (no duplicates, dismissed stays dismissed)
12. Changed-input re-evaluation (supersession of earlier finding)
13. Superseded finding history and linkages
14. API endpoints:
    - POST /api/v1/instruments/{id}/validation-runs
    - GET  /api/v1/instruments/{id}/validation-runs
    - GET  /api/v1/instruments/{id}/findings
    - GET  /api/v1/findings/{id}
    - POST /api/v1/findings/{id}/re-evaluate
    - POST /api/v1/instruments/{id}/rules/{rule_id}/evaluate
15. API authentication, RBAC, and institution tenant scoping
16. Invalid request rejection
17. Prevention of client-controlled trust-level / status changes
18. Unavailable rule execution / error recording
19. Accurate validation-run counts
"""
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.validation.models import (
    ValidationFinding,
    ValidationPolicyConfig,
    ValidationRun,
)
from app.modules.validation.enums import (
    FindingStatus,
    RuleOutcome,
    RuleSeverity,
    RuleType,
    FindingCategory,
)
from app.modules.validation.registry import (
    BaseValidationRule,
    RuleContext,
    RuleResult,
    rule_registry,
)
from app.modules.validation.engine import run_validation
from app.modules.validation.finding_service import (
    upsert_finding,
    resolve_finding_if_cleared,
    get_findings_for_instrument,
    dismiss_finding,
    re_evaluate_finding,
    get_validation_runs_for_instrument,
)
from app.modules.validation.policy_service import set_policy_config
from app.modules.auth.service import provision_user
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_BRANCH_HEAD,
    ROLE_AUDITOR,
    create_access_token,
)
from app.core.config import settings


# ---------------------------------------------------------------------------
# Fixtures and Helpers
# ---------------------------------------------------------------------------

def set_auth_cookie(client: TestClient, user: User):
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
def institution_a(db_session: Session) -> Institution:
    inst = Institution(
        code="INST-DET-01",
        legal_name="National Engineering Academy",
        display_name="NEA",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar NEA",
        contact_email="registrar@nea.ac.in",
        contact_phone="+91-11-23456789",
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
def institution_b(db_session: Session) -> Institution:
    inst = Institution(
        code="INST-DET-02",
        legal_name="Southern Science Institute",
        display_name="SSI",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar SSI",
        contact_email="registrar@ssi.ac.in",
        contact_phone="+91-80-23456789",
        address_line1="Campus South",
        city="Bengaluru",
        state="Karnataka",
        postal_code="560001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def inactive_institution(db_session: Session) -> Institution:
    inst = Institution(
        code="INST-INACT-01",
        legal_name="Defunct Technical College",
        display_name="DTC",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Ex-Registrar",
        contact_email="defunct@dtc.ac.in",
        contact_phone="+91-11-99999999",
        address_line1="Old Campus",
        city="Kanpur",
        state="Uttar Pradesh",
        postal_code="208001",
        is_active=False,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def instrument_a(db_session: Session, institution_a: Institution) -> Instrument:
    inst = Instrument(
        institution_id=institution_a.id,
        instrument_type="FDR",
        bank_name="Canara Bank",
        branch="Delhi Main Branch",
        reference_number="CAN-2026-FDR-001",
        amount=Decimal("2500000.00"),
        currency="INR",
        issue_date=date(2026, 1, 15),
        maturity_date=date(2031, 1, 15),
        lien_holder="AICTE Regulation Bureau",
        lien_marked=True,
        joint_with_aicte=True,
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def admin_user(db_session: Session) -> User:
    return provision_user(
        db=db_session,
        full_name="Module3 Admin",
        email="m3.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )


@pytest.fixture
def officer_user(db_session: Session) -> User:
    return provision_user(
        db=db_session,
        full_name="Module3 Officer",
        email="m3.officer@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SCRUTINY_OFFICER,
    )


@pytest.fixture
def inst_user_a(db_session: Session, institution_a: Institution) -> User:
    return provision_user(
        db=db_session,
        full_name="NEA User",
        email="user@nea.ac.in",
        password="SecurePass@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=institution_a.id,
    )


@pytest.fixture
def inst_user_b(db_session: Session, institution_b: Institution) -> User:
    return provision_user(
        db=db_session,
        full_name="SSI User",
        email="user@ssi.ac.in",
        password="SecurePass@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=institution_b.id,
    )


def make_ctx(
    instrument: Instrument,
    institution: Institution,
    policy: Optional[dict] = None,
    checklist_result: Optional[dict] = None,
    extracted_fields: Optional[list] = None,
) -> RuleContext:
    return RuleContext(
        instrument_id=instrument.id,
        institution_id=institution.id,
        instrument_status=instrument.status,
        instrument_trust_level=instrument.trust_level,
        instrument_type=instrument.instrument_type,
        bank_name=instrument.bank_name,
        branch=instrument.branch,
        reference_number=instrument.reference_number,
        amount_decimal=instrument.amount,
        currency=instrument.currency,
        issue_date=instrument.issue_date,
        maturity_date=instrument.maturity_date,
        lien_holder=instrument.lien_holder,
        lien_details=instrument.lien_details,
        lien_marked=instrument.lien_marked,
        joint_with_aicte=instrument.joint_with_aicte,
        assigned_office=instrument.assigned_office,
        institution_is_active=institution.is_active,
        institution_type=institution.institution_type,
        institution_legal_name=institution.legal_name,
        institution_code=institution.code,
        available_documents=[],
        checklist_result=checklist_result,
        extracted_fields=extracted_fields or [],
        policy=policy or {},
    )


# ---------------------------------------------------------------------------
# 1. Rule A: Required Instrument Fields (VAL-REQ-001)
# ---------------------------------------------------------------------------

def test_rule_a_required_fields_all_present(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-REQ-001")
    assert rule is not None
    ctx = make_ctx(instrument_a, institution_a)
    result = rule.evaluate(ctx)
    assert result.outcome == RuleOutcome.PASS
    assert "required fields are present" in result.explanation


def test_rule_a_required_fields_missing(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-REQ-001")
    ctx = make_ctx(instrument_a, institution_a)
    ctx.bank_name = ""
    ctx.reference_number = "   "
    ctx.amount_decimal = None

    result = rule.evaluate(ctx)
    assert result.outcome == RuleOutcome.FAIL
    assert "bank_name" in result.observed_value
    assert "reference_number" in result.observed_value
    assert "amount" in result.observed_value
    assert result.suggested_action is not None


def test_rule_a_configured_required_fields_policy(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-REQ-001")
    # Custom policy requiring branch and lien_holder
    ctx = make_ctx(
        instrument_a,
        institution_a,
        policy={
            "REQUIRED_INSTRUMENT_FIELDS": ["bank_name", "branch", "lien_holder"],
            "_policy_version_ref": "POL-REQ-V2",
        },
    )
    ctx.branch = None  # missing configured field
    result = rule.evaluate(ctx)
    assert result.outcome == RuleOutcome.FAIL
    assert "branch" in result.observed_value
    assert result.policy_version_ref == "POL-REQ-V2"


# ---------------------------------------------------------------------------
# 2. Rule B: Amount Validity (VAL-AMT-001, VAL-AMT-002)
# ---------------------------------------------------------------------------

def test_rule_b_positive_amount(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-AMT-001")
    ctx = make_ctx(instrument_a, institution_a)
    assert rule.evaluate(ctx).outcome == RuleOutcome.PASS

    ctx.amount_decimal = Decimal("0.00")
    assert rule.evaluate(ctx).outcome == RuleOutcome.FAIL

    ctx.amount_decimal = Decimal("-1000.00")
    assert rule.evaluate(ctx).outcome == RuleOutcome.FAIL

    ctx.amount_decimal = None
    assert rule.evaluate(ctx).outcome == RuleOutcome.UNABLE_TO_EVALUATE


def test_rule_b_missing_policy_amount(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-AMT-002")
    # No policy configured
    ctx = make_ctx(instrument_a, institution_a, policy={})
    result = rule.evaluate(ctx)
    assert result.outcome == RuleOutcome.UNABLE_TO_EVALUATE
    assert "no active, approved policy value is configured" in result.explanation


def test_rule_b_configured_policy_amount(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-AMT-002")
    # Configured policy threshold
    ctx = make_ctx(
        instrument_a,
        institution_a,
        policy={
            "MIN_DEPOSIT_AMOUNT_INR": "3000000.00",
            "_policy_version_ref": "POL-MIN-3M",
        },
    )
    # instrument amount is 2,500,000 < 3,000,000
    result = rule.evaluate(ctx)
    assert result.outcome == RuleOutcome.FAIL
    assert result.policy_version_ref == "POL-MIN-3M"
    assert "2500000.00" in result.observed_value

    # Compliant amount
    ctx.amount_decimal = Decimal("3500000.00")
    assert rule.evaluate(ctx).outcome == RuleOutcome.PASS


# ---------------------------------------------------------------------------
# 3. Rule C: Date Logic & Bounds (VAL-DATE-001, VAL-DATE-003)
# ---------------------------------------------------------------------------

def test_rule_c_date_ordering(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-DATE-001")
    ctx = make_ctx(instrument_a, institution_a)
    assert rule.evaluate(ctx).outcome == RuleOutcome.PASS

    # Maturity before issue
    ctx.issue_date = date(2026, 6, 1)
    ctx.maturity_date = date(2026, 5, 1)
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.FAIL
    assert "Maturity date is not after issue date" in res.title


def test_rule_c_out_of_bounds_dates(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-DATE-001")
    ctx = make_ctx(instrument_a, institution_a)
    # Out of supported calendar bounds (year 1980)
    ctx.issue_date = date(1980, 1, 1)
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.FAIL
    assert "outside supported system bounds" in res.title


def test_rule_c_configured_validity_period_not_applicable(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-DATE-003")
    # When no validity period configured, must be NOT_APPLICABLE
    ctx = make_ctx(instrument_a, institution_a, policy={})
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.NOT_APPLICABLE


def test_rule_c_configured_validity_period_evaluation(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-DATE-003")
    # Configure MIN_VALIDITY_DAYS = 365 * 3 (approx 1095 days)
    ctx = make_ctx(
        instrument_a,
        institution_a,
        policy={
            "MIN_VALIDITY_DAYS": "1095",
            "_policy_version_ref": "POL-TERM-3Y",
        },
    )
    # 5-year term passes
    ctx.issue_date = date(2026, 1, 1)
    ctx.maturity_date = date(2031, 1, 1)
    assert rule.evaluate(ctx).outcome == RuleOutcome.PASS

    # 1-year term fails configured minimum
    ctx.maturity_date = date(2027, 1, 1)
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.FAIL
    assert "shorter than configured minimum" in res.title
    assert res.policy_version_ref == "POL-TERM-3Y"


# ---------------------------------------------------------------------------
# 4. Rule D: Institution Consistency (VAL-INST-001)
# ---------------------------------------------------------------------------

def test_rule_d_institution_mismatch_detection(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-INST-001")
    # Extracted document mentions a completely different institution
    ctx = make_ctx(
        instrument_a,
        institution_a,
        extracted_fields=[
            {
                "document_version_id": "doc-ver-uuid-999",
                "doc_account_holder": "Royal Horizon Polytechnic",
            }
        ],
    )
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.FAIL
    assert "mismatch" in res.title.lower()
    assert "Royal Horizon Polytechnic" in res.observed_value
    assert institution_a.legal_name in res.expected_value
    assert "doc-ver-uuid-999" in res.evidence_refs


def test_rule_d_institution_matching(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-INST-001")
    # Extracted document matches institution name
    ctx = make_ctx(
        instrument_a,
        institution_a,
        extracted_fields=[
            {
                "document_version_id": "doc-ver-uuid-111",
                "doc_account_holder": "National Engineering Academy",
            }
        ],
    )
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.PASS


# ---------------------------------------------------------------------------
# 5. Rule E: Document Completeness Integration (VAL-DOC-002)
# ---------------------------------------------------------------------------

def test_rule_e_unavailable_checklist_profile(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-DOC-002")
    # When Module 2 has no checklist profile, reports limitation explicitly
    ctx = make_ctx(instrument_a, institution_a, checklist_result=None)
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.UNABLE_TO_EVALUATE
    assert "unavailable: No Module 2 checklist" in res.explanation


def test_rule_e_checklist_integration_evaluation(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-DOC-002")
    # Incomplete checklist
    ctx = make_ctx(
        instrument_a,
        institution_a,
        checklist_result={
            "is_complete": False,
            "items": [
                {"category": "FDR_COPY", "status": "SATISFIED", "document_id": "doc-1"},
                {"category": "BANK_CONFIRMATION", "status": "MISSING", "document_id": None},
            ],
            "evidence_refs": ["doc-1"],
        },
    )
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.FAIL
    assert "BANK_CONFIRMATION" in res.observed_value

    # Satisfied checklist
    ctx.checklist_result["is_complete"] = True
    ctx.checklist_result["items"][1]["status"] = "SATISFIED"
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.PASS


# ---------------------------------------------------------------------------
# 6. Rule F: Basic Data Consistency (VAL-CONS-001)
# ---------------------------------------------------------------------------

def test_rule_f_inactive_institution_restriction(instrument_a: Instrument, inactive_institution: Institution):
    rule = rule_registry.get("VAL-CONS-001")
    ctx = make_ctx(instrument_a, inactive_institution)
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.FAIL
    assert "inactive institution" in res.title.lower()


def test_rule_f_contradictory_lien_flags(instrument_a: Instrument, institution_a: Institution):
    rule = rule_registry.get("VAL-CONS-001")
    # joint_with_aicte True but lien_marked False
    ctx = make_ctx(instrument_a, institution_a)
    ctx.joint_with_aicte = True
    ctx.lien_marked = False
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.FAIL
    assert "contradictory" in res.title.lower()

    # lien_marked True but empty lien_holder
    ctx.lien_marked = True
    ctx.lien_holder = ""
    res = rule.evaluate(ctx)
    assert res.outcome == RuleOutcome.FAIL
    assert "unspecified" in res.title.lower()


# ---------------------------------------------------------------------------
# 7. Finding Lifecycle, Idempotency & Supersession
# ---------------------------------------------------------------------------

def test_idempotent_repeated_evaluation_and_dismissal(db_session: Session, instrument_a: Instrument, officer_user: User):
    # Instrument amount set to 0 -> raises VAL-AMT-001
    instrument_a.amount = Decimal("0.00")
    db_session.commit()

    run1 = run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)
    assert run1["failures_count"] >= 1

    findings1 = get_findings_for_instrument(db=db_session, instrument_id=instrument_a.id, status_filter=["OPEN"])
    amt_findings = [f for f in findings1 if f.rule_id == "VAL-AMT-001"]
    assert len(amt_findings) == 1
    finding_id = amt_findings[0].id
    first_detected = amt_findings[0].first_detected_at

    # Second run without input changes
    run2 = run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)
    findings2 = get_findings_for_instrument(db=db_session, instrument_id=instrument_a.id, status_filter=["OPEN"])
    amt_findings2 = [f for f in findings2 if f.rule_id == "VAL-AMT-001"]
    assert len(amt_findings2) == 1  # No duplicate
    assert amt_findings2[0].id == finding_id
    assert amt_findings2[0].first_detected_at == first_detected
    assert amt_findings2[0].last_evaluated_at >= first_detected

    # Dismiss finding
    dismiss_finding(db=db_session, finding=amt_findings2[0], dismissed_by_user_id=officer_user.id, reason="Reviewed paper certificate.")
    db_session.refresh(amt_findings2[0])
    assert amt_findings2[0].status == FindingStatus.DISMISSED.value

    # Third run: unchanged inputs must NOT re-open dismissed finding
    run3 = run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)
    findings3_open = get_findings_for_instrument(db=db_session, instrument_id=instrument_a.id, status_filter=["OPEN"])
    amt_findings3 = [f for f in findings3_open if f.rule_id == "VAL-AMT-001"]
    assert len(amt_findings3) == 0  # Still dismissed, not re-opened!


def test_changed_input_supersedes_finding(db_session: Session, instrument_a: Instrument, officer_user: User):
    # Set amount to -100 -> fires VAL-AMT-001
    instrument_a.amount = Decimal("-100.00")
    db_session.commit()
    run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)

    f1 = db_session.scalar(
        select(ValidationFinding).where(
            ValidationFinding.instrument_id == instrument_a.id,
            ValidationFinding.rule_id == "VAL-AMT-001",
            ValidationFinding.status == "OPEN",
        )
    )
    assert f1 is not None
    assert f1.observed_value == "-100.00"

    # Input changes to -200 -> re-evaluation supersedes f1 and creates f2
    instrument_a.amount = Decimal("-200.00")
    db_session.commit()
    run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)

    db_session.refresh(f1)
    assert f1.status == FindingStatus.SUPERSEDED.value

    f2 = db_session.scalar(
        select(ValidationFinding).where(
            ValidationFinding.instrument_id == instrument_a.id,
            ValidationFinding.rule_id == "VAL-AMT-001",
            ValidationFinding.status == "OPEN",
        )
    )
    assert f2 is not None
    assert f2.id != f1.id
    assert f1.superseded_by_finding_id == f2.id
    assert f2.observed_value == "-200.00"


def test_input_corrected_resolves_finding(db_session: Session, instrument_a: Instrument, officer_user: User):
    # Start with invalid amount
    instrument_a.amount = Decimal("-500.00")
    db_session.commit()
    run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)

    f = db_session.scalar(
        select(ValidationFinding).where(
            ValidationFinding.instrument_id == instrument_a.id,
            ValidationFinding.rule_id == "VAL-AMT-001",
            ValidationFinding.status == "OPEN",
        )
    )
    assert f is not None

    # Correct amount to valid positive value
    instrument_a.amount = Decimal("500000.00")
    db_session.commit()
    run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)

    db_session.refresh(f)
    assert f.status == FindingStatus.RESOLVED.value
    assert f.resolved_at is not None
    assert "cleared on re-evaluation" in f.resolution_note


# ---------------------------------------------------------------------------
# 8. API Endpoints: Validation Runs and Findings
# ---------------------------------------------------------------------------

def test_api_validation_runs_endpoints(
    client: TestClient,
    instrument_a: Instrument,
    officer_user: User,
    inst_user_a: User,
    inst_user_b: User,
):
    # 1. POST /api/v1/instruments/{id}/validation-runs by officer
    set_auth_cookie(client, officer_user)
    resp = client.post(
        f"/api/v1/instruments/{instrument_a.id}/validation-runs",
        json={"rule_ids": ["VAL-AMT-001", "VAL-DATE-001"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["instrument_id"] == instrument_a.id
    assert "passes_count" in data
    assert "rules_evaluated" in data
    assert "VAL-AMT-001" in data["rules_evaluated"]

    # 2. GET /api/v1/instruments/{id}/validation-runs
    resp_runs = client.get(f"/api/v1/instruments/{instrument_a.id}/validation-runs")
    assert resp_runs.status_code == 200
    runs_data = resp_runs.json()
    assert runs_data["total"] >= 1
    assert len(runs_data["items"]) >= 1

    # 3. GET /api/v1/instruments/{id}/findings
    resp_findings = client.get(f"/api/v1/instruments/{instrument_a.id}/findings")
    assert resp_findings.status_code == 200
    assert "items" in resp_findings.json()

    # 4. Scoping: Institution User A sees own instrument runs
    set_auth_cookie(client, inst_user_a)
    resp_inst_a = client.get(f"/api/v1/instruments/{instrument_a.id}/validation-runs")
    assert resp_inst_a.status_code == 200

    # 5. Scoping: Institution User B cannot see Institution A's instrument runs or findings
    set_auth_cookie(client, inst_user_b)
    resp_cross_runs = client.get(f"/api/v1/instruments/{instrument_a.id}/validation-runs")
    assert resp_cross_runs.status_code == 403

    resp_cross_findings = client.get(f"/api/v1/instruments/{instrument_a.id}/findings")
    assert resp_cross_findings.status_code == 403


def test_api_finding_by_id_and_reevaluate(
    client: TestClient,
    db_session: Session,
    instrument_a: Instrument,
    officer_user: User,
    inst_user_a: User,
):
    # Create a finding directly
    instrument_a.amount = Decimal("-10.00")
    db_session.commit()
    run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)

    finding = db_session.scalar(
        select(ValidationFinding).where(
            ValidationFinding.instrument_id == instrument_a.id,
            ValidationFinding.rule_id == "VAL-AMT-001",
            ValidationFinding.status == "OPEN",
        )
    )
    assert finding is not None

    # GET /api/v1/findings/{id}
    set_auth_cookie(client, inst_user_a)
    resp = client.get(f"/api/v1/findings/{finding.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == finding.id

    # Correct amount and re-evaluate via POST /api/v1/findings/{id}/re-evaluate
    instrument_a.amount = Decimal("50000.00")
    db_session.commit()

    set_auth_cookie(client, officer_user)
    resp_re = client.post(f"/api/v1/findings/{finding.id}/re-evaluate")
    assert resp_re.status_code == 200
    assert resp_re.json()["status"] == FindingStatus.RESOLVED.value


def test_api_single_rule_evaluation(
    client: TestClient,
    instrument_a: Instrument,
    officer_user: User,
):
    set_auth_cookie(client, officer_user)
    # Evaluate valid registered rule
    resp = client.post(f"/api/v1/instruments/{instrument_a.id}/rules/VAL-AMT-001/evaluate")
    assert resp.status_code == 200
    assert resp.json()["rules_evaluated"] == ["VAL-AMT-001"]

    # Evaluate unregistered rule -> rejected with 404
    resp_unknown = client.post(f"/api/v1/instruments/{instrument_a.id}/rules/VAL-NONEXISTENT/evaluate")
    assert resp_unknown.status_code == 404


def test_api_invalid_request_handling(
    client: TestClient,
    instrument_a: Instrument,
    officer_user: User,
):
    set_auth_cookie(client, officer_user)
    # Invalid rule ID in list
    resp = client.post(
        f"/api/v1/instruments/{instrument_a.id}/validation-runs",
        json={"rule_ids": ["VAL-INVALID-999"]},
    )
    assert resp.status_code == 422

    # Invalid category
    resp_cat = client.post(
        f"/api/v1/instruments/{instrument_a.id}/validation-runs",
        json={"category": "INVALID_CATEGORY_NAME"},
    )
    assert resp_cat.status_code == 422

    # Invalid sort_by on findings
    resp_sort = client.get(
        f"/api/v1/instruments/{instrument_a.id}/findings?sort_by=malicious_col"
    )
    assert resp_sort.status_code == 422


# ---------------------------------------------------------------------------
# 9. Safety Assertions
# ---------------------------------------------------------------------------

def test_trust_level_immutability(db_session: Session, instrument_a: Instrument, officer_user: User):
    original_trust = instrument_a.trust_level
    original_status = instrument_a.status

    # Trigger validation
    run_validation(db=db_session, instrument_id=instrument_a.id, triggered_by_user_id=officer_user.id)

    db_session.refresh(instrument_a)
    assert instrument_a.trust_level == original_trust, "Trust level must never be modified by validation"
    assert instrument_a.status == original_status, "Instrument status must never be modified by validation"


def test_rule_exception_safety(db_session: Session, instrument_a: Instrument):
    # Rule raising unexpected error must return UNABLE_TO_EVALUATE without halting sweep
    class BrokenRule(BaseValidationRule):
        rule_id = "VAL-BROKEN-001"
        rule_version = "1.0"
        rule_type = RuleType.DETERMINISTIC
        category = FindingCategory.OTHER
        severity = RuleSeverity.LOW
        description = "Broken test rule"
        enabled = True

        def evaluate(self, context: RuleContext) -> RuleResult:
            raise RuntimeError("Simulated crash in rule evaluation")

    rule_registry.register(BrokenRule())

    try:
        run = run_validation(db=db_session, instrument_id=instrument_a.id, rule_ids=["VAL-BROKEN-001"])
        assert run["unable_to_evaluate_count"] == 1
        broken_outcomes = [o for o in run["outcomes"] if o["rule_id"] == "VAL-BROKEN-001"]
        assert len(broken_outcomes) == 1
        assert broken_outcomes[0]["outcome"] == RuleOutcome.UNABLE_TO_EVALUATE.value
        assert "Simulated crash" in broken_outcomes[0]["explanation"]
    finally:
        # Cleanup
        rule_registry._rules.pop("VAL-BROKEN-001", None)
