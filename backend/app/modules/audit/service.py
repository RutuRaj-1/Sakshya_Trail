"""
Audit Module - Service Helper
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.modules.audit.models import AuditEvent


def log_audit_event(
    db: Session,
    entity_type: str,
    entity_id: str,
    action: str,
    actor_email: str,
    actor_role: str,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditEvent:
    """Appends an immutable audit event to the log."""
    event = AuditEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_email=actor_email,
        actor_role=actor_role,
        details=details,
        ip_address=ip_address,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
