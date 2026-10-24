"""
Module 3 — Validation, Discrepancy & Explainable Intelligence
SQLAlchemy Models

Tables
------
validation_policy_configs
    Versioned, institution-scoped (or global) policy configuration values used by rules.
    Policy changes are authorized, versioned, and audited. Ordinary users cannot modify.

validation_findings
    Persisted discrepancy records produced by the rule engine.
    Each finding is linked to an instrument, an optional document/version pair,
    the specific rule ID and version that generated it, and structured evidence.
    Findings are NEVER deleted; they are resolved, dismissed, or superseded.

validation_runs
    Lightweight run-log recording that a validation sweep was executed for an instrument
    at a specific timestamp, by which user, and what policy version was in effect.

Design boundaries
-----------------
* This module does NOT own instruments, documents, users, or institutions.
* A finding does NOT alter Instrument.trust_level.
* PASS / NOT_APPLICABLE outcomes do NOT create finding records.
* Evidence references are stored as JSON-encoded lists of record IDs, scoped to the
  instrument's institution to prevent cross-institution leakage.
* Sensitive document content is NEVER stored in finding fields.
"""
import uuid
import json
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String, Text, DateTime, Boolean, Integer, ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, get_utc_now


# ---------------------------------------------------------------------------
# Policy Configuration
# ---------------------------------------------------------------------------

class ValidationPolicyConfig(Base, TimestampMixin):
    """
    Versioned, append-only policy configuration record.

    Each record represents one named configuration key for a given scope
    (global or institution-specific) at a specific version. To update a policy,
    a new record is inserted with a higher version number and is_active=True;
    the previous record is deactivated (is_active=False). Historical records
    are preserved for auditability.

    Examples of config_key:
      - 'MIN_DEPOSIT_AMOUNT_INR'          (global minimum deposit)
      - 'MIN_VALIDITY_DAYS'               (minimum term in days)
      - 'REQUIRED_DOCUMENT_CATEGORIES'    (JSON list of category codes)
    """
    __tablename__ = "validation_policy_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Scope: None = global; institution UUID = institution-specific override
    institution_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )

    # Stable key name (never contains PII or financial amounts inline)
    config_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Human-readable label
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # The actual value, stored as a text representation
    # Numeric values are stored as decimal strings; lists as JSON arrays.
    config_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Value data type hint for consumers: 'decimal', 'integer', 'string', 'json_list', 'boolean'
    value_type: Mapped[str] = mapped_column(String(20), default="string", nullable=False)

    # Description and justification (regulatory reference, circular number, etc.)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Versioning: incremented on each update; policy rules reference the version they ran against
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Only one active record per (institution_id, config_key) at any time
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Who authorized this policy value (must be SYSTEM_ADMIN or higher)
    authorized_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Effective from date (UTC ISO string stored as text for portability)
    effective_from: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        Index("ix_vpc_key_institution", "config_key", "institution_id"),
        Index("ix_vpc_active_key", "is_active", "config_key"),
    )

    @property
    def parsed_value(self):
        """Returns config_value parsed according to value_type."""
        if self.value_type == "decimal":
            return Decimal(self.config_value)
        if self.value_type == "integer":
            return int(self.config_value)
        if self.value_type == "boolean":
            return self.config_value.lower() in ("true", "1", "yes")
        if self.value_type == "json_list":
            try:
                return json.loads(self.config_value)
            except Exception:
                return []
        return self.config_value


# ---------------------------------------------------------------------------
# Finding (Discrepancy)
# ---------------------------------------------------------------------------

