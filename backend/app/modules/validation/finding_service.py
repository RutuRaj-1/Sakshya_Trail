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
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.modules.instruments.models import Instrument
from app.modules.validation.models import ValidationFinding, ValidationRun
from app.modules.validation.enums import FindingStatus, RuleOutcome, RuleSeverity
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


# ---------------------------------------------------------------------------
# Prompt 4: Workflow Operations, Concurrency, and Review Queue
# ---------------------------------------------------------------------------

def transition_finding_status(
    db: Session,
    finding: ValidationFinding,
    target_status: str,
    actor_user: Any,
    reason: Optional[str] = None,
    expected_concurrency_version: Optional[int] = None,
) -> ValidationFinding:
    """
    Transition finding lifecycle status with strict transition rules, reason requirements,
    role authorization, and optimistic concurrency protection.

    Allowed transitions:
      OPEN      -> IN_REVIEW, RESOLVED, DISMISSED
      IN_REVIEW -> RESOLVED, DISMISSED
    """
    from app.common.exceptions import AppException, ForbiddenException, ConflictException
    from app.core.security import ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_SYSTEM_ADMIN

    # 1. Role permission: Only regulatory scrutiny officers can change finding status
    allowed_roles = (ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD)
    if actor_user.role not in allowed_roles:
        raise ForbiddenException(
            f"Role '{actor_user.role}' is not authorized to transition finding status. "
            f"Requires one of: {', '.join(allowed_roles)}."
        )

    # 2. Scope check: verify institution matches if user is scoped
    if actor_user.institution_id and actor_user.institution_id != finding.institution_id:
        raise ForbiddenException("Cannot modify finding belonging to another institution.")

    # 3. Optimistic concurrency check
    if expected_concurrency_version is not None:
        if finding.concurrency_version != expected_concurrency_version:
            raise ConflictException(
                "The finding has been modified by another concurrent review action. "
                f"Expected version {expected_concurrency_version}, but current version is {finding.concurrency_version}. "
                "Please reload and review latest state before retrying."
            )

    curr_status = finding.status
    target_norm = target_status.strip().upper()

    # 4. Enforce permitted transitions
    valid_transitions = {
        FindingStatus.OPEN.value: {
            FindingStatus.IN_REVIEW.value,
            FindingStatus.RESOLVED.value,
            FindingStatus.DISMISSED.value,
        },
        FindingStatus.IN_REVIEW.value: {
            FindingStatus.RESOLVED.value,
            FindingStatus.DISMISSED.value,
        },
    }

    allowed_targets = valid_transitions.get(curr_status, set())
    if target_norm not in allowed_targets:
        raise AppException(
            f"Invalid transition from '{curr_status}' to '{target_norm}'. "
            f"Allowed next states from '{curr_status}': {sorted(list(allowed_targets)) or 'None (terminal state)'}.",
            status_code=400,
            code="INVALID_FINDING_STATUS_TRANSITION",
        )

    # 5. Reason requirement: RESOLVED and DISMISSED strictly require a non-empty reason
    if target_norm in (FindingStatus.RESOLVED.value, FindingStatus.DISMISSED.value):
        if not reason or not reason.strip():
            raise AppException(
                f"A non-empty reason is mandatory when transitioning finding to '{target_norm}'.",
                status_code=422,
                code="REASON_REQUIRED",
            )

    now = _utc_now()
    prior_status = finding.status
    finding.status = target_norm
    finding.last_evaluated_at = now
    finding.concurrency_version += 1

    # Update resolution / dismissal tracking fields
    if target_norm in (FindingStatus.RESOLVED.value, FindingStatus.DISMISSED.value):
        finding.resolved_at = now
        finding.resolved_by_user_id = actor_user.id
        finding.resolution_note = reason.strip() if reason else None

    # Append to review_notes audit list
    notes = finding.review_notes
    notes.append({
        "id": str(uuid.uuid4()),
        "actor_id": actor_user.id,
        "actor_email": actor_user.email,
        "actor_role": actor_user.role,
        "action": f"STATUS_TRANSITION_{prior_status}_TO_{target_norm}",
        "reason": reason.strip() if reason else None,
        "timestamp": now.isoformat(),
    })
    finding.review_notes_json = json.dumps(notes)

    db.commit()
    db.refresh(finding)

    # Audit logging
    log_audit_event(
        db=db,
        action=f"VALIDATION_FINDING_{target_norm}",
        entity_type="validation_finding",
        entity_id=finding.id,
        actor_user_id=actor_user.id,
        actor_email=actor_user.email,
        actor_role=actor_user.role,
        outcome="SUCCESS",
        metadata={
            "prior_status": prior_status,
            "new_status": target_norm,
            "reason": reason.strip() if reason else None,
            "instrument_id": finding.instrument_id,
            "concurrency_version": finding.concurrency_version,
        },
    )

    return finding


