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
    metadata_json: Optional[str] = None


class AuditEventRead(AuditEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
