"""
Documents Module - Pydantic Schemas for API Requests and Responses
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# Processing state constants
PROCESSING_STATES = {
    "PENDING_SCAN": "Awaiting malware scan",
    "CLEAN": "Scan passed (no threats detected)",
    "INFECTED": "Scan detected potential threats",
    "SCAN_UNAVAILABLE": "Scan provider unavailable",
    "SCAN_BYPASSED_DEVELOPMENT": "Scan bypassed (development mode only)",
    "PROCESSING_FAILED": "Processing failed with error",
    "ARCHIVED": "Version archived",
}

# Document categories (prototype initial set; extensible)
DEFAULT_CATEGORIES = {
    "FDR_COPY": "Scanned copy of the Fixed Deposit Receipt",
    "FDR_RECEIPT": "Official FDR Receipt / Deposit Certificate",
    "FDR_CERTIFICATE": "Fixed Deposit Certificate / Advice Scan",
    "SANCTION_ORDER": "Regulatory or Institution Sanction Order",
    "DISCHARGE_SANCTION": "Discharge / Release Sanction Order",
    "BANK_CONFIRMATION": "Official bank confirmation letter",
    "BANK_CONFIRMATION_LETTER": "Bank Confirmation Letter",
    "LIEN_OR_PLEDGE_LETTER": "Lien or pledge endorsement letter",
    "AFFIDAVIT": "Sworn affidavit from institution",
    "REQUEST_LETTER": "Letter requesting release/renewal/verification",
    "RENEWAL_ADVICE": "Renewal / Lineage Rollover Notice",
    "SUPPORTING_DOCUMENT": "Additional supporting evidence",
    "OTHER_SUPPORTING": "Other Supporting Evidence",
    "OTHER": "Other document types",
}


class DocumentCategorySchema(BaseModel):
    """Category definition schema."""
    id: str
    code: str
    display_name: str
    description: Optional[str] = None
    is_active: bool = True
    metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentVersionRead(BaseModel):
    """Document version response schema."""
    id: str
    document_id: str
    version_number: int
    original_filename: str
    content_type: str
    file_size_bytes: int
    sha256_hash: str
    uploader_user_id: Optional[str] = None
    uploaded_at: datetime
    processing_status: str
    scan_provider: Optional[str] = None
    scan_result_json: Optional[str] = None
    error_details: Optional[str] = None
    parent_version_id: Optional[str] = None
    created_at: datetime


class DocumentRead(BaseModel):
    """Logical document response schema."""
    id: str
    institution_id: str
    instrument_id: str
    category: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: str
    current_version_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    archived_reason: Optional[str] = None
    versions: List[DocumentVersionRead] = []


class DocumentCreateRequest(BaseModel):
    """Request to create a new logical document."""
    instrument_id: str = Field(..., description="UUID of parent instrument")
    category: str = Field(..., description="Document category code")
    title: Optional[str] = Field(None, description="Optional document title")
    description: Optional[str] = Field(None, description="Optional document description")
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in DEFAULT_CATEGORIES:
            raise ValueError(f"Invalid category. Allowed: {', '.join(DEFAULT_CATEGORIES.keys())}")
        return v


class DocumentUpdateRequest(BaseModel):
    """Request to update document metadata."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and v not in ["ACTIVE", "ARCHIVED"]:
            raise ValueError("Status must be ACTIVE or ARCHIVED")
        return v


class DocumentUploadResponse(BaseModel):
    """Response when a document version is successfully uploaded."""
    document_id: str
    version_id: str
    version_number: int
    storage_key: str
    file_size_bytes: int
    sha256_hash: str
    processing_status: str = "PENDING_SCAN"
    uploaded_at: datetime


class DocumentListResponse(BaseModel):
    """List response with pagination."""
    total: int
    offset: int
    limit: int
    items: List[DocumentRead]
