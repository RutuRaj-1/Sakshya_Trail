"""
Module 3 — Validation Module: Pydantic Schemas

Request and response schemas for:
- Running validation
- Listing and reading findings
- Policy configuration management
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Validation run
# ---------------------------------------------------------------------------

class RunValidationRequest(BaseModel):
    """Trigger a validation sweep for a specific instrument."""
    rule_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific rule IDs to run. If omitted, all enabled rules run.",
    )
    category: Optional[str] = Field(
        default=None,
        description="Optional rule category to filter (e.g., 'DATE_CONSISTENCY', 'AMOUNT_CONSISTENCY').",
    )


class RuleOutcomeDetail(BaseModel):
    """Result of a single rule execution within a validation run."""
    rule_id: str
    rule_version: str
    rule_type: str
    outcome: str
    category: str
    severity: str
    title: str
    explanation: str
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None
    suggested_action: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)
    policy_version_ref: Optional[str] = None
    evaluated_at: str


class ValidationRunResponse(BaseModel):
    """Response returned after a validation run completes."""
    run_id: str
    instrument_id: str
    outcomes: List[RuleOutcomeDetail] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)
    rules_evaluated: List[str] = Field(default_factory=list)
    passes_count: int = 0
    failures_count: int = 0
    warnings_count: int = 0
    not_applicable_count: int = 0
    unable_to_evaluate_count: int = 0
    new_findings_count: int = 0
    resolved_findings_count: int = 0
    policy_version_ref: str = "no-policy"
    run_at: str


class ValidationRunSummaryResponse(BaseModel):
    """Lightweight summary of a historical validation run."""
    id: str
    instrument_id: str
    triggered_by_user_id: Optional[str] = None
    run_at: datetime
    rules_evaluated: List[str] = Field(default_factory=list)
    outcome_summary: Dict[str, int] = Field(default_factory=dict)
    new_findings_count: int = 0
    resolved_findings_count: int = 0
    run_status: str = "COMPLETED"
    policy_version_ref: Optional[str] = None


class ValidationRunListResponse(BaseModel):
    """Paginated list of validation runs."""
    items: List[ValidationRunSummaryResponse]
    total: int
    skip: int
    limit: int


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

class FindingResponse(BaseModel):
    """Serialized validation finding / discrepancy record."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_fingerprint: str
    instrument_id: str
    institution_id: str
    document_id: Optional[str] = None
    document_version_id: Optional[str] = None
    rule_id: str
    rule_version: str
    rule_type: str
    category: str
    severity: str
    status: str
    title: str
    explanation: Optional[str] = None
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)
    suggested_action: Optional[str] = None
    policy_version_ref: Optional[str] = None
    first_detected_at: datetime
    last_evaluated_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_user_id: Optional[str] = None
    resolution_note: Optional[str] = None
    superseded_by_finding_id: Optional[str] = None
    validation_run_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, finding) -> "FindingResponse":
        """Convert ORM object, parsing JSON evidence_refs."""
        data = {
            "id": finding.id,
            "finding_fingerprint": finding.finding_fingerprint,
            "instrument_id": finding.instrument_id,
            "institution_id": finding.institution_id,
            "document_id": finding.document_id,
            "document_version_id": finding.document_version_id,
            "rule_id": finding.rule_id,
            "rule_version": finding.rule_version,
            "rule_type": finding.rule_type,
            "category": finding.category,
            "severity": finding.severity,
            "status": finding.status,
            "title": finding.title,
            "explanation": finding.explanation,
            "observed_value": finding.observed_value,
            "expected_value": finding.expected_value,
            "evidence_refs": finding.evidence_refs,
            "suggested_action": finding.suggested_action,
            "policy_version_ref": finding.policy_version_ref,
            "first_detected_at": finding.first_detected_at,
            "last_evaluated_at": finding.last_evaluated_at,
            "resolved_at": finding.resolved_at,
            "resolved_by_user_id": finding.resolved_by_user_id,
            "resolution_note": finding.resolution_note,
            "superseded_by_finding_id": finding.superseded_by_finding_id,
            "validation_run_id": finding.validation_run_id,
            "created_at": finding.created_at,
            "updated_at": finding.updated_at,
        }
        return cls(**data)


class FindingListResponse(BaseModel):
    items: List[FindingResponse]
    total: int
    skip: int
    limit: int


class DismissFindingRequest(BaseModel):
    reason: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Human-readable reason for dismissal. Must be at least 10 characters.",
    )


# ---------------------------------------------------------------------------
# Rule registry listing
# ---------------------------------------------------------------------------

class RuleRegistryEntry(BaseModel):
    rule_id: str
    rule_version: str
    rule_type: str
    category: str
    severity: str
    description: str
    enabled: bool


# ---------------------------------------------------------------------------
# Policy configuration
# ---------------------------------------------------------------------------

class PolicyConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: Optional[str] = None
    config_key: str
    display_name: str
    config_value: str
    value_type: str
    description: Optional[str] = None
    policy_version: int
    is_active: bool
    authorized_by_user_id: Optional[str] = None
    effective_from: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PolicyConfigCreateRequest(BaseModel):
    config_key: str = Field(..., min_length=1, max_length=100)
    config_value: str = Field(..., min_length=1)
    value_type: str = Field(
        ...,
        description="One of: decimal, integer, string, json_list, boolean",
    )
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    institution_id: Optional[str] = Field(
        None,
        description="If set, this is an institution-specific override. If None, applies globally.",
    )
    effective_from: Optional[str] = Field(
        None,
        description="ISO date string for when this policy takes effect.",
    )
