"""
Module 5 — Lifecycle Evaluation Service
Performs time-sensitive maturity assessments, due-date calculations, overdue/escalation
determinations, and material transition tracking without mutating administrative instrument states.
"""
import json
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from app.core.config import settings
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import (
    LifecyclePolicy,
    LifecycleEvaluation,
    InstrumentLineage,
)
from app.modules.lifecycle.enums import (
    MaturityStage,
    DueCondition,
    LineageRelationshipStatus,
)
from app.modules.lifecycle.clock import (
    Clock,
    SystemClock,
    SimulatedClock,
    system_clock,
    get_calendar_days_between,
    calculate_due_date,
)
from app.modules.lifecycle.policy_service import resolve_active_policy, get_policy_by_id
from app.modules.audit.service import log_audit_event
from app.common.exceptions import AppException
from app.db.base import get_utc_now


def get_latest_evaluation_for_instrument(
    db: Session, instrument_id: str
) -> Optional[LifecycleEvaluation]:
    """Retrieves the most recent lifecycle evaluation record for an instrument."""
    return db.scalar(
        select(LifecycleEvaluation)
        .where(LifecycleEvaluation.instrument_id == instrument_id)
        .order_by(desc(LifecycleEvaluation.evaluation_timestamp), desc(LifecycleEvaluation.id))
    )


def evaluate_instrument_lifecycle(
    db: Session,
    instrument_id: str,
    policy_id: Optional[str] = None,
    simulated_date: Optional[date] = None,
    clock: Optional[Clock] = None,
    force_record: bool = False,
    instrument_obj: Optional[Instrument] = None,
    actor_user_id: Optional[str] = None,
    actor_email: Optional[str] = None,
) -> LifecycleEvaluation:
    """
    Evaluates time-sensitive maturity status, institution/officer due dates,
    and overdue/escalation conditions for an instrument.
    Preserves strict separation from administrative status and trust level.
    """
    instrument = instrument_obj or db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            status_code=404,
            message=f"Instrument '{instrument_id}' not found",
            code="INSTRUMENT_NOT_FOUND",
        )

    # Resolve policy
    policy = None
    if policy_id:
        policy = get_policy_by_id(db, policy_id)
    if not policy:
        policy = resolve_active_policy(
            db,
            instrument_type=instrument.instrument_type,
            assigned_office=instrument.assigned_office,
        )

    # Determine evaluation clock & date
    from app.modules.lifecycle.clock import get_current_clock
    active_clock = clock or get_current_clock()
    if simulated_date is not None:
        if not settings.ENABLE_LIFECYCLE_DATE_ADVANCE or settings.ENVIRONMENT == "production":
            raise AppException(
                status_code=403,
                message="Simulated date advance is disabled in this environment configuration.",
                code="DATE_ADVANCE_DISABLED",
            )
        eval_date = simulated_date
        eval_ts = active_clock.now_utc()
    else:
        eval_date = active_clock.today_in_tz(policy.timezone)
        eval_ts = active_clock.now_utc()

    # Check for active renewal successor (already renewed?)
    active_lineage = db.scalar(
        select(InstrumentLineage).where(
            and_(
                InstrumentLineage.predecessor_instrument_id == instrument_id,
                InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
            )
        )
    )

    # Maturity evaluation
    days_to_maturity: Optional[int] = None
    maturity_stage: str = MaturityStage.NOT_EVALUABLE.value
    inst_due_date: Optional[date] = None
    officer_due_date: Optional[date] = None
    is_overdue: bool = False
    is_escalated: bool = False
    escalation_role: Optional[str] = None
    due_condition: str = DueCondition.NORMAL.value
    matched_interval: Optional[int] = None

    if instrument.maturity_date is None:
        maturity_stage = MaturityStage.NOT_EVALUABLE.value
        due_condition = DueCondition.NORMAL.value
    else:
        days_to_maturity = (instrument.maturity_date - eval_date).days
        inst_due_date = calculate_due_date(instrument.maturity_date, policy.institution_action_lead_days)
        officer_due_date = calculate_due_date(instrument.maturity_date, policy.officer_action_lead_days)

        # Stage determination
        if days_to_maturity < 0:
            maturity_stage = MaturityStage.EXPIRED.value
        elif days_to_maturity == 0:
            maturity_stage = MaturityStage.MATURED.value
        elif days_to_maturity <= policy.maturity_critical_lead_days:
            maturity_stage = MaturityStage.CRITICAL_WINDOW.value
        elif days_to_maturity <= policy.institution_action_lead_days:
            maturity_stage = MaturityStage.MATURING_SOON.value
        else:
            maturity_stage = MaturityStage.ACTIVE.value

        # Check for discrete reminder intervals if configured
        configured_intervals = policy.reminder_intervals_days
        if configured_intervals and days_to_maturity in configured_intervals:
            matched_interval = days_to_maturity

        # Overdue / Escalation logic (only if not already renewed)
        if not active_lineage:
            if inst_due_date and eval_date > inst_due_date:
                is_overdue = True
                escalation_threshold = inst_due_date + timedelta(days=policy.escalation_interval_days)
                if eval_date > escalation_threshold:
                    is_escalated = True
                    escalation_role = policy.escalation_target_role
                    due_condition = DueCondition.ESCALATED.value
                else:
                    due_condition = DueCondition.OVERDUE.value
            elif officer_due_date and eval_date >= officer_due_date:
                due_condition = DueCondition.OFFICER_ACTION_DUE.value
            elif inst_due_date and eval_date >= inst_due_date:
                due_condition = DueCondition.INSTITUTION_ACTION_DUE.value
            elif matched_interval is not None:
                due_condition = DueCondition.REMINDER_DUE.value
            else:
                due_condition = DueCondition.NORMAL.value
        else:
            # Renewed predecessor is covered by its successor
            due_condition = DueCondition.NORMAL.value

    # Check for existing record on the exact same evaluation date for idempotency
    existing_record = db.scalar(
        select(LifecycleEvaluation).where(
            and_(
                LifecycleEvaluation.instrument_id == instrument_id,
                LifecycleEvaluation.evaluation_date == eval_date,
            )
        )
    )

    # Prior evaluation comparison for material transitions
    if existing_record:
        prior = db.scalar(
            select(LifecycleEvaluation)
            .where(
                and_(
                    LifecycleEvaluation.instrument_id == instrument_id,
                    LifecycleEvaluation.id != existing_record.id,
                    LifecycleEvaluation.evaluation_date < eval_date,
                )
            )
            .order_by(desc(LifecycleEvaluation.evaluation_date), desc(LifecycleEvaluation.evaluation_timestamp))
        )
    else:
        prior = get_latest_evaluation_for_instrument(db, instrument_id)

    is_material = False
    if prior is None:
        is_material = True
    else:
        if (
            prior.maturity_stage != maturity_stage
            or prior.is_overdue != is_overdue
            or prior.is_escalated != is_escalated
            or prior.due_condition != due_condition
        ):
            is_material = True

    metadata_str = json.dumps(
        {
            "instrument_reference": instrument.reference_number,
            "bank_name": instrument.bank_name,
            "amount": str(instrument.amount),
            "policy_code": policy.policy_code,
            "is_demo_policy": policy.is_demo,
        }
    )

    if existing_record:
        # Idempotent in-place update
        existing_record.policy_id = policy.id
        existing_record.policy_version = policy.version
        existing_record.evaluation_timestamp = eval_ts
        existing_record.evaluation_timezone = policy.timezone
        existing_record.days_to_maturity = days_to_maturity
        existing_record.maturity_stage = maturity_stage
        existing_record.institution_action_due_date = inst_due_date
        existing_record.officer_action_due_date = officer_due_date
        existing_record.is_overdue = is_overdue
        existing_record.is_escalated = is_escalated
        existing_record.escalation_role = escalation_role
        existing_record.due_condition = due_condition
        existing_record.matched_reminder_interval_days = matched_interval
        existing_record.lineage_relationship_id = active_lineage.id if active_lineage else None
        existing_record.is_material_transition = is_material
        existing_record.prior_evaluation_id = prior.id if prior else None
        existing_record.metadata_json = metadata_str
        eval_record = existing_record
    else:
        eval_record = LifecycleEvaluation(
            instrument_id=instrument_id,
            policy_id=policy.id,
            policy_version=policy.version,
            evaluation_date=eval_date,
            evaluation_timestamp=eval_ts,
            evaluation_timezone=policy.timezone,
            days_to_maturity=days_to_maturity,
            maturity_stage=maturity_stage,
            institution_action_due_date=inst_due_date,
            officer_action_due_date=officer_due_date,
            is_overdue=is_overdue,
            is_escalated=is_escalated,
            escalation_role=escalation_role,
            due_condition=due_condition,
            matched_reminder_interval_days=matched_interval,
            lineage_relationship_id=active_lineage.id if active_lineage else None,
            is_material_transition=is_material,
            prior_evaluation_id=prior.id if prior else None,
            metadata_json=metadata_str,
        )
        db.add(eval_record)

    db.commit()
    db.refresh(eval_record)

    # Emit audit event for material lifecycle changes
    if is_material and (not existing_record or existing_record.is_material_transition):
        log_audit_event(
            db=db,
            action="LIFECYCLE_STAGE_TRANSITION",
            entity_type="LIFECYCLE_EVALUATION",
            entity_id=eval_record.id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            metadata={
                "instrument_id": instrument_id,
                "maturity_stage": maturity_stage,
                "due_condition": due_condition,
                "is_overdue": is_overdue,
                "is_escalated": is_escalated,
                "days_to_maturity": days_to_maturity,
            },
        )

    return eval_record


