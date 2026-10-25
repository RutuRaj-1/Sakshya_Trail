"""
Dashboard & Command Center Module - Pydantic Schemas
Strict, typed schemas for aggregation APIs, metric definitions, and queue queries.
"""
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel, Field
from app.modules.dashboard.metrics import MetricDefinition


# ------------------------------------------------------------------------------
# Module 1 Legacy Compatibility Schema
# ------------------------------------------------------------------------------
class DashboardSummaryResponse(BaseModel):
    """Preserves exact compatibility with Module 1 dashboard."""
    total_active_institutions: int
    total_inactive_institutions: int
    total_instruments: int
    total_deposit_value: str
    instruments_by_status: Dict[str, int]
    instruments_by_trust_level: Dict[str, int]
    instruments_approaching_maturity: int


# ------------------------------------------------------------------------------
# Metric Dictionary Schema (PRD-FR-077)
# ------------------------------------------------------------------------------
class MetricDictionaryResponse(BaseModel):
    """Catalog of all documented command center metrics."""
    total_metrics: int
    metrics: List[MetricDefinition]


# ------------------------------------------------------------------------------
# Category A: Status Counts (PRD-FR-070a)
# ------------------------------------------------------------------------------
class StatusCountsResponse(BaseModel):
    """
    Administrative status breakdown for statutory instruments.
    Maintains strict separation between administrative status, trust level, and maturity.
    """
    metric_id: str = "MTR-STAT-ALL"
    active_count: int = Field(..., description="Active in-force instruments beyond expiry window")
    expiring_soon_count: int = Field(..., description="Instruments within monitoring expiry window")
    matured_count: int = Field(..., description="Term elapsed without renewal or release")
    renewed_count: int = Field(..., description="Instruments with verified active successor in lineage")
    released_count: int = Field(..., description="Formally discharged/released instruments")
    pending_count: int = Field(..., description="Draft, submitted, or intake scrutiny instruments")
    total_instruments: int = Field(..., description="Total non-cancelled instruments in scope")
    total_deposit_value: str = Field(..., description="Total deposit value in INR (exact decimal string)")
    window_days: int = Field(90, description="Monitoring window days applied for expiring soon")
    date_basis: str = Field("Asia/Kolkata calendar date", description="Timezone and calendar basis")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------------------
# Category B: Maturity Window (PRD-FR-070b)
# ------------------------------------------------------------------------------
class MaturityWindowRecordItem(BaseModel):
    """Individual instrument summary in maturity window drilldown."""
    id: str
    reference_number: str
    institution_id: str
    institution_name: Optional[str] = None
    bank_name: str
    branch: Optional[str] = None
    amount: str
    issue_date: date
    maturity_date: date
    days_to_maturity: int
    status: str
    trust_level: str
    assigned_office: Optional[str] = None


class MaturityWindowResponse(BaseModel):
    """Instruments maturing within an inclusive selectable date window."""
    metric_id: str = "MTR-MAT-WINDOW"
    start_date: date
    end_date: date
    total_instruments: int
    total_deposit_value: str
    by_bank: Dict[str, int]
    by_office: Dict[str, int]
    page: int = 1
    page_size: int = 50
    total_records: int
    records: List[MaturityWindowRecordItem]


# ------------------------------------------------------------------------------
# Category C: Overdue & Escalated Work (PRD-FR-070c)
# ------------------------------------------------------------------------------
class OverdueItem(BaseModel):
    """Individual overdue or escalated work item."""
    record_id: str
    record_type: str = Field("INSTRUMENT", description="INSTRUMENT or RELEASE_CASE")
    reference_number: str
    institution_id: str
    institution_name: Optional[str] = None
    assigned_office: Optional[str] = None
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    due_date: Optional[date] = None
    days_overdue: int
    is_escalated: bool
    escalation_role: Optional[str] = None
    due_condition: str


class OverdueEscalatedResponse(BaseModel):
    """Breakdown of overdue compliance actions and escalated cases."""
    metric_id: str = "MTR-OVERDUE-ESCALATED"
    total_overdue: int
    total_escalated: int
    by_office: Dict[str, int]
    by_assignee: Optional[Dict[str, int]] = None  # None for institution users
    records: List[OverdueItem]


# ------------------------------------------------------------------------------
# Category D: Verification Queue (PRD-FR-070d)
# ------------------------------------------------------------------------------
class VerificationQueueItem(BaseModel):
    """Item in bank verification queue."""
    request_id: str
    reference_code: str
    instrument_id: str
    instrument_reference: str
    institution_id: str
    institution_name: Optional[str] = None
    bank_name: str
    channel: str
    status: str
    created_at: datetime
    age_days: int
    attempt_count: int
    is_source_unavailable: bool


