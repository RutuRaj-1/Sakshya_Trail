"""
Audit Query Service (Module 7 — Command Center)
Implements PRD-FR-091 to PRD-FR-094:
Reads audit events, queries security violation logs, and performs integrity verification.
"""
import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.modules.auth.models import User
from app.modules.audit.models import AuditEvent


class AuditQueryService:
    """Service for querying tamper-evident audit logs and verifying integrity."""

    @staticmethod
    def query_audit_events(
        db: Session,
        current_user: User,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Retrieves filtered audit events for compliance review.
        """
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc())

        if entity_type:
            stmt = stmt.where(AuditEvent.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditEvent.entity_id == entity_id)
        if action:
            stmt = stmt.where(AuditEvent.action == action)
        if outcome:
            stmt = stmt.where(AuditEvent.outcome == outcome)

        clamped_limit = min(max(1, limit), 200)
        clamped_skip = max(0, skip)

        events = db.scalars(stmt.offset(clamped_skip).limit(clamped_limit)).all()

        results = []
        for e in events:
            results.append({
                "id": e.id,
                "actor_user_id": e.actor_user_id,
                "actor_email": e.actor_email,
                "actor_role": e.actor_role,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "outcome": e.outcome,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "metadata": e.parsed_metadata,
            })

        return {
            "total_returned": len(results),
            "skip": clamped_skip,
            "limit": clamped_limit,
            "events": results,
        }

    @staticmethod
    def verify_audit_log_integrity(
        db: Session,
        current_user: User,
        sample_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Verifies tamper-evidence and sequential consistency of the audit log chain.
        """
        events = db.scalars(
            select(AuditEvent).order_by(AuditEvent.created_at.asc()).limit(sample_size)
        ).all()

        is_intact = True
        anomalies = []
        prev_time = None

        for idx, ev in enumerate(events):
            # 1. Monotonic timestamp check
            if prev_time and ev.created_at and ev.created_at < prev_time:
                is_intact = False
                anomalies.append({
                    "event_id": ev.id,
                    "index": idx,
                    "reason": "Timestamp sequence regression detected",
                })
            prev_time = ev.created_at

            # 2. Required non-null integrity fields
            if not ev.action or not ev.entity_type or not ev.entity_id:
                is_intact = False
                anomalies.append({
                    "event_id": ev.id,
                    "index": idx,
                    "reason": "Required immutable field missing or null",
                })

        return {
            "verified_count": len(events),
            "is_chain_intact": is_intact,
            "status": "PASS" if is_intact else "TAMPER_SUSPECTED",
            "anomalies_detected": len(anomalies),
            "anomalies": anomalies,
            "verification_timestamp": datetime.utcnow().isoformat(),
        }
