"""
Module 3 — Validation Rules: Cross-Source Evidence Reconciliation

Rules for comparing machine-extracted suggestions from Module 2 documents
against authoritative Module 1 instrument fields without silently choosing a winner.

Rules in this file:
- VAL-XSRC-STALE: Stale Document Extraction Identified
- VAL-XSRC-001: Cross-Source Amount Reconciliation
- VAL-XSRC-002: Cross-Source Reference Number Reconciliation
- VAL-XSRC-003: Cross-Source Date Reconciliation
- VAL-XSRC-004: Cross-Source Bank Name Reconciliation
- VAL-XSRC-006: Cross-Source Lien Holder Reconciliation

Design constraints
------------------
* Extraction values are suggestions, NEVER authoritative truth.
* Machine extractions NEVER silently overwrite instrument registry fields.
* Never create a mismatch finding when extraction is disabled, missing, malformed, or has no usable value.
* Stale extractions (against older document versions) are clearly identified and require reprocessing.
* Extraction never establishes authenticity, bank confirmation, or release eligibility.
"""
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

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
from app.modules.validation.normalization import (
    normalize_reference_number,
    normalize_bank_name,
)


def _get_usable_extraction(context: RuleContext) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Helper to locate a usable extraction record from RuleContext.
    Returns (record, unusable_reason).
    """
    if not context.extracted_fields:
        return None, "No document extraction records available for this instrument."

    # Look for completed or partial extractions
    for rec in context.extracted_fields:
        status = rec.get("extraction_status", "").upper()
        if status in ("COMPLETED", "PARTIAL"):
            return rec, None

    # If all records are pending or failed
    first = context.extracted_fields[0]
    return None, f"Document extraction status is '{first.get('extraction_status')}', not ready for evaluation."


class StaleDocumentExtractionRule(BaseValidationRule):
    """
    VAL-XSRC-STALE — Detects whether document extraction was performed against
    an older version of the document (stale extraction).

    If the document has been updated with a newer version since the extraction was run,
    the extraction is stale and requires reprocessing or manual review before it can
    be relied upon as evidence.
    """
    rule_id = "VAL-XSRC-STALE"
    rule_version = "1.0"
    rule_type = RuleType.HEURISTIC
    category = FindingCategory.DOCUMENT_INTEGRITY
    severity = RuleSeverity.MEDIUM
    description = (
        "Identifies machine-extracted document fields that were generated from an older "
        "document version when a newer document version has since been uploaded."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        if not context.extracted_fields:
            return self._not_applicable("No document extraction records exist for this instrument.")

        stale_records = [rec for rec in context.extracted_fields if rec.get("is_stale")]
        if not stale_records:
            return self._pass("All document extractions correspond to current document versions.")

        first_stale = stale_records[0]
        extracted_ver = first_stale.get("document_version_id", "unknown")
        current_ver = first_stale.get("current_version_id", "unknown")

        return self._make_result(
            outcome=RuleOutcome.WARNING,
            title="Stale document extraction detected: document version has changed",
            explanation=(
                f"The machine-extracted suggestions were generated against an older document version "
                f"({extracted_ver}), but a newer document version ({current_ver}) is now current. "
                "Because document content may have changed, this extraction must be reprocessed or "
                "reviewed against the latest upload before being used as reconciliation evidence."
            ),
            observed_value=f"Extraction analyzed version: {extracted_ver}",
            expected_value=f"Current active version: {current_ver}",
            evidence_refs=[extracted_ver, current_ver],
            suggested_action=(
                "Re-run the OCR / document extraction pipeline on the current document version, "
                "or review the newly uploaded document file manually."
            ),
            fingerprint_key=f"extracted_ver={extracted_ver},current_ver={current_ver}",
        )


class CrossSourceAmountRule(BaseValidationRule):
    """
    VAL-XSRC-001 — Compare entered instrument amount against machine-extracted suggestion.

    - Extraction is a suggestion, not authoritative truth.
    - If extraction is missing, malformed, or stale: UNABLE_TO_EVALUATE (no false mismatch).
    - If amounts match: PASS.
    - If amounts differ: FAIL (discrepancy finding for human review).
    """
    rule_id = "VAL-XSRC-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.CROSS_SOURCE_RECONCILIATION
    severity = RuleSeverity.HIGH
    description = (
        "Reconciles entered instrument amount with machine-extracted certificate amount. "
        "Flags material differences for human review without silently overwriting either."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        if context.amount_decimal is None:
            return self._unable_to_evaluate("Instrument amount is not specified in the registry.")

        rec, reason = _get_usable_extraction(context)
        if not rec:
            return self._unable_to_evaluate(reason or "Extraction unavailable.")

        if rec.get("is_stale"):
            return self._unable_to_evaluate(
                "Document extraction is stale (older version). Reprocess current document version."
            )

        doc_amt_str = rec.get("doc_amount_str")
        if not doc_amt_str or not str(doc_amt_str).strip():
            return self._unable_to_evaluate(
                "Extracted document record does not contain an amount value."
            )

        try:
            doc_amount = Decimal(str(doc_amt_str).replace(",", "").strip())
        except Exception:
            return self._unable_to_evaluate(
                f"Extracted amount '{doc_amt_str}' could not be parsed as a valid numeric decimal."
            )

        entered_amount = Decimal(str(context.amount_decimal))

        if abs(entered_amount - doc_amount) < Decimal("0.01"):
            return self._pass(
                f"Entered instrument amount ({entered_amount}) matches extracted document suggestion ({doc_amount})."
            )

        return self._make_result(
            outcome=RuleOutcome.FAIL,
            title="Discrepancy between entered instrument amount and extracted document amount",
            explanation=(
                f"The entered instrument amount ({entered_amount}) differs from the machine-extracted "
                f"document suggestion ({doc_amount}). Machine-extracted values are suggestions, not authoritative "
                "truth, and have not overwritten the registry. Please review the physical document to verify "
                "the correct certificate amount."
            ),
            observed_value=f"Entered: {entered_amount}, Extracted: {doc_amount}",
            expected_value=f"Entered amount matching extracted certificate amount ({doc_amount})",
            evidence_refs=[rec.get("document_version_id", "")],
            suggested_action=(
                "Compare the entered amount with the certificate amount printed on the physical FDR document. "
                "If the entered amount was a typo, update the instrument. If the machine extraction misread "
                "the document, dismiss this finding with a review note."
            ),
            fingerprint_key=f"entered={entered_amount},extracted={doc_amount}",
        )


class CrossSourceReferenceRule(BaseValidationRule):
    """
    VAL-XSRC-002 — Compare entered reference number against machine-extracted suggestion.

    Normalizes whitespace and common formatting delimiters (slashes, hyphens)
    before comparing.
    """
    rule_id = "VAL-XSRC-002"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.CROSS_SOURCE_RECONCILIATION
    severity = RuleSeverity.HIGH
    description = (
        "Reconciles entered instrument reference number with machine-extracted certificate reference."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        if not context.reference_number or not context.reference_number.strip():
            return self._unable_to_evaluate("Instrument reference number is not set.")

        rec, reason = _get_usable_extraction(context)
        if not rec:
            return self._unable_to_evaluate(reason or "Extraction unavailable.")

        if rec.get("is_stale"):
            return self._unable_to_evaluate(
                "Document extraction is stale. Reprocess current document version."
            )

        doc_ref = rec.get("doc_reference_number")
        if not doc_ref or not str(doc_ref).strip():
            return self._unable_to_evaluate(
                "Extracted document record does not contain a certificate reference number."
            )

        norm_entered = normalize_reference_number(context.reference_number)
        norm_extracted = normalize_reference_number(doc_ref)

        if norm_entered == norm_extracted:
            return self._pass(
                f"Entered reference ('{context.reference_number}') matches extracted suggestion ('{doc_ref}')."
            )

        return self._make_result(
            outcome=RuleOutcome.FAIL,
            title="Discrepancy between entered reference number and extracted document reference",
            explanation=(
                f"The entered instrument reference ('{context.reference_number}', normalized: '{norm_entered}') "
                f"does not match the machine-extracted certificate reference ('{doc_ref}', normalized: '{norm_extracted}'). "
                "Machine extractions are suggestions and do not override registry values. Review the original certificate."
            ),
            observed_value=f"Entered: '{context.reference_number}', Extracted: '{doc_ref}'",
            expected_value=f"Matching certificate reference ('{doc_ref}')",
            evidence_refs=[rec.get("document_version_id", "")],
            suggested_action=(
                "Verify the reference number printed on the original bank FDR certificate. "
                "Update the instrument record if a typographical error occurred during data entry."
            ),
            fingerprint_key=f"entered={norm_entered},extracted={norm_extracted}",
        )


class CrossSourceDateRule(BaseValidationRule):
    """
    VAL-XSRC-003 — Compare entered issue and maturity dates against extracted suggestions.
    """
    rule_id = "VAL-XSRC-003"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.CROSS_SOURCE_RECONCILIATION
    severity = RuleSeverity.HIGH
    description = (
        "Reconciles entered instrument issue and maturity dates with machine-extracted certificate dates."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        rec, reason = _get_usable_extraction(context)
        if not rec:
            return self._unable_to_evaluate(reason or "Extraction unavailable.")

        if rec.get("is_stale"):
            return self._unable_to_evaluate("Document extraction is stale. Reprocess current document.")

        doc_issue_str = rec.get("doc_issue_date_str")
        doc_maturity_str = rec.get("doc_maturity_date_str")

        if not doc_issue_str and not doc_maturity_str:
            return self._unable_to_evaluate("No date values present in extracted document record.")

        mismatches = []
        if doc_issue_str and context.issue_date:
            try:
                parsed_doc_issue = date.fromisoformat(str(doc_issue_str).strip())
                if context.issue_date != parsed_doc_issue:
                    mismatches.append(
                        f"Issue date: entered={context.issue_date}, extracted={parsed_doc_issue}"
                    )
            except Exception:
                pass

        if doc_maturity_str and context.maturity_date:
            try:
                parsed_doc_maturity = date.fromisoformat(str(doc_maturity_str).strip())
                if context.maturity_date != parsed_doc_maturity:
                    mismatches.append(
                        f"Maturity date: entered={context.maturity_date}, extracted={parsed_doc_maturity}"
                    )
            except Exception:
                pass

        if not mismatches:
            return self._pass("Entered dates match extracted document date suggestions.")

        return self._make_result(
            outcome=RuleOutcome.FAIL,
            title="Discrepancy between entered instrument dates and extracted document dates",
            explanation=(
                "One or more entered instrument dates differ from the machine-extracted document suggestions: "
                + "; ".join(mismatches)
                + ". Review the physical FDR certificate to confirm authoritative dates."
            ),
            observed_value="; ".join(mismatches),
            expected_value="Entered dates matching extracted certificate dates",
            evidence_refs=[rec.get("document_version_id", "")],
            suggested_action="Verify issue and maturity dates against the physical bank receipt.",
            fingerprint_key=f"mismatches={';'.join(sorted(mismatches))}",
        )


class CrossSourceBankRule(BaseValidationRule):
    """
    VAL-XSRC-004 — Compare entered bank name with machine-extracted bank name.
    """
    rule_id = "VAL-XSRC-004"
    rule_version = "1.0"
    rule_type = RuleType.HEURISTIC
    category = FindingCategory.CROSS_SOURCE_RECONCILIATION
    severity = RuleSeverity.MEDIUM
    description = (
        "Compares entered issuing bank name with machine-extracted certificate bank name."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        if not context.bank_name:
            return self._unable_to_evaluate("Bank name not specified on instrument.")

        rec, reason = _get_usable_extraction(context)
        if not rec:
            return self._unable_to_evaluate(reason or "Extraction unavailable.")

        if rec.get("is_stale"):
            return self._unable_to_evaluate("Document extraction is stale. Reprocess current document.")

        doc_bank = rec.get("doc_bank_name")
        if not doc_bank or not str(doc_bank).strip():
            return self._unable_to_evaluate("Extracted bank name is empty or missing.")

        norm_entered = normalize_bank_name(context.bank_name)
        norm_extracted = normalize_bank_name(doc_bank)

        # Check match or containment
        if norm_entered == norm_extracted or norm_entered in norm_extracted or norm_extracted in norm_entered:
            return self._pass(
                f"Entered bank name '{context.bank_name}' aligns with extracted suggestion '{doc_bank}'."
            )

        return self._make_result(
            outcome=RuleOutcome.WARNING,
            title="Issuing bank mismatch between entered record and extracted document",
            explanation=(
                f"The entered issuing bank ('{context.bank_name}') differs from the machine-extracted "
                f"bank name ('{doc_bank}'). This is an advisory observation requiring human review."
            ),
            observed_value=f"Entered: '{context.bank_name}', Extracted: '{doc_bank}'",
            expected_value=f"Matching bank name ('{doc_bank}')",
            evidence_refs=[rec.get("document_version_id", "")],
            suggested_action="Review the issuing bank name on the FDR certificate.",
            fingerprint_key=f"entered={norm_entered},extracted={norm_extracted}",
        )


class CrossSourceLienRule(BaseValidationRule):
    """
    VAL-XSRC-006 — Compare entered lien holder with extracted lien holder text,
    ONLY where explicit and readable in the extraction.
    """
    rule_id = "VAL-XSRC-006"
    rule_version = "1.0"
    rule_type = RuleType.HEURISTIC
    category = FindingCategory.LIEN_VALIDITY
    severity = RuleSeverity.MEDIUM
    description = (
        "Compares entered lien holder with machine-extracted lien text only when explicit and readable."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        rec, reason = _get_usable_extraction(context)
        if not rec:
            return self._not_applicable("No document extraction available for lien holder verification.")

        doc_lien = rec.get("doc_lien_holder")
        confidence = rec.get("doc_lien_holder_confidence", 0.0) or 0.0

        # Only evaluate where explicit, readable, and confident
        if not doc_lien or not str(doc_lien).strip() or confidence < 0.70:
            return self._not_applicable(
                "Document extraction does not contain explicit, high-confidence lien holder text."
            )

        entered_lien = (context.lien_holder or "").strip().lower()
        extracted_lien = str(doc_lien).strip().lower()

        # Check alignment (e.g. AICTE / Member Secretary AICTE / regional officer)
        if entered_lien and (entered_lien in extracted_lien or extracted_lien in entered_lien or "aicte" in extracted_lien):
            return self._pass(f"Lien holder text aligns with extracted certificate text ('{doc_lien}').")

        return self._make_result(
            outcome=RuleOutcome.WARNING,
            title="Lien holder text differs between entered record and extracted document",
            explanation=(
                f"The entered lien holder ('{context.lien_holder or '[none]'}') differs from the "
                f"machine-extracted lien endorsement text ('{doc_lien}'). Human review is required."
            ),
            observed_value=f"Entered: '{context.lien_holder}', Extracted: '{doc_lien}'",
            expected_value="Matching lien holder endorsement text",
            evidence_refs=[rec.get("document_version_id", "")],
            suggested_action="Inspect the lien endorsement stamp or clause on the FDR receipt.",
            fingerprint_key=f"entered={entered_lien},extracted={extracted_lien}",
        )


# Self-register all reconciliation rules
rule_registry.register(StaleDocumentExtractionRule())
rule_registry.register(CrossSourceAmountRule())
rule_registry.register(CrossSourceReferenceRule())
rule_registry.register(CrossSourceDateRule())
rule_registry.register(CrossSourceBankRule())
rule_registry.register(CrossSourceLienRule())