class VerificationQueueResponse(BaseModel):
    """Outstanding verification requests, age distribution, and failure analysis."""
    metric_id: str = "MTR-VERIF-QUEUE"
    total_outstanding: int
    average_age_days: float
    age_distribution: Dict[str, int] = Field(
        ..., description="Bucket counts: '<7d', '7-14d', '15-30d', '>30d'"
    )
    source_unavailable_count: int
    failed_count: int
    records: List[VerificationQueueItem]


# ------------------------------------------------------------------------------
# Category E: Document Completeness (PRD-FR-070e)
# ------------------------------------------------------------------------------
class DocumentCompletenessResponse(BaseModel):
    """Document completeness checklist outcomes across authorized scope."""
    metric_id: str = "MTR-DOC-COMPLETENESS"
    policy_configured: bool
    policy_version: Optional[int] = None
    policy_status_message: Optional[str] = None
    present_count: int
    missing_count: int
    unreadable_count: int
    wrong_category_count: int
    awaiting_confirmation_count: int
    missing_categories_breakdown: Dict[str, int] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------------------
# Category F: Release Blockers (PRD-FR-070f)
# ------------------------------------------------------------------------------
class ReleaseBlockerCaseItem(BaseModel):
    """Release case obstructed by unmet mandatory checklist items."""
    case_id: str
    case_number: str
    instrument_id: str
    instrument_reference: str
    institution_id: str
    institution_name: Optional[str] = None
    case_type: str
    workflow_status: str
    blockers_count: int
    unsatisfied_item_codes: List[str]
    latest_assessment_outcome: str


class ReleaseBlockersResponse(BaseModel):
    """Active release requests obstructed by unmet checklist items."""
    metric_id: str = "MTR-REL-BLOCKERS"
    policy_configured: bool
    policy_version: Optional[int] = None
    total_active_release_requests: int
    blocked_requests_count: int
    ready_requests_count: int
    unmet_mandatory_items_count: int
    blockers_by_requirement_type: Dict[str, int] = Field(default_factory=dict)
    cases: List[ReleaseBlockerCaseItem] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# Category G: Month-Wise Maturity Load (PRD-FR-076)
# ------------------------------------------------------------------------------
class MonthWiseMaturityPoint(BaseModel):
    """Single month deterministic maturity point."""
    year: int
    month: int
    month_label: str = Field(..., description="Formatted 'YYYY-MM'")
    instrument_count: int
    total_amount: str = Field(..., description="Exact sum in INR")


class MonthWiseMaturityLoadResponse(BaseModel):
    """Deterministic month-wise maturity distribution (count and amount)."""
    metric_id: str = "MTR-MAT-LOAD"
    calendar_year: Optional[int] = None
    points: List[MonthWiseMaturityPoint]
    grand_total_instruments: int
    grand_total_amount: str
    disclaimer: str = "Deterministic calendar aggregation based strictly on recorded instrument maturity dates. Not a forecast or projection."


# ------------------------------------------------------------------------------
# Category H: Priority Queue (PRD-FR-075)
# ------------------------------------------------------------------------------
class PriorityQueueItem(BaseModel):
    """Urgency-ranked item in operational scrutiny queue."""
    instrument_id: str
    reference_number: str
    institution_id: str
    institution_name: Optional[str] = None
    bank_name: str
    amount: str
    maturity_date: date
    days_to_maturity: int
    status: str
    trust_level: str
    priority_score: float = Field(..., description="Composite priority score [0.0 - 100.0]")
    urgency_factor: float = Field(..., description="Maturity proximity factor [0.0 - 100.0]")
    discrepancy_factor: float = Field(..., description="Finding severity factor [0.0 - 100.0]")
    trust_factor: float = Field(..., description="Evidentiary trust factor [0.0 - 100.0]")
    overdue_factor: float = Field(..., description="Overdue lead time factor [0.0 - 100.0]")


class PriorityQueueResponse(BaseModel):
    """Operational priority queue with full factor transparency."""
    metric_id: str = "MTR-PRIORITY-QUEUE"
    total_count: int
    page: int = 1
    page_size: int = 50
    weights_applied: Dict[str, float] = Field(
        default_factory=lambda: {
            "urgency": 0.35,
            "discrepancy": 0.25,
            "trust": 0.20,
            "overdue": 0.20,
        },
        description="Transparent weights assigned to factors (assumptions disclosed)",
    )
    items: List[PriorityQueueItem]


# ------------------------------------------------------------------------------
# Consolidated Command Center Overview
# ------------------------------------------------------------------------------
class CommandCenterOverviewResponse(BaseModel):
    """Comprehensive high-level command center overview."""
    generated_at: datetime
    user_role: str
    scope_description: str
    status_counts: StatusCountsResponse
    maturity_window: MaturityWindowResponse
    overdue_escalated: OverdueEscalatedResponse
    verification_queue: VerificationQueueResponse
    document_completeness: DocumentCompletenessResponse
    release_blockers: ReleaseBlockersResponse
    maturity_load: MonthWiseMaturityLoadResponse


