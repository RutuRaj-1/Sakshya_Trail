"""
Module 5 — Lifecycle Orchestration & Renewal
SQLAlchemy Database Models

Tables:
- lifecycle_policies: Versioned policy configurations for reminder schedules, action lead times, and tolerances.
- instrument_lineages: Explicit predecessor-successor renewal and replacement lineage graph edges.
- lifecycle_evaluations: Audit-safe time-sensitive evaluations, days-to-maturity, and due conditions.
"""
import uuid
import json
from datetime import date, datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from sqlalchemy import (
    String,
    Text,
    Date,
    DateTime,
    Boolean,
    Integer,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, get_utc_now
from app.modules.lifecycle.enums import (
    PolicyStatus,
    MaturityStage,
    DueCondition,
    RenewalComparisonMethod,
    LineageRelationshipType,
    LineageRelationshipStatus,
    ContinuityIndicator,
)

if TYPE_CHECKING:
    from app.modules.instruments.models import Instrument
    from app.modules.institutions.models import Institution


class LifecyclePolicy(Base, TimestampMixin):
    """
    Versioned lifecycle policy configuration.
    Stores configurable reminder intervals, recipient roles, action lead times,
    continuity comparison rules, and synthetic demo designations.
    """
    __tablename__ = "lifecycle_policies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Stable identifier across versions (e.g. "DEFAULT_FDR_MONITORING")
    policy_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    # Monotonic version number within policy_code
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle state: DRAFT, APPROVED, ACTIVE, INACTIVE, SUPERSEDED
    status: Mapped[str] = mapped_column(
        String(50), default=PolicyStatus.DRAFT.value, index=True, nullable=False
    )

    # Synthetic demo indicator & unambiguous disclaimer
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    label: Mapped[str] = mapped_column(
        String(255),
        default="DEMO POLICY — NOT OFFICIAL AICTE POLICY",
        nullable=False,
    )

    # Scope boundaries
    scope_instrument_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scope_institution_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scope_assigned_office: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Date boundary timezone (defaults to Asia/Kolkata for development prototype)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)

    # Configurable reminder intervals in days (JSON list of integers, e.g. [90, 60, 30, 15, 7])
    reminder_intervals_days_json: Mapped[str] = mapped_column(
        Text, default="[90, 60, 30, 15, 7]", nullable=False
    )

    # Recipient roles mapped by interval string (JSON dict)
    recipient_roles_by_interval_json: Mapped[str] = mapped_column(
        Text,
        default='{"90": ["INSTITUTION_USER"], "60": ["INSTITUTION_USER"], "30": ["INSTITUTION_USER", "SCRUTINY_OFFICER"], "15": ["INSTITUTION_USER", "SCRUTINY_OFFICER"], "7": ["INSTITUTION_USER", "SCRUTINY_OFFICER", "BRANCH_HEAD"]}',
        nullable=False,
    )

    # Action lead times and escalation thresholds
    institution_action_lead_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    officer_action_lead_days: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    escalation_interval_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    escalation_target_role: Mapped[str] = mapped_column(String(50), default="BRANCH_HEAD", nullable=False)
    maturity_critical_lead_days: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    # Renewal continuity comparison rules
    renewal_comparison_method: Mapped[str] = mapped_column(
        String(50), default=RenewalComparisonMethod.ISSUE_DATE_TO_MATURITY_DATE.value, nullable=False
    )
    max_allowed_gap_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_allowed_overlap_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Effective date windows
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Governance & audit metadata
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_code", "version", name="uq_policy_code_version"),
        Index("ix_policy_code_status", "policy_code", "status"),
    )

    @property
    def reminder_intervals_days(self) -> List[int]:
        try:
            return json.loads(self.reminder_intervals_days_json)
        except Exception:
            return [90, 60, 30, 15, 7]

    @property
    def recipient_roles_by_interval(self) -> Dict[str, List[str]]:
        try:
            return json.loads(self.recipient_roles_by_interval_json)
        except Exception:
            return {}


