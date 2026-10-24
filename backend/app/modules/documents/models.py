"""
Documents Module - SQLAlchemy Models for Logical Documents and Immutable Versions
Provides the foundational data model for document intake, versioning, and integrity tracking.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey, LargeBinary, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """
    Logical document entity representing a single conceptual document within a specific instrument.
    One document can have multiple immutable versions (uploads).
    """
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Parent relationships: Document must be scoped to an instrument, which has an institution
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    instrument_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("instruments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Document metadata
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Record status: ACTIVE, ARCHIVED
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", index=True, nullable=False)
    
    # Current version reference for convenience (denormalized for fast access)
    current_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True
    )
    
    # Audit metadata
    created_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    # Optional archival metadata
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    institution: Mapped["Institution"] = relationship("Institution", foreign_keys=[institution_id])
    instrument: Mapped["Instrument"] = relationship("Instrument", foreign_keys=[instrument_id])
    versions: Mapped[List["DocumentVersion"]] = relationship(
        "DocumentVersion", 
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="DocumentVersion.document_id"
    )


class DocumentVersion(Base):
    """
    Immutable document version entity representing a single upload instance.
    Each version has:
    - Unique UUID (immutable once created)
    - Version number (monotonic within a document)
    - File metadata and integrity hash (SHA-256)
    - Upload timestamp and uploader user ID
    - Processing/scan status
    - Never overwrites bytes; each version is a distinct storage instance
    """
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Parent document reference
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Monotonic version number within the document
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Storage provider abstraction: private storage key (never exposed publicly)
    storage_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False, unique=True)
    
    # File metadata (for display and integrity tracking)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # File integrity: SHA-256 hash (hex-encoded)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    
    # Uploader audit
    uploader_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    
    # Processing/scan state machine
    processing_status: Mapped[str] = mapped_column(String(50), default="PENDING_SCAN", index=True, nullable=False)
    
    # Scan provider and result metadata (JSON-like metadata stored as text)
    scan_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scan_result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Error tracking and recovery
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Parent-version reference for version history linkage
    parent_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("document_versions.id", ondelete="SET NULL"), nullable=True
    )
    
    # Audit timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="versions", foreign_keys=[document_id])


class DocumentCategory(Base):
    """
    Configurable document category catalog.
    Allows extensible category management and optional category-specific rules.
    """
    __tablename__ = "document_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Unique category code (e.g., FDR_COPY, BANK_CONFIRMATION)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    
    # Human-readable display name
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Optional description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Is this category currently active/usable?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Optional category-specific metadata or rules (JSON stored as text)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Audit timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
