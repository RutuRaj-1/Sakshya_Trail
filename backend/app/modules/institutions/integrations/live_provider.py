"""
Institutional Verification Provider - Production Implementation
Enforces strict gating for live production integration with AICTE central systems.
Fails closed with a clear diagnostic when unconfigured or unauthorized.
"""
from typing import Optional
from app.core.config import settings
from app.common.exceptions import AppException
from app.modules.institutions.integrations.base import (
    InstitutionVerificationProvider,
    InstitutionVerificationResult,
)


class LiveInstitutionVerificationProvider(InstitutionVerificationProvider):
    """
    Production integration connector for the official AICTE API.
    Remains strictly disabled until AICTE_INTEGRATION_ENABLED is True and valid production credentials exist.
    """

    def _assert_live_enabled(self) -> None:
        if not settings.AICTE_INTEGRATION_ENABLED:
            raise AppException(
                message=(
                    "Live AICTE Institutional Verification is not enabled. "
                    "Official statutory API agreement, institutional API credentials, "
                    "or bilateral integration tokens have not been configured."
                ),
                status_code=503,
                code="AICTE_INTEGRATION_UNCONFIGURED",
                details={
                    "aicte_integration_enabled": settings.AICTE_INTEGRATION_ENABLED,
                    "resolution": "Configure AICTE_INTEGRATION_ENABLED=true and provision official credentials.",
                },
            )

    def verify_institution(
        self,
        institution_code: str,
        legal_name: str,
        expected_state: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> InstitutionVerificationResult:
        self._assert_live_enabled()
        # In future live environment: dispatch to production AICTE gateway via HTTPS with cert
        raise NotImplementedError("Production AICTE endpoint is not yet activated.")

