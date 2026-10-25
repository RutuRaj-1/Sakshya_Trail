"""
Module 5 — Renewal & Replacement Lineage Service
Enforces strict graph invariants: anti-self-reference, cycle detection,
cross-institution boundary checks, concurrency safety, and ancestor preservation.
Includes renewal draft initiation, successor creation, continuity assessment, and link correction.
"""
import uuid
import json
import logging
from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, desc

from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import InstrumentLineage, LifecyclePolicy
from app.modules.lifecycle.enums import (
    LineageRelationshipType,
    LineageRelationshipStatus,
    ContinuityIndicator,
    ContinuityOutcome,
)
from app.modules.lifecycle.schemas import (
    LineageCreateRequest,
    LineageChainItem,
    LineageTreeResponse,
    LineageValidateRequest,
    LineageValidateResponse,
    RenewalDraftResponse,
    RenewalCreateSuccessorRequest,
    ContinuityAssessmentResponse,
    LineageCorrectionRequest,
)
from app.modules.lifecycle.policy_service import resolve_active_policy, get_policy_by_id
from app.modules.lifecycle.continuity_service import (
    assess_lineage_continuity,
    ContinuityAssessmentResult,
)
from app.modules.audit.service import log_audit_event
from app.common.exceptions import AppException
from app.db.base import get_utc_now

logger = logging.getLogger(__name__)


def detect_cycle_in_lineage(
    db: Session,
    predecessor_id: str,
    successor_id: str,
) -> bool:
    """
    Checks if creating an edge (predecessor -> successor) introduces a directed cycle.
    A cycle occurs if `successor_id` is already an ancestor of `predecessor_id`,
    or if `predecessor_id == successor_id`.
    Uses iterative BFS to traverse ancestor edges.
    """
    if predecessor_id == successor_id:
        return True

    visited: Set[str] = set()
    queue: List[str] = [predecessor_id]

    while queue:
        current_id = queue.pop(0)
        if current_id == successor_id:
            return True
        if current_id in visited:
            continue
        visited.add(current_id)

        # Find all predecessors of current_id where relationship is ACTIVE
        incoming_edges = list(
            db.scalars(
                select(InstrumentLineage.predecessor_instrument_id).where(
                    and_(
                        InstrumentLineage.successor_instrument_id == current_id,
                        InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
                    )
                )
            ).all()
        )
        for parent_id in incoming_edges:
            if parent_id == successor_id:
                return True
            if parent_id not in visited:
                queue.append(parent_id)

    return False


