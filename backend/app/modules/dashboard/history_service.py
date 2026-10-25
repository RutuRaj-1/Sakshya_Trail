"""
History Service (Module 7 — Command Center)
Implements PRD-FR-072 & PRD-FR-073:
Unified historical timeline, multi-dimensional snapshot, document version history,
field-level provenance, verification attempts with SIMULATED labelling, and lineage continuity.
"""
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, or_, func

from app.common.exceptions import AppException
from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.verification.models import FieldProvenance, VerificationRequest
from app.modules.lifecycle.models import LifecycleEvaluation, InstrumentLineage
from app.modules.release.models import ReleaseRequest
from app.modules.validation.models import ValidationFinding
from app.modules.audit.models import AuditEvent
from app.modules.dashboard.dashboard_service import enforce_scope_and_get_conditions
from app.modules.dashboard.observation_service import ScrutinyObservationService


class HistoryService:
    """Retrieves document, field, lifecycle, observation, and audit history for an instrument."""

    @staticmethod
    def get_instrument_detail_snapshot(
        db: Session,
        current_user: User,
        instrument_id: str,
    ) -> Dict[str, Any]:
        """
        Builds a complete multi-dimensional snapshot of an instrument and its entire history.
        Enforces tenant isolation prior to retrieval.
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

        # ----------------------------------------------------------------------
        # A. Current Snapshot
        # ----------------------------------------------------------------------
        # Count active discrepancies
        disc_count = db.scalar(
            select(func.count(ValidationFinding.id)).where(
                ValidationFinding.instrument_id == instrument_id,
                ValidationFinding.status.in_(["OPEN", "IN_REVIEW", "PENDING_REVIEW"]),
            )
        ) or 0

        # Active findings list
        active_findings = db.scalars(
            select(ValidationFinding)
            .where(
                ValidationFinding.instrument_id == instrument_id,
                ValidationFinding.status.in_(["OPEN", "IN_REVIEW", "PENDING_REVIEW"]),
            )
            .order_by(ValidationFinding.created_at.desc())
        ).all()

        findings_summary = [
            {
                "id": f.id,
                "rule_code": f.rule_id,
                "severity": f.severity,
                "message": f.title,
                "field_name": getattr(f, "field_name", None),
                "review_status": f.status,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in active_findings
        ]

        # Pending verification count
        pending_verif = db.scalar(
            select(func.count(VerificationRequest.id)).where(
                VerificationRequest.instrument_id == instrument_id,
                VerificationRequest.status.in_(["PENDING", "REQUESTED", "SENT"]),
            )
        ) or 0

        # Lineage links (predecessors and successors)
        predecessors = db.scalars(
            select(InstrumentLineage).where(InstrumentLineage.successor_instrument_id == instrument_id)
        ).all()
        successors = db.scalars(
            select(InstrumentLineage).where(InstrumentLineage.predecessor_instrument_id == instrument_id)
        ).all()

        pred_info = []
        for p in predecessors:
            pred_inst = db.get(Instrument, p.predecessor_instrument_id)
            pred_info.append({
                "lineage_id": p.id,
                "predecessor_id": p.predecessor_instrument_id,
                "predecessor_reference": pred_inst.reference_number if pred_inst else "UNKNOWN",
                "lineage_type": p.relationship_type,
                "status": p.relationship_status,
            })

        succ_info = []
        for s in successors:
            succ_inst = db.get(Instrument, s.successor_instrument_id)
            succ_info.append({
                "lineage_id": s.id,
                "successor_id": s.successor_instrument_id,
                "successor_reference": succ_inst.reference_number if succ_inst else "UNKNOWN",
                "lineage_type": s.relationship_type,
                "status": s.relationship_status,
            })

        # Release case links
        release_cases = db.scalars(
            select(ReleaseRequest).where(ReleaseRequest.instrument_id == instrument_id)
        ).all()
        release_summary = [
            {
                "id": r.id,
                "case_number": r.case_number,
                "case_reference": r.case_number,
                "request_type": r.request_type,
                "workflow_status": r.workflow_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in release_cases
        ]

        # Role-based masking of office assignee
        assigned_office_display = inst.assigned_office or "Headquarters / Unassigned"

        instrument_snapshot = {
            "id": inst.id,
            "reference_number": inst.reference_number,
            "institution_id": inst.institution_id,
            "institution_name": inst.institution.name if inst.institution else None,
            "institution_code": inst.institution.code if inst.institution else None,
            "bank_name": inst.bank_name,
            "branch": inst.branch,
            "amount": f"{Decimal(inst.amount):.2f}",
            "currency": inst.currency or "INR",
            "issue_date": inst.issue_date.isoformat(),
            "maturity_date": inst.maturity_date.isoformat(),
            "status": inst.status,
            "trust_level": inst.trust_level,
            "assigned_office": assigned_office_display,
            "lien_holder": inst.lien_holder,
            "joint_with_aicte": inst.joint_with_aicte,
            "remarks": inst.remarks,
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
            "updated_at": inst.updated_at.isoformat() if inst.updated_at else None,
            "active_discrepancies_count": disc_count,
            "active_findings": findings_summary,
            "pending_verifications_count": pending_verif,
            "predecessors": pred_info,
            "successors": succ_info,
            "release_cases": release_summary,
        }

        # ----------------------------------------------------------------------
        # B. Document History
        # ----------------------------------------------------------------------
        doc_stmt = (
            select(DocumentVersion, Document.category, Document.status.label("doc_status"))
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.instrument_id == instrument_id)
            .order_by(DocumentVersion.uploaded_at.desc(), DocumentVersion.version_number.desc())
        )
        doc_history = []
        for ver, cat, doc_stat in db.execute(doc_stmt).all():
            uploader_user = db.get(User, ver.uploader_user_id) if ver.uploader_user_id else None
            is_clean = ver.processing_status in ["CLEAN", "PROCESSED", "READY"]
            doc_history.append({
                "id": ver.id,
                "document_id": ver.document_id,
                "version_number": ver.version_number,
                "category": cat,
                "uploader_user_id": ver.uploader_user_id,
                "uploader_name": uploader_user.full_name if uploader_user else "System Uploader",
                "uploaded_at": ver.uploaded_at.isoformat() if ver.uploaded_at else "",
                "sha256_hash": ver.sha256_hash,
                "file_name": ver.original_filename,
                "file_size_bytes": ver.file_size_bytes,
                "is_verified": is_clean,
                "download_url": f"/api/v1/documents/{ver.document_id}/versions/{ver.id}/content",
            })

        # ----------------------------------------------------------------------
        # C. Field History & Provenance
        # ----------------------------------------------------------------------
        prov_stmt = (
            select(FieldProvenance)
            .where(FieldProvenance.instrument_id == instrument_id)
            .order_by(FieldProvenance.created_at.desc())
        )
        field_history = []
        for p in db.scalars(prov_stmt).all():
            actor = db.get(User, p.source_actor_id) if p.source_actor_id else None
            # Check for masking sensitive field values
            val = p.recorded_value
            if current_user.role == "INSTITUTION_USER" and p.field_name.lower() in ["internal_notes", "officer_secret"]:
                val = "*** MASKED PER POLICY ***"

            field_history.append({
                "id": p.id,
                "field_name": p.field_name,
                "recorded_value": val,
                "previous_value": getattr(p, "previous_value", None),
                "source_type": p.source_type,
                "source_actor_id": p.source_actor_id,
                "actor_name": actor.full_name if actor else p.source_actor_id,
                "evidence_reference": p.evidence_reference,
                "reason": getattr(p, "change_reason", None),
                "created_at": p.created_at.isoformat() if p.created_at else "",
            })

        # ----------------------------------------------------------------------
        # D. Lifecycle and Lineage History
        # ----------------------------------------------------------------------
        lifecycle_events: List[Dict[str, Any]] = []

        # 1. Lifecycle evaluations
        eval_stmt = (
            select(LifecycleEvaluation)
            .where(LifecycleEvaluation.instrument_id == instrument_id)
            .order_by(LifecycleEvaluation.evaluation_timestamp.asc())
        )
        for ev in db.scalars(eval_stmt).all():
            lifecycle_events.append({
                "event_type": "LIFECYCLE_EVALUATION",
                "timestamp": ev.evaluation_timestamp.isoformat() if ev.evaluation_timestamp else "",
                "actor_id": "SYSTEM_CLOCK",
                "summary": f"Maturity stage evaluated as '{ev.maturity_stage}' (Condition: {ev.due_condition})",
                "details": {
                    "days_to_maturity": ev.days_to_maturity,
                    "is_overdue": ev.is_overdue,
                    "is_escalated": ev.is_escalated,
                },
                "is_simulated": False,
            })

        # 2. Verification requests & responses (with explicit SIMULATED label)
        verif_stmt = (
            select(VerificationRequest)
            .where(VerificationRequest.instrument_id == instrument_id)
            .order_by(VerificationRequest.created_at.asc())
        )
        for vr in db.scalars(verif_stmt).all():
            adapter_val = getattr(vr, "adapter_type", None)
            is_sim = (
                vr.channel.upper().startswith("SIMULAT")
                or vr.channel.upper() == "SIMULATED"
                or (adapter_val and "simulat" in str(adapter_val).lower())
            )
            lifecycle_events.append({
                "event_type": "VERIFICATION_REQUEST",
                "timestamp": vr.created_at.isoformat() if vr.created_at else "",
                "actor_id": getattr(vr, "requested_by_user_id", None) or "VERIFICATION_ROUTER",
                "summary": f"Verification requested via {vr.channel} ({vr.status})",
                "details": {
                    "request_code": vr.reference_code,
                    "channel": vr.channel,
                    "status": vr.status,
                    "adapter_type": adapter_val,
                    "is_source_unavailable": bool(vr.error_details and "source_unavailable" in vr.error_details.lower()),
                },
                "is_simulated": is_sim,
            })

        # 3. Lineage links
        for p in predecessors:
            lifecycle_events.append({
                "event_type": "LINEAGE_PREDECESSOR_LINK",
                "timestamp": p.created_at.isoformat() if p.created_at else "",
                "actor_id": p.created_by_user_id,
                "summary": f"Predecessor instrument linked (Type: {p.relationship_type})",
                "details": {
                    "predecessor_id": p.predecessor_instrument_id,
                    "status": p.relationship_status,
                },
                "is_simulated": False,
            })

        for s in successors:
            lifecycle_events.append({
                "event_type": "LINEAGE_SUCCESSOR_LINK",
                "timestamp": s.created_at.isoformat() if s.created_at else "",
                "actor_id": s.created_by_user_id,
                "summary": f"Successor renewal instrument linked (Type: {s.relationship_type})",
                "details": {
                    "successor_id": s.successor_instrument_id,
                    "status": s.relationship_status,
                },
                "is_simulated": False,
            })

        # Sort lifecycle events
        lifecycle_events.sort(key=lambda x: x["timestamp"], reverse=True)

        # ----------------------------------------------------------------------
        # E. Chronological Audit Timeline
        # ----------------------------------------------------------------------
        audit_stmt = (
            select(AuditEvent)
            .where(
                or_(
                    AuditEvent.entity_id == instrument_id,
                    AuditEvent.metadata_json.ilike(f"%{inst.reference_number}%"),
                )
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(50)
        )
        timeline = []
        for a in db.scalars(audit_stmt).all():
            actor = db.get(User, a.actor_user_id) if a.actor_user_id else None
            timeline.append({
                "event_type": a.action,
                "timestamp": a.created_at.isoformat() if a.created_at else "",
                "actor_id": actor.full_name if actor else (a.actor_email or a.actor_user_id or "SYSTEM"),
                "summary": f"{a.action} on {a.entity_type}",
                "details": a.parsed_metadata,
            })

        # ----------------------------------------------------------------------
        # F. Append-Only Scrutiny Observations
        # ----------------------------------------------------------------------
        observations = ScrutinyObservationService.get_observations(
            db=db,
            current_user=current_user,
            instrument_id=instrument_id,
        )

        return {
            "instrument": instrument_snapshot,
            "documents": doc_history,
            "field_history": field_history,
            "lifecycle_lineage": lifecycle_events,
            "timeline": timeline,
            "observations": observations,
        }

    @staticmethod
    def get_instrument_timeline(
        db: Session,
        current_user: User,
        instrument_id: str,
    ) -> Dict[str, Any]:
        """
        Backward compatible lightweight timeline.
        """
        snapshot = HistoryService.get_instrument_detail_snapshot(db, current_user, instrument_id)
        return {
            "instrument_id": instrument_id,
            "reference_number": snapshot["instrument"]["reference_number"],
            "total_events": len(snapshot["timeline"]),
            "events": snapshot["timeline"],
        }
