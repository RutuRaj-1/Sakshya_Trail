"""
Module 5 — Lifecycle Orchestration & Renewal
Enumerations and Constants
"""
from enum import Enum


class PolicyStatus(str, Enum):
    """
    Lifecycle and monitoring policy status.
    Ensures policies follow formal creation, approval, and activation workflows.
    """
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUPERSEDED = "SUPERSEDED"


class MaturityStage(str, Enum):
    """
    Time-sensitive maturity / validity condition derived at date-boundary evaluation.
    Separate from administrative workflow status (REGISTERED, DRAFT, etc.).
    """
    ACTIVE = "ACTIVE"
    MATURING_SOON = "MATURING_SOON"
    CRITICAL_WINDOW = "CRITICAL_WINDOW"
    MATURED = "MATURED"
    EXPIRED = "EXPIRED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


class DueCondition(str, Enum):
    """
    Action requirement status derived from configured policy lead times.
    """
    NORMAL = "NORMAL"
    REMINDER_DUE = "REMINDER_DUE"
    INSTITUTION_ACTION_DUE = "INSTITUTION_ACTION_DUE"
    OFFICER_ACTION_DUE = "OFFICER_ACTION_DUE"
    OVERDUE = "OVERDUE"
    ESCALATED = "ESCALATED"


class RenewalComparisonMethod(str, Enum):
    """
    Defines which instrument validity dates are compared to evaluate continuity.
    """
    ISSUE_DATE_TO_MATURITY_DATE = "ISSUE_DATE_TO_MATURITY_DATE"
    PROVISIONAL_ISSUE_DATE = "PROVISIONAL_ISSUE_DATE"
    STRICT_CONTINUOUS_TERM = "STRICT_CONTINUOUS_TERM"


class LineageRelationshipType(str, Enum):
    """
    Classification of relationship between predecessor and successor instruments.
    """
    RENEWAL = "RENEWAL"
    REPLACEMENT = "REPLACEMENT"
    SPLIT_RENEWAL = "SPLIT_RENEWAL"


class LineageRelationshipStatus(str, Enum):
    """
    Status of the lineage relationship link.
    """
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    CANCELLED = "CANCELLED"


class ContinuityIndicator(str, Enum):
    """
    Assessment result of validity continuity between predecessor and successor.
    """
    CONTINUOUS = "CONTINUOUS"
    GAP_DETECTED = "GAP_DETECTED"
    OVERLAP_DETECTED = "OVERLAP_DETECTED"
    UNKNOWN = "UNKNOWN"
