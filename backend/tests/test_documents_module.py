"""
Tests for Module 2 - Document Intake & Evidence Intelligence
Tests document creation, versioning, storage abstraction, and processing states.
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.modules.documents.models import Document, DocumentVersion, DocumentCategory
from app.modules.documents.service import DocumentService
from app.modules.documents.storage import LocalFileStorageProvider, StorageException
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument


@pytest.fixture
def sample_institution(db_session: Session) -> Institution:
    """Create a sample active institution."""
    inst = Institution(
        code="TEST-INST-001",
        legal_name="Test Institute of Technology",
        institution_type="TECHNICAL_INSTITUTE",
        contact_email="registrar@test.edu",
        state="Delhi",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    return inst


@pytest.fixture
def sample_instrument(db_session: Session, sample_institution: Institution) -> Instrument:
    """Create a sample instrument for testing."""
    from decimal import Decimal
    from datetime import date

    instrument = Instrument(
        institution_id=sample_institution.id,
        bank_name="State Bank of India",
        reference_number="FDR-2026-12345",
        amount=Decimal("5000000.00"),
        issue_date=date(2024, 10, 1),
        maturity_date=date(2026, 10, 1),
        status="REGISTERED",
        trust_level="L0_DECLARED",
    )
    db_session.add(instrument)
    db_session.commit()
    return instrument


class TestDocumentCreation:
    """Tests for document creation and validation."""

    def test_create_document_success(self, db_session: Session, sample_instrument: Instrument):
        """Test successful document creation."""
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
            title="Original FDR Scanned Copy",
            description="Front and back of FDR certificate",
            created_by_user_id="user-001",
        )
        
        assert doc.id is not None
        assert doc.instrument_id == sample_instrument.id
        assert doc.institution_id == sample_instrument.institution_id
        assert doc.category == "FDR_COPY"
        assert doc.status == "ACTIVE"
        assert doc.title == "Original FDR Scanned Copy"

    def test_create_document_nonexistent_instrument(self, db_session: Session):
        """Test document creation with nonexistent instrument."""
        with pytest.raises(ValueError, match="Instrument .* not found"):
            DocumentService.create_document(
                db=db_session,
                instrument_id="nonexistent-id",
                category="FDR_COPY",
            )

    def test_create_document_invalid_category(self, db_session: Session, sample_instrument: Instrument):
        """Test document creation with invalid category."""
        with pytest.raises(ValueError, match="Invalid category"):
            DocumentService.create_document(
                db=db_session,
                instrument_id=sample_instrument.id,
                category="INVALID_CATEGORY",
            )

    def test_create_document_inactive_institution(self, db_session: Session, sample_institution: Institution):
        """Test document creation with inactive institution."""
        # Deactivate institution
        sample_institution.is_active = False
        db_session.commit()
        
        # Create instrument under inactive institution
        from decimal import Decimal
        from datetime import date
        
        instrument = Instrument(
            institution_id=sample_institution.id,
            bank_name="Test Bank",
            reference_number="REF-123",
            amount=Decimal("1000000.00"),
            issue_date=date(2024, 1, 1),
            maturity_date=date(2026, 1, 1),
        )
        db_session.add(instrument)
        db_session.commit()
        
        # Try to create document
        with pytest.raises(ValueError, match="inactive"):
            DocumentService.create_document(
                db=db_session,
                instrument_id=instrument.id,
                category="FDR_COPY",
            )


class TestDocumentVersioning:
    """Tests for document versioning and immutability."""

    def test_upload_version_success(self, db_session: Session, sample_instrument: Instrument):
        """Test successful document version upload."""
        # Create document
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        # Upload version
        file_content = b"Test PDF content for version 1"
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=file_content,
            original_filename="fdr_copy_v1.pdf",
            content_type="application/pdf",
            uploader_user_id="user-002",
        )
        
        assert version.id is not None
        assert version.document_id == doc.id
        assert version.version_number == 1
        assert version.original_filename == "fdr_copy_v1.pdf"
        assert version.content_type == "application/pdf"
        assert version.file_size_bytes == len(file_content)
        assert version.processing_status == "PENDING_SCAN"

    def test_monotonic_version_numbering(self, db_session: Session, sample_instrument: Instrument):
        """Test that version numbers increment monotonically."""
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        # Upload multiple versions
        for i in range(1, 4):
            file_content = f"Version {i} content".encode()
            version = DocumentService.upload_version(
                db=db_session,
                document_id=doc.id,
                file_content=file_content,
                original_filename=f"version_{i}.pdf",
                content_type="application/pdf",
            )
            assert version.version_number == i

    def test_sha256_hash_computation(self, db_session: Session, sample_instrument: Instrument):
        """Test that SHA-256 hash is correctly computed."""
        import hashlib
        
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        file_content = b"Test content for hashing"
        expected_hash = hashlib.sha256(file_content).hexdigest()
        
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=file_content,
            original_filename="test.pdf",
            content_type="application/pdf",
        )
        
        assert version.sha256_hash == expected_hash

    def test_unique_storage_keys(self, db_session: Session, sample_instrument: Instrument):
        """Test that each version gets a unique storage key."""
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        keys = set()
        for i in range(3):
            version = DocumentService.upload_version(
                db=db_session,
                document_id=doc.id,
                file_content=f"Content {i}".encode(),
                original_filename=f"version_{i}.pdf",
                content_type="application/pdf",
            )
            assert version.storage_key not in keys
            keys.add(version.storage_key)


class TestProcessingStates:
    """Tests for document processing/scan status state machine."""

    def test_processing_status_pending_scan_default(self, db_session: Session, sample_instrument: Instrument):
        """Test that new uploads default to PENDING_SCAN."""
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=b"content",
            original_filename="test.pdf",
            content_type="application/pdf",
        )
        
        assert version.processing_status == "PENDING_SCAN"

    def test_update_processing_status_clean(self, db_session: Session, sample_instrument: Instrument):
        """Test updating processing status to CLEAN."""
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=b"content",
            original_filename="test.pdf",
            content_type="application/pdf",
        )
        
        updated = DocumentService.update_version_processing_status(
            db=db_session,
            version_id=version.id,
            processing_status="CLEAN",
            scan_provider="ClamAV",
            scan_result_json='{"threat_count": 0}',
        )
        
        assert updated.processing_status == "CLEAN"
        assert updated.scan_provider == "ClamAV"

    def test_update_processing_status_infected(self, db_session: Session, sample_instrument: Instrument):
        """Test updating processing status to INFECTED."""
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=b"content",
            original_filename="test.pdf",
            content_type="application/pdf",
        )
        
        updated = DocumentService.update_version_processing_status(
            db=db_session,
            version_id=version.id,
            processing_status="INFECTED",
            scan_provider="ClamAV",
            scan_result_json='{"threat_detected": "Exploit.Win32.CVE"}',
        )
        
        assert updated.processing_status == "INFECTED"

    def test_invalid_processing_status(self, db_session: Session, sample_instrument: Instrument):
        """Test that invalid processing status is rejected."""
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=b"content",
            original_filename="test.pdf",
            content_type="application/pdf",
        )
        
        with pytest.raises(ValueError, match="Invalid processing status"):
            DocumentService.update_version_processing_status(
                db=db_session,
                version_id=version.id,
                processing_status="INVALID_STATUS",
            )


class TestDocumentMetadata:
    """Tests for document metadata and audit fields."""

    def test_document_created_timestamp(self, db_session: Session, sample_instrument: Instrument):
        """Test that document creation timestamp is set."""
        from datetime import timezone as tz
        before = datetime.now(tz.utc)
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        after = datetime.now(tz.utc)
        
        # Handle timezone-naive vs aware
        created_at = doc.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=tz.utc)
        
        assert before <= created_at <= after


class TestStorageProvider:
    """Tests for storage provider abstraction."""

    def test_local_storage_save_and_read(self):
        """Test saving and reading files with local storage provider."""
        provider = LocalFileStorageProvider()
        
        content = b"Test file content for storage"
        storage_key = provider.save_file(content, "test.pdf")
        
        assert storage_key is not None
        assert provider.file_exists(storage_key)
        
        retrieved = provider.read_file(storage_key)
        assert retrieved == content
        
        # Cleanup
        provider.delete_file(storage_key)

    def test_local_storage_nonexistent_file_error(self):
        """Test that reading nonexistent file raises error."""
        provider = LocalFileStorageProvider()
        
        with pytest.raises(StorageException, match="not found"):
            provider.read_file("nonexistent-key")


class TestDocumentCategories:
    """Tests for document category management."""

    def test_initialize_default_categories(self, db_session: Session):
        """Test initialization of default document categories."""
        DocumentService.initialize_default_categories(db_session)
        
        from app.modules.documents.schemas import DEFAULT_CATEGORIES
        
        count = db_session.query(DocumentCategory).count()
        assert count >= len(DEFAULT_CATEGORIES)
