"""
Module 3 — Validation Rules: Amount Consistency Checks

VAL-AMT-001: Instrument amount must be positive (> 0).
VAL-AMT-002: Instrument amount must meet the minimum configured policy threshold,
             if such a policy is configured for the institution or globally.
             Returns UNABLE_TO_EVALUATE if no active policy is configured.

Safety note: This rule does NOT invent or hard-code AICTE deposit amounts.
It only evaluates when a validated, authorized policy value exists in the config store.
"""
from decimal import Decimal

from app.modules.validation.enums import (
    FindingCategory, RuleOutcome, RuleSeverity, RuleType,
)
from app.modules.validation.registry import (
    BaseValidationRule, RuleContext, RuleResult, rule_registry,
)

_POLICY_KEY_MIN_AMOUNT = "MIN_DEPOSIT_AMOUNT_INR"


class AmountPositiveRule(BaseValidationRule):
    """
    VAL-AMT-001 — Instrument amount must be greater than zero.

    This is a fundamental integrity check that does not depend on policy config.
    """
    rule_id = "VAL-AMT-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.AMOUNT_CONSISTENCY
    severity = RuleSeverity.CRITICAL
    description = "Instrument deposit amount must be greater than zero."
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        amount = context.amount_decimal

        if amount is None:
            return self._unable_to_evaluate(
                "Instrument amount is not available in the evaluation context."
            )

        try:
            amt_dec = Decimal(str(amount))
        except Exception:
            return self._unable_to_evaluate(
                f"Instrument amount could not be parsed as a decimal value: '{amount}'."
            )

        if amt_dec <= Decimal("0"):
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Instrument amount is not positive",
                explanation=(
                    f"The registered deposit amount ({amt_dec}) is zero or negative. "
                    "A valid FDR / security deposit must have a strictly positive principal amount."
                ),
                observed_value=str(amt_dec),
                expected_value="Amount > 0",
                suggested_action=(
                    "Correct the amount field in the instrument registry. "
                    "Verify against the original FDR certificate issued by the bank."
                ),
                fingerprint_key=f"amount={amt_dec}",
            )

        return self._pass(f"Amount {amt_dec} is positive.")


class AmountPolicyComplianceRule(BaseValidationRule):
    """
    VAL-AMT-002 — Instrument amount must meet the minimum policy threshold.

    The threshold is read from the policy configuration store.
    If no active policy is configured (globally or for this institution),
    this rule returns UNABLE_TO_EVALUATE with an explanatory message.

    IMPORTANT: This rule never invents or hard-codes a threshold value.
    """
    rule_id = "VAL-AMT-002"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.POLICY_COMPLIANCE
    severity = RuleSeverity.HIGH
    description = (
        "Instrument deposit amount must meet the minimum threshold configured "
        "in the active policy for this institution or globally."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        amount = context.amount_decimal

        if amount is None:
            return self._unable_to_evaluate(
                "Instrument amount is not available in the evaluation context."
            )

        # Look up the policy value
        min_amount_raw = context.policy.get(_POLICY_KEY_MIN_AMOUNT)
        if min_amount_raw is None:
            return self._unable_to_evaluate(
                f"Required amount rule unavailable: no active, approved policy value is "
                f"configured for '{_POLICY_KEY_MIN_AMOUNT}' for this institution/case. "
                "A SYSTEM_ADMIN must configure the minimum deposit threshold before "
                "this check can be evaluated."
            )

        try:
            min_amount = Decimal(str(min_amount_raw))
            amt_dec = Decimal(str(amount))
        except Exception as exc:
            return self._unable_to_evaluate(
                f"Policy amount value could not be parsed as a decimal: {exc}."
            )

        policy_ref = context.policy.get("_policy_version_ref", "unknown")

        if amt_dec < min_amount:
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Instrument amount is below the required minimum",
                explanation=(
                    f"The registered deposit amount ({amt_dec} {context.currency}) is below the "
                    f"configured minimum threshold ({min_amount} INR) as per the active policy "
                    f"(version: {policy_ref}). The instrument does not satisfy the minimum deposit "
                    "requirement for regulatory compliance."
                ),
                observed_value=f"{amt_dec} {context.currency}",
                expected_value=f">= {min_amount} INR (policy: {policy_ref})",
                suggested_action=(
                    "Verify the correct deposit amount with the institution. "
                    "If the FDR amount has been increased, update the registry with the "
                    "new certificate details and upload evidence."
                ),
                policy_version_ref=str(policy_ref),
                fingerprint_key=f"amount={amt_dec},min={min_amount},policy={policy_ref}",
            )

        return self._pass(
            f"Amount {amt_dec} meets or exceeds minimum threshold {min_amount} (policy: {policy_ref})."
        )


# Self-register
rule_registry.register(AmountPositiveRule())
rule_registry.register(AmountPolicyComplianceRule())
