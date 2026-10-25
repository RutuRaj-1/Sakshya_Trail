"""
Priority Service (Module 7 — Command Center)
Implements PRD-FR-075: Operational priority queue with transparent factor breakdown.
Computes an explainable [0.0 - 100.0] priority score with disclosed factor weights.
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_, desc

from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.validation.models import ValidationFinding
from app.modules.lifecycle.models import LifecycleEvaluation
from app.modules.dashboard.schemas import PriorityQueueResponse, PriorityQueueItem
from app.modules.dashboard.dashboard_service import enforce_scope_and_get_conditions


DEFAULT_WEIGHTS = {
    "urgency": 0.35,
    "discrepancy": 0.25,
    "trust": 0.20,
    "overdue": 0.20,
}


class PriorityService:
    """Calculates operational priority rankings with explainable weights."""

    @staticmethod
    def compute_priority_queue(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        assigned_office: Optional[str] = None,
        bank_name: Optional[str] = None,
        min_score: float = 0.0,
        page: int = 1,
        page_size: int = 50,
    ) -> PriorityQueueResponse:
        """
        Computes transparent, sorted priority queue for officers and branch heads.
        Weights and assumptions are explicitly disclosed.
        """
        today = date.today()
        base_conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            db=db,
        )

        # Exclude released instruments
        query_conditions = [
            *base_conditions,
            Instrument.status != "RELEASED",
        ]

        # Fetch candidate instruments
        instruments = db.scalars(
            select(Instrument).where(*query_conditions).order_by(Instrument.maturity_date.asc())
        ).all()

        scored_items: List[PriorityQueueItem] = []

        for inst in instruments:
            # 1. Urgency Factor (0 - 100)
            days_to_mat = (inst.maturity_date - today).days
            if days_to_mat <= 0:
                urgency = 100.0
            elif days_to_mat <= 15:
                urgency = 90.0
            elif days_to_mat <= 30:
                urgency = 75.0
            elif days_to_mat <= 60:
                urgency = 50.0
            elif days_to_mat <= 90:
                urgency = 30.0
            else:
                urgency = 10.0

            # 2. Discrepancy Factor (0 - 100)
            open_findings = db.scalars(
                select(ValidationFinding.severity).where(
                    ValidationFinding.instrument_id == inst.id,
                    ValidationFinding.status.in_(["OPEN", "IN_REVIEW"]),
                )
            ).all()

            if "CRITICAL" in open_findings:
                discrepancy = 100.0
            elif "HIGH" in open_findings:
                discrepancy = 75.0
            elif "MEDIUM" in open_findings:
                discrepancy = 50.0
            elif open_findings:
                discrepancy = 25.0
            else:
                discrepancy = 0.0

            # 3. Trust Factor (0 - 100)
            if inst.trust_level == "L0_DECLARED":
                trust = 80.0
            elif inst.trust_level == "L1_DOCUMENT_CONSISTENT":
                trust = 50.0
            elif inst.trust_level == "L2_OFFICER_VERIFIED":
                trust = 25.0
            else:  # L3_BANK_CONFIRMED
                trust = 0.0

            # 4. Overdue Factor (0 - 100)
            latest_eval = db.scalars(
                select(LifecycleEvaluation)
                .where(LifecycleEvaluation.instrument_id == inst.id)
                .order_by(LifecycleEvaluation.evaluation_date.desc())
            ).first()

            if latest_eval:
                if latest_eval.is_escalated:
                    overdue = 100.0
                elif latest_eval.is_overdue:
                    overdue = 80.0
                elif latest_eval.due_condition in ["INSTITUTION_ACTION_DUE", "OFFICER_ACTION_DUE"]:
                    overdue = 50.0
                else:
                    overdue = 0.0
            else:
                overdue = 0.0

            # Weighted composite score
            composite = (
                (DEFAULT_WEIGHTS["urgency"] * urgency)
                + (DEFAULT_WEIGHTS["discrepancy"] * discrepancy)
                + (DEFAULT_WEIGHTS["trust"] * trust)
                + (DEFAULT_WEIGHTS["overdue"] * overdue)
            )
            composite_score = round(composite, 1)

            if composite_score >= min_score:
                scored_items.append(
                    PriorityQueueItem(
                        instrument_id=inst.id,
                        reference_number=inst.reference_number,
                        institution_id=inst.institution_id,
                        institution_name=inst.institution.name if inst.institution else None,
                        bank_name=inst.bank_name,
                        amount=f"{Decimal(inst.amount):.2f}",
                        maturity_date=inst.maturity_date,
                        days_to_maturity=days_to_mat,
                        status=inst.status,
                        trust_level=inst.trust_level,
                        priority_score=composite_score,
                        urgency_factor=urgency,
                        discrepancy_factor=discrepancy,
                        trust_factor=trust,
                        overdue_factor=overdue,
                    )
                )

        # Stable sort: priority_score descending, then maturity_date ascending, then reference_number
        scored_items.sort(key=lambda x: (-x.priority_score, x.maturity_date, x.reference_number))

        total_count = len(scored_items)
        skip = (page - 1) * page_size
        paginated_items = scored_items[skip : skip + page_size]

        return PriorityQueueResponse(
            total_count=total_count,
            page=page,
            page_size=page_size,
            weights_applied=DEFAULT_WEIGHTS,
            items=paginated_items,
        )