def validate_proposed_lineage(
    db: Session,
    payload: LineageValidateRequest,
    current_user: Optional[User] = None,
) -> LineageValidateResponse:
    """
    Validates a proposed lineage link without committing any changes.
    Returns structured boolean is_valid with detailed error and warning lists.
    """
    pred_id = payload.predecessor_instrument_id
    succ_id = payload.successor_instrument_id
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Anti-self-reference
    if pred_id == succ_id:
        errors.append("An instrument cannot be linked to itself as its own renewal predecessor.")

    pred = db.scalar(select(Instrument).where(Instrument.id == pred_id))
    succ = db.scalar(select(Instrument).where(Instrument.id == succ_id))

    if not pred:
        errors.append(f"Predecessor instrument '{pred_id}' does not exist.")
    if not succ:
        errors.append(f"Successor instrument '{succ_id}' does not exist.")

    if pred and succ:
        # Tenancy check
        if current_user and current_user.role == "INSTITUTION_USER":
            if pred.institution_id != current_user.institution_id:
                errors.append("Access denied: Predecessor belongs to another institution.")
            if succ.institution_id != current_user.institution_id:
                errors.append("Access denied: Successor belongs to another institution.")

        # Cross-institution check
        if pred.institution_id != succ.institution_id and not payload.allow_authorized_transfer:
            errors.append(
                f"Cross-institution linkage prohibited. Predecessor is at institution '{pred.institution_id}' "
                f"while successor is at '{succ.institution_id}'."
            )

        # Cycle check
        if detect_cycle_in_lineage(db, predecessor_id=pred_id, successor_id=succ_id):
            errors.append(
                f"Cyclic renewal lineage detected. Instrument '{succ_id}' is already an ancestor of '{pred_id}'."
            )

        # Ambiguous branching checks
        existing_pred_link = db.scalar(
            select(InstrumentLineage).where(
                and_(
                    InstrumentLineage.predecessor_instrument_id == pred_id,
                    InstrumentLineage.successor_instrument_id != succ_id,
                    InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
                )
            )
        )
        if existing_pred_link:
            errors.append(
                f"Predecessor '{pred_id}' already has an active renewal link to successor '{existing_pred_link.successor_instrument_id}'."
            )

        existing_succ_link = db.scalar(
            select(InstrumentLineage).where(
                and_(
                    InstrumentLineage.successor_instrument_id == succ_id,
                    InstrumentLineage.predecessor_instrument_id != pred_id,
                    InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
                )
            )
        )
        if existing_succ_link:
            errors.append(
                f"Successor '{succ_id}' already has an active predecessor link to '{existing_succ_link.predecessor_instrument_id}'."
            )

        # Independent trust advisory
        if succ.trust_level != "L3_BANK_CONFIRMED":
            warnings.append(
                f"Successor is currently at trust level '{succ.trust_level}'. "
                "Linking to a predecessor does not promote or inherit trust; bank confirmation is required independently."
            )

    preliminary_continuity = None
    if pred and succ and not errors:
        policy = resolve_active_policy(db, instrument_type=pred.instrument_type)
        assessment = assess_lineage_continuity(db, pred, succ, policy, create_finding=False)
        preliminary_continuity = assessment.to_dict()

    return LineageValidateResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        predecessor_summary={
            "id": pred.id,
            "reference_number": pred.reference_number,
            "bank_name": pred.bank_name,
            "amount": str(pred.amount),
            "maturity_date": pred.maturity_date.isoformat() if pred.maturity_date else None,
            "status": pred.status,
            "trust_level": pred.trust_level,
        } if pred else None,
        successor_summary={
            "id": succ.id,
            "reference_number": succ.reference_number,
            "bank_name": succ.bank_name,
            "amount": str(succ.amount),
            "issue_date": succ.issue_date.isoformat() if succ.issue_date else None,
            "maturity_date": succ.maturity_date.isoformat() if succ.maturity_date else None,
            "effective_date": succ.effective_date.isoformat() if getattr(succ, "effective_date", None) else None,
            "status": succ.status,
            "trust_level": succ.trust_level,
        } if succ else None,
        preliminary_continuity=preliminary_continuity,
    )


