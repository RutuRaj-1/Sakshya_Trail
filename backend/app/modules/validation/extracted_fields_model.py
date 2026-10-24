"""
Module 3 — Extracted Document Fields Model

Stores structured field values parsed/extracted from document versions by an OCR
or extraction pipeline. These values are used by cross-validation rules to compare
document evidence against the instrument registry.

Design constraints
------------------
* One `DocumentExtractedFields` record per `document_version_id` (unique).
* Fields are stored as JSON-serialized strings; the raw document content is NEVER stored here.
* Each extracted field has an associated confidence score (0.0–1.0).
* Low-confidence extractions are flagged as advisory (HEURISTIC) findings only.
* A record may be partial — not all fields are always extractable.
* This table is owned by Module 3; it augments Module 2 without modifying it.
* Extracted field values MUST NOT contain PAN, Aadhaar, full account numbers, or passwords.
"""
import uuid
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import String, Text, DateTime, Float, Boolean, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, get_utc_now


class DocumentExtractedFields(Base):
    """
    Structured field values extracted from a specific document version.

    Extraction pipeline (OCR, rule-based parser, LLM extractor) writes records here.
    Cross-validation rules read these values to compare against the instrument registry.

    Confidence scores
    -----------------
    * confidence_overall: 0.0–1.0 aggregate extraction confidence.
    * Individual field confidence suffixed with _confidence (e.g. amount_confidence).
    * When confidence < 0.7 for a field, that field's cross-validation finding is
      labelled HEURISTIC / advisory, not deterministic.

    Extraction status
    -----------------
    PENDING     — record created; extraction not yet run
    COMPLETED   — extraction finished successfully (fields may still be partial)
    FAILED      — extraction pipeline errored; fields are unreliable
    PARTIAL     — extraction ran but some required fields are missing
    """
    __tablename__ = "document_extracted_fields"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ---- Scope ----
    document_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ---- Extraction metadata ----
    extraction_status: Mapped[str] = mapped_column(
        String(20), default="PENDING", nullable=False, index=True
    )
    confidence_overall: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extracted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # pipeline name
    extracted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ---- Extracted fields (all Optional — may not be present in every document) ----
    # Bank / issuing institution name as printed on the document
    doc_bank_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    doc_bank_name_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Certificate / reference number as printed on the document
    doc_reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    doc_reference_number_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Deposit amount as printed on the document (stored as decimal string)
    doc_amount_str: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    doc_amount_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Issue date as printed on the document (ISO date string: YYYY-MM-DD)
    doc_issue_date_str: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    doc_issue_date_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Maturity date as printed on the document (ISO date string: YYYY-MM-DD)
    doc_maturity_date_str: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    doc_maturity_date_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Account holder / depositor name as printed on the document
    # NOTE: MUST NOT store PAN/Aadhaar; only the name as on the FDR.
    doc_account_holder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    doc_account_holder_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Lien holder as printed on the document
    doc_lien_holder: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    doc_lien_holder_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # All additional extracted fields as a JSON blob (for future extensibility)
    extra_fields_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ---- Audit ----
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_def_instrument_id", "instrument_id"),
        Index("ix_def_institution_id", "institution_id"),
        Index("ix_def_extraction_status", "extraction_status"),
    )

    @property
    def doc_amount(self) -> Optional[Decimal]:
        """Parse doc_amount_str as Decimal, or None."""
        if not self.doc_amount_str:
            return None
        try:
            return Decimal(self.doc_amount_str.replace(",", "").strip())
        except Exception:
            return None

    @property
    def extra_fields(self) -> Dict[str, Any]:
        """Parse extra_fields_json."""
        if not self.extra_fields_json:
            return {}
        try:
            return json.loads(self.extra_fields_json)
        except Exception:
            return {}

    @property
    def is_ready(self) -> bool:
        return self.extraction_status in ("COMPLETED", "PARTIAL")

    def field_is_reliable(self, confidence: Optional[float], threshold: float = 0.70) -> bool:
        """Returns True if confidence is above the given threshold."""
        return confidence is not None and confidence >= threshold