def assign_finding(
    db: Session,
    finding: ValidationFinding,
    assigned_to_user_id: str,
    actor_user: Any,
) -> ValidationFinding:
    """Assign or reassign a finding to an authorized officer."""
    from app.common.exceptions import AppException, ForbiddenException, NotFoundException
    from app.modules.auth.models import User
    from app.core.security import ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_SYSTEM_ADMIN

    allowed_roles = (ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD)
    if actor_user.role not in allowed_roles:
        raise ForbiddenException("Not authorized to assign findings.")

    target_user = db.scalar(select(User).where(User.id == assigned_to_user_id))
    if not target_user:
        raise NotFoundException(f"User '{assigned_to_user_id}' not found.")

    now = _utc_now()
    finding.assigned_to_user_id = assigned_to_user_id
    finding.assigned_at = now
    finding.concurrency_version += 1

    notes = finding.review_notes
    notes.append({
        "id": str(uuid.uuid4()),
        "actor_id": actor_user.id,
        "actor_email": actor_user.email,
        "actor_role": actor_user.role,
        "action": "ASSIGNED",
        "assigned_to": target_user.email,
        "timestamp": now.isoformat(),
    })
    finding.review_notes_json = json.dumps(notes)

    db.commit()
    db.refresh(finding)

    log_audit_event(
        db=db,
        action="VALIDATION_FINDING_ASSIGNED",
        entity_type="validation_finding",
        entity_id=finding.id,
        actor_user_id=actor_user.id,
        actor_email=actor_user.email,
        actor_role=actor_user.role,
        outcome="SUCCESS",
        metadata={
            "assigned_to_user_id": assigned_to_user_id,
            "assigned_to_email": target_user.email,
            "instrument_id": finding.instrument_id,
        },
    )
    return finding


def add_finding_observation(
    db: Session,
    finding: ValidationFinding,
    actor_user: Any,
    observation_text: str,
) -> ValidationFinding:
    """Add a review observation note to a finding without altering its status."""
    from app.common.exceptions import AppException, ForbiddenException

    if not observation_text or not observation_text.strip():
        raise AppException("Observation note cannot be blank.", status_code=422, code="BLANK_OBSERVATION")

    now = _utc_now()
    finding.concurrency_version += 1

    notes = finding.review_notes
    notes.append({
        "id": str(uuid.uuid4()),
        "actor_id": actor_user.id,
        "actor_email": actor_user.email,
        "actor_role": actor_user.role,
        "action": "OBSERVATION",
        "note": observation_text.strip(),
        "timestamp": now.isoformat(),
    })
    finding.review_notes_json = json.dumps(notes)

    db.commit()
    db.refresh(finding)

    log_audit_event(
        db=db,
        action="VALIDATION_FINDING_OBSERVATION_ADDED",
        entity_type="validation_finding",
        entity_id=finding.id,
        actor_user_id=actor_user.id,
        actor_email=actor_user.email,
        actor_role=actor_user.role,
        outcome="SUCCESS",
        metadata={
            "instrument_id": finding.instrument_id,
            "observation_length": len(observation_text.strip()),
        },
    )
    return finding


