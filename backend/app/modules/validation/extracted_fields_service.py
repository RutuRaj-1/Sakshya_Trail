"""
Module 3 — Extracted Fields Service

Provides read/write access to DocumentExtractedFields records.

Write path: called by the extraction pipeline (OCR, LLM, rule-based parser).
Read path: called by cross-validation rules via the RuleContext's available_documents list
           (the engine enriches document metadata with extracted field summaries).

Safety constraints
------------------
* Never stores PAN, Aadhaar, full account numbers, or raw document text.
* Low-confidence field values are flagged; rules treat them as heuristic inputs.
* Extraction pipeline credentials and API keys are managed externally (env vars).
"""
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.validation.extracted_fields_model import DocumentExtractedFields
from app.modules.documents.models import Document, DocumentVersion


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_extracted_fields(
    db: Session,
    document_version_id: str,
) -> Optional[DocumentExtractedFields]:
    """Return the extracted fields record for a specific document version."""
    return db.scalar(
        select(DocumentExtractedFields).where(
            DocumentExtractedFields.document_version_id == document_version_id
        )
    )


def get_extracted_fields_for_instrument(
    db: Session,
    instrument_id: str,
) -> List[DocumentExtractedFields]:
    """Return all extracted field records for a given instrument."""
    return list(
        db.scalars(
            select(DocumentExtractedFields).where(
                DocumentExtractedFields.instrument_id == instrument_id,
                DocumentExtractedFields.extraction_status.in_(["COMPLETED", "PARTIAL"]),
            )
        ).all()
    )


def upsert_extracted_fields(
    db: Session,
    document_version_id: str,
    instrument_id: str,
    institution_id: str,
    document_id: str,
    extraction_status: str = "COMPLETED",
    confidence_overall: Optional[float] = None,
    extracted_by: Optional[str] = None,
    doc_bank_name: Optional[str] = None,
    doc_bank_name_confidence: Optional[float] = None,
    doc_reference_number: Optional[str] = None,
    doc_reference_number_confidence: Optional[float] = None,
    doc_amount_str: Optional[str] = None,
    doc_amount_confidence: Optional[float] = None,
    doc_issue_date_str: Optional[str] = None,
    doc_issue_date_confidence: Optional[float] = None,
    doc_maturity_date_str: Optional[str] = None,
    doc_maturity_date_confidence: Optional[float] = None,
    doc_account_holder: Optional[str] = None,
    doc_account_holder_confidence: Optional[float] = None,
    doc_lien_holder: Optional[str] = None,
    doc_lien_holder_confidence: Optional[float] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
    error_details: Optional[str] = None,
) -> DocumentExtractedFields:
    """
    Create or update extracted fields for a document version.

    Used by the extraction pipeline to persist extraction results.
    If a record already exists for this document_version_id, it is updated in place.
    """
    existing = get_extracted_fields(db, document_version_id)
    now = _utc_now()

    if existing:
        rec = existing
    else:
        rec = DocumentExtractedFields(
            document_version_id=document_version_id,
            document_id=document_id,
            instrument_id=instrument_id,
            institution_id=institution_id,
        )
        db.add(rec)

    rec.extraction_status = extraction_status
    rec.confidence_overall = confidence_overall
    rec.extracted_by = extracted_by
    rec.extracted_at = now
    rec.error_details = error_details
    rec.doc_bank_name = _safe_str(doc_bank_name)
    rec.doc_bank_name_confidence = doc_bank_name_confidence
    rec.doc_reference_number = _safe_str(doc_reference_number)
    rec.doc_reference_number_confidence = doc_reference_number_confidence
    rec.doc_amount_str = _safe_str(doc_amount_str)
    rec.doc_amount_confidence = doc_amount_confidence
    rec.doc_issue_date_str = _safe_str(doc_issue_date_str)
    rec.doc_issue_date_confidence = doc_issue_date_confidence
    rec.doc_maturity_date_str = _safe_str(doc_maturity_date_str)
    rec.doc_maturity_date_confidence = doc_maturity_date_confidence
    rec.doc_account_holder = _safe_str(doc_account_holder)
    rec.doc_account_holder_confidence = doc_account_holder_confidence
    rec.doc_lien_holder = _safe_str(doc_lien_holder)
    rec.doc_lien_holder_confidence = doc_lien_holder_confidence
    rec.extra_fields_json = json.dumps(extra_fields) if extra_fields else None
    rec.updated_at = now

    db.commit()
    db.refresh(rec)

    # Deterministic re-evaluation after extraction results become available
    try:
        from app.modules.validation.engine import trigger_post_save_validation
        trigger_post_save_validation(db, rec.instrument_id)
    except Exception:
        pass

    return rec


def build_extracted_fields_summary(rec: DocumentExtractedFields) -> Dict[str, Any]:
    """
    Build a safe, serializable summary of extracted fields for inclusion in RuleContext.

    This summary contains field values and confidence scores but NOT raw document content.
    """
    return {
        "document_version_id": rec.document_version_id,
        "extraction_status": rec.extraction_status,
        "confidence_overall": rec.confidence_overall,
        "doc_bank_name": rec.doc_bank_name,
        "doc_bank_name_confidence": rec.doc_bank_name_confidence,
        "doc_reference_number": rec.doc_reference_number,
        "doc_reference_number_confidence": rec.doc_reference_number_confidence,
        "doc_amount": str(rec.doc_amount) if rec.doc_amount is not None else None,
        "doc_amount_confidence": rec.doc_amount_confidence,
        "doc_issue_date_str": rec.doc_issue_date_str,
        "doc_issue_date_confidence": rec.doc_issue_date_confidence,
        "doc_maturity_date_str": rec.doc_maturity_date_str,
        "doc_maturity_date_confidence": rec.doc_maturity_date_confidence,
        "doc_lien_holder": rec.doc_lien_holder,
        "doc_lien_holder_confidence": rec.doc_lien_holder_confidence,
    }


def _safe_str(value: Optional[str]) -> Optional[str]:
    """Trim and truncate strings to prevent large accidental payloads."""
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed[:500] if trimmed else None
