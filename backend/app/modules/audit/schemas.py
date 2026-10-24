"""
Audit Module - Pydantic Schemas
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AuditEventBase(BaseModel):
    entity_type: str = Field(..., description="Target model (e.g. instrument, institution)")
    entity_id: str = Field(..., description="Target entity ID")
    action: str = Field(..., description="Lifecycle action (e.g. SUBMISSION, SCRUTINY, RENEWAL)")
    actor_email: str
    actor_role: str
    details: Optional[str] = None
    ip_address: Optional[str] = None


class AuditEventCreate(AuditEventBase):
    pass


class AuditEventRead(AuditEventBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
