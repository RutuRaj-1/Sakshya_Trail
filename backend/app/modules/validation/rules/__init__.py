"""
Module 3 — Validation Rules Package
Individual rule implementations are in submodules.
All rules self-register with the global rule_registry on import.
"""
from app.modules.validation.rules.date_rules import (
    MaturityAfterIssueDateRule,
    MaturityNotExpiredRule,
    ConfiguredValidityPeriodRule,
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
    DocumentCompletenessIntegrationRule,
)
from app.modules.validation.rules.duplicate_rules import (
    PotentialDuplicateHeuristicRule,
)
from app.modules.validation.rules.required_rules import (
    RequiredFieldsRule,
)
from app.modules.validation.rules.institution_rules import (
    InstitutionConsistencyRule,
)
from app.modules.validation.rules.consistency_rules import (
    BasicDataConsistencyRule,
)

__all__ = [
    "MaturityAfterIssueDateRule",
    "MaturityNotExpiredRule",
    "ConfiguredValidityPeriodRule",
    "AmountPositiveRule",
    "AmountPolicyComplianceRule",
    "ReferenceNumberFormatRule",
    "LienMarkedRule",
    "FDRCopyPresentRule",
    "DocumentCompletenessIntegrationRule",
    "PotentialDuplicateHeuristicRule",
    "RequiredFieldsRule",
    "InstitutionConsistencyRule",
    "BasicDataConsistencyRule",
]