class InstrumentLineage(Base, TimestampMixin):
    """
    Explicit predecessor-to-successor lineage relationship edge.
    Guarantees:
    - Predecessor is NEVER overwritten by successor.
    - Anti self-reference constraint (predecessor != successor).
    - Institution boundaries strictly enforced.
    - Concurrency-safe optimistic versioning.
    """
    __tablename__ = "instrument_lineages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    predecessor_instrument_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    successor_instrument_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("instruments.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    institution_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("institutions.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    relationship_type: Mapped[str] = mapped_column(
        String(50), default=LineageRelationshipType.RENEWAL.value, nullable=False
    )

    relationship_status: Mapped[str] = mapped_column(
        String(50), default=LineageRelationshipStatus.ACTIVE.value, nullable=False
    )

    reason_or_reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    policy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("lifecycle_policies.id", ondelete="SET NULL"), nullable=True
    )
    policy_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Continuity metrics
    validity_gap_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    validity_overlap_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    continuity_indicator: Mapped[str] = mapped_column(
        String(50), default=ContinuityIndicator.CONTINUOUS.value, nullable=False
    )

    # Concurrency control
    concurrency_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "predecessor_instrument_id != successor_instrument_id",
            name="ck_lineage_no_self_reference",
        ),
        Index("ix_lineage_predecessor_status", "predecessor_instrument_id", "relationship_status"),
        Index("ix_lineage_successor_status", "successor_instrument_id", "relationship_status"),
    )

    # Relationships
    predecessor: Mapped["Instrument"] = relationship(
        "Instrument", foreign_keys=[predecessor_instrument_id]
    )
    successor: Mapped["Instrument"] = relationship(
        "Instrument", foreign_keys=[successor_instrument_id]
    )
    institution: Mapped["Institution"] = relationship(
        "Institution", foreign_keys=[institution_id]
    )
    policy: Mapped[Optional["LifecyclePolicy"]] = relationship(
        "LifecyclePolicy", foreign_keys=[policy_id]
    )


class LifecycleEvaluation(Base, TimestampMixin):
    """
    Time-sensitive maturity, due condition, and action assessment record.
    Preserves audit history of lifecycle evaluations without mutating administrative states.
    """
    __tablename__ = "lifecycle_evaluations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    instrument_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("instruments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    policy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("lifecycle_policies.id", ondelete="SET NULL"), nullable=True
    )
    policy_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Calendar date and instant
    evaluation_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    evaluation_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )
    evaluation_timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)

    # Evaluated indicators
    days_to_maturity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    maturity_stage: Mapped[str] = mapped_column(
        String(50), default=MaturityStage.ACTIVE.value, index=True, nullable=False
    )

    institution_action_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    officer_action_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    escalation_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    due_condition: Mapped[str] = mapped_column(
        String(50), default=DueCondition.NORMAL.value, nullable=False
    )
    matched_reminder_interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Lineage link if applicable
    lineage_relationship_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("instrument_lineages.id", ondelete="SET NULL"), nullable=True
    )

    # Audit & transition tracking
    is_material_transition: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prior_evaluation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("lifecycle_evaluations.id", ondelete="SET NULL"), nullable=True
    )

    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_eval_instrument_date", "instrument_id", "evaluation_date"),
        Index("ix_eval_maturity_stage", "maturity_stage"),
        Index("ix_eval_due_condition", "due_condition"),
    )

    # Relationships
    instrument: Mapped["Instrument"] = relationship(
        "Instrument", foreign_keys=[instrument_id]
    )
    policy: Mapped[Optional["LifecyclePolicy"]] = relationship(
        "LifecyclePolicy", foreign_keys=[policy_id]
    )
    lineage: Mapped[Optional["InstrumentLineage"]] = relationship(
        "InstrumentLineage", foreign_keys=[lineage_relationship_id]
    )
