"""
Search Service (Module 7 — Command Center)
Implements PRD-FR-071: Role-scoped search, shared filters, allowlisted sorting and pagination.
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_, and_, desc, asc

from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.dashboard.dashboard_service import enforce_scope_and_get_conditions

ALLOWLISTED_SORT_FIELDS = {
    "maturity_date": Instrument.maturity_date,
    "issue_date": Instrument.issue_date,
    "amount": Instrument.amount,
    "reference_number": Instrument.reference_number,
    "created_at": Instrument.created_at,
    "status": Instrument.status,
    "trust_level": Instrument.trust_level,
    "bank_name": Instrument.bank_name,
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
        sort_by: str = "maturity_date",
        sort_order: str = "asc",
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Executes role-scoped parameterized instrument query with filtering, sorting, and pagination.
        """
        # Cap limit to prevent unbounded memory allocation
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
                    Instrument.branch.ilike(kw),
                    Instrument.institution.has(Institution.name.ilike(kw)),
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

        # Count query
        count_stmt = select(func.count(Instrument.id)).where(*conditions)
        total_count = db.scalar(count_stmt) or 0

        # Sorting
        sort_column = ALLOWLISTED_SORT_FIELDS.get(sort_by, Instrument.maturity_date)
        order_fn = desc if sort_order.lower() == "desc" else asc

        stmt = (
            select(Instrument)
            .where(*conditions)
            .order_by(order_fn(sort_column), Instrument.id.asc())
            .offset(clamped_skip)
            .limit(clamped_limit)
        )

        records = db.scalars(stmt).all()

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
                    "currency": inst.currency,
                    "issue_date": inst.issue_date.isoformat(),
                    "maturity_date": inst.maturity_date.isoformat(),
                    "status": inst.status,
                    "trust_level": inst.trust_level,
                    "assigned_office": inst.assigned_office,
                    "created_at": inst.created_at.isoformat() if inst.created_at else None,
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
