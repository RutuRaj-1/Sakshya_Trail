"""
Module 4 — Trust, Provenance & Verification Desk
SQLAlchemy Models

Tables:
- field_provenances: Append-only field-level provenance tracking.
- verification_requests: Bank verification requests.
- verification_responses: Traceable verification responses with simulation flags.
- trust_assessments: Field-level and aggregate trust evaluations (L0-L3).
- trust_transition_history: Immutable audit log for trust state changes.
"""
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Text, DateTime, Boolean, Integer, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, get_utc_now
from app.modules.verification.enums import (
    TrustLevel,
    ProvenanceSourceType,
    VerificationChannel,
    VerificationResult,
    VerificationRequestStatus,
    TrustAssessmentStatus,
    TrustTriggerType,
)


class FieldProvenance(Base):
    """
    Append-only field-level provenance entity.
    Maintains complete historical chain of custody for every tracked instrument field.
    Never mutates or deletes prior source entries.
    """
    __tablename__ = "field_provenances"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Scoped to instrument
    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Specific field name from allow-list (e.g. 'amount', 'reference_number')
    field_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)

    # Serialized protected value representation
    recorded_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Source classification
    source_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    # Originating actor or automated service
    source_actor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_service_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamp when source originated
    source_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    # Human-readable or structured evidence tag
    evidence_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Concrete documentary evidence references
    related_document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    related_document_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True
    )

    # Related validation run if derived from engine check
    related_validation_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("validation_runs.id", ondelete="SET NULL"), nullable=True
    )

    # Lineage / supersession links
    prior_provenance_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("field_provenances.id", ondelete="SET NULL"), nullable=True
    )
    superseded_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("field_provenances.id", ondelete="SET NULL"), nullable=True
    )

    provenance_schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Active flag: exactly one active record per (instrument_id, field_name)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    # Relationships
    instrument: Mapped["Instrument"] = relationship("Instrument", foreign_keys=[instrument_id])
    source_actor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[source_actor_id])


class VerificationRequest(Base, TimestampMixin):
    """
    Outbound or internal request for bank/third-party verification.
    """
    __tablename__ = "verification_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Traceable unique verification reference code (e.g. VR-20261025-XXXXX)
    reference_code: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )

    # Transmission mode / channel
    channel: Mapped[str] = mapped_column(String(50), nullable=False)

    # Lifecycle state
    status: Mapped[str] = mapped_column(
        String(50), default=VerificationRequestStatus.REQUESTED.value, index=True, nullable=False
    )

    # Frozen JSON snapshot of instrument fields at dispatch time
    snapshot_data_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Requested fields subset (JSON list)
    requested_fields_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Correlation / external idempotency tracking
    correlation_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)

    # Attempt and retry tracking
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error and failure diagnostics
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Expiry and closure metadata
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    requested_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    instrument: Mapped["Instrument"] = relationship("Instrument", foreign_keys=[instrument_id])
    requested_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[requested_by_user_id])
    responses: Mapped[List["VerificationResponse"]] = relationship(
        "VerificationResponse", back_populates="request", cascade="all, delete-orphan"
    )


