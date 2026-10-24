"""
Module 3 — Validation Rules: Potential Duplicate Detection (Heuristic)

VAL-DUP-001: Heuristic / advisory check — detects whether other instruments
             share the same normalized bank name and reference number.

This is labelled HEURISTIC because duplicate detection is advisory:
- Regulatory process allows intentional duplicate registration with explicit confirmation.
- A duplicate reference does NOT conclusively prove fraud or forgery.
- The finding MUST carry the advisory prefix and require human review.
"""
from app.modules.validation.enums import (
    FindingCategory, RuleOutcome, RuleSeverity, RuleType,
)
from app.modules.validation.registry import (
    BaseValidationRule, RuleContext, RuleResult, rule_registry,
)


class PotentialDuplicateHeuristicRule(BaseValidationRule):
    """
    VAL-DUP-001 — Advisory: potential duplicate instrument detected.

    Uses the existing_open_findings context field which the engine populates
    with a pre-computed count of sibling instruments sharing the same
    (bank_name, reference_number) combination.

    The engine sets context.policy['_duplicate_sibling_count'] to an integer
    count of other instruments with matching normalized bank+reference.

    If the count is > 0, this is an advisory WARNING — never a hard FAIL
    that blocks processing, and never labelled as fraud or forgery.
    """
    rule_id = "VAL-DUP-001"
    rule_version = "1.0"
    rule_type = RuleType.HEURISTIC
    category = FindingCategory.POTENTIAL_DUPLICATE
    severity = RuleSeverity.MEDIUM
    description = (
        "Advisory heuristic: detects whether other instruments share the same "
        "issuing bank and reference number (potential duplicate). "
        "Requires human review — does not constitute fraud or forgery determination."
    )
    enabled = True

    _CONTEXT_KEY = "_duplicate_sibling_count"
    _SIBLING_IDS_KEY = "_duplicate_sibling_ids"

    def evaluate(self, context: RuleContext) -> RuleResult:
        sibling_count = context.policy.get(self._CONTEXT_KEY)

        if sibling_count is None:
            return self._unable_to_evaluate(
                "Duplicate sibling count was not supplied in the evaluation context. "
                "The engine must populate policy['_duplicate_sibling_count'] before invoking this rule."
            )

        sibling_count = int(sibling_count)

        if sibling_count == 0:
            return self._pass(
                "No other instruments share the same issuing bank and reference number."
            )

        sibling_ids = context.policy.get(self._SIBLING_IDS_KEY, [])
        sibling_summary = f"{sibling_count} other instrument(s)"

        return self._make_result(
            outcome=RuleOutcome.WARNING,
            # Note: _make_result() will add "[Advisory — human review required]" prefix
            # because rule_type is HEURISTIC.
            title="Potential duplicate instrument detected",
            explanation=(
                f"{sibling_summary} in the registry share the same issuing bank "
                f"('{context.bank_name}') and reference number "
                f"('{context.reference_number}'). This may indicate a duplicate "
                "registration, a renewed FDR reusing the same reference, or a "
                "data entry error. This is an advisory observation only — it does "
                "NOT confirm fraud or forgery. Human review is required to determine "
                "the appropriate action."
            ),
            observed_value=f"{sibling_count} sibling instrument(s) with matching bank+reference",
            expected_value="No other instruments with same bank name and reference number",
            evidence_refs=[str(sid) for sid in sibling_ids if sid],
            suggested_action=(
                "Review the matching instrument records listed in the evidence references. "
                "If this is a legitimate re-registration (e.g. renewal), ensure the previous "
                "record is marked with the correct status. If this is a data entry error, "
                "correct the reference number."
            ),
            fingerprint_key=f"bank={context.bank_name.lower().strip()},ref={context.reference_number.lower().strip()}",
        )


# Self-register
rule_registry.register(PotentialDuplicateHeuristicRule())
