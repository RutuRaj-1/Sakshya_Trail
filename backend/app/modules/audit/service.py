"""
Audit Module - Logging Service with Automatic Credential Sanitization
"""
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.modules.audit.models import AuditEvent
from app.core.security import sanitize_dict


def log_audit_event(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_email: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    actor_role: Optional[str] = None,
    outcome: str = "SUCCESS",
    request_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """
    Appends an immutable audit event to the log.
    Metadata is automatically sanitized to strip passwords, tokens, and secrets.
    """
    # Strict sanitization
    clean_metadata = sanitize_dict(metadata) if metadata else None
    metadata_str = json.dumps(clean_metadata) if clean_metadata else None

    event = AuditEvent(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        actor_role=actor_role,
        outcome=outcome,
        request_id=request_id,
        ip_address=ip_address,
        metadata_json=metadata_str,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
