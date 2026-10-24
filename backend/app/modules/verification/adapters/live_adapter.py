"""
Module 4 — Live Bank Verification Adapter Interface
Integration boundary for future authorized bank confirmation services.
Enforces honest reporting when live banking integration is unconfigured or unauthorized.
Does NOT fabricate credentials, endpoints, or mock connections as real bank services.
"""
from typing import Optional, Dict, Any

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


class LiveBankVerificationAdapter(BaseVerificationAdapter):
    """
    Standard interface for authorized live banking integrations (e.g. SFTP, Direct Core Banking API).
    Reports cleanly and honestly when live integration is unconfigured.
    """

    def _assert_live_enabled(self) -> None:
        """Enforces that live banking adapter is only operational when explicitly authorized and configured."""
        if not settings.LIVE_BANK_ADAPTER_ENABLED:
            raise AppException(
                message=(
                    "Live bank verification integration is unconfigured. No authorized banking "
                    "service credentials or bilateral data-sharing protocols have been provisioned."
                ),
                status_code=503,
                code="LIVE_BANK_INTEGRATION_UNCONFIGURED",
                details={
                    "live_bank_adapter_enabled": settings.LIVE_BANK_ADAPTER_ENABLED,
                    "resolution": "Configure authorized bank API endpoint and credentials in AICTE administration.",
                },
            )

    def submit_request(self, request: Any, instrument: Any) -> AdapterSubmissionResult:
        self._assert_live_enabled()
        # In future live environment: dispatch to official bank gateway
        return AdapterSubmissionResult(
            success=False,
            status="SOURCE_UNAVAILABLE",
            message="Live banking provider is not yet provisioned with active bank connection.",
            channel=VerificationChannel.LIVE_BANK_API.value,
            is_simulated=False,
        )

    def check_or_receive_response(
        self, request: Any, instrument: Any, scenario: Optional[str] = None
    ) -> AdapterResponseResult:
        self._assert_live_enabled()
        return AdapterResponseResult(
            result=VerificationResult.SOURCE_UNAVAILABLE.value,
            bank_reference_number=None,
            bank_values={},
            is_simulated=False,
            source_classification=SourceClassification.AUTHORIZED_BANK_RESPONSE.value,
            source_identifier="Live Bank Adapter (Unconfigured)",
            error_details="No live bank API response received; endpoint unconfigured.",
        )

    def normalize_provider_response(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        return raw_payload
