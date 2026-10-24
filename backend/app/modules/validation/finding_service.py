"""
Module 3 — Finding Persistence and Deduplication Service

Responsibilities
----------------
* Persist new ValidationFinding records for FAIL / WARNING rule outcomes.
* Deduplicate: if an identical open finding (same fingerprint + rule_version) already
  exists for the instrument, update its last_evaluated_at timestamp instead of
  creating a duplicate.
* When a previously FAIL/WARNING outcome no longer fires (outcome is PASS or NOT_APPLICABLE),
  mark the corresponding open finding as RESOLVED (with an automated resolution note),
  preserving the history.
* Supersede: if a rule is updated (new rule_version) and fires, supersede the older version's
  finding and create a fresh one.

Safety constraints
------------------
* Does NOT modify Instrument.trust_level.
* Does NOT approve or reject releases.
* Does NOT delete findings — only status transitions with audit trail.
"""
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.modules.validation.models import ValidationFinding, ValidationRun
from app.modules.validation.enums import FindingStatus, RuleOutcome
from app.modules.validation.registry import RuleResult, compute_finding_fingerprint
from app.modules.audit.service import log_audit_event


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upsert_finding(
    db: Session,
    instrument_id: str,
    institution_id: str,
    rule_result: RuleResult,
    validation_run_id: Optional[str] = None,
    document_id: Optional[str] = None,
    document_version_id: Optional[str] = None,
    triggered_by_user_id: Optional[str] = None,
) -> Optional[ValidationFinding]:
    """
    Create or update a finding record for a FAIL or WARNING rule result.

    Deduplication logic
    -------------------
    1. Compute the finding fingerprint from (instrument_id, rule_id, rule_version, fingerprint_key).
    2. Look for an existing OPEN or IN_REVIEW finding with the same fingerprint AND rule_version.
    3. If found: update last_evaluated_at only (idempotent re-run).
    4. If not found: check for an older rule_version finding with the same fingerprint base
       (same rule_id) — if present, supersede it and create a fresh finding.
    5. If none found: create a new finding.

    Returns the created/updated ValidationFinding, or None if outcome is not a finding.
    """
    if not rule_result.is_finding:
        return None

    fingerprint = compute_finding_fingerprint(
        instrument_id=instrument_id,
        rule_id=rule_result.rule_id,
        rule_version=rule_result.rule_version,
        fingerprint_key=rule_result.fingerprint_key,
    )

    now = _utc_now()

    # --- Step 1: Exact match on fingerprint and rule_version across statuses ---
    existing = db.scalar(
        select(ValidationFinding).where(
            and_(
                ValidationFinding.instrument_id == instrument_id,
                ValidationFinding.finding_fingerprint == fingerprint,
                ValidationFinding.rule_version == rule_result.rule_version,
            )
        )
    )
    if existing:
        if existing.status in (FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value):
            existing.last_evaluated_at = now
            db.commit()
            db.refresh(existing)
            return existing
        elif existing.status == FindingStatus.DISMISSED.value:
            # Unchanged input was manually dismissed: do not re-open without an input/rule change
            existing.last_evaluated_at = now
            db.commit()
            db.refresh(existing)
            return existing
        elif existing.status == FindingStatus.RESOLVED.value:
            # Condition failed again with same fingerprint: transition back to OPEN
            existing.status = FindingStatus.OPEN.value
            existing.last_evaluated_at = now
            db.commit()
            db.refresh(existing)
            return existing

    # --- Step 2: Check for existing active findings for this rule (different version or changed inputs) ---
    active_findings = list(
        db.scalars(
            select(ValidationFinding).where(
                and_(
                    ValidationFinding.instrument_id == instrument_id,
                    ValidationFinding.rule_id == rule_result.rule_id,
                    ValidationFinding.status.in_([FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value]),
                )
            )
        ).all()
    )

    # --- Step 3: Create fresh finding ---
    new_finding = ValidationFinding(
        finding_fingerprint=fingerprint,
        instrument_id=instrument_id,
        institution_id=institution_id,
        document_id=document_id,
        document_version_id=document_version_id,
        rule_id=rule_result.rule_id,
        rule_version=rule_result.rule_version,
        rule_type=rule_result.rule_type.value,
        category=rule_result.category.value,
        severity=rule_result.severity.value,
        status=FindingStatus.OPEN.value,
        title=rule_result.title,
        explanation=rule_result.explanation,
        observed_value=rule_result.observed_value,
        expected_value=rule_result.expected_value,
        evidence_refs_json=json.dumps(rule_result.evidence_refs) if rule_result.evidence_refs else None,
        suggested_action=rule_result.suggested_action,
        policy_version_ref=rule_result.policy_version_ref,
        first_detected_at=now,
        last_evaluated_at=now,
        validation_run_id=validation_run_id,
    )
    db.add(new_finding)
    db.flush()  # get the new ID before superseding

    # Supersede older active findings (preserve original evidence and historical record)
    for older in active_findings:
        older.status = FindingStatus.SUPERSEDED.value
        older.resolved_at = now
        reason = (
            f"Superseded by updated rule version {rule_result.rule_version} (finding {new_finding.id})."
            if older.rule_version != rule_result.rule_version
            else f"Superseded due to changed input on re-evaluation (finding {new_finding.id})."
        )
        older.resolution_note = reason
        older.superseded_by_finding_id = new_finding.id

    db.commit()
    db.refresh(new_finding)

    # Audit
    if triggered_by_user_id:
        log_audit_event(
            db=db,
            action="VALIDATION_FINDING_CREATED",
            entity_type="validation_finding",
            entity_id=new_finding.id,
            actor_user_id=triggered_by_user_id,
            outcome="SUCCESS",
            metadata={
                "rule_id": rule_result.rule_id,
                "rule_version": rule_result.rule_version,
                "severity": rule_result.severity.value,
                "instrument_id": instrument_id,
                "outcome": rule_result.outcome.value,
            },
        )

    return new_finding


