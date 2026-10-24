"""
Module 4 — Verification Adapters
Factory and registry for verification providers.
"""
from typing import Dict, Type
from app.modules.verification.adapters.base import (
    BaseVerificationAdapter,
    AdapterSubmissionResult,
    AdapterResponseResult,
)
from app.modules.verification.adapters.manual_adapter import ManualVerificationAdapter
from app.modules.verification.adapters.simulated_adapter import SimulatedBankAdapter
from app.modules.verification.adapters.live_adapter import LiveBankVerificationAdapter
from app.modules.verification.enums import VerificationChannel


ADAPTER_REGISTRY: Dict[str, Type[BaseVerificationAdapter]] = {
    VerificationChannel.MANUAL.value: ManualVerificationAdapter,
    VerificationChannel.AUTHORIZED_MANUAL.value: ManualVerificationAdapter,
    VerificationChannel.SIMULATED.value: SimulatedBankAdapter,
    VerificationChannel.LIVE_BANK_API.value: LiveBankVerificationAdapter,
    VerificationChannel.DIRECT_API.value: LiveBankVerificationAdapter,
    VerificationChannel.SFTP_BATCH.value: LiveBankVerificationAdapter,
}


def get_adapter_for_channel(channel: str) -> BaseVerificationAdapter:
    """Instantiate the appropriate verification adapter for a channel."""
    adapter_cls = ADAPTER_REGISTRY.get(channel.upper())
    if not adapter_cls:
        # Default to simulated in development if matching pattern
        if "SIM" in channel.upper():
            return SimulatedBankAdapter()
        return ManualVerificationAdapter()
    return adapter_cls()


__all__ = [
    "BaseVerificationAdapter",
    "AdapterSubmissionResult",
    "AdapterResponseResult",
    "ManualVerificationAdapter",
    "SimulatedBankAdapter",
    "LiveBankVerificationAdapter",
    "get_adapter_for_channel",
]
