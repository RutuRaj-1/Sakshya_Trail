"""
Module 5 — Lifecycle Scheduler & Batch Worker Engine
Executes bounded daily maturity scans and on-demand evaluations with lease-lock concurrency protection,
per-record error isolation, and detailed diagnostics tracking.
"""
import uuid
import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func

from app.core.config import settings
from app.db.base import get_utc_now
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import (
    LifecycleJobRun,
    LifecycleEvaluation,
    LifecyclePolicy,
)
from app.modules.lifecycle.enums import MaturityStage
from app.modules.lifecycle.clock import Clock, get_current_clock
from app.modules.lifecycle.policy_service import resolve_active_policy
from app.modules.lifecycle.evaluation_service import evaluate_instrument_lifecycle
from app.modules.lifecycle.schemas import SchedulerRunStatusResponse, LifecycleJobRunResponse
from app.modules.audit.service import log_audit_event
from app.common.exceptions import AppException

logger = logging.getLogger(__name__)


def acquire_job_lease(
    db: Session,
    job_type: str,
    trigger_source: str,
    evaluation_date: date,
    evaluation_timezone: str,
    worker_instance_id: Optional[str] = None,
    lease_duration_minutes: int = 5,
) -> LifecycleJobRun:
    """
    Acquires a concurrency lease for an evaluation scan.
    Guarantees:
    1. If an unexpired job is already running, rejects concurrent execution with 409.
    2. Recovers automatically from stale/crashed runs whose lease has expired.
    3. Records worker instance ID and lease expiration timestamp.
    """
    now = get_utc_now()
    worker_id = worker_instance_id or f"worker-{uuid.uuid4().hex[:8]}"

    # Check for actively running job with valid lease
    active_job = db.scalar(
        select(LifecycleJobRun)
        .where(
            and_(
                LifecycleJobRun.status == "RUNNING",
                LifecycleJobRun.lease_expires_at > now,
            )
        )
    )
    if active_job:
        raise AppException(
            status_code=409,
            message=(
                f"Concurrent evaluation blocked. Job '{active_job.id}' ({active_job.job_type}) "
                f"is currently executing on worker '{active_job.worker_instance_id}'. "
                f"Active lease valid until {active_job.lease_expires_at.isoformat()}."
            ),
            code="CONCURRENT_JOB_RUNNING",
        )

    # Clean up any stale crashed jobs where lease has expired
    stale_jobs = list(
        db.scalars(
            select(LifecycleJobRun).where(
                and_(
                    LifecycleJobRun.status == "RUNNING",
                    LifecycleJobRun.lease_expires_at <= now,
                )
            )
        ).all()
    )
    for stale in stale_jobs:
        stale.status = "FAILED"
        stale.completed_at = now
        stale.error_summary_json = json.dumps(
            {"error": "Lease expired without completion. Worker process likely terminated unexpectedly."}
        )
    if stale_jobs:
        db.commit()

    lease_expiration = now + timedelta(minutes=lease_duration_minutes)
    job_run = LifecycleJobRun(
        job_type=job_type,
        status="RUNNING",
        trigger_source=trigger_source,
        started_at=now,
        evaluation_date=evaluation_date,
        evaluation_timezone=evaluation_timezone,
        worker_instance_id=worker_id,
        lease_expires_at=lease_expiration,
    )
    db.add(job_run)
    db.commit()
    db.refresh(job_run)
    return job_run


