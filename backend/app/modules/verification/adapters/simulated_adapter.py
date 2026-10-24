"""
Module 4 — Simulated Prototype Bank Adapter
Provides reproducible simulation of bank verification responses for development, testing, and SIH demonstrations.
Strictly disabled in production configuration. Simulated results CANNOT promote trust to L3_BANK_CONFIRMED.
"""
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import timedelta

from app.core.config import settings
from app.common.exceptions import AppException
from app.modules.verification.adapters.base import (
    BaseVerificationAdapter,
    AdapterSubmissionResult,
    AdapterResponseResult,
)
from app.modules.verification.enums import (
    VerificationChannel,
    VerificationResult,
    SourceClassification,
)

SIMULATED_DISCLAIMER = (
    "Simulated prototype response for demonstration and testing only. "
    "Does NOT contact a real bank and CANNOT authorize production L3 trust level."
)


class SimulatedBankAdapter(BaseVerificationAdapter):
    """
    Controlled simulation adapter.
    Produces deterministic outcomes (MATCH, MISMATCH, TIMEOUT, SOURCE_UNAVAILABLE, INCONCLUSIVE)
    without contacting external banking networks.
    """

    def _check_simulation_allowed(self) -> None:
        """Enforces that simulation is strictly barred in production environments."""
        if settings.ENVIRONMENT.lower() == "production" or not settings.ENABLE_SIMULATED_VERIFICATION:
            raise AppException(
                message="Simulated verification adapter is strictly disabled in production configuration.",
                status_code=403,
                code="SIMULATION_DISABLED_IN_PRODUCTION",
                details={
                    "environment": settings.ENVIRONMENT,
                    "enable_simulated_verification": settings.ENABLE_SIMULATED_VERIFICATION,
                },
            )

    def submit_request(self, request: Any, instrument: Any) -> AdapterSubmissionResult:
        self._check_simulation_allowed()
        return AdapterSubmissionResult(
            success=True,
            status="SENT",
            message="Request dispatched to simulated bank adapter queue.",
            channel=VerificationChannel.SIMULATED.value,
            provider_reference=f"SIM-TXN-{request.reference_code}",
            is_simulated=True,
        )

    def check_or_receive_response(
        self, request: Any, instrument: Any, scenario: Optional[str] = None
    ) -> AdapterResponseResult:
        self._check_simulation_allowed()

        # Determine scenario from explicit parameter or reference code hints
        effective_scenario = (scenario or "MATCH").upper()
        if "MISMATCH" in request.reference_code.upper():
            effective_scenario = "MISMATCH"
        elif "TIMEOUT" in request.reference_code.upper():
            effective_scenario = "TIMEOUT"
        elif "UNAVAILABLE" in request.reference_code.upper():
            effective_scenario = "SOURCE_UNAVAILABLE"
        elif "INCONCLUSIVE" in request.reference_code.upper():
            effective_scenario = "INCONCLUSIVE"

        # 1. TIMEOUT Scenario
        if effective_scenario == "TIMEOUT":
            return AdapterResponseResult(
                result=VerificationResult.TIMEOUT.value,
                bank_reference_number=None,
                bank_values={},
                is_simulated=True,
                source_classification=SourceClassification.SIMULATION.value,
                source_identifier="Simulated Core Banking Network (Timeout Simulator)",
                disclaimer=SIMULATED_DISCLAIMER,
                error_details="Simulated gateway read timeout (socket timeout after 30000ms).",
                raw_metadata={"simulated_error": "GATEWAY_TIMEOUT", "attempted_url": "mock://bank.sbi/fdr/verify"},
            )

        # 2. SOURCE_UNAVAILABLE Scenario
        if effective_scenario == "SOURCE_UNAVAILABLE":
            return AdapterResponseResult(
                result=VerificationResult.SOURCE_UNAVAILABLE.value,
                bank_reference_number=None,
                bank_values={},
                is_simulated=True,
                source_classification=SourceClassification.SIMULATION.value,
                source_identifier="Simulated Core Banking Network (Downtime Simulator)",
                disclaimer=SIMULATED_DISCLAIMER,
                error_details="Bank core API service is currently down for scheduled batch maintenance (HTTP 503).",
                raw_metadata={"simulated_error": "SERVICE_UNAVAILABLE", "retry_after_seconds": 3600},
            )

        # 3. INCONCLUSIVE Scenario
        if effective_scenario == "INCONCLUSIVE":
            return AdapterResponseResult(
                result=VerificationResult.INCONCLUSIVE.value,
                bank_reference_number=f"SIM-INCON-{request.reference_code[-6:]}",
                bank_values={"reference_number": instrument.reference_number},
                is_simulated=True,
                source_classification=SourceClassification.SIMULATION.value,
                source_identifier="Simulated Core Banking Network (Indeterminate Matcher)",
                disclaimer=SIMULATED_DISCLAIMER,
                error_details="Record found in core system but deposit status is marked PENDING_CLEARANCE.",
                raw_metadata={"simulated_status": "PENDING_CLEARANCE"},
            )

        # 4. MISMATCH Scenario
        if effective_scenario == "MISMATCH":
            # Return deliberately divergent amount and maturity date
            mismatched_amount = str(Decimal(str(instrument.amount)) * Decimal("0.85"))
            mismatched_maturity = (instrument.maturity_date + timedelta(days=365)).isoformat()
            bank_vals = {
                "bank_name": instrument.bank_name,
                "branch": instrument.branch,
                "reference_number": instrument.reference_number,
                "amount": mismatched_amount,
                "currency": instrument.currency,
                "issue_date": instrument.issue_date.isoformat(),
                "maturity_date": mismatched_maturity,
                "lien_holder": "None / Not Marked in Core Banking",
            }
            return AdapterResponseResult(
                result=VerificationResult.MISMATCH.value,
                bank_reference_number=f"SIM-MISMATCH-{request.reference_code[-6:]}",
                bank_values=bank_vals,
                is_simulated=True,
                source_classification=SourceClassification.SIMULATION.value,
                source_identifier="Simulated Core Banking Network (Discrepancy Generator)",
                disclaimer=SIMULATED_DISCLAIMER,
                error_details="Core banking data discrepancies detected on amount and maturity date.",
                raw_metadata={"simulated_discrepancy_types": ["AMOUNT_MISMATCH", "MATURITY_MISMATCH", "LIEN_UNRECORDED"]},
            )

        # 5. MATCH Scenario (Default)
        matched_vals = {
            "bank_name": instrument.bank_name,
            "branch": instrument.branch,
            "reference_number": instrument.reference_number,
            "amount": str(instrument.amount),
            "currency": instrument.currency,
            "issue_date": instrument.issue_date.isoformat(),
            "maturity_date": instrument.maturity_date.isoformat(),
            "lien_holder": instrument.lien_holder or "AICTE Regulation Bureau",
        }
        return AdapterResponseResult(
            result=VerificationResult.MATCH.value,
            bank_reference_number=f"SIM-SBI-CONF-{request.reference_code[-8:]}",
            bank_values=matched_vals,
            is_simulated=True,
            source_classification=SourceClassification.SIMULATION.value,
            source_identifier="Simulated Core Banking Network (Match Generator)",
            disclaimer=SIMULATED_DISCLAIMER,
            raw_metadata={"simulated_auth_token": "SIM-TOKEN-AUTHENTICATED", "channel": "SIMULATED_CORE_API"},
        )

    def normalize_provider_response(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return raw_payload
