"""
Module 4 — Trust, Provenance & Verification Desk
Enumerations and Constants
"""
from enum import Enum
from typing import Set, List


class TrustLevel(str, Enum):
    """
    Four-tier evidentiary trust hierarchy for statutory instruments.
    Maintains strict separation between administrative status and evidentiary certainty.
    """
    L0_DECLARED = "L0_DECLARED"
    L1_DOCUMENT_CONSISTENT = "L1_DOCUMENT_CONSISTENT"
    L2_OFFICER_VERIFIED = "L2_OFFICER_VERIFIED"
    L3_BANK_CONFIRMED = "L3_BANK_CONFIRMED"


class ProvenanceSourceType(str, Enum):
    """
    Field-level provenance source taxonomy.
    Distinguishes entered, extracted, documentary, and independently confirmed values.
    """
    INSTITUTION_ENTERED = "INSTITUTION_ENTERED"
    OFFICER_ENTERED = "OFFICER_ENTERED"
    IMPORTED = "IMPORTED"
    OCR_EXTRACTED = "OCR_EXTRACTED"
    VISION_LLM_EXTRACTED = "VISION_LLM_EXTRACTED"
    DOCUMENT_EVIDENCE = "DOCUMENT_EVIDENCE"
    MANUAL_BANK_EVIDENCE = "MANUAL_BANK_EVIDENCE"
    AUTHORIZED_BANK_RESPONSE = "AUTHORIZED_BANK_RESPONSE"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"


class VerificationChannel(str, Enum):
    """
    Verification transmission channel / mode.
    Simulated responses must NEVER promote trust level to L3.
    """
    SIMULATED = "SIMULATED"
    SFTP_BATCH = "SFTP_BATCH"
    DIRECT_API = "DIRECT_API"
    AUTHORIZED_MANUAL = "AUTHORIZED_MANUAL"


class VerificationResult(str, Enum):
    """
    Comparison outcome of verification against bank or independent source.
    """
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    INDETERMINATE = "INDETERMINATE"


class VerificationRequestStatus(str, Enum):
    """
    Lifecycle status of a verification request.
    """
    REQUESTED = "REQUESTED"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class TrustAssessmentStatus(str, Enum):
    """
    Lifecycle status of an individual trust assessment.
    """
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"


class TrustTriggerType(str, Enum):
    """
    Trigger source for trust transitions.
    """
    INITIAL_REGISTRATION = "INITIAL_REGISTRATION"
    DOCUMENT_VALIDATION = "DOCUMENT_VALIDATION"
    OFFICER_REVIEW = "OFFICER_REVIEW"
    BANK_CONFIRMATION = "BANK_CONFIRMATION"
    EVIDENCE_CORRECTION = "EVIDENCE_CORRECTION"
    REASSESSMENT_DOWNGRADE = "REASSESSMENT_DOWNGRADE"


# Explicit allow-list for tracked instrument fields under field provenance
TRACKED_INSTRUMENT_FIELDS: List[str] = [
    "amount",
    "currency",
    "issue_date",
    "maturity_date",
    "bank_name",
    "branch",
    "reference_number",
    "lien_marked",
    "lien_holder",
    "joint_with_aicte",
    "instrument_type",
]

TRACKED_FIELDS_SET: Set[str] = set(TRACKED_INSTRUMENT_FIELDS)
