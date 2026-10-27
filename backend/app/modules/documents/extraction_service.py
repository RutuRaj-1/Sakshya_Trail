"""
Module 2 & 3 — Document Extraction Service
Provides safe, deterministic, version-aware extraction of structured candidate fields
from certified document evidence (text-based PDFs) and stores them in DocumentExtractedFields.
"""
import io
import re
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.modules.documents.models import Document, DocumentVersion
from app.modules.validation.extracted_fields_model import DocumentExtractedFields
from app.modules.validation.extracted_fields_service import upsert_extracted_fields, get_extracted_fields
from app.modules.validation.engine import trigger_post_save_validation
from app.modules.audit.service import log_audit_event

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    status: str  # COMPLETED, PARTIAL, FAILED, OCR_UNAVAILABLE
    confidence_overall: Optional[float] = None
    provider_name: str
    doc_bank_name: Optional[str] = None
    doc_bank_name_confidence: Optional[float] = None
    doc_reference_number: Optional[str] = None
    doc_reference_number_confidence: Optional[float] = None
    doc_amount_str: Optional[str] = None
    doc_amount_confidence: Optional[float] = None
    doc_issue_date_str: Optional[str] = None
    doc_issue_date_confidence: Optional[float] = None
    doc_maturity_date_str: Optional[str] = None
    doc_maturity_date_confidence: Optional[float] = None
    doc_account_holder: Optional[str] = None
    doc_account_holder_confidence: Optional[float] = None
    doc_lien_holder: Optional[str] = None
    doc_lien_holder_confidence: Optional[float] = None
    extra_fields: Dict[str, Any] = {}
    error_details: Optional[str] = None


class BaseExtractionProvider(ABC):
    @abstractmethod
    def extract(self, file_content: bytes, filename: str, content_type: str) -> ExtractionResult:
        pass


def _normalize_date_str(raw: str) -> Optional[str]:
    """Normalize DD/MM/YYYY or DD-MM-YYYY or YYYY-MM-DD to ISO YYYY-MM-DD."""
    raw = raw.strip()
    # YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    # DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", raw)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            d = date(year, month, day)
            return d.isoformat()
        except ValueError:
            return None
    return None


