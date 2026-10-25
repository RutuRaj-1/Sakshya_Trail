"""
Module 5 — Email Notification Channel Provider
Dispatches email notifications through configured SMTP or routes to an explicitly
labeled local development mail-catcher / mock provider with honest delivery statuses.
"""
import time
import uuid
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import TYPE_CHECKING, Optional

from app.core.config import settings
from app.modules.lifecycle.channels.base import NotificationChannelProvider, DeliveryResult

if TYPE_CHECKING:
    from app.modules.lifecycle.models import LifecycleNotification

logger = logging.getLogger(__name__)


class EmailNotificationProvider(NotificationChannelProvider):
    """
    Email provider honoring strict delivery attribution:
    - If recipient email is invalid or missing -> FAILED (INVALID_RECIPIENT).
    - If real SMTP is configured and reaches the server -> ACCEPTED (not DELIVERED unless DSN/webhook confirms).
    - If local mail-catcher / mock mode -> ACCEPTED / MOCKED with clear disclaimer notice.
    - If SMTP connection fails -> FAILED (PROVIDER_UNAVAILABLE).
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        sender_email: Optional[str] = None,
        force_mock: bool = False,
    ):
        self.smtp_host = smtp_host or getattr(settings, "SMTP_HOST", None)
        self.smtp_port = smtp_port or getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = smtp_user or getattr(settings, "SMTP_USER", None)
        self.smtp_password = smtp_password or getattr(settings, "SMTP_PASSWORD", None)
        self.sender_email = sender_email or getattr(settings, "SMTP_SENDER", "sentinel-alerts@aicte-india.org")
        self.force_mock = force_mock

    def send(self, notification: "LifecycleNotification") -> DeliveryResult:
        start_time = time.time()

        # 1. Validation: Recipient Email
        recipient_email = notification.recipient_email
        if not recipient_email or "@" not in recipient_email:
            return DeliveryResult(
                status="FAILED",
                channel="EMAIL",
                error_category="INVALID_RECIPIENT",
                error_message=f"Missing or malformed recipient email '{recipient_email}'",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # 2. Local Mail-Catcher / Mock Mode (Default when no real SMTP host is configured)
        if self.force_mock or not self.smtp_host or self.smtp_host in ("localhost", "127.0.0.1", "mock"):
            duration = int((time.time() - start_time) * 1000)
            mock_ref = f"mock-mail-{uuid.uuid4().hex[:12]}"
            logger.info(
                f"[Email Provider] Simulated dispatch for notification '{notification.id}' "
                f"to '{recipient_email}': {notification.title} -> {mock_ref}"
            )
            return DeliveryResult(
                status="ACCEPTED",
                channel="EMAIL",
                provider_response_code="250_QUEUED_LOCAL_MAIL_CATCHER",
                provider_reference_id=mock_ref,
                is_mock=True,
                mock_disclaimer="QUEUED_FOR_LOCAL_MAIL_CATCHER",
                duration_ms=duration,
            )

        # 3. Real SMTP Execution
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = notification.title
            msg["From"] = self.sender_email
            msg["To"] = recipient_email
            msg["X-Sentinel-Notification-ID"] = notification.id
            msg.attach(MIMEText(notification.message, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            duration = int((time.time() - start_time) * 1000)
            smtp_ref = f"smtp-{uuid.uuid4().hex[:12]}"
            # Note: SMTP handshake confirms acceptance by the MTA relay, NOT inbox delivery.
            return DeliveryResult(
                status="ACCEPTED",
                channel="EMAIL",
                provider_response_code="250_OK_RELAYED",
                provider_reference_id=smtp_ref,
                is_mock=False,
                duration_ms=duration,
            )

        except smtplib.SMTPAuthenticationError as auth_err:
            duration = int((time.time() - start_time) * 1000)
            return DeliveryResult(
                status="FAILED",
                channel="EMAIL",
                error_category="AUTHENTICATION_ERROR",
                error_message=f"SMTP authentication rejected: {auth_err}",
                duration_ms=duration,
            )
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, ConnectionRefusedError) as conn_err:
            duration = int((time.time() - start_time) * 1000)
            return DeliveryResult(
                status="FAILED",
                channel="EMAIL",
                error_category="PROVIDER_UNAVAILABLE",
                error_message=f"Unable to connect to SMTP server '{self.smtp_host}:{self.smtp_port}': {conn_err}",
                duration_ms=duration,
            )
        except Exception as exc:
            duration = int((time.time() - start_time) * 1000)
            return DeliveryResult(
                status="FAILED",
                channel="EMAIL",
                error_category="NETWORK_TIMEOUT",
                error_message=f"SMTP dispatch failed: {exc}",
                duration_ms=duration,
            )
