"""
Institutions Integrations Package
"""
from app.modules.institutions.integrations.base import (
    InstitutionVerificationProvider,
    InstitutionVerificationResult,
)
from app.modules.institutions.integrations.mock_provider import MockInstitutionVerificationProvider
from app.modules.institutions.integrations.sandbox_provider import SandboxInstitutionVerificationProvider
from app.modules.institutions.integrations.live_provider import LiveInstitutionVerificationProvider
from app.modules.institutions.integrations.factory import (
    get_institution_verification_provider,
    set_institution_verification_provider,
)

__all__ = [
    "InstitutionVerificationProvider",
    "InstitutionVerificationResult",
    "MockInstitutionVerificationProvider",
    "SandboxInstitutionVerificationProvider",
    "LiveInstitutionVerificationProvider",
    "get_institution_verification_provider",
    "set_institution_verification_provider",
]