def execute_lifecycle_scan_job(
    db: Session,
    job_type: str = "DAILY_MATURITY_SCAN",
    trigger_source: str = "SCHEDULED",
    batch_size: int = 50,
    simulated_date: Optional[date] = None,
    worker_instance_id: Optional[str] = None,
    lease_duration_minutes: int = 5,
    force_reevaluation: bool = False,
    actor_user_id: Optional[str] = None,
    actor_email: Optional[str] = None,
) -> LifecycleJobRun:
    """
    Executes a bounded batch lifecycle scan across all eligible registered instruments.
    Key properties:
    - Bounded memory footprint (paginated/chunked streaming).
    - Per-record error isolation (single malformed instrument does not crash the batch).
    - Lease-lock concurrency protection.
    - Idempotent repeated runs on the same calendar date.
    - Explicit diagnosis and run metadata persistence.
    """
    clock = get_current_clock()
    default_policy = resolve_active_policy(db)
    target_tz = default_policy.timezone

    if simulated_date is not None:
        if not settings.ENABLE_LIFECYCLE_DATE_ADVANCE or settings.ENVIRONMENT == "production":
            raise AppException(
                status_code=403,
                message="Simulated date advance is disabled in production.",
                code="DATE_ADVANCE_DISABLED",
            )
        eval_date = simulated_date
    else:
        eval_date = clock.today_in_tz(target_tz)

    job_run = acquire_job_lease(
        db=db,
        job_type=job_type,
        trigger_source=trigger_source,
        evaluation_date=eval_date,
        evaluation_timezone=target_tz,
        worker_instance_id=worker_instance_id,
        lease_duration_minutes=lease_duration_minutes,
    )

    # Query total eligible instruments
    eligible_count = db.scalar(
        select(func.count(Instrument.id)).where(Instrument.status.in_(["REGISTERED", "DRAFT", "UNDER_REVIEW"]))
    ) or 0
    job_run.total_eligible = eligible_count
    db.commit()

    evaluated_count = 0
    success_count = 0
    error_count = 0
    material_count = 0
    approaching_count = 0
    matured_count = 0
    overdue_count = 0
    errors_summary: List[Dict[str, str]] = []

    # Stream in bounded batches
    offset = 0
    while True:
        stmt = (
            select(Instrument.id)
            .where(Instrument.status.in_(["REGISTERED", "DRAFT", "UNDER_REVIEW"]))
            .order_by(Instrument.id)
            .offset(offset)
            .limit(batch_size)
        )
        chunk_ids = list(db.scalars(stmt).all())
        if not chunk_ids:
            break

        for inst_id in chunk_ids:
            evaluated_count += 1
            try:
                eval_record = evaluate_instrument_lifecycle(
                    db=db,
                    instrument_id=inst_id,
                    simulated_date=simulated_date,
                    force_record=force_reevaluation,
                    actor_user_id=actor_user_id,
                    actor_email=actor_email,
                )
                success_count += 1
                if eval_record.is_material_transition:
                    material_count += 1
                if eval_record.maturity_stage in (
                    MaturityStage.MATURING_SOON.value,
                    MaturityStage.CRITICAL_WINDOW.value,
                ):
                    approaching_count += 1
                elif eval_record.maturity_stage in (
                    MaturityStage.MATURED.value,
                    MaturityStage.EXPIRED.value,
                ):
                    matured_count += 1
                if eval_record.is_overdue:
                    overdue_count += 1

            except Exception as exc:
                error_count += 1
                logger.error(f"[Scheduler Error] Instrument '{inst_id}' evaluation failed: {exc}")
                if len(errors_summary) < 20:  # Cap stored sample errors
                    errors_summary.append({"instrument_id": inst_id, "error": str(exc)})
                # Continue with next instrument without crashing entire batch

        offset += len(chunk_ids)

    # Finalize job run status
    finish_now = get_utc_now()
    job_run.completed_at = finish_now
    job_run.evaluated_count = evaluated_count
    job_run.success_count = success_count
    job_run.error_count = error_count
    job_run.material_transitions_count = material_count
    job_run.approaching_count = approaching_count
    job_run.matured_count = matured_count
    job_run.overdue_count = overdue_count

    if error_count == 0:
        job_run.status = "SUCCESS"
    elif success_count > 0:
        job_run.status = "PARTIAL_FAILURE"
    else:
        job_run.status = "FAILED"

    if errors_summary:
        job_run.error_summary_json = json.dumps(errors_summary)

    db.commit()
    db.refresh(job_run)

    log_audit_event(
        db=db,
        action="LIFECYCLE_SCAN_JOB_COMPLETED",
        entity_type="LIFECYCLE_JOB_RUN",
        entity_id=job_run.id,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        outcome=job_run.status,
        metadata={
            "job_type": job_run.job_type,
            "status": job_run.status,
            "evaluated_count": job_run.evaluated_count,
            "success_count": job_run.success_count,
            "error_count": job_run.error_count,
            "material_transitions": job_run.material_transitions_count,
        },
    )

    return job_run


def get_latest_job_runs(
    db: Session, limit: int = 10
) -> SchedulerRunStatusResponse:
    """
    Returns latest scheduler run history, clearly distinguishing between
    last attempted run and last successful run.
    """
    last_attempted = db.scalar(
        select(LifecycleJobRun).order_by(desc(LifecycleJobRun.started_at))
    )
    last_successful = db.scalar(
        select(LifecycleJobRun)
        .where(LifecycleJobRun.status == "SUCCESS")
        .order_by(desc(LifecycleJobRun.started_at))
    )
    recent = list(
        db.scalars(
            select(LifecycleJobRun)
            .order_by(desc(LifecycleJobRun.started_at))
            .limit(limit)
        ).all()
    )

    return SchedulerRunStatusResponse(
        last_attempted_run=last_attempted,  # type: ignore[arg-type]
        last_successful_run=last_successful,  # type: ignore[arg-type]
        recent_runs=recent,  # type: ignore[arg-type]
    )
