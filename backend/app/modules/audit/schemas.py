"""
Audit Module - Pydantic Schemas
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AuditEventBase(BaseModel):
    action: str = Field(..., description="Action performed (e.g. AUTH_LOGIN, USER_PROVISIONED)")
    entity_type: str = Field(..., description="Target entity type")
    entity_id: str = Field(..., description="Target entity identifier")
    outcome: str = "SUCCESS"
    actor_user_id: Optional[str] = None
    actor_email: Optional[str] = None
    actor_role: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    policy_version: Optional[str] = None
    metadata_json: Optional[str] = None


class AuditEventRead(AuditEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence_number: Optional[int] = None
    previous_hash: Optional[str] = None
    current_hash: Optional[str] = None
    created_at: datetime
    parsed_metadata: Optional[Dict[str, Any]] = None


class AuditInconsistencyDetail(BaseModel):
    sequence_number: Optional[int] = None
    event_id: Optional[str] = None
    failure_type: str
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    safe_explanation: str


class AuditChainVerificationResponse(BaseModel):
    status: str
    is_chain_intact: bool
    total_events_in_scope: int
    verified_count: int
    latest_sequence_number: Optional[int] = None
    chain_head_hash: Optional[str] = None
    first_inconsistency: Optional[AuditInconsistencyDetail] = None
    verification_timestamp: str
    verification_scope_description: str

