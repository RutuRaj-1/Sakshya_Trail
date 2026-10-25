"""
Module 5 — Notification Channel Provider Interface
Defines the delivery protocol and outcome payload contract for multi-channel notifications.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.lifecycle.models import LifecycleNotification


@dataclass
class DeliveryResult:
    """
    Standardized delivery attempt outcome reported by any channel provider.
    """
    status: str  # "ACCEPTED", "DELIVERED", "FAILED", "MOCKED"
    channel: str
    provider_response_code: Optional[str] = None
    provider_reference_id: Optional[str] = None
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    is_mock: bool = False
    mock_disclaimer: Optional[str] = None
    duration_ms: Optional[int] = None


class NotificationChannelProvider(ABC):
    """
    Abstract contract for notification dispatch channels.
    Decoupled from lifecycle evaluation logic.
    """

    @abstractmethod
    def send(self, notification: "LifecycleNotification") -> DeliveryResult:
        """
        Dispatches a rendered notification through the channel.
        Must return a structured DeliveryResult and never raise unhandled network exceptions.
        """
        pass