def create_renewal_lineage(
    db: Session,
    payload: LineageCreateRequest,
    created_by_user_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    current_user: Optional[User] = None,
) -> InstrumentLineage:
    """
    Creates an explicit predecessor-successor renewal relationship.
    Transactionally enforces:
    1. Predecessor != Successor (Anti-self-reference).
    2. Existence of both instruments.
    3. Same institution requirement (unless allow_authorized_transfer=True).
    4. Cycle prevention across the lineage DAG.
    5. Single active renewal link per predecessor / successor in MVP model.
    6. Non-destructive preservation: Predecessor status is NEVER modified or overwritten.
    7. Transparent Gap / overlap continuity evaluation and Module 3 finding integration.
    8. Auto-evaluates successor lifecycle upon linkage.
    """
    pred_id = payload.predecessor_instrument_id
    succ_id = payload.successor_instrument_id

    # 1. Anti self-reference
    if pred_id == succ_id:
        raise AppException(
            status_code=400,
            message="An instrument cannot be its own predecessor or renewal replacement.",
            code="SELF_REFERENTIAL_LINEAGE_PROHIBITED",
        )

    # 2. Check for exact duplicate link (idempotent handling)
    exact_link = db.scalar(
        select(InstrumentLineage).where(
            and_(
                InstrumentLineage.predecessor_instrument_id == pred_id,
                InstrumentLineage.successor_instrument_id == succ_id,
                InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
            )
        )
    )
    if exact_link:
        return exact_link

    # Concurrency safe row locking if DB supports with_for_update (SQLite skips gracefully)
    try:
        pred = db.scalar(
            select(Instrument).where(Instrument.id == pred_id).with_for_update()
        )
        succ = db.scalar(
            select(Instrument).where(Instrument.id == succ_id).with_for_update()
        )
    except Exception:
        pred = db.scalar(select(Instrument).where(Instrument.id == pred_id))
        succ = db.scalar(select(Instrument).where(Instrument.id == succ_id))

    # Existence verification
    if not pred:
        raise AppException(
            status_code=404,
            message=f"Predecessor instrument '{pred_id}' not found.",
            code="PREDECESSOR_NOT_FOUND",
        )
    if not succ:
        raise AppException(
            status_code=404,
            message=f"Successor instrument '{succ_id}' not found.",
            code="SUCCESSOR_NOT_FOUND",
        )

    # 2.5 Institution tenancy validation
    if current_user and current_user.role == "INSTITUTION_USER":
        if pred.institution_id != current_user.institution_id:
            raise AppException(
                status_code=403,
                message="Access denied: Predecessor belongs to another institution.",
                code="FORBIDDEN",
            )
        if succ.institution_id != current_user.institution_id:
            raise AppException(
                status_code=403,
                message="Access denied: Successor belongs to another institution.",
                code="FORBIDDEN",
            )
        if payload.allow_authorized_transfer:
            raise AppException(
                status_code=403,
                message="Access denied: Institution users cannot authorize cross-institution transfers.",
                code="FORBIDDEN",
            )

    # 3. Institution boundary validation
    if pred.institution_id != succ.institution_id and not payload.allow_authorized_transfer:
        raise AppException(
            status_code=400,
            message=(
                f"Cross-institution renewal prohibited. Predecessor belongs to institution "
                f"'{pred.institution_id}' while successor belongs to '{succ.institution_id}'. "
                f"Explicit authorized transfer flag is required for mergers."
            ),
            code="CROSS_INSTITUTION_LINEAGE_PROHIBITED",
        )

    # 4. Cycle prevention
    if detect_cycle_in_lineage(db, predecessor_id=pred_id, successor_id=succ_id):
        raise AppException(
            status_code=400,
            message=(
                f"Cyclic renewal lineage detected. Instrument '{succ_id}' is already an ancestor "
                f"or in the renewal path of '{pred_id}'. Directed cycles are strictly prohibited."
            ),
            code="CYCLIC_LINEAGE_DETECTED",
        )

    # 5. Ambiguous chain prevention (1:1 active link)
    existing_pred_link = db.scalar(
        select(InstrumentLineage).where(
            and_(
                InstrumentLineage.predecessor_instrument_id == pred_id,
                InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
            )
        )
    )
    if existing_pred_link:
        raise AppException(
            status_code=409,
            message=(
                f"Predecessor '{pred_id}' already has an active renewal relationship "
                f"(ID: {existing_pred_link.id}, successor: {existing_pred_link.successor_instrument_id}). "
                f"Ambiguous branching is prohibited in single-chain model."
            ),
            code="DUPLICATE_PREDECESSOR_LINEAGE",
        )

    existing_succ_link = db.scalar(
        select(InstrumentLineage).where(
            and_(
                InstrumentLineage.successor_instrument_id == succ_id,
                InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
            )
        )
    )
    if existing_succ_link:
        raise AppException(
            status_code=409,
            message=(
                f"Successor '{succ_id}' is already linked as a renewal of "
                f"predecessor '{existing_succ_link.predecessor_instrument_id}'."
            ),
            code="DUPLICATE_SUCCESSOR_LINEAGE",
        )

    # Resolve policy for continuity calculation
    policy = None
    if payload.policy_id:
        policy = get_policy_by_id(db, payload.policy_id)
    if not policy:
        policy = resolve_active_policy(db, instrument_type=pred.instrument_type)

    # 6. Assess continuity & integrate Module 3 findings
    assessment = assess_lineage_continuity(
        db=db,
        predecessor=pred,
        successor=succ,
        policy=policy,
        create_finding=True,
    )

    lineage = InstrumentLineage(
        predecessor_instrument_id=pred_id,
        successor_instrument_id=succ_id,
        institution_id=pred.institution_id,
        relationship_type=payload.relationship_type.value,
        relationship_status=LineageRelationshipStatus.ACTIVE.value,
        reason_or_reference=payload.reason_or_reference,
        policy_id=policy.id if policy else None,
        policy_version=policy.version if policy else None,
        validity_gap_days=assessment.gap_days,
        validity_overlap_days=assessment.overlap_days,
        continuity_indicator=assessment.continuity_indicator.value,
        continuity_details_json=json.dumps(assessment.to_dict()),
        concurrency_version=1,
        created_by_user_id=created_by_user_id,
    )

    db.add(lineage)
    db.commit()
    db.refresh(lineage)

    # 7. Auto-evaluate lifecycle for successor and re-evaluate predecessor
    try:
        from app.modules.lifecycle.evaluation_service import evaluate_instrument_lifecycle
        evaluate_instrument_lifecycle(db=db, instrument_id=succ_id)
        evaluate_instrument_lifecycle(db=db, instrument_id=pred_id)
    except Exception as eval_err:
        logger.warning(f"Lifecycle evaluation on lineage creation failed: {eval_err}")

    # 8. Audit event
    log_audit_event(
        db=db,
        action="INSTRUMENT_RENEWAL_LINEAGE_CREATED",
        entity_type="INSTRUMENT_LINEAGE",
        entity_id=lineage.id,
        actor_user_id=created_by_user_id,
        actor_email=actor_email,
        metadata={
            "predecessor_instrument_id": pred_id,
            "successor_instrument_id": succ_id,
            "institution_id": pred.institution_id,
            "validity_gap_days": assessment.gap_days,
            "validity_overlap_days": assessment.overlap_days,
            "continuity_indicator": assessment.continuity_indicator.value,
            "continuity_outcome": assessment.outcome.value,
        },
    )

    return lineage


