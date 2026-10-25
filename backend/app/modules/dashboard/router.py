"""
Dashboard & Command Center Module - API Endpoints
Provides typed, authenticated, and role-scoped endpoints for Module 7 Command Center:
- Metrics Dictionary (PRD-FR-077)
- Command Center Overview
- Status counts (PRD-FR-070a)
- Maturity window (PRD-FR-070b)
- Overdue & escalated work (PRD-FR-070c)
- Verification queue & health (PRD-FR-070d)
- Document completeness (PRD-FR-070e)
- Release / refund blockers (PRD-FR-070f)
- Month-wise maturity load (PRD-FR-076)
- Operational priority queue (PRD-FR-075)
- Common search & drilldown (PRD-FR-071)
- Reports (PRD-FR-074)
- Timeline history (PRD-FR-072)
- Audit log integrity verification (PRD-FR-093)
- Preserves legacy Module 1 /summary endpoint
"""
from typing import Optional, List, Dict, Any
from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user, require_roles
from app.modules.auth.models import User
from app.core.security import (
    ROLE_INSTITUTION_USER,
    ROLE_SCRUTINY_OFFICER,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
    ROLE_FINANCE_OFFICER,
    ROLE_AUDITOR,
    ROLE_SYSTEM_ADMIN,
    INTERNAL_ROLES,
)
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.dashboard.metrics import list_metric_definitions, get_metric_definition
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
    MetricDictionaryResponse,
    StatusCountsResponse,
    MaturityWindowResponse,
    OverdueEscalatedResponse,
    VerificationQueueResponse,
    DocumentCompletenessResponse,
    ReleaseBlockersResponse,
    MonthWiseMaturityLoadResponse,
    PriorityQueueResponse,
    CommandCenterOverviewResponse,
    InstrumentSearchResponse,
    ReleaseCaseSearchResponse,
    InstrumentDetailSnapshotResponse,
    ScrutinyObservationItem,
    ScrutinyObservationCreateRequest,
    ScrutinyObservationAmendRequest,
    ScrutinyObservationResolveRequest,
)
from app.modules.dashboard.dashboard_service import DashboardService
from app.modules.dashboard.priority_service import PriorityService
from app.modules.dashboard.search_service import SearchService
from app.modules.dashboard.report_service import ReportService
from app.modules.dashboard.history_service import HistoryService
from app.modules.dashboard.audit_query_service import AuditQueryService
from app.modules.dashboard.observation_service import ScrutinyObservationService

router = APIRouter(prefix="/dashboard", tags=["Module 7 Command Center"])


