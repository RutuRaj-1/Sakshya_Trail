"""
Storage Provider Abstraction for Document Files
Provides an extensible interface for file storage with local filesystem implementation.
Design: Store files outside frontend static/public directories; never expose storage paths.
"""
import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from io import BytesIO


class StorageProvider(ABC):
    """
    Abstract base class for storage providers.
    Implementations must handle file save/read/delete with server-managed keys.
    """

    @abstractmethod
    def save_file(self, content: bytes, original_filename: str) -> str:
        """
        Save file content and return a server-generated storage key (never user-supplied path).
        
        Args:
            content: File bytes to store
            original_filename: Original filename for metadata (not used in storage path)
        
        Returns:
            Unique storage key (string identifier)
        
        Raises:
            StorageException on write failure
        """
        pass

    @abstractmethod
    def read_file(self, storage_key: str) -> bytes:
        """
        Read stored file by storage key.
        
        Args:
            storage_key: Server-generated storage identifier
        
        Returns:
            File content as bytes
        
        Raises:
            StorageException if key not found or read fails
        """
        pass

    @abstractmethod
    def file_exists(self, storage_key: str) -> bool:
        """
        Check whether a file exists in storage.
        
        Args:
            storage_key: Server-generated storage identifier
        
        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def delete_file(self, storage_key: str) -> None:
        """
        Delete a file from storage (for cleanup of uncommitted temporary uploads).
        
        Args:
            storage_key: Server-generated storage identifier
        
        Raises:
            StorageException on delete failure
        """
        pass

    @abstractmethod
    def get_metadata(self, storage_key: str) -> Dict[str, Any]:
        """
        Obtain internal storage metadata without exposing secrets.
        
        Args:
            storage_key: Server-generated storage identifier
        
        Returns:
            Dict with metadata (e.g., file_size, path_info) safe for logging
        
        Raises:
            StorageException if key not found
        """
        pass


class StorageException(Exception):
    """Exception raised by storage operations."""
    pass


class LocalFileStorageProvider(StorageProvider):
    """
    Local filesystem storage provider for the working prototype.
    
    Design:
    - Files stored in a dedicated directory outside frontend/static/public.
    - Storage keys are server-generated UUIDs (deterministic per version).
    - Never exposes storage path to browser or client.
    - Handles interrupted writes and basic error recovery.
    - Excluded from Git via .gitignore.
    
    Consistency Strategy:
    - Write atomically using a temporary file, then rename.
    - Database transaction ensures metadata and file are consistent.
    - If database commit fails after file write, the orphaned file remains (acceptable for prototype).
    - Cleanup of orphaned files can be handled by periodic maintenance jobs.
    """

    def __init__(self, base_directory: Optional[str] = None):
        """
        Initialize local storage provider.
        
        Args:
            base_directory: Root directory for file storage. 
                          Defaults to ./storage/documents outside the workspace.
                          Must be created if it doesn't exist.
        """
        if base_directory is None:
            # Default to a storage directory at the backend root level
            base_directory = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "..",
                "storage",
                "documents"
            )
        
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
        
        # Verify the directory is writable
        test_file = self.base_directory / ".writable_test"
        try:
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise StorageException(f"Storage directory is not writable: {self.base_directory}") from e

    def save_file(self, content: bytes, original_filename: str) -> str:
        """
        Save file content with server-generated UUID key.
        
        Atomic write using temporary file + rename pattern.
        """
        storage_key = str(uuid.uuid4())
        file_path = self.base_directory / storage_key
        temp_path = self.base_directory / f"{storage_key}.tmp"

        try:
            # Write to temporary file first
            temp_path.write_bytes(content)
            # Atomic rename
            temp_path.replace(file_path)
            return storage_key
        except Exception as e:
            # Clean up temporary file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise StorageException(f"Failed to save file '{original_filename}': {str(e)}") from e

    def read_file(self, storage_key: str) -> bytes:
        """
        Read stored file by storage key.
        """
        file_path = self.base_directory / storage_key
        
        if not file_path.exists():
            raise StorageException(f"File not found: {storage_key}")
        
        try:
            return file_path.read_bytes()
        except Exception as e:
            raise StorageException(f"Failed to read file '{storage_key}': {str(e)}") from e

    def file_exists(self, storage_key: str) -> bool:
        """
        Check whether a file exists in storage.
        """
        file_path = self.base_directory / storage_key
        return file_path.exists()

    def delete_file(self, storage_key: str) -> None:
        """
        Delete a file from storage.
        Safe to call on non-existent files (no-op).
        """
        file_path = self.base_directory / storage_key
        
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                raise StorageException(f"Failed to delete file '{storage_key}': {str(e)}") from e

    def get_metadata(self, storage_key: str) -> Dict[str, Any]:
        """
        Return internal metadata without exposing full path.
        """
        file_path = self.base_directory / storage_key
        
        if not file_path.exists():
            raise StorageException(f"File not found: {storage_key}")
        
        try:
            stat = file_path.stat()
            return {
                "storage_key": storage_key,
                "file_size_bytes": stat.st_size,
                "exists": True,
                "provider": "local",
            }
        except Exception as e:
            raise StorageException(f"Failed to get metadata for '{storage_key}': {str(e)}") from e


# Global storage provider instance (singleton pattern)
# In a production system, this might be dependency-injected via FastAPI Depends
_storage_provider: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    """
    Get or initialize the global storage provider instance.

    Selection priority:
    1. If an explicit provider was set via set_storage_provider() (e.g. in tests), use it.
    2. If DOCUMENT_STORAGE_BACKEND=firebase AND FIREBASE_STORAGE_ENABLED=true, attempt
       to initialise FirebaseStorageProvider. On any initialisation failure, log a WARNING
       and fall back to local storage rather than crashing startup.
    3. Default: LocalFileStorageProvider (local filesystem).
    """
    global _storage_provider
    if _storage_provider is None:
        try:
            from app.core.config import settings
            backend = getattr(settings, "DOCUMENT_STORAGE_BACKEND", "local").lower()
            firebase_enabled = getattr(settings, "FIREBASE_STORAGE_ENABLED", False)

            if backend == "firebase" and firebase_enabled:
                try:
                    from app.modules.documents.firebase_storage import FirebaseStorageProvider
                    creds_path = getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", None)
                    bucket = settings.FIREBASE_STORAGE_BUCKET
                    if not bucket:
                        raise ValueError("FIREBASE_STORAGE_BUCKET is not configured.")
                    _storage_provider = FirebaseStorageProvider(
                        bucket_name=bucket,
                        credentials_path=creds_path,
                    )
                    print(
                        f"[Storage] Backend: Firebase Cloud Storage "
                        f"(bucket={bucket})"
                    )
                except Exception as exc:
                    print(
                        f"[Storage WARNING] Firebase storage unavailable: {exc}. "
                        f"Falling back to local storage."
                    )
                    _storage_provider = LocalFileStorageProvider()
            else:
                _storage_provider = LocalFileStorageProvider()
                print("[Storage] Backend: local filesystem")
        except Exception:
            _storage_provider = LocalFileStorageProvider()
    return _storage_provider


def set_storage_provider(provider: StorageProvider) -> None:
    """
    Set the global storage provider (for testing or alternative implementations).
    """
    global _storage_provider
    _storage_provider = provider
