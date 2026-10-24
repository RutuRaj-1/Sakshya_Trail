"""
Module 3 — Validation Rules: Reference Number Integrity

VAL-REF-001: Reference number must not be blank or consist only of whitespace.
             Reference must be at least 4 characters after trimming.
"""
import re

from app.modules.validation.enums import (
    FindingCategory, RuleOutcome, RuleSeverity, RuleType,
)
from app.modules.validation.registry import (
    BaseValidationRule, RuleContext, RuleResult, rule_registry,
)


class ReferenceNumberFormatRule(BaseValidationRule):
    """
    VAL-REF-001 — FDR reference number must be non-blank and meet a minimum
    meaningful length to be considered a valid certificate identifier.

    This rule does NOT validate against a specific bank's format (too institution-specific).
    It detects obviously empty or placeholder values.
    """
    rule_id = "VAL-REF-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.REFERENCE_INTEGRITY
    severity = RuleSeverity.HIGH
    description = (
        "FDR reference number must be non-blank and have a minimum meaningful length."
    )
    enabled = True

    _MIN_LENGTH = 4
    _PLACEHOLDER_PATTERN = re.compile(
        r"^(n/?a|nil|none|null|placeholder|test|xxx+|na|tbd|-)$",
        re.IGNORECASE,
    )

    def evaluate(self, context: RuleContext) -> RuleResult:
        ref = context.reference_number

        if not ref or not ref.strip():
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="FDR reference number is blank",
                explanation=(
                    "The instrument's reference number field is empty or contains only whitespace. "
                    "A valid FDR certificate reference number is required for traceability."
                ),
                observed_value="[empty]",
                expected_value="Non-blank reference number of at least 4 characters",
                suggested_action=(
                    "Enter the correct FDR certificate reference number as printed on the "
                    "original bank-issued Fixed Deposit Receipt."
                ),
                fingerprint_key="ref=blank",
            )

        trimmed = ref.strip()

        if len(trimmed) < self._MIN_LENGTH:
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="FDR reference number is too short",
                explanation=(
                    f"The reference number '{trimmed}' is only {len(trimmed)} character(s) long, "
                    f"which is below the minimum of {self._MIN_LENGTH} characters required for a "
                    "meaningful FDR certificate identifier."
                ),
                observed_value=f"Length {len(trimmed)}: '{trimmed}'",
                expected_value=f"At least {self._MIN_LENGTH} characters",
                suggested_action=(
                    "Verify and correct the reference number against the original certificate."
                ),
                fingerprint_key=f"ref_length={len(trimmed)}",
            )

        if self._PLACEHOLDER_PATTERN.match(trimmed):
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="FDR reference number appears to be a placeholder",
                explanation=(
                    f"The reference number '{trimmed}' matches a known placeholder or test value "
                    "pattern and is not a valid FDR certificate identifier."
                ),
                observed_value=f"'{trimmed}'",
                expected_value="Actual FDR certificate reference number",
                suggested_action=(
                    "Replace the placeholder with the actual FDR reference number as printed "
                    "on the bank-issued certificate."
                ),
                fingerprint_key=f"ref_placeholder={trimmed.lower()}",
            )

        return self._pass(
            f"Reference number '{trimmed}' meets minimum format requirements."
        )


# Self-register
rule_registry.register(ReferenceNumberFormatRule())
