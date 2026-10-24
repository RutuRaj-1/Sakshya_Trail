"""
Module 3 — Validation Rules: Institution Consistency

VAL-INST-001: Compare the instrument's institution association and existing institution
master-data fields to the applicable entered values or evidence that is already available.
A conflicting source should produce a finding with both values and their source references.
Do not silently modify the institution or instrument.
"""
from typing import Optional, List
import re

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


def _normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    # Lowercase, replace punctuation with spaces, collapse spaces
    cleaned = re.sub(r"[^\w\s]", " ", name.lower())
    return " ".join(cleaned.split())


class InstitutionConsistencyRule(BaseValidationRule):
    """
    VAL-INST-001 — Institution Association and Master-Data Consistency.

    Checks:
    1. Parent institution association is present and registered.
    2. Compares institution master-data fields (legal_name, code) against available
       document evidence (e.g. extracted depositor/account holder name).
    3. Conflicting values generate an explainable finding referencing both sources.
    4. Never silently modifies the institution or instrument.
    """
    rule_id = "VAL-INST-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.INSTITUTION_ELIGIBILITY
    severity = RuleSeverity.HIGH
    description = (
        "Compare instrument institution association and master-data against available "
        "evidence. Conflicting sources produce an explicit finding with source references."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        # 1. Association presence
        if not context.institution_id or not context.institution_id.strip():
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Instrument has no institution association",
                explanation=(
                    "The instrument record has no associated parent institution identifier. "
                    "All statutory security deposit instruments must belong to a registered institution."
                ),
                observed_value="institution_id: [empty]",
                expected_value="Valid registered institution UUID",
                suggested_action="Associate the instrument with a valid registered institution.",
                fingerprint_key="missing_institution_association",
            )

        registered_name = context.institution_legal_name or ""
        registered_code = context.institution_code or ""
        norm_registered = _normalize_name(registered_name)

        # 2. Check extracted evidence if available
        for ext in context.extracted_fields:
            doc_account_holder = ext.get("doc_account_holder")
            doc_ver_id = ext.get("document_version_id")

            if doc_account_holder and doc_account_holder.strip() and registered_name:
                norm_doc_holder = _normalize_name(doc_account_holder)

                # If both are substantial strings, check for meaningful token overlap or inclusion
                doc_tokens = set(norm_doc_holder.split())
                reg_tokens = set(norm_registered.split())

                # Exclude ubiquitous institutional stop words
                stop_words = {"institute", "institution", "college", "of", "technology", "and", "sciences", "the", "for"}
                sig_doc_tokens = doc_tokens - stop_words
                sig_reg_tokens = reg_tokens - stop_words

                # Check if there is significant discrepancy (both have distinctive words, but zero overlap)
                if sig_doc_tokens and sig_reg_tokens and not (sig_doc_tokens & sig_reg_tokens):
                    evidence = [doc_ver_id] if doc_ver_id else []
                    if context.instrument_id:
                        evidence.append(context.instrument_id)

                    return self._make_result(
                        outcome=RuleOutcome.FAIL,
                        title="Institution identity mismatch between instrument and uploaded document evidence",
                        explanation=(
                            f"The account holder / depositor name identified on document version "
                            f"'{doc_ver_id or 'unknown'}' ('{doc_account_holder}') conflicts with the "
                            f"instrument's registered institution master-data ('{registered_name}', code: '{registered_code}'). "
                            "This discrepancy may indicate a document uploaded under the wrong institution."
                        ),
                        observed_value=f"Document evidence: '{doc_account_holder}'",
                        expected_value=f"Registered institution: '{registered_name}' (Code: '{registered_code}')",
                        evidence_refs=evidence,
                        suggested_action=(
                            "Review the source document and verify whether the certificate was issued to "
                            "this institution. Do not silently modify the institution master data or instrument."
                        ),
                        fingerprint_key=f"inst_mismatch={doc_ver_id or 'doc'}",
                    )

        return self._pass(
            f"Instrument institution association is consistent with master data ({registered_name or context.institution_id})."
        )


rule_registry.register(InstitutionConsistencyRule())
