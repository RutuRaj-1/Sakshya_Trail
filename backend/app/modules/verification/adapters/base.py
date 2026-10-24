"""
Module 4 — Verification Adapters Base Interface
Defines typed provider submission and response contracts.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AdapterSubmissionResult:
    """Outcome of submitting a verification request to a provider or queue."""
    success: bool
    status: str
    message: str
    channel: str
    provider_reference: Optional[str] = None
    error_details: Optional[str] = None
    is_simulated: bool = False


@dataclass
class AdapterResponseResult:
    """Standardized normalized response payload from an adapter."""
    result: str  # MATCH, MISMATCH, TIMEOUT, SOURCE_UNAVAILABLE, INCONCLUSIVE
    bank_reference_number: Optional[str]
    bank_values: Dict[str, Any]
    is_simulated: bool
    source_classification: str  # AUTHORIZED_BANK_RESPONSE, MANUAL_EVIDENCE, SIMULATION
    source_identifier: str
    disclaimer: Optional[str] = None
    error_details: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


class BaseVerificationAdapter(ABC):
    """
    Narrow contract for verification channels (Manual, Simulated, Live Bank API).
    """

    @abstractmethod
    def submit_request(self, request: Any, instrument: Any) -> AdapterSubmissionResult:
        """Submit or queue a verification request to the provider."""
        pass

    @abstractmethod
    def check_or_receive_response(
        self, request: Any, instrument: Any, scenario: Optional[str] = None
    ) -> AdapterResponseResult:
        """Fetch, simulate, or process an incoming verification response."""
        pass

    @abstractmethod
    def normalize_provider_response(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize provider-specific fields into the canonical schema."""
        pass
