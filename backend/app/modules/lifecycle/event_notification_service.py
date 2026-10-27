"""
Module 5 — Material Event Notification Dispatcher & Operational Oversight Service
Implements Prompt 3 event catalogue, recipient policy by role & scope, idempotency deduplication,
and System Admin operational oversight feed.
"""
import json
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, func

from app.db.base import get_utc_now
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import LifecycleNotification, NotificationDeliveryAttempt
from app.modules.audit.service import log_audit_event
from app.common.exceptions import ForbiddenException, NotFoundException

logger = logging.getLogger(__name__)


def build_material_event_idempotency_key(
    entity_type: str,
    entity_id: str,
    event_type: str,
    recipient_role: str,
    recipient_user_id: Optional[str] = None,
    trigger_date: Optional[date] = None,
    extra_suffix: Optional[str] = None,
) -> str:
    """
    Builds a deterministic idempotency key for material business events.
    Guarantees deduplication across retries and repeated calls.
    """
    dt_str = (trigger_date or datetime.now(timezone.utc).date()).isoformat()
    recip_part = recipient_user_id or recipient_role
    base = f"notif:event:{entity_type}:{entity_id}:{event_type}:{recip_part}:{dt_str}"
    if extra_suffix:
        base = f"{base}:{extra_suffix}"
    return base


def _create_and_deliver_in_app_notification(
    db: Session,
    idempotency_key: str,
    event_type: str,
    recipient_role: str,
    title: str,
    message: str,
    instrument_id: Optional[str] = None,
    institution_id: Optional[str] = None,
    recipient_user_id: Optional[str] = None,
    payload_metadata: Optional[Dict[str, Any]] = None,
    is_mock: bool = False,
    mock_disclaimer: Optional[str] = None,
) -> Optional[LifecycleNotification]:
    """
    Creates an in-app notification idempotently, immediately marking it DELIVERED
    in the recipient's in-app inbox.
    """
    # Check if notification with this idempotency key already exists
    existing = db.scalar(
        select(LifecycleNotification).where(LifecycleNotification.idempotency_key == idempotency_key)
    )
    if existing:
        return existing

    now = get_utc_now()
    notif_id = str(uuid.uuid4())
    metadata_json = json.dumps(payload_metadata) if payload_metadata else None

    notif = LifecycleNotification(
        id=notif_id,
        idempotency_key=idempotency_key,
        instrument_id=instrument_id,
        institution_id=institution_id,
        policy_id=None,
        policy_version=1,
        event_type=event_type,
        reminder_milestone_days=None,
        trigger_date=now.date(),
        recipient_user_id=recipient_user_id,
        recipient_role=recipient_role,
        recipient_email=None,
        recipient_name=None,
        channel="IN_APP",
        template_id=f"TEMPLATE_{event_type}",
        template_version=1,
        title=title,
        message=message,
        payload_metadata_json=metadata_json,
        status="DELIVERED",
        is_read=False,
        read_at=None,
        scheduled_at=now,
        first_attempted_at=now,
        last_attempted_at=now,
        delivered_at=now,
        failed_at=None,
        retry_count=0,
        max_retries=3,
        is_mock=is_mock,
        mock_disclaimer=mock_disclaimer,
    )
    db.add(notif)

    # Record delivery attempt
    attempt = NotificationDeliveryAttempt(
        id=str(uuid.uuid4()),
        notification_id=notif_id,
        attempt_number=1,
        attempted_at=now,
        channel="IN_APP",
        status="DELIVERED",
        provider_response_code="200",
        duration_ms=5,
    )
    db.add(attempt)
    return notif


