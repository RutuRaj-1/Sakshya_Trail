"""
Module 7 — Command Center, Search, Reporting & Audit
Central Metric Dictionary (PRD-FR-070, PRD-FR-076, PRD-FR-077)

Formal, traceable catalog of all dashboard, aggregation, and command center metrics.
Defines calculation logic, criteria, exclusions, source entities, date conventions,
authorization scoping, and handling of unconfigured or absent policy data.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class MetricDefinition(BaseModel):
    """
    Formal specification of a command center / dashboard metric.
    Complies with PRD-FR-077: one-page metric definition dictionary.
    """
    metric_id: str = Field(..., description="Unique stable metric identifier")
    display_label: str = Field(..., description="Human-readable title for UI cards and headers")
    category: str = Field(..., description="Functional metric grouping")
    prd_mapping: str = Field(..., description="Associated PRD functional requirement ID")
    description: str = Field(..., description="Authoritative definition and business intent")
    calculation_rule: str = Field(..., description="Exact algorithmic formula or SQL aggregation rule")
    inclusion_criteria: str = Field(..., description="Conditions for including a record in aggregation")
    exclusion_criteria: str = Field(..., description="Explicitly excluded record types or states")
    date_basis: str = Field(..., description="Primary date field used and timezone convention")
    supported_filters: List[str] = Field(default_factory=list, description="Allowlisted query parameters")
    authorization_scope: str = Field(..., description="Role-scoping and visibility restrictions")
    unconfigured_handling: str = Field(..., description="Behavior when policy or config is missing")
    api_endpoint: str = Field(..., description="Primary REST API endpoint serving this metric")


METRIC_DICTIONARY: Dict[str, MetricDefinition] = {
    # --------------------------------------------------------------------------
    # Category A: Instrument Status Counts (PRD-FR-070a)
    # --------------------------------------------------------------------------
    "MTR-STAT-ACTIVE": MetricDefinition(
        metric_id="MTR-STAT-ACTIVE",
        display_label="Active Instruments",
        category="STATUS_COUNTS",
        prd_mapping="PRD-FR-070a",
        description="Statutory security deposits and FDRs currently in force, beyond immediate expiry window, and not released or superseded.",
        calculation_rule="COUNT(instruments.id) WHERE status IN ('ACTIVE', 'REGISTERED', 'VERIFIED') AND maturity_date > (today + window_days) AND id NOT IN (active_predecessors) AND status != 'RELEASED'",
        inclusion_criteria="Administrative status is ACTIVE, REGISTERED, or VERIFIED; maturity date is strictly beyond the expiring-soon threshold.",
        exclusion_criteria="Predecessor instruments with verified active renewal; instruments marked RELEASED, CANCELLED, or in pending draft/scrutiny states.",
        date_basis="Instrument.maturity_date evaluated against current business date (Asia/Kolkata).",
        supported_filters=["institution_id", "bank_name", "assigned_office", "status", "trust_level"],
        authorization_scope="INSTITUTION_USER restricted to own institution; bureau roles view authorized office/national scope; AUDITOR read-only.",
        unconfigured_handling="Returns 0 if no records match authorized scope.",
        api_endpoint="/api/v1/dashboard/status-counts",
    ),
    "MTR-STAT-EXPIRING-SOON": MetricDefinition(
        metric_id="MTR-STAT-EXPIRING-SOON",
        display_label="Expiring Soon Instruments",
        category="STATUS_COUNTS",
        prd_mapping="PRD-FR-070a",
        description="Instruments maturing within the configured monitoring window (default 90 days) requiring renewal action or scrutiny.",
        calculation_rule="COUNT(instruments.id) WHERE status IN ('ACTIVE', 'REGISTERED', 'VERIFIED') AND maturity_date >= today AND maturity_date <= (today + window_days) AND status != 'RELEASED' AND id NOT IN (active_predecessors)",
        inclusion_criteria="Maturity date between today and today + window_days (inclusive); active registry status; not released.",
        exclusion_criteria="Instruments already matured (maturity_date < today), already replaced/renewed with an active successor, or formally released.",
        date_basis="Instrument.maturity_date against Asia/Kolkata current business calendar date.",
        supported_filters=["institution_id", "bank_name", "assigned_office", "window_days", "trust_level"],
        authorization_scope="INSTITUTION_USER restricted to own institution; bureau roles view authorized office/national scope.",
        unconfigured_handling="Defaults window to 90 days if lifecycle policy interval is unconfigured.",
        api_endpoint="/api/v1/dashboard/status-counts",
    ),
    "MTR-STAT-MATURED": MetricDefinition(
        metric_id="MTR-STAT-MATURED",
        display_label="Matured Instruments",
        category="STATUS_COUNTS",
        prd_mapping="PRD-FR-070a",
        description="Instruments whose term has elapsed without a confirmed release or verified renewal successor.",
        calculation_rule="COUNT(instruments.id) WHERE maturity_date < today AND status != 'RELEASED' AND id NOT IN (active_predecessors) AND status NOT IN ('DRAFT', 'SUBMITTED', 'UNDER_SCRUTINY')",
        inclusion_criteria="Recorded maturity date is strictly prior to today; instrument is not formally released or renewed.",
        exclusion_criteria="Predecessors with active renewal edge; instruments formally released; unsubmitted draft records.",
        date_basis="Instrument.maturity_date < today (Asia/Kolkata).",
        supported_filters=["institution_id", "bank_name", "assigned_office", "trust_level"],
        authorization_scope="INSTITUTION_USER restricted to own institution; bureau roles view authorized scope.",
        unconfigured_handling="Returns 0 if no records match criteria.",
        api_endpoint="/api/v1/dashboard/status-counts",
    ),
    "MTR-STAT-RENEWED": MetricDefinition(
        metric_id="MTR-STAT-RENEWED",
        display_label="Renewed / Replaced Instruments",
        category="STATUS_COUNTS",
        prd_mapping="PRD-FR-070a",
        description="Instruments that have undergone formal renewal or replacement with an active successor link in lineage graph.",
        calculation_rule="COUNT(DISTINCT instrument_lineages.predecessor_instrument_id) WHERE relationship_status = 'ACTIVE' AND relationship_type IN ('RENEWAL', 'REPLACEMENT')",
        inclusion_criteria="Instrument is recorded as predecessor in active lineage relationship; predecessor history remains immutable.",
        exclusion_criteria="Cancelled or rejected renewal edges; instruments without valid successor links.",
        date_basis="Lineage creation timestamp and instrument effective dates.",
        supported_filters=["institution_id", "bank_name", "assigned_office"],
        authorization_scope="Tenant-isolated by institution; bureau officers view permitted scope.",
        unconfigured_handling="Returns 0 if no lineage edges exist.",
        api_endpoint="/api/v1/dashboard/status-counts",
    ),
    "MTR-STAT-RELEASED": MetricDefinition(
        metric_id="MTR-STAT-RELEASED",
        display_label="Released Instruments",
        category="STATUS_COUNTS",
        prd_mapping="PRD-FR-070a",
        description="Instruments formally discharged, refund processed, or lien released by competent authority order.",
        calculation_rule="COUNT(instruments.id) WHERE status = 'RELEASED'",
        inclusion_criteria="Instrument administrative status is exactly 'RELEASED' following executed release order.",
        exclusion_criteria="Cases pending bank-side lien release or under scrutiny; draft release requests.",
        date_basis="Instrument.updated_at or release_order_records.executed_at.",
        supported_filters=["institution_id", "bank_name", "assigned_office"],
        authorization_scope="INSTITUTION_USER restricted to own institution; bureau roles view authorized office/national scope.",
        unconfigured_handling="Returns 0 if no records match criteria.",
        api_endpoint="/api/v1/dashboard/status-counts",
    ),
    "MTR-STAT-PENDING": MetricDefinition(
        metric_id="MTR-STAT-PENDING",
        display_label="Pending Registration / Review",
        category="STATUS_COUNTS",
        prd_mapping="PRD-FR-070a",
        description="Instruments in intake, draft, submission, or deficiency correction stages prior to formal active registry.",
        calculation_rule="COUNT(instruments.id) WHERE status IN ('DRAFT', 'SUBMITTED', 'UNDER_SCRUTINY', 'UNDER_REVIEW', 'RETURNED_FOR_CORRECTION')",
        inclusion_criteria="Administrative workflow status indicates intake or review underway.",
        exclusion_criteria="Active registered instruments; formally matured, renewed, or released instruments.",
        date_basis="Instrument.created_at or submission instant.",
        supported_filters=["institution_id", "bank_name", "assigned_office", "status"],
        authorization_scope="INSTITUTION_USER views own drafts/submissions; Scrutiny officers view review intake.",
        unconfigured_handling="Returns 0 if no pending records exist.",
        api_endpoint="/api/v1/dashboard/status-counts",
    ),

    # --------------------------------------------------------------------------
    # Category B: Maturity Window (PRD-FR-070b)
    # --------------------------------------------------------------------------
    "MTR-MAT-WINDOW": MetricDefinition(
        metric_id="MTR-MAT-WINDOW",
        display_label="Maturity Window Count & Volume",
        category="MATURITY_WINDOW",
        prd_mapping="PRD-FR-070b",
        description="Instruments and total monetary volume maturing within an explicitly selectable date window [start_date, end_date].",
        calculation_rule="COUNT(instruments.id), SUM(instruments.amount) WHERE maturity_date >= start_date AND maturity_date <= end_date AND status != 'RELEASED'",
        inclusion_criteria="Instrument maturity date falls within inclusive boundaries of requested window; not released.",
        exclusion_criteria="Maturity dates outside window; cancelled or released instruments.",
        date_basis="Inclusive calendar date range on Instrument.maturity_date (Asia/Kolkata).",
        supported_filters=["start_date", "end_date", "window_days", "institution_id", "bank_name", "assigned_office"],
        authorization_scope="Enforces institution tenant boundaries; bureau roles view permitted jurisdiction.",
        unconfigured_handling="Requires valid date boundaries; rejects invalid range (start_date > end_date).",
        api_endpoint="/api/v1/dashboard/maturity-window",
    ),

    # --------------------------------------------------------------------------
    # Category C: Overdue & Escalated Work (PRD-FR-070c)
    # --------------------------------------------------------------------------
    "MTR-OVERDUE-ESCALATED": MetricDefinition(
        metric_id="MTR-OVERDUE-ESCALATED",
        display_label="Overdue & Escalated Cases",
        category="OVERDUE_ESCALATED",
        prd_mapping="PRD-FR-070c",
        description="Instruments and cases exceeding compliance action lead times or escalated to higher authority, grouped by office and assignee.",
        calculation_rule="COUNT(DISTINCT instrument_id) WHERE is_overdue = TRUE OR is_escalated = TRUE OR due_condition IN ('OVERDUE', 'ESCALATED')",
        inclusion_criteria="Lifecycle evaluations or release workflow records marked is_overdue=True or is_escalated=True.",
        exclusion_criteria="Resolved or closed cases; items within standard policy lead times.",
        date_basis="Evaluation timestamp, institution_action_due_date, officer_action_due_date.",
        supported_filters=["assigned_office", "assignee_id", "institution_id", "due_condition"],
        authorization_scope="Assignee breakdown visible only to Branch Heads, Admins, and assigned Scrutiny Officers.",
        unconfigured_handling="Reports unconfigured state if lifecycle policy has no action lead times set.",
        api_endpoint="/api/v1/dashboard/overdue-escalated",
    ),

    # --------------------------------------------------------------------------
    # Category D: Verification Queue (PRD-FR-070d)
    # --------------------------------------------------------------------------
    "MTR-VERIF-QUEUE": MetricDefinition(
        metric_id="MTR-VERIF-QUEUE",
        display_label="Verification Queue & Health",
        category="VERIFICATION_QUEUE",
        prd_mapping="PRD-FR-070d",
        description="Outstanding bank verification requests, average aging, distribution across age buckets, and source-unavailable cases.",
        calculation_rule="COUNT(verification_requests.id) WHERE status IN ('PENDING', 'REQUESTED', 'SENT'); Age = (today - created_at.date()); Source Unavailable = status IN ('SOURCE_UNAVAILABLE', 'TIMEOUT', 'FAILED')",
        inclusion_criteria="Bank verification requests currently in-flight or failed due to adapter/channel unavailability.",
        exclusion_criteria="Completed verifications (MATCH / MISMATCH confirmed with qualifying response); cancelled requests.",
        date_basis="VerificationRequest.created_at against current date.",
        supported_filters=["institution_id", "bank_name", "channel", "status"],
        authorization_scope="Officer, Branch Head, Authority, Auditor; Institution sees only own requests without confidential bank adapter telemetry.",
        unconfigured_handling="Returns zero queue count when no requests are outstanding.",
        api_endpoint="/api/v1/dashboard/verification-queue",
    ),

    # --------------------------------------------------------------------------
    # Category E: Document Completeness (PRD-FR-070e)
    # --------------------------------------------------------------------------
    "MTR-DOC-COMPLETENESS": MetricDefinition(
        metric_id="MTR-DOC-COMPLETENESS",
        display_label="Document Completeness Breakdown",
        category="DOCUMENT_COMPLETENESS",
        prd_mapping="PRD-FR-070e",
        description="Aggregate compliance of uploaded documentation: present, missing, unreadable, wrong category, and awaiting scan confirmation.",
        calculation_rule="Aggregates DocumentVersion.processing_status and ValidationFinding where category IN ('DOCUMENT_COMPLETENESS', 'DOCUMENT_INTEGRITY') against active ValidationPolicyConfig.",
        inclusion_criteria="All documents and versions associated with authorized instruments under active policy.",
        exclusion_criteria="Archived document versions; dismissed findings; instruments excluded from policy scope.",
        date_basis="Document version upload timestamps and validation execution instants.",
        supported_filters=["institution_id", "instrument_id", "category", "policy_version"],
        authorization_scope="Institution views own documents; bureau officers view assigned scope.",
        unconfigured_handling="If REQUIRED_DOCUMENT_CATEGORIES is unconfigured, returns explicit 'POLICY_UNCONFIGURED' status rather than misleading 0.",
        api_endpoint="/api/v1/dashboard/document-completeness",
    ),

    # --------------------------------------------------------------------------
    # Category F: Release Blockers (PRD-FR-070f)
    # --------------------------------------------------------------------------
    "MTR-REL-BLOCKERS": MetricDefinition(
        metric_id="MTR-REL-BLOCKERS",
        display_label="Release & Refund Blockers",
        category="RELEASE_BLOCKERS",
        prd_mapping="PRD-FR-070f",
        description="Active release and refund cases obstructed by unmet mandatory checklist items, unsatisfied trust levels, or unresolved findings.",
        calculation_rule="COUNT(release_requests.id) WHERE workflow_status NOT IN ('COMPLETED', 'CLOSED', 'CANCELLED', 'REJECTED') AND (latest_assessment.blockers_count > 0 OR latest_assessment.outcome = 'BLOCKED')",
        inclusion_criteria="Release cases with an active readiness assessment having at least one unsatisfied mandatory checklist item.",
        exclusion_criteria="Cases ready for authority approval; fully executed and closed release orders.",
        date_basis="ReadinessAssessment.evaluated_at and release request submission timestamp.",
        supported_filters=["institution_id", "case_type", "assigned_office", "policy_version"],
        authorization_scope="Institutions view own blockers; Scrutiny Officers and Competent Authorities view within scope.",
        unconfigured_handling="If checklist profile is missing or inactive, marks readiness as 'UNABLE_TO_EVALUATE' with explicit explanation.",
        api_endpoint="/api/v1/dashboard/release-blockers",
    ),

    # --------------------------------------------------------------------------
    # Category G: Month-Wise Maturity Load (PRD-FR-076)
    # --------------------------------------------------------------------------
    "MTR-MAT-LOAD": MetricDefinition(
        metric_id="MTR-MAT-LOAD",
        display_label="Month-Wise Maturity Load",
        category="MATURITY_LOAD",
        prd_mapping="PRD-FR-076",
        description="Deterministic monthly aggregation of instrument counts and total statutory deposit values maturing across calendar months.",
        calculation_rule="SELECT EXTRACT(YEAR FROM maturity_date) AS yr, EXTRACT(MONTH FROM maturity_date) AS mo, COUNT(id), SUM(amount) GROUP BY yr, mo",
        inclusion_criteria="All non-released instruments with recorded maturity dates falling in requested calendar year or 12-month span.",
        exclusion_criteria="Released instruments; synthetic projections or speculative renewals (purely historical/recorded aggregation).",
        date_basis="Instrument.maturity_date grouped by year and month.",
        supported_filters=["year", "start_month", "end_month", "institution_id", "bank_name", "assigned_office"],
        authorization_scope="Role-scoped aggregation; never reveals unauthorized tenant data in sum or count.",
        unconfigured_handling="Returns empty month series or explicit zeroes for months with no scheduled maturities.",
        api_endpoint="/api/v1/dashboard/maturity-load",
    ),

    # --------------------------------------------------------------------------
    # Category H: Operational Priority Queue (PRD-FR-075)
    # --------------------------------------------------------------------------
    "MTR-PRIORITY-QUEUE": MetricDefinition(
        metric_id="MTR-PRIORITY-QUEUE",
        display_label="Operational Priority Queue",
        category="PRIORITY_QUEUE",
        prd_mapping="PRD-FR-075",
        description="Transparent urgency-ranked queue of instruments requiring administrative attention, weighted by urgency, severity, and trust state.",
        calculation_rule="Composite Score = (UrgencyWeight * UrgencyScore) + (FindingWeight * FindingScore) + (TrustWeight * TrustScore) + (OverdueWeight * OverdueScore); weights: 35/25/20/20.",
        inclusion_criteria="Active and pending instruments requiring review, nearing maturity, or bearing open discrepancies.",
        exclusion_criteria="Formally released and closed cases; dismissed or resolved findings.",
        date_basis="Days to maturity from current date; finding detection timestamps.",
        supported_filters=["institution_id", "bank_name", "assigned_office", "min_score", "limit", "skip"],
        authorization_scope="Scoped to user jurisdiction; factor breakdown fully disclosed in response.",
        unconfigured_handling="Uses default neutral scores (50.0) with assumption flag if policy weights are unspecified.",
        api_endpoint="/api/v1/dashboard/priority-queue",
    ),
}


def get_metric_definition(metric_id: str) -> Optional[MetricDefinition]:
    """Retrieve metric definition by ID."""
    return METRIC_DICTIONARY.get(metric_id)


def list_metric_definitions(category: Optional[str] = None) -> List[MetricDefinition]:
    """List metric definitions optionally filtered by category."""
    if category:
        return [m for m in METRIC_DICTIONARY.values() if m.category == category]
    return list(METRIC_DICTIONARY.values())
