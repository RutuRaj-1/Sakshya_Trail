"""
Core Domain: Authoritative Canonical Nine-Stage FDR Lifecycle Contract
Defines the authoritative stage identifiers, ordering, operational roles,
preconditions, exit conditions, endpoints, audit events, and truthful status rules
for SIH 2026 Problem Statement 26265.
"""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CanonicalStageId(str, Enum):
    STAGE_1_SUBMISSION_REGISTRATION = "STAGE_1_SUBMISSION_REGISTRATION"
    STAGE_2_DOCUMENT_EVIDENCE = "STAGE_2_DOCUMENT_EVIDENCE"
    STAGE_3_VALIDATION_DISCREPANCY = "STAGE_3_VALIDATION_DISCREPANCY"
    STAGE_4_SCRUTINY_REVIEW = "STAGE_4_SCRUTINY_REVIEW"
    STAGE_5_BANK_VERIFICATION_TRUST = "STAGE_5_BANK_VERIFICATION_TRUST"
    STAGE_6_LIFECYCLE_MONITORING = "STAGE_6_LIFECYCLE_MONITORING"
    STAGE_7_RENEWAL_LINEAGE = "STAGE_7_RENEWAL_LINEAGE"
    STAGE_8_RELEASE_READINESS = "STAGE_8_RELEASE_READINESS"
    STAGE_9_MAKER_CHECKER_CLOSURE = "STAGE_9_MAKER_CHECKER_CLOSURE"


class StageProgressState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_EXTERNAL = "AWAITING_EXTERNAL"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    ONGOING = "ONGOING"


class StageEndpoint(BaseModel):
    method: str
    path: str
    description: str
    is_privileged: bool = False
    allowed_roles: List[str] = Field(default_factory=list)


class StageContract(BaseModel):
    stage_number: int
    stage_id: CanonicalStageId
    label: str
    business_purpose: str
    frontend_destination: str
    related_modules: List[str]
    endpoints: List[StageEndpoint]
    permitted_read_roles: List[str]
    permitted_action_roles: Dict[str, List[str]]
    preconditions: List[str]
    exit_conditions: List[str]
    audit_events: List[str]
    known_limitations: List[str] = Field(default_factory=list)


ALL_SEVEN_ROLES = [
    "INSTITUTION_USER",
    "SCRUTINY_OFFICER",
    "BRANCH_HEAD",
    "COMPETENT_AUTHORITY",
    "FINANCE_OFFICER",
    "SYSTEM_ADMIN",
    "AUDITOR",
]

INTERNAL_BUREAU_ROLES = [
    "SCRUTINY_OFFICER",
    "BRANCH_HEAD",
    "COMPETENT_AUTHORITY",
    "FINANCE_OFFICER",
    "SYSTEM_ADMIN",
    "AUDITOR",
]

