"""
Database Models for Module 7 (Command Center, Search, Reporting & Audit)
Implements PRD-FR-072 & PRD-FR-073: Append-Only Scrutiny Observations
"""
import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, get_utc_now


class ScrutinyObservation(Base, TimestampMixin):
    """
    Append-only scrutiny observations recorded by officers and reviewers.
    Preserves complete authorship, timestamping, evidence linkage,
    and non-destructive supersession chains (corrections link to prior observation).
    """
    __tablename__ = "scrutiny_observations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    instrument_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    release_request_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("release_requests.id", ondelete="CASCADE"), nullable=True, index=True
    )
    finding_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("validation_findings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    supporting_document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    supporting_version_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    observation_category: Mapped[str] = mapped_column(
        String(50), default="GENERAL", nullable=False
    )
    observation_text: Mapped[str] = mapped_column(Text, nullable=False)

    author_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    author_role: Mapped[str] = mapped_column(String(50), nullable=False)

    status: Mapped[str] = mapped_column(
        String(30), default="RECORDED", nullable=False
    )  # RECORDED, AMENDED, SUPERSEDED, RESOLVED

    resolution_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    # Append-only supersession chain: an amendment references the prior note
    supersedes_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("scrutiny_observations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    superseded_by_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("scrutiny_observations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    is_internal_only: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_user_id])
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by_user_id])
    instrument: Mapped[Optional["Instrument"]] = relationship("Instrument", foreign_keys=[instrument_id])
    release_request: Mapped[Optional["ReleaseRequest"]] = relationship("ReleaseRequest", foreign_keys=[release_request_id])
    supporting_document: Mapped[Optional["Document"]] = relationship("Document", foreign_keys=[supporting_document_id])

    __table_args__ = (
        Index("ix_obs_inst_created", "instrument_id", "created_at"),
        Index("ix_obs_rel_created", "release_request_id", "created_at"),
        Index("ix_obs_status", "status"),
    )
