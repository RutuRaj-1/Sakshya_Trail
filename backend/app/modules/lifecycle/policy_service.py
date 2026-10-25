"""
Module 5 — Lifecycle Policy Service
Manages versioned lifecycle monitoring and renewal policies with approval gates,
historical preservation, and explicit synthetic demo policy labelling.
"""
import json
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from app.modules.lifecycle.models import LifecyclePolicy
from app.modules.lifecycle.enums import PolicyStatus
from app.modules.lifecycle.schemas import LifecyclePolicyCreate, LifecyclePolicyUpdate
from app.modules.audit.service import log_audit_event
from app.common.exceptions import AppException
from app.db.base import get_utc_now


DEFAULT_DEMO_POLICY_CODE = "DEMO_AICTE_FDR_POLICY"
DEMO_POLICY_LABEL = "DEMO POLICY — NOT OFFICIAL AICTE POLICY"


def get_policy_by_id(db: Session, policy_id: str) -> Optional[LifecyclePolicy]:
    return db.scalar(select(LifecyclePolicy).where(LifecyclePolicy.id == policy_id))


def get_policy_by_code_and_version(
    db: Session, policy_code: str, version: int
) -> Optional[LifecyclePolicy]:
    return db.scalar(
        select(LifecyclePolicy).where(
            and_(
                LifecyclePolicy.policy_code == policy_code,
                LifecyclePolicy.version == version,
            )
        )
    )


def list_policies(
    db: Session,
    policy_code: Optional[str] = None,
    status: Optional[str] = None,
    include_demo: bool = True,
    limit: int = 50,
) -> List[LifecyclePolicy]:
    stmt = select(LifecyclePolicy)
    filters = []
    if policy_code:
        filters.append(LifecyclePolicy.policy_code == policy_code)
    if status:
        filters.append(LifecyclePolicy.status == status)
    if not include_demo:
        filters.append(LifecyclePolicy.is_demo == False)  # noqa: E712
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.order_by(LifecyclePolicy.policy_code, desc(LifecyclePolicy.version)).limit(limit)
    return list(db.scalars(stmt).all())


