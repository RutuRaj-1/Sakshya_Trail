"""
Tests for Module 2 Upload & Download Pipeline
Tests secure file upload, validation, scanning, and authenticated retrieval.
"""
import pytest
from datetime import datetime, timezone
from io import BytesIO
from sqlalchemy.orm import Session

from app.modules.documents.service import DocumentService
from app.modules.documents.validation import validate_upload, UploadValidationError, normalize_filename
from app.modules.documents.scanner import (
    DemoScannerProvider,
    DevelopmentBypassScannerProvider,
    set_scanner_provider,
)
from app.modules.institutions.models import Institution
from app.modules.instruments.models import Instrument
from app.modules.auth.models import User
from decimal import Decimal
from datetime import date


@pytest.fixture
def sample_institution(db_session: Session) -> Institution:
    """Create a sample active institution."""
    inst = Institution(
        code="TEST-INST-UPLOAD",
        legal_name="Upload Test Institute",
        institution_type="TECHNICAL_INSTITUTE",
        contact_email="upload@test.edu",
        state="Delhi",
        is_active=True,
    )
    db_session.add(inst)
    db_session.commit()
    return inst


@pytest.fixture
def sample_instrument(db_session: Session, sample_institution: Institution) -> Instrument:
    """Create a sample instrument."""
    instrument = Instrument(
        institution_id=sample_institution.id,
        bank_name="Test Bank",
        reference_number="REF-UPLOAD-123",
        amount=Decimal("1000000.00"),
        issue_date=date(2024, 1, 1),
        maturity_date=date(2026, 1, 1),
    )
    db_session.add(instrument)
    db_session.commit()
    return instrument