class ValidationFinding(Base, TimestampMixin):
    """
    Persisted discrepancy / finding record produced by the rule engine.

    Lifecycle
    ---------
    OPEN → IN_REVIEW → RESOLVED  (issue corrected)
                     → DISMISSED (human reviewer determined not actionable)
         → SUPERSEDED             (replaced by a newer finding from updated rule/evidence)

    Findings are NEVER deleted. Resolved/dismissed/superseded records remain
    traceable for audit and historical reconstruction.

    Safety constraints
    ------------------
    * This record DOES NOT modify Instrument.trust_level.
    * FAIL outcome alone CANNOT approve or reject a financial release.
    * Heuristic findings carry rule_type='HEURISTIC' and title/explanation prefix.
    * 'observed_value' and 'expected_value' MUST NOT store raw bank account numbers,
      PAN, Aadhaar, or full financial document text.
    * Evidence references are stored as JSON lists of UUIDs, NOT raw content.
    """
    __tablename__ = "validation_findings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # ---- Stable fingerprint for deduplication ----
    # SHA-256 (hex) of (instrument_id, rule_id, rule_version, fingerprint_inputs)
    # Used to detect whether an identical finding already exists for this instrument+rule+version.
    finding_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )

    # ---- Instrument ownership ----
    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # ---- Document evidence (optional) ----
    # References the logical document and the exact immutable version at detection time.
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    document_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # ---- Rule provenance ----
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)    # DETERMINISTIC | HEURISTIC

    # ---- Classification ----
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # ---- Status lifecycle ----
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="OPEN", index=True
    )

    # ---- Human-readable explanation ----
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ---- Observed vs expected (safe, non-sensitive values only) ----
    # Stores short descriptive strings, NOT raw financial identifiers.
    observed_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    expected_value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ---- Evidence references (JSON list of UUIDs) ----
    # e.g. ["<document_version_id>", "<audit_event_id>"]
    # Never stores raw content; references only.
    evidence_refs_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ---- Suggested next action ----
    suggested_action: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ---- Policy version at evaluation time (for auditability) ----
    policy_version_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ---- Temporal tracking ----
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )
    last_evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    # ---- Resolution / dismissal metadata ----
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dismissed or superseded by which finding (optional linkage)
    superseded_by_finding_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("validation_findings.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Validation run reference (optional; links finding to the triggering run)
    validation_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("validation_runs.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # ---- Review assignment & observations ----
    assigned_to_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ---- Optimistic concurrency control ----
    concurrency_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    instrument: Mapped["Instrument"] = relationship("Instrument", foreign_keys=[instrument_id])
    document: Mapped[Optional["Document"]] = relationship("Document", foreign_keys=[document_id])

    @property
    def review_notes(self) -> List[Dict[str, Any]]:
        """Parse review_notes_json as a list of dicts."""
        if not self.review_notes_json:
            return []
        try:
            return json.loads(self.review_notes_json)
        except Exception:
            return []

    __table_args__ = (
        Index("ix_vf_instrument_status", "instrument_id", "status"),
        Index("ix_vf_instrument_rule", "instrument_id", "rule_id"),
        Index("ix_vf_severity_status", "severity", "status"),
        Index("ix_vf_category_status", "category", "status"),
        Index("ix_vf_first_detected", "first_detected_at"),
        Index("ix_vf_last_evaluated", "last_evaluated_at"),
        # NOTE: fingerprint is intentionally NOT unique globally —
        # the same fingerprint may exist across different rule_versions or distinct evidence.
        # Deduplication logic is applied in the service layer using (fingerprint, status, rule_version).
    )

    @property
    def evidence_refs(self) -> List[str]:
        """Parsed evidence reference IDs."""
        if not self.evidence_refs_json:
            return []
        try:
            return json.loads(self.evidence_refs_json)
        except Exception:
            return []

    @property
    def is_advisory(self) -> bool:
        return self.rule_type == "HEURISTIC"

    @property
    def is_open(self) -> bool:
        return self.status == "OPEN"


# ---------------------------------------------------------------------------
# Validation Run Log
# ---------------------------------------------------------------------------

class ValidationRun(Base):
    """
    Lightweight log of a validation sweep execution.

    Records who triggered evaluation, when, what rule set was used,
    and what policy version was in effect. Not every individual rule result
    is persisted here — only the aggregated outcome metadata.
    Findings link back to the run that created them via validation_run_id.
    """
    __tablename__ = "validation_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Who triggered the run (None = system-triggered background sweep)
    triggered_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # ISO timestamp of run start
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False, index=True
    )

    # Comma-separated list of rule IDs that were evaluated
    rules_evaluated_csv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Aggregate outcome counts (JSON: {"PASS":n, "FAIL":n, "WARNING":n, ...})
    outcome_summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Policy config snapshot version reference
    policy_version_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Number of new findings created in this run
    new_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Number of findings marked resolved in this run
    resolved_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Overall run status: COMPLETED, PARTIAL, FAILED
    run_status: Mapped[str] = mapped_column(String(20), default="COMPLETED", nullable=False)

    # Optional error message if run_status == FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False,
    )

    @property
    def outcome_summary(self) -> Dict[str, Any]:
        if not self.outcome_summary_json:
            return {}
        try:
            return json.loads(self.outcome_summary_json)
        except Exception:
            return {}
