"""
Module 3 — Validation Rules: Name Similarity Advisory Checks

Rule:
- VAL-SIM-001: Explainable Name Similarity Comparison (Institution Legal Name vs FDR Depositor)

Requirements:
- Shows both original strings.
- States the exact normalization and comparison method (difflib.SequenceMatcher / Gestalt pattern matching).
- Returns the computed similarity score.
- Exposes the configured threshold.
- Treated strictly as `Advisory — human review required`.
- Borderline matches do NOT automatically reject a submission or modify trust level.
- Never claims the similarity algorithm determines legal identity.
"""
from typing import Optional

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
from app.modules.validation.normalization import calculate_name_similarity


class NameSimilarityAdvisoryRule(BaseValidationRule):
    """
    VAL-SIM-001 — Explainable name similarity check between institution registered
    legal name and extracted document account holder / depositor name.
    """
    rule_id = "VAL-SIM-001"
    rule_version = "1.0"
    rule_type = RuleType.HEURISTIC
    category = FindingCategory.CROSS_SOURCE_RECONCILIATION
    severity = RuleSeverity.MEDIUM
    description = (
        "Compares institution registered legal name with machine-extracted certificate depositor name. "
        "Provides explainable similarity scoring. Advisory heuristic only."
    )
    enabled = True

    _DEFAULT_THRESHOLD = 0.85

    def evaluate(self, context: RuleContext) -> RuleResult:
        inst_name = context.institution_legal_name
        if not inst_name or not inst_name.strip():
            return self._unable_to_evaluate(
                "Institution legal name is not available in evaluation context."
            )

        if not context.extracted_fields:
            return self._unable_to_evaluate(
                "No document extraction records available for name comparison."
            )

        # Locate first completed/partial extraction record with account holder name
        target_rec = None
        for rec in context.extracted_fields:
            if rec.get("is_stale"):
                continue
            if rec.get("doc_account_holder"):
                target_rec = rec
                break

        if not target_rec or not target_rec.get("doc_account_holder"):
            return self._unable_to_evaluate(
                "Extracted document record does not contain an account holder / depositor name."
            )

        extracted_name = str(target_rec["doc_account_holder"]).strip()
        threshold = float(context.policy.get("NAME_SIMILARITY_THRESHOLD", self._DEFAULT_THRESHOLD))

        score, norm_a, norm_b = calculate_name_similarity(inst_name, extracted_name)

        # Exact match
        if score == 1.0 or norm_a == norm_b:
            return self._pass(
                f"Depositor name '{extracted_name}' matches registered institution legal name '{inst_name}' exactly."
            )

        # Borderline match / spelling variant (e.g. score >= threshold)
        if score >= threshold:
            return self._make_result(
                outcome=RuleOutcome.WARNING,
                title="Depositor name spelling variation detected",
                explanation=(
                    f"String A (Registered Institution Legal Name): '{inst_name}'\n"
                    f"String B (Extracted FDR Depositor Name): '{extracted_name}'\n"
                    "Comparison Method: difflib.SequenceMatcher (Gestalt pattern matching) after prefix, "
                    "punctuation, and whitespace normalization.\n"
                    f"Computed Similarity Score: {score:.3f} (Configured Threshold: {threshold:.2f}).\n"
                    "The depositor name appears to be a genuine spelling variant, abbreviation, or slight "
                    "variation of the registered institution name. Human review is required to verify identity. "
                    "Advisory note: This similarity algorithm is an advisory heuristic only and does not "
                    "determine legal identity. Borderline matches do not reject a submission or modify trust."
                ),
                observed_value=f"Similarity score: {score:.3f} (extracted: '{extracted_name}')",
                expected_value=f"Similarity >= 1.0 (exact match with '{inst_name}')",
                evidence_refs=[target_rec.get("document_version_id", "")],
                suggested_action=(
                    "Verify the depositor name printed on the physical FDR receipt against institutional "
                    "incorporation/registration documents. If this is a valid alias, accept the variation."
                ),
                fingerprint_key=f"name_a={norm_a},name_b={norm_b},score={score:.3f}",
            )

        # Dissimilar name (score < threshold)
        return self._make_result(
            outcome=RuleOutcome.WARNING,
            title="Depositor name differs significantly from registered institution legal name",
            explanation=(
                f"String A (Registered Institution Legal Name): '{inst_name}'\n"
                f"String B (Extracted FDR Depositor Name): '{extracted_name}'\n"
                "Comparison Method: difflib.SequenceMatcher after prefix, punctuation, and whitespace normalization.\n"
                f"Computed Similarity Score: {score:.3f} (Configured Threshold: {threshold:.2f}).\n"
                "The extracted depositor name does not closely match the registered institution legal name. "
                "Human scrutiny review is required to determine whether the deposit is held in the name of "
                "the institution, an parent trust/society, or an unrelated party. "
                "Advisory note: This similarity metric is an advisory indicator and does not determine legal identity."
            ),
            observed_value=f"Similarity score: {score:.3f} (extracted: '{extracted_name}')",
            expected_value=f"Similarity score >= {threshold:.2f} (matching '{inst_name}')",
            evidence_refs=[target_rec.get("document_version_id", "")],
            suggested_action=(
                "Scrutinize the FDR document and request trust deed / society registration linkage "
                "if the FDR was taken in the name of the sponsoring body rather than the college."
            ),
            fingerprint_key=f"name_a={norm_a},name_b={norm_b},score={score:.3f}",
        )


# Self-register
rule_registry.register(NameSimilarityAdvisoryRule())
