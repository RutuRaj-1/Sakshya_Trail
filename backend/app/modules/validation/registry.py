"""
Module 3 — Validation Engine
Rule Registry and Base Rule Interface

The registry is the single source of truth for all registered rule implementations.
Rules are registered by decorating a class (or by calling register() explicitly).

Design constraints
------------------
* No eval(), no exec(), no unrestricted dynamic loading.
* Each rule is an explicit Python class implementing BaseValidationRule.
* The registry maps stable string rule IDs to rule class instances.
* Enabling/disabling a rule is handled via the rule's `enabled` flag and by
  admin policy — not by deleting or monkey-patching the class.
"""
from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.validation.enums import (
    FindingCategory,
    RuleOutcome,
    RuleSeverity,
    RuleType,
)


# ---------------------------------------------------------------------------
# Rule execution result (in-memory; NOT the persisted finding)
# ---------------------------------------------------------------------------

@dataclass
class RuleResult:
    """
    Structured result returned by a single rule execution.

    This is an in-memory DTO — it is consumed by the engine and
    converted into ValidationFinding records (for FAIL / WARNING outcomes)
    or discarded (for PASS / NOT_APPLICABLE outcomes).
    """
    rule_id: str
    rule_version: str
    rule_type: RuleType
    outcome: RuleOutcome
    category: FindingCategory
    severity: RuleSeverity

    # Human-readable
    title: str
    explanation: str

    # Safe observed vs expected (MUST NOT contain raw sensitive identifiers)
    observed_value: Optional[str] = None
    expected_value: Optional[str] = None

    # Evidence UUIDs (document_version IDs, audit event IDs, etc.)
    evidence_refs: List[str] = field(default_factory=list)

    # Suggested action for the reviewer
    suggested_action: Optional[str] = None

    # Policy version that was active when this result was produced
    policy_version_ref: Optional[str] = None

    # Fingerprint inputs — used by the finding service to compute the finding fingerprint
    # The engine will hash (rule_id, rule_version, instrument_id, fingerprint_key)
    fingerprint_key: str = ""

    # Timestamp of evaluation
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_finding(self) -> bool:
        """Only FAIL and WARNING outcomes produce persisted findings."""
        return self.outcome in (RuleOutcome.FAIL, RuleOutcome.WARNING)

    @property
    def advisory_label(self) -> str:
        """Prefix for heuristic finding titles."""
        if self.rule_type == RuleType.HEURISTIC:
            return "[Advisory — human review required] "
        return ""


# ---------------------------------------------------------------------------
# Rule execution context (read-only snapshot passed to each rule)
# ---------------------------------------------------------------------------

@dataclass
class RuleContext:
    """
    Read-only context bundle passed to every rule execution.

    The engine populates this from live database queries before invoking
    any rule, so individual rules never need direct DB access (testability).

    Fields starting with 'instrument_' come from Instrument.
    Fields starting with 'documents_' come from related Document / DocumentVersion records.
    'policy' carries the active policy configuration values as a typed dict.
    'institution_' fields come from the parent Institution.

    Safety: this context does NOT carry raw document content, passwords, or tokens.
    """
    instrument_id: str
    institution_id: str

    # Instrument registry data
    instrument_status: str
    instrument_trust_level: str
    instrument_type: str
    bank_name: str
    reference_number: str
    amount_decimal: Optional[Any] = None           # Decimal or None
    currency: str = "INR"
    issue_date: Optional[Any] = None               # date or None
    maturity_date: Optional[Any] = None            # date or None
    lien_holder: Optional[str] = None
    lien_marked: Optional[bool] = None
    joint_with_aicte: Optional[bool] = None
    assigned_office: Optional[str] = None

    branch: Optional[str] = None
    lien_details: Optional[str] = None

    # Institution
    institution_is_active: bool = True
    institution_type: str = "TECHNICAL_INSTITUTE"
    institution_legal_name: Optional[str] = None
    institution_code: Optional[str] = None

    # Document metadata: list of dicts, each with keys:
    # {document_id, document_version_id, category, processing_status, sha256_hash, ...}
    # Content fields are NEVER included.
    available_documents: List[Dict[str, Any]] = field(default_factory=list)

    # Document completeness / checklist result from Module 2 (if available)
    checklist_result: Optional[Dict[str, Any]] = None

    # Extracted field metadata from document versions (if available)
    extracted_fields: List[Dict[str, Any]] = field(default_factory=list)

    # Policy configuration: {config_key: parsed_value}
    policy: Dict[str, Any] = field(default_factory=dict)

    # Snapshot of currently open findings for this instrument (for cross-check rules)
    existing_open_findings: List[Dict[str, Any]] = field(default_factory=list)

    # Caller metadata (for audit)
    triggered_by_user_id: Optional[str] = None
    run_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Abstract base rule
# ---------------------------------------------------------------------------