class VerificationResponse(Base):
    """
    Recorded response from a bank, official adapter, or manual correspondence.
    Carries is_simulated flag. Simulated responses CANNOT satisfy L3 trust requirements.
    """
    __tablename__ = "verification_responses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("verification_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Matching request code (asserted equal to request.reference_code)
    request_code: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)

    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True, nullable=False
    )

    channel: Mapped[str] = mapped_column(String(50), nullable=False)

    # Source classification: AUTHORIZED_BANK_RESPONSE, MANUAL_EVIDENCE, SIMULATION
    source_classification: Mapped[str] = mapped_column(
        String(50), default="SIMULATION", index=True, nullable=False
    )

    # Source identifier or institution label
    source_identifier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Outcome: MATCH, MISMATCH, INDETERMINATE, TIMEOUT, SOURCE_UNAVAILABLE, ERROR
    result: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    # Official external confirmation identifier
    bank_reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Structured bank response attributes
    bank_values_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Field-by-field comparison outcome
    field_comparisons_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    responded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    # Receipt timestamp
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    # Supporting documentary evidence for manual verification letters
    evidence_document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    evidence_document_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True
    )
    evidence_references_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Strict simulation flag: Must be True if channel == SIMULATED
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)

    # Idempotency token to prevent duplicate responses
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    recorded_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    recorded_by_service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Safe raw metadata (sanitized)
    raw_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "((channel = 'SIMULATED' AND is_simulated = 1) OR (channel != 'SIMULATED' AND is_simulated = 0))",
            name="ck_vr_sim_consistency"
        ),
        CheckConstraint(
            "(channel NOT IN ('MANUAL', 'AUTHORIZED_MANUAL') OR evidence_document_version_id IS NOT NULL OR evidence_document_id IS NOT NULL OR notes IS NOT NULL)",
            name="ck_vr_manual_evidence"
        ),
    )

    # Relationships
    request: Mapped["VerificationRequest"] = relationship("VerificationRequest", back_populates="responses")
    instrument: Mapped["Instrument"] = relationship("Instrument", foreign_keys=[instrument_id])
    recorded_by_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[recorded_by_user_id])


class TrustAssessment(Base):
    """
    Evidentiary trust assessment record.
    Can be scoped to a single field (field_name != None) or the aggregate instrument (field_name == None).
    Enforces that L3_BANK_CONFIRMED strictly requires an authorized verification response.
    """
    __tablename__ = "trust_assessments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Nullable: None represents overall aggregate instrument trust; non-None represents specific field
    field_name: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)

    # L0_DECLARED, L1_DOCUMENT_CONSISTENT, L2_OFFICER_VERIFIED, L3_BANK_CONFIRMED
    trust_level: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    supporting_evidence_references_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    supporting_document_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True
    )

    related_validation_run_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("validation_runs.id", ondelete="SET NULL"), nullable=True
    )

    # Mandatory for L3
    related_verification_response_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("verification_responses.id", ondelete="SET NULL"), nullable=True
    )

    assessing_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assessing_service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Mandatory justification
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    assessment_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    trust_rule_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default=TrustAssessmentStatus.ACTIVE.value, index=True, nullable=False
    )

    is_downgrade: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    superseded_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("trust_assessments.id", ondelete="SET NULL"), nullable=True
    )

    # Explicit backward link to the assessment this one supersedes (complements superseded_by_id)
    prior_assessment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("trust_assessments.id", ondelete="SET NULL"), nullable=True
    )

    # Optimistic-locking counter — must match when attempting a supersession
    concurrency_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Source authorization config key that qualified this assessment (for L3 policy gate)
    source_authorization_config: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(trust_level != 'L3_BANK_CONFIRMED' OR related_verification_response_id IS NOT NULL)",
            name="ck_ta_l3_response"
        ),
    )

    # Relationships
    instrument: Mapped["Instrument"] = relationship("Instrument", foreign_keys=[instrument_id])
    assessing_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assessing_user_id])
    verification_response: Mapped[Optional["VerificationResponse"]] = relationship(
        "VerificationResponse", foreign_keys=[related_verification_response_id]
    )


class TrustTransitionHistory(Base):
    """
    Append-only durable audit trail for trust transitions.
    Ordinary application endpoints cannot edit or delete rows from this table.
    """
    __tablename__ = "trust_transition_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True, nullable=False
    )

    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    prior_trust_level: Mapped[str] = mapped_column(String(50), nullable=False)
    new_trust_level: Mapped[str] = mapped_column(String(50), nullable=False)

    actor_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    reason: Mapped[str] = mapped_column(Text, nullable=False)

    evidence_references_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)

    related_verification_response_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("verification_responses.id", ondelete="SET NULL"), nullable=True
    )

    rule_policy_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    outcome: Mapped[str] = mapped_column(String(20), default="APPLIED", nullable=False)

    is_downgrade: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Explicit links to the before/after assessment records for full audit trail
    previous_assessment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    new_assessment_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Concurrency version of the prior assessment at the moment of transition
    concurrency_version_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    # Relationships
    instrument: Mapped["Instrument"] = relationship("Instrument", foreign_keys=[instrument_id])
    actor_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_user_id])