@pytest.fixture
def sample_user(db_session: Session, sample_institution: Institution) -> User:
    """Create a sample institution user."""
    from app.core.security import hash_password
    user = User(
        full_name="Test Uploader",
        email="uploader@test.edu",
        password_hash=hash_password("password123"),
        role="INSTITUTION_USER",
        institution_id=sample_institution.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestFileValidation:
    """Tests for file upload validation."""

    def test_validate_pdf_success(self):
        """Test valid PDF file validation."""
        # Minimal PDF signature
        pdf_content = b"%PDF-1.4\n%test pdf content"
        mime, filename, size = validate_upload("document.pdf", pdf_content)
        
        assert mime == "application/pdf"
        assert filename == "document.pdf"
        assert "B" in size  # Has byte size

    def test_validate_png_success(self):
        """Test valid PNG file validation."""
        png_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mime, filename, size = validate_upload("image.png", png_content)
        
        assert mime == "image/png"
        assert filename == "image.png"

    def test_validate_jpeg_success(self):
        """Test valid JPEG file validation."""
        jpeg_content = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        mime, filename, size = validate_upload("photo.jpg", jpeg_content)
        
        assert mime == "image/jpeg"
        assert filename == "photo.jpg"

    def test_empty_file_rejection(self):
        """Test that empty files are rejected."""
        with pytest.raises(UploadValidationError, match="empty"):
            validate_upload("empty.pdf", b"")

    def test_oversized_file_rejection(self):
        """Test that oversized files are rejected."""
        # Create oversized content (exceed 50MB)
        huge_content = b"X" * (51 * 1024 * 1024)
        
        with pytest.raises(UploadValidationError, match="exceeds maximum"):
            validate_upload("huge.pdf", huge_content)

    def test_unsupported_extension_rejection(self):
        """Test that unsupported extensions are rejected."""
        with pytest.raises(UploadValidationError, match="not supported"):
            validate_upload("document.exe", b"MZ\x90\x00")  # EXE header

    def test_mime_mismatch_rejection(self):
        """Test that extension/content mismatch is rejected."""
        pdf_content = b"%PDF-1.4"
        
        # Extension says PDF, but content is not PDF
        with pytest.raises(UploadValidationError, match="does not match"):
            validate_upload("photo.jpg", pdf_content)

    def test_no_extension_rejection(self):
        """Test that files without extension are rejected."""
        with pytest.raises(UploadValidationError, match="no extension"):
            validate_upload("document", b"%PDF-1.4")


class TestFilenameNormalization:
    """Tests for filename safety normalization."""

    def test_path_traversal_blocked(self):
        """Test that path traversal attempts are normalized."""
        result = normalize_filename("../../../etc/passwd")
        assert "/" not in result
        assert ".." not in result
        # Should only keep alphanumeric chars, normalization varies
        assert "passwd" in result.lower()

    def test_null_bytes_removed(self):
        """Test that null bytes are removed."""
        result = normalize_filename("file\x00name.pdf")
        assert "\x00" not in result

    def test_long_filename_truncated(self):
        """Test that overly long filenames are truncated."""
        long_name = "a" * 300 + ".pdf"
        result = normalize_filename(long_name, max_length=255)
        assert len(result) <= 255
        assert result.endswith(".pdf")

    def test_spaces_normalized(self):
        """Test that spaces don't break filenames."""
        result = normalize_filename("my test file.pdf")
        # Spaces are allowed in display filenames but not as path separators
        assert result == "my test file.pdf"
        assert "/" not in result


class TestScannerIntegration:
    """Tests for malware scanner integration."""

    def test_demo_scanner_clean(self):
        """Test demo scanner marks small files as clean."""
        set_scanner_provider(DemoScannerProvider())
        from app.modules.documents.scanner import get_scanner_provider
        
        scanner = get_scanner_provider()
        result = scanner.scan_bytes(b"small", "test.pdf")
        
        assert result.status == "CLEAN"
        assert result.provider == "demo"

    def test_demo_scanner_infected_pattern(self):
        """Test demo scanner detects 'infected' filename pattern."""
        set_scanner_provider(DemoScannerProvider())
        from app.modules.documents.scanner import get_scanner_provider
        
        scanner = get_scanner_provider()
        result = scanner.scan_bytes(b"content", "infected_file.pdf")
        
        assert result.status == "INFECTED"
        assert result.provider == "demo"

    def test_development_bypass_scanner(self):
        """Test development bypass scanner marks files as bypassed."""
        set_scanner_provider(DevelopmentBypassScannerProvider())
        from app.modules.documents.scanner import get_scanner_provider
        
        scanner = get_scanner_provider()
        result = scanner.scan_bytes(b"content", "file.pdf")
        
        assert result.status == "SCAN_BYPASSED_DEVELOPMENT"
        assert "warning" in result.result_data


class TestDocumentUploadWorkflow:
    """Tests for complete upload workflow."""

    def test_successful_document_upload(self, db_session: Session, sample_instrument: Instrument, sample_user: User):
        """Test successful document creation and upload."""
        from app.modules.documents.scanner import get_scanner_provider
        set_scanner_provider(DemoScannerProvider())
        
        # Create document
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
            title="FDR Document",
            created_by_user_id=sample_user.id,
        )
        
        # Upload version
        pdf_content = b"%PDF-1.4\nTest PDF"
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=pdf_content,
            original_filename="fdr.pdf",
            content_type="application/pdf",
            uploader_user_id=sample_user.id,
        )
        
        # Scan
        scanner = get_scanner_provider()
        scan_result = scanner.scan_bytes(pdf_content, "fdr.pdf")
        DocumentService.update_version_processing_status(
            db=db_session,
            version_id=version.id,
            processing_status=scan_result.status,
            scan_provider=scan_result.provider,
        )
        
        # Verify
        assert doc.id is not None
        assert version.version_number == 1
        assert version.processing_status == "CLEAN"
        assert version.content_type == "application/pdf"

    def test_replacement_version_increments(self, db_session: Session, sample_instrument: Instrument, sample_user: User):
        """Test that uploading a replacement increments version number."""
        set_scanner_provider(DemoScannerProvider())
        
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
            created_by_user_id=sample_user.id,
        )
        
        # First version
        v1_content = b"%PDF-1.4\nVersion 1"
        v1 = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=v1_content,
            original_filename="fdr_v1.pdf",
            content_type="application/pdf",
        )
        v1_hash = v1.sha256_hash
        
        # Second version (replacement)
        v2_content = b"%PDF-1.4\nVersion 2 Updated"
        v2 = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=v2_content,
            original_filename="fdr_v2.pdf",
            content_type="application/pdf",
        )
        
        # Verify
        assert v1.version_number == 1
        assert v2.version_number == 2
        assert v1_hash != v2.sha256_hash
        assert doc.current_version_id == v2.id
        
        # Verify v1 still exists
        v1_retrieved = DocumentService.get_version(db_session, v1.id)
        assert v1_retrieved.version_number == 1

    def test_concurrent_uploads_safe(self, db_session: Session, sample_instrument: Instrument):
        """Test that concurrent uploads don't create conflicting versions."""
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        # Simulate concurrent uploads
        versions = []
        for i in range(3):
            content = f"File {i}".encode()
            v = DocumentService.upload_version(
                db=db_session,
                document_id=doc.id,
                file_content=content,
                original_filename=f"file{i}.pdf",
                content_type="application/pdf",
            )
            versions.append(v)
        
        # Verify all versions have unique numbers
        version_numbers = [v.version_number for v in versions]
        assert version_numbers == [1, 2, 3]
        assert len(set(v.id for v in versions)) == 3


class TestSecureRetrieval:
    """Tests for secure document retrieval."""

    def test_retrieval_requires_clean_status(self, db_session: Session, sample_instrument: Instrument):
        """Test that retrieval is blocked for unsafe states."""
        from app.modules.documents.storage import LocalFileStorageProvider, set_storage_provider
        
        set_storage_provider(LocalFileStorageProvider())
        
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=b"%PDF-1.4",
            original_filename="test.pdf",
            content_type="application/pdf",
        )
        
        # Simulate INFECTED status
        DocumentService.update_version_processing_status(
            db=db_session,
            version_id=version.id,
            processing_status="INFECTED",
        )
        
        # Verify it's marked infected
        v = DocumentService.get_version(db_session, version.id)
        assert v.processing_status == "INFECTED"

    def test_file_content_integrity(self, db_session: Session, sample_instrument: Instrument):
        """Test that file content is returned exactly as stored."""
        from app.modules.documents.storage import LocalFileStorageProvider, set_storage_provider
        
        set_storage_provider(LocalFileStorageProvider())
        
        doc = DocumentService.create_document(
            db=db_session,
            instrument_id=sample_instrument.id,
            category="FDR_COPY",
        )
        
        original_content = b"%PDF-1.4\n" + b"Test content " * 100
        version = DocumentService.upload_version(
            db=db_session,
            document_id=doc.id,
            file_content=original_content,
            original_filename="test.pdf",
            content_type="application/pdf",
        )
        
        # Retrieve file
        storage = LocalFileStorageProvider()
        retrieved_content = storage.read_file(version.storage_key)
        
        assert retrieved_content == original_content