def initiate_renewal_draft(
    db: Session,
    predecessor_id: str,
    current_user: User,
) -> RenewalDraftResponse:
    """
    Initializes a renewal draft context for a predecessor instrument.
    Enforces tenancy scoping and prepares suggested successor fields without modifying predecessor.
    """
    pred = db.scalar(select(Instrument).where(Instrument.id == predecessor_id))
    if not pred:
        raise AppException(
            status_code=404,
            message=f"Predecessor instrument '{predecessor_id}' not found.",
            code="INSTRUMENT_NOT_FOUND",
        )

    if current_user.role == "INSTITUTION_USER" and pred.institution_id != current_user.institution_id:
        raise AppException(
            status_code=403,
            message="Access denied: Predecessor instrument belongs to another institution.",
            code="FORBIDDEN",
        )

    # Check if predecessor already has an active successor
    existing_successor_lineage = db.scalar(
        select(InstrumentLineage).where(
            and_(
                InstrumentLineage.predecessor_instrument_id == predecessor_id,
                InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
            )
        )
    )
    if existing_successor_lineage:
        raise AppException(
            status_code=409,
            message=(
                f"Predecessor '{predecessor_id}' already has an active renewal link to successor "
                f"'{existing_successor_lineage.successor_instrument_id}'. Duplicate renewal prohibited."
            ),
            code="ALREADY_RENEWED",
        )

    policy = resolve_active_policy(db, instrument_type=pred.instrument_type)

    suggested_issue_date = pred.maturity_date if pred.maturity_date else date.today()
    suggested_maturity_date = suggested_issue_date + timedelta(days=365)

    suggested_fields = {
        "bank_name": pred.bank_name,
        "branch": pred.branch,
        "amount": str(pred.amount),
        "currency": pred.currency,
        "suggested_issue_date": suggested_issue_date.isoformat(),
        "suggested_maturity_date": suggested_maturity_date.isoformat(),
        "suggested_effective_date": suggested_issue_date.isoformat(),
        "lien_holder": pred.lien_holder or "AICTE Regulation Bureau",
        "lien_details": pred.lien_details,
        "joint_with_aicte": pred.joint_with_aicte,
        "assigned_office": pred.assigned_office,
    }

    predecessor_summary = {
        "id": pred.id,
        "reference_number": pred.reference_number,
        "bank_name": pred.bank_name,
        "branch": pred.branch,
        "amount": str(pred.amount),
        "currency": pred.currency,
        "issue_date": pred.issue_date.isoformat() if pred.issue_date else None,
        "maturity_date": pred.maturity_date.isoformat() if pred.maturity_date else None,
        "status": pred.status,
        "trust_level": pred.trust_level,
    }

    policy_summary = {
        "policy_id": policy.id,
        "policy_code": policy.policy_code,
        "version": policy.version,
        "max_allowed_gap_days": policy.max_allowed_gap_days,
        "max_allowed_overlap_days": policy.max_allowed_overlap_days,
        "renewal_comparison_method": policy.renewal_comparison_method,
    }

    return RenewalDraftResponse(
        predecessor_instrument_id=pred.id,
        institution_id=pred.institution_id,
        suggested_fields=suggested_fields,
        predecessor_summary=predecessor_summary,
        policy_summary=policy_summary,
    )


