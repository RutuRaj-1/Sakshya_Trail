"""
Dashboard Module - Versioned API Endpoints
Provides scoped executive and operational summary metrics for Module 1.
"""
from datetime import date, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import get_db
from app.modules.auth.dependencies import get_current_active_user
from app.modules.auth.models import User
from app.core.security import ROLE_INSTITUTION_USER
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.dashboard.schemas import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["Module 1 Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    """
    Returns scoped operational metrics for the Module 1 dashboard.
    - INSTITUTION_USER receives counts restricted exclusively to their assigned institution.
    - Authorized bureau roles receive global bureau-wide counts.
    """
    today = date.today()
    approaching_date = today + timedelta(days=90)

    # 1. Scope Determination
    is_inst_user = current_user.role == ROLE_INSTITUTION_USER
    user_inst_id = current_user.institution_id if is_inst_user else None

    # 2. Institution Counts
    if is_inst_user:
        if user_inst_id:
            inst = db.get(Institution, user_inst_id)
            if inst and inst.is_active:
                total_active_institutions = 1
                total_inactive_institutions = 0
            elif inst and not inst.is_active:
                total_active_institutions = 0
                total_inactive_institutions = 1
            else:
                total_active_institutions = 0
                total_inactive_institutions = 0
        else:
            total_active_institutions = 0
            total_inactive_institutions = 0
    else:
        total_active_institutions = db.scalar(
            select(func.count(Institution.id)).where(Institution.is_active.is_(True))
        ) or 0
        total_inactive_institutions = db.scalar(
            select(func.count(Institution.id)).where(Institution.is_active.is_(False))
        ) or 0

    # 3. Instrument Conditions
    inst_conditions = []
    if is_inst_user:
        inst_conditions.append(Instrument.institution_id == user_inst_id)

    # Total instruments & Total value
    stmt_totals = select(
        func.count(Instrument.id),
        func.coalesce(func.sum(Instrument.amount), Decimal("0.00")),
    )
    if inst_conditions:
        stmt_totals = stmt_totals.where(*inst_conditions)

    total_instruments, total_value = db.execute(stmt_totals).one()
    total_instruments = total_instruments or 0
    total_deposit_value = f"{Decimal(total_value):.2f}"

    # Status breakdown
    stmt_status = select(Instrument.status, func.count(Instrument.id))
    if inst_conditions:
        stmt_status = stmt_status.where(*inst_conditions)
    stmt_status = stmt_status.group_by(Instrument.status)
    status_rows = db.execute(stmt_status).all()
    instruments_by_status = {row[0]: row[1] for row in status_rows}

    # Ensure baseline status keys exist
    for default_status in ("DRAFT", "REGISTERED"):
        if default_status not in instruments_by_status:
            instruments_by_status[default_status] = 0

    # Trust level breakdown
    stmt_trust = select(Instrument.trust_level, func.count(Instrument.id))
    if inst_conditions:
        stmt_trust = stmt_trust.where(*inst_conditions)
    stmt_trust = stmt_trust.group_by(Instrument.trust_level)
    trust_rows = db.execute(stmt_trust).all()
    instruments_by_trust_level = {row[0]: row[1] for row in trust_rows}

    for default_trust in ("L0_DECLARED", "L1_DOCUMENT_CONSISTENT", "L2_OFFICER_VERIFIED", "L3_BANK_CONFIRMED"):
        if default_trust not in instruments_by_trust_level:
            instruments_by_trust_level[default_trust] = 0

    # Approaching maturity (0 <= maturity_date - today <= 90 days)
    stmt_approaching = select(func.count(Instrument.id)).where(
        Instrument.maturity_date >= today,
        Instrument.maturity_date <= approaching_date,
    )
    if inst_conditions:
        stmt_approaching = stmt_approaching.where(*inst_conditions)
    instruments_approaching_maturity = db.scalar(stmt_approaching) or 0

    return DashboardSummaryResponse(
        total_active_institutions=total_active_institutions,
        total_inactive_institutions=total_inactive_institutions,
        total_instruments=total_instruments,
        total_deposit_value=total_deposit_value,
        instruments_by_status=instruments_by_status,
        instruments_by_trust_level=instruments_by_trust_level,
        instruments_approaching_maturity=instruments_approaching_maturity,
    )
