"""
Audit Module - Logging Service with Cryptographic SHA-256 Hash Chaining
Implements PRD-FR-091, PRD-FR-092, PRD-FR-093, and PRD-FR-094:
- Automatic credential sanitization (never logs secrets, auth tokens, passwords)
- Append-only monotonic sequence numbering
- Deterministic canonical serialization (SHA-256)
- Tamper-evident previous-hash and current-hash linking
"""
import uuid
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.modules.audit.models import AuditEvent
from app.core.security import sanitize_dict

GENESIS_HASH: str = "0" * 64


def compute_canonical_event_hash(
    sequence_number: int,
    event_id: str,
    created_at: datetime,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_user_id: Optional[str],
    actor_email: Optional[str],
    actor_role: Optional[str],
    outcome: str,
    request_id: Optional[str],
    policy_version: Optional[str],
    clean_metadata: Optional[Dict[str, Any]],
    previous_hash: str,
) -> str:
    """
    Computes deterministic cryptographic SHA-256 hash across canonical event payload.
    Guarantees:
    - Invariant key ordering via sort_keys=True
    - Canonical whitespace formatting (separators=(',', ':'))
    - Strict RFC 3339 / ISO 8601 timestamp serialization
    - Safe handling of Unicode, nulls, and nested structures
    """
    if isinstance(created_at, datetime):
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
        ts_str = created_at.isoformat()
    else:
        ts_str = str(created_at)

    canonical_dict = {
        "action": action,
        "actor_email": actor_email,
        "actor_role": actor_role,
        "actor_user_id": actor_user_id,
        "created_at": ts_str,
        "entity_id": str(entity_id),
        "entity_type": entity_type,
        "id": str(event_id),
        "metadata": clean_metadata or {},
        "outcome": outcome,
        "policy_version": policy_version,
        "previous_hash": previous_hash,
        "request_id": request_id,
        "sequence_number": sequence_number,
    }

    canonical_bytes = json.dumps(
        canonical_dict,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

    return hashlib.sha256(canonical_bytes).hexdigest()


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
    policy_version: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """
    Appends an immutable, hash-chained audit event to the ledger.
    - Sanitizes metadata to strip tokens, passwords, and private contents.
    - Determines monotonic sequence position.
    - Chains previous event's current_hash into the new event's payload.
    - Computes and stores authoritative SHA-256 digest.
    """
    clean_metadata = sanitize_dict(metadata) if metadata else None
    metadata_str = json.dumps(clean_metadata) if clean_metadata else None
    event_id = str(uuid.uuid4())
    event_created_at = datetime.now(timezone.utc)

    # Monotonic Sequence and Previous Hash Resolution
    latest_event = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.sequence_number.is_not(None))
        .order_by(AuditEvent.sequence_number.desc())
        .limit(1)
    ).first()

    if not latest_event:
        seq_num = 1
        prev_hash = GENESIS_HASH
    else:
        seq_num = latest_event.sequence_number + 1
        prev_hash = latest_event.current_hash or GENESIS_HASH

    curr_hash = compute_canonical_event_hash(
        sequence_number=seq_num,
        event_id=event_id,
        created_at=event_created_at,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        actor_role=actor_role,
        outcome=outcome,
        request_id=request_id,
        policy_version=policy_version,
        clean_metadata=clean_metadata,
        previous_hash=prev_hash,
    )

    event = AuditEvent(
        id=event_id,
        sequence_number=seq_num,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        actor_user_id=actor_user_id,
        actor_email=actor_email,
        actor_role=actor_role,
        outcome=outcome,
        request_id=request_id,
        ip_address=ip_address,
        policy_version=policy_version,
        metadata_json=metadata_str,
        previous_hash=prev_hash,
        current_hash=curr_hash,
        created_at=event_created_at,
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def backfill_legacy_audit_chain(db: Session) -> int:
    """
    Backfills any historical unchained audit records with continuous monotonic sequence numbers
    and cryptographic SHA-256 chain links starting from genesis.
    Uses _allow_audit_migration flag to allow the migration routine to set sequence fields.
    """
    unchained = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.sequence_number.is_(None))
        .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
    ).all()

    if not unchained:
        return 0

    latest_event = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.sequence_number.is_not(None))
        .order_by(AuditEvent.sequence_number.desc())
        .limit(1)
    ).first()

    current_seq = latest_event.sequence_number if latest_event else 0
    prev_hash = latest_event.current_hash if latest_event else GENESIS_HASH

    count = 0
    for ev in unchained:
        current_seq += 1
        ev._allow_audit_migration = True
        ev.sequence_number = current_seq
        ev.previous_hash = prev_hash

        ev.current_hash = compute_canonical_event_hash(
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
            clean_metadata=ev.parsed_metadata,
            previous_hash=prev_hash,
        )
        prev_hash = ev.current_hash
        count += 1

    db.commit()
    return count