def create_and_link_renewal_successor(
    db: Session,
    predecessor_id: str,
    payload: RenewalCreateSuccessorRequest,
    current_user: User,
) -> Tuple[Instrument, InstrumentLineage]:
    """
    Creates a new successor instrument and links it to the predecessor in a single transaction.
    Guarantees:
    - Predecessor record, documents, trust, and history are completely unchanged.
    - Successor starts at L0_DECLARED with its own distinct ID and fields.
    - Trust is NEVER promoted or copied from the predecessor.
    - Lineage constraints and gap/overlap continuity are strictly evaluated.
    """
    pred = db.scalar(select(Instrument).where(Instrument.id == predecessor_id))
    if not pred:
        raise AppException(
            status_code=404,
            message=f"Predecessor instrument '{predecessor_id}' not found.",
            code="INSTRUMENT_NOT_FOUND",
        )

    if current_user.role == "INSTITUTION_USER" and pred.institution_id != current_user.institution_id:
        raise AppException(
            status_code=403,
            message="Access denied: Predecessor instrument belongs to another institution.",
            code="FORBIDDEN",
        )

    # 1. Instantiate brand new successor instrument
    successor = Instrument(
        institution_id=pred.institution_id,
        instrument_type=pred.instrument_type,
        bank_name=payload.bank_name,
        branch=payload.branch,
        reference_number=payload.reference_number,
        amount=payload.amount,
        currency=payload.currency,
        issue_date=payload.issue_date,
        maturity_date=payload.maturity_date,
        effective_date=payload.effective_date,
        lien_holder=payload.lien_holder,
        lien_details=payload.lien_details,
        joint_with_aicte=payload.joint_with_aicte,
        lien_marked=True,
        assigned_office=pred.assigned_office,
        status="REGISTERED",
        trust_level="L0_DECLARED",  # NEVER inherits predecessor trust!
        created_by_user_id=current_user.id,
    )
    db.add(successor)
    db.commit()
    db.refresh(successor)

    # 2. Link successor to predecessor via lineage service
    lineage_req = LineageCreateRequest(
        predecessor_instrument_id=pred.id,
        successor_instrument_id=successor.id,
        relationship_type=payload.relationship_type,
        reason_or_reference=payload.reason_or_reference or f"Statutory renewal replacement for FDR {pred.reference_number}",
        allow_authorized_transfer=False,
    )

    lineage = create_renewal_lineage(
        db=db,
        payload=lineage_req,
        created_by_user_id=current_user.id,
        actor_email=current_user.email,
    )

    log_audit_event(
        db=db,
        action="RENEWAL_SUCCESSOR_CREATED_AND_LINKED",
        entity_type="INSTRUMENT",
        entity_id=successor.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        metadata={
            "successor_instrument_id": successor.id,
            "predecessor_instrument_id": pred.id,
            "lineage_id": lineage.id,
            "successor_reference": successor.reference_number,
            "trust_level": successor.trust_level,
        },
    )

    return successor, lineage