def get_or_create_default_demo_policy(db: Session) -> LifecyclePolicy:
    """
    Returns the active default demo policy or provisions it if missing.
    Clearly labelled: 'DEMO POLICY — NOT OFFICIAL AICTE POLICY'.
    """
    existing = db.scalar(
        select(LifecyclePolicy).where(
            and_(
                LifecyclePolicy.policy_code == DEFAULT_DEMO_POLICY_CODE,
                LifecyclePolicy.status == PolicyStatus.ACTIVE.value,
            )
        )
    )
    if existing:
        return existing

    # Create new active demo policy
    policy = LifecyclePolicy(
        policy_code=DEFAULT_DEMO_POLICY_CODE,
        version=1,
        name="Standard Prototype Monitoring & Renewal Policy",
        description=(
            "Synthetic development baseline policy for prototype verification. "
            "Defines standard 90/60/30/15/7 day reminder intervals and action lead times. "
            "Not an officially ratified AICTE policy document."
        ),
        status=PolicyStatus.ACTIVE.value,
        is_demo=True,
        label=DEMO_POLICY_LABEL,
        scope_instrument_type="FDR",
        scope_institution_type=None,
        scope_assigned_office=None,
        timezone="Asia/Kolkata",
        reminder_intervals_days_json=json.dumps([90, 60, 30, 15, 7]),
        recipient_roles_by_interval_json=json.dumps(
            {
                "90": ["INSTITUTION_USER"],
                "60": ["INSTITUTION_USER"],
                "30": ["INSTITUTION_USER", "SCRUTINY_OFFICER"],
                "15": ["INSTITUTION_USER", "SCRUTINY_OFFICER"],
                "7": ["INSTITUTION_USER", "SCRUTINY_OFFICER", "BRANCH_HEAD"],
            }
        ),
        institution_action_lead_days=30,
        officer_action_lead_days=15,
        escalation_interval_days=7,
        escalation_target_role="BRANCH_HEAD",
        maturity_critical_lead_days=15,
        renewal_comparison_method="ISSUE_DATE_TO_MATURITY_DATE",
        max_allowed_gap_days=0,
        max_allowed_overlap_days=30,
        is_active=True,
        activated_at=get_utc_now(),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def resolve_active_policy(
    db: Session,
    instrument_type: Optional[str] = "FDR",
    institution_type: Optional[str] = None,
    assigned_office: Optional[str] = None,
) -> LifecyclePolicy:
    """
    Resolves the most specific active policy for an instrument.
    Priority:
    1. Matching (instrument_type, institution_type, assigned_office)
    2. Matching (instrument_type, institution_type)
    3. Matching instrument_type
    4. Fallback to active demo policy
    """
    stmt = (
        select(LifecyclePolicy)
        .where(
            and_(
                LifecyclePolicy.status == PolicyStatus.ACTIVE.value,
                LifecyclePolicy.is_active == True,  # noqa: E712
            )
        )
        .order_by(desc(LifecyclePolicy.version))
    )
    all_active = list(db.scalars(stmt).all())

    # Exact match on all scopes
    for p in all_active:
        if (
            (p.scope_instrument_type is None or p.scope_instrument_type == instrument_type)
            and (p.scope_institution_type is None or p.scope_institution_type == institution_type)
            and (p.scope_assigned_office is None or p.scope_assigned_office == assigned_office)
        ):
            return p

    # Fallback to default demo policy
    return get_or_create_default_demo_policy(db)


def create_policy(
    db: Session,
    payload: LifecyclePolicyCreate,
    created_by_user_id: Optional[str] = None,
    actor_email: Optional[str] = None,
) -> LifecyclePolicy:
    """
    Creates a new policy. If a policy with policy_code already exists,
    allocates the next monotonic version number.
    New policies start in DRAFT status unless explicitly approved.
    """
    latest = db.scalar(
        select(LifecyclePolicy)
        .where(LifecyclePolicy.policy_code == payload.policy_code)
        .order_by(desc(LifecyclePolicy.version))
    )
    next_version = (latest.version + 1) if latest else 1

    policy = LifecyclePolicy(
        policy_code=payload.policy_code,
        version=next_version,
        name=payload.name,
        description=payload.description,
        status=PolicyStatus.DRAFT.value,
        is_demo=payload.is_demo,
        label=payload.label if payload.is_demo else "OFFICIAL REGULATORY POLICY",
        scope_instrument_type=payload.scope_instrument_type,
        scope_institution_type=payload.scope_institution_type,
        scope_assigned_office=payload.scope_assigned_office,
        timezone=payload.timezone,
        reminder_intervals_days_json=json.dumps(payload.reminder_intervals_days),
        recipient_roles_by_interval_json=json.dumps(payload.recipient_roles_by_interval),
        institution_action_lead_days=payload.institution_action_lead_days,
        officer_action_lead_days=payload.officer_action_lead_days,
        escalation_interval_days=payload.escalation_interval_days,
        escalation_target_role=payload.escalation_target_role,
        maturity_critical_lead_days=payload.maturity_critical_lead_days,
        renewal_comparison_method=payload.renewal_comparison_method.value,
        max_allowed_gap_days=payload.max_allowed_gap_days,
        max_allowed_overlap_days=payload.max_allowed_overlap_days,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        created_by_user_id=created_by_user_id,
        is_active=True,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

    log_audit_event(
        db=db,
        action="LIFECYCLE_POLICY_CREATED",
        entity_type="LIFECYCLE_POLICY",
        entity_id=policy.id,
        actor_user_id=created_by_user_id,
        actor_email=actor_email,
        metadata={
            "policy_code": policy.policy_code,
            "version": policy.version,
            "is_demo": policy.is_demo,
        },
    )
    return policy


def approve_policy(
    db: Session,
    policy_id: str,
    approver_user_id: str,
    actor_email: Optional[str] = None,
) -> LifecyclePolicy:
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        raise AppException(status_code=404, message=f"Policy '{policy_id}' not found", code="POLICY_NOT_FOUND")

    if policy.status != PolicyStatus.DRAFT.value:
        raise AppException(
            status_code=400,
            message=f"Only DRAFT policies can be approved. Current status: {policy.status}",
            code="INVALID_POLICY_STATUS",
        )

    policy.status = PolicyStatus.APPROVED.value
    policy.approved_by_user_id = approver_user_id
    policy.approved_at = get_utc_now()
    db.commit()
    db.refresh(policy)

    log_audit_event(
        db=db,
        action="LIFECYCLE_POLICY_APPROVED",
        entity_type="LIFECYCLE_POLICY",
        entity_id=policy.id,
        actor_user_id=approver_user_id,
        actor_email=actor_email,
        metadata={"policy_code": policy.policy_code, "version": policy.version},
    )
    return policy


def activate_policy(
    db: Session,
    policy_id: str,
    activator_user_id: str,
    actor_email: Optional[str] = None,
) -> LifecyclePolicy:
    """
    Activates an APPROVED policy.
    Atomically supersedes any previous ACTIVE policy with the same policy_code.
    """
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        raise AppException(status_code=404, message=f"Policy '{policy_id}' not found", code="POLICY_NOT_FOUND")

    if policy.status not in (PolicyStatus.APPROVED.value, PolicyStatus.DRAFT.value):
        raise AppException(
            status_code=400,
            message=f"Cannot activate policy with status: {policy.status}",
            code="INVALID_POLICY_STATUS",
        )

    # Supersede existing active policies with this code
    existing_actives = list(
        db.scalars(
            select(LifecyclePolicy).where(
                and_(
                    LifecyclePolicy.policy_code == policy.policy_code,
                    LifecyclePolicy.status == PolicyStatus.ACTIVE.value,
                    LifecyclePolicy.id != policy.id,
                )
            )
        ).all()
    )
    for p in existing_actives:
        p.status = PolicyStatus.SUPERSEDED.value

    policy.status = PolicyStatus.ACTIVE.value
    policy.activated_at = get_utc_now()
    db.commit()
    db.refresh(policy)

    log_audit_event(
        db=db,
        action="LIFECYCLE_POLICY_ACTIVATED",
        entity_type="LIFECYCLE_POLICY",
        entity_id=policy.id,
        actor_user_id=activator_user_id,
        actor_email=actor_email,
        metadata={
            "policy_code": policy.policy_code,
            "version": policy.version,
            "superseded_count": len(existing_actives),
        },
    )
    return policy
