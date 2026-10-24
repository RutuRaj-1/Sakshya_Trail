"""
Audit Module - API Router
Allows compliance auditors and administrators to inspect audit trails.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.modules.audit.models import AuditEvent
from app.modules.audit.schemas import AuditEventRead
from app.modules.auth.dependencies import require_roles
from app.modules.auth.models import User
from app.core.security import ROLE_SYSTEM_ADMIN, ROLE_AUDITOR

router = APIRouter(prefix="/audit", tags=["Audit Trails"])


@router.get("", response_model=List[AuditEventRead])
@router.get("/events", response_model=List[AuditEventRead])
def list_audit_events(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_AUDITOR])),
    db: Session = Depends(get_db),
):
    """List tamper-evident audit history. Strictly restricted to SYSTEM_ADMIN and AUDITOR."""
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if entity_type:
        stmt = stmt.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditEvent.entity_id == entity_id)
    results = db.scalars(stmt.limit(100)).all()
    return results
