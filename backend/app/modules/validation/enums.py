"""
Module 3 — Validation, Discrepancy & Explainable Intelligence
Enums: Rule outcome, finding status, severity, category, and type definitions.

Design notes
------------
* RuleOutcome describes what a single rule execution produced.
* FindingStatus describes the lifecycle of a persisted discrepancy / finding record.
* These are intentionally distinct from:
    - Instrument administrative status  (Instrument.status)
    - Document scan/processing status   (DocumentVersion.processing_status)
    - FDR trust level                   (Instrument.trust_level L0–L3)
    - Release / refund authorization status (future Module 6)
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Rule execution outcome
# ---------------------------------------------------------------------------

class RuleOutcome(str, Enum):
    """
    Result produced by executing a single validation rule against an instrument.

    PASS
        All checks passed; no discrepancy detected.
    FAIL
        A deterministic check failed; a finding should be persisted.
    WARNING
        A heuristic or advisory check produced a concern that requires human review.
        Wording on findings MUST include 'Advisory — human review required'.
    NOT_APPLICABLE
        The rule is not relevant to this instrument or configuration
        (e.g. wrong instrument type, excluded by scope filter).
    UNABLE_TO_EVALUATE
        Inputs required by this rule are missing or the policy configuration for this
        institution / case has not been set up. This is NOT the same as a failure —
        it signals that a human must configure the system or supply evidence before
        a conclusion can be reached.
    """
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNABLE_TO_EVALUATE = "UNABLE_TO_EVALUATE"


# ---------------------------------------------------------------------------
# Finding / discrepancy lifecycle status
# ---------------------------------------------------------------------------

class FindingStatus(str, Enum):
    """
    Lifecycle states of a persisted discrepancy (finding) record.

    OPEN
        Newly detected; awaiting review.
    IN_REVIEW
        A reviewer has acknowledged and is actively examining the finding.
    DISMISSED
        A human reviewer determined the finding is not actionable
        (e.g. known data entry artefact, exemption granted). Reason must be recorded.
    RESOLVED
        The underlying issue has been corrected and the finding no longer fires
        on re-evaluation.
    SUPERSEDED
        A later finding (newer rule version or updated evidence) replaced this record.
        Historical record is preserved for auditability.
    """
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"
    SUPERSEDED = "SUPERSEDED"

    @classmethod
    def terminal_statuses(cls):
        """Statuses from which a finding cannot transition further."""
        return {cls.DISMISSED, cls.SUPERSEDED}

    @classmethod
    def resolvable_statuses(cls):
        """Statuses from which a finding can be moved to RESOLVED."""
        return {cls.OPEN, cls.IN_REVIEW}


# ---------------------------------------------------------------------------
# Rule / finding severity
# ---------------------------------------------------------------------------

class RuleSeverity(str, Enum):
    """
    Review priority / urgency attached to a rule and its findings.

    CRITICAL
        Fundamental data integrity issue (e.g. reference number missing entirely).
    HIGH
        Significant discrepancy that must be resolved before trust-level promotion.
    MEDIUM
        Notable inconsistency requiring investigation but not a blocker by itself.
    LOW
        Minor advisory observation; informational for scrutiny staff.
    INFO
        Purely informational; no action required unless escalated by a reviewer.
    """
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# ---------------------------------------------------------------------------
# Rule type
# ---------------------------------------------------------------------------

class RuleType(str, Enum):
    """
    Classification of how a rule produces its outcome.

    DETERMINISTIC
        Logical / mathematical check with a definitive outcome for given inputs.
        Findings are labelled 'Deterministic'.
    HEURISTIC
        Statistical or heuristic check; outcome is advisory, not conclusive.
        Findings MUST carry the label 'Advisory — human review required'.
    """
    DETERMINISTIC = "DETERMINISTIC"
    HEURISTIC = "HEURISTIC"


# ---------------------------------------------------------------------------
# Finding category
# ---------------------------------------------------------------------------

class FindingCategory(str, Enum):
    """
    High-level grouping of the discrepancy type for filtering and reporting.
    """
    DATE_CONSISTENCY = "DATE_CONSISTENCY"
    AMOUNT_CONSISTENCY = "AMOUNT_CONSISTENCY"
    REFERENCE_INTEGRITY = "REFERENCE_INTEGRITY"
    DOCUMENT_COMPLETENESS = "DOCUMENT_COMPLETENESS"
    LIEN_VALIDITY = "LIEN_VALIDITY"
    CROSS_FIELD_CONSISTENCY = "CROSS_FIELD_CONSISTENCY"
    POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE"
    POLICY_COMPLIANCE = "POLICY_COMPLIANCE"
    INSTITUTION_ELIGIBILITY = "INSTITUTION_ELIGIBILITY"
    CROSS_SOURCE_RECONCILIATION = "CROSS_SOURCE_RECONCILIATION"
    DOCUMENT_INTEGRITY = "DOCUMENT_INTEGRITY"
    ADVISORY = "ADVISORY"
    OTHER = "OTHER"
