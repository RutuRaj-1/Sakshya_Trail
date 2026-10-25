"""
Search Service (Module 7 — Command Center)
Implements PRD-FR-071: Role-scoped search, shared filters, allowlisted sorting,
discrepancy status filtering, and dual support for Instruments and Release Cases.
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, desc, asc

from app.common.exceptions import AppException
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.validation.models import ValidationFinding
from app.modules.verification.models import VerificationRequest
from app.modules.release.models import ReleaseRequest, ReadinessAssessment
from app.modules.dashboard.dashboard_service import enforce_scope_and_get_conditions

ALLOWLISTED_INSTRUMENT_SORT_FIELDS = {
    "maturity_date": Instrument.maturity_date,
    "issue_date": Instrument.issue_date,
    "amount": Instrument.amount,
    "reference_number": Instrument.reference_number,
    "created_at": Instrument.created_at,
    "status": Instrument.status,
    "trust_level": Instrument.trust_level,
    "bank_name": Instrument.bank_name,
}

ALLOWLISTED_RELEASE_SORT_FIELDS = {
    "created_at": ReleaseRequest.created_at,
    "case_number": ReleaseRequest.case_number,
    "case_reference": ReleaseRequest.case_number,
    "request_type": ReleaseRequest.request_type,
    "workflow_status": ReleaseRequest.workflow_status,
}


class SearchService:
    """Reusable query service for role-scoped record searches."""

    @staticmethod
    def search_instruments(
        db: Session,
        current_user: User,
        q: Optional[str] = None,
        institution_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        assigned_office: Optional[str] = None,
        status: Optional[str] = None,
        trust_level: Optional[str] = None,
        maturity_from: Optional[date] = None,
        maturity_to: Optional[date] = None,
        issue_from: Optional[date] = None,
        issue_to: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        has_discrepancies: Optional[bool] = None,
        priority_category: Optional[str] = None,
        sort_by: str = "maturity_date",
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Executes role-scoped parameterized instrument query with filtering, sorting, and pagination.
        """
        clamped_limit = min(max(1, limit), 100)
        clamped_skip = max(0, skip)

        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            status_filter=status,
            trust_level_filter=trust_level,
            db=db,
        )

        # Keyword text search across reference, bank, branch, and institution name
        if q and q.strip():
            kw = f"%{q.strip()}%"
            conditions.append(
                or_(
                    Instrument.reference_number.ilike(kw),
                    Instrument.bank_name.ilike(kw),
                    Instrument.institution.has(
                        or_(
                            Institution.legal_name.ilike(kw),
                            Institution.display_name.ilike(kw),
                        )
                    ),
                )
            )

        # Date range filters
        if maturity_from:
            conditions.append(Instrument.maturity_date >= maturity_from)
        if maturity_to:
            conditions.append(Instrument.maturity_date <= maturity_to)
        if issue_from:
            conditions.append(Instrument.issue_date >= issue_from)
        if issue_to:
            conditions.append(Instrument.issue_date <= issue_to)

        # Amount bounds
        if min_amount is not None:
            conditions.append(Instrument.amount >= min_amount)
        if max_amount is not None:
            conditions.append(Instrument.amount <= max_amount)

        # Discrepancy flag filter
        if has_discrepancies is True:
            subq = (
                select(ValidationFinding.instrument_id)
                .where(ValidationFinding.status.in_(["OPEN", "IN_REVIEW", "PENDING_REVIEW"]))
            )
            conditions.append(Instrument.id.in_(subq))
        elif has_discrepancies is False:
            subq = (
                select(ValidationFinding.instrument_id)
                .where(ValidationFinding.status.in_(["OPEN", "IN_REVIEW", "PENDING_REVIEW"]))
            )
            conditions.append(~Instrument.id.in_(subq))

        # Priority / monitoring category filter
        today = date.today()
        if priority_category:
            p_cat = priority_category.upper().strip()
            if p_cat == "EXPIRING_SOON":
                conditions.append(Instrument.maturity_date >= today)
                from datetime import timedelta
                conditions.append(Instrument.maturity_date <= today + timedelta(days=90))
                conditions.append(Instrument.status != "RELEASED")
            elif p_cat == "MATURED":
                conditions.append(Instrument.maturity_date < today)
                conditions.append(Instrument.status != "RELEASED")
            elif p_cat == "ACTIVE":
                conditions.append(Instrument.status.in_(["ACTIVE", "REGISTERED", "VERIFIED"]))

        # Count query
        count_stmt = select(func.count(Instrument.id)).where(*conditions)
        total_count = db.scalar(count_stmt) or 0

        # Sorting
        sort_column = ALLOWLISTED_INSTRUMENT_SORT_FIELDS.get(sort_by, Instrument.maturity_date)
        order_fn = desc if sort_order.lower() == "desc" else asc

        stmt = (
            select(Instrument)
            .where(*conditions)
            .order_by(order_fn(sort_column), Instrument.id.asc())
            .offset(clamped_skip)
            .limit(clamped_limit)
        )

        records = db.scalars(stmt).all()

        # Batch check active discrepancies & pending verification for returned IDs
        inst_ids = [inst.id for inst in records]
        discrepancy_ids = set()
        pending_verif_ids = set()
        if inst_ids:
            disc_q = select(ValidationFinding.instrument_id).where(
                ValidationFinding.instrument_id.in_(inst_ids),
                ValidationFinding.status.in_(["OPEN", "IN_REVIEW", "PENDING_REVIEW"]),
            )
            discrepancy_ids = set(db.scalars(disc_q).all())

            verif_q = select(VerificationRequest.instrument_id).where(
                VerificationRequest.instrument_id.in_(inst_ids),
                VerificationRequest.status.in_(["PENDING", "REQUESTED", "SENT"]),
            )
            pending_verif_ids = set(db.scalars(verif_q).all())

        results = []
        for inst in records:
            results.append(
                {
                    "id": inst.id,
                    "reference_number": inst.reference_number,
                    "institution_id": inst.institution_id,
                    "institution_name": inst.institution.name if inst.institution else None,
                    "bank_name": inst.bank_name,
                    "branch": inst.branch,
                    "amount": f"{Decimal(inst.amount):.2f}",
                    "currency": inst.currency or "INR",
                    "issue_date": inst.issue_date.isoformat(),
                    "maturity_date": inst.maturity_date.isoformat(),
                    "status": inst.status,
                    "trust_level": inst.trust_level,
                    "assigned_office": inst.assigned_office,
                    "created_at": inst.created_at.isoformat() if inst.created_at else None,
                    "has_active_discrepancies": inst.id in discrepancy_ids,
                    "pending_verification": inst.id in pending_verif_ids,
                }
            )

        return {
            "total_count": total_count,
            "skip": clamped_skip,
            "limit": clamped_limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "records": results,
        }

    @staticmethod
    def search_release_cases(
        db: Session,
        current_user: User,
        q: Optional[str] = None,
        institution_id: Optional[str] = None,
        request_type: Optional[str] = None,
        workflow_status: Optional[str] = None,
        readiness_outcome: Optional[str] = None,
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Executes role-scoped parameterized query across Release & Refund cases.
        """
        clamped_limit = min(max(1, limit), 100)
        clamped_skip = max(0, skip)

        conditions = []

        # Tenant isolation
        if current_user.role == "INSTITUTION_USER":
            if not current_user.institution_id:
                raise AppException("Institution user missing institution_id context", status_code=403, code="TENANT_ISOLATION_ERROR")
            conditions.append(ReleaseRequest.institution_id == current_user.institution_id)
        elif institution_id:
            conditions.append(ReleaseRequest.institution_id == institution_id)

        # Filters
        if request_type:
            conditions.append(ReleaseRequest.request_type == request_type.upper().strip())
        if workflow_status:
            conditions.append(ReleaseRequest.workflow_status == workflow_status.upper().strip())

        # Date range
        if created_from:
            conditions.append(ReleaseRequest.created_at >= datetime.combine(created_from, datetime.min.time()))
        if created_to:
            conditions.append(ReleaseRequest.created_at <= datetime.combine(created_to, datetime.max.time()))

        # Keyword text search
        if q and q.strip():
            kw = f"%{q.strip()}%"
            conditions.append(
                or_(
                    ReleaseRequest.case_number.ilike(kw),
                    ReleaseRequest.instrument.has(Instrument.reference_number.ilike(kw)),
                    ReleaseRequest.instrument.has(Instrument.bank_name.ilike(kw)),
                    ReleaseRequest.institution.has(
                        or_(
                            Institution.legal_name.ilike(kw),
                            Institution.display_name.ilike(kw),
                        )
                    ),
                )
            )

        # Count query
        count_stmt = select(func.count(ReleaseRequest.id)).where(*conditions)
        total_count = db.scalar(count_stmt) or 0

        # Sorting
        sort_column = ALLOWLISTED_RELEASE_SORT_FIELDS.get(sort_by, ReleaseRequest.created_at)
        order_fn = desc if sort_order.lower() == "desc" else asc

        stmt = (
            select(ReleaseRequest)
            .where(*conditions)
            .order_by(order_fn(sort_column), ReleaseRequest.id.asc())
            .offset(clamped_skip)
            .limit(clamped_limit)
        )

        records = db.scalars(stmt).all()

        results = []
        for case in records:
            # Latest readiness assessment
            latest_assessment = case.assessments[0] if case.assessments else None

            # Filter by readiness_outcome if specified
            if readiness_outcome and (not latest_assessment or latest_assessment.assessment_outcome != readiness_outcome):
                continue

            results.append(
                {
                    "id": case.id,
                    "case_number": case.case_number,
                    "case_reference": case.case_number,
                    "instrument_id": case.instrument_id,
                    "instrument_reference": case.instrument.reference_number if case.instrument else None,
                    "institution_id": case.institution_id,
                    "institution_name": case.institution.name if case.institution else None,
                    "request_type": case.request_type,
                    "case_type": case.case_type,
                    "workflow_status": case.workflow_status,
                    "readiness_outcome": latest_assessment.assessment_outcome if latest_assessment else "UNASSESSED",
                    "blockers_count": latest_assessment.blockers_count if latest_assessment else 0,
                    "created_at": case.created_at.isoformat() if case.created_at else None,
                }
            )

        return {
            "total_count": total_count,
            "skip": clamped_skip,
            "limit": clamped_limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "records": results,
        }
