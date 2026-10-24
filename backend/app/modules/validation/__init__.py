"""
Module 3 — Validation, Discrepancy & Explainable Intelligence
Package init — exports public API surface.
"""
from app.modules.validation.enums import (
    RuleOutcome,
    FindingStatus,
    RuleSeverity,
    RuleType,
    FindingCategory,
)
from app.modules.validation.models import (
    ValidationPolicyConfig,
    ValidationFinding,
    ValidationRun,
)
from app.modules.validation.registry import (
    BaseValidationRule,
    RuleResult,
    RuleContext,
    rule_registry,
    compute_finding_fingerprint,
)
# Import all rules to trigger self-registration
import app.modules.validation.rules  # noqa: F401

from app.modules.validation.router import router as validation_router

__all__ = [
    # Enums
    "RuleOutcome",
    "FindingStatus",
    "RuleSeverity",
    "RuleType",
    "FindingCategory",
    # Models
    "ValidationPolicyConfig",
    "ValidationFinding",
    "ValidationRun",
    # Registry
    "BaseValidationRule",
    "RuleResult",
    "RuleContext",
    "rule_registry",
    "compute_finding_fingerprint",
    # Router
    "validation_router",
]
