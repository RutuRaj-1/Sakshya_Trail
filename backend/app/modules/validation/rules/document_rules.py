"""
Module 3 — Validation Rules: Document Completeness Checks

VAL-DOC-001: At least one document of category 'FDR_COPY' (or equivalent configured
             required category) must be present and in a processed/accepted state.

Missing evidence means UNABLE_TO_EVALUATE, not automatically suspicious.
"""
from app.modules.validation.enums import (
    FindingCategory, RuleOutcome, RuleSeverity, RuleType,
)
from app.modules.validation.registry import (
    BaseValidationRule, RuleContext, RuleResult, rule_registry,
)

# The document category code we require (matches DocumentCategory.code)
_REQUIRED_CATEGORY = "FDR_COPY"
_ACCEPTED_PROCESSING_STATES = {"PROCESSED", "CLEAN", "ACCEPTED", "SCAN_COMPLETE"}


class FDRCopyPresentRule(BaseValidationRule):
    """
    VAL-DOC-001 — At least one document of category FDR_COPY must be uploaded
    and in an accepted processing state.

    If no documents are available in the context at all, returns UNABLE_TO_EVALUATE
    (missing evidence ≠ invalid).
    If documents exist but none match the required category, returns FAIL.
    """
    rule_id = "VAL-DOC-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.DOCUMENT_COMPLETENESS
    severity = RuleSeverity.MEDIUM
    description = (
        "At least one FDR copy document (category: FDR_COPY) must be uploaded "
        "and in an accepted processing state."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        docs = context.available_documents

        if not docs:
            return self._unable_to_evaluate(
                "No document metadata is available for this instrument. "
                "Missing evidence is treated as unknown, not invalid — "
                "upload the FDR copy to enable document completeness checks."
            )

        # Find FDR_COPY documents
        fdr_copies = [
            d for d in docs
            if d.get("category", "").upper() == _REQUIRED_CATEGORY
        ]

        if not fdr_copies:
            all_categories = list({d.get("category", "UNKNOWN") for d in docs})
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="FDR copy document is missing",
                explanation=(
                    f"No document of category '{_REQUIRED_CATEGORY}' has been uploaded for this "
                    f"instrument. Available categories: {all_categories}. "
                    "An FDR copy is required to verify the certificate details against the "
                    "registered instrument data."
                ),
                observed_value=f"Available categories: {all_categories}",
                expected_value=f"At least one document with category '{_REQUIRED_CATEGORY}'",
                suggested_action=(
                    f"Upload the bank-issued Fixed Deposit Receipt as a document with "
                    f"category '{_REQUIRED_CATEGORY}'."
                ),
                fingerprint_key="fdr_copy=missing",
            )

        # Check if at least one is in an accepted state
        accepted = [
            d for d in fdr_copies
            if d.get("processing_status", "").upper() in _ACCEPTED_PROCESSING_STATES
        ]

        if not accepted:
            statuses = [d.get("processing_status", "UNKNOWN") for d in fdr_copies]
            # Build evidence refs from document version IDs
            evidence = [
                d["document_version_id"] for d in fdr_copies
                if d.get("document_version_id")
            ]
            return self._make_result(
                outcome=RuleOutcome.WARNING,
                title="FDR copy document is present but not yet processed",
                explanation=(
                    f"{len(fdr_copies)} FDR copy document(s) found, but none are in an accepted "
                    f"processing state. Current statuses: {statuses}. "
                    "Document processing must complete before content can be verified."
                ),
                observed_value=f"Processing statuses: {statuses}",
                expected_value=f"At least one in: {sorted(_ACCEPTED_PROCESSING_STATES)}",
                evidence_refs=evidence,
                suggested_action=(
                    "Wait for document processing to complete. If processing has stalled, "
                    "re-upload the document or contact the system administrator."
                ),
                fingerprint_key=f"fdr_copy=unprocessed,count={len(fdr_copies)}",
            )

        # At least one FDR_COPY is in an accepted state
        evidence = [
            d["document_version_id"] for d in accepted
            if d.get("document_version_id")
        ]
        return self._make_result(
            outcome=RuleOutcome.PASS,
            title="FDR copy document is present and accepted",
            explanation=(
                f"{len(accepted)} accepted FDR copy document version(s) found."
            ),
            evidence_refs=evidence,
            fingerprint_key="fdr_copy=present",
        )


# Self-register
rule_registry.register(FDRCopyPresentRule())


class DocumentCompletenessIntegrationRule(BaseValidationRule):
    """
    VAL-DOC-002 — Document Completeness Integration Rule (Rule E).

    Reads Module 2's existing checklist result if available.
    Does NOT reimplement the completeness engine in Module 3.
    If Module 2 has no applicable checklist/profile, reports the limitation explicitly
    rather than automatically declaring all document categories missing.
    """
    rule_id = "VAL-DOC-002"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.DOCUMENT_COMPLETENESS
    severity = RuleSeverity.HIGH
    description = (
        "Integrate Module 2 checklist result for document completeness verification. "
        "Reports explicit limitation when no Module 2 checklist profile is available."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        checklist = context.checklist_result

        # If Module 2 has no applicable checklist/profile, report limitation explicitly
        if checklist is None:
            return self._unable_to_evaluate(
                "Document completeness integration unavailable: No Module 2 checklist "
                "or document profile is configured for this instrument/case type. "
                "Completeness cannot be evaluated without an approved Module 2 checklist profile."
            )

        # Module 2 checklist result is present; inspect status and items
        is_complete = checklist.get("is_complete", False)
        items = checklist.get("items", [])
        evidence = checklist.get("evidence_refs", [])

        if not is_complete:
            missing_categories = [
                item.get("category", "UNKNOWN")
                for item in items
                if item.get("status") in ("MISSING", "REQUIRED_NOT_MET", "UNREADABLE")
            ]
            category_list_str = ", ".join(sorted(missing_categories)) if missing_categories else "Unsatisfied items"

            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Module 2 document completeness checklist has unsatisfied items",
                explanation=(
                    f"Module 2 checklist evaluation indicates incomplete documentation. "
                    f"Unsatisfied category requirements: {category_list_str}."
                ),
                observed_value=f"Unsatisfied: {missing_categories}",
                expected_value="All Module 2 checklist requirements satisfied (is_complete=True)",
                evidence_refs=evidence,
                suggested_action=(
                    "Upload the required documents identified in Module 2's checklist "
                    f"({category_list_str}) and ensure they reach PROCESSED status."
                ),
                fingerprint_key=f"checklist_incomplete={category_list_str}",
            )

        return self._pass(
            f"Module 2 document completeness checklist satisfied ({len(items)} items verified)."
        )


rule_registry.register(DocumentCompletenessIntegrationRule())
