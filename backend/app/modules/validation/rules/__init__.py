"""
Module 3 — Validation Rules Package
Individual rule implementations are in submodules.
All rules self-register with the global rule_registry on import.
"""
from app.modules.validation.rules.date_rules import (
    MaturityAfterIssueDateRule,
    MaturityNotExpiredRule,
)
from app.modules.validation.rules.amount_rules import (
    AmountPositiveRule,
    AmountPolicyComplianceRule,
)
from app.modules.validation.rules.reference_rules import (
    ReferenceNumberFormatRule,
)
from app.modules.validation.rules.lien_rules import (
    LienMarkedRule,
)
from app.modules.validation.rules.document_rules import (
    FDRCopyPresentRule,
)
from app.modules.validation.rules.duplicate_rules import (
    PotentialDuplicateHeuristicRule,
)

__all__ = [
    "MaturityAfterIssueDateRule",
    "MaturityNotExpiredRule",
    "AmountPositiveRule",
    "AmountPolicyComplianceRule",
    "ReferenceNumberFormatRule",
    "LienMarkedRule",
    "FDRCopyPresentRule",
    "PotentialDuplicateHeuristicRule",
]
