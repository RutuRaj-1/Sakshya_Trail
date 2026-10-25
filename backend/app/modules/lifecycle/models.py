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

    # Permitted notification channels, retry limits & templates
    permitted_channels_json: Mapped[str] = mapped_column(
        Text, default='["IN_APP", "EMAIL"]', nullable=False
    )
    max_retry_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    template_id: Mapped[str] = mapped_column(
        String(100), default="DEFAULT_REGULATORY_REMINDER", nullable=False
    )
    template_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

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

    @reminder_intervals_days.setter
    def reminder_intervals_days(self, val: List[int]) -> None:
        self.reminder_intervals_days_json = json.dumps(val or [])

    @property
    def reminder_milestones_days(self) -> List[int]:
        return self.reminder_intervals_days

    @reminder_milestones_days.setter
    def reminder_milestones_days(self, val: List[int]) -> None:
        self.reminder_intervals_days = val

    @property
    def recipient_roles_by_interval(self) -> Dict[str, List[str]]:
        try:
            return json.loads(self.recipient_roles_by_interval_json)
        except Exception:
            return {}

    @recipient_roles_by_interval.setter
    def recipient_roles_by_interval(self, val: Dict[str, List[str]]) -> None:
        self.recipient_roles_by_interval_json = json.dumps(val or {})

    @property
    def permitted_channels(self) -> List[str]:
        try:
            return json.loads(self.permitted_channels_json)
        except Exception:
            return ["IN_APP", "EMAIL"]

    @permitted_channels.setter
    def permitted_channels(self, val: List[str]) -> None:
        self.permitted_channels_json = json.dumps(val or [])

    @property
    def escalation_delay_days(self) -> int:
        return self.escalation_interval_days

    @escalation_delay_days.setter
    def escalation_delay_days(self, val: int) -> None:
        self.escalation_interval_days = val

    @property
    def escalation_destination_role(self) -> str:
        return self.escalation_target_role

    @escalation_destination_role.setter
    def escalation_destination_role(self, val: str) -> None:
        self.escalation_target_role = val


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
    continuity_details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correction_history_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
        UniqueConstraint("instrument_id", "evaluation_date", name="uq_eval_instrument_date"),
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


class LifecycleJobRun(Base, TimestampMixin):
    """
    Execution tracker, lease lock, and structured diagnostics log for
    scheduled and on-demand maturity scan jobs.
    """
    __tablename__ = "lifecycle_job_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    job_type: Mapped[str] = mapped_column(
        String(50), default="DAILY_MATURITY_SCAN", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="RUNNING", index=True, nullable=False
    )
    trigger_source: Mapped[str] = mapped_column(
        String(50), default="SCHEDULED", nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)
    evaluation_timezone: Mapped[str] = mapped_column(
        String(50), default="Asia/Kolkata", nullable=False
    )

    total_eligible: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evaluated_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    material_transitions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approaching_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matured_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overdue_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    worker_instance_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    error_summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_job_status_started", "status", "started_at"),
        Index("ix_job_type_date", "job_type", "evaluation_date"),
    )


class LifecycleNotification(Base, TimestampMixin):
    """
    Time-sensitive reminder, due-date alert, and escalation notification record.
    Tracks granular lifecycle state, delivery attempts, and idempotency guarantees.
    """
    __tablename__ = "lifecycle_notifications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    policy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("lifecycle_policies.id", ondelete="SET NULL"), nullable=True
    )
    policy_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reminder_milestone_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trigger_date: Mapped[date] = mapped_column(Date, nullable=False)

    recipient_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    recipient_role: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    channel: Mapped[str] = mapped_column(String(50), default="IN_APP", nullable=False)
    template_id: Mapped[str] = mapped_column(
        String(100), default="DEFAULT_REGULATORY_REMINDER", nullable=False
    )
    template_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default="CREATED", index=True, nullable=False
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )
    first_attempted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_attempted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mock_disclaimer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_notif_event_date", "event_type", "trigger_date"),
    )

    # Relationships
    attempts: Mapped[List["NotificationDeliveryAttempt"]] = relationship(
        "NotificationDeliveryAttempt",
        back_populates="notification",
        cascade="all, delete-orphan",
        order_by="NotificationDeliveryAttempt.attempt_number",
    )
    instrument: Mapped["Instrument"] = relationship("Instrument", foreign_keys=[instrument_id])
    institution: Mapped["Institution"] = relationship("Institution", foreign_keys=[institution_id])

    # Compatibility properties for tests and view layer
    @property
    def rendered_title(self) -> str:
        return self.title

    @rendered_title.setter
    def rendered_title(self, val: str) -> None:
        self.title = val

    @property
    def rendered_message(self) -> str:
        return self.message

    @rendered_message.setter
    def rendered_message(self, val: str) -> None:
        self.message = val

    @property
    def failure_details(self) -> Optional[str]:
        return self.failure_reason

    @failure_details.setter
    def failure_details(self, val: Optional[str]) -> None:
        self.failure_reason = val

    @property
    def milestone_days(self) -> Optional[int]:
        return self.reminder_milestone_days

    @milestone_days.setter
    def milestone_days(self, val: Optional[int]) -> None:
        self.reminder_milestone_days = val


class NotificationDeliveryAttempt(Base):
    """
    Granular attempt tracking per notification for retries and delivery audits.
    """
    __tablename__ = "notification_delivery_attempts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    notification_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lifecycle_notifications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    provider_response_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_reference_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    notification: Mapped["LifecycleNotification"] = relationship(
        "LifecycleNotification", back_populates="attempts"
    )

    @property
    def provider_name(self) -> Optional[str]:
        return self.provider_response_code

    @provider_name.setter
    def provider_name(self, val: Optional[str]) -> None:
        self.provider_response_code = val

    @property
    def provider_reference(self) -> Optional[str]:
        return self.provider_reference_id

    @provider_reference.setter
    def provider_reference(self, val: Optional[str]) -> None:
        self.provider_reference_id = val

    @property
    def failure_category(self) -> Optional[str]:
        return self.error_category

    @failure_category.setter
    def failure_category(self, val: Optional[str]) -> None:
        self.error_category = val

    @property
    def failure_details(self) -> Optional[str]:
        return self.error_message

    @failure_details.setter
    def failure_details(self, val: Optional[str]) -> None:
        self.error_message = val

    @property
    def is_mock(self) -> bool:
        return self.status == "MOCKED" or (self.notification.is_mock if self.notification else False)

    @is_mock.setter
    def is_mock(self, val: bool) -> None:
        pass


