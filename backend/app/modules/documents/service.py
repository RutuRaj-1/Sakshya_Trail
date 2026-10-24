"""
Documents Module - Business Logic Service Layer
Handles document creation, versioning, upload processing, and state management.
"""
import hashlib
import json
from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc

from app.modules.documents.models import Document, DocumentVersion, DocumentCategory
from app.modules.documents.schemas import (
    DocumentCreateRequest,
    DocumentUpdateRequest,
    DocumentUploadResponse,
    DEFAULT_CATEGORIES,
    PROCESSING_STATES,
)
from app.modules.documents.storage import get_storage_provider, StorageException
from app.modules.instruments.models import Instrument
from app.modules.institutions.models import Institution
from app.modules.audit.service import log_audit_event


class DocumentService:
    """Business logic for document management."""

    @staticmethod
    def create_document(
        db: Session,
        instrument_id: str,
        category: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        created_by_user_id: Optional[str] = None,
    ) -> Document:
        """
        Create a new logical document linked to an instrument.
        
        Args:
            db: Database session
            instrument_id: UUID of parent instrument
            category: Document category code
            title: Optional document title
            description: Optional document description
            created_by_user_id: User creating the document
        
        Returns:
            Created Document instance
        
        Raises:
            ValueError: If instrument doesn't exist or is inactive
        """
        # Verify instrument exists and get its institution
        instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
        if not instrument:
            raise ValueError(f"Instrument {instrument_id} not found")
        
        institution = db.query(Institution).filter(Institution.id == instrument.institution_id).first()
        if not institution or not institution.is_active:
            raise ValueError(f"Institution {instrument.institution_id} is inactive or not found")
        
        # Validate category
        if category not in DEFAULT_CATEGORIES:
            raise ValueError(f"Invalid category: {category}")
        
        # Create document
        document = Document(
            institution_id=instrument.institution_id,
            instrument_id=instrument_id,
            category=category,
            title=title,
            description=description,
            status="ACTIVE",
            created_by_user_id=created_by_user_id,
        )
        
        db.add(document)
        db.flush()
        
        # Audit log
        log_audit_event(
            db=db,
            action="DOCUMENT_CREATED",
            entity_type="Document",
            entity_id=document.id,
            actor_user_id=created_by_user_id,
            metadata={
                "instrument_id": instrument_id,
                "category": category,
                "title": title,
            },
        )
        
        db.commit()
        db.refresh(document)
        return document

    @staticmethod
    def upload_version(
        db: Session,
        document_id: str,
        file_content: bytes,
        original_filename: str,
        content_type: str,
        uploader_user_id: Optional[str] = None,
    ) -> DocumentVersion:
        """
        Upload a new version of a document.
        Each upload creates an immutable version with unique storage key and SHA-256 hash.
        
        Args:
            db: Database session
            document_id: UUID of parent document
            file_content: File bytes
            original_filename: Original filename (for display only)
            content_type: MIME type (e.g. application/pdf)
            uploader_user_id: User uploading the file
        
        Returns:
            Created DocumentVersion instance
        
        Raises:
            ValueError: If document not found
            StorageException: If storage write fails
        """
        # Verify document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Compute SHA-256 hash
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        
        # Get next version number
        from sqlalchemy import func
        max_version = db.query(
            func.coalesce(func.max(DocumentVersion.version_number), 0)
        ).filter(DocumentVersion.document_id == document_id).scalar()
        next_version_number = max_version + 1
        
        # Save file to storage
        storage_provider = get_storage_provider()
        storage_key = storage_provider.save_file(file_content, original_filename)
        
        # Create version record
        version = DocumentVersion(
            document_id=document_id,
            version_number=next_version_number,
            storage_key=storage_key,
            original_filename=original_filename,
            content_type=content_type,
            file_size_bytes=len(file_content),
            sha256_hash=sha256_hash,
            uploader_user_id=uploader_user_id,
            processing_status="PENDING_SCAN",
        )
        
        db.add(version)
        db.flush()
        
        # Update document's current_version_id
        document.current_version_id = version.id
        document.updated_at = datetime.now(timezone.utc)
        
        db.flush()
        
        # Audit log
        log_audit_event(
            db=db,
            action="DOCUMENT_VERSION_UPLOADED",
            entity_type="DocumentVersion",
            entity_id=version.id,
            actor_user_id=uploader_user_id,
            metadata={
                "document_id": document_id,
                "version_number": next_version_number,
                "original_filename": original_filename,
                "content_type": content_type,
                "file_size_bytes": len(file_content),
                "sha256_hash": sha256_hash,
            },
        )
        
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def get_document(db: Session, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID."""
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def get_documents_by_instrument(
        db: Session,
        instrument_id: str,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Document]]:
        """
        List documents for an instrument with pagination.
        
        Returns:
            Tuple of (total_count, documents)
        """
        query = db.query(Document).filter(Document.instrument_id == instrument_id)
        total = query.count()
        documents = query.offset(offset).limit(limit).all()
        return total, documents

    @staticmethod
    def update_document(
        db: Session,
        document_id: str,
        update_data: DocumentUpdateRequest,
        updated_by_user_id: Optional[str] = None,
    ) -> Document:
        """
        Update document metadata (title, description, status).
        
        Args:
            db: Database session
            document_id: UUID of document to update
            update_data: Update payload
            updated_by_user_id: User performing the update
        
        Returns:
            Updated Document instance
        
        Raises:
            ValueError: If document not found
        """
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Apply updates
        if update_data.title is not None:
            document.title = update_data.title
        if update_data.description is not None:
            document.description = update_data.description
        if update_data.status is not None:
            if update_data.status == "ARCHIVED" and document.status == "ACTIVE":
                document.status = "ARCHIVED"
                document.archived_at = datetime.now(timezone.utc)
            elif update_data.status == "ACTIVE":
                document.status = "ACTIVE"
                document.archived_at = None
        
        document.updated_at = datetime.now(timezone.utc)
        
        db.flush()
        
        # Audit log
        log_audit_event(
            db=db,
            action="DOCUMENT_UPDATED",
            entity_type="Document",
            entity_id=document_id,
            actor_user_id=updated_by_user_id,
            metadata={
                "title": document.title,
                "status": document.status,
            },
        )
        
        db.commit()
        db.refresh(document)
        return document

    @staticmethod
    def get_version(db: Session, version_id: str) -> Optional[DocumentVersion]:
        """Retrieve a document version by ID."""
        return db.query(DocumentVersion).filter(DocumentVersion.id == version_id).first()

    @staticmethod
    def update_version_processing_status(
        db: Session,
        version_id: str,
        processing_status: str,
        scan_provider: Optional[str] = None,
        scan_result_json: Optional[str] = None,
        error_details: Optional[str] = None,
    ) -> DocumentVersion:
        """
        Update processing/scan status of a document version.
        
        Args:
            db: Database session
            version_id: UUID of document version
            processing_status: New status (e.g., CLEAN, INFECTED, PROCESSING_FAILED)
            scan_provider: Name of scan provider (optional)
            scan_result_json: Scan result as JSON (optional)
            error_details: Error details if processing failed (optional)
        
        Returns:
            Updated DocumentVersion instance
        
        Raises:
            ValueError: If version not found or invalid status
        """
        if processing_status not in PROCESSING_STATES:
            raise ValueError(f"Invalid processing status: {processing_status}")
        
        version = db.query(DocumentVersion).filter(DocumentVersion.id == version_id).first()
        if not version:
            raise ValueError(f"DocumentVersion {version_id} not found")
        
        version.processing_status = processing_status
        version.scan_provider = scan_provider
        version.scan_result_json = scan_result_json
        version.error_details = error_details
        
        db.flush()
        
        # Audit log
        log_audit_event(
            db=db,
            action="DOCUMENT_SCAN_STATUS_UPDATED",
            entity_type="DocumentVersion",
            entity_id=version_id,
            metadata={
                "processing_status": processing_status,
                "scan_provider": scan_provider,
            },
        )
        
        db.commit()
        db.refresh(version)
        return version

    @staticmethod
    def initialize_default_categories(db: Session) -> None:
        """
        Initialize default document categories if they don't exist.
        Idempotent operation (safe to call multiple times).
        """
        for code, display_name in DEFAULT_CATEGORIES.items():
            existing = db.query(DocumentCategory).filter(DocumentCategory.code == code).first()
            if not existing:
                category = DocumentCategory(
                    code=code,
                    display_name=display_name,
                    is_active=True,
                )
                db.add(category)
        
        db.commit()