# ------------------------------------------------------------------------------
# Module 1 Legacy Compatibility Endpoint
# ------------------------------------------------------------------------------
@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    """
    Returns scoped operational metrics for the Module 1 dashboard.
    Maintained for complete backward compatibility.
    """
    today = date.today()
    approaching_date = today + timedelta(days=90)

    is_inst_user = current_user.role == ROLE_INSTITUTION_USER
    user_inst_id = current_user.institution_id if is_inst_user else None

    # Institution Counts
    if is_inst_user:
        if user_inst_id:
            inst = db.get(Institution, user_inst_id)
            if inst and inst.is_active:
                total_active_institutions = 1
                total_inactive_institutions = 0
            elif inst and not inst.is_active:
                total_active_institutions = 0
                total_inactive_institutions = 1
            else:
                total_active_institutions = 0
                total_inactive_institutions = 0
        else:
            total_active_institutions = 0
            total_inactive_institutions = 0
    else:
        total_active_institutions = db.scalar(
            select(func.count(Institution.id)).where(Institution.is_active.is_(True))
        ) or 0
        total_inactive_institutions = db.scalar(
            select(func.count(Institution.id)).where(Institution.is_active.is_(False))
        ) or 0

    # Instrument Conditions
    inst_conditions = []
    if is_inst_user:
        inst_conditions.append(Instrument.institution_id == user_inst_id)

    stmt_totals = select(
        func.count(Instrument.id),
        func.coalesce(func.sum(Instrument.amount), Decimal("0.00")),
    )
    if inst_conditions:
        stmt_totals = stmt_totals.where(*inst_conditions)

    total_instruments, total_value = db.execute(stmt_totals).one()
    total_instruments = total_instruments or 0
    total_deposit_value = f"{Decimal(total_value):.2f}"

    # Status breakdown
    stmt_status = select(Instrument.status, func.count(Instrument.id))
    if inst_conditions:
        stmt_status = stmt_status.where(*inst_conditions)
    stmt_status = stmt_status.group_by(Instrument.status)
    status_rows = db.execute(stmt_status).all()
    instruments_by_status = {row[0]: row[1] for row in status_rows}

    for default_status in ("DRAFT", "REGISTERED"):
        if default_status not in instruments_by_status:
            instruments_by_status[default_status] = 0

    # Trust level breakdown
    stmt_trust = select(Instrument.trust_level, func.count(Instrument.id))
    if inst_conditions:
        stmt_trust = stmt_trust.where(*inst_conditions)
    stmt_trust = stmt_trust.group_by(Instrument.trust_level)
    trust_rows = db.execute(stmt_trust).all()
    instruments_by_trust_level = {row[0]: row[1] for row in trust_rows}

    for default_trust in ("L0_DECLARED", "L1_DOCUMENT_CONSISTENT", "L2_OFFICER_VERIFIED", "L3_BANK_CONFIRMED"):
        if default_trust not in instruments_by_trust_level:
            instruments_by_trust_level[default_trust] = 0

    stmt_approaching = select(func.count(Instrument.id)).where(
        Instrument.maturity_date >= today,
        Instrument.maturity_date <= approaching_date,
    )
    if inst_conditions:
        stmt_approaching = stmt_approaching.where(*inst_conditions)
    instruments_approaching_maturity = db.scalar(stmt_approaching) or 0

    return DashboardSummaryResponse(
        total_active_institutions=total_active_institutions,
        total_inactive_institutions=total_inactive_institutions,
        total_instruments=total_instruments,
        total_deposit_value=total_deposit_value,
        instruments_by_status=instruments_by_status,
        instruments_by_trust_level=instruments_by_trust_level,
        instruments_approaching_maturity=instruments_approaching_maturity,
    )


# ------------------------------------------------------------------------------
# Metric Dictionary Endpoint (PRD-FR-077)
# ------------------------------------------------------------------------------
@router.get("/metrics/dictionary", response_model=MetricDictionaryResponse)
def get_metric_dictionary(
    category: Optional[str] = Query(None, description="Filter metrics by functional category"),
    current_user: User = Depends(get_current_active_user),
) -> MetricDictionaryResponse:
    """
    Returns the central Metric Dictionary documentation (PRD-FR-077).
    Guarantees transparent definitions, calculation rules, inclusions, and exclusions.
    """
    defs = list_metric_definitions(category=category)
    return MetricDictionaryResponse(total_metrics=len(defs), metrics=defs)


