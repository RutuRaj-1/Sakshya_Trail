"""
Module 3 — Validation Rules: Date Consistency Checks

VAL-DATE-001: Maturity date must be strictly after issue date.
VAL-DATE-002: Instrument must not have passed its maturity date without a status update.
"""
from datetime import date

from app.modules.validation.enums import (
    FindingCategory, RuleOutcome, RuleSeverity, RuleType,
)
from app.modules.validation.registry import (
    BaseValidationRule, RuleContext, RuleResult, rule_registry,
)


class MaturityAfterIssueDateRule(BaseValidationRule):
    """
    VAL-DATE-001 — Maturity date must be strictly after issue date.

    This is a deterministic check against the instrument's own dates.
    If either date is missing, returns UNABLE_TO_EVALUATE.
    """
    rule_id = "VAL-DATE-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.DATE_CONSISTENCY
    severity = RuleSeverity.HIGH
    description = "Maturity date must be strictly later than issue date."
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        issue = context.issue_date
        maturity = context.maturity_date

        if issue is None or maturity is None:
            return self._unable_to_evaluate(
                "Issue date or maturity date is absent from the instrument record."
            )

        if maturity <= issue:
            observed = (
                f"Issue: {issue.isoformat()}, Maturity: {maturity.isoformat()}"
            )
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Maturity date is not after issue date",
                explanation=(
                    f"The instrument's maturity date ({maturity.isoformat()}) is not strictly "
                    f"later than its issue date ({issue.isoformat()}). This renders the FDR term "
                    "invalid. The instrument record must be corrected."
                ),
                observed_value=observed,
                expected_value="maturity_date > issue_date",
                suggested_action=(
                    "Correct the issue date or maturity date in the instrument registry. "
                    "Contact the issuing bank to obtain the correct certificate details."
                ),
                fingerprint_key=f"issue={issue.isoformat()},maturity={maturity.isoformat()}",
            )

        return self._pass(
            f"Maturity date ({maturity.isoformat()}) is after issue date ({issue.isoformat()})."
        )


class MaturityNotExpiredRule(BaseValidationRule):
    """
    VAL-DATE-002 — The instrument's maturity date must not be in the past
    for an instrument that is still in an active registry status.

    UNABLE_TO_EVALUATE if maturity date is missing.
    NOT_APPLICABLE for instruments already in terminal statuses (RELEASED, CANCELLED).
    WARNING (advisory) for instruments within 90 days of expiry.
    FAIL for already-expired instruments still showing active status.
    """
    rule_id = "VAL-DATE-002"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.DATE_CONSISTENCY
    severity = RuleSeverity.HIGH
    description = "Active instruments must not have a past maturity date."
    enabled = True

    _TERMINAL_STATUSES = {"RELEASED", "CANCELLED", "MATURED", "CLOSED"}
    _EXPIRY_WARNING_DAYS = 90

    def evaluate(self, context: RuleContext) -> RuleResult:
        maturity = context.maturity_date
        status = context.instrument_status

        if maturity is None:
            return self._unable_to_evaluate("Maturity date is absent from the instrument record.")

        if status in self._TERMINAL_STATUSES:
            return self._not_applicable(
                f"Instrument has terminal status '{status}'; maturity expiry check not applicable."
            )

        today = date.today()
        days_to_maturity = (maturity - today).days

        if days_to_maturity < 0:
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Instrument maturity date has passed",
                explanation=(
                    f"The FDR maturity date ({maturity.isoformat()}) is {abs(days_to_maturity)} "
                    f"day(s) in the past. The instrument status is '{status}', indicating it is "
                    "still active. This inconsistency requires investigation — the FDR may have "
                    "been renewed, released, or cancelled without a corresponding registry update."
                ),
                observed_value=f"Maturity: {maturity.isoformat()} ({abs(days_to_maturity)} days ago)",
                expected_value="Maturity date in future, or status updated to terminal state",
                suggested_action=(
                    "Verify the instrument's current status with the issuing bank. "
                    "Update the registry status to MATURED, RELEASED, or CANCELLED as appropriate. "
                    "If the FDR was renewed, register the renewal instrument separately."
                ),
                fingerprint_key=f"maturity={maturity.isoformat()},expired",
            )

        if 0 <= days_to_maturity <= self._EXPIRY_WARNING_DAYS:
            return self._make_result(
                outcome=RuleOutcome.WARNING,
                title="Instrument approaching maturity",
                explanation=(
                    f"The FDR matures in {days_to_maturity} day(s) ({maturity.isoformat()}). "
                    "Action may be required to renew or release the instrument before expiry."
                ),
                observed_value=f"Days to maturity: {days_to_maturity}",
                expected_value=f"Maturity more than {self._EXPIRY_WARNING_DAYS} days away",
                suggested_action=(
                    "Initiate renewal or release workflow before the maturity date. "
                    "Notify the institution to take timely action."
                ),
                fingerprint_key=f"maturity={maturity.isoformat()},expiring_soon",
            )

        return self._pass(
            f"Instrument matures on {maturity.isoformat()} ({days_to_maturity} days from today)."
        )


# Self-register
rule_registry.register(MaturityAfterIssueDateRule())
rule_registry.register(MaturityNotExpiredRule())
