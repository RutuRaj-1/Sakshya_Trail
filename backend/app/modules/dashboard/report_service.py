"""
Report Service (Module 7 — Command Center)
Implements PRD-FR-074: Report dataset construction for operational reports:
- Pending verification report (instruments awaiting L2/L3 verification with age)
- Upcoming maturities report (instruments within window with trust level & renewal status)
- Missing documents report (instruments with missing/unreadable/wrong category items)
- Interventions report (overdue, escalated, disputed, or source-unavailable cases)
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, not_

from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationFinding, ValidationPolicyConfig
from app.modules.verification.models import VerificationRequest
from app.modules.lifecycle.models import LifecycleEvaluation, InstrumentLineage
from app.modules.release.models import ReleaseRequest
from app.modules.dashboard.dashboard_service import enforce_scope_and_get_conditions


class ReportService:
    """Constructs standardized operational report datasets."""

    @staticmethod
    def get_pending_verification_report(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        assigned_office: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Report on instruments and verification requests awaiting L2 or L3 verification."""
        today = date.today()
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            db=db,
        )

        stmt = (
            select(Instrument)
            .where(
                *conditions,
                Instrument.trust_level.in_(["L0_DECLARED", "L1_DOCUMENT_CONSISTENT"]),
                Instrument.status.in_(["REGISTERED", "ACTIVE", "UNDER_SCRUTINY"]),
            )
            .order_by(Instrument.maturity_date.asc())
            .limit(limit)
        )
        instruments = db.scalars(stmt).all()

        rows = []
        for inst in instruments:
            # Check latest verification request
            req = db.scalars(
                select(VerificationRequest)
                .where(VerificationRequest.instrument_id == inst.id)
                .order_by(VerificationRequest.created_at.desc())
            ).first()

            age_days = (today - req.created_at.date()).days if req and req.created_at else None

            rows.append({
                "instrument_id": inst.id,
                "reference_number": inst.reference_number,
                "institution_id": inst.institution_id,
                "institution_name": inst.institution.name if inst.institution else None,
                "bank_name": inst.bank_name,
                "branch": inst.branch,
                "amount": f"{Decimal(inst.amount):.2f}",
                "maturity_date": inst.maturity_date.isoformat(),
                "trust_level": inst.trust_level,
                "verification_status": req.status if req else "NOT_REQUESTED",
                "request_reference": req.reference_code if req else None,
                "request_age_days": age_days,
                "assigned_office": inst.assigned_office,
            })

        return {
            "report_type": "PENDING_VERIFICATION",
            "generated_at": datetime.utcnow().isoformat(),
            "total_records": len(rows),
            "rows": rows,
        }

    @staticmethod
    def get_upcoming_maturities_report(
        db: Session,
        current_user: User,
        window_days: int = 90,
        institution_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        assigned_office: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Report on instruments maturing within monitoring window with trust level & renewal status."""
        today = date.today()
        end_date = today + timedelta(days=window_days)
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            db=db,
        )

        stmt = (
            select(Instrument)
            .where(
                *conditions,
                Instrument.maturity_date >= today,
                Instrument.maturity_date <= end_date,
                Instrument.status != "RELEASED",
            )
            .order_by(Instrument.maturity_date.asc())
            .limit(limit)
        )
        instruments = db.scalars(stmt).all()

        rows = []
        for inst in instruments:
            # Lineage check
            lineage = db.scalars(
                select(InstrumentLineage).where(
                    InstrumentLineage.predecessor_instrument_id == inst.id,
                    InstrumentLineage.relationship_status == "ACTIVE",
                )
            ).first()

            renewal_status = "RENEWAL_LINKED" if lineage else "NO_RENEWAL_RECORDED"

            rows.append({
                "instrument_id": inst.id,
                "reference_number": inst.reference_number,
                "institution_id": inst.institution_id,
                "institution_name": inst.institution.name if inst.institution else None,
                "bank_name": inst.bank_name,
                "amount": f"{Decimal(inst.amount):.2f}",
                "maturity_date": inst.maturity_date.isoformat(),
                "days_to_maturity": (inst.maturity_date - today).days,
                "status": inst.status,
                "trust_level": inst.trust_level,
                "renewal_status": renewal_status,
                "successor_instrument_id": lineage.successor_instrument_id if lineage else None,
                "assigned_office": inst.assigned_office,
            })

        return {
            "report_type": "UPCOMING_MATURITIES",
            "window_days": window_days,
            "generated_at": datetime.utcnow().isoformat(),
            "total_records": len(rows),
            "rows": rows,
        }

    @staticmethod
    def get_missing_documents_report(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Report on cases and instruments with missing, unreadable, or wrong-category documents."""
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            db=db,
        )

        # Findings for document completeness
        stmt = (
            select(ValidationFinding, Instrument)
            .join(Instrument, ValidationFinding.instrument_id == Instrument.id)
            .where(
                *conditions,
                ValidationFinding.category.in_(["DOCUMENT_COMPLETENESS", "DOCUMENT_INTEGRITY"]),
                ValidationFinding.status.in_(["OPEN", "IN_REVIEW"]),
            )
            .order_by(ValidationFinding.created_at.desc())
            .limit(limit)
        )
        findings = db.execute(stmt).all()

        rows = []
        for f, inst in findings:
            rows.append({
                "finding_id": f.id,
                "instrument_id": inst.id,
                "reference_number": inst.reference_number,
                "institution_id": inst.institution_id,
                "institution_name": inst.institution.name if inst.institution else None,
                "category": f.category,
                "severity": f.severity,
                "rule_id": f.rule_id,
                "title": f.title,
                "status": f.status,
                "detected_at": f.created_at.isoformat() if f.created_at else None,
            })

        return {
            "report_type": "MISSING_DOCUMENTS",
            "generated_at": datetime.utcnow().isoformat(),
            "total_records": len(rows),
            "rows": rows,
        }

    @staticmethod
    def get_interventions_report(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        assigned_office: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Report on overdue, escalated, disputed, or source-unavailable intervention items."""
        today = date.today()
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            db=db,
        )

        rows = []

        # 1. Overdue/Escalated Lifecycle cases
        eval_stmt = (
            select(LifecycleEvaluation, Instrument)
            .join(Instrument, LifecycleEvaluation.instrument_id == Instrument.id)
            .where(
                *conditions,
                or_(
                    LifecycleEvaluation.is_overdue.is_(True),
                    LifecycleEvaluation.is_escalated.is_(True),
                ),
            )
            .limit(limit)
        )
        for ev, inst in db.execute(eval_stmt).all():
            rows.append({
                "case_type": "LIFECYCLE_OVERDUE_ESCALATION",
                "instrument_id": inst.id,
                "reference_number": inst.reference_number,
                "institution_id": inst.institution_id,
                "issue_description": f"Lifecycle condition: {ev.due_condition}; Escalated: {ev.is_escalated}",
                "assigned_office": inst.assigned_office,
                "escalation_role": ev.escalation_role,
            })

        # 2. Source-unavailable or failed verification
        verif_stmt = (
            select(VerificationRequest, Instrument)
            .join(Instrument, VerificationRequest.instrument_id == Instrument.id)
            .where(
                *conditions,
                VerificationRequest.status.in_(["SOURCE_UNAVAILABLE", "TIMEOUT", "FAILED", "ERROR"]),
            )
            .limit(limit)
        )
        for vr, inst in db.execute(verif_stmt).all():
            rows.append({
                "case_type": "VERIFICATION_SOURCE_UNAVAILABLE",
                "instrument_id": inst.id,
                "reference_number": inst.reference_number,
                "institution_id": inst.institution_id,
                "issue_description": f"Verification code {vr.reference_code} status: {vr.status}; Channel: {vr.channel}",
                "assigned_office": inst.assigned_office,
                "escalation_role": "SCRUTINY_OFFICER",
            })

        return {
            "report_type": "INTERVENTIONS",
            "generated_at": datetime.utcnow().isoformat(),
            "total_records": len(rows),
            "rows": rows[:limit],
        }
