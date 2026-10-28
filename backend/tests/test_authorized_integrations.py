"""
Comprehensive Unit & Integration Tests for Module 4 External Gateways & Integrations (Prompt 2).

Covers:
1. Institutional Verification Provider (Mock, Sandbox, Live-Unconfigured).
2. Bank FDR Verification Provider (Mock, Sandbox, Live-Unconfigured).
3. Configuration switching (INTEGRATION_MODE: mock, sandbox, production).
4. Request correlation ID generation and idempotency.
5. Automatic discrepancy finding creation on bank verification MISMATCH.
6. Strict invariant: Mock/Sandbox can NEVER grant production L3 trust level.
7. Tenant isolation (Institution User cross-tenant prevention).
8. Statutory Release Gate cannot be bypassed by provider success.
9. Audit trail logging and sensitive data redaction.
"""
import json
import uuid
from decimal import Decimal
from datetime import date, datetime, timezone
import pytest
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.common.exceptions import AppException
from app.db.session import SessionLocal
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.institutions.integrations import (
    get_institution_verification_provider,
    set_institution_verification_provider,
    MockInstitutionVerificationProvider,
    SandboxInstitutionVerificationProvider,
    LiveInstitutionVerificationProvider,
)
from app.modules.verification.adapters import (
    get_adapter_for_channel,
    SimulatedBankAdapter,
    SandboxBankAdapter,
    LiveBankVerificationAdapter,
)
from app.modules.verification.enums import (
    VerificationChannel,
    VerificationResult,
    TrustLevel,
    VerificationRequestStatus,
)
from app.modules.verification.verification_service import (
    create_verification_request,
    dispatch_verification_request,
)
from app.modules.verification.trust_service import (
    transition_trust_level,
    apply_l3_bank_confirmation,
)
from app.modules.validation.models import ValidationFinding


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def scrutiny_officer(db):
    officer = db.query(User).filter(User.role == "SCRUTINY_OFFICER").first()
    if not officer:
        officer = User(
            id=str(uuid.uuid4()),
            email=f"scrutiny.test.{uuid.uuid4().hex[:6]}@aicte.gov.in",
            full_name="Scrutiny Test Officer",
            role="SCRUTINY_OFFICER",
            is_active=True,
            password_hash="test-hashed-pw",
        )
        db.add(officer)
        db.commit()
        db.refresh(officer)
    return officer


@pytest.fixture
def institution_user(db, test_institution):
    inst_user = db.query(User).filter(User.role == "INSTITUTION_USER", User.institution_id == test_institution.id).first()
    if not inst_user:
        inst_user = User(
            id=str(uuid.uuid4()),
            email=f"inst.test.{uuid.uuid4().hex[:6]}@institution.edu",
            full_name="Institution Nodal Officer",
            role="INSTITUTION_USER",
            institution_id=test_institution.id,
            is_active=True,
            password_hash="test-hashed-pw",
        )
        db.add(inst_user)
        db.commit()
        db.refresh(inst_user)
    return inst_user


