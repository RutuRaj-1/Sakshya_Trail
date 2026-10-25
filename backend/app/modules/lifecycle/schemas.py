"""
Module 5 — Lifecycle Orchestration & Renewal
Pydantic Schemas for Policies, Lineage, and Evaluations
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.modules.lifecycle.enums import (
    PolicyStatus,
    MaturityStage,
    DueCondition,
    RenewalComparisonMethod,
    LineageRelationshipType,
    LineageRelationshipStatus,
    ContinuityIndicator,
)


# --- Policy Schemas -------------------------------------------------------------

class LifecyclePolicyBase(BaseModel):
    policy_code: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Z0-9_\-]+$")
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    is_demo: bool = False
    label: str = "DEMO POLICY — NOT OFFICIAL AICTE POLICY"
    scope_instrument_type: Optional[str] = None
    scope_institution_type: Optional[str] = None
    scope_assigned_office: Optional[str] = None
    timezone: str = "Asia/Kolkata"
    reminder_intervals_days: List[int] = Field(default_factory=lambda: [90, 60, 30, 15, 7])
    recipient_roles_by_interval: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "90": ["INSTITUTION_USER"],
            "60": ["INSTITUTION_USER"],
            "30": ["INSTITUTION_USER", "SCRUTINY_OFFICER"],
            "15": ["INSTITUTION_USER", "SCRUTINY_OFFICER"],
            "7": ["INSTITUTION_USER", "SCRUTINY_OFFICER", "BRANCH_HEAD"],
        }
    )
    institution_action_lead_days: int = Field(default=30, ge=1, le=365)
    officer_action_lead_days: int = Field(default=15, ge=1, le=365)
    escalation_interval_days: int = Field(default=7, ge=1, le=180)
    escalation_target_role: str = "BRANCH_HEAD"
    maturity_critical_lead_days: int = Field(default=15, ge=1, le=180)
    renewal_comparison_method: RenewalComparisonMethod = RenewalComparisonMethod.ISSUE_DATE_TO_MATURITY_DATE
    max_allowed_gap_days: int = Field(default=0, ge=0, le=180)
    max_allowed_overlap_days: int = Field(default=30, ge=0, le=365)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

    @field_validator("reminder_intervals_days")
    @classmethod
    def validate_intervals(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("At least one reminder interval must be configured")
        for x in v:
            if x <= 0:
                raise ValueError(f"Reminder intervals must be strictly positive integers: {x}")
        # Return sorted descending (e.g. 90, 60, 30)
        return sorted(list(set(v)), reverse=True)


class LifecyclePolicyCreate(LifecyclePolicyBase):
    pass


class LifecyclePolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PolicyStatus] = None
    reminder_intervals_days: Optional[List[int]] = None
    recipient_roles_by_interval: Optional[Dict[str, List[str]]] = None
    institution_action_lead_days: Optional[int] = None
    officer_action_lead_days: Optional[int] = None
    escalation_interval_days: Optional[int] = None
    escalation_target_role: Optional[str] = None
    max_allowed_gap_days: Optional[int] = None
    max_allowed_overlap_days: Optional[int] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class LifecyclePolicyResponse(LifecyclePolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    status: str
    created_by_user_id: Optional[str] = None
    approved_by_user_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Lineage Schemas ------------------------------------------------------------

class LineageCreateRequest(BaseModel):
    predecessor_instrument_id: str
    successor_instrument_id: str
    relationship_type: LineageRelationshipType = LineageRelationshipType.RENEWAL
    reason_or_reference: Optional[str] = Field(None, max_length=500)
    policy_id: Optional[str] = None
    allow_authorized_transfer: bool = False  # Explicit override flag for cross-institution mergers


class LineageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    predecessor_instrument_id: str
    successor_instrument_id: str
    institution_id: str
    relationship_type: str
    relationship_status: str
    reason_or_reference: Optional[str] = None
    policy_id: Optional[str] = None
    policy_version: Optional[int] = None
    validity_gap_days: Optional[int] = None
    validity_overlap_days: Optional[int] = None
    continuity_indicator: str
    concurrency_version: int
    created_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LineageChainItem(BaseModel):
    instrument_id: str
    reference_number: str
    bank_name: str
    amount: str
    issue_date: Optional[str] = None
    maturity_date: Optional[str] = None
    status: str
    trust_level: str
    depth: int


class LineageTreeResponse(BaseModel):
    current_instrument_id: str
    ancestors: List[LineageChainItem]
    successors: List[LineageChainItem]
    direct_predecessor_lineage: Optional[LineageResponse] = None
    direct_successor_lineage: Optional[LineageResponse] = None


# --- Evaluation Schemas ---------------------------------------------------------

class LifecycleEvaluationRequest(BaseModel):
    instrument_id: str
    policy_id: Optional[str] = None
    simulated_date: Optional[date] = None  # Permitted only when ENABLE_LIFECYCLE_DATE_ADVANCE is active
    force_evaluation: bool = False


class LifecycleEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    policy_id: Optional[str] = None
    policy_version: Optional[int] = None
    evaluation_date: date
    evaluation_timestamp: datetime
    evaluation_timezone: str
    days_to_maturity: Optional[int] = None
    maturity_stage: str
    institution_action_due_date: Optional[date] = None
    officer_action_due_date: Optional[date] = None
    is_overdue: bool
    is_escalated: bool
    escalation_role: Optional[str] = None
    due_condition: str
    matched_reminder_interval_days: Optional[int] = None
    lineage_relationship_id: Optional[str] = None
    is_material_transition: bool
    prior_evaluation_id: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime


class BatchEvaluationRequest(BaseModel):
    instrument_ids: Optional[List[str]] = None
    institution_id: Optional[str] = None
    simulated_date: Optional[date] = None
    limit: int = 100


class BatchEvaluationResponse(BaseModel):
    evaluated_count: int
    material_transitions_count: int
    evaluations: List[LifecycleEvaluationResponse]


# --- Scheduler & Diagnostics Schemas --------------------------------------------

class LifecycleJobRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: str
    status: str
    trigger_source: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    evaluation_date: date
    evaluation_timezone: str
    total_eligible: int
    evaluated_count: int
    success_count: int
    error_count: int
    material_transitions_count: int
    approaching_count: int
    matured_count: int
    overdue_count: int
    worker_instance_id: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    error_summary_json: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime


class SchedulerRunStatusResponse(BaseModel):
    last_attempted_run: Optional[LifecycleJobRunResponse] = None
    last_successful_run: Optional[LifecycleJobRunResponse] = None
    recent_runs: List[LifecycleJobRunResponse] = Field(default_factory=list)


class TriggerJobRequest(BaseModel):
    batch_size: int = Field(default=50, ge=1, le=500)
    simulated_date: Optional[date] = None
    force_reevaluation: bool = False


# --- Demo Clock Schemas ---------------------------------------------------------

class DemoClockStatusResponse(BaseModel):
    is_simulated: bool
    active_timezone: str
    today: str
    now_utc: str
    offset_days: int
    disclaimer: Optional[str] = None


class DemoClockAdvanceRequest(BaseModel):
    days: Optional[int] = Field(None, ge=1, le=3650)
    target_date: Optional[date] = None


# --- Monitoring Schemas ---------------------------------------------------------

class MonitoringInstrumentItem(BaseModel):
    instrument_id: str
    institution_id: str
    institution_name: Optional[str] = None
    reference_number: str
    bank_name: str
    amount: str
    issue_date: Optional[str] = None
    maturity_date: Optional[str] = None
    days_to_maturity: Optional[int] = None
    maturity_stage: str
    due_condition: str
    is_overdue: bool
    is_escalated: bool
    escalation_role: Optional[str] = None
    institution_action_due_date: Optional[str] = None
    officer_action_due_date: Optional[str] = None
    administrative_status: str
    trust_level: str
    unresolved_findings_count: int = 0
    verification_status: Optional[str] = None


class MonitoringListResponse(BaseModel):
    category: str  # "APPROACHING_MATURITY", "MATURED", "OVERDUE"
    total_count: int
    page: int
    limit: int
    items: List[MonitoringInstrumentItem]

