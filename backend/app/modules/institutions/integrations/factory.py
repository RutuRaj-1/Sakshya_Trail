"""
Institutional Verification Provider Factory
Selects appropriate provider based on INTEGRATION_MODE configuration.
"""
from app.core.config import settings
from app.modules.institutions.integrations.base import InstitutionVerificationProvider
from app.modules.institutions.integrations.mock_provider import MockInstitutionVerificationProvider
from app.modules.institutions.integrations.sandbox_provider import SandboxInstitutionVerificationProvider
from app.modules.institutions.integrations.live_provider import LiveInstitutionVerificationProvider

_institution_provider = None


def get_institution_verification_provider() -> InstitutionVerificationProvider:
    """Returns the configured InstitutionVerificationProvider singleton."""
    global _institution_provider
    if _institution_provider is None:
        mode = getattr(settings, "INTEGRATION_MODE", "mock").lower()
        if mode == "production":
            _institution_provider = LiveInstitutionVerificationProvider()
        elif mode == "sandbox":
            _institution_provider = SandboxInstitutionVerificationProvider()
        else:
            _institution_provider = MockInstitutionVerificationProvider()
    return _institution_provider


def set_institution_verification_provider(provider: InstitutionVerificationProvider) -> None:
    """Overrides provider for testing."""
    global _institution_provider
    _institution_provider = provider

