"""
Documents Module - Secure Document Intake & Evidence Intelligence
Provides document versioning, storage abstraction, integrity tracking, and processing state management.
"""

from app.modules.documents.models import Document, DocumentVersion, DocumentCategory
from app.modules.documents.service import DocumentService
from app.modules.documents.schemas import (
    DocumentRead,
    DocumentCreateRequest,
    DocumentUploadResponse,
    DEFAULT_CATEGORIES,
    PROCESSING_STATES,
)
from app.modules.documents.storage import (
    StorageProvider,
    LocalFileStorageProvider,
    get_storage_provider,
    set_storage_provider,
)

__all__ = [
    "Document",
    "DocumentVersion",
    "DocumentCategory",
    "DocumentService",
    "DocumentRead",
    "DocumentCreateRequest",
    "DocumentUploadResponse",
    "DEFAULT_CATEGORIES",
    "PROCESSING_STATES",
    "StorageProvider",
    "LocalFileStorageProvider",
    "get_storage_provider",
    "set_storage_provider",
]