def return_instrument_for_correction(
    db: Session,
    instrument_id: str,
    actor_user: Any,
    explanation: str,
) -> Instrument:
    """
    Return an instrument to the submitting institution for correction.
    Requires an explicit non-empty explanation and officer authorization.
    """
    from app.common.exceptions import AppException, ForbiddenException, NotFoundException
    from app.modules.instruments.models import Instrument
    from app.core.security import ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD, ROLE_SYSTEM_ADMIN

    allowed_roles = (ROLE_SCRUTINY_OFFICER, ROLE_BRANCH_HEAD)
    if actor_user.role not in allowed_roles:
        raise ForbiddenException("Only authorized officers can return a submission for correction.")

    if not explanation or not explanation.strip():
        raise AppException(
            "An explicit explanation is required when returning an instrument for correction.",
            status_code=422,
            code="EXPLANATION_REQUIRED",
        )

    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise NotFoundException(f"Instrument '{instrument_id}' not found.")

    instrument.status = "RETURNED_FOR_CORRECTION"
    instrument.updated_by_user_id = actor_user.id
    instrument.remarks = f"[Returned for correction by {actor_user.email}]: {explanation.strip()}"

    db.commit()
    db.refresh(instrument)

    log_audit_event(
        db=db,
        action="INSTRUMENT_RETURNED_FOR_CORRECTION",
        entity_type="Instrument",
        entity_id=instrument.id,
        actor_user_id=actor_user.id,
        actor_email=actor_user.email,
        actor_role=actor_user.role,
        outcome="SUCCESS",
        metadata={
            "explanation": explanation.strip(),
            "institution_id": instrument.institution_id,
        },
    )

    # Module 5: Emit material event notification
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="SUBMISSION_RETURNED_FOR_CORRECTION",
            entity_type="INSTRUMENT",
            entity_id=instrument.id,
            actor_user=actor_user,
            instrument_id=instrument.id,
            institution_id=instrument.institution_id,
            resulting_state="RETURNED_FOR_CORRECTION",
            details={
                "reference_number": instrument.reference_number,
                "reason": explanation.strip(),
            },
        )
        db.commit()
    except Exception:
        pass

    return instrument


