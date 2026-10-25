"""
Module 4 — Trust, Provenance & Verification Desk
Exports models, enums, services, adapters, and routers.
"""
from app.modules.verification.enums import (
    TrustLevel,
    ProvenanceSourceType,
    VerificationChannel,
    SourceClassification,
    VerificationResult,
    VerificationRequestStatus,
    TrustAssessmentStatus,
    TrustTriggerType,
    TRACKED_INSTRUMENT_FIELDS,
    TRACKED_FIELDS_SET,
)
from app.modules.verification.models import (
    FieldProvenance,
    VerificationRequest,
    VerificationResponse,
    TrustAssessment,
    TrustTransitionHistory,
)
from app.modules.verification.provenance_service import (
    record_field_provenance,
    get_active_field_provenances,
    get_field_provenance_history,
    initialize_instrument_provenance,
)
from app.modules.verification.trust_service import (
    transition_trust_level,
    request_l1_reassessment,
    record_l2_officer_decision,
    apply_l3_bank_confirmation,
    perform_trust_downgrade,
    get_active_trust_assessments,
    get_trust_transition_history,
    compute_aggregate_trust_summary,
)
from app.modules.verification.verification_service import (
    create_verification_request,
    list_instrument_verification_requests,
    get_verification_request_by_id,
    dispatch_verification_request,
    record_manual_verification_result,
    retry_verification_request,
    cancel_verification_request,
    get_verification_response_by_id,
)
from app.modules.verification.adapters import (
    BaseVerificationAdapter,
    ManualVerificationAdapter,
    SimulatedBankAdapter,
    LiveBankVerificationAdapter,
    get_adapter_for_channel,
)
from app.modules.verification.router import router as verification_router

__all__ = [
    "TrustLevel",
    "ProvenanceSourceType",
    "VerificationChannel",
    "SourceClassification",
    "VerificationResult",
    "VerificationRequestStatus",
    "TrustAssessmentStatus",
    "TrustTriggerType",
    "TRACKED_INSTRUMENT_FIELDS",
    "TRACKED_FIELDS_SET",
    "FieldProvenance",
    "VerificationRequest",
    "VerificationResponse",
    "TrustAssessment",
    "TrustTransitionHistory",
    "record_field_provenance",
    "get_active_field_provenances",
    "get_field_provenance_history",
    "initialize_instrument_provenance",
    "transition_trust_level",
    "request_l1_reassessment",
    "record_l2_officer_decision",
    "apply_l3_bank_confirmation",
    "perform_trust_downgrade",
    "get_active_trust_assessments",
    "get_trust_transition_history",
    "compute_aggregate_trust_summary",
    "create_verification_request",
    "list_instrument_verification_requests",
    "get_verification_request_by_id",
    "dispatch_verification_request",
    "record_manual_verification_result",
    "retry_verification_request",
    "cancel_verification_request",
    "get_verification_response_by_id",
    "BaseVerificationAdapter",
    "ManualVerificationAdapter",
    "SimulatedBankAdapter",
    "LiveBankVerificationAdapter",
    "get_adapter_for_channel",
    "verification_router",
]