def evaluate_batch_instruments(
    db: Session,
    instrument_ids: Optional[List[str]] = None,
    institution_id: Optional[str] = None,
    simulated_date: Optional[date] = None,
    limit: int = 100,
    actor_user_id: Optional[str] = None,
    actor_email: Optional[str] = None,
) -> Tuple[int, int, List[LifecycleEvaluation]]:
    """
    Evaluates lifecycle status across a set or query of instruments.
    Returns (total_evaluated, material_transitions_count, list_of_evaluations).
    """
    stmt = select(Instrument.id)
    filters = []
    if instrument_ids:
        filters.append(Instrument.id.in_(instrument_ids))
    if institution_id:
        filters.append(Instrument.institution_id == institution_id)
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.limit(limit)

    ids = list(db.scalars(stmt).all())
    evaluations: List[LifecycleEvaluation] = []
    material_count = 0

    for iid in ids:
        ev = evaluate_instrument_lifecycle(
            db=db,
            instrument_id=iid,
            simulated_date=simulated_date,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
        )
        evaluations.append(ev)
        if ev.is_material_transition:
            material_count += 1

    return len(evaluations), material_count, evaluations


def get_latest_evaluation_for_instrument(
    db: Session, instrument_id: str
) -> Optional[LifecycleEvaluation]:
    """
    Retrieves the most recent lifecycle evaluation record for an instrument.
    """
    return db.scalar(
        select(LifecycleEvaluation)
        .where(LifecycleEvaluation.instrument_id == instrument_id)
        .order_by(desc(LifecycleEvaluation.created_at))
    )

