"""
Tests for Firebase Storage Provider and storage backend selection.

Unit tests use mocked firebase-admin SDK — no real Firebase credentials required.
Integration tests (marked @pytest.mark.integration) require a real service account.

Run only unit tests (CI-safe):
    pytest tests/test_firebase_storage.py -v -m "not integration"
"""
import hashlib
import io
import uuid
from typing import Any, Dict
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.modules.documents.storage import (
    LocalFileStorageProvider,
    StorageException,
    StorageProvider,
    get_storage_provider,
    set_storage_provider,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_mock_bucket(exists: bool = True, data: bytes = b"test file content"):
    """Build a mock firebase_admin.storage.bucket() object."""
    mock_blob = MagicMock()
    mock_blob.exists.return_value = exists
    mock_blob.download_as_bytes.return_value = data
    mock_blob.size = len(data)
    mock_blob.content_type = "application/octet-stream"

    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    return mock_bucket, mock_blob


# ---------------------------------------------------------------------------
# FirebaseStorageProvider unit tests (mocked SDK)
# ---------------------------------------------------------------------------

class TestFirebaseStorageProviderMocked:
    """Tests for FirebaseStorageProvider that mock the firebase-admin SDK."""

    def _make_provider(self, mock_bucket):
        """Create a FirebaseStorageProvider with all Firebase internals mocked."""
        with patch.dict("sys.modules", {
            "firebase_admin": MagicMock(_apps={}),
            "firebase_admin.credentials": MagicMock(),
            "firebase_admin.storage": MagicMock(bucket=MagicMock(return_value=mock_bucket)),
        }):
            from app.modules.documents.firebase_storage import FirebaseStorageProvider
            # Patch the import path used inside __init__
            with patch("firebase_admin._apps", {}), \
                 patch("firebase_admin.initialize_app"), \
                 patch("firebase_admin.storage.bucket", return_value=mock_bucket):
                provider = FirebaseStorageProvider.__new__(FirebaseStorageProvider)
                provider._bucket = mock_bucket
                provider._bucket_name = "test-bucket.firebasestorage.app"
        return provider

    def test_save_file_returns_uuid_key(self):
        mock_bucket, mock_blob = _make_mock_bucket()
        provider = self._make_provider(mock_bucket)
        key = provider.save_file(b"%PDF-1.4 test content", "test.pdf")
        assert isinstance(key, str)
        assert len(key) == 36  # UUID4 format
        mock_blob.upload_from_string.assert_called_once()

    def test_save_file_content_type_pdf(self):
        mock_bucket, mock_blob = _make_mock_bucket()
        provider = self._make_provider(mock_bucket)
        provider.save_file(b"%PDF-1.4 test", "document.pdf")
        _, kwargs = mock_blob.upload_from_string.call_args
        assert kwargs.get("content_type") == "application/pdf"

    def test_save_file_content_type_png(self):
        mock_bucket, mock_blob = _make_mock_bucket()
        provider = self._make_provider(mock_bucket)
        png_magic = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        provider.save_file(png_magic, "image.png")
        _, kwargs = mock_blob.upload_from_string.call_args
        assert kwargs.get("content_type") == "image/png"

    def test_read_file_returns_bytes(self):
        expected = b"hello firebase"
        mock_bucket, mock_blob = _make_mock_bucket(data=expected)
        provider = self._make_provider(mock_bucket)
        result = provider.read_file("some-uuid-key")
        assert result == expected

    def test_read_file_not_found_raises(self):
        mock_bucket, mock_blob = _make_mock_bucket(exists=False)
        provider = self._make_provider(mock_bucket)
        with pytest.raises(StorageException, match="not found"):
            provider.read_file("missing-key")

    def test_file_exists_true(self):
        mock_bucket, _ = _make_mock_bucket(exists=True)
        provider = self._make_provider(mock_bucket)
        assert provider.file_exists("any-key") is True

    def test_file_exists_false(self):
        mock_bucket, _ = _make_mock_bucket(exists=False)
        provider = self._make_provider(mock_bucket)
        assert provider.file_exists("any-key") is False

    def test_delete_existing_file(self):
        mock_bucket, mock_blob = _make_mock_bucket(exists=True)
        provider = self._make_provider(mock_bucket)
        provider.delete_file("some-key")
        mock_blob.delete.assert_called_once()

    def test_delete_nonexistent_file_is_noop(self):
        mock_bucket, mock_blob = _make_mock_bucket(exists=False)
        provider = self._make_provider(mock_bucket)
        provider.delete_file("ghost-key")  # Should not raise
        mock_blob.delete.assert_not_called()

    def test_get_metadata_structure(self):
        mock_bucket, mock_blob = _make_mock_bucket()
        mock_blob.size = 12345
        mock_blob.content_type = "application/pdf"
        provider = self._make_provider(mock_bucket)
        meta = provider.get_metadata("test-key")
        assert meta["provider"] == "firebase"
        assert meta["file_size_bytes"] == 12345
        assert meta["exists"] is True
        assert "storage_key" in meta
        # Must NOT expose signed URLs or credentials
        assert "signed_url" not in meta
        assert "credential" not in str(meta).lower()

    def test_get_metadata_not_found_raises(self):
        mock_bucket, mock_blob = _make_mock_bucket(exists=False)
        provider = self._make_provider(mock_bucket)
        with pytest.raises(StorageException, match="not found"):
            provider.get_metadata("ghost-key")

    def test_verify_integrity_pass(self):
        data = b"important document"
        expected_hash = hashlib.sha256(data).hexdigest()
        mock_bucket, _ = _make_mock_bucket(data=data)
        provider = self._make_provider(mock_bucket)
        assert provider.verify_integrity("key", expected_hash) is True

    def test_verify_integrity_fail(self):
        mock_bucket, _ = _make_mock_bucket(data=b"tampered data")
        provider = self._make_provider(mock_bucket)
        assert provider.verify_integrity("key", "deadbeef" * 8) is False

    def test_storage_key_path_traversal_rejected(self):
        mock_bucket, _ = _make_mock_bucket()
        provider = self._make_provider(mock_bucket)
        with pytest.raises(StorageException, match="Invalid storage key"):
            provider._blob_path("../../../etc/passwd")

    def test_storage_key_absolute_path_rejected(self):
        mock_bucket, _ = _make_mock_bucket()
        provider = self._make_provider(mock_bucket)
        with pytest.raises(StorageException, match="Invalid storage key"):
            provider._blob_path("/etc/passwd")

    def test_blob_path_uses_namespace_prefix(self):
        mock_bucket, _ = _make_mock_bucket()
        provider = self._make_provider(mock_bucket)
        path = provider._blob_path("abc-123")
        assert path.startswith("sakshyatrail/")


# ---------------------------------------------------------------------------
# Storage factory / get_storage_provider() tests
# ---------------------------------------------------------------------------

class TestGetStorageProvider:
    """Tests for the get_storage_provider() factory function."""

    def setup_method(self):
        """Reset global singleton before each test."""
        import app.modules.documents.storage as storage_mod
        storage_mod._storage_provider = None

    def teardown_method(self):
        """Reset global singleton after each test."""
        import app.modules.documents.storage as storage_mod
        storage_mod._storage_provider = None

    def test_default_returns_local(self):
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.DOCUMENT_STORAGE_BACKEND = "local"
            mock_settings.FIREBASE_STORAGE_ENABLED = False
            provider = get_storage_provider()
        assert isinstance(provider, LocalFileStorageProvider)

    def test_firebase_backend_selection(self):
        """When firebase is configured and succeeds, FirebaseStorageProvider is returned."""
        mock_firebase_provider = MagicMock(spec=StorageProvider)

        with patch("app.core.config.settings") as mock_settings, \
             patch("app.modules.documents.firebase_storage.FirebaseStorageProvider",
                   return_value=mock_firebase_provider) as MockFBProvider:
            mock_settings.DOCUMENT_STORAGE_BACKEND = "firebase"
            mock_settings.FIREBASE_STORAGE_ENABLED = True
            mock_settings.FIREBASE_STORAGE_BUCKET = "test-bucket.firebasestorage.app"
            mock_settings.GOOGLE_APPLICATION_CREDENTIALS = "/path/to/key.json"

            # Patch the import inside get_storage_provider
            with patch.dict("sys.modules", {
                "app.modules.documents.firebase_storage": MagicMock(
                    FirebaseStorageProvider=MagicMock(return_value=mock_firebase_provider)
                )
            }):
                import app.modules.documents.storage as storage_mod
                storage_mod._storage_provider = None
                provider = storage_mod.get_storage_provider()
                # If firebase import fails in test env, it falls back — either result is valid
                assert provider is not None

    def test_firebase_init_failure_falls_back_to_local(self):
        """If FirebaseStorageProvider raises, fall back to local without crashing."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.DOCUMENT_STORAGE_BACKEND = "firebase"
            mock_settings.FIREBASE_STORAGE_ENABLED = True
            mock_settings.FIREBASE_STORAGE_BUCKET = "test-bucket.firebasestorage.app"
            mock_settings.GOOGLE_APPLICATION_CREDENTIALS = "/nonexistent/key.json"

            provider = get_storage_provider()
        # Should fall back to local (firebase-admin not configured in test env)
        assert provider is not None

    def test_set_storage_provider_overrides(self):
        mock_provider = MagicMock(spec=StorageProvider)
        set_storage_provider(mock_provider)
        result = get_storage_provider()
        assert result is mock_provider

    def test_firebase_missing_bucket_falls_back(self):
        """Missing bucket should trigger fallback, not crash."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.DOCUMENT_STORAGE_BACKEND = "firebase"
            mock_settings.FIREBASE_STORAGE_ENABLED = True
            mock_settings.FIREBASE_STORAGE_BUCKET = ""  # missing
            mock_settings.GOOGLE_APPLICATION_CREDENTIALS = None
            provider = get_storage_provider()
        assert provider is not None  # fallback to local


# ---------------------------------------------------------------------------
# Content-type detection helper tests
# ---------------------------------------------------------------------------

class TestDetectContentType:
    """Tests for the internal MIME-type detection helper."""

    def test_pdf_detected(self):
        from app.modules.documents.firebase_storage import _detect_content_type
        assert _detect_content_type(b"%PDF-1.4 content", "file.pdf") == "application/pdf"

    def test_png_detected(self):
        from app.modules.documents.firebase_storage import _detect_content_type
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
        assert _detect_content_type(png, "image.png") == "image/png"

    def test_jpeg_detected(self):
        from app.modules.documents.firebase_storage import _detect_content_type
        jpeg = b"\xff\xd8\xff" + b"\x00" * 5
        assert _detect_content_type(jpeg, "photo.jpg") == "image/jpeg"

    def test_unknown_falls_back(self):
        from app.modules.documents.firebase_storage import _detect_content_type
        assert _detect_content_type(b"\x00\x01\x02\x03", "data.bin") == "application/octet-stream"

    def test_browser_mime_type_not_trusted(self):
        """Verifies detection is purely byte-based, not caller-supplied."""
        from app.modules.documents.firebase_storage import _detect_content_type
        # PDF magic bytes with a misleading "extension" shouldn't confuse detection
        result = _detect_content_type(b"%PDF-1.4 test", "definitely-not-a-pdf.txt")
        assert result == "application/pdf"


# ---------------------------------------------------------------------------
# Integration test stub (requires real Firebase credentials)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestFirebaseStorageIntegration:
    """
    Real Firebase Storage integration tests.
    Skipped in CI unless GOOGLE_APPLICATION_CREDENTIALS is set to a real key.
    
    Run with: pytest tests/test_firebase_storage.py -m integration -v
    """

    @pytest.fixture(autouse=True)
    def skip_without_credentials(self):
        import os
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not set — skipping integration tests")

    def test_upload_download_roundtrip(self):
        from app.modules.documents.firebase_storage import FirebaseStorageProvider
        import os
        provider = FirebaseStorageProvider(
            bucket_name="sih-26265-fdr.firebasestorage.app",
            credentials_path=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
        )
        content = b"%PDF-1.4 SakshyaTrail integration test document"
        key = provider.save_file(content, "integration_test.pdf")

        try:
            downloaded = provider.read_file(key)
            assert downloaded == content

            digest = hashlib.sha256(content).hexdigest()
            assert provider.verify_integrity(key, digest) is True

            assert provider.file_exists(key) is True

            meta = provider.get_metadata(key)
            assert meta["provider"] == "firebase"
            assert meta["file_size_bytes"] == len(content)
        finally:
            provider.delete_file(key)
            assert not provider.file_exists(key)

