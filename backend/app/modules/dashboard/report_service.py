"""
Report Service (Module 7 — Command Center)
Implements PRD-FR-074 & Prompt 4:
Standardized operational report datasets and evidence extraction:
- A. Pending Verification Report
- B. Upcoming Maturities Report
- C. Missing Documents Report
- D. Interventions Report
- E. Audit Evidence Pack
"""
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, not_

from app.common.exceptions import AppException
from app.modules.auth.models import User
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.models import ValidationFinding
from app.modules.verification.models import VerificationRequest, FieldProvenance
from app.modules.lifecycle.models import LifecycleEvaluation, InstrumentLineage
from app.modules.release.models import ReleaseRequest
from app.modules.audit.models import AuditEvent
from app.modules.dashboard.dashboard_service import enforce_scope_and_get_conditions
from app.modules.dashboard.observation_service import ScrutinyObservationService


class ReportService:
    """Constructs standardized, scope-isolated operational report datasets."""

    # --------------------------------------------------------------------------
    # A. Pending Verification Report
    # --------------------------------------------------------------------------
    @staticmethod
    def get_pending_verification_report(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        assigned_office: Optional[str] = None,
        trust_level: Optional[str] = None,
        verification_status: Optional[str] = None,
        limit: int = 500,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        Report on instruments and verification requests awaiting verification.
        Clearly distinguishes simulated verification, timeouts, manual evidence, and pending states.
        """
        today = date.today()
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            db=db,
        )

        if trust_level and trust_level != "ALL":
            conditions.append(Instrument.trust_level == trust_level)

        stmt = (
            select(Instrument)
            .where(
                *conditions,
                Instrument.trust_level.in_(["L0_DECLARED", "L1_DOCUMENT_CONSISTENT", "L2_OFFICER_VERIFIED"]),
                Instrument.status.in_(["REGISTERED", "ACTIVE", "UNDER_SCRUTINY", "LODGED", "DRAFT"]),
            )
            .order_by(Instrument.maturity_date.asc())
        )
        all_instruments = db.scalars(stmt).all()

        rows = []
        for inst in all_instruments:
            # Retrieve latest verification request if present
            latest_req = db.scalars(
                select(VerificationRequest)
                .where(VerificationRequest.instrument_id == inst.id)
                .order_by(VerificationRequest.created_at.desc())
            ).first()

            # Determine verification status and simulation flag
            if latest_req:
                v_status = latest_req.status
                is_sim = (
                    latest_req.channel.upper().startswith("SIMULAT")
                    or latest_req.channel.upper() == "SIMULATED"
                    or (hasattr(latest_req, "adapter_type") and "simulat" in str(getattr(latest_req, "adapter_type", "")).lower())
                )
                req_date = latest_req.created_at.date().isoformat() if latest_req.created_at else None
                req_ref = latest_req.reference_code
                age_days = (today - latest_req.created_at.date()).days if latest_req.created_at else 0
                source_stat = (
                    "SOURCE_UNAVAILABLE" if latest_req.status == "SOURCE_UNAVAILABLE"
                    else "SIMULATED_ADAPTER" if is_sim
                    else latest_req.channel or "BANK_GATEWAY"
                )
                officer_id = getattr(latest_req, "requested_by_user_id", None)
            else:
                v_status = "NOT_REQUESTED"
                is_sim = False
                req_date = None
                req_ref = None
                age_days = (today - inst.issue_date).days if inst.issue_date else None
                source_stat = "UNSUBMITTED"
                officer_id = None

            # Filter by verification_status if specified
            if verification_status and verification_status != "ALL" and v_status != verification_status:
                continue

            # Check open discrepancies
            disc_count = db.scalar(
                select(func.count(ValidationFinding.id)).where(
                    ValidationFinding.instrument_id == inst.id,
                    ValidationFinding.status.in_(["OPEN", "IN_REVIEW"]),
                )
            ) or 0

            officer_user = db.get(User, officer_id) if officer_id else None

            rows.append({
                "instrument_id": inst.id,
                "reference_number": inst.reference_number,
                "institution_id": inst.institution_id,
                "institution_name": inst.institution.display_name if inst.institution else None,
                "bank_name": inst.bank_name,
                "branch": inst.branch,
                "amount": f"{Decimal(inst.amount):.2f}",
                "maturity_date": inst.maturity_date.isoformat(),
                "trust_level": inst.trust_level,
                "verification_status": v_status,
                "source_status": source_stat,
                "request_reference": req_ref,
                "request_date": req_date,
                "pending_age_days": age_days,
                "assigned_office": inst.assigned_office,
                "assigned_officer": officer_user.full_name if officer_user else None,
                "is_simulated": is_sim,
                "has_discrepancies": bool(disc_count > 0),
                "discrepancy_count": disc_count,
                "drill_down_path": f"/instruments/{inst.id}",
            })

        total_records = len(rows)
        clamped_rows = rows[skip : skip + limit]

        return {
            "report_type": "PENDING_VERIFICATION",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": total_records,
            "filters_applied": {
                "institution_id": institution_id,
                "bank_name": bank_name,
                "assigned_office": assigned_office,
                "trust_level": trust_level,
                "verification_status": verification_status,
                "scope_description": f"Role: {current_user.role}",
            },
            "rows": clamped_rows,
        }

    # --------------------------------------------------------------------------
    # B. Upcoming Maturities Report
    # --------------------------------------------------------------------------
    @staticmethod
    def get_upcoming_maturities_report(
        db: Session,
        current_user: User,
        window_days: int = 90,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        institution_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        assigned_office: Optional[str] = None,
        trust_level: Optional[str] = None,
        status: Optional[str] = None,
        renewal_status: Optional[str] = None,
        limit: int = 500,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        Report on instruments maturing within a selected monitoring window.
        Uses exact same date conventions as Command Center maturity monitoring.
        """
        today = date.today()
        if date_from:
            try:
                start_d = date.fromisoformat(date_from)
            except ValueError:
                start_d = today
        else:
            start_d = today

        if date_to:
            try:
                end_d = date.fromisoformat(date_to)
            except ValueError:
                end_d = today + timedelta(days=window_days)
        else:
            end_d = today + timedelta(days=window_days)

        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            db=db,
        )

        conditions.append(Instrument.maturity_date >= start_d)
        conditions.append(Instrument.maturity_date <= end_d)
        conditions.append(Instrument.status != "RELEASED")

        if trust_level and trust_level != "ALL":
            conditions.append(Instrument.trust_level == trust_level)
        if status and status != "ALL":
            conditions.append(Instrument.status == status)

        stmt = select(Instrument).where(*conditions).order_by(Instrument.maturity_date.asc())
        instruments = db.scalars(stmt).all()

        rows = []
        total_val = Decimal("0.00")

        for inst in instruments:
            # Check renewal lineage
            lineage = db.scalars(
                select(InstrumentLineage).where(
                    InstrumentLineage.predecessor_instrument_id == inst.id,
                    InstrumentLineage.relationship_status == "ACTIVE",
                )
            ).first()

            ren_stat = "RENEWAL_LINKED" if lineage else "NO_RENEWAL_RECORDED"
            if renewal_status and renewal_status != "ALL" and ren_stat != renewal_status:
                continue

            amt = Decimal(inst.amount)
            total_val += amt

            rows.append({
                "instrument_id": inst.id,
                "reference_number": inst.reference_number,
                "institution_id": inst.institution_id,
                "institution_name": inst.institution.display_name if inst.institution else None,
                "bank_name": inst.bank_name,
                "branch": inst.branch,
                "amount": f"{amt:.2f}",
                "currency": getattr(inst, "currency", "INR"),
                "issue_date": inst.issue_date.isoformat(),
                "maturity_date": inst.maturity_date.isoformat(),
                "days_to_maturity": (inst.maturity_date - today).days,
                "administrative_status": inst.status,
                "trust_level": inst.trust_level,
                "renewal_status": ren_stat,
                "successor_instrument_id": lineage.successor_instrument_id if lineage else None,
                "assigned_office": inst.assigned_office,
                "assigned_officer": None,
                "drill_down_path": f"/instruments/{inst.id}",
            })

        total_records = len(rows)
        clamped_rows = rows[skip : skip + limit]

        return {
            "report_type": "UPCOMING_MATURITIES",
            "date_basis": "Asia/Kolkata Calendar Date",
            "window_days": (end_d - start_d).days,
            "date_from": start_d.isoformat(),
            "date_to": end_d.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": total_records,
            "total_deposit_value": f"{total_val:.2f}",
            "filters_applied": {
                "institution_id": institution_id,
                "bank_name": bank_name,
                "assigned_office": assigned_office,
                "trust_level": trust_level,
                "status": status,
                "date_from": start_d.isoformat(),
                "date_to": end_d.isoformat(),
                "window_days": window_days,
                "scope_description": f"Role: {current_user.role}",
            },
            "regulatory_notice": "Statutory deposit maturity tracking; maturity date does not equate to release eligibility.",
            "rows": clamped_rows,
        }

    # --------------------------------------------------------------------------
    # C. Missing Documents Report
    # --------------------------------------------------------------------------
    @staticmethod
    def get_missing_documents_report(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        bank_name: Optional[str] = None,
        assigned_office: Optional[str] = None,
        checklist_outcome: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 500,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        Report on instruments whose effective checklist has missing, unreadable, or wrong-category documents.
        """
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            bank_name=bank_name,
            db=db,
        )

        finding_conds = [
            ValidationFinding.category.in_(["DOCUMENT_COMPLETENESS", "DOCUMENT_INTEGRITY", "DOCUMENT_VERIFICATION"]),
            ValidationFinding.status.in_(["OPEN", "IN_REVIEW"]),
        ]

        if severity and severity != "ALL":
            finding_conds.append(ValidationFinding.severity == severity)

        stmt = (
            select(ValidationFinding, Instrument)
            .join(Instrument, ValidationFinding.instrument_id == Instrument.id)
            .where(
                *conditions,
                *finding_conds,
            )
            .order_by(ValidationFinding.created_at.desc())
        )
        findings = db.execute(stmt).all()

        rows = []
        for f, inst in findings:
            # Map outcome based on title/category
            title_lower = f.title.lower() if f.title else ""
            if "missing" in title_lower or "absent" in title_lower:
                outcome = "MISSING"
            elif "unreadable" in title_lower or "ocr" in title_lower:
                outcome = "UNREADABLE"
            elif "category" in title_lower or "wrong" in title_lower:
                outcome = "WRONG_CATEGORY"
            else:
                outcome = "AWAITING_CONFIRMATION"

            if checklist_outcome and checklist_outcome != "ALL" and outcome != checklist_outcome:
                continue

            rows.append({
                "finding_id": f.id,
                "instrument_id": inst.id,
                "reference_number": inst.reference_number,
                "institution_id": inst.institution_id,
                "institution_name": inst.institution.display_name if inst.institution else None,
                "bank_name": inst.bank_name,
                "assigned_office": inst.assigned_office,
                "document_category": getattr(f, "field_name", None) or "FDR_CERTIFICATE",
                "policy_version": getattr(f, "policy_version", 1),
                "checklist_outcome": outcome,
                "severity": f.severity,
                "rule_id": f.rule_id,
                "title": f.title,
                "description": f.description if hasattr(f, "description") else f.title,
                "last_updated_at": f.updated_at.isoformat() if hasattr(f, "updated_at") and f.updated_at else (f.created_at.isoformat() if f.created_at else None),
                "drill_down_path": f"/instruments/{inst.id}",
            })

        total_records = len(rows)
        clamped_rows = rows[skip : skip + limit]

        return {
            "report_type": "MISSING_DOCUMENTS",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": total_records,
            "filters_applied": {
                "institution_id": institution_id,
                "bank_name": bank_name,
                "assigned_office": assigned_office,
                "checklist_outcome": checklist_outcome,
                "severity": severity,
                "scope_description": f"Role: {current_user.role}",
            },
            "rows": clamped_rows,
        }

    # --------------------------------------------------------------------------
    # D. Interventions Report
    # --------------------------------------------------------------------------
    @staticmethod
    def get_interventions_report(
        db: Session,
        current_user: User,
        institution_id: Optional[str] = None,
        assigned_office: Optional[str] = None,
        intervention_type: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 500,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        Report on cases requiring follow-up: overdue compliance tasks, escalation triggers,
        unresolved discrepancies, source-unavailable verification, or release blockers.
        Uses neutral, non-accusatory terminology.
        """
        today = date.today()
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            requested_institution_id=institution_id,
            assigned_office=assigned_office,
            db=db,
        )

        rows = []

        # 1. Overdue and Escalated Lifecycle Cases
        if not intervention_type or intervention_type in ["ALL", "OVERDUE_ESCALATION"]:
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
                .order_by(LifecycleEvaluation.days_to_maturity.asc())
            )
            for ev, inst in db.execute(eval_stmt).all():
                days_over = abs(ev.days_to_maturity) if ev.days_to_maturity < 0 else 0
                sev = "CRITICAL" if ev.is_escalated else ("HIGH" if days_over > 14 else "MEDIUM")
                if severity and severity != "ALL" and sev != severity:
                    continue

                rows.append({
                    "intervention_type": "OVERDUE_ESCALATION",
                    "entity_id": inst.id,
                    "reference_number": inst.reference_number,
                    "institution_id": inst.institution_id,
                    "institution_name": inst.institution.display_name if inst.institution else None,
                    "reason_description": f"Statutory renewal overdue by {days_over} days (Condition: {ev.due_condition})",
                    "severity": sev,
                    "age_days": days_over,
                    "deadline_date": inst.maturity_date.isoformat(),
                    "assigned_office": inst.assigned_office,
                    "assigned_officer": None,
                    "next_appropriate_action": "Issue formal regulatory renewal demand and notify nodal officer",
                    "drill_down_path": f"/instruments/{inst.id}",
                })

        # 2. Source-Unavailable or Failed Electronic Verification
        if not intervention_type or intervention_type in ["ALL", "VERIFICATION_FAILED"]:
            verif_stmt = (
                select(VerificationRequest, Instrument)
                .join(Instrument, VerificationRequest.instrument_id == Instrument.id)
                .where(
                    *conditions,
                    VerificationRequest.status.in_(["SOURCE_UNAVAILABLE", "TIMEOUT", "FAILED", "ERROR"]),
                )
                .order_by(VerificationRequest.created_at.desc())
            )
            for vr, inst in db.execute(verif_stmt).all():
                age_days = (today - vr.created_at.date()).days if vr.created_at else 0
                sev = "HIGH" if vr.status in ["FAILED", "ERROR"] else "MEDIUM"
                if severity and severity != "ALL" and sev != severity:
                    continue

                rows.append({
                    "intervention_type": "VERIFICATION_FAILED",
                    "entity_id": inst.id,
                    "reference_number": inst.reference_number,
                    "institution_id": inst.institution_id,
                    "institution_name": inst.institution.display_name if inst.institution else None,
                    "reason_description": f"Electronic verification {vr.reference_code} returned {vr.status} on channel {vr.channel}",
                    "severity": sev,
                    "age_days": age_days,
                    "deadline_date": None,
                    "assigned_office": inst.assigned_office,
                    "assigned_officer": None,
                    "next_appropriate_action": "Switch to alternate banking channel or dispatch manual verification request",
                    "drill_down_path": f"/instruments/{inst.id}",
                })

        # 3. Unresolved Discrepancies
        if not intervention_type or intervention_type in ["ALL", "DISCREPANCY_FLAG"]:
            disc_stmt = (
                select(ValidationFinding, Instrument)
                .join(Instrument, ValidationFinding.instrument_id == Instrument.id)
                .where(
                    *conditions,
                    ValidationFinding.status.in_(["OPEN", "IN_REVIEW"]),
                )
                .order_by(ValidationFinding.created_at.desc())
            )
            for f, inst in db.execute(disc_stmt).all():
                age_days = (today - f.created_at.date()).days if f.created_at else 0
                sev = f.severity
                if severity and severity != "ALL" and sev != severity:
                    continue

                rows.append({
                    "intervention_type": "DISCREPANCY_FLAG",
                    "entity_id": inst.id,
                    "reference_number": inst.reference_number,
                    "institution_id": inst.institution_id,
                    "institution_name": inst.institution.display_name if inst.institution else None,
                    "reason_description": f"Active discrepancy: {f.title} ({f.rule_id})",
                    "severity": sev,
                    "age_days": age_days,
                    "deadline_date": None,
                    "assigned_office": inst.assigned_office,
                    "assigned_officer": None,
                    "next_appropriate_action": "Scrutiny review in Discrepancy Queue or request clarifying affidavit",
                    "drill_down_path": f"/instruments/{inst.id}",
                })

        # 4. Release Request Blockers
        if not intervention_type or intervention_type in ["ALL", "RELEASE_BLOCKER"]:
            rel_conds = []
            if current_user.role == "INSTITUTION_USER":
                rel_conds.append(ReleaseRequest.institution_id == current_user.institution_id)
            elif institution_id:
                rel_conds.append(ReleaseRequest.institution_id == institution_id)

            rel_stmt = (
                select(ReleaseRequest)
                .where(
                    *rel_conds,
                    ReleaseRequest.workflow_status.in_(["UNDER_SCRUTINY", "SUBMITTED", "COMMITTEE_REVIEW"]),
                )
                .order_by(ReleaseRequest.created_at.desc())
            )
            for case in db.scalars(rel_stmt).all():
                latest_assessment = case.assessments[0] if case.assessments else None
                if latest_assessment and latest_assessment.blockers_count > 0:
                    sev = "HIGH"
                    if severity and severity != "ALL" and sev != severity:
                        continue
                    age_days = (today - case.created_at.date()).days if case.created_at else 0
                    rows.append({
                        "intervention_type": "RELEASE_BLOCKER",
                        "entity_id": case.id,
                        "reference_number": case.case_number,
                        "institution_id": case.institution_id,
                        "institution_name": case.institution.display_name if case.institution else None,
                        "reason_description": f"Release request blocked: {latest_assessment.blockers_count} mandatory checklist criteria unmet",
                        "severity": sev,
                        "age_days": age_days,
                        "deadline_date": None,
                        "assigned_office": case.assigned_office,
                        "assigned_officer": None,
                        "next_appropriate_action": "Review outstanding checklist items on Release Case Desk",
                        "drill_down_path": f"/release/{case.id}",
                    })

        total_records = len(rows)
        clamped_rows = rows[skip : skip + limit]

        return {
            "report_type": "INTERVENTIONS",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": total_records,
            "filters_applied": {
                "institution_id": institution_id,
                "assigned_office": assigned_office,
                "intervention_type": intervention_type,
                "severity": severity,
                "scope_description": f"Role: {current_user.role}",
            },
            "rows": clamped_rows,
        }

    # --------------------------------------------------------------------------
    # E. Audit Evidence Pack
    # --------------------------------------------------------------------------
    @staticmethod
    def get_audit_evidence_pack(
        db: Session,
        current_user: User,
        instrument_id: str,
    ) -> Dict[str, Any]:
        """
        Extracts structured audit evidence pack for an instrument.
        Includes document versions, SHA-256 hashes, field provenance count, observations, and audit events.
        """
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            db=db,
        )
        inst = db.scalars(
            select(Instrument).where(*conditions, Instrument.id == instrument_id)
        ).first()

        if not inst:
            raise AppException("Instrument not found or unauthorized", status_code=404, code="RECORD_NOT_FOUND")

        # Documents & SHA-256 digests
        doc_stmt = (
            select(DocumentVersion, Document)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.instrument_id == instrument_id)
            .order_by(DocumentVersion.version_number.asc())
        )
        doc_records = db.execute(doc_stmt).all()

        documents = []
        for ver, doc in doc_records:
            uploader_id = getattr(ver, "uploader_user_id", None)
            uploader = db.get(User, uploader_id) if uploader_id else None
            documents.append({
                "version_number": ver.version_number,
                "category": doc.category,
                "file_name": getattr(ver, "original_filename", getattr(ver, "file_name", "document")),
                "sha256_hash": ver.sha256_hash,
                "uploaded_at": ver.uploaded_at.isoformat() if getattr(ver, "uploaded_at", None) else (ver.created_at.isoformat() if getattr(ver, "created_at", None) else ""),
                "uploader_name": uploader.full_name if uploader else uploader_id,
            })

        # Field provenance count
        prov_count = db.scalar(
            select(func.count(FieldProvenance.id)).where(FieldProvenance.instrument_id == instrument_id)
        ) or 0

        # Verification summary
        latest_verif = db.scalars(
            select(VerificationRequest)
            .where(VerificationRequest.instrument_id == instrument_id)
            .order_by(VerificationRequest.created_at.desc())
        ).first()

        verif_summary = {
            "status": latest_verif.status if latest_verif else "NOT_REQUESTED",
            "channel": latest_verif.channel if latest_verif else None,
            "reference_code": latest_verif.reference_code if latest_verif else None,
            "is_simulated": (
                bool(latest_verif.channel.upper().startswith("SIMULAT") or latest_verif.channel.upper() == "SIMULATED")
                if latest_verif else False
            ),
        }

        # Observations count
        try:
            obs_list = ScrutinyObservationService.get_observations(db=db, current_user=current_user, instrument_id=instrument_id)
            obs_count = len(obs_list)
        except Exception:
            obs_count = 0

        # Audit events count
        audit_events_count = db.scalar(
            select(func.count(AuditEvent.id)).where(
                or_(
                    AuditEvent.entity_id == instrument_id,
                    AuditEvent.metadata_json.ilike(f"%{inst.reference_number}%"),
                )
            )
        ) or 0

        return {
            "report_type": "AUDIT_EVIDENCE_PACK",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "instrument_id": inst.id,
            "reference_number": inst.reference_number,
            "institution_id": inst.institution_id,
            "institution_name": inst.institution.display_name if inst.institution else None,
            "administrative_status": inst.status,
            "trust_level": inst.trust_level,
            "documents": documents,
            "field_provenance_count": prov_count,
            "verification_summary": verif_summary,
            "scrutiny_observations_count": obs_count,
            "audit_events_count": audit_events_count,
            "audit_chain_verified": False,
            "audit_chain_status": "PENDING_PROMPT_5_CRYPTO_VERIFICATION",
            "certification_disclaimer": (
                "Internal operational audit extract from FDR Sentinel. Does not constitute certified external judicial evidence "
                "unless independently verified against the cryptographic tamper-evident sequence."
            ),
        }
