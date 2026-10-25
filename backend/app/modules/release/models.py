"""
Module 6 — Release / Refund Case Management
SQLAlchemy Domain Models

Tables:
- release_requests: Core administrative release/discharge/refund cases.
- release_checklist_profiles: Versioned policy profiles and readiness rules.
- release_checklist_items: Individual checklist criteria and mandatory blocker flags.
- readiness_assessments: Historically reproducible assessment snapshots.
- readiness_check_results: Point-in-time results for individual checklist items.
- release_review_observations: Scrutiny officer observations and return notes.
- release_decisions: Authorized decision and approval history.
- release_order_records: Administrative release letter/order tracking and bank action states.
"""
import uuid
from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING

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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, get_utc_now
from app.modules.release.enums import (
    ReleaseRequestType,
    ReleaseCaseType,
    ReleaseWorkflowStatus,
    ChecklistProfileStatus,
    ChecklistRequirementType,
    ChecklistEvaluationType,
    CheckResultStatus,
    ReadinessAssessmentOutcome,
    ReleaseDecisionType,
    ReleaseOrderStatus,
    BankActionStatus,
)

if TYPE_CHECKING:
    from app.modules.instruments.models import Instrument
    from app.modules.institutions.models import Institution
    from app.modules.auth.models import User
    from app.modules.documents.models import Document


class ReleaseChecklistProfile(Base, TimestampMixin):
    """
    Versioned checklist profile governing eligibility criteria for release,
    discharge, or refund requests.
    """
    __tablename__ = "release_checklist_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    profile_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    request_type: Mapped[str] = mapped_column(String(30), nullable=False)
    case_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ChecklistProfileStatus.DRAFT.value, nullable=False
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    demo_disclaimer: Mapped[str] = mapped_column(
        String(255),
        default="DEMO RELEASE POLICY — NOT OFFICIAL AICTE POLICY",
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    approved_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    audit_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    items: Mapped[List["ReleaseChecklistItem"]] = relationship(
        "ReleaseChecklistItem",
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ReleaseChecklistItem.sort_order",
    )

    __table_args__ = (
        UniqueConstraint("profile_code", "version", name="uq_release_profile_code_version"),
        Index("ix_release_profile_lookup", "request_type", "case_type", "status"),
    )


class ReleaseChecklistItem(Base, TimestampMixin):
    """
    Individual requirement item within a checklist profile.
    Specifies whether the requirement is a mandatory blocker or advisory.
    """
    __tablename__ = "release_checklist_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("release_checklist_profiles.id"), nullable=False, index=True
    )
    item_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_mandatory_blocker: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    evaluation_type: Mapped[str] = mapped_column(
        String(30), default=ChecklistEvaluationType.AUTOMATED.value, nullable=False
    )
    expected_evidence_source: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["ReleaseChecklistProfile"] = relationship(
        "ReleaseChecklistProfile", back_populates="items"
    )

    __table_args__ = (
        UniqueConstraint("profile_id", "item_code", name="uq_release_profile_item_code"),
    )


class ReleaseRequest(Base, TimestampMixin):
    """
    Core administrative release, discharge, or refund case.
    Manages the multi-stage review and authorization lifecycle.
    """
    __tablename__ = "release_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    case_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id"), index=True, nullable=False
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id"), index=True, nullable=False
    )
    request_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    case_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    policy_profile_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("release_checklist_profiles.id"), nullable=True
    )
    policy_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requester_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    request_reason: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_status: Mapped[str] = mapped_column(
        String(30),
        default=ReleaseWorkflowStatus.DRAFT.value,
        index=True,
        nullable=False,
    )
    assigned_reviewer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    assigned_office: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latest_assessment_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closure_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    instrument: Mapped["Instrument"] = relationship("Instrument")
    institution: Mapped["Institution"] = relationship("Institution")
    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id])
    assigned_reviewer: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[assigned_reviewer_id]
    )
    policy_profile: Mapped[Optional["ReleaseChecklistProfile"]] = relationship(
        "ReleaseChecklistProfile"
    )

    assessments: Mapped[List["ReadinessAssessment"]] = relationship(
        "ReadinessAssessment",
        back_populates="release_request",
        cascade="all, delete-orphan",
        order_by="desc(ReadinessAssessment.evaluated_at)",
    )
    decisions: Mapped[List["ReleaseDecision"]] = relationship(
        "ReleaseDecision",
        back_populates="release_request",
        cascade="all, delete-orphan",
        order_by="desc(ReleaseDecision.created_at)",
    )
    observations: Mapped[List["ReleaseReviewObservation"]] = relationship(
        "ReleaseReviewObservation",
        back_populates="release_request",
        cascade="all, delete-orphan",
        order_by="desc(ReleaseReviewObservation.created_at)",
    )
    release_orders: Mapped[List["ReleaseOrderRecord"]] = relationship(
        "ReleaseOrderRecord",
        back_populates="release_request",
        cascade="all, delete-orphan",
        order_by="desc(ReleaseOrderRecord.created_at)",
    )

    __table_args__ = (
        Index("ix_release_req_inst_status", "institution_id", "workflow_status"),
        Index("ix_release_req_instrument", "instrument_id", "workflow_status"),
    )


