"""
Module 5 — In-App Notification Channel Provider
Directly stores and surfaces real-time notifications in the recipient's Sentinel dashboard inbox.
"""
import time
import uuid
from typing import TYPE_CHECKING
from app.modules.lifecycle.channels.base import NotificationChannelProvider, DeliveryResult

if TYPE_CHECKING:
    from app.modules.lifecycle.models import LifecycleNotification


class InAppNotificationProvider(NotificationChannelProvider):
    """
    Delivers in-app alerts directly into the platform user database.
    Since the notification record itself is persisted in the application DB,
    delivery to the in-app inbox is immediately confirmed as DELIVERED upon persistence.
    """

    def send(self, notification: "LifecycleNotification") -> DeliveryResult:
        start_time = time.time()
        # In-app delivery succeeds immediately as the database row is the in-app message
        duration = int((time.time() - start_time) * 1000)
        return DeliveryResult(
            status="DELIVERED",
            channel="IN_APP",
            provider_response_code="200_IN_APP_QUEUED",
            provider_reference_id=f"inapp-{uuid.uuid4().hex[:12]}",
            duration_ms=duration,
            is_mock=False,
        )