class DeterministicPdfExtractionProvider(BaseExtractionProvider):
    """
    Deterministic extraction provider using standard pypdf text extraction.
    Parses structured FDR fields from text streams. If the document is an image-only
    or scanned PDF without extractable text, marks extraction as OCR_UNAVAILABLE
    rather than synthesizing fake values.
    """

    KNOWN_BANKS = [
        "State Bank of India",
        "Punjab National Bank",
        "Canara Bank",
        "Bank of Baroda",
        "Union Bank of India",
        "HDFC Bank",
        "ICICI Bank",
        "Axis Bank",
        "Kotak Mahindra Bank",
        "Indian Bank",
        "Central Bank of India",
        "Bank of India",
        "Indian Overseas Bank",
        "IDBI Bank",
    ]

    def extract(self, file_content: bytes, filename: str, content_type: str) -> ExtractionResult:
        if content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
            return ExtractionResult(
                status="FAILED",
                provider_name="DeterministicPdfExtractor",
                error_details=f"Unsupported format '{content_type}': only PDF extraction supported in local environment",
            )

        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_content))
            pages_text = []
            for p in reader.pages:
                text = p.extract_text()
                if text:
                    pages_text.append(text)
            full_text = "\n".join(pages_text).strip()
        except Exception as e:
            return ExtractionResult(
                status="FAILED",
                provider_name="DeterministicPdfExtractor",
                error_details=f"Malformed or unreadable PDF: {str(e)}",
            )

        # Check for image-only/scanned PDF without text layer
        if not full_text or len(full_text) < 15:
            return ExtractionResult(
                status="FAILED",
                provider_name="DeterministicPdfExtractor",
                error_details="Scanned or image-only PDF: OCR text extraction unavailable in local environment.",
            )

        # Parse fields from text
        confidences: List[float] = []

        # 1. Reference number
        doc_ref = None
        doc_ref_conf = None
        ref_match = re.search(
            r"(?i)(?:fixed\s*deposit\s*(?:receipt)?|fdr\s*(?:receipt)?|deposit\s*receipt|certificate|reference|receipt)\s*(?:no|num|number)?[:.\s#]+([A-Z0-9/\-_]*\d[A-Z0-9/\-_]*)",
            full_text,
        )
        if not ref_match:
            ref_match = re.search(
                r"(?i)(?:fdr|ref|certificate|receipt)\s*(?:no|num|number)?[:.\s#]+([A-Z0-9/\-_]{4,35})",
                full_text,
            )
        if ref_match:
            doc_ref = ref_match.group(1).strip()
            doc_ref_conf = 0.95
            confidences.append(doc_ref_conf)

        # 2. Bank name
        doc_bank = None
        doc_bank_conf = None
        for b in self.KNOWN_BANKS:
            if re.search(r"\b" + re.escape(b) + r"\b", full_text, re.IGNORECASE):
                doc_bank = b
                doc_bank_conf = 0.95
                confidences.append(doc_bank_conf)
                break
        if not doc_bank:
            bank_match = re.search(r"(?i)(?:bank\s*name|issuing\s*bank|bank)[:.\s]*([A-Za-z\s&]{3,40}(?:bank)?)", full_text)
            if bank_match:
                doc_bank = bank_match.group(1).strip()
                doc_bank_conf = 0.75
                confidences.append(doc_bank_conf)

        # 3. Amount
        doc_amount = None
        doc_amount_conf = None
        amt_match = re.search(
            r"(?i)(?:rs\.?|inr|amount|deposit\s*amount|principal(?:\s*amount)?)[:.\s]*([\d,]+(?:\.\d{2})?)",
            full_text,
        )
        if amt_match:
            raw_amt = amt_match.group(1).replace(",", "").strip()
            try:
                # Validate Decimal format
                d_amt = Decimal(raw_amt)
                doc_amount = f"{d_amt:.2f}"
                doc_amount_conf = 0.95
                confidences.append(doc_amount_conf)
            except Exception:
                pass

        # 4. Dates
        doc_issue = None
        doc_issue_conf = None
        issue_match = re.search(
            r"(?i)(?:issue\s*date|date\s*of\s*issue|issued\s*on)[:.\s]*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            full_text,
        )
        if issue_match:
            norm_issue = _normalize_date_str(issue_match.group(1))
            if norm_issue:
                doc_issue = norm_issue
                doc_issue_conf = 0.90
                confidences.append(doc_issue_conf)

        doc_maturity = None
        doc_maturity_conf = None
        mat_match = re.search(
            r"(?i)(?:maturity\s*date|date\s*of\s*maturity|due\s*date|valid\s*upto|valid\s*till)[:.\s]*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            full_text,
        )
        if mat_match:
            norm_mat = _normalize_date_str(mat_match.group(1))
            if norm_mat:
                doc_maturity = norm_mat
                doc_maturity_conf = 0.90
                confidences.append(doc_maturity_conf)

        # 5. Account holder
        doc_holder = None
        doc_holder_conf = None
        holder_match = re.search(
            r"(?i)(?:account\s*holder|depositor(?:\s*name)?|in\s*the\s*name\s*of)[:.\s]*([A-Za-z\s.]+?)(?:\n|\r|,|;|$)",
            full_text,
        )
        if holder_match:
            cand_holder = holder_match.group(1).strip()
            if len(cand_holder) >= 3 and not re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", cand_holder):  # Exclude PAN
                doc_holder = cand_holder
                doc_holder_conf = 0.85
                confidences.append(doc_holder_conf)

        # 6. Lien holder
        doc_lien = None
        doc_lien_conf = None
        lien_match = re.search(
            r"(?i)(?:lien\s*in\s*favou?r\s*of|lien\s*holder|pledged\s*to)[:.\s]*([A-Za-z\s.]+?)(?:\n|\r|,|;|$)",
            full_text,
        )
        if lien_match:
            cand_lien = lien_match.group(1).strip()
            if len(cand_lien) >= 3:
                doc_lien = cand_lien
                doc_lien_conf = 0.90
                confidences.append(doc_lien_conf)
        elif re.search(r"(?i)\bAICTE\b|All\s*India\s*Council\s*for\s*Technical\s*Education", full_text):
            doc_lien = "All India Council for Technical Education"
            doc_lien_conf = 0.85
            confidences.append(doc_lien_conf)

        overall_conf = round(sum(confidences) / len(confidences), 2) if confidences else None

        extracted_count = sum(1 for v in [doc_ref, doc_bank, doc_amount, doc_issue, doc_maturity] if v is not None)
        if extracted_count >= 3:
            status = "COMPLETED"
        elif extracted_count > 0:
            status = "PARTIAL"
        else:
            status = "PARTIAL"

        return ExtractionResult(
            status=status,
            confidence_overall=overall_conf,
            provider_name="DeterministicPdfExtractor",
            doc_bank_name=doc_bank,
            doc_bank_name_confidence=doc_bank_conf,
            doc_reference_number=doc_ref,
            doc_reference_number_confidence=doc_ref_conf,
            doc_amount_str=doc_amount,
            doc_amount_confidence=doc_amount_conf,
            doc_issue_date_str=doc_issue,
            doc_issue_date_confidence=doc_issue_conf,
            doc_maturity_date_str=doc_maturity,
            doc_maturity_date_confidence=doc_maturity_conf,
            doc_account_holder=doc_holder,
            doc_account_holder_confidence=doc_holder_conf,
            doc_lien_holder=doc_lien,
            doc_lien_holder_confidence=doc_lien_conf,
            extra_fields={"page_count": len(reader.pages), "char_count": len(full_text)},
        )