class ReadinessAssessment(Base, TimestampMixin):
    """
    Historically reproducible snapshot of checklist readiness evaluations.
    Never overwritten; new evidence produces a new assessment record.
    """
    __tablename__ = "readiness_assessments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    release_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("release_requests.id"), nullable=False, index=True
    )
    profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("release_checklist_profiles.id"), nullable=False
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    assessment_outcome: Mapped[str] = mapped_column(
        String(30),
        default=ReadinessAssessmentOutcome.INCOMPLETE.value,
        nullable=False,
    )
    total_items_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    satisfied_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blockers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    advisory_flags_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evaluated_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    release_request: Mapped["ReleaseRequest"] = relationship(
        "ReleaseRequest", back_populates="assessments"
    )
    evaluator: Mapped[Optional["User"]] = relationship("User")
    results: Mapped[List["ReadinessCheckResult"]] = relationship(
        "ReadinessCheckResult",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )


class ReadinessCheckResult(Base):
    """
    Individual evaluation result for a checklist item within an assessment.
    """
    __tablename__ = "readiness_check_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    assessment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("readiness_assessments.id"), nullable=False, index=True
    )
    checklist_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("release_checklist_items.id"), nullable=True
    )
    item_code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default=CheckResultStatus.PENDING.value, nullable=False
    )
    is_mandatory_blocker: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_references_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_module: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    assessment: Mapped["ReadinessAssessment"] = relationship(
        "ReadinessAssessment", back_populates="results"
    )
    checklist_item: Mapped[Optional["ReleaseChecklistItem"]] = relationship(
        "ReleaseChecklistItem"
    )


class ReleaseReviewObservation(Base):
    """
    Review observations, deficiencies, or return instructions recorded by officers.
    """
    __tablename__ = "release_review_observations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    release_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("release_requests.id"), nullable=False, index=True
    )
    officer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    observation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    is_blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    release_request: Mapped["ReleaseRequest"] = relationship(
        "ReleaseRequest", back_populates="observations"
    )
    officer: Mapped["User"] = relationship("User")


class ReleaseDecision(Base):
    """
    Authorized workflow decision or approval step in the release case lifecycle.
    Requires mandatory non-empty reason.
    """
    __tablename__ = "release_decisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    release_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("release_requests.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    policy_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    readiness_assessment_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("readiness_assessments.id"), nullable=True
    )
    evidence_references_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    previous_status: Mapped[str] = mapped_column(String(30), nullable=False)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    audit_event_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_utc_now, nullable=False
    )

    release_request: Mapped["ReleaseRequest"] = relationship(
        "ReleaseRequest", back_populates="decisions"
    )
    actor: Mapped["User"] = relationship("User")
    readiness_assessment: Mapped[Optional["ReadinessAssessment"]] = relationship(
        "ReadinessAssessment"
    )


class ReleaseOrderRecord(Base, TimestampMixin):
    """
    Tracks official AICTE release order / letter details and bank-side action.
    """
    __tablename__ = "release_order_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    release_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("release_requests.id"), nullable=False, index=True
    )
    order_reference_number: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    responsible_officer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    supporting_document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default=ReleaseOrderStatus.DRAFT_RECORDED.value, nullable=False
    )
    bank_action_status: Mapped[str] = mapped_column(
        String(30), default=BankActionStatus.PENDING.value, nullable=False
    )
    bank_action_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bank_action_confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_synthetic_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    release_request: Mapped["ReleaseRequest"] = relationship(
        "ReleaseRequest", back_populates="release_orders"
    )
    responsible_officer: Mapped["User"] = relationship("User")