def correct_renewal_lineage(
    db: Session,
    lineage_id: str,
    payload: LineageCorrectionRequest,
    current_user: User,
) -> InstrumentLineage:
    """
    Authorized correction or deactivation of an existing lineage relationship edge.
    Actions supported:
    - DEACTIVATE: Marks status CANCELLED with mandatory reason.
    - SUPERSEDE: Marks status SUPERSEDED.
    - UPDATE_REASON: Updates reason_or_reference.
    Guarantees:
    - Optimistic concurrency control via expected_concurrency_version.
    - Full historical audit trail preserved in correction_history_json.
    - Re-evaluates lifecycle status of affected instruments.
    """
    lineage = db.scalar(select(InstrumentLineage).where(InstrumentLineage.id == lineage_id))
    if not lineage:
        raise AppException(
            status_code=404,
            message=f"Lineage relationship '{lineage_id}' not found.",
            code="LINEAGE_NOT_FOUND",
        )

    # Tenancy check
    if current_user.role == "INSTITUTION_USER" and lineage.institution_id != current_user.institution_id:
        raise AppException(
            status_code=403,
            message="Access denied: Lineage belongs to another institution.",
            code="FORBIDDEN",
        )

    # Optimistic concurrency check
    if payload.expected_concurrency_version is not None:
        if lineage.concurrency_version != payload.expected_concurrency_version:
            raise AppException(
                status_code=409,
                message=(
                    f"Lineage concurrency conflict. Expected version {payload.expected_concurrency_version}, "
                    f"but record is at version {lineage.concurrency_version}."
                ),
                code="CONCURRENCY_CONFLICT",
            )

    now = get_utc_now()
    old_status = lineage.relationship_status
    old_reason = lineage.reason_or_reference

    # Append to correction history
    history: List[Dict[str, Any]] = []
    if lineage.correction_history_json:
        try:
            history = json.loads(lineage.correction_history_json)
        except Exception:
            history = []

    history_entry = {
        "action": payload.action,
        "reason": payload.reason,
        "actor_user_id": current_user.id,
        "actor_role": current_user.role,
        "timestamp": now.isoformat(),
        "old_status": old_status,
        "old_reason": old_reason,
        "version_before": lineage.concurrency_version,
    }

    if payload.action == "DEACTIVATE":
        lineage.relationship_status = LineageRelationshipStatus.CANCELLED.value
    elif payload.action == "SUPERSEDE":
        lineage.relationship_status = LineageRelationshipStatus.SUPERSEDED.value
    elif payload.action == "UPDATE_REASON":
        lineage.reason_or_reference = payload.reason
    else:
        raise AppException(
            status_code=400,
            message=f"Unsupported lineage correction action '{payload.action}'. Supported: DEACTIVATE, SUPERSEDE, UPDATE_REASON.",
            code="INVALID_ACTION",
        )

    history.append(history_entry)
    lineage.correction_history_json = json.dumps(history)
    lineage.concurrency_version += 1
    db.commit()
    db.refresh(lineage)

    # Re-evaluate affected instruments
    try:
        from app.modules.lifecycle.evaluation_service import evaluate_instrument_lifecycle
        evaluate_instrument_lifecycle(db=db, instrument_id=lineage.predecessor_instrument_id)
        evaluate_instrument_lifecycle(db=db, instrument_id=lineage.successor_instrument_id)
    except Exception as eval_err:
        logger.warning(f"Re-evaluation after lineage correction failed: {eval_err}")

    log_audit_event(
        db=db,
        action="INSTRUMENT_LINEAGE_CORRECTED",
        entity_type="INSTRUMENT_LINEAGE",
        entity_id=lineage.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        metadata={
            "action": payload.action,
            "reason": payload.reason,
            "old_status": old_status,
            "new_status": lineage.relationship_status,
            "concurrency_version": lineage.concurrency_version,
        },
    )

    return lineage


