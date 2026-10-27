"""
Dashboard & Command Center Service Layer (Module 7 Foundation)
Implements role-scoped aggregation logic and metric computations:
- Instrument status counts (Category A)
- Maturity window query and drilldown (Category B)
- Overdue and escalated work (Category C)
- Verification queue and source-unavailable tracking (Category D)
- Document completeness aggregation (Category E)
- Release / refund blockers (Category F)
- Month-wise maturity load (Category G)
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, not_, extract

from app.core.security import ROLE_INSTITUTION_USER, ROLE_AUDITOR
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationFinding, ValidationPolicyConfig
from app.modules.verification.models import VerificationRequest, VerificationResponse
from app.modules.lifecycle.models import (
    LifecycleEvaluation,
    LifecyclePolicy,
    InstrumentLineage,
)
from app.modules.release.models import (
    ReleaseRequest,
    ReadinessAssessment,
    ReadinessCheckResult,
    ReleaseChecklistProfile,
)
from app.modules.release.enums import (
    ReleaseWorkflowStatus,
    ReadinessAssessmentOutcome,
    CheckResultStatus,
)
from app.modules.dashboard.schemas import (
    StatusCountsResponse,
    MaturityWindowResponse,
    MaturityWindowRecordItem,
    OverdueEscalatedResponse,
    OverdueItem,
    VerificationQueueResponse,
    VerificationQueueItem,
    DocumentCompletenessResponse,
    ReleaseBlockersResponse,
    ReleaseBlockerCaseItem,
    MonthWiseMaturityLoadResponse,
    MonthWiseMaturityPoint,
    CommandCenterOverviewResponse,
)
from app.modules.audit.service import log_audit_event


def enforce_scope_and_get_conditions(
    current_user: User,
    requested_institution_id: Optional[str] = None,
    assigned_office: Optional[str] = None,
    bank_name: Optional[str] = None,
    status_filter: Optional[str] = None,
    trust_level_filter: Optional[str] = None,
    db: Optional[Session] = None,
) -> List[Any]:
    """
    Applies security boundaries before database query execution.
    - An INSTITUTION_USER can ONLY query their assigned institution.
    - Attempting cross-tenant access triggers 403 Forbidden and audit log.
    - Bureau roles can optionally filter by institution, office, or bank.
    """
    conditions: List[Any] = []

    if current_user.role == ROLE_INSTITUTION_USER:
        if not current_user.institution_id:
            # Unassigned institution user has no data access
            conditions.append(Instrument.institution_id == "__NONE__")
            return conditions

        if requested_institution_id and requested_institution_id != current_user.institution_id:
            if db:
                log_audit_event(
                    db=db,
                    action="UNAUTHORIZED_CROSS_TENANT_DASHBOARD_ACCESS",
                    entity_type="INSTITUTION",
                    entity_id=requested_institution_id,
                    actor_email=current_user.email,
                    actor_user_id=current_user.id,
                    actor_role=current_user.role,
                    outcome="FAILURE",
                    metadata={
                        "attempted_institution_id": requested_institution_id,
                        "user_institution_id": current_user.institution_id,
                    },
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot query metrics for another institution.",
            )
        conditions.append(Instrument.institution_id == current_user.institution_id)
    else:
        # Bureau / Admin / Auditor roles
        if requested_institution_id:
            conditions.append(Instrument.institution_id == requested_institution_id)

    if assigned_office:
        conditions.append(Instrument.assigned_office == assigned_office)
    if bank_name:
        conditions.append(Instrument.bank_name.ilike(f"%{bank_name}%"))
    if status_filter:
        conditions.append(Instrument.status == status_filter)
    if trust_level_filter:
        conditions.append(Instrument.trust_level == trust_level_filter)

    return conditions


class DashboardService:
    """Core aggregation and metrics computation engine."""

    @staticmethod
    def compute_status_counts(
        db: Session,
        current_user: User,
        window_days: int = 90,
        institution_id: Optional[str] = None,
        assigned_office: Optional[str] = None,
        bank_name: Optional[str] = None,
        trust_level: Optional[str] = None,
    ) -> StatusCountsResponse:
        """
        Category A: Instrument status counts (PRD-FR-070a).
        Computes deterministic status breakdown: Active, Expiring soon, Matured, Renewed, Released, Pending.
        Does not conflate administrative status with trust level, verification state, or release state.
        """
        from app.modules.lifecycle.clock import get_business_date
        today = get_business_date()
        expiring_threshold = today + timedelta(days=window_days)

        base_conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            trust_level_filter=trust_level,
            db=db,
        )

        # 1. Identify renewed predecessor instruments in active lineage edges
        lineage_subq = (
            select(InstrumentLineage.predecessor_instrument_id)
            .where(
                InstrumentLineage.relationship_status == "ACTIVE",
                InstrumentLineage.relationship_type.in_(["RENEWAL", "REPLACEMENT"]),
            )
            .scalar_subquery()
        )

        # Exclude released status from pending/matured/active/expiring calculations
        is_released = Instrument.status == "RELEASED"
        is_renewed = or_(
            Instrument.status.in_(["RENEWED", "RENEWED_SUPERSEDED"]),
            Instrument.id.in_(lineage_subq),
        )
        is_pending = and_(
            Instrument.status.in_(
                ["DRAFT", "SUBMITTED", "UNDER_SCRUTINY", "UNDER_REVIEW", "RETURNED_FOR_CORRECTION"]
            ),
            not_(is_released),
            not_(is_renewed),
        )

        # Released count
        released_stmt = select(func.count(Instrument.id)).where(
            *base_conditions,
            is_released,
        )
        released_count = db.scalar(released_stmt) or 0

        # Renewed count (not released)
        renewed_stmt = select(func.count(Instrument.id)).where(
            *base_conditions,
            is_renewed,
            not_(is_released),
        )
        renewed_count = db.scalar(renewed_stmt) or 0

        # Pending count (draft, submission, scrutiny intake)
        pending_stmt = select(func.count(Instrument.id)).where(
            *base_conditions,
            is_pending,
        )
        pending_count = db.scalar(pending_stmt) or 0

        # Matured count (maturity_date < today, not released, not renewed, not pending)
        matured_stmt = select(func.count(Instrument.id)).where(
            *base_conditions,
            Instrument.maturity_date < today,
            not_(is_released),
            not_(is_renewed),
            not_(is_pending),
        )
        matured_count = db.scalar(matured_stmt) or 0

        # Expiring soon count (today <= maturity_date <= today + window_days, registered/active, not renewed/released)
        expiring_stmt = select(func.count(Instrument.id)).where(
            *base_conditions,
            Instrument.maturity_date >= today,
            Instrument.maturity_date <= expiring_threshold,
            Instrument.status.in_(["ACTIVE", "REGISTERED", "VERIFIED"]),
            not_(is_released),
            not_(is_renewed),
        )
        expiring_soon_count = db.scalar(expiring_stmt) or 0

        # Active count (maturity_date > today + window_days, registered/active, not renewed/released)
        active_stmt = select(func.count(Instrument.id)).where(
            *base_conditions,
            Instrument.maturity_date > expiring_threshold,
            Instrument.status.in_(["ACTIVE", "REGISTERED", "VERIFIED"]),
            not_(is_released),
            not_(is_renewed),
        )
        active_count = db.scalar(active_stmt) or 0

        # Total instruments and deposit value
        total_stmt = select(
            func.count(Instrument.id),
            func.coalesce(func.sum(Instrument.amount), Decimal("0.00")),
        ).where(*base_conditions)
        total_instruments, total_value = db.execute(total_stmt).one()
        total_instruments = total_instruments or 0
        total_deposit_value = f"{Decimal(total_value):.2f}"

        return StatusCountsResponse(
            active_count=active_count,
            expiring_soon_count=expiring_soon_count,
            matured_count=matured_count,
            renewed_count=renewed_count,
            released_count=released_count,
            pending_count=pending_count,
            total_instruments=total_instruments,
            total_deposit_value=total_deposit_value,
            window_days=window_days,
            date_basis="Asia/Kolkata calendar date",
            metadata={
                "as_of_date": today.isoformat(),
                "expiring_threshold_date": expiring_threshold.isoformat(),
            },
        )

    @staticmethod
    def compute_maturity_window(
        db: Session,
        current_user: User,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        window_days: Optional[int] = None,
        institution_id: Optional[str] = None,
        assigned_office: Optional[str] = None,
        bank_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> MaturityWindowResponse:
        """
        Category B: Maturity window metrics and drilldown (PRD-FR-070b).
        Aggregates instruments maturing within selectable, inclusive date window.
        """
        from app.modules.lifecycle.clock import get_business_date
        today = get_business_date()
        eff_start = start_date or today
        if end_date:
            eff_end = end_date
        elif window_days:
            eff_end = eff_start + timedelta(days=window_days)
        else:
            eff_end = eff_start + timedelta(days=90)

        if eff_start > eff_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date range: start_date cannot be after end_date.",
            )

        base_conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            db=db,
        )

        window_conditions = [
            *base_conditions,
            Instrument.maturity_date >= eff_start,
            Instrument.maturity_date <= eff_end,
            Instrument.status != "RELEASED",
        ]

        # Total count & volume
        totals_stmt = select(
            func.count(Instrument.id),
            func.coalesce(func.sum(Instrument.amount), Decimal("0.00")),
        ).where(*window_conditions)
        total_count, total_amt = db.execute(totals_stmt).one()
        total_count = total_count or 0
        total_value = f"{Decimal(total_amt):.2f}"

        # Breakdown by Bank
        bank_stmt = (
            select(Instrument.bank_name, func.count(Instrument.id))
            .where(*window_conditions)
            .group_by(Instrument.bank_name)
        )
        by_bank = {row[0]: row[1] for row in db.execute(bank_stmt).all()}

        # Breakdown by Office
        office_stmt = (
            select(
                func.coalesce(Instrument.assigned_office, "UNASSIGNED"),
                func.count(Instrument.id),
            )
            .where(*window_conditions)
            .group_by(Instrument.assigned_office)
        )
        by_office = {row[0]: row[1] for row in db.execute(office_stmt).all()}

        # Paginated drilldown records
        skip = (page - 1) * page_size
        records_stmt = (
            select(Instrument)
            .where(*window_conditions)
            .order_by(Instrument.maturity_date.asc())
            .offset(skip)
            .limit(page_size)
        )
        instruments = db.scalars(records_stmt).all()

        record_items = []
        for inst in instruments:
            days_to_mat = (inst.maturity_date - today).days
            record_items.append(
                MaturityWindowRecordItem(
                    id=inst.id,
                    reference_number=inst.reference_number,
                    institution_id=inst.institution_id,
                    institution_name=inst.institution.name if inst.institution else None,
                    bank_name=inst.bank_name,
                    branch=inst.branch,
                    amount=f"{Decimal(inst.amount):.2f}",
                    issue_date=inst.issue_date,
                    maturity_date=inst.maturity_date,
                    days_to_maturity=days_to_mat,
                    status=inst.status,
                    trust_level=inst.trust_level,
                    assigned_office=inst.assigned_office,
                )
            )

        return MaturityWindowResponse(
            start_date=eff_start,
            end_date=eff_end,
            total_instruments=total_count,
            total_deposit_value=total_value,
            by_bank=by_bank,
            by_office=by_office,
            page=page,
            page_size=page_size,
            total_records=total_count,
            records=record_items,
        )

    @staticmethod
    def compute_overdue_and_escalated(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        assigned_office: Optional[str] = None,
        limit: int = 50,
    ) -> OverdueEscalatedResponse:
        """
        Category C: Overdue and escalated work (PRD-FR-070c).
        Identifies cases past compliance deadlines or escalated across administrative levels.
        Assignee grouping is only visible to authorized bureau staff.
        """
        today = date.today()
        base_inst_cond = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            db=db,
        )

        # 1. Query overdue/escalated from LifecycleEvaluation
        eval_stmt = (
            select(LifecycleEvaluation, Instrument)
            .join(Instrument, LifecycleEvaluation.instrument_id == Instrument.id)
            .where(
                *base_inst_cond,
                or_(
                    LifecycleEvaluation.is_overdue.is_(True),
                    LifecycleEvaluation.is_escalated.is_(True),
                    LifecycleEvaluation.due_condition.in_(["OVERDUE", "ESCALATED"]),
                ),
            )
            .order_by(LifecycleEvaluation.evaluation_date.desc())
        )
        eval_rows = db.execute(eval_stmt.limit(limit)).all()

        by_office: Dict[str, int] = {}
        by_assignee: Dict[str, int] = {}
        items: List[OverdueItem] = []
        seen_inst_ids = set()

        for eval_rec, inst in eval_rows:
            if inst.id in seen_inst_ids:
                continue
            seen_inst_ids.add(inst.id)

            off = inst.assigned_office or "UNASSIGNED"
            by_office[off] = by_office.get(off, 0) + 1

            due_d = eval_rec.institution_action_due_date or eval_rec.officer_action_due_date
            days_od = (today - due_d).days if due_d and due_d < today else 0

            item = OverdueItem(
                record_id=inst.id,
                record_type="INSTRUMENT",
                reference_number=inst.reference_number,
                institution_id=inst.institution_id,
                institution_name=inst.institution.name if inst.institution else None,
                assigned_office=inst.assigned_office,
                assignee_id=None,
                assignee_name=None,
                due_date=due_d,
                days_overdue=max(0, days_od),
                is_escalated=eval_rec.is_escalated,
                escalation_role=eval_rec.escalation_role,
                due_condition=eval_rec.due_condition,
            )
            items.append(item)

        # 2. Release Requests past deadline or returned for correction
        rel_cond = []
        if current_user.role == ROLE_INSTITUTION_USER:
            rel_cond.append(ReleaseRequest.institution_id == current_user.institution_id)
        elif institution_id:
            rel_cond.append(ReleaseRequest.institution_id == institution_id)
        if assigned_office:
            rel_cond.append(ReleaseRequest.assigned_office == assigned_office)

        rel_cond.append(
            ReleaseRequest.workflow_status.in_(
                [
                    ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value,
                    ReleaseWorkflowStatus.UNDER_REVIEW.value,
                ]
            )
        )

        rel_cases = db.scalars(select(ReleaseRequest).where(*rel_cond).limit(limit)).all()
        for c in rel_cases:
            off = c.assigned_office or "UNASSIGNED"
            by_office[off] = by_office.get(off, 0) + 1

            if c.assigned_reviewer_id:
                by_assignee[c.assigned_reviewer_id] = by_assignee.get(c.assigned_reviewer_id, 0) + 1

            sub_date = c.submitted_at.date() if c.submitted_at else c.created_at.date()
            days_od = (today - sub_date).days

            items.append(
                OverdueItem(
                    record_id=c.id,
                    record_type="RELEASE_CASE",
                    reference_number=c.case_number,
                    institution_id=c.institution_id,
                    institution_name=c.institution.name if c.institution else None,
                    assigned_office=c.assigned_office,
                    assignee_id=c.assigned_reviewer_id,
                    assignee_name=c.assigned_reviewer.full_name if c.assigned_reviewer else None,
                    due_date=sub_date,
                    days_overdue=days_od,
                    is_escalated=c.workflow_status == ReleaseWorkflowStatus.RETURNED_FOR_CORRECTION.value,
                    escalation_role="SCRUTINY_OFFICER",
                    due_condition=c.workflow_status,
                )
            )

        total_overdue = len(items)
        total_escalated = sum(1 for it in items if it.is_escalated)

        # Restrict assignee details for institution users
        assignee_breakdown = by_assignee if current_user.role != ROLE_INSTITUTION_USER else None

        return OverdueEscalatedResponse(
            total_overdue=total_overdue,
            total_escalated=total_escalated,
            by_office=by_office,
            by_assignee=assignee_breakdown,
            records=items[:limit],
        )

    @staticmethod
    def compute_verification_queue(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        limit: int = 50,
    ) -> VerificationQueueResponse:
        """
        Category D: Verification queue and channel health (PRD-FR-070d).
        Outstanding requests, aging metrics, and source-unavailable cases.
        """
        today = date.today()
        inst_cond = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            bank_name=bank_name,
            db=db,
        )

        # Base query joined with Instrument for tenant scoping
        stmt = (
            select(VerificationRequest, Instrument)
            .join(Instrument, VerificationRequest.instrument_id == Instrument.id)
            .where(*inst_cond)
        )

        all_requests = db.execute(stmt).all()

        outstanding_items: List[VerificationQueueItem] = []
        source_unavailable_count = 0
        failed_count = 0
        age_distribution = {"<7d": 0, "7-14d": 0, "15-30d": 0, ">30d": 0}
        total_age_days = 0

        for req, inst in all_requests:
            req_created_d = req.created_at.date() if req.created_at else today
            age_days = max(0, (today - req_created_d).days)

            is_src_unavail = bool(
                req.status in ["SOURCE_UNAVAILABLE", "TIMEOUT"]
                or bool(req.error_details and "source_unavailable" in req.error_details.lower())
            )
            is_failed = bool(req.status in ["FAILED", "ERROR"])

            if is_src_unavail:
                source_unavailable_count += 1
            if is_failed:
                failed_count += 1

            if req.status in ["PENDING", "REQUESTED", "SENT", "DRAFT"]:
                total_age_days += age_days
                if age_days < 7:
                    age_distribution["<7d"] += 1
                elif age_days <= 14:
                    age_distribution["7-14d"] += 1
                elif age_days <= 30:
                    age_distribution["15-30d"] += 1
                else:
                    age_distribution[">30d"] += 1

                item = VerificationQueueItem(
                    request_id=req.id,
                    reference_code=req.reference_code,
                    instrument_id=inst.id,
                    instrument_reference=inst.reference_number,
                    institution_id=inst.institution_id,
                    institution_name=inst.institution.name if inst.institution else None,
                    bank_name=inst.bank_name,
                    channel=req.channel,
                    status=req.status,
                    created_at=req.created_at,
                    age_days=age_days,
                    attempt_count=req.attempt_count,
                    is_source_unavailable=is_src_unavail,
                )
                outstanding_items.append(item)

        total_outstanding = len(outstanding_items)
        avg_age = round(total_age_days / total_outstanding, 1) if total_outstanding > 0 else 0.0

        # Sort outstanding items by age descending (oldest first)
        outstanding_items.sort(key=lambda x: x.age_days, reverse=True)

        return VerificationQueueResponse(
            total_outstanding=total_outstanding,
            average_age_days=avg_age,
            age_distribution=age_distribution,
            source_unavailable_count=source_unavailable_count,
            failed_count=failed_count,
            records=outstanding_items[:limit],
        )

    @staticmethod
    def compute_document_completeness(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
    ) -> DocumentCompletenessResponse:
        """
        Category E: Document completeness checklist outcomes (PRD-FR-070e).
        Aggregates present, missing, unreadable, wrong category, and awaiting confirmation.
        If policy is absent, explicitly reports unconfigured policy state rather than misleading 0.
        """
        inst_cond = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            db=db,
        )

        # 1. Check for active ValidationPolicyConfig for REQUIRED_DOCUMENT_CATEGORIES
        pol_stmt = select(ValidationPolicyConfig).where(
            ValidationPolicyConfig.config_key == "REQUIRED_DOCUMENT_CATEGORIES",
            ValidationPolicyConfig.is_active.is_(True),
        )
        if current_user.role == ROLE_INSTITUTION_USER and current_user.institution_id:
            pol_stmt = pol_stmt.where(
                or_(
                    ValidationPolicyConfig.institution_id == current_user.institution_id,
                    ValidationPolicyConfig.institution_id.is_(None),
                )
            ).order_by(ValidationPolicyConfig.institution_id.desc().nullslast())
        policy = db.scalars(pol_stmt).first()

        policy_configured = policy is not None
        policy_version = policy.policy_version if policy else None
        policy_msg = None if policy_configured else "POLICY_UNCONFIGURED: No active REQUIRED_DOCUMENT_CATEGORIES policy in effect."

        # 2. Present documents & Awaiting confirmation & Unreadable versions
        doc_stmt = (
            select(DocumentVersion.processing_status, func.count(DocumentVersion.id))
            .join(Document, DocumentVersion.document_id == Document.id)
            .join(Instrument, Document.instrument_id == Instrument.id)
            .where(*inst_cond)
            .group_by(DocumentVersion.processing_status)
        )
        status_counts = {r[0]: r[1] for r in db.execute(doc_stmt).all()}

        present_count = status_counts.get("CLEAN", 0) + status_counts.get("SCAN_BYPASSED_DEVELOPMENT", 0)
        unreadable_count = status_counts.get("PROCESSING_FAILED", 0) + status_counts.get("INFECTED", 0)
        awaiting_count = status_counts.get("PENDING_SCAN", 0)

        # 3. Discrepancies / Wrong category from ValidationFindings
        finding_stmt = (
            select(func.count(ValidationFinding.id))
            .join(Instrument, ValidationFinding.instrument_id == Instrument.id)
            .where(
                *inst_cond,
                ValidationFinding.category.in_(["DOCUMENT_COMPLETENESS", "DOCUMENT_INTEGRITY"]),
                ValidationFinding.status.in_(["OPEN", "IN_REVIEW"]),
            )
        )
        wrong_cat_count = db.scalar(finding_stmt) or 0

        # 4. Missing required document categories
        missing_count = 0
        missing_cat_breakdown: Dict[str, int] = {}

        if policy_configured and policy:
            req_cats = policy.parsed_value if isinstance(policy.parsed_value, list) else ["FDR_COPY"]
            # For each instrument in scope, check if any required category is missing
            instruments = db.scalars(select(Instrument).where(*inst_cond)).all()
            for inst in instruments:
                inst_doc_cats = {
                    d.category
                    for d in inst.institution.instruments
                    if d.id == inst.id
                } if inst.institution else set()
                # Query actual docs for instrument
                doc_cats = set(
                    db.scalars(
                        select(Document.category).where(
                            Document.instrument_id == inst.id,
                            Document.status == "ACTIVE",
                        )
                    ).all()
                )
                for rc in req_cats:
                    if rc not in doc_cats:
                        missing_count += 1
                        missing_cat_breakdown[rc] = missing_cat_breakdown.get(rc, 0) + 1

        return DocumentCompletenessResponse(
            policy_configured=policy_configured,
            policy_version=policy_version,
            policy_status_message=policy_msg,
            present_count=present_count,
            missing_count=missing_count,
            unreadable_count=unreadable_count,
            wrong_category_count=wrong_cat_count,
            awaiting_confirmation_count=awaiting_count,
            missing_categories_breakdown=missing_cat_breakdown,
        )

    @staticmethod
    def compute_release_blockers(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        case_type: Optional[str] = None,
        limit: int = 50,
    ) -> ReleaseBlockersResponse:
        """
        Category F: Release / refund blockers (PRD-FR-070f).
        Counts cases with unmet mandatory checklist items per Module 6 Release Gate engine.
        Does NOT implement a second inconsistent engine; aggregates existing readiness results.
        """
        rel_cond = []
        if current_user.role == ROLE_INSTITUTION_USER:
            rel_cond.append(ReleaseRequest.institution_id == current_user.institution_id)
        elif institution_id:
            rel_cond.append(ReleaseRequest.institution_id == institution_id)

        if case_type:
            rel_cond.append(ReleaseRequest.case_type == case_type)

        # Active cases only
        rel_cond.append(
            ReleaseRequest.workflow_status.notin_(
                [
                    ReleaseWorkflowStatus.COMPLETED.value,
                    ReleaseWorkflowStatus.CLOSED.value,
                    ReleaseWorkflowStatus.CANCELLED.value,
                    ReleaseWorkflowStatus.REJECTED.value,
                ]
            )
        )

        active_cases = db.scalars(select(ReleaseRequest).where(*rel_cond)).all()
        total_active = len(active_cases)

        # Verify whether checklist profiles are configured
        profile_count = db.scalar(
            select(func.count(ReleaseChecklistProfile.id)).where(
                ReleaseChecklistProfile.status == "ACTIVE"
            )
        ) or 0
        policy_configured = profile_count > 0

        blocked_count = 0
        ready_count = 0
        unmet_mandatory_total = 0
        blockers_by_type: Dict[str, int] = {}
        blocked_case_items: List[ReleaseBlockerCaseItem] = []

        for req in active_cases:
            # Check latest assessment
            latest_assessment = (
                db.scalars(
                    select(ReadinessAssessment)
                    .where(ReadinessAssessment.release_request_id == req.id)
                    .order_by(ReadinessAssessment.evaluated_at.desc())
                ).first()
            )

            if not latest_assessment:
                # No assessment yet evaluated
                continue

            if (
                latest_assessment.assessment_outcome == ReadinessAssessmentOutcome.BLOCKED.value
                or latest_assessment.blockers_count > 0
            ):
                blocked_count += 1
                unmet_mandatory_total += latest_assessment.blockers_count

                # Unmet items
                check_results = db.scalars(
                    select(ReadinessCheckResult).where(
                        ReadinessCheckResult.assessment_id == latest_assessment.id,
                        ReadinessCheckResult.is_mandatory_blocker.is_(True),
                        ReadinessCheckResult.status != CheckResultStatus.SATISFIED.value,
                    )
                ).all()

                item_codes = []
                for cr in check_results:
                    item_codes.append(cr.item_code)
                    src_mod = cr.source_module or "GENERAL"
                    blockers_by_type[src_mod] = blockers_by_type.get(src_mod, 0) + 1

                blocked_case_items.append(
                    ReleaseBlockerCaseItem(
                        case_id=req.id,
                        case_number=req.case_number,
                        instrument_id=req.instrument_id,
                        instrument_reference=req.instrument.reference_number if req.instrument else req.instrument_id,
                        institution_id=req.institution_id,
                        institution_name=req.institution.name if req.institution else None,
                        case_type=req.case_type,
                        workflow_status=req.workflow_status,
                        blockers_count=latest_assessment.blockers_count,
                        unsatisfied_item_codes=item_codes,
                        latest_assessment_outcome=latest_assessment.assessment_outcome,
                    )
                )
            elif latest_assessment.assessment_outcome == ReadinessAssessmentOutcome.READY_FOR_APPROVAL.value:
                ready_count += 1

        return ReleaseBlockersResponse(
            policy_configured=policy_configured,
            policy_version=1 if policy_configured else None,
            total_active_release_requests=total_active,
            blocked_requests_count=blocked_count,
            ready_requests_count=ready_count,
            unmet_mandatory_items_count=unmet_mandatory_total,
            blockers_by_requirement_type=blockers_by_type,
            cases=blocked_case_items[:limit],
        )

    @staticmethod
    def compute_month_wise_maturity_load(
        db: Session,
        current_user: User,
        calendar_year: Optional[int] = None,
        institution_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        assigned_office: Optional[str] = None,
    ) -> MonthWiseMaturityLoadResponse:
        """
        Category G: Month-wise maturity load (PRD-FR-076).
        Deterministic calendar aggregation of instrument counts and total amounts.
        Not a prediction or financial forecast.
        """
        target_year = calendar_year or date.today().year

        base_conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            db=db,
        )

        load_conditions = [
            *base_conditions,
            extract("year", Instrument.maturity_date) == target_year,
            Instrument.status != "RELEASED",
        ]

        # Deterministic SQL group by year and month
        stmt = (
            select(
                extract("month", Instrument.maturity_date).label("mo"),
                func.count(Instrument.id).label("cnt"),
                func.coalesce(func.sum(Instrument.amount), Decimal("0.00")).label("amt"),
            )
            .where(*load_conditions)
            .group_by(extract("month", Instrument.maturity_date))
            .order_by("mo")
        )

        rows = db.execute(stmt).all()
        month_map = {int(r[0]): (int(r[1]), Decimal(r[2])) for r in rows if r[0] is not None}

        points: List[MonthWiseMaturityPoint] = []
        grand_total_instruments = 0
        grand_total_amount = Decimal("0.00")

        # Generate all 12 calendar months deterministically
        for m in range(1, 13):
            cnt, amt = month_map.get(m, (0, Decimal("0.00")))
            points.append(
                MonthWiseMaturityPoint(
                    year=target_year,
                    month=m,
                    month_label=f"{target_year}-{m:02d}",
                    instrument_count=cnt,
                    total_amount=f"{amt:.2f}",
                )
            )
            grand_total_instruments += cnt
            grand_total_amount += amt

        return MonthWiseMaturityLoadResponse(
            calendar_year=target_year,
            points=points,
            grand_total_instruments=grand_total_instruments,
            grand_total_amount=f"{grand_total_amount:.2f}",
        )

    @staticmethod
    def get_command_center_overview(
        db: Session,
        current_user: User,
        window_days: int = 90,
    ) -> CommandCenterOverviewResponse:
        """
        Consolidated Command Center Overview for executive & operational cockpits.
        """
        status_counts = DashboardService.compute_status_counts(
            db=db, current_user=current_user, window_days=window_days
        )
        maturity_window = DashboardService.compute_maturity_window(
            db=db, current_user=current_user, window_days=window_days, page_size=10
        )
        overdue_escalated = DashboardService.compute_overdue_and_escalated(
            db=db, current_user=current_user, limit=10
        )
        verification_queue = DashboardService.compute_verification_queue(
            db=db, current_user=current_user, limit=10
        )
        doc_completeness = DashboardService.compute_document_completeness(
            db=db, current_user=current_user
        )
        release_blockers = DashboardService.compute_release_blockers(
            db=db, current_user=current_user, limit=10
        )
        maturity_load = DashboardService.compute_month_wise_maturity_load(
            db=db, current_user=current_user
        )

        scope_desc = (
            f"Institution-Scoped (ID: {current_user.institution_id})"
            if current_user.role == ROLE_INSTITUTION_USER
            else f"Bureau Jurisdiction Scope ({current_user.role})"
        )

        return CommandCenterOverviewResponse(
            generated_at=datetime.now(timezone.utc),
            user_role=current_user.role,
            scope_description=scope_desc,
            status_counts=status_counts,
            maturity_window=maturity_window,
            overdue_escalated=overdue_escalated,
            verification_queue=verification_queue,
            document_completeness=doc_completeness,
            release_blockers=release_blockers,
            maturity_load=maturity_load,
        )
