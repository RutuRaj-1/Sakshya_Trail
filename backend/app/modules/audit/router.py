"""
Audit Module - API Router
Provides authenticated, role-scoped endpoints for audit exploration,
event inspection, and replayable SHA-256 cryptographic chain verification.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user, require_roles
from app.modules.auth.models import User
from app.core.security import (
    ROLE_SYSTEM_ADMIN,
    ROLE_AUDITOR,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
)
from app.modules.audit.schemas import (
    AuditEventRead,
    AuditChainVerificationResponse,
)

router = APIRouter(prefix="/audit", tags=["Audit Trails"])


@router.get("/integrity", response_model=AuditChainVerificationResponse)
@router.post("/verify", response_model=AuditChainVerificationResponse)
def verify_audit_integrity(
    sample_size: Optional[int] = Query(None, ge=1, le=5000, description="Optional sample size (None for full ledger scan)"),
    start_sequence: int = Query(1, ge=1, description="Start sequence number"),
    current_user: User = Depends(require_roles([ROLE_SYSTEM_ADMIN, ROLE_AUDITOR, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY])),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Replays and cryptographically verifies the SHA-256 audit event chain (PRD-FR-093).
    Verifies monotonic sequence continuity, block hash linking, and canonical payload integrity.
    Identifies the earliest detected inconsistency if any.
    """
    from app.modules.dashboard.audit_query_service import AuditQueryService
    return AuditQueryService.verify_audit_log_integrity(
        db=db,
        current_user=current_user,
        sample_size=sample_size,
        start_sequence=start_sequence,
    )


@router.get("/events")
@router.get("")
def list_audit_events(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    action: Optional[str] = Query(None, description="Filter by action code"),
    outcome: Optional[str] = Query(None, description="Filter by outcome (SUCCESS, FAILURE, DENIED)"),
    actor_email: Optional[str] = Query(None, description="Filter by actor email"),
    actor_role: Optional[str] = Query(None, description="Filter by actor role"),
    date_from: Optional[str] = Query(None, description="ISO date filter (start)"),
    date_to: Optional[str] = Query(None, description="ISO date filter (end)"),
    search: Optional[str] = Query(None, description="Search term matching ID, action, actor, or metadata"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Lists audit events with multi-attribute filtering, search, and row-level tenant scoping.
    Auditors and internal officers inspect administrative trails; institution users are scoped to their institution.
    """
    from app.modules.dashboard.audit_query_service import AuditQueryService
    return AuditQueryService.query_audit_events(
        db=db,
        current_user=current_user,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        outcome=outcome,
        actor_email=actor_email,
        actor_role=actor_role,
        date_from=date_from,
        date_to=date_to,
        search_query=search,
        skip=skip,
        limit=limit,
    )


@router.get("/events/{event_id}")
def get_audit_event_detail(
    event_id: str = Path(..., description="Target audit event UUID"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves full recorded details and cryptographic hashes for a single audit event."""
    from app.modules.dashboard.audit_query_service import AuditQueryService
    return AuditQueryService.get_audit_event_detail(
        db=db,
        current_user=current_user,
        event_id=event_id,
    )