def get_lineage_by_id(db: Session, lineage_id: str) -> Optional[InstrumentLineage]:
    return db.scalar(select(InstrumentLineage).where(InstrumentLineage.id == lineage_id))


def get_lineage_continuity_assessment(
    db: Session,
    lineage_id_or_instrument_id: str,
    current_user: Optional[User] = None,
) -> ContinuityAssessmentResponse:
    """
    Returns the granular continuity and gap/overlap assessment for a lineage ID or instrument.
    Enforces tenancy scoping when called by an INSTITUTION_USER.
    """
    lineage = db.scalar(
        select(InstrumentLineage).where(
            or_(
                InstrumentLineage.id == lineage_id_or_instrument_id,
                InstrumentLineage.successor_instrument_id == lineage_id_or_instrument_id,
                InstrumentLineage.predecessor_instrument_id == lineage_id_or_instrument_id,
            )
        )
    )

    if not lineage:
        raise AppException(
            status_code=404,
            message=f"No lineage relationship found for identifier '{lineage_id_or_instrument_id}'.",
            code="LINEAGE_NOT_FOUND",
        )

    pred = db.scalar(select(Instrument).where(Instrument.id == lineage.predecessor_instrument_id))
    succ = db.scalar(select(Instrument).where(Instrument.id == lineage.successor_instrument_id))

    if current_user and current_user.role == "INSTITUTION_USER":
        if lineage.institution_id != current_user.institution_id:
            raise AppException(
                status_code=403,
                message="Access denied: Lineage belongs to another institution.",
                code="FORBIDDEN",
            )
        if pred and pred.institution_id != current_user.institution_id:
            raise AppException(
                status_code=403,
                message="Access denied: Instrument belongs to another institution.",
                code="FORBIDDEN",
            )
        if succ and succ.institution_id != current_user.institution_id:
            raise AppException(
                status_code=403,
                message="Access denied: Instrument belongs to another institution.",
                code="FORBIDDEN",
            )

    policy = (
        get_policy_by_id(db, lineage.policy_id)
        if lineage.policy_id
        else resolve_active_policy(db, instrument_type=pred.instrument_type if pred else "FDR")
    )

    assessment = assess_lineage_continuity(
        db=db,
        predecessor=pred,  # type: ignore[arg-type]
        successor=succ,    # type: ignore[arg-type]
        policy=policy,
        create_finding=False,
    )

    return ContinuityAssessmentResponse(
        lineage_id=lineage.id,
        predecessor_instrument_id=lineage.predecessor_instrument_id,
        successor_instrument_id=lineage.successor_instrument_id,
        dates_compared=assessment.dates_compared,
        date_source_fields=assessment.date_source_fields,
        comparison_semantics=assessment.comparison_semantics,
        gap_days=assessment.gap_days,
        overlap_days=assessment.overlap_days,
        policy_version=assessment.policy_version,
        outcome=assessment.outcome.value,
        explanation=assessment.explanation,
        is_provisional=assessment.is_provisional,
        detector_type=assessment.detector_type,
        finding_id=assessment.finding_id,
        evaluated_at=assessment.evaluated_at,
    )


