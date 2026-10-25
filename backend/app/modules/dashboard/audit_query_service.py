"""
Audit Query & Integrity Verification Service (Module 7 — Command Center)
Implements PRD-FR-091, PRD-FR-092, PRD-FR-093, and PRD-FR-094:
- Filtered audit trail queries with row-level tenant authorization
- Cryptographic SHA-256 hash-chain verification and replay
- Tamper detection identifying earliest inconsistent sequence and event ID
- Database-level append-only guardrails and verification logging
"""
import hashlib
import json
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func, or_

if TYPE_CHECKING:
    from app.modules.auth.models import User
from app.modules.audit.models import AuditEvent
from app.modules.audit.service import (
    compute_canonical_event_hash,
    log_audit_event,
    GENESIS_HASH,
)
from app.modules.instruments.models import Instrument
from app.core.security import (
    ROLE_INSTITUTION_USER,
    ROLE_AUDITOR,
    ROLE_SYSTEM_ADMIN,
    ROLE_BRANCH_HEAD,
    ROLE_COMPETENT_AUTHORITY,
)
from app.common.exceptions import AppException


class AuditQueryService:
    """Service for querying tamper-evident audit logs and verifying cryptographic integrity."""

    @staticmethod
    def query_audit_events(
        db: Session,
        current_user: User,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Optional[str] = None,
        actor_email: Optional[str] = None,
        actor_role: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_query: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Retrieves filtered audit events for compliance review.
        Applies tenant-scoped authorization: INSTITUTION_USER can only see events
        relating to instruments in their assigned institution or their own actions.
        """
        stmt = select(AuditEvent)

        # Multi-Tenant Scoping (PRD-FR-090)
        if current_user.role == ROLE_INSTITUTION_USER:
            if not current_user.institution_id:
                return {"total_count": 0, "skip": skip, "limit": limit, "events": []}

            # Scope to institution's instrument IDs or actor's own actions
            inst_ids = db.scalars(
                select(Instrument.id).where(Instrument.institution_id == current_user.institution_id)
            ).all()

            stmt = stmt.where(
                or_(
                    AuditEvent.actor_user_id == current_user.id,
                    AuditEvent.entity_id == current_user.institution_id,
                    AuditEvent.entity_id.in_(inst_ids) if inst_ids else False,
                )
            )

        # Attribute Filters
        if entity_type:
            stmt = stmt.where(AuditEvent.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditEvent.entity_id == entity_id)
        if action:
            stmt = stmt.where(AuditEvent.action == action)
        if outcome:
            stmt = stmt.where(AuditEvent.outcome == outcome)
        if actor_email:
            stmt = stmt.where(AuditEvent.actor_email.ilike(f"%{actor_email}%"))
        if actor_role:
            stmt = stmt.where(AuditEvent.actor_role == actor_role)
        if date_from:
            try:
                df = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
                stmt = stmt.where(AuditEvent.created_at >= df)
            except Exception:
                pass
        if date_to:
            try:
                dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
                stmt = stmt.where(AuditEvent.created_at <= dt)
            except Exception:
                pass
        if search_query:
            q = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    AuditEvent.id.ilike(q),
                    AuditEvent.entity_id.ilike(q),
                    AuditEvent.action.ilike(q),
                    AuditEvent.actor_email.ilike(q),
                    AuditEvent.metadata_json.ilike(q),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = db.scalar(count_stmt) or 0

        # Order and paginate
        clamped_limit = min(max(1, limit), 200)
        clamped_skip = max(0, skip)
        events = db.scalars(
            stmt.order_by(AuditEvent.sequence_number.desc().nullslast(), AuditEvent.created_at.desc())
            .offset(clamped_skip)
            .limit(clamped_limit)
        ).all()

        results = []
        for e in events:
            results.append({
                "id": e.id,
                "sequence_number": e.sequence_number,
                "previous_hash": e.previous_hash,
                "current_hash": e.current_hash,
                "actor_user_id": e.actor_user_id,
                "actor_email": e.actor_email,
                "actor_role": e.actor_role,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "outcome": e.outcome,
                "policy_version": e.policy_version,
                "request_id": e.request_id,
                "ip_address": e.ip_address,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "metadata": e.parsed_metadata,
            })

        has_more = (clamped_skip + len(results)) < total_count
        return {
            "total_count": total_count,
            "total": total_count,
            "skip": clamped_skip,
            "limit": clamped_limit,
            "has_more": has_more,
            "events": results,
            "items": results,
        }

    @staticmethod
    def get_audit_event_detail(
        db: Session,
        current_user: User,
        event_id: str,
    ) -> Dict[str, Any]:
        """Retrieves complete details for a single audit event."""
        ev = db.get(AuditEvent, event_id)
        if not ev:
            raise AppException("Audit event not found", status_code=404, code="RECORD_NOT_FOUND")

        # Tenant scoping
        if current_user.role == ROLE_INSTITUTION_USER:
            if not current_user.institution_id:
                raise AppException("Unauthorized audit access", status_code=403, code="UNAUTHORIZED")
            if ev.actor_user_id != current_user.id and ev.entity_id != current_user.institution_id:
                # Check instrument
                inst = db.get(Instrument, ev.entity_id)
                if not inst or inst.institution_id != current_user.institution_id:
                    raise AppException("Unauthorized audit access", status_code=403, code="UNAUTHORIZED")

        return {
            "id": ev.id,
            "sequence_number": ev.sequence_number,
            "previous_hash": ev.previous_hash,
            "current_hash": ev.current_hash,
            "action": ev.action,
            "entity_type": ev.entity_type,
            "entity_id": ev.entity_id,
            "actor_user_id": ev.actor_user_id,
            "actor_email": ev.actor_email,
            "actor_role": ev.actor_role,
            "outcome": ev.outcome,
            "policy_version": ev.policy_version,
            "request_id": ev.request_id,
            "ip_address": ev.ip_address,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
            "metadata": ev.parsed_metadata,
        }

    @staticmethod
    def verify_audit_log_integrity(
        db: Session,
        current_user: User,
        sample_size: Optional[int] = None,
        start_sequence: int = 1,
        log_verification_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Replays and cryptographically verifies the SHA-256 audit event chain (PRD-FR-093).
        Checks:
        1. Monotonic sequence continuity (detects deleted, skipped, or reordered events).
        2. Block hash linking (previous_hash matches preceding event's current_hash).
        3. Canonical payload integrity (recomputed SHA-256 matches stored current_hash).
        4. Monotonic timestamp progression.

        Stops at the FIRST detected inconsistency and reports failure diagnostics.
        """
        # Role Authorization: Strictly restricted to Auditor, Admin, and Branch Head
        allowed_roles = [ROLE_SYSTEM_ADMIN, ROLE_AUDITOR, ROLE_BRANCH_HEAD, ROLE_COMPETENT_AUTHORITY]
        if current_user.role not in allowed_roles:
            raise AppException("Audit verification restricted to authorized compliance officers", status_code=403, code="UNAUTHORIZED")

        query = (
            select(AuditEvent)
            .where(AuditEvent.sequence_number.is_not(None))
            .where(AuditEvent.sequence_number >= start_sequence)
            .order_by(AuditEvent.sequence_number.asc())
        )

        if sample_size and sample_size > 0:
            query = query.limit(sample_size)

        events: List[AuditEvent] = db.scalars(query).all()
        total_in_scope = len(events)
        now_utc = datetime.now(timezone.utc).isoformat()

        if total_in_scope == 0:
            return {
                "status": "PASS",
                "is_chain_intact": True,
                "total_events_in_scope": 0,
                "verified_count": 0,
                "latest_sequence_number": None,
                "chain_head_hash": None,
                "first_inconsistency": None,
                "verification_timestamp": now_utc,
                "verification_scope_description": "Empty audit ledger; 0 events in scope.",
            }

        expected_sequence = start_sequence
        expected_previous_hash = GENESIS_HASH if start_sequence == 1 else None
        prev_timestamp = None
        verified_count = 0
        latest_valid_seq = None
        latest_valid_hash = None

        for ev in events:
            # 1. Check Monotonic Sequence Continuity
            if ev.sequence_number != expected_sequence:
                inconsistency = {
                    "sequence_number": ev.sequence_number,
                    "event_id": ev.id,
                    "failure_type": "SEQUENCE_GAP_OR_REORDER",
                    "expected_hash": None,
                    "actual_hash": None,
                    "safe_explanation": f"Sequence discontinuity detected: expected sequence #{expected_sequence}, found #{ev.sequence_number}.",
                }
                if log_verification_run:
                    log_audit_event(
                        db=db,
                        action="AUDIT_CHAIN_INTEGRITY_VERIFICATION",
                        entity_type="AUDIT_CHAIN",
                        entity_id="audit_events",
                        actor_email=current_user.email,
                        actor_user_id=current_user.id,
                        actor_role=current_user.role,
                        outcome="FAILURE",
                        metadata={"status": "TAMPER_DETECTED", "failure": inconsistency},
                    )
                return {
                    "status": "TAMPER_DETECTED",
                    "is_chain_intact": False,
                    "total_events_in_scope": total_in_scope,
                    "verified_count": verified_count,
                    "latest_sequence_number": latest_valid_seq,
                    "chain_head_hash": latest_valid_hash,
                    "first_inconsistency": inconsistency,
                    "verification_timestamp": now_utc,
                    "verification_scope_description": f"Verification failed at sequence #{ev.sequence_number}.",
                }

            # 2. Check Previous Hash Pointer Linking
            if expected_previous_hash is not None and ev.previous_hash != expected_previous_hash:
                inconsistency = {
                    "sequence_number": ev.sequence_number,
                    "event_id": ev.id,
                    "failure_type": "BROKEN_CHAIN_LINK",
                    "expected_hash": expected_previous_hash,
                    "actual_hash": ev.previous_hash,
                    "safe_explanation": f"Cryptographic link broken at sequence #{ev.sequence_number}: previous_hash does not match prior block digest.",
                }
                if log_verification_run:
                    log_audit_event(
                        db=db,
                        action="AUDIT_CHAIN_INTEGRITY_VERIFICATION",
                        entity_type="AUDIT_CHAIN",
                        entity_id="audit_events",
                        actor_email=current_user.email,
                        actor_user_id=current_user.id,
                        actor_role=current_user.role,
                        outcome="FAILURE",
                        metadata={"status": "TAMPER_DETECTED", "failure": inconsistency},
                    )
                return {
                    "status": "TAMPER_DETECTED",
                    "is_chain_intact": False,
                    "total_events_in_scope": total_in_scope,
                    "verified_count": verified_count,
                    "latest_sequence_number": latest_valid_seq,
                    "chain_head_hash": latest_valid_hash,
                    "first_inconsistency": inconsistency,
                    "verification_timestamp": now_utc,
                    "verification_scope_description": f"Verification failed at sequence #{ev.sequence_number}.",
                }

            # 3. Canonical Payload Recomputation and Integrity Check
            clean_meta = ev.parsed_metadata
            recomputed_hash = compute_canonical_event_hash(
                sequence_number=ev.sequence_number,
                event_id=ev.id,
                created_at=ev.created_at,
                action=ev.action,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                actor_user_id=ev.actor_user_id,
                actor_email=ev.actor_email,
                actor_role=ev.actor_role,
                outcome=ev.outcome,
                request_id=ev.request_id,
                policy_version=ev.policy_version,
                clean_metadata=clean_meta,
                previous_hash=ev.previous_hash or GENESIS_HASH,
            )

            if ev.current_hash != recomputed_hash:
                inconsistency = {
                    "sequence_number": ev.sequence_number,
                    "event_id": ev.id,
                    "failure_type": "PAYLOAD_TAMPERED",
                    "expected_hash": recomputed_hash,
                    "actual_hash": ev.current_hash,
                    "safe_explanation": f"Payload modification detected at sequence #{ev.sequence_number}: recorded current_hash does not match canonical payload digest.",
                }
                if log_verification_run:
                    log_audit_event(
                        db=db,
                        action="AUDIT_CHAIN_INTEGRITY_VERIFICATION",
                        entity_type="AUDIT_CHAIN",
                        entity_id="audit_events",
                        actor_email=current_user.email,
                        actor_user_id=current_user.id,
                        actor_role=current_user.role,
                        outcome="FAILURE",
                        metadata={"status": "TAMPER_DETECTED", "failure": inconsistency},
                    )
                return {
                    "status": "TAMPER_DETECTED",
                    "is_chain_intact": False,
                    "total_events_in_scope": total_in_scope,
                    "verified_count": verified_count,
                    "latest_sequence_number": latest_valid_seq,
                    "chain_head_hash": latest_valid_hash,
                    "first_inconsistency": inconsistency,
                    "verification_timestamp": now_utc,
                    "verification_scope_description": f"Verification failed at sequence #{ev.sequence_number}.",
                }

            # 4. Check Timestamp Monotonicity (Advisory Regression Check)
            if prev_timestamp and ev.created_at and ev.created_at < prev_timestamp:
                inconsistency = {
                    "sequence_number": ev.sequence_number,
                    "event_id": ev.id,
                    "failure_type": "TIMESTAMP_REGRESSION",
                    "expected_hash": None,
                    "actual_hash": None,
                    "safe_explanation": f"Timestamp sequence inversion detected at sequence #{ev.sequence_number}.",
                }
                if log_verification_run:
                    log_audit_event(
                        db=db,
                        action="AUDIT_CHAIN_INTEGRITY_VERIFICATION",
                        entity_type="AUDIT_CHAIN",
                        entity_id="audit_events",
                        actor_email=current_user.email,
                        actor_user_id=current_user.id,
                        actor_role=current_user.role,
                        outcome="FAILURE",
                        metadata={"status": "TAMPER_DETECTED", "failure": inconsistency},
                    )
                return {
                    "status": "TAMPER_DETECTED",
                    "is_chain_intact": False,
                    "total_events_in_scope": total_in_scope,
                    "verified_count": verified_count,
                    "latest_sequence_number": latest_valid_seq,
                    "chain_head_hash": latest_valid_hash,
                    "first_inconsistency": inconsistency,
                    "verification_timestamp": now_utc,
                    "verification_scope_description": f"Verification failed at sequence #{ev.sequence_number}.",
                }

            # Progress pointers
            prev_timestamp = ev.created_at
            expected_previous_hash = ev.current_hash
            expected_sequence += 1
            verified_count += 1
            latest_valid_seq = ev.sequence_number
            latest_valid_hash = ev.current_hash

        # All events verified successfully
        if log_verification_run:
            log_audit_event(
                db=db,
                action="AUDIT_CHAIN_INTEGRITY_VERIFICATION",
                entity_type="AUDIT_CHAIN",
                entity_id="audit_events",
                actor_email=current_user.email,
                actor_user_id=current_user.id,
                actor_role=current_user.role,
                outcome="SUCCESS",
                metadata={
                    "status": "PASS",
                    "verified_count": verified_count,
                    "head_sequence": latest_valid_seq,
                },
            )

        return {
            "status": "PASS",
            "is_chain_intact": True,
            "total_events_in_scope": total_in_scope,
            "verified_count": verified_count,
            "latest_sequence_number": latest_valid_seq,
            "chain_head_hash": latest_valid_hash,
            "first_inconsistency": None,
            "verification_timestamp": now_utc,
            "verification_scope_description": f"Full audit sequence (Blocks #{start_sequence} to #{latest_valid_seq}) verified intact.",
        }
