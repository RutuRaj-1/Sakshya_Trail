"""
Module 3 — Validation Rules: Required Instrument Fields Check

VAL-REQ-001: Evaluates configured fields required for the applicable instrument/case type.
The exact required field set is configurable via policy (key: 'REQUIRED_INSTRUMENT_FIELDS').
If not set in policy, sensible default required fields are evaluated:
institution_id, instrument_type, bank_name, reference_number, amount, issue_date, maturity_date.
"""
from typing import Any, Dict, List, Optional
from decimal import Decimal

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

_POLICY_KEY_REQUIRED_FIELDS = "REQUIRED_INSTRUMENT_FIELDS"
_DEFAULT_REQUIRED_FIELDS = [
    "institution_id",
    "instrument_type",
    "bank_name",
    "reference_number",
    "amount",
    "issue_date",
    "maturity_date",
]


class RequiredFieldsRule(BaseValidationRule):
    """
    VAL-REQ-001 — Required Instrument Fields Rule.

    Evaluates configured fields required for the applicable instrument/case type.
    The exact required field set is configurable via policy (key: 'REQUIRED_INSTRUMENT_FIELDS').
    """
    rule_id = "VAL-REQ-001"
    rule_version = "1.0"
    rule_type = RuleType.DETERMINISTIC
    category = FindingCategory.CROSS_FIELD_CONSISTENCY
    severity = RuleSeverity.HIGH
    description = (
        "Evaluate configured fields required for the applicable instrument/case type. "
        "Configurable via policy without hard-coding universal mandates."
    )
    enabled = True

    def evaluate(self, context: RuleContext) -> RuleResult:
        # 1. Resolve required fields list from policy or default
        policy_cfg = context.policy.get(_POLICY_KEY_REQUIRED_FIELDS)
        policy_ref = context.policy.get("_policy_version_ref")

        if policy_cfg:
            if isinstance(policy_cfg, list):
                required_fields = [str(f).strip() for f in policy_cfg if str(f).strip()]
            elif isinstance(policy_cfg, str):
                required_fields = [f.strip() for f in policy_cfg.split(",") if f.strip()]
            else:
                return self._unable_to_evaluate(
                    f"Configured policy '{_POLICY_KEY_REQUIRED_FIELDS}' has invalid type: {type(policy_cfg).__name__}."
                )
        else:
            required_fields = list(_DEFAULT_REQUIRED_FIELDS)

        # 2. Extract fields from context
        field_values: Dict[str, Any] = {
            "institution_id": context.institution_id,
            "instrument_type": context.instrument_type,
            "bank_name": context.bank_name,
            "reference_number": context.reference_number,
            "amount": context.amount_decimal,
            "issue_date": context.issue_date,
            "maturity_date": context.maturity_date,
            "lien_holder": context.lien_holder,
            "assigned_office": context.assigned_office,
            "branch": context.branch,
        }

        missing_fields: List[str] = []
        for field_name in required_fields:
            val = field_values.get(field_name)
            if val is None:
                missing_fields.append(field_name)
            elif isinstance(val, str) and not val.strip():
                missing_fields.append(field_name)

        if missing_fields:
            sorted_missing = sorted(missing_fields)
            return self._make_result(
                outcome=RuleOutcome.FAIL,
                title="Required instrument fields missing",
                explanation=(
                    f"The instrument record is missing required field(s): {', '.join(sorted_missing)}. "
                    f"Configured required fields: {', '.join(required_fields)}."
                ),
                observed_value=f"Missing: {sorted_missing}",
                expected_value=f"Required: {required_fields}",
                suggested_action=(
                    f"Provide values for missing field(s): {', '.join(sorted_missing)} "
                    "in the instrument registry."
                ),
                policy_version_ref=str(policy_ref) if policy_ref else None,
                fingerprint_key=f"missing={','.join(sorted_missing)}",
            )

        return self._pass(
            f"All {len(required_fields)} configured required fields are present."
        )


rule_registry.register(RequiredFieldsRule())