class BaseValidationRule(abc.ABC):
    """
    Contract that every validation rule must implement.

    Attributes (class-level, set by subclasses)
    -------------------------------------------
    rule_id : str
        Stable, human-readable rule identifier (e.g. 'VAL-DATE-001').
        Must be unique across the registry.
    rule_version : str
        Semantic version of this rule implementation (e.g. '1.0').
        Stored on every finding for historical traceability.
    rule_type : RuleType
        DETERMINISTIC or HEURISTIC.
    category : FindingCategory
        Default finding category for this rule.
    severity : RuleSeverity
        Default severity if the rule fires.
    description : str
        Short human-readable description of what the rule checks.
    enabled : bool
        Soft switch; disabled rules are skipped but remain registered.
    """
    rule_id: str = ""
    rule_version: str = "1.0"
    rule_type: RuleType = RuleType.DETERMINISTIC
    category: FindingCategory = FindingCategory.OTHER
    severity: RuleSeverity = RuleSeverity.MEDIUM
    description: str = ""
    enabled: bool = True

    @abc.abstractmethod
    def evaluate(self, context: RuleContext) -> RuleResult:
        """
        Execute the rule against the given context.

        Must return a RuleResult. Must NEVER raise unhandled exceptions —
        the engine wraps calls in try/except and records UNABLE_TO_EVALUATE
        if an unexpected error occurs.

        Must NOT modify context, the database, or the instrument.
        Must NOT set instrument trust level.
        """
        ...

    def _make_result(
        self,
        outcome: RuleOutcome,
        title: str,
        explanation: str,
        observed_value: Optional[str] = None,
        expected_value: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
        suggested_action: Optional[str] = None,
        policy_version_ref: Optional[str] = None,
        fingerprint_key: str = "",
    ) -> RuleResult:
        """Helper to build a correctly-typed RuleResult from rule attributes."""
        # Heuristic findings MUST carry the advisory prefix
        if self.rule_type == RuleType.HEURISTIC and outcome in (RuleOutcome.FAIL, RuleOutcome.WARNING):
            if not title.startswith("[Advisory"):
                title = f"[Advisory — human review required] {title}"

        return RuleResult(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            rule_type=self.rule_type,
            outcome=outcome,
            category=self.category,
            severity=self.severity,
            title=title,
            explanation=explanation,
            observed_value=observed_value,
            expected_value=expected_value,
            evidence_refs=evidence_refs or [],
            suggested_action=suggested_action,
            policy_version_ref=policy_version_ref,
            fingerprint_key=fingerprint_key,
        )

    def _pass(self, detail: str = "Check passed.") -> RuleResult:
        return self._make_result(RuleOutcome.PASS, "Pass", detail)

    def _not_applicable(self, reason: str) -> RuleResult:
        return self._make_result(RuleOutcome.NOT_APPLICABLE, "Not Applicable", reason)

    def _unable_to_evaluate(self, reason: str) -> RuleResult:
        return self._make_result(RuleOutcome.UNABLE_TO_EVALUATE, "Unable to Evaluate", reason)


# ---------------------------------------------------------------------------
# Rule registry
# ---------------------------------------------------------------------------

class RuleRegistry:
    """
    Central registry of all known validation rules.

    Rules are registered at import time using the @register decorator
    or by calling registry.register(rule_instance) directly.

    The registry is read-only after application startup. No rule can be
    added or removed at runtime through an API endpoint.
    """

    def __init__(self) -> None:
        self._rules: Dict[str, BaseValidationRule] = {}

    def register(self, rule: BaseValidationRule) -> None:
        """Register a rule instance. Raises ValueError on duplicate rule_id."""
        if not rule.rule_id:
            raise ValueError(f"Rule class {type(rule).__name__} has no rule_id set.")
        if rule.rule_id in self._rules:
            raise ValueError(
                f"Duplicate rule_id '{rule.rule_id}': already registered by "
                f"{type(self._rules[rule.rule_id]).__name__}."
            )
        self._rules[rule.rule_id] = rule

    def get(self, rule_id: str) -> Optional[BaseValidationRule]:
        """Return the rule with the given ID, or None if not found."""
        return self._rules.get(rule_id)

    def get_enabled_rules(self) -> List[BaseValidationRule]:
        """Return all currently enabled rules in stable sorted order."""
        return sorted(
            [r for r in self._rules.values() if r.enabled],
            key=lambda r: r.rule_id,
        )

    def list_all(self) -> List[Dict[str, Any]]:
        """Return a serializable summary of all registered rules."""
        result = []
        for r in sorted(self._rules.values(), key=lambda x: x.rule_id):
            result.append({
                "rule_id": r.rule_id,
                "rule_version": r.rule_version,
                "rule_type": r.rule_type.value,
                "category": r.category.value,
                "severity": r.severity.value,
                "description": r.description,
                "enabled": r.enabled,
            })
        return result

    def __len__(self) -> int:
        return len(self._rules)


# ---------------------------------------------------------------------------
# Singleton registry — imported by rules and the engine
# ---------------------------------------------------------------------------

rule_registry = RuleRegistry()


# ---------------------------------------------------------------------------
# Fingerprint helper
# ---------------------------------------------------------------------------

def compute_finding_fingerprint(
    instrument_id: str,
    rule_id: str,
    rule_version: str,
    fingerprint_key: str,
) -> str:
    """
    Compute a stable SHA-256 hex fingerprint for deduplicating findings.

    The fingerprint is derived from rule identity + instrument identity +
    a caller-supplied key (which can encode specific field values relevant
    to the rule, e.g. 'maturity_date=2025-01-01').

    This is intentionally NOT globally unique — the same fingerprint across
    different rule_versions is expected and fine.
    """
    raw = json.dumps(
        {
            "instrument_id": instrument_id,
            "rule_id": rule_id,
            "rule_version": rule_version,
            "fingerprint_key": fingerprint_key,
        },
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
