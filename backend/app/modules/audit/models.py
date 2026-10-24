"""
Audit Module - SQLAlchemy Audit Event Model
Provides tamper-evident trail for regulatory lifecycle and authentication actions.
"""
import uuid
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Actor information
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Action and target
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    # Outcome: SUCCESS or FAILURE
    outcome: Mapped[str] = mapped_column(String(20), default="SUCCESS", nullable=False)
    
    # Correlation & Network context
    request_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Structured metadata (strictly sanitized; never holds credentials)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def parsed_metadata(self) -> Dict[str, Any]:
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {"raw": self.metadata_json}
