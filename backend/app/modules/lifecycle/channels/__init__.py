"""
Module 5 — Lifecycle Notification Channels Package
"""
from app.modules.lifecycle.channels.base import NotificationChannelProvider, DeliveryResult
from app.modules.lifecycle.channels.in_app import InAppNotificationProvider
from app.modules.lifecycle.channels.email import EmailNotificationProvider
from app.modules.lifecycle.channels.mock_sms import MockSmsProvider
from app.modules.lifecycle.channels.registry import get_channel_provider, register_channel_provider

__all__ = [
    "NotificationChannelProvider",
    "DeliveryResult",
    "InAppNotificationProvider",
    "EmailNotificationProvider",
    "MockSmsProvider",
    "get_channel_provider",
    "register_channel_provider",
]
