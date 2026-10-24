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


class VerificationRequestCreate(BaseModel):
    instrument_id: str
    channel: str
    notes: Optional[str] = None


class VerificationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    reference_code: str
    channel: str
    status: str
    created_at: datetime


class VerificationResponseCreate(BaseModel):
    request_id: str
    channel: str
    result: str
    is_simulated: bool
    idempotency_key: str
    bank_reference_number: Optional[str] = None
    bank_values: Optional[Dict[str, Any]] = None
    evidence_document_id: Optional[str] = None
    evidence_document_version_id: Optional[str] = None
    notes: Optional[str] = None


class VerificationResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    instrument_id: str
    channel: str
    result: str
    bank_reference_number: Optional[str] = None
    is_simulated: bool
    responded_at: datetime
