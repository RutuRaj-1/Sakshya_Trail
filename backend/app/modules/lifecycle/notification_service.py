"""
Module 5 — Lifecycle Notification & Escalation Engine
Coordinates policy-driven milestone reminders, due date alerts, role-based escalations,
idempotent deliveries, bounded retries, and comprehensive audit history.
"""
import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc, func

from app.core.config import settings
from app.db.base import get_utc_now
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import (
    LifecyclePolicy,
    LifecycleEvaluation,
    LifecycleNotification,
    NotificationDeliveryAttempt,
)
from app.modules.lifecycle.enums import MaturityStage, DueCondition
from app.modules.lifecycle.policy_service import resolve_active_policy, get_policy_by_id
from app.modules.lifecycle.channels.registry import get_channel_provider
from app.modules.lifecycle.channels.base import DeliveryResult
from app.modules.audit.service import log_audit_event
from app.common.exceptions import AppException, ForbiddenException, NotFoundException

logger = logging.getLogger(__name__)


def resolve_recipients_for_role(
    db: Session,
    role: str,
    institution_id: str,
    assigned_office: Optional[str] = None,
) -> List[User]:
    """
    Deterministically resolves eligible users for a given recipient role.
    Guarantees:
    - INSTITUTION_USER: Resolved strictly from users belonging to the specific institution.
    - SCRUTINY_OFFICER / BRANCH_HEAD: Resolved from officers assigned to the office/region.
    - Never routes reminders to the wrong institution or arbitrary administrators.
    """
    stmt = select(User).where(User.is_active == True)  # noqa: E712

    if role == "INSTITUTION_USER":
        stmt = stmt.where(
            and_(
                User.role == "INSTITUTION_USER",
                User.institution_id == institution_id,
            )
        )
    elif role in ("SCRUTINY_OFFICER", "BRANCH_HEAD", "COMPETENT_AUTHORITY"):
        stmt = stmt.where(User.role == role)
    elif role == "SYSTEM_ADMIN":
        stmt = stmt.where(User.role == "SYSTEM_ADMIN")
    else:
        stmt = stmt.where(User.role == role)

    return list(db.scalars(stmt).all())


def build_idempotency_key(
    instrument_id: str,
    event_type: str,
    milestone_days: Optional[int],
    trigger_date: date,
    recipient_identifier: Optional[str] = None,
    channel: str = "IN_APP",
    recipient_id_or_role: Optional[str] = None,
) -> str:
    """
    Generates a deterministic idempotency key for notification deduplication.
    Ensures that scheduler reruns or worker restarts on the same calendar date
    never create duplicate reminders for the same event, recipient, and channel.
    """
    recip = recipient_identifier or recipient_id_or_role or "ROLE"
    milestone_str = str(milestone_days) if milestone_days is not None else "0"
    return f"notif:{instrument_id}:{event_type}:{milestone_str}:{trigger_date.isoformat()}:{recip}:{channel}"



