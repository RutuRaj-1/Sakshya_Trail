"""
Module 5 — Lifecycle Monitoring Service
Surfaces approaching maturity, matured, and overdue instruments with tenancy-aware scoping,
unresolved discrepancy counts from Module 3, and verification states from Module 4.
"""
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc, func

from app.modules.instruments.models import Instrument
from app.modules.institutions.models import Institution
from app.modules.lifecycle.models import LifecycleEvaluation
from app.modules.lifecycle.enums import MaturityStage
from app.modules.lifecycle.schemas import (
    MonitoringInstrumentItem,
    MonitoringListResponse,
)
from app.modules.validation.models import ValidationFinding
from app.modules.verification.models import VerificationRequest
from app.modules.auth.models import User
from app.common.exceptions import ForbiddenException, AppException


def _get_scoped_instrument_ids(
    db: Session,
    current_user: User,
    institution_id: Optional[str] = None,
    office: Optional[str] = None,
) -> Any:
    """Applies strict RBAC and tenancy scoping on instrument queries."""
    stmt = select(Instrument.id, Instrument.institution_id)
    filters = []

    # Institution user scope: strictly limited to their own institution
    if current_user.role == "INSTITUTION_USER":
        if not current_user.institution_id:
            raise ForbiddenException("Institution user record lacks assigned institution ID.")
        filters.append(Instrument.institution_id == current_user.institution_id)
    else:
        # Officer / Admin scopes
        if institution_id:
            filters.append(Instrument.institution_id == institution_id)
        if office:
            filters.append(Instrument.assigned_office == office)

    if filters:
        stmt = stmt.where(and_(*filters))
    return stmt


def list_monitoring_instruments(
    db: Session,
    category: str,
    current_user: User,
    page: int = 1,
    limit: int = 50,
    institution_id: Optional[str] = None,
    office: Optional[str] = None,
) -> MonitoringListResponse:
    """
    Retrieves paginated instrument monitoring items based on category:
    - APPROACHING_MATURITY: MATURING_SOON or CRITICAL_WINDOW
    - MATURED: MATURED or EXPIRED
    - OVERDUE: is_overdue == True or is_escalated == True
    """
    offset = (page - 1) * limit

    # Base filter for category
    eval_filter = []
    if category == "APPROACHING_MATURITY":
        eval_filter.append(
            LifecycleEvaluation.maturity_stage.in_(
                [MaturityStage.MATURING_SOON.value, MaturityStage.CRITICAL_WINDOW.value]
            )
        )
    elif category == "MATURED":
        eval_filter.append(
            LifecycleEvaluation.maturity_stage.in_(
                [MaturityStage.MATURED.value, MaturityStage.EXPIRED.value]
            )
        )
    elif category == "OVERDUE":
        eval_filter.append(
            (LifecycleEvaluation.is_overdue == True) | (LifecycleEvaluation.is_escalated == True)  # noqa: E712
        )
    else:
        raise AppException(status_code=400, message=f"Invalid category '{category}'", code="INVALID_CATEGORY")

    # Tenancy scoping on instruments
    scoped_query = _get_scoped_instrument_ids(db, current_user, institution_id, office)
    scoped_inst_ids = [row[0] for row in db.execute(scoped_query).all()]

    if not scoped_inst_ids:
        return MonitoringListResponse(
            category=category,
            total_count=0,
            page=page,
            limit=limit,
            items=[],
        )

    # Subquery for latest evaluation ID per instrument
    latest_eval_subq = (
        select(
            LifecycleEvaluation.instrument_id,
            func.max(LifecycleEvaluation.evaluation_timestamp).label("max_ts"),
        )
        .where(LifecycleEvaluation.instrument_id.in_(scoped_inst_ids))
        .group_by(LifecycleEvaluation.instrument_id)
        .subquery()
    )

    # Join with latest evaluation matching criteria
    query = (
        select(LifecycleEvaluation, Instrument, Institution)
        .join(
            latest_eval_subq,
            and_(
                LifecycleEvaluation.instrument_id == latest_eval_subq.c.instrument_id,
                LifecycleEvaluation.evaluation_timestamp == latest_eval_subq.c.max_ts,
            ),
        )
        .join(Instrument, Instrument.id == LifecycleEvaluation.instrument_id)
        .join(Institution, Institution.id == Instrument.institution_id)
        .where(and_(*eval_filter))
    )

    total_count = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = db.execute(
        query.order_by(LifecycleEvaluation.days_to_maturity.asc().nullslast()).offset(offset).limit(limit)
    ).all()

    items: List[MonitoringInstrumentItem] = []
    for eval_rec, inst, inst_info in records:
        # Cross-surface Module 3 open findings count
        open_findings_count = db.scalar(
            select(func.count(ValidationFinding.id)).where(
                and_(
                    ValidationFinding.instrument_id == inst.id,
                    ValidationFinding.status == "OPEN",
                )
            )
        ) or 0

        # Cross-surface Module 4 verification status
        latest_vr = db.scalar(
            select(VerificationRequest)
            .where(VerificationRequest.instrument_id == inst.id)
            .order_by(desc(VerificationRequest.created_at))
        )
        vr_status = latest_vr.status if latest_vr else None

        items.append(
            MonitoringInstrumentItem(
                instrument_id=inst.id,
                institution_id=inst.institution_id,
                institution_name=inst_info.display_name or inst_info.legal_name,
                reference_number=inst.reference_number,
                bank_name=inst.bank_name,
                amount=str(inst.amount),
                issue_date=inst.issue_date.isoformat() if inst.issue_date else None,
                maturity_date=inst.maturity_date.isoformat() if inst.maturity_date else None,
                days_to_maturity=eval_rec.days_to_maturity,
                maturity_stage=eval_rec.maturity_stage,
                due_condition=eval_rec.due_condition,
                is_overdue=eval_rec.is_overdue,
                is_escalated=eval_rec.is_escalated,
                escalation_role=eval_rec.escalation_role,
                institution_action_due_date=eval_rec.institution_action_due_date.isoformat()
                if eval_rec.institution_action_due_date
                else None,
                officer_action_due_date=eval_rec.officer_action_due_date.isoformat()
                if eval_rec.officer_action_due_date
                else None,
                administrative_status=inst.status,
                trust_level=inst.trust_level,
                unresolved_findings_count=open_findings_count,
                verification_status=vr_status,
            )
        )

    return MonitoringListResponse(
        category=category,
        total_count=total_count,
        page=page,
        limit=limit,
        items=items,
    )