CANONICAL_STAGE_CONTRACTS: Dict[CanonicalStageId, StageContract] = {
    CanonicalStageId.STAGE_1_SUBMISSION_REGISTRATION: StageContract(
        stage_number=1,
        stage_id=CanonicalStageId.STAGE_1_SUBMISSION_REGISTRATION,
        label="FDR Submission & Registration",
        business_purpose="Intake and initial registration of institutional security deposit FDR certificates pledged under statutory AICTE terms.",
        frontend_destination="/instruments",
        related_modules=["Module 1: Intake & Registry"],
        endpoints=[
            StageEndpoint(
                method="GET",
                path="/api/v1/instruments",
                description="List and search registered FDR instruments with tenancy scoping",
                is_privileged=False,
                allowed_roles=ALL_SEVEN_ROLES,
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/instruments",
                description="Record initial FDR certificate metadata (institution, bank, branch, amount, dates)",
                is_privileged=True,
                allowed_roles=["INSTITUTION_USER", "SYSTEM_ADMIN"],
            ),
        ],
        permitted_read_roles=ALL_SEVEN_ROLES,
        permitted_action_roles={
            "register_fdr": ["INSTITUTION_USER", "SYSTEM_ADMIN"],
        },
        preconditions=[
            "Institution must be active and registered in bureau database.",
            "Authenticated session with institution tenancy or bureau administrative scope.",
        ],
        exit_conditions=[
            "Instrument persisted with unique reference number, amount, maturity date, and status REGISTERED or DRAFT.",
            "Initial trust level recorded as L0_DECLARED.",
        ],
        audit_events=["INSTRUMENT_REGISTERED", "NOTIFICATION_DISPATCHED"],
        known_limitations=[
            "Module 1 static expiry window (<=90d) operates independently from Module 5 dynamic policy rules until unified.",
        ],
    ),
    CanonicalStageId.STAGE_2_DOCUMENT_EVIDENCE: StageContract(
        stage_number=2,
        stage_id=CanonicalStageId.STAGE_2_DOCUMENT_EVIDENCE,
        label="Document Upload & Evidence",
        business_purpose="Upload certified FDR scan copy, calculate SHA-256 integrity hash digest, perform scan checks, and lock evidence.",
        frontend_destination="/documents",
        related_modules=["Module 2: Evidence & Documents"],
        endpoints=[
            StageEndpoint(
                method="GET",
                path="/api/v1/documents",
                description="List uploaded evidence documents with metadata and verification status",
                is_privileged=False,
                allowed_roles=ALL_SEVEN_ROLES,
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/instruments/{id}/documents",
                description="Upload evidence file, compute SHA-256 digest, and link to instrument",
                is_privileged=True,
                allowed_roles=["INSTITUTION_USER", "SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
        ],
        permitted_read_roles=ALL_SEVEN_ROLES,
        permitted_action_roles={
            "upload_evidence": ["INSTITUTION_USER", "SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
        },
        preconditions=[
            "FDR certificate record must exist in database.",
            "Uploader must be authenticated and permitted (Auditors strictly excluded).",
        ],
        exit_conditions=[
            "File stored with valid SHA-256 byte hash digest recorded in database.",
            "Scan status set to CLEAN or processing completed without security flags.",
        ],
        audit_events=["DOCUMENT_UPLOADED", "DOCUMENT_HASH_VERIFIED"],
        known_limitations=[
            "OCR text extraction is simulated in local development environments.",
        ],
    ),
    CanonicalStageId.STAGE_3_VALIDATION_DISCREPANCY: StageContract(
        stage_number=3,
        stage_id=CanonicalStageId.STAGE_3_VALIDATION_DISCREPANCY,
        label="Validation & Discrepancy Detection",
        business_purpose="Deterministic rule engine execution against statutory requirements (date ordering, minimum tenure, joint holding, lien mark) and discrepancy queue generation.",
        frontend_destination="/findings/queue?status=OPEN",
        related_modules=["Module 3: Validation Engine"],
        endpoints=[
            StageEndpoint(
                method="GET",
                path="/api/v1/findings/queue",
                description="Query active validation findings filtered by status, severity, category",
                is_privileged=True,
                allowed_roles=INTERNAL_BUREAU_ROLES,
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/instruments/{id}/validation-runs",
                description="Trigger deterministic rule engine evaluation on instrument",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
        ],
        permitted_read_roles=INTERNAL_BUREAU_ROLES,
        permitted_action_roles={
            "execute_validation": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
        },
        preconditions=[
            "FDR metadata and attached evidence must be present.",
        ],
        exit_conditions=[
            "All deterministic rules evaluated.",
            "Identified discrepancies recorded in findings queue with severity and priority scores.",
            "Trust level invariant preserved (validation does NOT mutate trust level).",
        ],
        audit_events=["VALIDATION_RULES_EVALUATED", "FINDING_GENERATED"],
        known_limitations=[],
    ),
    CanonicalStageId.STAGE_4_SCRUTINY_REVIEW: StageContract(
        stage_number=4,
        stage_id=CanonicalStageId.STAGE_4_SCRUTINY_REVIEW,
        label="Scrutiny & Review",
        business_purpose="Bureau officer examination of discrepancies, append-only scrutiny observation recording, discrepancy resolution, or returning instrument to institution for correction.",
        frontend_destination="/findings/queue?status=IN_REVIEW",
        related_modules=["Module 3: Scrutiny Desk", "Module 7: Command Center"],
        endpoints=[
            StageEndpoint(
                method="POST",
                path="/api/v1/dashboard/instruments/{id}/observations",
                description="Record append-only scrutiny observation with category and secrecy flags",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/findings/{id}/status",
                description="Transition finding status (IN_REVIEW, RESOLVED, DISMISSED)",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/instruments/{id}/return-for-correction",
                description="Return instrument to institution for deficiency correction",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
        ],
        permitted_read_roles=INTERNAL_BUREAU_ROLES,
        permitted_action_roles={
            "record_observation": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            "resolve_finding": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            "return_correction": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
        },
        preconditions=[
            "Validation run executed and findings available for examination.",
        ],
        exit_conditions=[
            "Officer records conclusive scrutiny observation, resolves all blocking findings, OR returns instrument for correction.",
        ],
        audit_events=["OBSERVATION_RECORDED", "FINDING_STATUS_TRANSITIONED", "RETURNED_FOR_CORRECTION"],
        known_limitations=[],
    ),
    CanonicalStageId.STAGE_5_BANK_VERIFICATION_TRUST: StageContract(
        stage_number=5,
        stage_id=CanonicalStageId.STAGE_5_BANK_VERIFICATION_TRUST,
        label="Bank Verification & Trust",
        business_purpose="Statutory 4-tier trust assessment (L0 Declared -> L1 Document-Consistent -> L2 Officer-Attested -> L3 Bank-Confirmed). Officer attestation and authentic external bank confirmation.",
        frontend_destination="/verification",
        related_modules=["Module 4: Trust Desk & Bank Verification"],
        endpoints=[
            StageEndpoint(
                method="GET",
                path="/api/v1/verification/instruments/{id}/trust",
                description="Retrieve trust transitions, provenance history, and current trust tier",
                is_privileged=False,
                allowed_roles=INTERNAL_BUREAU_ROLES,
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/verification/instruments/{id}/trust/l2-officer-decision",
                description="Record authorized officer L2 attestation with evidence references",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/verification/instruments/{id}/requests",
                description="Create bank verification request across supported channels",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/verification/instruments/{id}/trust/l3-bank-confirmation",
                description="Apply genuine bank-confirmed trust level (strictly rejects simulated responses)",
                is_privileged=True,
                allowed_roles=["BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
        ],
        permitted_read_roles=INTERNAL_BUREAU_ROLES,
        permitted_action_roles={
            "record_l2_attestation": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            "dispatch_verification": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            "apply_l3_confirmation": ["BRANCH_HEAD", "SYSTEM_ADMIN"],
        },
        preconditions=[
            "Scrutiny completed without unresolved discrepancy findings.",
        ],
        exit_conditions=[
            "L2 officer attestation successfully recorded, OR authentic L3 bank confirmation applied.",
            "Simulated bank responses cannot claim L3 genuine confirmation (statutory guardrail).",
        ],
        audit_events=["L2_OFFICER_ATTESTED", "VERIFICATION_REQUEST_DISPATCHED", "L3_BANK_CONFIRMED"],
        known_limitations=[
            "SFMS live bank gateway operates in simulated mode for sandboxed testing.",
        ],
    ),
    CanonicalStageId.STAGE_6_LIFECYCLE_MONITORING: StageContract(
        stage_number=6,
        stage_id=CanonicalStageId.STAGE_6_LIFECYCLE_MONITORING,
        label="Lifecycle Monitoring",
        business_purpose="Longitudinal calendar maturity surveillance, multi-tier automated notification intervals (30d, 60d, 90d), policy compliance evaluation, and continuous deposit tenure tracking.",
        frontend_destination="/monitoring",
        related_modules=["Module 5: Lifecycle Orchestration"],
        endpoints=[
            StageEndpoint(
                method="GET",
                path="/api/v1/lifecycle/instruments/{id}/evaluation",
                description="Retrieve current maturity evaluation, window, and validity status",
                is_privileged=False,
                allowed_roles=ALL_SEVEN_ROLES,
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/lifecycle/evaluate",
                description="Evaluate maturity stage against authoritative policy clock",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/lifecycle/notifications/dispatch-due",
                description="Batch dispatch statutory maturity reminder notifications",
                is_privileged=True,
                allowed_roles=["SYSTEM_ADMIN", "SCRUTINY_OFFICER"],
            ),
        ],
        permitted_read_roles=ALL_SEVEN_ROLES,
        permitted_action_roles={
            "trigger_evaluation": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            "dispatch_reminders": ["SYSTEM_ADMIN", "SCRUTINY_OFFICER"],
        },
        preconditions=[
            "Instrument active with valid maturity date and active compliance status.",
        ],
        exit_conditions=[
            "Continuous surveillance active; automated alerts dispatched at 90d, 60d, 30d thresholds.",
            "Maturity stage evaluated as ACTIVE, APPROACHING_MATURITY, or MATURED.",
        ],
        audit_events=["LIFECYCLE_EVALUATION_COMPLETED", "REMINDER_NOTIFICATIONS_DISPATCHED"],
        known_limitations=[
            "Separate Module 1 EXPIRING_SOON filter is preserved until unified in lifecycle prompt.",
        ],
    ),
    CanonicalStageId.STAGE_7_RENEWAL_LINEAGE: StageContract(
        stage_number=7,
        stage_id=CanonicalStageId.STAGE_7_RENEWAL_LINEAGE,
        label="Renewal & Successor Lineage",
        business_purpose="Rollover and successor instrument creation, cryptographic predecessor-successor linking, continuity tenure validation, and preservation of historical lineage trees.",
        frontend_destination="/monitoring?tab=renewals",
        related_modules=["Module 5: Lineage & Renewal"],
        endpoints=[
            StageEndpoint(
                method="GET",
                path="/api/v1/lifecycle/instruments/{id}/lineage",
                description="Retrieve complete predecessor-successor lineage graph",
                is_privileged=False,
                allowed_roles=ALL_SEVEN_ROLES,
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/lifecycle/instruments/{id}/renew",
                description="Create successor renewal instrument and link to predecessor",
                is_privileged=True,
                allowed_roles=["INSTITUTION_USER", "SYSTEM_ADMIN"],
            ),
            StageEndpoint(
                method="GET",
                path="/api/v1/lifecycle/instruments/{id}/continuity",
                description="Assess tenure continuity across lineage tree",
                is_privileged=False,
                allowed_roles=ALL_SEVEN_ROLES,
            ),
        ],
        permitted_read_roles=ALL_SEVEN_ROLES,
        permitted_action_roles={
            "initiate_renewal": ["INSTITUTION_USER", "SYSTEM_ADMIN"],
            "correct_lineage": ["BRANCH_HEAD", "SYSTEM_ADMIN"],
        },
        preconditions=[
            "Predecessor instrument exists and is nearing or past statutory maturity.",
        ],
        exit_conditions=[
            "Successor instrument created and active.",
            "Predecessor marked RENEWED or SUPERSEDED.",
            "Lineage record persisted with ACTIVE relationship status.",
        ],
        audit_events=["LINEAGE_LINK_ESTABLISHED", "INSTRUMENT_RENEWED"],
        known_limitations=[],
    ),
    CanonicalStageId.STAGE_8_RELEASE_READINESS: StageContract(
        stage_number=8,
        stage_id=CanonicalStageId.STAGE_8_RELEASE_READINESS,
        label="Release Readiness",
        business_purpose="Pre-discharge compliance readiness evaluation against checklist policy profiles (mandatory documents, legal hold checks, verification tier thresholds, zero blockers).",
        frontend_destination="/release?status=UNDER_REVIEW",
        related_modules=["Module 6: Release Readiness"],
        endpoints=[
            StageEndpoint(
                method="POST",
                path="/api/v1/release/requests",
                description="Initiate draft release or refund request petition",
                is_privileged=True,
                allowed_roles=["INSTITUTION_USER", "SYSTEM_ADMIN"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/release/requests/{id}/evaluate-readiness",
                description="Evaluate release gate checklist profile items and identify blockers",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/release/requests/{id}/recommend-for-authority",
                description="Officer scrutiny recommendation (requires zero mandatory blockers)",
                is_privileged=True,
                allowed_roles=["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            ),
        ],
        permitted_read_roles=ALL_SEVEN_ROLES,
        permitted_action_roles={
            "create_release_request": ["INSTITUTION_USER", "SYSTEM_ADMIN"],
            "evaluate_readiness": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
            "recommend_release": ["SCRUTINY_OFFICER", "BRANCH_HEAD", "SYSTEM_ADMIN"],
        },
        preconditions=[
            "Release request petition submitted by institution or admin.",
        ],
        exit_conditions=[
            "Readiness gate evaluated.",
            "All mandatory checklist items satisfied (outcome PASSED).",
            "Officer recommends case for Competent Authority sanction (status READY_FOR_AUTHORITY).",
        ],
        audit_events=["RELEASE_REQUEST_SUBMITTED", "READINESS_GATE_EVALUATED", "RELEASE_RECOMMENDED"],
        known_limitations=[],
    ),
    CanonicalStageId.STAGE_9_MAKER_CHECKER_CLOSURE: StageContract(
        stage_number=9,
        stage_id=CanonicalStageId.STAGE_9_MAKER_CHECKER_CLOSURE,
        label="Maker-Checker Decision & Closure",
        business_purpose="Multi-step grouped statutory closure: (9a) Competent Authority approval/rejection sanction; (9b) Finance Officer official release order recording; (9c) Bank-side execution confirmation; (9d) Settlement verification & case closure.",
        frontend_destination="/release?status=READY_FOR_AUTHORITY",
        related_modules=["Module 6: Authority & Order Management", "Module 7: Hash-Chain Ledger"],
        endpoints=[
            StageEndpoint(
                method="POST",
                path="/api/v1/release/requests/{id}/approve",
                description="Competent Authority statutory release sanction (enforces maker-checker)",
                is_privileged=True,
                allowed_roles=["COMPETENT_AUTHORITY"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/release/requests/{id}/reject",
                description="Authority rejection of release petition",
                is_privileged=True,
                allowed_roles=["COMPETENT_AUTHORITY"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/release/requests/{id}/record-order",
                description="Finance Officer records official discharge letter and bank routing",
                is_privileged=True,
                allowed_roles=["FINANCE_OFFICER"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/release/requests/{id}/confirm-bank-action",
                description="Record downstream bank disbursement/lien-removal confirmation",
                is_privileged=True,
                allowed_roles=["FINANCE_OFFICER", "BRANCH_HEAD"],
            ),
            StageEndpoint(
                method="POST",
                path="/api/v1/release/requests/{id}/close-case",
                description="Formal case closure and permanent audit ledger sealing",
                is_privileged=True,
                allowed_roles=["FINANCE_OFFICER", "BRANCH_HEAD"],
            ),
        ],
        permitted_read_roles=ALL_SEVEN_ROLES,
        permitted_action_roles={
            "statutory_approval": ["COMPETENT_AUTHORITY"],
            "statutory_rejection": ["COMPETENT_AUTHORITY"],
            "record_release_order": ["FINANCE_OFFICER"],
            "confirm_bank_action": ["FINANCE_OFFICER", "BRANCH_HEAD"],
            "close_case": ["FINANCE_OFFICER", "BRANCH_HEAD"],
        },
        preconditions=[
            "Case in status READY_FOR_AUTHORITY with zero mandatory readiness blockers.",
        ],
        exit_conditions=[
            "Competent Authority approves petition (maker-checker verified).",
            "Finance Officer records official release order (status RELEASE_ORDER_RECORDED).",
            "Downstream bank action confirmed (status COMPLETED).",
            "Case formally closed (status CLOSED) and permanently sealed in SHA-256 audit ledger.",
        ],
        audit_events=[
            "RELEASE_APPROVED",
            "RELEASE_ORDER_RECORDED",
            "BANK_ACTION_CONFIRMED",
            "RELEASE_CASE_CLOSED",
        ],
        known_limitations=[
            "Bank UTR confirmation requires manual officer confirmation in absence of direct SFMS webhook.",
        ],
    ),
}


def get_canonical_stage_contract(stage_id: CanonicalStageId) -> Optional[StageContract]:
    return CANONICAL_STAGE_CONTRACTS.get(stage_id)


def list_canonical_stages() -> List[StageContract]:
    return [CANONICAL_STAGE_CONTRACTS[sid] for sid in sorted(CANONICAL_STAGE_CONTRACTS.keys(), key=lambda k: CANONICAL_STAGE_CONTRACTS[k].stage_number)]
