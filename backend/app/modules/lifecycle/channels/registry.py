"""
Module 5 — Notification Channel Registry & Factory
Resolves the active channel provider for a given notification channel name.
"""
from typing import Dict
from app.modules.lifecycle.channels.base import NotificationChannelProvider
from app.modules.lifecycle.channels.in_app import InAppNotificationProvider
from app.modules.lifecycle.channels.email import EmailNotificationProvider
from app.modules.lifecycle.channels.mock_sms import MockSmsProvider
from app.common.exceptions import AppException

_PROVIDERS: Dict[str, NotificationChannelProvider] = {
    "IN_APP": InAppNotificationProvider(),
    "EMAIL": EmailNotificationProvider(),
    "MOCK_SMS": MockSmsProvider(),
    "MOCK_WHATSAPP": MockSmsProvider(),  # Reuses mock channel
}


def get_channel_provider(channel: str) -> NotificationChannelProvider:
    """
    Returns the channel provider instance for the requested channel.
    Raises AppException if an unknown/unsupported channel is requested.
    """
    norm_channel = channel.upper().strip()
    provider = _PROVIDERS.get(norm_channel)
    if not provider:
        raise AppException(
            status_code=400,
            message=f"Unsupported notification channel '{channel}'. Permitted: {list(_PROVIDERS.keys())}",
            code="UNSUPPORTED_NOTIFICATION_CHANNEL",
        )
    return provider


def register_channel_provider(channel: str, provider: NotificationChannelProvider) -> None:
    """Allows test fixtures or custom extensions to register mock or specialized providers."""
    _PROVIDERS[channel.upper().strip()] = provider
