"""
Module 3 — Validation Rules: Document Metadata Advisory Indicators (Heuristic)

Rule:
- VAL-META-001: File Metadata Advisory Indicator

Requirements:
- Clearly classified as heuristic/advisory.
- Inspects document metadata / scan results for potential indicators (e.g. editing tool markers,
  timestamp discrepancies, or missing metadata).
- Explicit disclaimer: Legitimate scanning, conversion, and re-saving can alter document metadata.
  Metadata alone must NEVER be treated as proof of tampering, fraud, or forgery.
- Clean extension interface for future metadata inspection without adding unverified AI models.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.validation.enums import (
    FindingCategory,
    RuleOutcome,
    RuleSeverity,
    RuleType,
)
from app.modules.validation.registry import (
    BaseValidationRule,
    RuleContext,
    RuleResult,
    rule_registry,
)


class DocumentMetadataAdvisoryRule(BaseValidationRule):
    """
    VAL-META-001 — Advisory heuristic for document metadata indicators.

    Inspects available document scan / file metadata for:
    1. Known PDF editing / modification tool signatures (e.g. iLovePDF, PDFescape, Sejda).
    2. Upload timestamp occurring prior to the claimed issue date.
    3. Incomplete or unavailable file scan metadata.

    Important:
    * This is an ADVISORY heuristic check.
    * Legitimate institutional scanning, compression, and conversion tools can alter metadata.
    * Metadata alone must NEVER be treated as proof of tampering, fraud, or forgery.
    """
    rule_id = "VAL-META-001"
    rule_version = "1.0"
    rule_type = RuleType.HEURISTIC
    category = FindingCategory.DOCUMENT_INTEGRITY
    severity = RuleSeverity.LOW
    description = (
        "Advisory heuristic: inspects document metadata for conversion/editing tool markers "
        "or timestamp inconsistencies. Advisory only — does not establish tampering."
    )
    enabled = True

    _EDITING_TOOL_MARKERS = [
        "ilovepdf", "pdfescape", "sejda", "smallpdf", "pdf2go", "canva", "photoshop"
    ]

    def evaluate(self, context: RuleContext) -> RuleResult:
        docs = context.available_documents
        if not docs:
            return self._not_applicable("No uploaded document records available for metadata evaluation.")

        indicators: List[str] = []
        evidence_versions: List[str] = []

        for doc in docs:
            ver_id = doc.get("document_version_id")
            if ver_id:
                evidence_versions.append(ver_id)

            # 1. Check scan processing status
            proc_status = doc.get("processing_status", "")
            if proc_status in ("SCAN_UNAVAILABLE", "PROCESSING_FAILED"):
                indicators.append(
                    f"Document {doc.get('document_id')} file scan metadata is unavailable (status: {proc_status})."
                )

            # 2. Check upload timestamp vs claimed issue date
            uploaded_at_str = doc.get("uploaded_at")
            if uploaded_at_str and context.issue_date:
                try:
                    uploaded_date = datetime.fromisoformat(uploaded_at_str).date()
                    if uploaded_date < context.issue_date:
                        indicators.append(
                            f"Document upload date ({uploaded_date}) is earlier than claimed certificate issue date ({context.issue_date})."
                        )
                except Exception:
                    pass

        # Also check policy for custom metadata flags (extension hook)
        meta_tool = context.policy.get("_metadata_producer_tool")
        if meta_tool and any(marker in str(meta_tool).lower() for marker in self._EDITING_TOOL_MARKERS):
            indicators.append(
                f"Document producer/creation metadata indicates conversion tool: '{meta_tool}'."
            )

        if not indicators:
            return self._pass(
                "Document file metadata shows no anomalous editing markers or timestamp inversions."
            )

        return self._make_result(
            outcome=RuleOutcome.WARNING,
            title="Document metadata advisory indicator",
            explanation=(
                "One or more advisory metadata indicators were identified:\n"
                + "\n".join(f"- {ind}" for ind in indicators)
                + "\n\nAdvisory note: This check is an advisory heuristic. Legitimate scanning, "
                "compression, conversion, and re-saving can alter document metadata. Metadata indicators "
                "alone must NEVER be treated as proof of tampering, fraud, or forgery. Human review is required."
            ),
            observed_value="; ".join(indicators),
            expected_value="Standard scan metadata without external tool markers or timestamp inversions",
            evidence_refs=evidence_versions,
            suggested_action=(
                "Perform standard document visual inspection. If the physical certificate text, "
                "bank logo, and signature endorsements appear regular, no action is necessary."
            ),
            fingerprint_key=f"indicators={';'.join(sorted(indicators))}",
        )


# Self-register
rule_registry.register(DocumentMetadataAdvisoryRule())