def resolve_finding_if_cleared(
    db: Session,
    instrument_id: str,
    rule_id: str,
    rule_version: str,
    fingerprint_key: str = "",
    resolution_note: str = "Condition resolved on re-evaluation.",
    resolved_by_user_id: Optional[str] = None,
) -> int:
    """
    Mark open findings for a rule as RESOLVED when the rule no longer fires.
    Resolves any OPEN or IN_REVIEW finding for (instrument_id, rule_id).
    Returns the number of findings resolved.
    """
    now = _utc_now()

    open_findings = db.scalars(
        select(ValidationFinding).where(
            and_(
                ValidationFinding.instrument_id == instrument_id,
                ValidationFinding.rule_id == rule_id,
                ValidationFinding.status.in_([FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value]),
            )
        )
    ).all()

    count = 0
    for finding in open_findings:
        finding.status = FindingStatus.RESOLVED.value
        finding.resolved_at = now
        finding.resolved_by_user_id = resolved_by_user_id
        finding.resolution_note = resolution_note
        finding.last_evaluated_at = now
        count += 1

    if count:
        db.commit()

    return count


def get_findings_for_instrument(
    db: Session,
    instrument_id: str,
    status_filter: Optional[List[str]] = None,
    severity_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[ValidationFinding]:
    """Retrieve findings for an instrument with optional filters."""
    stmt = select(ValidationFinding).where(
        ValidationFinding.instrument_id == instrument_id
    )

    if status_filter:
        stmt = stmt.where(ValidationFinding.status.in_(status_filter))
    if severity_filter:
        stmt = stmt.where(ValidationFinding.severity == severity_filter)
    if category_filter:
        stmt = stmt.where(ValidationFinding.category == category_filter)

    stmt = stmt.order_by(
        ValidationFinding.first_detected_at.desc()
    ).offset(skip).limit(limit)

    return list(db.scalars(stmt).all())


def get_finding_by_id(
    db: Session,
    finding_id: str,
    instrument_id: Optional[str] = None,
) -> Optional[ValidationFinding]:
    """Retrieve a single finding by ID, optionally scoped to an instrument."""
    stmt = select(ValidationFinding).where(ValidationFinding.id == finding_id)
    if instrument_id:
        stmt = stmt.where(ValidationFinding.instrument_id == instrument_id)
    return db.scalar(stmt)


def dismiss_finding(
    db: Session,
    finding: ValidationFinding,
    dismissed_by_user_id: str,
    reason: str,
) -> ValidationFinding:
    """
    Dismiss a finding (human reviewer determined it is not actionable).
    Only OPEN or IN_REVIEW findings may be dismissed.
    """
    from app.common.exceptions import AppException
    if finding.status in (FindingStatus.DISMISSED.value, FindingStatus.SUPERSEDED.value):
        raise AppException(
            f"Finding is already in terminal status '{finding.status}' and cannot be dismissed.",
            status_code=400,
            code="FINDING_TERMINAL_STATUS",
        )

    now = _utc_now()
    finding.status = FindingStatus.DISMISSED.value
    finding.resolved_at = now
    finding.resolved_by_user_id = dismissed_by_user_id
    finding.resolution_note = reason
    db.commit()
    db.refresh(finding)

    log_audit_event(
        db=db,
        action="VALIDATION_FINDING_DISMISSED",
        entity_type="validation_finding",
        entity_id=finding.id,
        actor_user_id=dismissed_by_user_id,
        outcome="SUCCESS",
        metadata={"reason": reason, "instrument_id": finding.instrument_id},
    )
    return finding


def re_evaluate_finding(
    db: Session,
    finding_id: str,
    actor_user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Re-evaluate a specific finding by re-running its governing rule on the parent instrument.
    Enforces that only the registered rule for this finding is executed.
    """
    from app.common.exceptions import NotFoundException
    finding = db.scalar(select(ValidationFinding).where(ValidationFinding.id == finding_id))
    if not finding:
        raise NotFoundException(f"Finding '{finding_id}' not found.")

    from app.modules.validation.engine import run_validation
    run_result = run_validation(
        db=db,
        instrument_id=finding.instrument_id,
        triggered_by_user_id=actor_user_id,
        rule_ids=[finding.rule_id],
    )
    db.refresh(finding)

    if actor_user_id:
        log_audit_event(
            db=db,
            action="VALIDATION_FINDING_REEVALUATED",
            entity_type="validation_finding",
            entity_id=finding.id,
            actor_user_id=actor_user_id,
            outcome="SUCCESS",
            metadata={
                "rule_id": finding.rule_id,
                "instrument_id": finding.instrument_id,
                "status_after": finding.status,
            },
        )

    return {
        "finding": finding,
        "run_result": run_result,
    }


def get_validation_runs_for_instrument(
    db: Session,
    instrument_id: str,
    skip: int = 0,
    limit: int = 50,
) -> tuple[List[ValidationRun], int]:
    """Retrieve validation run logs for an instrument with pagination."""
    from sqlalchemy import func, desc
    total = db.scalar(
        select(func.count(ValidationRun.id)).where(ValidationRun.instrument_id == instrument_id)
    ) or 0

    runs = list(
        db.scalars(
            select(ValidationRun)
            .where(ValidationRun.instrument_id == instrument_id)
            .order_by(desc(ValidationRun.run_at))
            .offset(skip)
            .limit(limit)
        ).all()
    )
    return runs, total

