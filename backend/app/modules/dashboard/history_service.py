"""
History Service (Module 7 — Command Center)
Implements PRD-FR-072 & PRD-FR-073:
Unified historical timeline, document history, and field-level provenance audit queries.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.modules.auth.models import User
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.verification.models import FieldProvenance
from app.modules.lifecycle.models import LifecycleEvaluation
from app.modules.release.models import ReleaseReviewObservation
from app.modules.dashboard.dashboard_service import enforce_scope_and_get_conditions


class HistoryService:
    """Retrieves document, field, lifecycle and observation history for an instrument."""

    @staticmethod
    def get_instrument_timeline(
        db: Session,
        current_user: User,
        instrument_id: str,
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive chronologically sorted timeline of events for an instrument.
        """
        # Scope check
        conditions = enforce_scope_and_get_conditions(
            current_user=current_user,
            db=db,
        )
        inst = db.scalars(
            select(Instrument).where(*conditions, Instrument.id == instrument_id)
        ).first()

        if not inst:
            return {"error": "Instrument not found or unauthorized", "events": []}

        events: List[Dict[str, Any]] = []

        # 1. Registration event
        if inst.created_at:
            events.append({
                "event_type": "INSTRUMENT_REGISTERED",
                "timestamp": inst.created_at.isoformat(),
                "actor_id": inst.created_by_user_id,
                "summary": f"Instrument registered with reference {inst.reference_number}",
                "details": {
                    "bank_name": inst.bank_name,
                    "amount": str(inst.amount),
                    "maturity_date": inst.maturity_date.isoformat(),
                    "trust_level": inst.trust_level,
                },
            })

        # 2. Document upload events
        doc_stmt = (
            select(DocumentVersion, Document.category)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(Document.instrument_id == instrument_id)
            .order_by(DocumentVersion.uploaded_at.asc())
        )
        for ver, cat in db.execute(doc_stmt).all():
            events.append({
                "event_type": "DOCUMENT_UPLOADED",
                "timestamp": ver.uploaded_at.isoformat(),
                "actor_id": ver.uploader_user_id,
                "summary": f"Uploaded version {ver.version_number} of {cat}",
                "details": {
                    "document_id": ver.document_id,
                    "sha256_hash": ver.sha256_hash,
                    "processing_status": ver.processing_status,
                },
            })

        # 3. Field provenance changes
        prov_stmt = (
            select(FieldProvenance)
            .where(FieldProvenance.instrument_id == instrument_id)
            .order_by(FieldProvenance.created_at.asc())
        )
        for p in db.scalars(prov_stmt).all():
            events.append({
                "event_type": "FIELD_PROVENANCE_RECORDED",
                "timestamp": p.created_at.isoformat(),
                "actor_id": p.source_actor_id,
                "summary": f"Provenance entry for field '{p.field_name}' via {p.source_type}",
                "details": {
                    "field_name": p.field_name,
                    "recorded_value": p.recorded_value,
                    "source_type": p.source_type,
                    "evidence_reference": p.evidence_reference,
                },
            })

        # 4. Lifecycle evaluations
        eval_stmt = (
            select(LifecycleEvaluation)
            .where(LifecycleEvaluation.instrument_id == instrument_id)
            .order_by(LifecycleEvaluation.evaluation_timestamp.asc())
        )
        for ev in db.scalars(eval_stmt).all():
            events.append({
                "event_type": "LIFECYCLE_EVALUATION",
                "timestamp": ev.evaluation_timestamp.isoformat(),
                "actor_id": "SYSTEM_CLOCK",
                "summary": f"Lifecycle evaluation: stage={ev.maturity_stage}, condition={ev.due_condition}",
                "details": {
                    "days_to_maturity": ev.days_to_maturity,
                    "is_overdue": ev.is_overdue,
                    "is_escalated": ev.is_escalated,
                },
            })

        # Sort all events chronologically ascending
        events.sort(key=lambda x: x["timestamp"])

        return {
            "instrument_id": instrument_id,
            "reference_number": inst.reference_number,
            "total_events": len(events),
            "events": events,
        }
