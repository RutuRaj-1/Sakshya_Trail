"""
Test Suite: Module 3 — Validation Engine Foundation
Tests cover all requirements from Prompt 1 Section 9:

1.  Rule registration and execution
2.  Valid and invalid rule definitions
3.  Rule version persistence
4.  Finding creation and retrieval
5.  Rejection of invalid statuses
6.  Evidence-link integrity
7.  Idempotent evaluation of the same input
8.  Preservation of previously detected findings
9.  Unknown/unconfigured policy behavior
10. Prevention of trust-level changes
11. Authorization integration through existing helpers
12. Migration from the previous working database state (schema presence test)
"""
import json
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
    compute_finding_fingerprint,
)
from app.modules.validation.engine import run_validation
from app.modules.validation.finding_service import (
    upsert_finding,
    resolve_finding_if_cleared,
    get_findings_for_instrument,
    dismiss_finding,
)
from app.modules.validation.policy_service import (
    set_policy_config,
    get_active_policy_config,
    build_policy_context,
)
from app.modules.auth.service import provision_user
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    ROLE_BRANCH_HEAD,
    create_access_token,
)
from app.core.config import settings
from app.common.exceptions import AppException


# ---------------------------------------------------------------------------
# Helper fixtures
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
def institution(db_session: Session) -> Institution:
    inst = Institution(
        code="1-VAL-TEST-01",
        legal_name="Validation Test Institute",
        display_name="VTI",
        institution_type="TECHNICAL_INSTITUTE",
        contact_name="Registrar VTI",
        contact_email="registrar@vti.ac.in",
        contact_phone="+91-11-20001111",
        address_line1="Test Campus",
        city="Pune",
        state="Maharashtra",
        postal_code="411001",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def valid_instrument(db_session: Session, institution: Institution) -> Instrument:
    """A healthy, valid instrument that should pass all deterministic rules."""
    inst = Instrument(
        institution_id=institution.id,
        instrument_type="FDR",
        bank_name="State Bank of India",
        branch="Pune Main Branch",
        reference_number="SBI-VAL-2026-001",
        amount=Decimal("5000000.00"),
        currency="INR",
        issue_date=date.today() - timedelta(days=30),
        maturity_date=date.today() + timedelta(days=365 * 5),
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
def expired_instrument(db_session: Session, institution: Institution) -> Instrument:
    """An instrument with a past maturity date in REGISTERED status."""
    inst = Instrument(
        institution_id=institution.id,
        instrument_type="FDR",
        bank_name="Punjab National Bank",
        branch="Mumbai Branch",
        reference_number="PNB-EXPIRED-2020",
        amount=Decimal("3000000.00"),
        currency="INR",
        issue_date=date(2019, 1, 1),
        maturity_date=date(2020, 1, 1),  # in the past
        lien_holder="AICTE Regulation Bureau",
        lien_marked=True,
        joint_with_aicte=True,
        status="REGISTERED",  # active status but expired date → FAIL
        trust_level="L0_DECLARED",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


@pytest.fixture
def admin_user(db_session: Session, institution: Institution) -> User:
    return provision_user(
        db=db_session,
        full_name="Validation Admin",
        email="val.admin@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SYSTEM_ADMIN,
    )


@pytest.fixture
def scrutiny_user(db_session: Session) -> User:
    return provision_user(
        db=db_session,
        full_name="Scrutiny Officer Val",
        email="val.scrutiny@aicte.gov.in",
        password="SecurePass@2026",
        role=ROLE_SCRUTINY_OFFICER,
    )


@pytest.fixture
def inst_user(db_session: Session, institution: Institution) -> User:
    return provision_user(
        db=db_session,
        full_name="Institution Val User",
        email="val.inst@vti.ac.in",
        password="SecurePass@2026",
        role=ROLE_INSTITUTION_USER,
        institution_id=institution.id,
    )


# ---------------------------------------------------------------------------
# Helper: build a minimal RuleContext from an instrument
# ---------------------------------------------------------------------------

def make_context(
    instrument: Instrument,
    institution: Institution,
    policy: Optional[dict] = None,
) -> RuleContext:
    return RuleContext(
        instrument_id=instrument.id,
        institution_id=institution.id,
        instrument_status=instrument.status,
        instrument_trust_level=instrument.trust_level,
        instrument_type=instrument.instrument_type,
        bank_name=instrument.bank_name,
        reference_number=instrument.reference_number,
        amount_decimal=instrument.amount,
        currency=instrument.currency,
        issue_date=instrument.issue_date,
        maturity_date=instrument.maturity_date,
        lien_holder=instrument.lien_holder,
        lien_marked=instrument.lien_marked,
        joint_with_aicte=instrument.joint_with_aicte,
        institution_is_active=institution.is_active,
        institution_type=institution.institution_type,
        available_documents=[],
        policy=policy or {"_duplicate_sibling_count": 0, "_duplicate_sibling_ids": []},
    )


# ===========================================================================
# 1. Rule registration and execution
# ===========================================================================

class TestRuleRegistrationAndExecution:
    def test_registry_has_expected_rules(self):
        """All rules defined in the rules package must be registered."""
        rule_ids = [r["rule_id"] for r in rule_registry.list_all()]
        assert "VAL-DATE-001" in rule_ids
        assert "VAL-DATE-002" in rule_ids
        assert "VAL-AMT-001" in rule_ids
        assert "VAL-AMT-002" in rule_ids
        assert "VAL-REF-001" in rule_ids
        assert "VAL-LIEN-001" in rule_ids
        assert "VAL-DOC-001" in rule_ids
        assert "VAL-DUP-001" in rule_ids

    def test_enabled_rules_are_returned(self):
        enabled = rule_registry.get_enabled_rules()
        assert len(enabled) >= 7
        for r in enabled:
            assert r.enabled is True

    def test_rule_execution_returns_result(
        self, db_session: Session, valid_instrument: Instrument, institution: Institution
    ):
        rule = rule_registry.get("VAL-DATE-001")
        assert rule is not None
        ctx = make_context(valid_instrument, institution)
        result = rule.evaluate(ctx)
        assert isinstance(result, RuleResult)
        assert result.rule_id == "VAL-DATE-001"
        assert result.outcome == RuleOutcome.PASS

    def test_expired_instrument_fails_date_rule(
        self, db_session: Session, expired_instrument: Instrument, institution: Institution
    ):
        rule = rule_registry.get("VAL-DATE-002")
        ctx = make_context(expired_instrument, institution)
        result = rule.evaluate(ctx)
        assert result.outcome == RuleOutcome.FAIL
        assert "maturity" in result.title.lower() or "expired" in result.explanation.lower()


# ===========================================================================
# 2. Valid and invalid rule definitions
# ===========================================================================

class TestRuleDefinitions:
    def test_rule_without_id_raises_on_register(self):
        class NoIdRule(BaseValidationRule):
            rule_id = ""  # invalid
            def evaluate(self, context):
                return self._pass()

        import copy
        from app.modules.validation.registry import RuleRegistry
        fresh_registry = RuleRegistry()
        with pytest.raises(ValueError, match="no rule_id"):
            fresh_registry.register(NoIdRule())

    def test_duplicate_rule_id_raises(self):
        from app.modules.validation.registry import RuleRegistry
        fresh_registry = RuleRegistry()

        class RuleA(BaseValidationRule):
            rule_id = "TEST-DUP-001"
            def evaluate(self, c): return self._pass()

        class RuleB(BaseValidationRule):
            rule_id = "TEST-DUP-001"
            def evaluate(self, c): return self._pass()

        fresh_registry.register(RuleA())
        with pytest.raises(ValueError, match="Duplicate rule_id"):
            fresh_registry.register(RuleB())

    def test_heuristic_rule_title_has_advisory_prefix(
        self, db_session: Session, valid_instrument: Instrument, institution: Institution
    ):
        """Heuristic (advisory) findings must carry the advisory prefix."""
        rule = rule_registry.get("VAL-DUP-001")
        ctx = make_context(
            valid_instrument,
            institution,
            policy={
                "_duplicate_sibling_count": 2,
                "_duplicate_sibling_ids": ["fake-id-1", "fake-id-2"],
            },
        )
        result = rule.evaluate(ctx)
        assert result.outcome == RuleOutcome.WARNING
        assert "[Advisory" in result.title, (
            "Heuristic rule findings must start with '[Advisory — human review required]'"
        )


# ===========================================================================
# 3. Rule version persistence
# ===========================================================================

class TestRuleVersionPersistence:
    def test_finding_stores_rule_version(
        self, db_session: Session, valid_instrument: Instrument, institution: Institution
    ):
        from app.modules.validation.rules.date_rules import MaturityAfterIssueDateRule
        import copy

        # Simulate an instrument with invalid dates to force a FAIL
        bad_instrument = Instrument(
            institution_id=institution.id,
            instrument_type="FDR",
            bank_name="Test Bank Version",
            reference_number="VERS-TEST-001",
            amount=Decimal("1000000.00"),
            currency="INR",
            issue_date=date(2026, 6, 1),
            maturity_date=date(2026, 5, 1),  # before issue — invalid
            lien_marked=True,
            lien_holder="AICTE",
            status="REGISTERED",
            trust_level="L0_DECLARED",
        )
        db_session.add(bad_instrument)
        db_session.commit()
        db_session.refresh(bad_instrument)

        rule = rule_registry.get("VAL-DATE-001")
        ctx = make_context(bad_instrument, institution)
        result = rule.evaluate(ctx)
        assert result.outcome == RuleOutcome.FAIL

        finding = upsert_finding(
            db=db_session,
            instrument_id=bad_instrument.id,
            institution_id=institution.id,
            rule_result=result,
        )
        assert finding is not None
        assert finding.rule_version == rule.rule_version
        assert finding.rule_id == "VAL-DATE-001"


# ===========================================================================
# 4. Finding creation and retrieval
# ===========================================================================

class TestFindingCreationAndRetrieval:
    def test_create_and_retrieve_finding(
        self, db_session: Session, expired_instrument: Instrument, institution: Institution
    ):
        rule = rule_registry.get("VAL-DATE-002")
        ctx = make_context(expired_instrument, institution)
        result = rule.evaluate(ctx)
        assert result.is_finding

        finding = upsert_finding(
            db=db_session,
            instrument_id=expired_instrument.id,
            institution_id=institution.id,
            rule_result=result,
        )
        assert finding is not None
        assert finding.instrument_id == expired_instrument.id
        assert finding.status == FindingStatus.OPEN.value

        # Retrieve
        findings = get_findings_for_instrument(db_session, expired_instrument.id)
        assert any(f.id == finding.id for f in findings)

    def test_finding_has_all_required_fields(
        self, db_session: Session, expired_instrument: Instrument, institution: Institution
    ):
        rule = rule_registry.get("VAL-DATE-002")
        ctx = make_context(expired_instrument, institution)
        result = rule.evaluate(ctx)

        finding = upsert_finding(
            db=db_session,
            instrument_id=expired_instrument.id,
            institution_id=institution.id,
            rule_result=result,
        )
        assert finding.finding_fingerprint
        assert finding.rule_id
        assert finding.rule_version
        assert finding.severity
        assert finding.category
        assert finding.title
        assert finding.first_detected_at is not None
        assert finding.last_evaluated_at is not None


# ===========================================================================
# 5. Rejection of invalid finding statuses
# ===========================================================================

class TestFindingStatusValidation:
    def test_cannot_dismiss_already_dismissed_finding(
        self, db_session: Session, expired_instrument: Instrument, institution: Institution
    ):
        rule = rule_registry.get("VAL-DATE-002")
        ctx = make_context(expired_instrument, institution)
        result = rule.evaluate(ctx)
        finding = upsert_finding(
            db=db_session,
            instrument_id=expired_instrument.id,
            institution_id=institution.id,
            rule_result=result,
        )
        # First dismissal
        dismiss_finding(db_session, finding, "user-1", "Legitimate reason for first dismissal")

        # Second dismissal should raise
        with pytest.raises(AppException) as exc_info:
            dismiss_finding(db_session, finding, "user-1", "Second attempt")
        assert "terminal status" in str(exc_info.value.message).lower()

    def test_status_strings_are_valid_enum_values(self):
        for status in FindingStatus:
            assert status.value in {"OPEN", "IN_REVIEW", "DISMISSED", "RESOLVED", "SUPERSEDED"}

    def test_finding_status_distinct_from_instrument_status(self):
        """Finding status values must not overlap with instrument administrative status values."""
        instrument_statuses = {"DRAFT", "REGISTERED", "SUBMITTED", "RELEASED", "CANCELLED"}
        finding_statuses = {s.value for s in FindingStatus}
        overlap = instrument_statuses & finding_statuses
        assert not overlap, (
            f"Finding statuses should not overlap with instrument statuses. Overlap: {overlap}"
        )


# ===========================================================================
# 6. Evidence-link integrity
# ===========================================================================

class TestEvidenceLinkIntegrity:
    def test_evidence_refs_stored_as_json(
        self, db_session: Session, expired_instrument: Instrument, institution: Institution
    ):
        rule = rule_registry.get("VAL-DATE-002")
        ctx = make_context(expired_instrument, institution)
        result = rule.evaluate(ctx)
        result.evidence_refs = ["fake-doc-version-id-123"]

        finding = upsert_finding(
            db=db_session,
            instrument_id=expired_instrument.id,
            institution_id=institution.id,
            rule_result=result,
        )
        assert finding.evidence_refs_json is not None
        parsed = json.loads(finding.evidence_refs_json)
        assert "fake-doc-version-id-123" in parsed

    def test_evidence_refs_property_returns_list(
        self, db_session: Session, expired_instrument: Instrument, institution: Institution
    ):
        rule = rule_registry.get("VAL-DATE-002")
        ctx = make_context(expired_instrument, institution)
        result = rule.evaluate(ctx)
        finding = upsert_finding(
            db=db_session,
            instrument_id=expired_instrument.id,
            institution_id=institution.id,
            rule_result=result,
        )
        assert isinstance(finding.evidence_refs, list)


# ===========================================================================
# 7. Idempotent evaluation of the same input
# ===========================================================================

class TestIdempotentEvaluation:
    def test_same_rule_same_input_produces_one_finding(
        self, db_session: Session, expired_instrument: Instrument, institution: Institution
    ):
        """Running the same rule twice on unchanged input must not create duplicate findings."""
        rule = rule_registry.get("VAL-DATE-002")
        ctx = make_context(expired_instrument, institution)

        result1 = rule.evaluate(ctx)
        result2 = rule.evaluate(ctx)

        finding1 = upsert_finding(
            db=db_session,
            instrument_id=expired_instrument.id,
            institution_id=institution.id,
            rule_result=result1,
        )
        finding2 = upsert_finding(
            db=db_session,
            instrument_id=expired_instrument.id,
            institution_id=institution.id,
            rule_result=result2,
        )

        # Should be the same finding record (upsert)
        assert finding1.id == finding2.id

        # Only one open finding for this rule
        findings = get_findings_for_instrument(
            db_session,
            expired_instrument.id,
            status_filter=["OPEN"],
        )
        rule_findings = [f for f in findings if f.rule_id == "VAL-DATE-002"]
        assert len(rule_findings) == 1


# ===========================================================================
# 8. Preservation of previously detected findings
# ===========================================================================

class TestFindingPreservation:
    def test_resolved_finding_is_preserved_not_deleted(
        self, db_session: Session, institution: Institution
    ):
        """When a rule clears, the finding must be RESOLVED (not deleted)."""
        # Create a "bad" instrument (expired)
        bad_inst = Instrument(
            institution_id=institution.id,
            instrument_type="FDR",
            bank_name="Preservation Bank",
            reference_number="PRES-001",
            amount=Decimal("1000000.00"),
            currency="INR",
            issue_date=date(2019, 1, 1),
            maturity_date=date(2020, 1, 1),
            lien_marked=True,
            lien_holder="AICTE",
            status="REGISTERED",
            trust_level="L0_DECLARED",
        )
        db_session.add(bad_inst)
        db_session.commit()
        db_session.refresh(bad_inst)

        ctx = make_context(bad_inst, institution)
        rule = rule_registry.get("VAL-DATE-002")
        result = rule.evaluate(ctx)
        assert result.is_finding

        finding = upsert_finding(
            db=db_session,
            instrument_id=bad_inst.id,
            institution_id=institution.id,
            rule_result=result,
        )
        original_id = finding.id
        assert finding.status == FindingStatus.OPEN.value

        # Simulate rule clearing (instrument corrected)
        resolved_count = resolve_finding_if_cleared(
            db=db_session,
            instrument_id=bad_inst.id,
            rule_id="VAL-DATE-002",
            rule_version=rule.rule_version,
            fingerprint_key=result.fingerprint_key,
            resolution_note="Condition cleared.",
        )
        assert resolved_count == 1

        # Finding still exists in DB — just marked RESOLVED
        preserved = db_session.scalar(
            select(ValidationFinding).where(ValidationFinding.id == original_id)
        )
        assert preserved is not None
        assert preserved.status == FindingStatus.RESOLVED.value
        assert preserved.resolved_at is not None

    def test_superseded_finding_is_preserved(
        self, db_session: Session, institution: Institution
    ):
        """When a new rule version fires, the old finding is superseded, not deleted."""
        bad_inst = Instrument(
            institution_id=institution.id,
            instrument_type="FDR",
            bank_name="Supersede Bank",
            reference_number="SUPER-001",
            amount=Decimal("1000000.00"),
            currency="INR",
            issue_date=date(2019, 1, 1),
            maturity_date=date(2020, 1, 1),
            lien_marked=True,
            lien_holder="AICTE",
            status="REGISTERED",
            trust_level="L0_DECLARED",
        )
        db_session.add(bad_inst)
        db_session.commit()
        db_session.refresh(bad_inst)

        ctx = make_context(bad_inst, institution)
        rule = rule_registry.get("VAL-DATE-002")

        # First version result
        result_v1 = rule.evaluate(ctx)
        result_v1.rule_version = "1.0"
        finding_v1 = upsert_finding(
            db=db_session,
            instrument_id=bad_inst.id,
            institution_id=institution.id,
            rule_result=result_v1,
        )

        # New version result (different version string)
        result_v2 = rule.evaluate(ctx)
        result_v2.rule_version = "2.0"
        finding_v2 = upsert_finding(
            db=db_session,
            instrument_id=bad_inst.id,
            institution_id=institution.id,
            rule_result=result_v2,
        )

        # Old finding must be SUPERSEDED, not deleted
        db_session.refresh(finding_v1)
        assert finding_v1.status == FindingStatus.SUPERSEDED.value
        assert finding_v2.id != finding_v1.id


# ===========================================================================
# 9. Unknown / unconfigured policy behavior
# ===========================================================================

class TestUnconfiguredPolicy:
    def test_amount_policy_rule_returns_unable_without_config(
        self, db_session: Session, valid_instrument: Instrument, institution: Institution
    ):
        """VAL-AMT-002 must return UNABLE_TO_EVALUATE when no MIN_DEPOSIT_AMOUNT_INR is set."""
        rule = rule_registry.get("VAL-AMT-002")
        # Policy has no MIN_DEPOSIT_AMOUNT_INR key
        ctx = make_context(
            valid_instrument,
            institution,
            policy={"_duplicate_sibling_count": 0},
        )
        result = rule.evaluate(ctx)
        assert result.outcome == RuleOutcome.UNABLE_TO_EVALUATE
        assert "no active, approved policy value" in result.explanation.lower() or \
               "unavailable" in result.explanation.lower()

    def test_amount_policy_rule_passes_when_config_set(
        self, db_session: Session, valid_instrument: Instrument, institution: Institution
    ):
        """VAL-AMT-002 must evaluate correctly when policy is configured."""
        rule = rule_registry.get("VAL-AMT-002")
        ctx = make_context(
            valid_instrument,
            institution,
            policy={
                "_duplicate_sibling_count": 0,
                "MIN_DEPOSIT_AMOUNT_INR": Decimal("1000000.00"),  # well below 5M
                "_policy_version_ref": "MIN_DEPOSIT_AMOUNT_INR:v1",
            },
        )
        result = rule.evaluate(ctx)
        assert result.outcome == RuleOutcome.PASS

    def test_policy_config_set_and_retrieve(
        self, db_session: Session, institution: Institution
    ):
        """Policy must be storable, versionable, and retrievable."""
        admin_id = "test-admin-user-id"
        cfg = set_policy_config(
            db=db_session,
            config_key="MIN_DEPOSIT_AMOUNT_INR",
            config_value="500000.00",
            value_type="decimal",
            display_name="Minimum Deposit Amount (INR)",
            authorized_by_user_id=admin_id,
            institution_id=institution.id,
        )
        assert cfg.policy_version == 1
        assert cfg.is_active is True

        # Update to version 2
        cfg2 = set_policy_config(
            db=db_session,
            config_key="MIN_DEPOSIT_AMOUNT_INR",
            config_value="1000000.00",
            value_type="decimal",
            display_name="Minimum Deposit Amount (INR)",
            authorized_by_user_id=admin_id,
            institution_id=institution.id,
        )
        assert cfg2.policy_version == 2

        # Old version should be deactivated
        db_session.refresh(cfg)
        assert cfg.is_active is False

        # Active retrieve returns v2
        active = get_active_policy_config(
            db_session, "MIN_DEPOSIT_AMOUNT_INR", institution_id=institution.id
        )
        assert active is not None
        assert active.policy_version == 2


# ===========================================================================
# 10. Prevention of trust-level changes
# ===========================================================================

class TestTrustLevelProtection:
    def test_validation_run_does_not_change_trust_level(
        self,
        db_session: Session,
        valid_instrument: Instrument,
        institution: Institution,
        client: TestClient,
        admin_user: User,
    ):
        """Running validation MUST NOT modify Instrument.trust_level."""
        original_trust_level = valid_instrument.trust_level
        assert original_trust_level == "L0_DECLARED"

        result = run_validation(
            db=db_session,
            instrument_id=valid_instrument.id,
        )

        # Reload instrument from DB
        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Instrument).where(Instrument.id == valid_instrument.id)
        )
        assert refreshed.trust_level == original_trust_level, (
            f"trust_level changed from {original_trust_level} to {refreshed.trust_level} "
            "— validation MUST NOT modify trust level"
        )

    def test_api_validation_endpoint_does_not_change_trust_level(
        self,
        client: TestClient,
        db_session: Session,
        valid_instrument: Instrument,
        admin_user: User,
    ):
        """Calling the API run endpoint must not alter trust_level."""
        set_auth_cookie(client, admin_user)
        original_tl = valid_instrument.trust_level

        res = client.post(
            f"/api/v1/validation/instruments/{valid_instrument.id}/run",
            json={"rule_ids": None},
        )
        assert res.status_code == 200

        db_session.expire_all()
        refreshed = db_session.scalar(
            select(Instrument).where(Instrument.id == valid_instrument.id)
        )
        assert refreshed.trust_level == original_tl


# ===========================================================================
# 11. Authorization integration
# ===========================================================================

class TestAuthorizationIntegration:
    def test_institution_user_cannot_trigger_validation(
        self,
        client: TestClient,
        db_session: Session,
        valid_instrument: Instrument,
        inst_user: User,
    ):
        """INSTITUTION_USER is not permitted to trigger validation runs."""
        set_auth_cookie(client, inst_user)
        res = client.post(
            f"/api/v1/validation/instruments/{valid_instrument.id}/run",
            json={},
        )
        assert res.status_code == 403

    def test_auditor_can_read_findings_not_trigger(
        self,
        client: TestClient,
        db_session: Session,
        valid_instrument: Instrument,
    ):
        """AUDITOR can read findings (GET) but cannot trigger validation runs (POST)."""
        auditor = provision_user(
            db=db_session,
            full_name="Auditor Val",
            email="auditor.val@aicte.gov.in",
            password="SecurePass@2026",
            role=ROLE_AUDITOR,
        )
        set_auth_cookie(client, auditor)

        # GET findings: should succeed
        get_res = client.get(
            f"/api/v1/validation/instruments/{valid_instrument.id}/findings"
        )
        assert get_res.status_code == 200

        # POST run: should be forbidden
        run_res = client.post(
            f"/api/v1/validation/instruments/{valid_instrument.id}/run",
            json={},
        )
        assert run_res.status_code == 403

    def test_institution_user_cannot_see_other_institution_findings(
        self,
        client: TestClient,
        db_session: Session,
        institution: Institution,
        inst_user: User,
    ):
        """INSTITUTION_USER must not access findings for another institution's instrument."""
        # Create a second institution and instrument
        other_inst = Institution(
            code="1-OTHER-VAL-02",
            legal_name="Other Validation Institute",
            contact_name="Dean Other",
            contact_email="dean@other-val.ac.in",
            contact_phone="+91-11-30001111",
            address_line1="Other Street",
            city="Delhi",
            state="Delhi",
            postal_code="110001",
            is_active=True,
        )
        db_session.add(other_inst)
        db_session.commit()
        db_session.refresh(other_inst)

        other_instrument = Instrument(
            institution_id=other_inst.id,
            instrument_type="FDR",
            bank_name="Other Bank",
            reference_number="OTHER-REF-001",
            amount=Decimal("2000000.00"),
            currency="INR",
            issue_date=date.today() - timedelta(days=10),
            maturity_date=date.today() + timedelta(days=365),
            lien_marked=True,
            lien_holder="AICTE",
            status="REGISTERED",
            trust_level="L0_DECLARED",
        )
        db_session.add(other_instrument)
        db_session.commit()
        db_session.refresh(other_instrument)

        set_auth_cookie(client, inst_user)
        res = client.get(
            f"/api/v1/validation/instruments/{other_instrument.id}/findings"
        )
        assert res.status_code == 403

    def test_only_admin_can_write_policy(
        self,
        client: TestClient,
        db_session: Session,
        scrutiny_user: User,
    ):
        """Only SYSTEM_ADMIN may write policy configuration."""
        set_auth_cookie(client, scrutiny_user)
        res = client.post(
            "/api/v1/validation/policy",
            json={
                "config_key": "MIN_DEPOSIT_AMOUNT_INR",
                "config_value": "500000.00",
                "value_type": "decimal",
                "display_name": "Min Deposit",
            },
        )
        assert res.status_code == 403

    def test_admin_can_write_and_scrutiny_can_read_policy(
        self,
        client: TestClient,
        db_session: Session,
        admin_user: User,
        scrutiny_user: User,
    ):
        """SYSTEM_ADMIN may write policy; SCRUTINY_OFFICER may read it."""
        set_auth_cookie(client, admin_user)
        write_res = client.post(
            "/api/v1/validation/policy",
            json={
                "config_key": "MIN_VALIDITY_DAYS",
                "config_value": "365",
                "value_type": "integer",
                "display_name": "Minimum Validity Period (days)",
            },
        )
        assert write_res.status_code == 201

        set_auth_cookie(client, scrutiny_user)
        read_res = client.get("/api/v1/validation/policy")
        assert read_res.status_code == 200
        keys = [c["config_key"] for c in read_res.json()]
        assert "MIN_VALIDITY_DAYS" in keys

    def test_unauthenticated_cannot_access_findings(
        self,
        client: TestClient,
        valid_instrument: Instrument,
    ):
        client.cookies.clear()
        res = client.get(
            f"/api/v1/validation/instruments/{valid_instrument.id}/findings"
        )
        assert res.status_code == 401


# ===========================================================================
# 12. Migration — schema presence
# ===========================================================================

class TestMigrationSchemaPresence:
    def test_validation_tables_exist(self, db_session: Session):
        """Verify all three Module 3 tables are present in the test database."""
        from sqlalchemy import inspect
        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()
        assert "validation_findings" in tables
        assert "validation_policy_configs" in tables
        assert "validation_runs" in tables

    def test_previous_module_tables_still_exist(self, db_session: Session):
        """Module 1 and 2 tables must be preserved after Module 3 migration."""
        from sqlalchemy import inspect
        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()
        for expected in [
            "institutions", "users", "instruments", "audit_events",
            "documents", "document_versions", "document_categories",
        ]:
            assert expected in tables, f"Module 1/2 table '{expected}' is missing after Module 3 migration"

    def test_finding_fingerprint_index_exists(self, db_session: Session):
        """finding_fingerprint must be indexed for efficient deduplication queries."""
        from sqlalchemy import inspect
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes("validation_findings")
        index_cols = [
            col
            for idx in indexes
            for col in idx["column_names"]
        ]
        assert "finding_fingerprint" in index_cols


# ===========================================================================
# Full engine integration tests
# ===========================================================================

class TestEngineIntegration:
    def test_full_run_returns_structured_results(
        self, db_session: Session, valid_instrument: Instrument
    ):
        result = run_validation(db=db_session, instrument_id=valid_instrument.id)
        assert "run_id" in result
        assert "outcomes" in result
        assert isinstance(result["outcomes"], list)
        assert len(result["outcomes"]) >= 7
        assert "summary" in result
        for outcome_key in ["PASS", "FAIL", "WARNING", "NOT_APPLICABLE", "UNABLE_TO_EVALUATE"]:
            assert outcome_key in result["summary"]

    def test_full_run_on_expired_instrument_creates_finding(
        self, db_session: Session, expired_instrument: Instrument
    ):
        run_validation(db=db_session, instrument_id=expired_instrument.id)
        findings = get_findings_for_instrument(db_session, expired_instrument.id)
        assert len(findings) >= 1
        rule_ids = [f.rule_id for f in findings]
        assert "VAL-DATE-002" in rule_ids

    def test_run_log_is_created(
        self, db_session: Session, valid_instrument: Instrument
    ):
        result = run_validation(db=db_session, instrument_id=valid_instrument.id)
        run = db_session.scalar(
            select(ValidationRun).where(ValidationRun.id == result["run_id"])
        )
        assert run is not None
        assert run.instrument_id == valid_instrument.id
        assert run.run_status == "COMPLETED"

    def test_unknown_instrument_raises_404(self, db_session: Session):
        from app.common.exceptions import NotFoundException
        with pytest.raises(NotFoundException):
            run_validation(db=db_session, instrument_id="00000000-0000-0000-0000-000000000000")

    def test_rule_ids_filter_restricts_execution(
        self, db_session: Session, valid_instrument: Instrument
    ):
        """Selective rule execution must only run the specified rules."""
        result = run_validation(
            db=db_session,
            instrument_id=valid_instrument.id,
            rule_ids=["VAL-DATE-001"],
        )
        assert len(result["outcomes"]) == 1
        assert result["outcomes"][0]["rule_id"] == "VAL-DATE-001"

    def test_fingerprint_computation_is_deterministic(self):
        """Same inputs must always produce the same fingerprint."""
        fp1 = compute_finding_fingerprint("inst-1", "VAL-DATE-001", "1.0", "test-key")
        fp2 = compute_finding_fingerprint("inst-1", "VAL-DATE-001", "1.0", "test-key")
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA-256 hex

    def test_different_inputs_produce_different_fingerprints(self):
        fp1 = compute_finding_fingerprint("inst-1", "VAL-DATE-001", "1.0", "key-a")
        fp2 = compute_finding_fingerprint("inst-1", "VAL-DATE-001", "1.0", "key-b")
        assert fp1 != fp2


# ===========================================================================
# API-level integration tests
# ===========================================================================

class TestAPIEndpoints:
    def test_run_validation_api(
        self,
        client: TestClient,
        db_session: Session,
        valid_instrument: Instrument,
        admin_user: User,
    ):
        set_auth_cookie(client, admin_user)
        res = client.post(
            f"/api/v1/validation/instruments/{valid_instrument.id}/run",
            json={},
        )
        assert res.status_code == 200
        data = res.json()
        assert "run_id" in data
        assert "outcomes" in data
        assert "summary" in data

    def test_list_findings_api(
        self,
        client: TestClient,
        db_session: Session,
        expired_instrument: Instrument,
        admin_user: User,
    ):
        set_auth_cookie(client, admin_user)
        # Create a finding first
        client.post(
            f"/api/v1/validation/instruments/{expired_instrument.id}/run",
            json={},
        )
        res = client.get(
            f"/api/v1/validation/instruments/{expired_instrument.id}/findings"
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data

    def test_list_rules_api(
        self,
        client: TestClient,
        admin_user: User,
    ):
        set_auth_cookie(client, admin_user)
        res = client.get("/api/v1/validation/rules")
        assert res.status_code == 200
        rules = res.json()
        assert isinstance(rules, list)
        rule_ids = [r["rule_id"] for r in rules]
        assert "VAL-DATE-001" in rule_ids

    def test_dismiss_finding_api(
        self,
        client: TestClient,
        db_session: Session,
        expired_instrument: Instrument,
        scrutiny_user: User,
        admin_user: User,
    ):
        # Admin creates findings
        set_auth_cookie(client, admin_user)
        client.post(
            f"/api/v1/validation/instruments/{expired_instrument.id}/run",
            json={},
        )
        findings_res = client.get(
            f"/api/v1/validation/instruments/{expired_instrument.id}/findings?status=OPEN"
        )
        findings = findings_res.json()["items"]
        if not findings:
            pytest.skip("No OPEN findings to dismiss")

        finding_id = findings[0]["id"]

        # Scrutiny officer dismisses
        set_auth_cookie(client, scrutiny_user)
        dismiss_res = client.post(
            f"/api/v1/validation/instruments/{expired_instrument.id}/findings/{finding_id}/dismiss",
            json={"reason": "Verified with institution — this is a historical record."},
        )
        assert dismiss_res.status_code == 200
        assert dismiss_res.json()["status"] == "DISMISSED"