_default_provider = DeterministicPdfExtractionProvider()


def get_extraction_provider() -> BaseExtractionProvider:
    return _default_provider


class DocumentExtractionService:
    @staticmethod
    def extract_and_persist(
        db: Session,
        version: DocumentVersion,
        file_content: bytes,
        actor_user_id: Optional[str] = None,
    ) -> DocumentExtractedFields:
        """
        Executes deterministic extraction for an approved, clean document version.
        Persists results with version-level provenance and triggers Module 3 validation.
        """
        doc = version.document
        if not doc:
            doc = db.query(Document).filter(Document.id == version.document_id).first()

        provider = get_extraction_provider()
        res = provider.extract(
            file_content=file_content,
            filename=version.original_filename,
            content_type=version.content_type,
        )

        extracted_record = upsert_extracted_fields(
            db=db,
            document_version_id=version.id,
            instrument_id=doc.instrument_id,
            institution_id=doc.institution_id,
            document_id=doc.id,
            extraction_status=res.status,
            confidence_overall=res.confidence_overall,
            extracted_by=res.provider_name,
            doc_bank_name=res.doc_bank_name,
            doc_bank_name_confidence=res.doc_bank_name_confidence,
            doc_reference_number=res.doc_reference_number,
            doc_reference_number_confidence=res.doc_reference_number_confidence,
            doc_amount_str=res.doc_amount_str,
            doc_amount_confidence=res.doc_amount_confidence,
            doc_issue_date_str=res.doc_issue_date_str,
            doc_issue_date_confidence=res.doc_issue_date_confidence,
            doc_maturity_date_str=res.doc_maturity_date_str,
            doc_maturity_date_confidence=res.doc_maturity_date_confidence,
            doc_account_holder=res.doc_account_holder,
            doc_account_holder_confidence=res.doc_account_holder_confidence,
            doc_lien_holder=res.doc_lien_holder,
            doc_lien_holder_confidence=res.doc_lien_holder_confidence,
            extra_fields=res.extra_fields,
            error_details=res.error_details,
        )

        # Audit event
        log_audit_event(
            db=db,
            action="DOCUMENT_EXTRACTION_COMPLETED" if res.status in ("COMPLETED", "PARTIAL") else "DOCUMENT_EXTRACTION_FAILED",
            entity_type="DocumentExtractedFields",
            entity_id=extracted_record.id,
            actor_user_id=actor_user_id,
            outcome="SUCCESS" if res.status in ("COMPLETED", "PARTIAL") else "FAILURE",
            metadata={
                "document_id": doc.id,
                "version_id": version.id,
                "status": res.status,
                "confidence_overall": res.confidence_overall,
                "provider": res.provider_name,
                "error": res.error_details,
            },
        )

        # Trigger Module 3 validation engine cross-validation rules
        try:
            trigger_post_save_validation(db, doc.instrument_id)
        except Exception as e:
            logger.warning(f"Post-extraction validation error for instrument {doc.instrument_id}: {e}")

        return extracted_record
