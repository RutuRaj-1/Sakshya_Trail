"""
Module 6 — Release / Refund Case Management
Pydantic Schemas for Requests, Responses, Checklist Profiles, and Decision Records.
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.modules.release.enums import (
    ReleaseRequestType,
    ReleaseCaseType,
    ReleaseWorkflowStatus,
    ChecklistProfileStatus,
    ChecklistRequirementType,
    ChecklistEvaluationType,
    CheckResultStatus,
    ReadinessAssessmentOutcome,
    ReleaseDecisionType,
    ReleaseOrderStatus,
    BankActionStatus,
)


# --- Checklist Item Schemas ----------------------------------------------------

class ChecklistItemCreate(BaseModel):
    item_code: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    explanation: str
    requirement_type: ChecklistRequirementType
    is_mandatory_blocker: bool = True
    evaluation_type: ChecklistEvaluationType = ChecklistEvaluationType.AUTOMATED
    expected_evidence_source: str = Field(..., max_length=100)
    sort_order: int = 0
    is_active: bool = True


class ChecklistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    item_code: str
    title: str
    explanation: str
    requirement_type: str
    is_mandatory_blocker: bool
    evaluation_type: str
    expected_evidence_source: str
    sort_order: int
    is_active: bool
    created_at: datetime


# --- Checklist Profile Schemas -------------------------------------------------

class ChecklistProfileCreate(BaseModel):
    profile_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    version: int = 1
    request_type: ReleaseRequestType
    case_type: ReleaseCaseType
    is_demo: bool = False
    demo_disclaimer: str = "DEMO RELEASE POLICY — NOT OFFICIAL AICTE POLICY"
    description: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    items: List[ChecklistItemCreate] = []


class ChecklistProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_code: str
    name: str
    version: int
    request_type: str
    case_type: str
    status: str
    is_demo: bool
    demo_disclaimer: str
    description: Optional[str]
    effective_from: Optional[date]
    effective_to: Optional[date]
    created_at: datetime
    items: List[ChecklistItemResponse] = []


# --- Readiness Assessment & Result Schemas -------------------------------------

class ReadinessCheckResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_code: str
    status: str
    is_mandatory_blocker: bool
    explanation: str
    evidence_references_json: Optional[str]
    source_module: str
    evaluated_at: datetime


class ReadinessAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    release_request_id: str
    profile_id: str
    profile_version: int
    assessment_outcome: str
    total_items_count: int
    satisfied_count: int
    blockers_count: int
    pending_count: int
    advisory_flags_count: int
    summary_notes: Optional[str]
    evaluated_by_user_id: Optional[str]
    evaluated_at: datetime
    results: List[ReadinessCheckResultResponse] = []


# --- Review Observation Schemas ------------------------------------------------

class ReviewObservationCreate(BaseModel):
    observation_type: str = Field(..., max_length=50)
    notes: str = Field(..., min_length=3)
    is_blocking: bool = False


class ReviewObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    release_request_id: str
    officer_user_id: str
    observation_type: str
    notes: str
    is_blocking: bool
    created_at: datetime


# --- Decision Schemas ----------------------------------------------------------

class ReleaseDecisionCreate(BaseModel):
    decision_type: ReleaseDecisionType
    reason: str = Field(..., min_length=3, description="Mandatory non-empty justification")
    evidence_references_json: Optional[str] = None


class ReleaseDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    release_request_id: str
    actor_user_id: str
    actor_role: str
    decision_type: str
    reason: str
    policy_version: Optional[int]
    readiness_assessment_id: Optional[str]
    evidence_references_json: Optional[str]
    previous_status: str
    new_status: str
    created_at: datetime


# --- Release Order Schemas -----------------------------------------------------

class ReleaseOrderCreate(BaseModel):
    order_reference_number: str = Field(..., min_length=3, max_length=100)
    order_date: date
    supporting_document_id: Optional[str] = None
    is_synthetic_demo: bool = False
    notes: Optional[str] = None


class ReleaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    release_request_id: str
    order_reference_number: str
    order_date: date
    responsible_officer_id: str
    supporting_document_id: Optional[str]
    status: str
    bank_action_status: str
    bank_action_notes: Optional[str]
    bank_action_confirmed_at: Optional[datetime]
    is_synthetic_demo: bool
    notes: Optional[str]
    created_at: datetime


# --- Core Release Request Schemas ----------------------------------------------

class ReleaseRequestCreate(BaseModel):
    instrument_id: str
    request_type: ReleaseRequestType
    case_type: ReleaseCaseType
    request_reason: str = Field(..., min_length=5, description="Mandatory detailed justification for release/refund")
    policy_profile_id: Optional[str] = None


class ReleaseRequestUpdate(BaseModel):
    request_reason: Optional[str] = Field(None, min_length=5)
    case_type: Optional[ReleaseCaseType] = None
    policy_profile_id: Optional[str] = None


class ReleaseRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_number: str
    instrument_id: str
    institution_id: str
    request_type: str
    case_type: str
    policy_profile_id: Optional[str]
    policy_version: Optional[int]
    requester_id: str
    request_reason: str
    workflow_status: str
    assigned_reviewer_id: Optional[str]
    assigned_office: Optional[str]
    latest_assessment_id: Optional[str]
    submitted_at: Optional[datetime]
    closed_at: Optional[datetime]
    closure_notes: Optional[str]
    version: int
    created_at: datetime
    updated_at: datetime


class ReleaseRequestDetailResponse(ReleaseRequestResponse):
    policy_profile: Optional[ChecklistProfileResponse] = None
    assessments: List[ReadinessAssessmentResponse] = []
    decisions: List[ReleaseDecisionResponse] = []
    observations: List[ReviewObservationResponse] = []
    release_orders: List[ReleaseOrderResponse] = []
