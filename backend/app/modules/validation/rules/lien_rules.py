"""
Module 3 — Validation Rules: Lien Validity Checks

VAL-LIEN-001: Instrument must have a lien marked and a non-blank lien holder.
"""
from app.modules.validation.enums import (
    FindingCategory, RuleOutcome, RuleSeverity, RuleType,
)
from app.modules.validation.registry import (
    BaseValidationRule, RuleContext, RuleResult, rule_registry,
)


class LienMarkedRule(BaseValidationRule):
    """
    VAL-LIEN-001 — The FDR must have a lien marked and a non-blank lien holder.

    AICTE security deposits require the FDR to be pledged / lien-marked in favour
    of the regulatory authority. An instrument without a lien is not a valid
    security deposit instrument for regulatory purposes.

    NOT_APPLICABLE for non-FDR instrument types (future-proofing).
    """
    rule_id = "VAL-LIEN-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.LIEN_VALIDITY
    severity = RuleSeverity.HIGH
    description = (
        "FDR must have a lien marked in favour of the regulatory authority."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        if context.instrument_type != "FDR":
            return self._not_applicable(
                f"Lien check is specific to FDR instruments; instrument type is '{context.instrument_type}'."
            )

        lien_marked = context.lien_marked
        lien_holder = context.lien_holder

        issues = []

        if lien_marked is False:
            issues.append("Lien is not marked on this instrument.")

        if not lien_holder or not str(lien_holder).strip():
            issues.append("Lien holder is blank or missing.")

        if issues:
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="FDR lien is not properly established",
                explanation=(
                    "The FDR instrument does not have a valid lien configuration: "
                    + " ".join(issues)
                    + " A security deposit FDR must be pledged (lien-marked) in favour of "
                    "the regulatory authority before it can be accepted."
                ),
                observed_value=(
                    f"lien_marked={lien_marked}, lien_holder='{lien_holder or '[blank]'}'"
                ),
                expected_value="lien_marked=True and lien_holder is non-blank",
                suggested_action=(
                    "Request a lien letter from the issuing bank confirming lien marking in "
                    "favour of the regulatory authority. Update the registry once the lien is confirmed."
                ),
                fingerprint_key=f"lien_marked={lien_marked},lien_holder={'blank' if not lien_holder else 'set'}",
            )

        return self._pass(
            f"Lien is marked; lien holder: '{lien_holder}'."
        )


# Self-register
rule_registry.register(LienMarkedRule())
