"""
Document Management API Endpoints
Upload, retrieve, and manage documents with full authorization and security.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.models import User
from app.modules.auth.dependencies import get_current_active_user, require_roles, enforce_institution_scope
from app.modules.instruments.models import Instrument
from app.modules.documents.models import Document, DocumentVersion
from app.modules.documents.service import DocumentService
from app.modules.documents.schemas import DocumentRead, DocumentCreateRequest, DocumentUpdateRequest
from app.modules.documents.validation import validate_upload, UploadValidationError
from app.modules.documents.scanner import get_scanner_provider
from app.modules.audit.service import log_audit_event
from app.common.exceptions import NotFoundException, ForbiddenException

router = APIRouter(tags=["documents"])


@router.post("/instruments/{instrument_id}/documents")
async def create_and_upload_document(
    instrument_id: str,
    category: str = Form(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new logical document and upload its first version.
    
    - Validates instrument exists and user can access it
    - Validates file upload (signature, size, type)
    - Scans file for malware
    - Records immutable version
    - Returns document and version metadata
    """
    
    # 1. Verify instrument exists and is active
    instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if not instrument:
        raise NotFoundException(f"Instrument {instrument_id} not found")
    
    # 2. Enforce institution scoping
    enforce_institution_scope(current_user, instrument.institution_id)
    
    # 3. Read and validate file
    try:
        file_content = await file.read()
    except Exception as e:
        log_audit_event(
            db=db,
            action="DOCUMENT_UPLOAD_FAILED",
            entity_type="Document",
            entity_id="",
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="FAILURE",
            metadata={"error": "Failed to read uploaded file", "reason": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file",
        )
    
    # Validate file
    try:
        mime_type, normalized_filename, size_str = validate_upload(
            file.filename or "document",
            file_content,
            file.content_type,
        )
    except UploadValidationError as e:
        log_audit_event(
            db=db,
            action="DOCUMENT_UPLOAD_REJECTED",
            entity_type="Document",
            entity_id="",
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="FAILURE",
            metadata={
                "reason": str(e),
                "filename": file.filename,
                "browser_mime": file.content_type,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # 4. Create logical document
    try:
        doc = DocumentService.create_document(
            db=db,
            instrument_id=instrument_id,
            category=category,
            title=title,
            description=description,
            created_by_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    # 5. Upload version
    try:
        version = DocumentService.upload_version(
            db=db,
            document_id=doc.id,
            file_content=file_content,
            original_filename=file.filename or "document",
            content_type=mime_type,
            uploader_user_id=current_user.id,
        )
    except Exception as e:
        log_audit_event(
            db=db,
            action="DOCUMENT_VERSION_UPLOAD_FAILED",
            entity_type="Document",
            entity_id=doc.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="FAILURE",
            metadata={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store document version",
        )
    
    # 6. Scan file
    scanner = get_scanner_provider()
    scan_result = scanner.scan_bytes(file_content, file.filename or "document")
    
    # Update version with scan result
    DocumentService.update_version_processing_status(
        db=db,
        version_id=version.id,
        processing_status=scan_result.status,
        scan_provider=scan_result.provider,
        scan_result_json=scan_result.to_json(),
        error_details=scan_result.error_message,
    )
    
    # 7. Emit audit event
    log_audit_event(
        db=db,
        action="DOCUMENT_UPLOADED",
        entity_type="Document",
        entity_id=doc.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        metadata={
            "document_id": doc.id,
            "version_id": version.id,
            "category": category,
            "filename": file.filename,
            "content_type": mime_type,
            "size_bytes": len(file_content),
            "sha256": version.sha256_hash,
            "scan_status": scan_result.status,
            "scan_provider": scan_result.provider,
        },
    )

    # Trigger post-save validation for the instrument
    try:
        from app.modules.validation.engine import trigger_post_save_validation
        trigger_post_save_validation(db, doc.instrument_id, triggered_by_user_id=current_user.id)
    except Exception:
        pass

    # Module 5: Emit material event notifications & admin oversight
    try:
        from app.modules.lifecycle.event_notification_service import emit_material_event
        emit_material_event(
            db=db,
            event_type="DOCUMENT_UPLOADED",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            actor_user=current_user,
            instrument_id=instrument.id,
            institution_id=instrument.institution_id,
            resulting_state=scan_result.status,
            details={
                "document_type": category,
                "filename": file.filename,
                "reference_number": instrument.reference_number,
            },
        )
        db.commit()
    except Exception:
        pass
    
    return {
        "success": True,
        "document_id": doc.id,
        "version_id": version.id,
        "version_number": version.version_number,
        "category": doc.category,
        "title": doc.title,
        "filename": normalized_filename,
        "content_type": mime_type,
        "file_size": size_str,
        "sha256_hash": version.sha256_hash,
        "processing_status": scan_result.status,
        "scan_provider": scan_result.provider,
        "uploaded_at": version.uploaded_at.isoformat(),
    }


@router.get("/instruments/{instrument_id}/documents")
async def list_documents_by_instrument(
    instrument_id: str,
    offset: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List documents for an instrument with pagination and filtering.
    """
    # Verify instrument exists
    instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if not instrument:
        raise NotFoundException(f"Instrument {instrument_id} not found")
    
    # Enforce institution scoping
    enforce_institution_scope(current_user, instrument.institution_id)
    
    # Get documents
    total, documents = DocumentService.get_documents_by_instrument(
        db=db,
        instrument_id=instrument_id,
        offset=offset,
        limit=limit,
    )
    
    # Filter by category if requested
    if category:
        documents = [d for d in documents if d.category == category]
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": d.id,
                "category": d.category,
                "title": d.title,
                "status": d.status,
                "current_version_number": d.versions[-1].version_number if d.versions else 0,
                "version_count": len(d.versions),
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
            }
            for d in documents
        ],
    }


@router.get("/documents/{document_id}")
async def get_document_detail(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve complete document metadata including all versions.
    """
    doc = DocumentService.get_document(db, document_id)
    if not doc:
        raise NotFoundException(f"Document {document_id} not found")
    
    # Enforce institution scoping
    enforce_institution_scope(current_user, doc.institution_id)
    
    return {
        "id": doc.id,
        "instrument_id": doc.instrument_id,
        "institution_id": doc.institution_id,
        "category": doc.category,
        "title": doc.title,
        "description": doc.description,
        "status": doc.status,
        "current_version_id": doc.current_version_id,
        "created_by_user_id": doc.created_by_user_id,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
        "version_count": len(doc.versions),
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "filename": v.original_filename,
                "content_type": v.content_type,
                "size_bytes": v.file_size_bytes,
                "sha256_hash": v.sha256_hash,
                "processing_status": v.processing_status,
                "scan_provider": v.scan_provider,
                "uploader_user_id": v.uploader_user_id,
                "uploaded_at": v.uploaded_at.isoformat(),
            }
            for v in sorted(doc.versions, key=lambda v: v.version_number)
        ],
    }


@router.get("/documents/{document_id}/versions/{version_id}/content")
async def download_document_content(
    document_id: str,
    version_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Download document version content with security checks.
    
    - Verifies document and version association
    - Checks access authorization
    - Refuses unsafe/quarantined files
    - Returns file with safe headers
    """
    
    # Get document
    doc = DocumentService.get_document(db, document_id)
    if not doc:
        # Don't disclose existence
        raise NotFoundException("Document not found")
    
    # Enforce institution scoping
    enforce_institution_scope(current_user, doc.institution_id)
    
    # Get version
    version = DocumentService.get_version(db, version_id)
    if not version or version.document_id != document_id:
        raise NotFoundException("Version not found for this document")
    
    # Check processing status
    unsafe_states = ["PENDING_SCAN", "INFECTED", "SCAN_UNAVAILABLE"]
    if version.processing_status in unsafe_states:
        if version.processing_status == "INFECTED":
            log_audit_event(
                db=db,
                action="DOCUMENT_DOWNLOAD_BLOCKED_INFECTED",
                entity_type="DocumentVersion",
                entity_id=version.id,
                actor_user_id=current_user.id,
                actor_email=current_user.email,
                actor_role=current_user.role,
                outcome="FAILURE",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="File is quarantined due to malware detection",
            )
        elif version.processing_status == "SCAN_UNAVAILABLE":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File scan unavailable; cannot confirm safety",
            )
        else:  # PENDING_SCAN
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="File scan still pending; please try again soon",
            )
    
    # Read file from storage
    from app.modules.documents.storage import get_storage_provider
    storage = get_storage_provider()
    
    try:
        file_content = storage.read_file(version.storage_key)
    except Exception as e:
        log_audit_event(
            db=db,
            action="DOCUMENT_DOWNLOAD_FAILED_STORAGE",
            entity_type="DocumentVersion",
            entity_id=version.id,
            actor_user_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            outcome="FAILURE",
            metadata={"error": "Storage read failed"},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve document",
        )
    
    # Log successful download
    log_audit_event(
        db=db,
        action="DOCUMENT_DOWNLOADED",
        entity_type="DocumentVersion",
        entity_id=version.id,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        metadata={
            "document_id": document_id,
            "version_number": version.version_number,
            "filename": version.original_filename,
            "size_bytes": version.file_size_bytes,
        },
    )
    
    # Return file with safe headers
    return Response(
        content=file_content,
        media_type=version.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{version.original_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache, no-store, must-revalidate",
        },
    )
