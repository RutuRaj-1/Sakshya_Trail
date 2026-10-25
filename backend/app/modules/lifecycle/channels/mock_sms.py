"""
Module 5 — Mock SMS Notification Channel Provider
Explicitly labeled mock provider for SMS channel when external gateway is unconfigured.
"""
import time
import uuid
from typing import TYPE_CHECKING
from app.modules.lifecycle.channels.base import NotificationChannelProvider, DeliveryResult

if TYPE_CHECKING:
    from app.modules.lifecycle.models import LifecycleNotification


class MockSmsProvider(NotificationChannelProvider):
    """
    Mock SMS provider ensuring SMS channel remains clearly tagged as MOCKED in all logs and UIs.
    """

    def send(self, notification: "LifecycleNotification") -> DeliveryResult:
        start_time = time.time()
        duration = int((time.time() - start_time) * 1000)
        return DeliveryResult(
            status="MOCKED",
            channel="MOCK_SMS",
            provider_response_code="MOCK_SMS_200",
            provider_reference_id=f"sms-{uuid.uuid4().hex[:12]}",
            is_mock=True,
            mock_disclaimer="MOCKED — SMS PROVIDER NOT CONFIGURED IN PROTOTYPE",
            duration_ms=duration,
        )