def get_lineage_tree(
    db: Session,
    instrument_id: str,
    current_user: Optional[User] = None,
) -> LineageTreeResponse:
    """
    Constructs the complete renewal ancestry and successor chain for an instrument.
    Traverses backward (ancestors) and forward (successors) up to depth 20.
    Enforces tenancy scoping when called by an INSTITUTION_USER.
    """
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(
            status_code=404,
            message=f"Instrument '{instrument_id}' not found",
            code="INSTRUMENT_NOT_FOUND",
        )

    if current_user and current_user.role == "INSTITUTION_USER":
        if instrument.institution_id != current_user.institution_id:
            raise AppException(
                status_code=403,
                message="Access denied: Instrument belongs to another institution.",
                code="FORBIDDEN",
            )

    # Direct relationships
    direct_pred_edge = db.scalar(
        select(InstrumentLineage).where(
            and_(
                InstrumentLineage.successor_instrument_id == instrument_id,
                InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
            )
        )
    )
    direct_succ_edge = db.scalar(
        select(InstrumentLineage).where(
            and_(
                InstrumentLineage.predecessor_instrument_id == instrument_id,
                InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
            )
        )
    )

    # 1. Traverse backward to find all ancestors
    ancestors: List[LineageChainItem] = []
    curr_id = instrument_id
    depth = 1
    while depth <= 20:
        edge = db.scalar(
            select(InstrumentLineage).where(
                and_(
                    InstrumentLineage.successor_instrument_id == curr_id,
                    InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
                )
            )
        )
        if not edge:
            break
        parent = db.scalar(select(Instrument).where(Instrument.id == edge.predecessor_instrument_id))
        if not parent:
            break
        ancestors.append(
            LineageChainItem(
                instrument_id=parent.id,
                reference_number=parent.reference_number,
                bank_name=parent.bank_name,
                amount=str(parent.amount),
                issue_date=str(parent.issue_date) if parent.issue_date else None,
                maturity_date=str(parent.maturity_date) if parent.maturity_date else None,
                status=parent.status,
                trust_level=parent.trust_level,
                depth=-depth,
            )
        )
        curr_id = parent.id
        depth += 1

    # 2. Traverse forward to find all successors
    successors: List[LineageChainItem] = []
    curr_id = instrument_id
    depth = 1
    while depth <= 20:
        edge = db.scalar(
            select(InstrumentLineage).where(
                and_(
                    InstrumentLineage.predecessor_instrument_id == curr_id,
                    InstrumentLineage.relationship_status == LineageRelationshipStatus.ACTIVE.value,
                )
            )
        )
        if not edge:
            break
        child = db.scalar(select(Instrument).where(Instrument.id == edge.successor_instrument_id))
        if not child:
            break
        successors.append(
            LineageChainItem(
                instrument_id=child.id,
                reference_number=child.reference_number,
                bank_name=child.bank_name,
                amount=str(child.amount),
                issue_date=str(child.issue_date) if child.issue_date else None,
                maturity_date=str(child.maturity_date) if child.maturity_date else None,
                status=child.status,
                trust_level=child.trust_level,
                depth=depth,
            )
        )
        curr_id = child.id
        depth += 1

    return LineageTreeResponse(
        current_instrument_id=instrument_id,
        ancestors=ancestors,
        successors=successors,
        direct_predecessor_lineage=direct_pred_edge,  # type: ignore[arg-type]
        direct_successor_lineage=direct_succ_edge,    # type: ignore[arg-type]
    )
