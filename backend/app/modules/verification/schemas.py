"""
Module 4 — Trust, Provenance & Verification Desk
Pydantic Schemas for Requests and Responses
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class FieldProvenanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    field_name: str
    recorded_value: str
    source_type: str
    source_actor_id: Optional[str] = None
    source_service_id: Optional[str] = None
    source_timestamp: datetime
    evidence_reference: Optional[str] = None
    related_document_id: Optional[str] = None
    related_document_version_id: Optional[str] = None
    related_validation_run_id: Optional[str] = None
    prior_provenance_id: Optional[str] = None
    is_active: bool
    created_at: datetime


class RecordFieldProvenanceRequest(BaseModel):
    field_name: str
    value: Any
    source_type: str
    evidence_reference: Optional[str] = None
    related_document_id: Optional[str] = None
    related_document_version_id: Optional[str] = None


class TrustAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    field_name: Optional[str] = None
    trust_level: str
    supporting_evidence_references_json: Optional[str] = None
    supporting_document_version_id: Optional[str] = None
    related_verification_response_id: Optional[str] = None
    assessing_user_id: Optional[str] = None
    assessing_service: Optional[str] = None
    reason: str
    assessment_timestamp: datetime
    trust_rule_version: int
    status: str
    is_downgrade: bool
    created_at: datetime


class TrustTransitionRequest(BaseModel):
    target_trust_level: str
    reason: str
    field_name: Optional[str] = None
    supporting_document_version_id: Optional[str] = None
    related_verification_response_id: Optional[str] = None
    evidence_references: Optional[List[str]] = None


class TrustTransitionHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    field_name: Optional[str] = None
    prior_trust_level: str
    new_trust_level: str
    actor_user_id: Optional[str] = None
    actor_service: Optional[str] = None
    timestamp: datetime
    reason: str
    evidence_references_json: Optional[str] = None
    trigger_type: str
    outcome: str
    is_downgrade: bool


class VerificationResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    request_code: Optional[str] = None
    instrument_id: str
    channel: str
    source_classification: str
    source_identifier: Optional[str] = None
    result: str
    bank_reference_number: Optional[str] = None
    bank_values_json: Optional[str] = None
    field_comparisons_json: Optional[str] = None
    is_simulated: bool
    responded_at: datetime
    received_at: datetime
    notes: Optional[str] = None
    created_at: datetime


class VerificationRequestCreate(BaseModel):
    channel: str = Field("SIMULATED", description="Verification channel: SIMULATED, MANUAL, LIVE_BANK_API, SFTP_BATCH")
    requested_fields: Optional[List[str]] = Field(None, description="Subset of fields to verify; defaults to all tracked")
    correlation_id: Optional[str] = None
    notes: Optional[str] = None


class VerificationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    reference_code: str
    channel: str
    status: str
    requested_fields_json: Optional[str] = None
    attempt_count: int
    last_attempt_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    error_details: Optional[str] = None
    closed_at: Optional[datetime] = None
    closed_reason: Optional[str] = None
    created_at: datetime
    responses: Optional[List[VerificationResponseOut]] = None


class VerificationDispatchAction(BaseModel):
    scenario: Optional[str] = Field("MATCH", description="Optional simulation scenario: MATCH, MISMATCH, TIMEOUT, SOURCE_UNAVAILABLE, INCONCLUSIVE")


class ManualVerificationRecordRequest(BaseModel):
    external_reference: str = Field(..., description="External bank correspondence/letter reference number")
    communication_date: datetime = Field(..., description="Date and time of external communication")
    result: str = Field("MATCH", description="Outcome: MATCH, MISMATCH, INCONCLUSIVE")
    reason: str = Field(..., description="Mandatory officer review reason and justification")
    evidence_document_version_id: Optional[str] = Field(None, description="Module 2 document version reference")
    bank_values: Optional[Dict[str, Any]] = Field(None, description="Values confirmed by the bank")


class VerificationRetryRequest(BaseModel):
    scenario: Optional[str] = Field(None, description="Optional retry scenario for simulated adapter")


class VerificationCancelRequest(BaseModel):
    reason: str = Field(..., description="Mandatory reason for cancelling or closing the verification request")
