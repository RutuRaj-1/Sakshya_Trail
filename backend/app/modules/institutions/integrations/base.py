"""
Institutional Verification Provider - Base Interface & Models
Defines the standard contract for verifying educational institutions against
external regulatory registries (e.g., AICTE Central Registry, AISHE portal).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


@dataclass
class InstitutionVerificationResult:
    """Standardized normalized outcome of an institutional registry verification lookup."""
    is_verified: bool
    status: str  # MATCH, MISMATCH, UNAVAILABLE, ERROR
    provider_name: str
    environment: str  # mock, sandbox, production
    correlation_id: str
    timestamp: datetime
    verified_fields: Dict[str, Any]
    mismatched_fields: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    unsupported_fields: List[str] = field(default_factory=list)
    official_approval_status: Optional[str] = None  # APPROVED, REJECTED, WITHDRAWN, UNKNOWN
    handbook_year: Optional[str] = None
    notes: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


class InstitutionVerificationProvider(ABC):
    """
    Contract for institutional verification providers.
    Supports deterministic mock, authorized sandbox, and production adapters.
    """

    @abstractmethod
    def verify_institution(
        self,
        institution_code: str,
        legal_name: str,
        expected_state: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> InstitutionVerificationResult:
        """
        Verify an institution's identity, code, legal name, and approval status
        against the external authoritative or simulated registry.
        """
        pass

