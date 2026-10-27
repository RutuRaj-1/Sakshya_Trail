"""
Module 5 — Lifecycle Orchestration & Renewal REST API Router
Exposes policy configuration, lineage graph management, and time-sensitive lifecycle evaluations.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Path

from app.db.session import get_db
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ALL_ROLES,
)
from app.modules.auth.dependencies import (
    get_current_user,
    require_roles,
)
from app.modules.auth.models import User
from app.modules.lifecycle.schemas import (
    LifecyclePolicyCreate,
    LifecyclePolicyResponse,
    LineageCreateRequest,
    LineageResponse,
    LineageTreeResponse,
    LifecycleEvaluationRequest,
    LifecycleEvaluationResponse,
    BatchEvaluationRequest,
    BatchEvaluationResponse,
    LifecycleJobRunResponse,
    SchedulerRunStatusResponse,
    TriggerJobRequest,
    DemoClockStatusResponse,
    DemoClockAdvanceRequest,
    MonitoringListResponse,
    NotificationResponse,
    NotificationListResponse,
    RetryNotificationRequest,
    DispatchRemindersRequest,
    DispatchRemindersResponse,
    RenewalDraftResponse,
    RenewalCreateSuccessorRequest,
    RenewalSuccessorCreatedResponse,
    LineageValidateRequest,
    LineageValidateResponse,
    ContinuityAssessmentResponse,
    LineageCorrectionRequest,
)
from app.modules.lifecycle.policy_service import (
    create_policy,
    approve_policy,
    activate_policy,
    get_policy_by_id,
    list_policies,
    get_or_create_default_demo_policy,
)
from app.modules.lifecycle.lineage_service import (
    create_renewal_lineage,
    get_lineage_by_id,
    get_lineage_tree,
    validate_proposed_lineage,
    initiate_renewal_draft,
    create_and_link_renewal_successor,
    correct_renewal_lineage,
    get_lineage_continuity_assessment,
)
from app.modules.lifecycle.evaluation_service import (
    evaluate_instrument_lifecycle,
    get_latest_evaluation_for_instrument,
    evaluate_batch_instruments,
)
from app.common.exceptions import AppException
from app.core.canonical_stages import list_canonical_stages, StageContract

router = APIRouter(prefix="/lifecycle", tags=["Module 5 — Lifecycle & Renewal"])
instruments_lifecycle_router = APIRouter(prefix="/instruments", tags=["Module 5 — Instrument Lifecycle & Lineage"])


@router.get(
    "/canonical-stages",
    response_model=List[StageContract],
    summary="Get authoritative nine-stage canonical workflow contracts",
)
def get_canonical_stages_endpoint(
    current_user: User = Depends(get_current_user),
):
    """
    Exposes the authoritative nine-stage FDR lifecycle contract connecting
    frontend routes, backend APIs, permitted roles, action capabilities,
    and audit event definitions.
    """
    return list_canonical_stages()


# --- Policy Management Endpoints ------------------------------------------------

@router.post(
    "/policies",
    response_model=LifecyclePolicyResponse,
    summary="Create a new versioned lifecycle policy (Admin only)",
)
def create_lifecycle_policy_endpoint(
    payload: LifecyclePolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN])),
):
    return create_policy(
        db=db,
        payload=payload,
        created_by_user_id=current_user.id,
        actor_email=current_user.email,
    )


@router.get(
    "/policies",
    response_model=List[LifecyclePolicyResponse],
    summary="List versioned lifecycle policies",
)
def list_lifecycle_policies_endpoint(
    policy_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    include_demo: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Ensure default demo policy is provisioned
    get_or_create_default_demo_policy(db)
    return list_policies(
        db=db,
        policy_code=policy_code,
        status=status,
        include_demo=include_demo,
    )


@router.get(
    "/policies/{policy_id}",
    response_model=LifecyclePolicyResponse,
    summary="Get lifecycle policy by ID",
)
def get_lifecycle_policy_endpoint(
    policy_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = get_policy_by_id(db, policy_id)
    if not policy:
        raise AppException(status_code=404, message=f"Policy '{policy_id}' not found", code="POLICY_NOT_FOUND")
    return policy


@router.post(
    "/policies/{policy_id}/approve",
    response_model=LifecyclePolicyResponse,
    summary="Approve a draft policy (Admin / Competent Authority)",
)
def approve_lifecycle_policy_endpoint(
    policy_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_COMPETENT_AUTHORITY])),
):
    return approve_policy(
        db=db,
        policy_id=policy_id,
        approver_user_id=current_user.id,
        actor_email=current_user.email,
    )


@router.post(
    "/policies/{policy_id}/activate",
    response_model=LifecyclePolicyResponse,
    summary="Activate an approved policy (Admin only)",
)
def activate_lifecycle_policy_endpoint(
    policy_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN])),
):
    return activate_policy(
        db=db,
        policy_id=policy_id,
        activator_user_id=current_user.id,
        actor_email=current_user.email,
    )


# --- Lineage Management Endpoints -----------------------------------------------

@router.post(
    "/lineage/validate",
    response_model=LineageValidateResponse,
    summary="Pre-validate proposed predecessor-successor renewal relationship",
)
def validate_proposed_lineage_endpoint(
    payload: LineageValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return validate_proposed_lineage(db=db, payload=payload, current_user=current_user)


@router.post(
    "/lineage/renew",
    response_model=LineageResponse,
    summary="Create predecessor-successor renewal relationship link",
)
@router.post(
    "/lineage/link",
    response_model=LineageResponse,
    summary="Link predecessor and successor instruments",
)
def create_renewal_lineage_endpoint(
    payload: LineageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_renewal_lineage(
        db=db,
        payload=payload,
        created_by_user_id=current_user.id,
        actor_email=current_user.email,
        current_user=current_user,
    )


@router.get(
    "/lineage/{lineage_id}",
    response_model=LineageResponse,
    summary="Get lineage relationship details by ID",
)
def get_lineage_endpoint(
    lineage_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lineage = get_lineage_by_id(db, lineage_id)
    if not lineage:
        raise AppException(status_code=404, message=f"Lineage record '{lineage_id}' not found", code="LINEAGE_NOT_FOUND")
    if current_user.role == "INSTITUTION_USER" and lineage.institution_id != current_user.institution_id:
        raise AppException(status_code=403, message="Access denied: Lineage record belongs to another institution.", code="FORBIDDEN")
    return lineage


@router.get(
    "/lineage/{lineage_id}/continuity",
    response_model=ContinuityAssessmentResponse,
    summary="Get granular continuity gap/overlap assessment for a lineage edge",
)
def get_lineage_continuity_endpoint(
    lineage_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_lineage_continuity_assessment(db=db, lineage_id_or_instrument_id=lineage_id, current_user=current_user)


@router.post(
    "/lineage/{lineage_id}/correct",
    response_model=LineageResponse,
    summary="Authorized correction, deactivation, or superseding of a lineage relationship",
)
def correct_lineage_endpoint(
    lineage_id: str = Path(...),
    payload: LineageCorrectionRequest = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    return correct_renewal_lineage(
        db=db,
        lineage_id=lineage_id,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/instruments/{id}/renewal-draft",
    response_model=RenewalDraftResponse,
    summary="Initiate renewal draft for predecessor instrument",
)
@instruments_lifecycle_router.get(
    "/{id}/renewal-draft",
    response_model=RenewalDraftResponse,
    summary="Initiate renewal draft for predecessor instrument",
)
def initiate_renewal_draft_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return initiate_renewal_draft(db=db, predecessor_id=id, current_user=current_user)


@router.post(
    "/instruments/{id}/renew",
    response_model=RenewalSuccessorCreatedResponse,
    summary="Create brand new successor instrument and link to predecessor",
)
@instruments_lifecycle_router.post(
    "/{id}/renew",
    response_model=RenewalSuccessorCreatedResponse,
    summary="Create brand new successor instrument and link to predecessor",
)
def create_renewal_successor_endpoint(
    id: str = Path(...),
    payload: RenewalCreateSuccessorRequest = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    successor, lineage = create_and_link_renewal_successor(
        db=db,
        predecessor_id=id,
        payload=payload,
        current_user=current_user,
    )
    return RenewalSuccessorCreatedResponse(
        successor_instrument_id=successor.id,
        predecessor_instrument_id=id,
        lineage_id=lineage.id,
        reference_number=successor.reference_number,
        trust_level=successor.trust_level,
        status=successor.status,
        validity_gap_days=lineage.validity_gap_days,
        validity_overlap_days=lineage.validity_overlap_days,
        continuity_indicator=lineage.continuity_indicator,
        lineage=lineage,  # type: ignore[arg-type]
    )


@router.get(
    "/instruments/{id}/lineage",
    response_model=LineageTreeResponse,
    summary="Get complete renewal lineage ancestry and successor chain for an instrument",
)
@instruments_lifecycle_router.get(
    "/{id}/lineage",
    response_model=LineageTreeResponse,
    summary="Get complete renewal lineage ancestry and successor chain for an instrument",
)
def get_instrument_lineage_tree_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_lineage_tree(db, instrument_id=id, current_user=current_user)


@router.get(
    "/instruments/{id}/continuity",
    response_model=ContinuityAssessmentResponse,
    summary="Get continuity gap/overlap assessment for instrument's active lineage link",
)
@instruments_lifecycle_router.get(
    "/{id}/continuity",
    response_model=ContinuityAssessmentResponse,
    summary="Get continuity gap/overlap assessment for instrument's active lineage link",
)
def get_instrument_continuity_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_lineage_continuity_assessment(db=db, lineage_id_or_instrument_id=id, current_user=current_user)


# --- Evaluation Endpoints -------------------------------------------------------

@router.post(
    "/evaluate",
    response_model=LifecycleEvaluationResponse,
    summary="Perform on-demand or demo lifecycle evaluation for an instrument",
)
def evaluate_lifecycle_endpoint(
    payload: LifecycleEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.instruments.models import Instrument
    inst = db.scalar(select(Instrument).where(Instrument.id == payload.instrument_id))
    if not inst:
        raise AppException(status_code=404, message=f"Instrument '{payload.instrument_id}' not found", code="INSTRUMENT_NOT_FOUND")
    if current_user.role == "INSTITUTION_USER" and inst.institution_id != current_user.institution_id:
        raise AppException(status_code=403, message="Access denied: Instrument belongs to another institution.", code="FORBIDDEN")

    return evaluate_instrument_lifecycle(
        db=db,
        instrument_id=payload.instrument_id,
        policy_id=payload.policy_id,
        simulated_date=payload.simulated_date,
        force_record=payload.force_evaluation,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )


@instruments_lifecycle_router.get(
    "/{id}/lifecycle",
    response_model=Optional[LifecycleEvaluationResponse],
    summary="Get latest lifecycle evaluation snapshot for an instrument",
)
def get_instrument_latest_lifecycle_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.instruments.models import Instrument
    inst = db.scalar(select(Instrument).where(Instrument.id == id))
    if not inst:
        raise AppException(status_code=404, message=f"Instrument '{id}' not found", code="INSTRUMENT_NOT_FOUND")
    if current_user.role == "INSTITUTION_USER" and inst.institution_id != current_user.institution_id:
        raise AppException(status_code=403, message="Access denied: Instrument belongs to another institution.", code="FORBIDDEN")

    ev = get_latest_evaluation_for_instrument(db, instrument_id=id)
    if not ev:
        # Trigger an initial on-demand evaluation if never evaluated
        ev = evaluate_instrument_lifecycle(
            db=db,
            instrument_id=id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
        )
    return ev


@router.post(
    "/batch-evaluate",
    response_model=BatchEvaluationResponse,
    summary="Trigger batch lifecycle evaluation across instruments",
)
def batch_evaluate_endpoint(
    payload: BatchEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    total, material, evals = evaluate_batch_instruments(
        db=db,
        instrument_ids=payload.instrument_ids,
        institution_id=payload.institution_id,
        simulated_date=payload.simulated_date,
        limit=payload.limit,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )
    return BatchEvaluationResponse(
        evaluated_count=total,
        material_transitions_count=material,
        evaluations=evals,
    )


# --- Monitoring Endpoints -------------------------------------------------------

@router.get(
    "/assessments/{instrument_id}",
    response_model=Optional[LifecycleEvaluationResponse],
    summary="Get detailed lifecycle assessment for an instrument",
)
def get_instrument_assessment_endpoint(
    instrument_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ev = get_latest_evaluation_for_instrument(db, instrument_id=instrument_id)
    if not ev:
        ev = evaluate_instrument_lifecycle(
            db=db,
            instrument_id=instrument_id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
        )
    return ev


@router.get(
    "/monitoring/approaching-maturity",
    response_model=MonitoringListResponse,
    summary="List instruments with approaching maturity (MATURING_SOON / CRITICAL_WINDOW)",
)
def list_approaching_maturity_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    institution_id: Optional[str] = Query(None),
    office: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.monitoring_service import list_monitoring_instruments
    return list_monitoring_instruments(
        db=db,
        category="APPROACHING_MATURITY",
        current_user=current_user,
        page=page,
        limit=limit,
        institution_id=institution_id,
        office=office,
    )


@router.get(
    "/monitoring/matured",
    response_model=MonitoringListResponse,
    summary="List matured and expired instruments",
)
def list_matured_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    institution_id: Optional[str] = Query(None),
    office: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.monitoring_service import list_monitoring_instruments
    return list_monitoring_instruments(
        db=db,
        category="MATURED",
        current_user=current_user,
        page=page,
        limit=limit,
        institution_id=institution_id,
        office=office,
    )


@router.get(
    "/monitoring/overdue",
    response_model=MonitoringListResponse,
    summary="List instruments with overdue or escalated compliance requirements",
)
def list_overdue_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    institution_id: Optional[str] = Query(None),
    office: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.monitoring_service import list_monitoring_instruments
    return list_monitoring_instruments(
        db=db,
        category="OVERDUE",
        current_user=current_user,
        page=page,
        limit=limit,
        institution_id=institution_id,
        office=office,
    )


# --- Scheduler Execution & Diagnostics Endpoints -------------------------------

@router.post(
    "/scheduler/trigger",
    response_model=LifecycleJobRunResponse,
    summary="Trigger a bounded maturity scan job manually (Officer / Admin)",
)
def trigger_scheduler_job_endpoint(
    payload: TriggerJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    from app.modules.lifecycle.scheduler import execute_lifecycle_scan_job
    return execute_lifecycle_scan_job(
        db=db,
        job_type="MANUAL_EVALUATION",
        trigger_source="MANUAL_API",
        batch_size=payload.batch_size,
        simulated_date=payload.simulated_date,
        force_reevaluation=payload.force_reevaluation,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )


@router.get(
    "/scheduler/runs",
    response_model=List[LifecycleJobRunResponse],
    summary="List recent scheduler run execution logs",
)
def list_scheduler_runs_endpoint(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    from sqlalchemy import select, desc
    from app.modules.lifecycle.models import LifecycleJobRun
    return list(db.scalars(select(LifecycleJobRun).order_by(desc(LifecycleJobRun.started_at)).limit(limit)).all())


@router.get(
    "/scheduler/runs/latest",
    response_model=SchedulerRunStatusResponse,
    summary="Get status of latest attempted and successful scheduler runs",
)
def get_latest_scheduler_runs_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.scheduler import get_latest_job_runs
    return get_latest_job_runs(db=db)


# --- Demo Date-Advancement Endpoints --------------------------------------------

@router.get(
    "/demo/clock",
    response_model=DemoClockStatusResponse,
    summary="Read current active clock state (development/demo inspection)",
)
def get_demo_clock_status_endpoint(
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.clock import get_clock_status
    return get_clock_status()


@router.post(
    "/demo/advance-clock",
    response_model=DemoClockStatusResponse,
    summary="Advance demo simulated clock forward (Development / Demo only)",
)
def advance_demo_clock_endpoint(
    payload: DemoClockAdvanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER])),
):
    from app.core.config import settings
    if not settings.ENABLE_LIFECYCLE_DATE_ADVANCE or settings.ENVIRONMENT == "production":
        raise AppException(
            status_code=403,
            message="Demo date advancement is strictly forbidden in production mode.",
            code="DEMO_CONTROL_DISABLED_IN_PRODUCTION",
        )

    from app.modules.lifecycle.clock import (
        get_current_clock,
        set_current_clock,
        SimulatedClock,
        get_clock_status,
    )
    from app.modules.audit.service import log_audit_event

    current_clock = get_current_clock()
    if isinstance(current_clock, SimulatedClock):
        sim_clock = current_clock
    else:
        sim_clock = SimulatedClock()
        set_current_clock(sim_clock)

    before_date = sim_clock.today_in_tz().isoformat()
    if payload.target_date:
        sim_clock.set_date(payload.target_date)
    elif payload.days:
        sim_clock.advance_days(payload.days)
    else:
        raise AppException(status_code=400, message="Must specify 'days' or 'target_date'", code="INVALID_PARAMETERS")

    after_date = sim_clock.today_in_tz().isoformat()

    log_audit_event(
        db=db,
        action="DEMO_DATE_ADVANCED",
        entity_type="SYSTEM_CLOCK",
        entity_id="SIMULATED_CLOCK",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        metadata={"before_date": before_date, "after_date": after_date, "offset_days": sim_clock._offset.days},
    )

    return get_clock_status()


@router.post(
    "/demo/reset-clock",
    response_model=DemoClockStatusResponse,
    summary="Reset simulated clock back to host system time",
)
def reset_demo_clock_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN])),
):
    from app.modules.lifecycle.clock import reset_to_system_clock, get_clock_status
    from app.modules.audit.service import log_audit_event

    reset_to_system_clock()

    log_audit_event(
        db=db,
        action="DEMO_CLOCK_RESET",
        entity_type="SYSTEM_CLOCK",
        entity_id="SYSTEM_CLOCK",
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )

    return get_clock_status()


# --- Notification & Escalation Endpoints ----------------------------------------

@router.get(
    "/instruments/{instrument_id}/notifications",
    response_model=NotificationListResponse,
    summary="Get tenancy-scoped notification history for an instrument",
)
@instruments_lifecycle_router.get(
    "/{instrument_id}/notifications",
    response_model=NotificationListResponse,
    summary="Get tenancy-scoped notification history for an instrument",
)
def get_instrument_notifications_endpoint(
    instrument_id: str = Path(...),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.notification_service import get_instrument_notifications
    total, records = get_instrument_notifications(
        db=db,
        instrument_id=instrument_id,
        current_user=current_user,
        page=page,
        limit=limit,
    )
    return NotificationListResponse(
        total_count=total,
        page=page,
        limit=limit,
        items=records,  # type: ignore[arg-type]
    )


@router.get(
    "/notifications/inbox",
    response_model=NotificationListResponse,
    summary="Get in-app notification inbox for the current user",
)
def get_user_inbox_endpoint(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.notification_service import get_user_inbox_notifications
    total, records = get_user_inbox_notifications(
        db=db,
        current_user=current_user,
        unread_only=unread_only,
        page=page,
        limit=limit,
    )
    return NotificationListResponse(
        total_count=total,
        page=page,
        limit=limit,
        items=records,  # type: ignore[arg-type]
    )


@router.post(
    "/notifications/{id}/read",
    response_model=NotificationResponse,
    summary="Mark an in-app notification as read",
)
def mark_notification_read_endpoint(
    id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.notification_service import mark_notification_as_read
    return mark_notification_as_read(db=db, notification_id=id, current_user=current_user)


@router.post(
    "/notifications/read-all",
    summary="Mark all inbox notifications as read for current user",
)
def mark_all_notifications_read_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.modules.lifecycle.event_notification_service import mark_all_inbox_as_read
    count = mark_all_inbox_as_read(db=db, current_user=current_user)
    return {"message": "All notifications marked as read.", "marked_read": count}


@router.get(
    "/admin/oversight",
    response_model=NotificationListResponse,
    summary="Get operational oversight notification feed (System Admin only)",
)
@router.get(
    "/notifications/admin-oversight",
    response_model=NotificationListResponse,
    summary="Get operational oversight notification feed (System Admin only)",
)
def get_admin_oversight_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN])),
):
    from app.modules.lifecycle.event_notification_service import get_admin_oversight_feed
    total, records = get_admin_oversight_feed(db=db, page=page, limit=limit)
    return NotificationListResponse(
        total_count=total,
        page=page,
        limit=limit,
        items=records,  # type: ignore[arg-type]
    )


@router.get(
    "/notifications/failed",
    response_model=NotificationListResponse,
    summary="List failed or pending delivery attempts (Admin/Officer audit view)",
)
def list_failed_notifications_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    from app.modules.lifecycle.notification_service import list_failed_notifications
    total, records = list_failed_notifications(
        db=db,
        current_user=current_user,
        page=page,
        limit=limit,
    )
    return NotificationListResponse(
        total_count=total,
        page=page,
        limit=limit,
        items=records,  # type: ignore[arg-type]
    )


@router.post(
    "/notifications/{id}/retry",
    response_model=NotificationResponse,
    summary="Controlled administrative manual retry of a notification",
)
def retry_notification_endpoint(
    id: str = Path(...),
    payload: RetryNotificationRequest = RetryNotificationRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER])),
):
    from app.modules.lifecycle.notification_service import retry_notification
    return retry_notification(
        db=db,
        notification_id=id,
        current_user=current_user,
        force=payload.force,
    )


@router.post(
    "/notifications/dispatch-due",
    response_model=DispatchRemindersResponse,
    summary="Trigger reminder dispatch for evaluated instruments",
)
def dispatch_due_reminders_endpoint(
    payload: DispatchRemindersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD])),
):
    from sqlalchemy import select
    from app.modules.instruments.models import Instrument
    from app.modules.lifecycle.evaluation_service import get_latest_evaluation_for_instrument, evaluate_instrument_lifecycle
    from app.modules.lifecycle.notification_service import generate_and_dispatch_reminders_for_instrument

    query = select(Instrument.id).where(Instrument.status.in_(["REGISTERED", "DRAFT", "UNDER_REVIEW"]))
    if payload.instrument_ids:
        query = query.where(Instrument.id.in_(payload.instrument_ids))
    inst_ids = list(db.scalars(query.limit(payload.batch_size)).all())

    processed = 0
    dispatched_all = []
    failed_count = 0

    for i_id in inst_ids:
        processed += 1
        eval_rec = get_latest_evaluation_for_instrument(db, i_id)
        if not eval_rec or payload.simulated_date:
            eval_rec = evaluate_instrument_lifecycle(
                db=db,
                instrument_id=i_id,
                simulated_date=payload.simulated_date,
                actor_user_id=current_user.id,
                actor_email=current_user.email,
            )
        try:
            notifs = generate_and_dispatch_reminders_for_instrument(
                db=db,
                instrument_id=i_id,
                eval_record=eval_rec,
                simulated_date=payload.simulated_date,
                actor_user_id=current_user.id,
                actor_email=current_user.email,
            )
            dispatched_all.extend(notifs)
        except Exception as e:
            failed_count += 1

    return DispatchRemindersResponse(
        processed_count=processed,
        dispatched_count=len(dispatched_all),
        failed_count=failed_count,
        notifications=dispatched_all,  # type: ignore[arg-type]
    )


