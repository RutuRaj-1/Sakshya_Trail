"""
Audit Module - SQLAlchemy Audit Event Model
Provides tamper-evident trail for regulatory lifecycle and authentication actions.
"""
import uuid
import json
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Integer, event
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Monotonic sequence counter for append-only gap/reorder detection
    sequence_number: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    
    # Actor information
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Action and target
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    # Outcome: SUCCESS, FAILURE, DENIED, REJECTED
    outcome: Mapped[str] = mapped_column(String(20), default="SUCCESS", nullable=False)
    
    # Correlation & Network context
    request_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    # Policy version reference at the time of action
    policy_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Structured metadata (strictly sanitized; never holds credentials)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Cryptographic SHA-256 Hash Chaining (PRD-FR-092)
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    current_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    
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


# ------------------------------------------------------------------------------
# Append-Only ORM Guardrails: Reject UPDATE and DELETE mutations
# ------------------------------------------------------------------------------
@event.listens_for(AuditEvent, "before_update")
def guard_audit_update(mapper, connection, target):
    """Rejects all ORM updates to preserve append-only ledger integrity."""
    if getattr(target, "_allow_audit_migration", False):
        return
    raise PermissionError("Mutation of audit events is strictly prohibited: audit_events table is append-only.")


@event.listens_for(AuditEvent, "before_delete")
def guard_audit_delete(mapper, connection, target):
    """Rejects all ORM deletions to preserve append-only ledger integrity."""
    if getattr(target, "_allow_audit_migration", False):
        return
    raise PermissionError("Deletion of audit events is strictly prohibited: audit_events table is append-only.")