def emit_material_event(
    db: Session,
    event_type: str,
    entity_type: str,
    entity_id: str,
    actor_user: Optional[User] = None,
    instrument_id: Optional[str] = None,
    institution_id: Optional[str] = None,
    resulting_state: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    idempotency_suffix: Optional[str] = None,
    is_mock: bool = False,
    mock_disclaimer: Optional[str] = None,
) -> List[LifecycleNotification]:
    """
    Main dispatch entry point for material events across the 9-stage lifecycle.
    1. Determines recipient roles according to Phase B policy.
    2. Enforces institution isolation: INSTITUTION_USER notifications are scoped strictly to the institution.
    3. Emits structured operational oversight notifications to SYSTEM_ADMIN.
    4. Records idempotent persistent notifications.
    """
    created_notifications: List[LifecycleNotification] = []
    details_dict = details.copy() if details else {}

    # Extract instrument reference or identifiers if available
    instrument_ref = details_dict.get("reference_number")
    if not instrument_ref and instrument_id:
        inst_row = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
        if inst_row:
            instrument_ref = inst_row.reference_number
            if not institution_id:
                institution_id = inst_row.institution_id
    inst_ref_display = instrument_ref or entity_id

    # Safe detail link
    if entity_type == "INSTRUMENT" or instrument_id:
        safe_link = f"/instruments/{instrument_id or entity_id}"
    elif entity_type == "RELEASE_CASE":
        safe_link = f"/release/{entity_id}"
    elif entity_type == "USER":
        safe_link = f"/admin/users/{entity_id}"
    elif entity_type == "POLICY":
        safe_link = f"/lifecycle/policies/{entity_id}"
    elif entity_type == "AUDIT_CHAIN":
        safe_link = "/audit"
    else:
        safe_link = f"/{entity_type.lower()}/{entity_id}"

    actor_display = (
        f"{actor_user.full_name} ({actor_user.email}, {actor_user.role})"
        if actor_user
        else "System / Automated Engine"
    )

    # 1. Resolve Recipient Roles and Custom Messages
    recipients_to_notify: List[Tuple[str, Optional[str], Optional[str], str, str]] = []
    # Tuples: (role, user_id, inst_id_scope, title, message)

    if event_type == "INSTRUMENT_SUBMITTED":
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                actor_user.id if actor_user and actor_user.role == "INSTITUTION_USER" else None,
                institution_id,
                "Instrument Submitted for Scrutiny",
                f"FDR instrument {inst_ref_display} has been submitted for scrutiny. Current Status: SUBMITTED.",
            ))
        recipients_to_notify.append((
            "SCRUTINY_OFFICER",
            None,
            None,
            "New Instrument Awaiting Scrutiny",
            f"FDR instrument {inst_ref_display} submitted. Assigned to scrutiny queue.",
        ))

    elif event_type == "DOCUMENT_UPLOADED":
        doc_type = details_dict.get("document_type", "Document")
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                actor_user.id if actor_user and actor_user.role == "INSTITUTION_USER" else None,
                institution_id,
                "Evidence Document Uploaded",
                f"Document '{doc_type}' uploaded successfully for instrument {inst_ref_display}.",
            ))
        recipients_to_notify.append((
            "SCRUTINY_OFFICER",
            None,
            None,
            "New Evidence Document Uploaded",
            f"Institution uploaded '{doc_type}' for instrument {inst_ref_display}.",
        ))

    elif event_type == "VALIDATION_FINDING_CREATED":
        finding_code = details_dict.get("finding_code", "FINDING")
        severity = details_dict.get("severity", "MEDIUM")
        recipients_to_notify.append((
            "SCRUTINY_OFFICER",
            None,
            None,
            "Validation Finding Generated",
            f"Validation finding [{severity}] '{finding_code}' generated for instrument {inst_ref_display}.",
        ))

    elif event_type == "SUBMISSION_RETURNED_FOR_CORRECTION":
        reason = details_dict.get("reason", "Incomplete documentation or clarification requested.")
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Action Required: Submission Returned for Correction",
                f"Instrument {inst_ref_display} has been returned for correction. Reason: {reason}",
            ))
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            "Instrument Returned for Correction",
            f"Officer returned instrument {inst_ref_display} for correction.",
        ))

    elif event_type == "CORRECTION_RESPONSE_SUBMITTED":
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                actor_user.id if actor_user and actor_user.role == "INSTITUTION_USER" else None,
                institution_id,
                "Correction Response Submitted",
                f"Correction response for instrument {inst_ref_display} has been submitted for scrutiny.",
            ))
        recipients_to_notify.append((
            "SCRUTINY_OFFICER",
            None,
            None,
            "Correction Response Awaiting Review",
            f"Institution has resubmitted corrected information for instrument {inst_ref_display}. Scrutiny review required.",
        ))

    elif event_type == "SCRUTINY_REVIEW_COMPLETED":
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            "Scrutiny Review Completed",
            f"Scrutiny review completed for instrument {inst_ref_display}. Ready for L2 attestation or verification.",
        ))

    elif event_type == "L2_OFFICER_ATTESTATION_RECORDED":
        attest_type = details_dict.get("attestation_type", "REGULATORY_SCRUTINY")
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Officer Scrutiny Verification Confirmed",
                f"Instrument {inst_ref_display} officer verification confirmed at Trust Level L2 ({attest_type}).",
            ))
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            "L2 Officer Attestation Recorded",
            f"L2 officer verification recorded for instrument {inst_ref_display}.",
        ))

    elif event_type == "SIMULATED_BANK_RESPONSE_RECORDED":
        bank_status = details_dict.get("bank_status", "MATCHED")
        recipients_to_notify.append((
            "SCRUTINY_OFFICER",
            None,
            None,
            "Simulated Bank Response Recorded",
            f"Simulated bank verification response recorded for {inst_ref_display} (Status: {bank_status}). NOTE: Simulated bank responses do not establish genuine L3 trust.",
        ))
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Bank Verification Response Recorded",
                f"Bank verification response received for instrument {inst_ref_display}.",
            ))

    elif event_type == "RENEWAL_INSTRUMENT_CREATED":
        succ_ref = details_dict.get("successor_reference", inst_ref_display)
        pred_ref = details_dict.get("predecessor_reference", "predecessor")
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Renewal Successor Instrument Linked",
                f"Successor instrument {succ_ref} has been linked to {pred_ref}. Lineage continuity preserved.",
            ))
        recipients_to_notify.append((
            "SCRUTINY_OFFICER",
            None,
            None,
            "Renewal Successor Instrument Registered",
            f"Renewal successor {succ_ref} linked to predecessor {pred_ref}. Lineage verification required.",
        ))

    elif event_type == "RELEASE_REQUEST_SUBMITTED":
        case_id = details_dict.get("case_id", entity_id)
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Release Request Submitted",
                f"Release request {case_id} submitted for instrument {inst_ref_display}. Pending readiness evaluation.",
            ))
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            "New Release Request Pending Review",
            f"Release request submitted for instrument {inst_ref_display} (Case {case_id}).",
        ))

    elif event_type in ("RELEASE_GATE_READINESS_CHANGED", "RELEASE_READINESS_BLOCKED", "RELEASE_READINESS_SATISFIED"):
        readiness = details_dict.get("readiness_status", "EVALUATED")
        blockers = details_dict.get("blockers_count", 0)
        if readiness == "BLOCKED" or blockers > 0 or event_type == "RELEASE_READINESS_BLOCKED":
            title = f"Release Gate Blocked: {blockers} Blocker(s) Active"
            msg = f"Case {entity_id} on {inst_ref_display}: Readiness Gate is BLOCKED with {blockers} blocker(s). Authority sanction prohibited."
        else:
            title = "Release Gate Satisfied — Ready for Authority Review"
            msg = f"Case {entity_id} on {inst_ref_display}: All mandatory release readiness criteria SATISFIED."

        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            title,
            msg,
        ))
        recipients_to_notify.append((
            "COMPETENT_AUTHORITY",
            None,
            None,
            title,
            msg,
        ))

    elif event_type == "RELEASE_CASE_RECOMMENDED":
        recipients_to_notify.append((
            "COMPETENT_AUTHORITY",
            None,
            None,
            "Release Petition Awaiting Final Sanction",
            f"Case {entity_id} on instrument {inst_ref_display} has been recommended by Branch Head. Final decision required.",
        ))

    elif event_type == "RELEASE_CASE_RETURNED":
        reason = details_dict.get("reason", "Additional evidence or clarification required.")
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Release Petition Returned for Clarification",
                f"Release request for {inst_ref_display} returned for clarification. Reason: {reason}",
            ))
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            "Release Petition Returned by Decision-Maker",
            f"Case {entity_id} on {inst_ref_display} returned for clarification.",
        ))

    elif event_type == "RELEASE_CASE_REJECTED":
        reason = details_dict.get("reason", "Regulatory obligations or release conditions not satisfied.")
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Release Petition Rejected",
                f"Release petition for {inst_ref_display} was rejected. Rationale: {reason}",
            ))

    elif event_type == "RELEASE_CASE_APPROVED":
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Release Petition Sanctioned",
                f"Release approval granted for instrument {inst_ref_display}. Release order generation in progress.",
            ))
        recipients_to_notify.append((
            "FINANCE_OFFICER",
            None,
            None,
            "Release Sanctioned — Release Order Required",
            f"Release approved for case {entity_id} on {inst_ref_display}. Awaiting release order recording.",
        ))

    elif event_type == "RELEASE_ORDER_RECORDED":
        order_no = details_dict.get("release_order_number", "ORDER")
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Release Order Recorded",
                f"Release Order {order_no} recorded for instrument {inst_ref_display}. Awaiting bank disbursement.",
            ))
        recipients_to_notify.append((
            "FINANCE_OFFICER",
            None,
            None,
            "Release Order Issued — Bank Disbursement Pending",
            f"Release Order {order_no} issued for {inst_ref_display}. Follow up for downstream bank confirmation.",
        ))

    elif event_type == "DOWNSTREAM_BANK_ACTION_RECORDED":
        bank_ref = details_dict.get("bank_disbursement_reference", "CONFIRMED")
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Bank Disbursement Confirmed",
                f"Bank disbursement reference {bank_ref} confirmed for {inst_ref_display}. Awaiting final case closure.",
            ))
        recipients_to_notify.append((
            "FINANCE_OFFICER",
            None,
            None,
            "Downstream Bank Disbursement Confirmed",
            f"Bank disbursement verified ({bank_ref}) for instrument {inst_ref_display}. Ready for final closure.",
        ))

    elif event_type == "RELEASE_CASE_CLOSED":
        case_no = details_dict.get("case_number", entity_id)
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "Release Case Formally Closed",
                f"Release case {case_no} for instrument {inst_ref_display} has been formally closed.",
            ))
        recipients_to_notify.append((
            "FINANCE_OFFICER",
            None,
            None,
            "Release Case Formally Closed",
            f"Release case {case_no} for instrument {inst_ref_display} has been marked CLOSED.",
        ))
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            "Release Case Closed",
            f"Release case {case_no} on instrument {inst_ref_display} is formally CLOSED.",
        ))

    elif event_type in ("MATURITY_APPROACHING", "MATURITY_MILESTONE_REMINDER"):
        days = details_dict.get("days_to_maturity", 30)
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                f"Maturity Approaching: {days} Days Remaining",
                f"Instrument {inst_ref_display} will mature in {days} days. Please review renewal requirements.",
            ))
        recipients_to_notify.append((
            "SCRUTINY_OFFICER",
            None,
            None,
            f"Instrument Maturing Soon ({days} Days)",
            f"Instrument {inst_ref_display} matures in {days} days.",
        ))

    elif event_type in ("MATURITY_OVERDUE", "ACTION_OVERDUE"):
        if institution_id:
            recipients_to_notify.append((
                "INSTITUTION_USER",
                None,
                institution_id,
                "OVERDUE: Instrument Past Maturity Date",
                f"Instrument {inst_ref_display} is past its maturity date without verified renewal. Immediate compliance action required.",
            ))
        recipients_to_notify.append((
            "SCRUTINY_OFFICER",
            None,
            None,
            "OVERDUE: Instrument Compliance Overdue",
            f"Instrument {inst_ref_display} is past maturity date without verified renewal.",
        ))
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            "Escalation Notice: Overdue FDR Instrument",
            f"Instrument {inst_ref_display} overdue past grace period. Escalation review required.",
        ))

    elif event_type in ("LIFECYCLE_EXCEPTION", "SCHEDULER_FAILURE"):
        err_msg = details_dict.get("error_message", "Unexpected lifecycle evaluation exception")
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            "Lifecycle Policy Exception Alert",
            f"Lifecycle processing exception on {inst_ref_display}: {err_msg}",
        ))

    elif event_type in ("NOTIFICATION_DELIVERY_FAILED", "NOTIFICATION_RETRY_EXHAUSTED"):
        channel = details_dict.get("channel", "EXTERNAL")
        reason = details_dict.get("failure_reason", "Provider delivery failed")
        recipients_to_notify.append((
            "BRANCH_HEAD",
            None,
            None,
            f"Notification Dispatch Failure ({channel})",
            f"Notification delivery failed for {inst_ref_display} over {channel}. Reason: {reason}",
        ))

    elif event_type == "USER_ROLE_ASSIGNMENT_CHANGED":
        target_user_id = details_dict.get("target_user_id", entity_id)
        new_role = details_dict.get("new_role", "UPDATED")
        recipients_to_notify.append((
            "USER",
            target_user_id,
            None,
            "Role Assignment Updated",
            f"Your user role has been updated to {new_role} by administrator.",
        ))

    elif event_type == "AUDIT_CHAIN_VERIFICATION_PASSED":
        total_events = details_dict.get("total_events", 0)
        recipients_to_notify.append((
            "AUDITOR",
            None,
            None,
            "Audit Cryptographic Chain Verified",
            f"Full cryptographic SHA-256 ledger integrity check PASSED ({total_events} events verified without defect).",
        ))

    elif event_type == "AUDIT_CHAIN_VERIFICATION_FAILED":
        seq_break = details_dict.get("broken_sequence_number", "UNKNOWN")
        recipients_to_notify.append((
            "AUDITOR",
            None,
            None,
            "CRITICAL: Audit Ledger Integrity Verification Failed",
            f"Cryptographic hash chain break detected at sequence #{seq_break}! Immediate tamper investigation required.",
        ))

    # Always notify System Admin with structured operational oversight notification
    admin_title = f"Operational Oversight: {event_type.replace('_', ' ').title()}"
    admin_meta = {
        "actor": {
            "id": actor_user.id if actor_user else "SYSTEM",
            "name": actor_user.full_name if actor_user else "Automated Worker",
            "email": actor_user.email if actor_user else "system@fdr.internal",
            "role": actor_user.role if actor_user else "SYSTEM",
        },
        "entity": {
            "type": entity_type,
            "id": entity_id,
            "reference": inst_ref_display,
        },
        "event_type": event_type,
        "resulting_state": resulting_state or "UPDATED",
        "timestamp": get_utc_now().isoformat(),
        "audit_event_recorded": True,
        "delivery_failed": False,
        "safe_link": safe_link,
        "details": details_dict,
        "is_mock": is_mock,
    }

    admin_message = (
        f"Actor: {actor_display} | Entity: {entity_type} {inst_ref_display} | "
        f"State: {resulting_state or 'COMMITTED'} | Link: {safe_link}"
    )

    admin_key = build_material_event_idempotency_key(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=f"{event_type}_ADMIN_OVERSIGHT",
        recipient_role="SYSTEM_ADMIN",
        extra_suffix=idempotency_suffix,
    )

    admin_notif = _create_and_deliver_in_app_notification(
        db=db,
        idempotency_key=admin_key,
        event_type=f"{event_type}_ADMIN_OVERSIGHT",
        recipient_role="SYSTEM_ADMIN",
        title=admin_title,
        message=admin_message,
        instrument_id=instrument_id,
        institution_id=institution_id,
        payload_metadata=admin_meta,
        is_mock=is_mock,
        mock_disclaimer=mock_disclaimer,
    )
    if admin_notif:
        created_notifications.append(admin_notif)

    # Deliver to each recipient in the recipient list
    for role, target_uid, target_inst_id, title, msg in recipients_to_notify:
        idem_key = build_material_event_idempotency_key(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            recipient_role=role,
            recipient_user_id=target_uid,
            extra_suffix=idempotency_suffix,
        )
        notif_item = _create_and_deliver_in_app_notification(
            db=db,
            idempotency_key=idem_key,
            event_type=event_type,
            recipient_role=role,
            title=title,
            message=msg,
            instrument_id=instrument_id,
            institution_id=target_inst_id,
            recipient_user_id=target_uid,
            payload_metadata=details_dict,
            is_mock=is_mock,
            mock_disclaimer=mock_disclaimer,
        )
        if notif_item:
            created_notifications.append(notif_item)

    return created_notifications


def get_admin_oversight_feed(
    db: Session,
    page: int = 1,
    limit: int = 50,
) -> Tuple[int, List[LifecycleNotification]]:
    """
    Returns the structured operational oversight feed exclusively for SYSTEM_ADMIN.
    """
    stmt = (
        select(LifecycleNotification)
        .where(LifecycleNotification.recipient_role == "SYSTEM_ADMIN")
        .order_by(desc(LifecycleNotification.created_at))
    )
    total = db.scalar(
        select(func.count(LifecycleNotification.id)).where(LifecycleNotification.recipient_role == "SYSTEM_ADMIN")
    ) or 0
    records = list(db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all())
    return total, records


def mark_all_inbox_as_read(
    db: Session,
    current_user: User,
) -> int:
    """
    Marks all unread inbox notifications for the current user as read.
    """
    from app.modules.lifecycle.notification_service import _get_user_inbox_filter
    now = get_utc_now()
    filters = _get_user_inbox_filter(current_user)
    filters.append(LifecycleNotification.is_read == False)  # noqa: E712

    unreads = list(db.scalars(select(LifecycleNotification).where(and_(*filters))).all())
    count = len(unreads)
    for n in unreads:
        n.is_read = True
        n.read_at = now
    db.commit()
    return count
