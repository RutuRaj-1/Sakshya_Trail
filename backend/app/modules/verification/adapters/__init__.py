"""
Module 4 — Verification Adapters
Factory and registry for verification providers.
Integrates Mock, Sandbox, Live, and Manual adapters under configured INTEGRATION_MODE.
"""
from typing import Dict, Type
from app.core.config import settings
from app.modules.verification.adapters.base import (
    BaseVerificationAdapter,
    AdapterSubmissionResult,
    AdapterResponseResult,
)
from app.modules.verification.adapters.manual_adapter import ManualVerificationAdapter
from app.modules.verification.adapters.simulated_adapter import SimulatedBankAdapter
from app.modules.verification.adapters.sandbox_adapter import SandboxBankAdapter
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
    """
    Instantiate the appropriate verification adapter for a channel.
    Takes into account INTEGRATION_MODE when live or automated channels are requested.
    """
    channel_norm = channel.upper()

    # Manual channels always use ManualVerificationAdapter
    if channel_norm in {VerificationChannel.MANUAL.value, VerificationChannel.AUTHORIZED_MANUAL.value}:
        return ManualVerificationAdapter()

    mode = getattr(settings, "INTEGRATION_MODE", "mock").lower()

    if mode == "sandbox":
        # In sandbox mode, automated requests route through SandboxBankAdapter
        return SandboxBankAdapter()
    elif mode == "production":
        # In production mode, route to LiveBankVerificationAdapter (which checks configuration)
        return LiveBankVerificationAdapter()
    else:
        # Default mock / development mode
        if channel_norm == VerificationChannel.SIMULATED.value or "SIM" in channel_norm:
            return SimulatedBankAdapter()
        adapter_cls = ADAPTER_REGISTRY.get(channel_norm, SimulatedBankAdapter)
        return adapter_cls()


__all__ = [
    "BaseVerificationAdapter",
    "AdapterSubmissionResult",
    "AdapterResponseResult",
    "ManualVerificationAdapter",
    "SimulatedBankAdapter",
    "SandboxBankAdapter",
    "LiveBankVerificationAdapter",
    "get_adapter_for_channel",
]
