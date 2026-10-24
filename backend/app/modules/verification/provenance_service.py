"""
Module 4 — Field-Level Provenance Service
Manages immutable recording, retrieval, and historical supersession of tracked field values.
"""
import json
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.common.exceptions import AppException
from app.modules.instruments.models import Instrument
from app.modules.verification.models import FieldProvenance
from app.modules.verification.enums import (
    ProvenanceSourceType,
    TRACKED_FIELDS_SET,
)


def _serialize_value(value: Any) -> str:
    """Format recorded value into a protected, serialized string representation."""
    if value is None:
        return "null"
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def record_field_provenance(
    db: Session,
    instrument_id: str,
    field_name: str,
    value: Any,
    source_type: str,
    actor_user_id: Optional[str] = None,
    source_service_id: Optional[str] = None,
    evidence_reference: Optional[str] = None,
    related_document_id: Optional[str] = None,
    related_document_version_id: Optional[str] = None,
    related_validation_run_id: Optional[str] = None,
    source_timestamp: Optional[datetime] = None,
) -> FieldProvenance:
    """
    Appends a new field provenance record.
    Marks any previously active record for (instrument_id, field_name) as superseded.
    Preserves complete chain of custody without deleting or modifying historical values.
    """
    if field_name not in TRACKED_FIELDS_SET:
        raise AppException(
            message=f"Field '{field_name}' is not in the tracked provenance allow-list.",
            status_code=422,
            code="UNTRACKED_FIELD",
            details={"tracked_fields": sorted(list(TRACKED_FIELDS_SET))},
        )

    # 1. Fetch current active record for this field on this instrument if any
    stmt = (
        select(FieldProvenance)
        .where(
            and_(
                FieldProvenance.instrument_id == instrument_id,
                FieldProvenance.field_name == field_name,
                FieldProvenance.is_active == True,
            )
        )
    )
    prior_rec = db.scalars(stmt).first()

    serialized_val = _serialize_value(value)

    # 2. Instantiate new active provenance row
    new_rec = FieldProvenance(
        instrument_id=instrument_id,
        field_name=field_name,
        recorded_value=serialized_val,
        source_type=source_type,
        source_actor_id=actor_user_id,
        source_service_id=source_service_id,
        evidence_reference=evidence_reference,
        related_document_id=related_document_id,
        related_document_version_id=related_document_version_id,
        related_validation_run_id=related_validation_run_id,
        prior_provenance_id=prior_rec.id if prior_rec else None,
        is_active=True,
    )
    if source_timestamp:
        new_rec.source_timestamp = source_timestamp

    db.add(new_rec)
    db.flush()

    # 3. Supersede prior record if present
    if prior_rec:
        prior_rec.is_active = False
        prior_rec.superseded_by_id = new_rec.id
        db.add(prior_rec)

    db.commit()
    db.refresh(new_rec)
    return new_rec


def get_active_field_provenances(db: Session, instrument_id: str) -> List[FieldProvenance]:
    """Retrieve all current active provenance records for an instrument."""
    stmt = (
        select(FieldProvenance)
        .where(
            and_(
                FieldProvenance.instrument_id == instrument_id,
                FieldProvenance.is_active == True,
            )
        )
        .order_by(FieldProvenance.field_name)
    )
    return list(db.scalars(stmt).all())


def get_field_provenance_history(
    db: Session, instrument_id: str, field_name: str
) -> List[FieldProvenance]:
    """Retrieve the full historical chain of custody for a specific field on an instrument."""
    stmt = (
        select(FieldProvenance)
        .where(
            and_(
                FieldProvenance.instrument_id == instrument_id,
                FieldProvenance.field_name == field_name,
            )
        )
        .order_by(FieldProvenance.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def initialize_instrument_provenance(
    db: Session,
    instrument: Instrument,
    actor_user_id: Optional[str] = None,
    source_type: str = ProvenanceSourceType.INSTITUTION_ENTERED.value,
) -> List[FieldProvenance]:
    """
    Initializes baseline field provenance rows (L0_DECLARED) for a newly registered instrument.
    Called upon instrument creation or import.
    """
    created_records = []
    for field_name in TRACKED_FIELDS_SET:
        if hasattr(instrument, field_name):
            val = getattr(instrument, field_name)
            rec = record_field_provenance(
                db=db,
                instrument_id=instrument.id,
                field_name=field_name,
                value=val,
                source_type=source_type,
                actor_user_id=actor_user_id,
                evidence_reference="Initial instrument registration declaration",
            )
            created_records.append(rec)
    return created_records