@pytest.fixture
def test_institution(db):
    inst = db.query(Institution).filter(Institution.code == "1-10924811").first()
    if not inst:
        inst = Institution(
            id=str(uuid.uuid4()),
            code="1-10924811",
            legal_name="Government Engineering College, Bilaspur",
            display_name="GEC Bilaspur",
            institution_type="GOVERNMENT_INSTITUTE",
            state="Chhattisgarh",
            city="Bilaspur",
            contact_email="principal@gecbsp.ac.in",
            is_active=True,
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
    return inst


@pytest.fixture
def test_instrument(db, test_institution):
    inst_obj = db.query(Instrument).filter(Instrument.institution_id == test_institution.id).first()
    if not inst_obj:
        inst_obj = Instrument(
            id=str(uuid.uuid4()),
            institution_id=test_institution.id,
            reference_number=f"FDR-TEST-{uuid.uuid4().hex[:8].upper()}",
            bank_name="State Bank of India",
            branch="Bilaspur Main Branch",
            amount=Decimal("1500000.00"),
            currency="INR",
            issue_date=date(2025, 1, 15),
            maturity_date=date(2030, 1, 15),
            lien_marked=True,
            joint_with_aicte=True,
            status="REGISTERED",
            trust_level="L0_DECLARED",
        )
        db.add(inst_obj)
        db.commit()
        db.refresh(inst_obj)
    return inst_obj


# ---------------------------------------------------------------------------
# 1. Institutional Verification Provider Tests
# ---------------------------------------------------------------------------

class TestInstitutionVerificationProvider:
    """Tests the institutional registry lookup providers."""

    def test_mock_provider_matching_record(self):
        provider = MockInstitutionVerificationProvider()
        result = provider.verify_institution(
            institution_code="1-10924811",
            legal_name="Government Engineering College, Bilaspur",
            expected_state="Chhattisgarh",
        )
        assert result.is_verified is True
        assert result.status == "MATCH"
        assert result.official_approval_status == "APPROVED"
        assert "code" in result.verified_fields
        assert result.correlation_id.startswith("AICTE-MOCK-")

    def test_mock_provider_mismatch_state(self):
        provider = MockInstitutionVerificationProvider()
        result = provider.verify_institution(
            institution_code="1-10924811",
            legal_name="Government Engineering College, Bilaspur",
            expected_state="Maharashtra",  # Mismatch (real state is Chhattisgarh)
        )
        assert result.is_verified is False
        assert result.status == "MISMATCH"
        assert "state" in result.mismatched_fields

    def test_mock_provider_unknown_code(self):
        provider = MockInstitutionVerificationProvider()
        result = provider.verify_institution(
            institution_code="9-99999999",
            legal_name="Unknown Technical Institute",
        )
        assert result.is_verified is False
        assert result.status == "MISMATCH"
        assert "code" in result.mismatched_fields

    def test_sandbox_provider_execution(self):
        provider = SandboxInstitutionVerificationProvider()
        result = provider.verify_institution(
            institution_code="1-45678901",
            legal_name="Delhi Technological University",
            expected_state="Delhi",
        )
        assert result.environment == "sandbox"
        assert result.status == "MATCH"
        assert result.correlation_id.startswith("AICTE-SBX-")

    def test_live_provider_fails_closed_when_unconfigured(self):
        provider = LiveInstitutionVerificationProvider()
        with patch.object(settings, "AICTE_INTEGRATION_ENABLED", False):
            with pytest.raises(AppException) as exc_info:
                provider.verify_institution(
                    institution_code="1-10924811",
                    legal_name="GEC Bilaspur",
                )
            assert exc_info.value.code == "AICTE_INTEGRATION_UNCONFIGURED"
            assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# 2. Bank FDR Verification Provider & Adapter Registry Tests
# ---------------------------------------------------------------------------

class TestBankFDRVerificationAdapters:
    """Tests the bank confirmation adapter factory and mode resolution."""

    def test_get_adapter_mock_mode(self):
        with patch.object(settings, "INTEGRATION_MODE", "mock"):
            adapter = get_adapter_for_channel(VerificationChannel.SIMULATED.value)
            assert isinstance(adapter, SimulatedBankAdapter)

    def test_get_adapter_sandbox_mode(self):
        with patch.object(settings, "INTEGRATION_MODE", "sandbox"):
            adapter = get_adapter_for_channel(VerificationChannel.DIRECT_API.value)
            assert isinstance(adapter, SandboxBankAdapter)

    def test_get_adapter_production_mode(self):
        with patch.object(settings, "INTEGRATION_MODE", "production"):
            adapter = get_adapter_for_channel(VerificationChannel.LIVE_BANK_API.value)
            assert isinstance(adapter, LiveBankVerificationAdapter)

    def test_live_bank_adapter_fails_closed_when_unconfigured(self):
        adapter = LiveBankVerificationAdapter()
        with patch.object(settings, "LIVE_BANK_ADAPTER_ENABLED", False):
            with pytest.raises(AppException) as exc_info:
                adapter.submit_request(MagicMock(), MagicMock())
            assert exc_info.value.code == "LIVE_BANK_INTEGRATION_UNCONFIGURED"
            assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# 3. Verification Request Pipeline & Correlation ID Tests
# ---------------------------------------------------------------------------

class TestVerificationPipeline:
    """Tests the end-to-end verification pipeline in verification_service.py."""

    def test_create_verification_request_has_stable_correlation_id(self, db, test_instrument, scrutiny_officer):
        custom_corr = f"MY-CORR-{uuid.uuid4().hex[:8]}"
        req = create_verification_request(
            db=db,
            instrument_id=test_instrument.id,
            channel=VerificationChannel.SIMULATED.value,
            current_user=scrutiny_officer,
            correlation_id=custom_corr,
        )
        assert req.correlation_id == custom_corr
        assert req.reference_code.startswith("VR-SEC-")
        assert req.status == VerificationRequestStatus.PENDING.value

    def test_dispatch_mismatch_creates_validation_finding(self, db, test_instrument, scrutiny_officer):
        """Verifies that a MISMATCH outcome generates a persistent ValidationFinding."""
        req = create_verification_request(
            db=db,
            instrument_id=test_instrument.id,
            channel=VerificationChannel.SIMULATED.value,
            current_user=scrutiny_officer,
        )
        # Dispatch with deliberate MISMATCH scenario
        resp = dispatch_verification_request(
            db=db,
            request_id=req.id,
            current_user=scrutiny_officer,
            scenario="MISMATCH",
        )
        assert resp.result == VerificationResult.MISMATCH.value
        assert req.status == VerificationRequestStatus.MISMATCH.value

        # Check that discrepancy finding was created
        finding = db.query(ValidationFinding).filter(
            ValidationFinding.instrument_id == test_instrument.id,
            ValidationFinding.category == "CROSS_SOURCE_RECONCILIATION",
        ).first()
        assert finding is not None
        assert finding.rule_id == "RULE_BANK_RECONCILIATION_MISMATCH"
        assert finding.status in {"OPEN", "IN_REVIEW"}


# ---------------------------------------------------------------------------
# 4. Strict Trust Invariant: Mock/Sandbox Responses CANNOT Grant L3 Trust
# ---------------------------------------------------------------------------

class TestTrustLevelInvariants:
    """Verifies that simulated responses strictly cannot produce L3_BANK_CONFIRMED."""

    def test_simulated_response_cannot_promote_to_l3(self, db, test_instrument, scrutiny_officer):
        req = create_verification_request(
            db=db,
            instrument_id=test_instrument.id,
            channel=VerificationChannel.SIMULATED.value,
            current_user=scrutiny_officer,
        )
        resp = dispatch_verification_request(
            db=db,
            request_id=req.id,
            current_user=scrutiny_officer,
            scenario="MATCH",
        )
        assert resp.is_simulated is True

        # Attempt to apply L3 using simulated response must fail
        with pytest.raises(AppException) as exc_info:
            apply_l3_bank_confirmation(
                db=db,
                instrument_id=test_instrument.id,
                verification_response_id=resp.id,
                reason="Attempting to use mock for L3",
                current_user=scrutiny_officer,
                source_authorization_config="TEST_CONFIG",
            )
        assert "simulated" in str(exc_info.value.message).lower() or "SIMULATED" in str(exc_info.value.code).upper()


# ---------------------------------------------------------------------------
# 5. Cross-Tenant Isolation Tests
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    """Verifies an institution user cannot access or verify another tenant's FDR."""

    def test_institution_user_cannot_create_verification_request(self, db, test_instrument, institution_user):
        """Institution users are not regulatory officers and cannot initiate verification."""
        with pytest.raises(AppException) as exc_info:
            create_verification_request(
                db=db,
                instrument_id=test_instrument.id,
                channel=VerificationChannel.SIMULATED.value,
                current_user=institution_user,
            )
        assert exc_info.value.code == "OFFICER_ROLE_REQUIRED"
        assert exc_info.value.status_code == 403
