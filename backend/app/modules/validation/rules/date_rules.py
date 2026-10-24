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

        MIN_SUPPORTED_YEAR = 1990
        MAX_SUPPORTED_YEAR = 2100
        if (
            issue.year < MIN_SUPPORTED_YEAR
            or issue.year > MAX_SUPPORTED_YEAR
            or maturity.year < MIN_SUPPORTED_YEAR
            or maturity.year > MAX_SUPPORTED_YEAR
        ):
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Instrument dates fall outside supported system bounds",
                explanation=(
                    f"Recorded dates (issue: {issue.isoformat()}, maturity: {maturity.isoformat()}) "
                    f"fall outside supported system calendar bounds ({MIN_SUPPORTED_YEAR} to {MAX_SUPPORTED_YEAR})."
                ),
                observed_value=f"Issue: {issue.isoformat()}, Maturity: {maturity.isoformat()}",
                expected_value=f"Dates between {MIN_SUPPORTED_YEAR}-01-01 and {MAX_SUPPORTED_YEAR}-12-31",
                suggested_action="Review the source document and correct the date values.",
                fingerprint_key=f"bounds_issue={issue.isoformat()},maturity={maturity.isoformat()}",
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


class ConfiguredValidityPeriodRule(BaseValidationRule):
    """
    VAL-DATE-003 — Configured Validity Period Rule.

    Any configured validity-period rule is applied ONLY when the governing period
    and applicability are actually configured in policy (MIN_VALIDITY_DAYS / MAX_VALIDITY_DAYS).
    Does not infer a universal renewal or maturity requirement.
    """
    rule_id = "VAL-DATE-003"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.DATE_CONSISTENCY
    severity = RuleSeverity.HIGH
    description = (
        "Verify instrument validity term against policy configuration when governing "
        "period is configured."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        min_days_raw = context.policy.get("MIN_VALIDITY_DAYS")
        max_days_raw = context.policy.get("MAX_VALIDITY_DAYS")
        policy_ref = context.policy.get("_policy_version_ref")

        if min_days_raw is None and max_days_raw is None:
            return self._not_applicable(
                "No validity period policy (MIN_VALIDITY_DAYS / MAX_VALIDITY_DAYS) is configured. "
                "Validity period check is not applicable."
            )

        issue = context.issue_date
        maturity = context.maturity_date

        if issue is None or maturity is None:
            return self._unable_to_evaluate(
                "Issue date or maturity date is absent from the instrument record."
            )

        term_days = (maturity - issue).days

        if min_days_raw is not None:
            try:
                min_days = int(min_days_raw)
                if term_days < min_days:
                    return self._make_result(
                        outcome=RuleOutcome.FAIL,
                        title="Instrument term is shorter than configured minimum validity period",
                        explanation=(
                            f"The instrument validity period ({term_days} days) is less than the configured "
                            f"minimum term of {min_days} days as per active policy ({policy_ref})."
                        ),
                        observed_value=f"Validity: {term_days} days",
                        expected_value=f">= {min_days} days (policy: {policy_ref})",
                        suggested_action="Review the certificate term and confirm against policy guidelines.",
                        policy_version_ref=str(policy_ref) if policy_ref else None,
                        fingerprint_key=f"term_days={term_days},min={min_days}",
                    )
            except (ValueError, TypeError) as exc:
                return self._unable_to_evaluate(f"Invalid MIN_VALIDITY_DAYS policy value: {exc}")

        if max_days_raw is not None:
            try:
                max_days = int(max_days_raw)
                if term_days > max_days:
                    return self._make_result(
                        outcome=RuleOutcome.FAIL,
                        title="Instrument term exceeds configured maximum validity period",
                        explanation=(
                            f"The instrument validity period ({term_days} days) exceeds the configured "
                            f"maximum term of {max_days} days as per active policy ({policy_ref})."
                        ),
                        observed_value=f"Validity: {term_days} days",
                        expected_value=f"<= {max_days} days (policy: {policy_ref})",
                        suggested_action="Review the certificate term and confirm against policy guidelines.",
                        policy_version_ref=str(policy_ref) if policy_ref else None,
                        fingerprint_key=f"term_days={term_days},max={max_days}",
                    )
            except (ValueError, TypeError) as exc:
                return self._unable_to_evaluate(f"Invalid MAX_VALIDITY_DAYS policy value: {exc}")

        return self._pass(
            f"Instrument validity term of {term_days} days complies with configured policy bounds."
        )


# Self-register
rule_registry.register(MaturityAfterIssueDateRule())
rule_registry.register(MaturityNotExpiredRule())
rule_registry.register(ConfiguredValidityPeriodRule())