# ------------------------------------------------------------------------------
# Consolidated Command Center Overview
# ------------------------------------------------------------------------------
@router.get("/command-center", response_model=CommandCenterOverviewResponse)
def get_command_center(
    window_days: int = Query(90, ge=1, le=730, description="Monitoring window in days"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CommandCenterOverviewResponse:
    """
    Aggregated Command Center cockpit response combining all key cards and queues.
    """
    return DashboardService.get_command_center_overview(
        db=db, current_user=current_user, window_days=window_days
    )


# ------------------------------------------------------------------------------
# Category A: Status Counts (PRD-FR-070a)
# ------------------------------------------------------------------------------
@router.get("/status-counts", response_model=StatusCountsResponse)
def get_status_counts(
    window_days: int = Query(90, ge=1, le=730, description="Expiring soon window in days"),
    institution_id: Optional[str] = Query(None, description="Filter by institution (authorized roles only)"),
    assigned_office: Optional[str] = Query(None, description="Filter by office jurisdiction"),
    bank_name: Optional[str] = Query(None, description="Filter by issuing bank"),
    trust_level: Optional[str] = Query(None, description="Filter by trust level (L0-L3)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> StatusCountsResponse:
    """
    Category A: Status counts breakdown (Active, Expiring Soon, Matured, Renewed, Released, Pending).
    """
    return DashboardService.compute_status_counts(
        db=db,
        current_user=current_user,
        window_days=window_days,
        institution_id=institution_id,
        assigned_office=assigned_office,
        bank_name=bank_name,
        trust_level=trust_level,
    )


# ------------------------------------------------------------------------------
# Category B: Maturity Window (PRD-FR-070b)
# ------------------------------------------------------------------------------
@router.get("/maturity-window", response_model=MaturityWindowResponse)
def get_maturity_window(
    start_date: Optional[date] = Query(None, description="Inclusive start date (defaults to today)"),
    end_date: Optional[date] = Query(None, description="Inclusive end date"),
    window_days: Optional[int] = Query(None, ge=1, le=730, description="Window duration in days from start"),
    institution_id: Optional[str] = Query(None, description="Filter by institution (authorized roles only)"),
    assigned_office: Optional[str] = Query(None, description="Filter by assigned office"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    page: int = Query(1, ge=1, description="Page number for drilldown"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MaturityWindowResponse:
    """
    Category B: Instruments maturing within an inclusive selectable date window.
    """
    return DashboardService.compute_maturity_window(
        db=db,
        current_user=current_user,
        start_date=start_date,
        end_date=end_date,
        window_days=window_days,
        institution_id=institution_id,
        assigned_office=assigned_office,
        bank_name=bank_name,
        page=page,
        page_size=page_size,
    )


# ------------------------------------------------------------------------------
# Category C: Overdue & Escalated Work (PRD-FR-070c)
# ------------------------------------------------------------------------------
@router.get("/overdue-escalated", response_model=OverdueEscalatedResponse)
def get_overdue_escalated(
    institution_id: Optional[str] = Query(None, description="Filter by institution"),
    assigned_office: Optional[str] = Query(None, description="Filter by assigned office"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> OverdueEscalatedResponse:
    """
    Category C: Overdue compliance actions and escalated cases.
    """
    return DashboardService.compute_overdue_and_escalated(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
        assigned_office=assigned_office,
        limit=limit,
    )


# ------------------------------------------------------------------------------
# Category D: Verification Queue (PRD-FR-070d)
# ------------------------------------------------------------------------------
@router.get("/verification-queue", response_model=VerificationQueueResponse)
def get_verification_queue(
    institution_id: Optional[str] = Query(None, description="Filter by institution"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    limit: int = Query(50, ge=1, le=100, description="Max queue records"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> VerificationQueueResponse:
    """
    Category D: Outstanding verification requests, aging, and source-unavailable cases.
    """
    return DashboardService.compute_verification_queue(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
        bank_name=bank_name,
        limit=limit,
    )


# ------------------------------------------------------------------------------
# Category E: Document Completeness (PRD-FR-070e)
# ------------------------------------------------------------------------------
@router.get("/document-completeness", response_model=DocumentCompletenessResponse)
def get_document_completeness(
    institution_id: Optional[str] = Query(None, description="Filter by institution"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DocumentCompletenessResponse:
    """
    Category E: Document completeness checklist outcomes.
    Explicitly reports policy status when unconfigured.
    """
    return DashboardService.compute_document_completeness(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
    )


# ------------------------------------------------------------------------------
# Category F: Release Blockers (PRD-FR-070f)
# ------------------------------------------------------------------------------
@router.get("/release-blockers", response_model=ReleaseBlockersResponse)
def get_release_blockers(
    institution_id: Optional[str] = Query(None, description="Filter by institution"),
    case_type: Optional[str] = Query(None, description="Filter by release case type"),
    limit: int = Query(50, ge=1, le=100, description="Max cases to return"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ReleaseBlockersResponse:
    """
    Category F: Active release requests obstructed by unmet mandatory checklist items.
    """
    return DashboardService.compute_release_blockers(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
        case_type=case_type,
        limit=limit,
    )


# ------------------------------------------------------------------------------
# Category G: Month-Wise Maturity Load (PRD-FR-076)
# ------------------------------------------------------------------------------
@router.get("/maturity-load", response_model=MonthWiseMaturityLoadResponse)
def get_maturity_load(
    calendar_year: Optional[int] = Query(None, ge=1990, le=2100, description="Calendar year to aggregate"),
    institution_id: Optional[str] = Query(None, description="Filter by institution"),
    bank_name: Optional[str] = Query(None, description="Filter by bank"),
    assigned_office: Optional[str] = Query(None, description="Filter by assigned office"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MonthWiseMaturityLoadResponse:
    """
    Category G: Deterministic month-wise count and sum of maturing instruments.
    """
    return DashboardService.compute_month_wise_maturity_load(
        db=db,
        current_user=current_user,
        calendar_year=calendar_year,
        institution_id=institution_id,
        bank_name=bank_name,
        assigned_office=assigned_office,
    )


# ------------------------------------------------------------------------------
# Category H: Operational Priority Queue (PRD-FR-075)
# ------------------------------------------------------------------------------
@router.get("/priority-queue", response_model=PriorityQueueResponse)
def get_priority_queue(
    min_score: float = Query(0.0, ge=0.0, le=100.0, description="Minimum composite score threshold"),
    institution_id: Optional[str] = Query(None, description="Filter by institution"),
    assigned_office: Optional[str] = Query(None, description="Filter by office jurisdiction"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Records per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PriorityQueueResponse:
    """
    Category H: Transparent operational priority queue (PRD-FR-075).
    """
    return PriorityService.compute_priority_queue(
        db=db,
        current_user=current_user,
        institution_id=institution_id,
        assigned_office=assigned_office,
        bank_name=bank_name,
        min_score=min_score,
        page=page,
        page_size=page_size,
    )


# ------------------------------------------------------------------------------
# Reusable Search & Filter Endpoints (PRD-FR-071)
# ------------------------------------------------------------------------------
@router.get("/search", response_model=InstrumentSearchResponse)
@router.get("/search/instruments", response_model=InstrumentSearchResponse)
def search_instruments(
    q: Optional[str] = Query(None, description="Keyword search in reference, bank, branch, institution"),
    institution_id: Optional[str] = Query(None, description="Filter by institution ID"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    assigned_office: Optional[str] = Query(None, description="Filter by assigned office"),
    status: Optional[str] = Query(None, description="Filter by administrative status"),
    trust_level: Optional[str] = Query(None, description="Filter by trust level"),
    maturity_from: Optional[date] = Query(None, description="Maturity date start"),
    maturity_to: Optional[date] = Query(None, description="Maturity date end"),
    issue_from: Optional[date] = Query(None, description="Issue date start"),
    issue_to: Optional[date] = Query(None, description="Issue date end"),
    min_amount: Optional[Decimal] = Query(None, ge=0, description="Minimum deposit amount"),
    max_amount: Optional[Decimal] = Query(None, ge=0, description="Maximum deposit amount"),
    has_discrepancies: Optional[bool] = Query(None, description="Filter by unresolved discrepancy presence"),
    priority_category: Optional[str] = Query(None, description="Filter by category: EXPIRING_SOON, MATURED, ACTIVE"),
    sort_by: str = Query("maturity_date", description="Allowlisted sort column"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Common role-scoped search for FDR instruments with sorting and pagination (PRD-FR-071).
    """
    return SearchService.search_instruments(
        db=db,
        current_user=current_user,
        q=q,
        institution_id=institution_id,
        bank_name=bank_name,
        assigned_office=assigned_office,
        status=status,
        trust_level=trust_level,
        maturity_from=maturity_from,
        maturity_to=maturity_to,
        issue_from=issue_from,
        issue_to=issue_to,
        min_amount=min_amount,
        max_amount=max_amount,
        has_discrepancies=has_discrepancies,
        priority_category=priority_category,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )


@router.get("/search/release-cases", response_model=ReleaseCaseSearchResponse)
def search_release_cases(
    q: Optional[str] = Query(None, description="Keyword search in case reference, instrument, bank"),
    institution_id: Optional[str] = Query(None, description="Filter by institution ID"),
    request_type: Optional[str] = Query(None, description="Filter by request type (RELEASE, DISCHARGE, REFUND)"),
    workflow_status: Optional[str] = Query(None, description="Filter by workflow status"),
    readiness_outcome: Optional[str] = Query(None, description="Filter by assessment outcome (READY, BLOCKED, INCOMPLETE)"),
    created_from: Optional[date] = Query(None, description="Created date start"),
    created_to: Optional[date] = Query(None, description="Created date end"),
    sort_by: str = Query("created_at", description="Allowlisted sort column"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Role-scoped search for Release & Refund cases with sorting and pagination.
    """
    return SearchService.search_release_cases(
        db=db,
        current_user=current_user,
        q=q,
        institution_id=institution_id,
        request_type=request_type,
        workflow_status=workflow_status,
        readiness_outcome=readiness_outcome,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )


# ------------------------------------------------------------------------------
# Operational Reports Query Endpoint (PRD-FR-074)
# ------------------------------------------------------------------------------
@router.get("/reports/{report_type}")
def get_report_dataset(
    report_type: str = Path(..., description="Report code: PENDING_VERIFICATION, UPCOMING_MATURITIES, MISSING_DOCUMENTS, INTERVENTIONS"),
    window_days: int = Query(90, ge=1, le=730, description="Maturity window days"),
    institution_id: Optional[str] = Query(None, description="Filter by institution"),
    bank_name: Optional[str] = Query(None, description="Filter by bank"),
    assigned_office: Optional[str] = Query(None, description="Filter by assigned office"),
    limit: int = Query(100, ge=1, le=200, description="Max report rows"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Constructs report datasets for authorized compliance & audit reviews (PRD-FR-074).
    Export permission is separate from viewing permission.
    """
    rpt = report_type.upper()
    if rpt == "PENDING_VERIFICATION":
        return ReportService.get_pending_verification_report(
            db=db,
            current_user=current_user,
            institution_id=institution_id,
            bank_name=bank_name,
            assigned_office=assigned_office,
            limit=limit,
        )
    elif rpt == "UPCOMING_MATURITIES":
        return ReportService.get_upcoming_maturities_report(
            db=db,
            current_user=current_user,
            window_days=window_days,
            institution_id=institution_id,
            bank_name=bank_name,
            assigned_office=assigned_office,
            limit=limit,
        )
    elif rpt == "MISSING_DOCUMENTS":
        return ReportService.get_missing_documents_report(
            db=db,
            current_user=current_user,
            institution_id=institution_id,
            limit=limit,
        )
    elif rpt == "INTERVENTIONS":
        return ReportService.get_interventions_report(
            db=db,
            current_user=current_user,
            institution_id=institution_id,
            assigned_office=assigned_office,
            limit=limit,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown report type '{report_type}'. Supported: PENDING_VERIFICATION, UPCOMING_MATURITIES, MISSING_DOCUMENTS, INTERVENTIONS",
        )


# ------------------------------------------------------------------------------
# Instrument Detail & Comprehensive History Snapshot (Prompt 3)
# ------------------------------------------------------------------------------
@router.get("/instruments/{instrument_id}/detail", response_model=InstrumentDetailSnapshotResponse)
def get_instrument_detail_snapshot(
    instrument_id: str = Path(..., description="Target instrument UUID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns complete multi-dimensional snapshot of an instrument:
    current snapshot, document history, field provenance, lifecycle/lineage,
    audit timeline, and append-only scrutiny observations.
    """
    return HistoryService.get_instrument_detail_snapshot(
        db=db, current_user=current_user, instrument_id=instrument_id
    )


# ------------------------------------------------------------------------------
# Append-Only Scrutiny Observations (PRD-FR-072 / FR-073)
# ------------------------------------------------------------------------------
@router.get("/instruments/{instrument_id}/observations", response_model=List[ScrutinyObservationItem])
def list_instrument_observations(
    instrument_id: str = Path(..., description="Target instrument UUID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Lists all observations recorded for an instrument (redacting internal-only notes for institutions).
    """
    return ScrutinyObservationService.get_observations(
        db=db, current_user=current_user, instrument_id=instrument_id
    )


@router.post("/instruments/{instrument_id}/observations", response_model=ScrutinyObservationItem, status_code=status.HTTP_201_CREATED)
def create_instrument_observation(
    instrument_id: str = Path(..., description="Target instrument UUID"),
    payload: ScrutinyObservationCreateRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Creates an append-only scrutiny observation note attached to the instrument.
    Auditors are strictly read-only.
    """
    obs = ScrutinyObservationService.create_observation(
        db=db,
        current_user=current_user,
        instrument_id=instrument_id,
        observation_text=payload.observation_text,
        observation_category=payload.observation_category,
        finding_id=payload.finding_id,
        supporting_document_id=payload.supporting_document_id,
        supporting_version_number=payload.supporting_version_number,
        is_internal_only=payload.is_internal_only,
    )
    items = ScrutinyObservationService.get_observations(db=db, current_user=current_user, instrument_id=instrument_id)
    return next(item for item in items if item["id"] == obs.id)


@router.post("/observations/{observation_id}/amend", response_model=ScrutinyObservationItem)
def amend_scrutiny_observation(
    observation_id: str = Path(..., description="Prior observation UUID to supersede"),
    payload: ScrutinyObservationAmendRequest = ...,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Amends an observation by creating a superseding observation.
    The prior note is marked SUPERSEDED but remains intact and auditable.
    """
    amended = ScrutinyObservationService.amend_observation(
        db=db,
        current_user=current_user,
        observation_id=observation_id,
        observation_text=payload.observation_text,
        amendment_reason=payload.amendment_reason,
        is_internal_only=payload.is_internal_only,
    )
    items = ScrutinyObservationService.get_observations(db=db, current_user=current_user, instrument_id=amended.instrument_id)
    return next(item for item in items if item["id"] == amended.id)


@router.post("/observations/{observation_id}/resolve", response_model=ScrutinyObservationItem)
def resolve_scrutiny_observation(
    observation_id: str = Path(..., description="Observation UUID to resolve"),
    payload: ScrutinyObservationResolveRequest = ...,
    current_user: User = Depends(require_roles([ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY, ROLE_SYSTEM_ADMIN])),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Resolves an observation with mandatory rationale.
    Requires officer or elevated authority.
    """
    resolved = ScrutinyObservationService.resolve_observation(
        db=db,
        current_user=current_user,
        observation_id=observation_id,
        resolution_reason=payload.resolution_reason,
    )
    items = ScrutinyObservationService.get_observations(db=db, current_user=current_user, instrument_id=resolved.instrument_id)
    return next(item for item in items if item["id"] == resolved.id)


# ------------------------------------------------------------------------------
# Historical Timeline Query (PRD-FR-072)
# ------------------------------------------------------------------------------
@router.get("/history/{instrument_id}")
def get_instrument_history(
    instrument_id: str = Path(..., description="Target instrument ID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Unified historical timeline combining documents, field provenance, and lifecycle evaluations (PRD-FR-072).
    """
    res = HistoryService.get_instrument_timeline(
        db=db, current_user=current_user, instrument_id=instrument_id
    )
    if "error" in res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=res["error"])
    return res


# ------------------------------------------------------------------------------
# Audit Trail Chain Verification (PRD-FR-093)
# ------------------------------------------------------------------------------
@router.get("/audit/integrity")
def verify_audit_integrity(
    sample_size: int = Query(100, ge=10, le=500, description="Number of events to verify"),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_AUDITOR, ROLE_BRANCH_HEAD])),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Verifies tamper-evident audit log sequence and integrity (PRD-FR-093).
    Strictly restricted to Auditor, Admin, and Branch Head roles.
    """
    return AuditQueryService.verify_audit_log_integrity(
        db=db, current_user=current_user, sample_size=sample_size
    )