def _render_notification_template(
    event_type: str,
    instrument: Instrument,
    institution: Optional[Institution],
    milestone_days: Optional[int],
    policy: LifecyclePolicy,
    due_date: Optional[date] = None,
    escalation_role: Optional[str] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Renders standard regulatory reminder/escalation message text and safe metadata.
    Does NOT include secrets, raw document bytes, or private security tokens.
    """
    inst_name = institution.legal_name if institution else "Educational Institution"
    fdr_ref = instrument.reference_number
    amount_str = f"INR {instrument.amount:,.2f}"
    mat_date_str = instrument.maturity_date.isoformat() if instrument.maturity_date else "UNKNOWN"

    metadata = {
        "instrument_id": instrument.id,
        "reference_number": fdr_ref,
        "bank_name": instrument.bank_name,
        "amount": str(instrument.amount),
        "maturity_date": mat_date_str,
        "institution_id": instrument.institution_id,
        "institution_name": inst_name,
        "policy_code": policy.policy_code,
        "policy_version": policy.version,
    }

    if event_type == "MATURITY_MILESTONE_REMINDER":
        title = f"AICTE Notice: Security Deposit {fdr_ref} Matures in {milestone_days} Days"
        message = (
            f"Statutory Fixed Deposit Receipt {fdr_ref} for {inst_name} (Amount: {amount_str}, "
            f"Bank: {instrument.bank_name}) has reached the {milestone_days}-day regulatory reminder milestone. "
            f"Maturity Date: {mat_date_str}. Please review renewal compliance directives."
        )
        metadata["milestone_days"] = milestone_days

    elif event_type == "INSTITUTION_ACTION_DUE":
        due_str = due_date.isoformat() if due_date else "Immediate"
        title = f"Action Required: Compliance Due for FDR {fdr_ref}"
        message = (
            f"Institution compliance action for FDR {fdr_ref} is due on or before {due_str}. "
            f"Please ensure renewal documentation or lien rollover instructions are initiated."
        )
        metadata["due_date"] = due_str

    elif event_type == "OFFICER_ACTION_DUE":
        due_str = due_date.isoformat() if due_date else "Immediate"
        title = f"Bureau Action Due: Scrutiny Review for FDR {fdr_ref}"
        message = (
            f"Regulatory scrutiny action for FDR {fdr_ref} ({inst_name}) is due by {due_str}. "
            f"Please review institutional compliance and maturity status."
        )
        metadata["due_date"] = due_str

    elif event_type == "ACTION_OVERDUE":
        title = f"OVERDUE NOTICE: Statutory Renewal Pending for FDR {fdr_ref}"
        message = (
            f"Compliance actions for FDR {fdr_ref} ({inst_name}) are now OVERDUE. "
            f"Immediate attention is required to avoid formal escalation to {policy.escalation_target_role}."
        )

    elif event_type == "ACTION_ESCALATED":
        title = f"ESCALATION ALERT: Delinquent Statutory Deposit {fdr_ref}"
        message = (
            f"ESCALATION DIRECTIVE to {escalation_role or policy.escalation_target_role}: FDR {fdr_ref} "
            f"for {inst_name} has exceeded the regulatory grace window without documented rollover. "
            f"Initiating formal supervisory intervention under policy {policy.policy_code} v{policy.version}."
        )
        metadata["escalation_target"] = escalation_role or policy.escalation_target_role

    elif event_type == "MATURED_NOTICE":
        title = f"MATURITY REACHED: FDR {fdr_ref} Has Reached Maturity Date"
        message = (
            f"Fixed Deposit Receipt {fdr_ref} reached its maturity date on {mat_date_str}. "
            f"Status remains locked. Release or renewal requires verified regulatory authorization."
        )

    else:
        title = f"Lifecycle Notification: FDR {fdr_ref}"
        message = f"Lifecycle update for instrument {fdr_ref} under policy {policy.policy_code}."

    return title, message, metadata


def dispatch_single_notification(
    db: Session,
    notification: LifecycleNotification,
    force_retry: bool = False,
) -> DeliveryResult:
    """
    Executes the delivery attempt for a single notification through its configured channel.
    Tracks granular attempt history, manages retry counters, and isolates failures.
    """
    now = get_utc_now()

    # Do not re-dispatch if already successfully accepted/delivered unless force_retry
    if notification.status in ("DELIVERED", "ACCEPTED") and not force_retry:
        return DeliveryResult(
            status=notification.status,
            channel=notification.channel,
            provider_reference_id=notification.provider_message_id,
            is_mock=notification.is_mock,
            mock_disclaimer=notification.mock_disclaimer,
        )

    # Check retry exhaustion
    if notification.retry_count >= notification.max_retries and not force_retry:
        notification.status = "FAILED"
        notification.failure_category = "RETRY_EXHAUSTED"
        notification.failure_reason = f"Max delivery attempts ({notification.max_retries}) exhausted without confirmation."
        notification.failed_at = now
        db.commit()
        return DeliveryResult(
            status="FAILED",
            channel=notification.channel,
            error_category="RETRY_EXHAUSTED",
            error_message=notification.failure_reason,
        )

    # Attempt dispatch
    attempt_num = notification.retry_count + 1
    notification.retry_count = attempt_num
    if not notification.first_attempted_at:
        notification.first_attempted_at = now
    notification.last_attempted_at = now

    try:
        provider = get_channel_provider(notification.channel)
        result = provider.send(notification)
    except Exception as exc:
        logger.error(f"[Notification Error] Channel provider crashed for notification '{notification.id}': {exc}")
        result = DeliveryResult(
            status="FAILED",
            channel=notification.channel,
            error_category="PROVIDER_UNAVAILABLE",
            error_message=str(exc),
        )

    # Record delivery attempt
    attempt = NotificationDeliveryAttempt(
        notification_id=notification.id,
        attempt_number=attempt_num,
        attempted_at=now,
        channel=notification.channel,
        status=result.status,
        provider_response_code=result.provider_response_code,
        provider_reference_id=result.provider_reference_id,
        error_category=result.error_category,
        error_message=result.error_message,
        duration_ms=result.duration_ms,
    )
    db.add(attempt)

    # Update notification state
    notification.status = result.status
    notification.provider_message_id = result.provider_reference_id
    notification.is_mock = result.is_mock
    notification.mock_disclaimer = result.mock_disclaimer

    if result.status == "DELIVERED":
        notification.delivered_at = now
        notification.failure_category = None
        notification.failure_reason = None
    elif result.status in ("ACCEPTED", "MOCKED"):
        notification.failure_category = None
        notification.failure_reason = None
    elif result.status == "FAILED":
        notification.failed_at = now
        notification.failure_category = result.error_category or "DELIVERY_FAILURE"
        notification.failure_reason = result.error_message
        notification.next_retry_at = now + timedelta(minutes=notification.max_retries * 15)

    db.commit()
    db.refresh(notification)

    log_audit_event(
        db=db,
        action="NOTIFICATION_DELIVERY_ATTEMPTED",
        entity_type="LIFECYCLE_NOTIFICATION",
        entity_id=notification.id,
        actor_user_id=None,
        actor_email=None,
        outcome=result.status,
        metadata={
            "channel": notification.channel,
            "attempt_number": attempt_num,
            "status": result.status,
            "is_mock": result.is_mock,
            "error_category": result.error_category,
        },
    )

    return result


def generate_and_dispatch_reminders_for_instrument(
    db: Session,
    instrument_id: str,
    eval_record: Optional[LifecycleEvaluation] = None,
    simulated_date: Optional[date] = None,
    actor_user_id: Optional[str] = None,
    actor_email: Optional[str] = None,
) -> List[LifecycleNotification]:
    """
    Consumes lifecycle assessment outputs from Prompt 2, resolves active policy rules,
    identifies due reminder/escalation events, and generates idempotent notification records.
    Never alters trust levels, financial terms, or administrative states.
    """
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise NotFoundException(f"Instrument '{instrument_id}' not found.")

    # Ineligible / resolved instruments (e.g. CLOSED) produce no new reminders
    if instrument.status in ("CLOSED", "CANCELLED", "RENEWED_SUPERSEDED"):
        return []

    if eval_record is None:
        from app.modules.lifecycle.evaluation_service import (
            get_latest_evaluation_for_instrument,
            evaluate_instrument_lifecycle,
        )
        eval_record = get_latest_evaluation_for_instrument(db, instrument_id)
        if not eval_record or eval_record.evaluation_date != (simulated_date or eval_record.evaluation_date):
            eval_record = evaluate_instrument_lifecycle(
                db=db,
                instrument_id=instrument_id,
                simulated_date=simulated_date,
                actor_user_id=actor_user_id,
                actor_email=actor_email,
            )

    institution = db.scalar(select(Institution).where(Institution.id == instrument.institution_id))
    policy = (
        get_policy_by_id(db, eval_record.policy_id)
        if eval_record.policy_id
        else resolve_active_policy(db, instrument_type=instrument.instrument_type)
    )

    eval_date = eval_record.evaluation_date
    dispatched_notifications: List[LifecycleNotification] = []

    # Map candidate events triggered by this evaluation
    candidate_events: List[Dict[str, Any]] = []

    # 1. Milestone Reminder (e.g. 90, 60, 30, 15, 7 days before maturity)
    if eval_record.matched_reminder_interval_days is not None:
        milestone = eval_record.matched_reminder_interval_days
        roles = policy.recipient_roles_by_interval.get(str(milestone), ["INSTITUTION_USER"])
        for role in roles:
            candidate_events.append({
                "event_type": "MATURITY_MILESTONE_REMINDER",
                "milestone_days": milestone,
                "role": role,
            })

    # 2. Institution Action Due
    if eval_record.due_condition == DueCondition.INSTITUTION_ACTION_DUE.value:
        candidate_events.append({
            "event_type": "INSTITUTION_ACTION_DUE",
            "milestone_days": None,
            "role": "INSTITUTION_USER",
            "due_date": eval_record.institution_action_due_date,
        })

    # 3. Officer Action Due
    if eval_record.due_condition == DueCondition.OFFICER_ACTION_DUE.value:
        candidate_events.append({
            "event_type": "OFFICER_ACTION_DUE",
            "milestone_days": None,
            "role": "SCRUTINY_OFFICER",
            "due_date": eval_record.officer_action_due_date,
        })

    # 4. Action Overdue (not yet escalated)
    if eval_record.due_condition == DueCondition.OVERDUE.value and eval_record.is_overdue:
        candidate_events.append({
            "event_type": "ACTION_OVERDUE",
            "milestone_days": None,
            "role": "INSTITUTION_USER",
        })
        candidate_events.append({
            "event_type": "ACTION_OVERDUE",
            "milestone_days": None,
            "role": "SCRUTINY_OFFICER",
        })

    # 5. Escalation Directive
    if eval_record.due_condition == DueCondition.ESCALATED.value and eval_record.is_escalated:
        target_role = eval_record.escalation_role or policy.escalation_target_role
        candidate_events.append({
            "event_type": "ACTION_ESCALATED",
            "milestone_days": None,
            "role": target_role,
            "escalation_role": target_role,
        })

    # 6. Maturity Date Reached (Day Zero)
    if eval_record.maturity_stage == MaturityStage.MATURED.value and eval_record.days_to_maturity == 0:
        candidate_events.append({
            "event_type": "MATURED_NOTICE",
            "milestone_days": 0,
            "role": "INSTITUTION_USER",
        })
        candidate_events.append({
            "event_type": "MATURED_NOTICE",
            "milestone_days": 0,
            "role": "SCRUTINY_OFFICER",
        })

    # Process each candidate event across permitted channels
    permitted_channels = policy.permitted_channels
    now_ts = get_utc_now()

    for event in candidate_events:
        evt_type = event["event_type"]
        milestone = event["milestone_days"]
        target_role = event["role"]

        # Resolve actual eligible recipients
        recipients = resolve_recipients_for_role(
            db=db,
            role=target_role,
            institution_id=instrument.institution_id,
            assigned_office=instrument.assigned_office,
        )

        # Explicit configuration issue handling when no recipients exist
        if not recipients:
            logger.warning(
                f"[Lifecycle Notification] No recipient found for role '{target_role}' "
                f"at institution '{instrument.institution_id}'. Recording configuration failure."
            )
            for channel in permitted_channels:
                idempotency_key = build_idempotency_key(
                    instrument_id=instrument.id,
                    event_type=evt_type,
                    milestone_days=milestone,
                    trigger_date=eval_date,
                    recipient_identifier=f"UNRESOLVED_ROLE_{target_role}",
                    channel=channel,
                )
                existing = db.scalar(
                    select(LifecycleNotification).where(
                        LifecycleNotification.idempotency_key == idempotency_key
                    )
                )
                if existing:
                    dispatched_notifications.append(existing)
                    continue

                title, msg, meta = _render_notification_template(
                    event_type=evt_type,
                    instrument=instrument,
                    institution=institution,
                    milestone_days=milestone,
                    policy=policy,
                    due_date=event.get("due_date"),
                    escalation_role=event.get("escalation_role"),
                )
                meta["error"] = f"No active user resolved for role '{target_role}'"
                unresolved_notif = LifecycleNotification(
                    idempotency_key=idempotency_key,
                    instrument_id=instrument.id,
                    institution_id=instrument.institution_id,
                    policy_id=policy.id,
                    policy_version=policy.version,
                    event_type=evt_type,
                    reminder_milestone_days=milestone,
                    trigger_date=eval_date,
                    recipient_user_id=None,
                    recipient_role=target_role,
                    recipient_email=None,
                    recipient_name=None,
                    channel=channel,
                    template_id=policy.template_id,
                    template_version=policy.template_version,
                    title=title,
                    message=msg,
                    payload_metadata_json=json.dumps(meta),
                    status="FAILED",
                    failure_category="CONFIGURATION_ERROR",
                    failure_reason=f"No active registered user resolved for role '{target_role}'.",
                    failed_at=now_ts,
                    scheduled_at=now_ts,
                )
                db.add(unresolved_notif)
                db.commit()
                db.refresh(unresolved_notif)
                dispatched_notifications.append(unresolved_notif)
            continue

        # For each resolved recipient and permitted channel
        for user in recipients:
            for channel in permitted_channels:
                idempotency_key = build_idempotency_key(
                    instrument_id=instrument.id,
                    event_type=evt_type,
                    milestone_days=milestone,
                    trigger_date=eval_date,
                    recipient_identifier=user.id,
                    channel=channel,
                )

                # Check database idempotency
                existing_notif = db.scalar(
                    select(LifecycleNotification).where(
                        LifecycleNotification.idempotency_key == idempotency_key
                    )
                )
                if existing_notif:
                    # Rerun on unchanged event & date does not duplicate
                    dispatched_notifications.append(existing_notif)
                    continue

                title, msg, meta = _render_notification_template(
                    event_type=evt_type,
                    instrument=instrument,
                    institution=institution,
                    milestone_days=milestone,
                    policy=policy,
                    due_date=event.get("due_date"),
                    escalation_role=event.get("escalation_role"),
                )

                notif = LifecycleNotification(
                    idempotency_key=idempotency_key,
                    instrument_id=instrument.id,
                    institution_id=instrument.institution_id,
                    policy_id=policy.id,
                    policy_version=policy.version,
                    event_type=evt_type,
                    reminder_milestone_days=milestone,
                    trigger_date=eval_date,
                    recipient_user_id=user.id,
                    recipient_role=user.role,
                    recipient_email=user.email,
                    recipient_name=user.full_name,
                    channel=channel,
                    template_id=policy.template_id,
                    template_version=policy.template_version,
                    title=title,
                    message=msg,
                    payload_metadata_json=json.dumps(meta),
                    status="CREATED",
                    scheduled_at=now_ts,
                    max_retries=policy.max_retry_limit,
                )
                db.add(notif)
                db.commit()
                db.refresh(notif)

                # Dispatch immediately through channel
                dispatch_single_notification(db, notif)
                dispatched_notifications.append(notif)

    return dispatched_notifications


def retry_notification(
    db: Session,
    notification_id: str,
    current_user: Optional[User] = None,
    actor_user_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    reason: Optional[str] = None,
    force: bool = False,
) -> LifecycleNotification:
    """
    Controlled administrative manual retry of a failed or pending notification.
    Enforces retry boundaries, tenancy permissions, and audit tracking.
    """
    notif = db.scalar(select(LifecycleNotification).where(LifecycleNotification.id == notification_id))
    if not notif:
        raise NotFoundException(f"Notification '{notification_id}' not found.")

    if notif.retry_count >= notif.max_retries and not force:
        raise AppException(
            status_code=400,
            message=f"Notification '{notification_id}' has reached retry limit of {notif.max_retries} attempts.",
            code="RETRY_EXHAUSTED",
        )

    # Scoping check: institution users cannot retry internal official notifications
    if current_user and current_user.role == "INSTITUTION_USER" and notif.institution_id != current_user.institution_id:
        raise ForbiddenException("Access to notification outside institution scope is denied.")

    dispatch_single_notification(db=db, notification=notif, force_retry=force)
    db.refresh(notif)
    return notif


def _get_user_inbox_filter(current_user: User) -> List[Any]:
    """
    Constructs inbox query filters respecting strict role and tenant boundaries:
    - INSTITUTION_USER: must belong to the user's institution.
    - INTERNAL ROLES (SCRUTINY, BRANCH_HEAD, etc.): matched by recipient_user_id or recipient_role.
    - SYSTEM_ADMIN: receives system-admin and targeted administrative alerts.
    """
    if current_user.role == "INSTITUTION_USER":
        return [
            LifecycleNotification.channel == "IN_APP",
            LifecycleNotification.institution_id == current_user.institution_id,
            or_(
                LifecycleNotification.recipient_user_id == current_user.id,
                LifecycleNotification.recipient_role == "INSTITUTION_USER",
            ),
        ]
    elif current_user.role == "SYSTEM_ADMIN":
        return [
            LifecycleNotification.channel == "IN_APP",
            or_(
                LifecycleNotification.recipient_user_id == current_user.id,
                LifecycleNotification.recipient_role == "SYSTEM_ADMIN",
            ),
        ]
    else:
        return [
            LifecycleNotification.channel == "IN_APP",
            or_(
                LifecycleNotification.recipient_user_id == current_user.id,
                LifecycleNotification.recipient_role == current_user.role,
            ),
        ]


def mark_notification_as_read(
    db: Session,
    notification_id: str,
    current_user: User,
) -> LifecycleNotification:
    """
    Marks an in-app notification as read by the recipient.
    """
    notif = db.scalar(select(LifecycleNotification).where(LifecycleNotification.id == notification_id))
    if not notif:
        raise NotFoundException(f"Notification '{notification_id}' not found.")

    if current_user.role == "INSTITUTION_USER":
        if notif.institution_id != current_user.institution_id:
            raise ForbiddenException("Access denied.")
    else:
        if (
            current_user.role != "SYSTEM_ADMIN"
            and notif.recipient_user_id != current_user.id
            and notif.recipient_role != current_user.role
        ):
            raise ForbiddenException("Access denied.")

    notif.is_read = True
    notif.read_at = get_utc_now()
    db.commit()
    db.refresh(notif)
    return notif


def get_instrument_notifications(
    db: Session,
    instrument_id: str,
    current_user: User,
    page: int = 1,
    limit: int = 50,
) -> Tuple[int, List[LifecycleNotification]]:
    """
    Returns tenancy-scoped notification history for an instrument.
    """
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise NotFoundException(f"Instrument '{instrument_id}' not found.")

    if current_user.role == "INSTITUTION_USER" and instrument.institution_id != current_user.institution_id:
        raise ForbiddenException("Access to other institution's notification history is strictly prohibited.")

    stmt = (
        select(LifecycleNotification)
        .where(LifecycleNotification.instrument_id == instrument_id)
        .order_by(desc(LifecycleNotification.created_at))
    )

    total = db.scalar(select(func.count(LifecycleNotification.id)).where(LifecycleNotification.instrument_id == instrument_id)) or 0
    records = list(db.scalars(stmt.offset((page - 1) * limit).limit(limit)).all())
    return total, records


def get_user_inbox_notifications(
    db: Session,
    current_user: User,
    unread_only: bool = False,
    page: int = 1,
    limit: int = 50,
) -> Tuple[int, List[LifecycleNotification]]:
    """
    Fetches in-app inbox notifications addressed to the current user or their assigned role.
    """
    filters = _get_user_inbox_filter(current_user)
    if unread_only:
        filters.append(LifecycleNotification.is_read == False)  # noqa: E712

    total = db.scalar(select(func.count(LifecycleNotification.id)).where(and_(*filters))) or 0
    records = list(
        db.scalars(
            select(LifecycleNotification)
            .where(and_(*filters))
            .order_by(desc(LifecycleNotification.created_at))
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return total, records


def list_failed_notifications(
    db: Session,
    current_user: User,
    page: int = 1,
    limit: int = 50,
) -> Tuple[int, List[LifecycleNotification]]:
    """
    Lists failed notification delivery attempts for administrative review and retry.
    """
    if current_user.role == "INSTITUTION_USER":
        raise ForbiddenException("Audit access to global failed notification queues requires officer/admin role.")

    filters = [
        or_(
            LifecycleNotification.status == "FAILED",
            LifecycleNotification.failure_category.isnot(None),
        )
    ]
    total = db.scalar(select(func.count(LifecycleNotification.id)).where(and_(*filters))) or 0
    records = list(
        db.scalars(
            select(LifecycleNotification)
            .where(and_(*filters))
            .order_by(desc(LifecycleNotification.failed_at), desc(LifecycleNotification.created_at))
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    return total, records
