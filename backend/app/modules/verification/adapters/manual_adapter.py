"""
Module 4 — Manual Evidence Verification Adapter
Handles verification performed outside the automated system by authorized regulatory officers
(e.g., direct branch correspondence, official physical inspection letters, verified bank seal certificates).
"""
from typing import Optional, Dict, Any
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

MANUAL_EVIDENCE_DISCLAIMER = (
    "The system recorded an authorized officer's manual verification evidence, "
    "NOT a machine-authenticated direct bank response. Governed by regulatory scrutiny review."
)


class ManualVerificationAdapter(BaseVerificationAdapter):
    """
    Adapter for manually recorded external verification correspondence.
    Carries source_classification = MANUAL_EVIDENCE and mandatory disclaimer.
    """

    def submit_request(self, request: Any, instrument: Any) -> AdapterSubmissionResult:
        return AdapterSubmissionResult(
            success=True,
            status="PENDING",
            message="Manual verification request registered for regulatory officer follow-up.",
            channel=VerificationChannel.MANUAL.value,
            provider_reference=request.reference_code,
            is_simulated=False,
        )

    def check_or_receive_response(
        self, request: Any, instrument: Any, scenario: Optional[str] = None
    ) -> AdapterResponseResult:
        # For manual adapter, response is supplied via officer submission
        return AdapterResponseResult(
            result=VerificationResult.INCONCLUSIVE.value,
            bank_reference_number=None,
            bank_values={},
            is_simulated=False,
            source_classification=SourceClassification.MANUAL_EVIDENCE.value,
            source_identifier="Officer Manual External Verification",
            disclaimer=MANUAL_EVIDENCE_DISCLAIMER,
            error_details="Awaiting officer manual entry submission.",
        )

    def normalize_provider_response(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize officer manual fields into clean standard dictionary."""
        return {
            "bank_name": str(raw_payload.get("bank_name", "")).strip(),
            "branch": str(raw_payload.get("branch", "")).strip() if raw_payload.get("branch") else None,
            "reference_number": str(raw_payload.get("reference_number", "")).strip().upper(),
            "amount": str(raw_payload.get("amount", "")).strip(),
            "currency": str(raw_payload.get("currency", "INR")).strip().upper(),
            "issue_date": str(raw_payload.get("issue_date", "")).strip(),
            "maturity_date": str(raw_payload.get("maturity_date", "")).strip(),
            "lien_holder": str(raw_payload.get("lien_holder", "")).strip() if raw_payload.get("lien_holder") else None,
        }