def get_review_queue(
    db: Session,
    current_user: Any,
    status_filter: Optional[List[str]] = None,
    severity_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    rule_id_filter: Optional[str] = None,
    instrument_id_filter: Optional[str] = None,
    institution_id_filter: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "priority",  # 'priority', 'detected_at', 'severity', 'status'
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Query the discrepancy review queue with filtering, search, pagination,
    role-based tenant scoping, and transparent priority score calculation.
    """
    from app.core.security import ROLE_INSTITUTION_USER
    from app.modules.instruments.models import Instrument
    from app.modules.institutions.models import Institution
    from app.modules.documents.models import Document
    from app.modules.validation.priority_score import calculate_review_priority_score

    stmt = select(ValidationFinding).join(Instrument, ValidationFinding.instrument_id == Instrument.id)

    # 1. Scope enforcement
    if current_user.role == ROLE_INSTITUTION_USER:
        if not current_user.institution_id:
            return {"items": [], "total": 0, "skip": skip, "limit": limit}
        stmt = stmt.where(ValidationFinding.institution_id == current_user.institution_id)
        # Exclude internal-only cross-institution rules for standard institution users
        stmt = stmt.where(ValidationFinding.rule_id != "VAL-DUP-002")
    elif institution_id_filter:
        stmt = stmt.where(ValidationFinding.institution_id == institution_id_filter)

    if instrument_id_filter:
        stmt = stmt.where(ValidationFinding.instrument_id == instrument_id_filter)
    if status_filter:
        stmt = stmt.where(ValidationFinding.status.in_(status_filter))
    if severity_filter:
        stmt = stmt.where(ValidationFinding.severity == severity_filter)
    if category_filter:
        stmt = stmt.where(ValidationFinding.category == category_filter)
    if rule_id_filter:
        stmt = stmt.where(ValidationFinding.rule_id == rule_id_filter)

    # Text search
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            ValidationFinding.title.ilike(term)
            | ValidationFinding.rule_id.ilike(term)
            | Instrument.reference_number.ilike(term)
            | Instrument.bank_name.ilike(term)
        )

    # Query all matching findings for accurate prioritization
    all_matching = list(db.scalars(stmt).all())
    total_count = len(all_matching)

    # Pre-cache instruments and their open findings for fast score computation
    inst_ids = {f.instrument_id for f in all_matching}
    instruments_map = {
        inst.id: inst for inst in db.scalars(select(Instrument).where(Instrument.id.in_(inst_ids))).all()
    } if inst_ids else {}

    # Check FDR copy presence for each instrument
    fdr_copy_map = {}
    if inst_ids:
        docs = db.scalars(
            select(Document).where(
                Document.instrument_id.in_(inst_ids),
                Document.category == "FDR_COPY",
                Document.status == "ACTIVE",
            )
        ).all()
        for d in docs:
            fdr_copy_map[d.instrument_id] = True

    # Compute priority scores and decorate findings
    scored_items: List[Dict[str, Any]] = []
    for f in all_matching:
        inst = instruments_map.get(f.instrument_id)
        has_fdr = fdr_copy_map.get(f.instrument_id, False)

        # Related open findings for this instrument
        inst_open_findings = [
            other for other in all_matching
            if other.instrument_id == f.instrument_id and other.status in (FindingStatus.OPEN.value, FindingStatus.IN_REVIEW.value)
        ]

        priority_res = calculate_review_priority_score(
            instrument=inst,
            open_findings=inst_open_findings,
            has_fdr_copy=has_fdr,
        )

        item_dict = {
            "id": f.id,
            "instrument_id": f.instrument_id,
            "institution_id": f.institution_id,
            "rule_id": f.rule_id,
            "rule_version": f.rule_version,
            "rule_type": f.rule_type,
            "category": f.category,
            "severity": f.severity,
            "status": f.status,
            "title": f.title,
            "explanation": f.explanation,
            "observed_value": f.observed_value,
            "expected_value": f.expected_value,
            "evidence_refs": json.loads(f.evidence_refs_json) if f.evidence_refs_json else [],
            "suggested_action": f.suggested_action,
            "policy_version_ref": f.policy_version_ref,
            "first_detected_at": f.first_detected_at.isoformat() if f.first_detected_at else None,
            "last_evaluated_at": f.last_evaluated_at.isoformat() if f.last_evaluated_at else None,
            "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
            "resolution_note": f.resolution_note,
            "assigned_to_user_id": f.assigned_to_user_id,
            "assigned_at": f.assigned_at.isoformat() if f.assigned_at else None,
            "concurrency_version": f.concurrency_version,
            "review_notes": f.review_notes,
            "priority_score": priority_res.total_score,
            "priority_score_details": priority_res.to_dict(),
            "instrument_summary": {
                "reference_number": inst.reference_number if inst else None,
                "bank_name": inst.bank_name if inst else None,
                "amount": str(inst.amount) if inst and inst.amount else None,
                "status": inst.status if inst else None,
                "trust_level": inst.trust_level if inst else None,
                "maturity_date": inst.maturity_date.isoformat() if inst and inst.maturity_date else None,
            } if inst else None,
        }
        scored_items.append(item_dict)

    # Sorting
    reverse = (sort_order.lower() == "desc")
    if sort_by == "priority":
        scored_items.sort(key=lambda x: x["priority_score"], reverse=reverse)
    elif sort_by == "severity":
        sev_rank = {RuleSeverity.CRITICAL.value: 4, RuleSeverity.HIGH.value: 3, RuleSeverity.MEDIUM.value: 2, RuleSeverity.LOW.value: 1, RuleSeverity.INFO.value: 0}
        scored_items.sort(key=lambda x: sev_rank.get(x["severity"], 0), reverse=reverse)
    elif sort_by == "status":
        scored_items.sort(key=lambda x: x["status"], reverse=reverse)
    else:  # detected_at
        scored_items.sort(key=lambda x: x["first_detected_at"] or "", reverse=reverse)

    paginated = scored_items[skip : skip + limit]

    return {
        "items": paginated,
        "total": total_count,
        "skip": skip,
        "limit": limit,
    }


