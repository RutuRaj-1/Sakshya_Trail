"""
Module 3 — Validation Rules: Basic Data Consistency

VAL-CONS-001: Deterministic cross-field consistency checks supported by existing fields:
- Inactive institution restrictions (active instrument under inactive institution).
- Contradictory fields where both values are available (e.g., joint_with_aicte=True but lien_marked=False,
  or lien_marked=True but lien_holder is blank).
- Invalid amount/date combinations.
- No speculative financial calculations.
"""
from decimal import Decimal
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


class BasicDataConsistencyRule(BaseValidationRule):
    """
    VAL-CONS-001 — Basic Data Consistency Rule (Rule F).

    Enforces deterministic cross-field consistency checks without adding speculative
    financial calculations.
    """
    rule_id = "VAL-CONS-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.CROSS_FIELD_CONSISTENCY
    severity = RuleSeverity.HIGH
    description = (
        "Deterministic cross-field consistency checks: inactive institution restrictions, "
        "contradictory joint/lien flags, and valid field combinations."
    )
    enabled = True

    _ACTIVE_INSTRUMENT_STATUSES = {"DRAFT", "REGISTERED", "SUBMITTED"}

    def evaluate(self, context: RuleContext) -> RuleResult:
        # 1. Inactive institution restriction
        if not context.institution_is_active and context.instrument_status in self._ACTIVE_INSTRUMENT_STATUSES:
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Active instrument registered under inactive institution",
                explanation=(
                    f"The instrument status is '{context.instrument_status}', but the parent institution "
                    f"'{context.institution_legal_name or context.institution_id}' is marked inactive. "
                    "Active instruments cannot be maintained for deactivated institutions without review."
                ),
                observed_value=f"Instrument status: {context.instrument_status}, Institution is_active: False",
                expected_value="Parent institution must be active for active instrument registrations",
                suggested_action="Review the parent institution operational status before proceeding.",
                fingerprint_key="inactive_institution_active_instrument",
            )

        # 2. Contradictory joint custody vs lien marked
        if context.joint_with_aicte is True and context.lien_marked is False:
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Contradictory joint custody and lien marking flags",
                explanation=(
                    "The instrument specifies joint custody with AICTE (joint_with_aicte=True), "
                    "but lien_marked is set to False. By regulatory convention, joint instruments "
                    "require lien marking."
                ),
                observed_value="joint_with_aicte=True, lien_marked=False",
                expected_value="lien_marked=True when joint_with_aicte=True",
                suggested_action="Correct the lien_marked or joint_with_aicte flag in the instrument record.",
                fingerprint_key="contradictory_joint_lien",
            )

        # 3. Lien marked but lien holder is missing or empty
        if context.lien_marked is True and (not context.lien_holder or not context.lien_holder.strip()):
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Lien is marked but lien holder is unspecified",
                explanation=(
                    "The instrument indicates that a lien is marked (lien_marked=True), but the "
                    "lien_holder field is empty or contains only whitespace."
                ),
                observed_value=f"lien_marked=True, lien_holder='{context.lien_holder or ''}'",
                expected_value="Non-empty lien_holder when lien_marked=True",
                suggested_action="Provide the legal entity name of the lien holder (e.g., 'AICTE Regulation Bureau').",
                fingerprint_key="lien_marked_empty_holder",
            )

        # 4. Invalid amount/date combination (e.g. non-positive amount with valid future dates)
        if context.amount_decimal is not None and context.maturity_date is not None:
            try:
                amt = Decimal(str(context.amount_decimal))
                if amt <= Decimal("0"):
                    return self._make_result(
                        outcome=RuleOutcome.FAIL,
                        title="Invalid amount and maturity date combination",
                        explanation=(
                            f"The recorded amount is {amt} while a future maturity date "
                            f"({context.maturity_date.isoformat()}) is registered. Non-positive amounts "
                            "cannot represent a valid active deposit term."
                        ),
                        observed_value=f"Amount: {amt}, Maturity: {context.maturity_date.isoformat()}",
                        expected_value="Amount > 0 for term deposits",
                        suggested_action="Verify and correct the instrument amount against the bank certificate.",
                        fingerprint_key=f"invalid_amt_date_combo={amt}",
                    )
            except Exception:
                pass

        return self._pass("Deterministic basic data consistency checks passed.")


rule_registry.register(BasicDataConsistencyRule())
