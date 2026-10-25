"""
Module 6 — Release / Refund Case Management
Workflow enums, requirement types, and status state machines.
"""
from enum import Enum


class ReleaseRequestType(str, Enum):
    """Core administrative intent of the case."""
    RELEASE = "RELEASE"          # Standard maturity or substitution release of FDR
    DISCHARGE = "DISCHARGE"      # Formal discharge of lien / guarantee obligation
    REFUND = "REFUND"            # Return of surplus or erroneous security deposit


class ReleaseCaseType(str, Enum):
    """Specific administrative scenario under the request type."""
    STANDARD_MATURITY_RELEASE = "STANDARD_MATURITY_RELEASE"
    SUBSTITUTION_RELEASE = "SUBSTITUTION_RELEASE"
    PROGRAM_CLOSURE_DISCHARGE = "PROGRAM_CLOSURE_DISCHARGE"
    EXCESS_DEPOSIT_REFUND = "EXCESS_DEPOSIT_REFUND"
    SPECIAL_DISPENSATION = "SPECIAL_DISPENSATION"


class ReleaseWorkflowStatus(str, Enum):
    """
    Strict lifecycle state machine for release / refund cases.
    Authorization, approval, release-order recording, and completion are distinct states.
    """
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RETURNED_FOR_CORRECTION = "RETURNED_FOR_CORRECTION"
    READY_FOR_AUTHORITY = "READY_FOR_AUTHORITY"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RELEASE_ORDER_RECORDED = "RELEASE_ORDER_RECORDED"
    BANK_SIDE_ACTION_PENDING = "BANK_SIDE_ACTION_PENDING"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ChecklistProfileStatus(str, Enum):
    """Versioned checklist policy lifecycle."""
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    INACTIVE = "INACTIVE"


class ChecklistRequirementType(str, Enum):
    """Category of operational or evidence check."""
    DOCUMENT_COMPLETENESS = "DOCUMENT_COMPLETENESS"  # Module 2
    TRUST_LEVEL = "TRUST_LEVEL"                      # Module 4
    VALIDATION_FINDINGS = "VALIDATION_FINDINGS"      # Module 3
    LIFECYCLE_MATURITY = "LIFECYCLE_MATURITY"        # Module 5
    LINEAGE_CONTINUITY = "LINEAGE_CONTINUITY"        # Module 5
    AFFIDAVIT_OR_NOC = "AFFIDAVIT_OR_NOC"            # Module 2 / Administrative
    MANUAL_CLEARANCE = "MANUAL_CLEARANCE"            # Officer manual review


class ChecklistEvaluationType(str, Enum):
    """Method by which a checklist item is evaluated."""
    AUTOMATED = "AUTOMATED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    HYBRID = "HYBRID"


class CheckResultStatus(str, Enum):
    """Status of an individual checklist item check."""
    SATISFIED = "SATISFIED"
    UNSATISFIED = "UNSATISFIED"
    PENDING = "PENDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNABLE_TO_EVALUATE = "UNABLE_TO_EVALUATE"


class ReadinessAssessmentOutcome(str, Enum):
    """Overall outcome of a point-in-time readiness assessment."""
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    BLOCKED = "BLOCKED"
    PENDING_REVIEW = "PENDING_REVIEW"
    INCOMPLETE = "INCOMPLETE"


class ReleaseDecisionType(str, Enum):
    """Action recorded in decision history."""
    SUBMIT = "SUBMIT"
    RETURN_FOR_CORRECTION = "RETURN_FOR_CORRECTION"
    RECOMMEND_FOR_AUTHORITY = "RECOMMEND_FOR_AUTHORITY"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CANCEL = "CANCEL"


class ReleaseOrderStatus(str, Enum):
    """State of an official administrative release letter/order."""
    DRAFT_RECORDED = "DRAFT_RECORDED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


class BankActionStatus(str, Enum):
    """State of post-approval bank-side lien release / fund transfer."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    DISPUTED = "DISPUTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