# ------------------------------------------------------------------------------
# Prompt 3: Unified Search, History & Scrutiny Observation Schemas
# ------------------------------------------------------------------------------

class InstrumentSearchItem(BaseModel):
    """Concise instrument search hit with role-masked attributes."""
    id: str
    reference_number: str
    institution_id: str
    institution_name: Optional[str] = None
    bank_name: str
    branch: Optional[str] = None
    amount: str
    currency: str = "INR"
    issue_date: str
    maturity_date: str
    status: str
    trust_level: str
    assigned_office: Optional[str] = None
    created_at: Optional[str] = None
    has_active_discrepancies: bool = False
    pending_verification: bool = False


class InstrumentSearchResponse(BaseModel):
    """Server-backed search results for FDR instruments."""
    total_count: int
    skip: int
    limit: int
    sort_by: str
    sort_order: str
    records: List[InstrumentSearchItem]


class ReleaseCaseSearchItem(BaseModel):
    """Concise release/refund case search hit."""
    id: str
    case_number: str
    case_reference: Optional[str] = None
    instrument_id: str
    instrument_reference: Optional[str] = None
    institution_id: str
    institution_name: Optional[str] = None
    request_type: str
    case_type: str
    workflow_status: str
    readiness_outcome: Optional[str] = None
    blockers_count: int = 0
    created_at: str


class ReleaseCaseSearchResponse(BaseModel):
    """Server-backed search results for Release & Refund cases."""
    total_count: int
    skip: int
    limit: int
    sort_by: str
    sort_order: str
    records: List[ReleaseCaseSearchItem]


class DocumentHistoryItem(BaseModel):
    """Versioned document metadata and secure download access."""
    id: str
    document_id: str
    version_number: int
    category: str
    uploader_user_id: Optional[str] = None
    uploader_name: Optional[str] = None
    uploaded_at: str
    sha256_hash: str
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    is_verified: bool = False
    download_url: str


class FieldProvenanceHistoryItem(BaseModel):
    """Field-level value change and evidentiary source provenance."""
    id: str
    field_name: str
    recorded_value: str
    previous_value: Optional[str] = None
    source_type: str
    source_actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    evidence_reference: Optional[str] = None
    reason: Optional[str] = None
    created_at: str


class LifecycleLineageItem(BaseModel):
    """Lifecycle event or lineage edge."""
    event_type: str
    timestamp: str
    actor_id: Optional[str] = None
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    is_simulated: bool = False


class TimelineEventItem(BaseModel):
    """Chronological material event for audit trail."""
    event_type: str
    timestamp: str
    actor_id: Optional[str] = None
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ScrutinyObservationItem(BaseModel):
    """Append-only scrutiny observation with supersession lineage."""
    id: str
    instrument_id: Optional[str] = None
    release_request_id: Optional[str] = None
    finding_id: Optional[str] = None
    supporting_document_id: Optional[str] = None
    supporting_version_number: Optional[int] = None
    observation_category: str
    observation_text: str
    author_user_id: str
    author_name: Optional[str] = None
    author_role: str
    status: str
    resolution_reason: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by_user_id: Optional[str] = None
    resolved_by_name: Optional[str] = None
    supersedes_id: Optional[str] = None
    superseded_by_id: Optional[str] = None
    is_internal_only: bool = False
    created_at: str
    updated_at: str


class InstrumentDetailSnapshotResponse(BaseModel):
    """Complete multi-dimensional snapshot of an instrument and its full historical record."""
    instrument: Dict[str, Any]
    documents: List[DocumentHistoryItem]
    field_history: List[FieldProvenanceHistoryItem]
    lifecycle_lineage: List[LifecycleLineageItem]
    timeline: List[TimelineEventItem]
    observations: List[ScrutinyObservationItem]


class ScrutinyObservationCreateRequest(BaseModel):
    """Creation of a new append-only observation note."""
    observation_text: str = Field(..., min_length=3, max_length=2000, description="Mandatory observation content")
    observation_category: str = Field("GENERAL", description="GENERAL, DISCREPANCY, DOCUMENT, MANDATE, COMPLIANCE")
    finding_id: Optional[str] = None
    supporting_document_id: Optional[str] = None
    supporting_version_number: Optional[int] = None
    is_internal_only: bool = False


class ScrutinyObservationAmendRequest(BaseModel):
    """Amendment or correction creating a superseding observation."""
    observation_text: str = Field(..., min_length=3, max_length=2000, description="Updated observation content")
    amendment_reason: str = Field(..., min_length=3, max_length=500, description="Reason for amendment/correction")
    is_internal_only: bool = False


class ScrutinyObservationResolveRequest(BaseModel):
    """Reasoned resolution of an observation note."""
    resolution_reason: str = Field(..., min_length=3, max_length=1000, description="Reason for resolving/dismissing")

