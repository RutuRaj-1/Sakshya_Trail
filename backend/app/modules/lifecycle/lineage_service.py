"""
Module 5 — Renewal & Replacement Lineage Service
Enforces strict graph invariants: anti-self-reference, cycle detection,
cross-institution boundary checks, concurrency safety, and ancestor preservation.
"""
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.modules.instruments.models import Instrument
from app.modules.lifecycle.models import InstrumentLineage, LifecyclePolicy
from app.modules.lifecycle.enums import (
    LineageRelationshipType,
    LineageRelationshipStatus,
    ContinuityIndicator,
)
from app.modules.lifecycle.schemas import (
    LineageCreateRequest,
    LineageChainItem,
    LineageTreeResponse,
)
from app.modules.lifecycle.policy_service import resolve_active_policy, get_policy_by_id
from app.modules.audit.service import log_audit_event
from app.common.exceptions import AppException
from app.db.base import get_utc_now


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


def create_renewal_lineage(
    db: Session,
    payload: LineageCreateRequest,
    created_by_user_id: Optional[str] = None,
    actor_email: Optional[str] = None,
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
    7. Gap / overlap continuity evaluation.
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

    # 2. Existence verification
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

    # 5. MVP Ambiguous chain prevention (1:1 active link)
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
                f"Ambiguous branching is prohibited in MVP single-chain model."
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

    # 6. Continuity calculation (Gap vs Overlap)
    validity_gap_days = None
    validity_overlap_days = None
    continuity = ContinuityIndicator.UNKNOWN.value

    if pred.maturity_date and succ.issue_date:
        diff_days = (succ.issue_date - pred.maturity_date).days
        if diff_days > 0:
            validity_gap_days = diff_days
            validity_overlap_days = 0
            if validity_gap_days > policy.max_allowed_gap_days:
                continuity = ContinuityIndicator.GAP_DETECTED.value
            else:
                continuity = ContinuityIndicator.CONTINUOUS.value
        else:
            validity_gap_days = 0
            validity_overlap_days = abs(diff_days)
            if validity_overlap_days > policy.max_allowed_overlap_days:
                continuity = ContinuityIndicator.OVERLAP_DETECTED.value
            else:
                continuity = ContinuityIndicator.CONTINUOUS.value

    lineage = InstrumentLineage(
        predecessor_instrument_id=pred_id,
        successor_instrument_id=succ_id,
        institution_id=pred.institution_id,
        relationship_type=payload.relationship_type.value,
        relationship_status=LineageRelationshipStatus.ACTIVE.value,
        reason_or_reference=payload.reason_or_reference,
        policy_id=policy.id if policy else None,
        policy_version=policy.version if policy else None,
        validity_gap_days=validity_gap_days,
        validity_overlap_days=validity_overlap_days,
        continuity_indicator=continuity,
        concurrency_version=1,
        created_by_user_id=created_by_user_id,
    )

    db.add(lineage)
    db.commit()
    db.refresh(lineage)

    # Audit event
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
            "validity_gap_days": validity_gap_days,
            "validity_overlap_days": validity_overlap_days,
            "continuity_indicator": continuity,
        },
    )

    return lineage


def get_lineage_by_id(db: Session, lineage_id: str) -> Optional[InstrumentLineage]:
    return db.scalar(select(InstrumentLineage).where(InstrumentLineage.id == lineage_id))


def get_lineage_tree(db: Session, instrument_id: str) -> LineageTreeResponse:
    """
    Constructs the complete renewal ancestry and successor chain for an instrument.
    Traverses backward (ancestors) and forward (successors) up to depth 20.
    """
    instrument = db.scalar(select(Instrument).where(Instrument.id == instrument_id))
    if not instrument:
        raise AppException(status_code=404, message=f"Instrument '{instrument_id}' not found", code="INSTRUMENT_NOT_FOUND")

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
