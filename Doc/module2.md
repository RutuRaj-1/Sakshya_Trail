# FDR Sentinel — Module 2 Specification & Implementation Report
## Secure Document Intake & Evidence Intelligence Foundation

**Project:** FDR Sentinel (AICTE Security Deposit / FDR Lifecycle Integrity Platform)  
**Problem Statement ID:** 26265  
**Department:** Regulation Bureau, All India Council for Technical Education (AICTE)  
**Module:** 2 — Secure Document Intake & Evidence Intelligence (Foundation Layer)  
**Stage:** Foundation Implementation Complete  
**Date:** October 24, 2026  
**Status:** Completed & Verified (16 Backend Tests Passing, Migration Applied)

---

## 1. Executive Summary

Module 2 of **FDR Sentinel** establishes the foundational data model and storage infrastructure for **Secure Document Intake & Evidence Intelligence**. This layer enables:

1. **Logical Document Entity**: One document record per physical/logical document within an instrument.
2. **Immutable Document Versioning**: Each upload creates a distinct, immutable version with SHA-256 integrity tracking.
3. **Document Categories**: Configurable, extensible catalog of document types (FDR_COPY, BANK_CONFIRMATION, etc.).
4. **Processing State Machine**: Explicit scanning/malware states (PENDING_SCAN, CLEAN, INFECTED, PROCESSING_FAILED, etc.).
5. **Private Storage Abstraction**: Server-managed storage keys; files never exposed to client; extensible for S3 or other backends.
6. **Audit Integration**: All material actions logged via the existing Module 1 audit service.
7. **Database Migrations**: Clean, additive Alembic migration (no deletions; backward-compatible).

Module 2 does **not** own: FDR lifecycle transitions, bank verification, release/refund approval, or the general discrepancy/risk engine (those are Modules 3–5).

---

## 2. Database Schema & Models

### 2.1 Three Core Tables

#### A. `document_categories` Table
Configurable document category catalog supporting extensibility and optional metadata.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | String(36) UUID | PK | Unique category identifier |
| `code` | String(50) | UNIQUE, NOT NULL | Machine code (e.g., FDR_COPY) |
| `display_name` | String(255) | NOT NULL | Human-readable name |
| `description` | Text | Nullable | Optional category details |
| `is_active` | Boolean | NOT NULL, DEFAULT=true | Active/inactive flag |
| `metadata_json` | Text | Nullable | Optional category-specific rules (JSON) |
| `created_at` | DateTime(UTC) | NOT NULL | Record creation timestamp |
| `updated_at` | DateTime(UTC) | NOT NULL | Last modification timestamp |

**Indexes:**
- `code` (unique)
- `is_active`

**Initial Categories:**
- FDR_COPY: Scanned copy of the Fixed Deposit Receipt
- BANK_CONFIRMATION: Official bank confirmation letter
- LIEN_OR_PLEDGE_LETTER: Lien or pledge endorsement letter
- AFFIDAVIT: Sworn affidavit from institution
- REQUEST_LETTER: Letter requesting release/renewal/verification
- SUPPORTING_DOCUMENT: Additional supporting evidence
- OTHER: Other document types

#### B. `documents` Table
Logical document entity representing a single conceptual document within an instrument.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | String(36) UUID | PK | Unique document identifier |
| `institution_id` | String(36) UUID | FK (institutions), NOT NULL | Parent institution (enforces scoping) |
| `instrument_id` | String(36) UUID | FK (instruments), NOT NULL | Parent FDR/instrument |
| `category` | String(50) | NOT NULL | Document category code |
| `title` | String(255) | Nullable | Optional document title |
| `description` | Text | Nullable | Optional document description |
| `status` | String(50) | NOT NULL, DEFAULT='ACTIVE' | ACTIVE or ARCHIVED |
| `current_version_id` | String(36) UUID | FK (document_versions), Nullable | Pointer to most recent version |
| `created_by_user_id` | String(36) UUID | Nullable | User who created the document |
| `created_at` | DateTime(UTC) | NOT NULL | Record creation timestamp |
| `updated_at` | DateTime(UTC) | NOT NULL | Last modification timestamp |
| `archived_at` | DateTime(UTC) | Nullable | Timestamp when document was archived |
| `archived_reason` | String(255) | Nullable | Reason for archival |

**Indexes:**
- `institution_id` (for institution scoping)
- `instrument_id` (for instrument lookup)
- `category` (for filtering)
- `status` (for active/archived filtering)

**Constraints:**
- CASCADE delete on institution and instrument deletion
- Foreign key linking `current_version_id` to document_versions

#### C. `document_versions` Table
Immutable document version records representing individual upload instances.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | String(36) UUID | PK | Unique version identifier (immutable) |
| `document_id` | String(36) UUID | FK (documents), NOT NULL | Parent logical document |
| `version_number` | Integer | NOT NULL | Monotonically increasing within document |
| `storage_key` | String(255) | UNIQUE, NOT NULL | Server-generated storage identifier (never user-supplied path) |
| `original_filename` | String(255) | NOT NULL | Sanitized original filename (display only) |
| `content_type` | String(100) | NOT NULL | MIME type (e.g., application/pdf) |
| `file_size_bytes` | Integer | NOT NULL | File size in bytes |
| `sha256_hash` | String(64) | NOT NULL | SHA-256 hex digest for integrity |
| `uploader_user_id` | String(36) UUID | Nullable | User who uploaded the version |
| `uploaded_at` | DateTime(UTC) | NOT NULL | Upload timestamp |
| `processing_status` | String(50) | NOT NULL, DEFAULT='PENDING_SCAN' | Scan state machine |
| `scan_provider` | String(100) | Nullable | Name of scan service (e.g., ClamAV) |
| `scan_result_json` | Text | Nullable | Scan result metadata (JSON-encoded) |
| `error_details` | Text | Nullable | Error message if processing failed |
| `parent_version_id` | String(36) UUID | FK (document_versions), Nullable | Reference to previous version (version history linkage) |
| `created_at` | DateTime(UTC) | NOT NULL | Version creation timestamp |

**Indexes:**
- `document_id` (for version lookup by document)
- `storage_key` (unique, for fast key lookup)
- `sha256_hash` (for integrity verification and duplicate detection)
- `processing_status` (for querying by scan state)

**Constraints:**
- CASCADE delete on document deletion
- Self-referential foreign key on `parent_version_id` (allows version chains)
- Immutable once created (no UPDATE on file content fields)

---

## 3. Processing States

The `processing_status` field implements an explicit state machine for document scanning and validation.

| State | Description | Transition Rules |
|-------|-------------|------------------|
| **PENDING_SCAN** | Default state; awaiting malware scan | → CLEAN, INFECTED, SCAN_UNAVAILABLE, PROCESSING_FAILED |
| **CLEAN** | Scan passed; no threats detected | Final (read-only) |
| **INFECTED** | Scan detected potential threats | Final (quarantine state) |
| **SCAN_UNAVAILABLE** | Scan service unavailable; deferred | → PENDING_SCAN (retry), or remain pending |
| **SCAN_BYPASSED_DEVELOPMENT** | Scan bypassed (development mode only) | Development-only; visibly labeled; audit trail required |
| **PROCESSING_FAILED** | Processing failed with error | → PENDING_SCAN (retry after fix) |
| **ARCHIVED** | Document version archived | Applied to logical document, not individual versions |

**Design Philosophy:**
- States are **explicit and separate** from administrative status or trust level.
- No implicit upgrade from PENDING_SCAN to CLEAN; requires scanner response.
- "Pending/unconfirmed/source unavailable" are **legitimate terminal states** if scanner timeout/unavailable.
- Production configuration **fails closed**: if no scanner is configured, new uploads remain in PENDING_SCAN unless explicitly bypassed (with audit trail).
- Development bypass is **visibly labeled** and **auditable**.

---

## 4. Document Category Catalog

Initial categories are configurable and extensible. Categories can be added, enabled/disabled, and updated without database schema changes.

**Prototype Initial Categories:**
```python
{
    "FDR_COPY": "Scanned copy of the Fixed Deposit Receipt",
    "BANK_CONFIRMATION": "Official bank confirmation letter",
    "LIEN_OR_PLEDGE_LETTER": "Lien or pledge endorsement letter",
    "AFFIDAVIT": "Sworn affidavit from institution",
    "REQUEST_LETTER": "Letter requesting release/renewal/verification",
    "SUPPORTING_DOCUMENT": "Additional supporting evidence",
    "OTHER": "Other document types",
}
```

**Initialization:** `DocumentService.initialize_default_categories(db)` is idempotent and seeds the catalog on first application startup.

---

## 5. Storage Abstraction Layer

### 5.1 Storage Provider Interface (`StorageProvider`)

Abstract base class defining file operations:
- `save_file(content: bytes, original_filename: str) → storage_key: str`
- `read_file(storage_key: str) → bytes`
- `file_exists(storage_key: str) → bool`
- `delete_file(storage_key: str) → None`
- `get_metadata(storage_key: str) → Dict[str, Any]`

### 5.2 LocalFileStorageProvider (Reference Implementation)

**Design:**
- Files stored in dedicated directory: `./storage/documents/` (outside frontend static/public)
- **Server-generated UUID keys**: never accepts user-supplied paths
- **Atomic writes**: uses temporary file + rename pattern to prevent partial writes
- **Excluded from Git**: add `storage/` to `.gitignore`
- **Extensible**: can be replaced with S3-compatible provider later

**Key Behaviors:**
- `save_file()` returns a UUID-based storage key; original_filename is metadata only
- Files with same content get different storage keys (content-independent naming)
- Concurrent writes are safe due to UUID uniqueness
- Delete is idempotent (no-op on missing file)
- Get metadata returns safe info (key, size, provider) without exposing filesystem path

**Consistency & Recovery:**
- Database transaction ensures metadata and file writes are consistent at commit time
- If database commit fails after file write, orphaned file remains (acceptable for prototype)
- Cleanup of orphaned files can be handled by periodic maintenance jobs (not implemented in foundation)

### 5.3 Extensibility

To use S3-compatible storage later:
1. Create `S3StorageProvider(StorageProvider)` subclass
2. Implement abstract methods using boto3 or similar
3. Update `get_storage_provider()` to select based on configuration
4. No changes needed to models or business logic

---

## 6. Service Layer (`DocumentService`)

Business logic and workflows for document management.

### 6.1 Key Methods

**`create_document(db, instrument_id, category, title, description, created_by_user_id)`**
- Creates a logical document linked to an instrument
- Validates: instrument exists, institution is active, category is valid
- Initializes status='ACTIVE', current_version_id=None
- Logs audit event (DOCUMENT_CREATED)

**`upload_version(db, document_id, file_content, original_filename, content_type, uploader_user_id)`**
- Uploads new version of document (immutable once created)
- Computes SHA-256 hash
- Stores file via storage provider (server-generated key)
- Increments version_number monotonically
- Sets processing_status='PENDING_SCAN' by default
- Updates document's current_version_id pointer
- Logs audit event (DOCUMENT_VERSION_UPLOADED)

**`update_version_processing_status(db, version_id, processing_status, scan_provider, scan_result_json, error_details)`**
- Updates scan/processing state after scanning
- Validates status is in PROCESSING_STATES
- Records scan provider, result metadata, and errors
- Logs audit event (DOCUMENT_SCAN_STATUS_UPDATED)

**`update_document(db, document_id, update_data, updated_by_user_id)`**
- Updates document metadata (title, description, status)
- Handles ACTIVE → ARCHIVED transition with archived_at and archived_reason
- Logs audit event (DOCUMENT_UPDATED)

**`get_document(db, document_id)`** / **`get_documents_by_instrument(db, instrument_id, offset, limit)`**
- Retrieves documents with pagination

**`initialize_default_categories(db)`**
- Idempotent seeding of default categories on startup

---

## 7. API Schemas & Endpoints

### 7.1 Request/Response Schemas

**DocumentCreateRequest:**
```python
{
    "instrument_id": "uuid",
    "category": "FDR_COPY | BANK_CONFIRMATION | ...",
    "title": "Optional title",
    "description": "Optional description"
}
```

**DocumentUpdateRequest:**
```python
{
    "title": "Updated title (optional)",
    "description": "Updated description (optional)",
    "status": "ACTIVE | ARCHIVED (optional)"
}
```

**DocumentRead (Response):**
```python
{
    "id": "uuid",
    "institution_id": "uuid",
    "instrument_id": "uuid",
    "category": "FDR_COPY",
    "title": "...",
    "description": "...",
    "status": "ACTIVE",
    "current_version_id": "uuid",
    "created_by_user_id": "uuid",
    "created_at": "2026-10-24T18:40:00Z",
    "updated_at": "2026-10-24T18:40:00Z",
    "archived_at": null,
    "archived_reason": null,
    "versions": [
        {
            "id": "uuid",
            "version_number": 1,
            "original_filename": "fdr_copy.pdf",
            "content_type": "application/pdf",
            "file_size_bytes": 2048000,
            "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "processing_status": "CLEAN",
            "scan_provider": "ClamAV",
            "uploaded_at": "2026-10-24T18:40:10Z"
        }
    ]
}
```

### 7.2 Planned API Endpoints (Module 3+)

Future modules will add:
- `POST /api/v1/documents` — Create document
- `POST /api/v1/documents/{id}/versions` — Upload version
- `GET /api/v1/documents/{id}` — Retrieve document
- `PATCH /api/v1/documents/{id}` — Update document metadata
- `GET /api/v1/instruments/{instrument_id}/documents` — List documents for instrument
- Administrative endpoints for category management

---

## 8. Database Migration

### 8.1 Migration File

**Revision ID:** `a7b2c4d9e8f5`  
**Description:** Add Module 2 documents, versions, categories, and storage abstraction  
**Depends On:** `058efcf1e144` (Module 1 expansion)  
**Applied:** October 24, 2026 at 23:50 UTC

**Changes:**
- Creates `document_categories` table with indexes
- Creates `documents` table with foreign keys and indexes
- Creates `document_versions` table with self-referential foreign key and indexes
- Adds foreign key constraint `documents.current_version_id` → `document_versions.id`

**Reversibility:** Full downgrade removes all three tables and indexes.

### 8.2 Migration Verification

```powershell
alembic upgrade head
# Output:
# INFO  [alembic.runtime.migration] Running upgrade 058efcf1e144 -> a7b2c4d9e8f5, add_module_2_documents_storage
```

Migration applies cleanly on existing Module 1 schema without conflicts or data loss.

---

## 9. Automated Test Suite

### 9.1 Test Coverage

**File:** `backend/tests/test_documents_module.py`  
**Total Tests:** 16  
**Status:** All Passing ✓

| Test Class | Tests | Purpose |
|-----------|-------|---------|
| **TestDocumentCreation** | 4 | Document creation, validation, inactive institution handling |
| **TestDocumentVersioning** | 4 | Version immutability, monotonic numbering, hashing, unique keys |
| **TestProcessingStates** | 4 | State machine transitions, invalid state rejection |
| **TestDocumentMetadata** | 1 | Timestamp tracking |
| **TestStorageProvider** | 2 | Local file storage operations and error handling |
| **TestDocumentCategories** | 1 | Category initialization and idempotency |

### 9.2 Test Execution Results

```
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.1.1, pluggy-1.6.0
collected 16 items
tests\test_documents_module.py ................                          [100%]
======================== 16 passed, 1 warning in 0.29s ========================
```

**All tests passing with minimal warnings** (SQLite foreign key cycle warning during teardown is expected and handled).

### 9.3 Test Highlights

1. ✓ Document creation with correct scoping to instrument and institution
2. ✓ Rejection of nonexistent instruments
3. ✓ Rejection of inactive institutions
4. ✓ Invalid category validation
5. ✓ Monotonic version numbering (v1, v2, v3, ...)
6. ✓ SHA-256 integrity hash computation
7. ✓ Unique storage keys per version
8. ✓ Processing state transitions (PENDING_SCAN → CLEAN, INFECTED, etc.)
9. ✓ Invalid processing status rejection
10. ✓ Storage provider file save/read/exist/delete operations
11. ✓ Storage provider error handling (nonexistent key)
12. ✓ Category initialization and idempotency

---

## 10. Integration with Module 1

### 10.1 Reused Components

- **Database Session:** Uses existing SQLAlchemy session management from Module 1
- **Base Models:** `Document`, `DocumentVersion`, `DocumentCategory` inherit from Module 1's `Base` and `TimestampMixin`
- **Audit Service:** Material actions logged via Module 1's `log_audit_event()`
- **Institution & Instrument Models:** Foreign key relationships to Module 1 entities

### 10.2 No Breaking Changes

- Module 1 tables unchanged
- All Module 1 migrations preserved
- Alembic migration chain intact
- Existing tests unaffected (separate test suite for Module 2)

---

## 11. Known Limitations & Design Decisions

### 11.1 Design Decisions (Intentional)

1. **No Automatic Scan Bypass:** New uploads default to PENDING_SCAN. No implicit upgrade to CLEAN without evidence.
2. **No OCR in Foundation:** Document extraction handled by future Module 3 (OCR pipeline).
3. **No Release Logic:** Document readiness/release approval is Modules 3–5 scope.
4. **Storage Abstraction:** Local implementation extensible; S3 can be added without model changes.
5. **Immutable Versions:** Once uploaded, file content cannot be modified; new uploads create new versions.
6. **Audit Trail:** All material actions logged; sensitive metadata sanitized.

### 11.2 Limitations (Future Work)

1. **File Cleanup:** Orphaned files (if database commit fails) not automatically cleaned up; can be handled by periodic maintenance job.
2. **Concurrent Uploads:** Local storage provider doesn't enforce per-document concurrency limits; S3 provider might add versioning.
3. **File Streaming:** Currently loads entire file into memory; for large files (>100MB), streaming upload/download should be implemented.
4. **Storage Quota:** No per-institution or per-instrument storage limits; can be added in future module.
5. **Soft Deletes:** Archives via status flag; no physical deletion of versions (suitable for audit trail requirements).
6. **No Full-Text Search:** Filename and category filters only; full-text search on document content (OCR or indexing) in future module.

---

## 12. Completion Checklist

### ✓ Core Implementation
- [x] Document and DocumentVersion models
- [x] DocumentCategory configurable catalog
- [x] Processing state machine
- [x] Storage abstraction interface
- [x] LocalFileStorageProvider implementation
- [x] DocumentService business logic

### ✓ Data Persistence
- [x] Database migrations (additive, no deletions)
- [x] Indexes for performance
- [x] Foreign key constraints
- [x] Cascade delete rules

### ✓ Audit & Integrity
- [x] SHA-256 integrity hashing
- [x] Audit logging integration
- [x] Timestamp tracking
- [x] Uploader attribution

### ✓ Testing
- [x] 16 automated tests (all passing)
- [x] Document creation and validation
- [x] Version immutability and numbering
- [x] Processing state transitions
- [x] Storage provider operations
- [x] Category management

### ✓ Documentation
- [x] Model definitions and constraints
- [x] Storage abstraction design
- [x] Processing states and transitions
- [x] API schemas (ready for Module 3)
- [x] This completion report

---

## 13. Commands Executed & Results

### 13.1 Environment Setup

```powershell
# Install backend dependencies
pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy alembic psycopg httpx python-dotenv email-validator argon2-cffi pyjwt pytest pytest-asyncio
# Result: All dependencies installed successfully

# Fix pyproject.toml README path issue
# (Removed relative path reference that was causing build errors)
```

### 13.2 Migration

```powershell
# Apply Alembic migrations
alembic upgrade head
# Output:
# INFO  [alembic.runtime.migration] Running upgrade  -> 1a1cd8595579, create_initial_identity_models
# INFO  [alembic.runtime.migration] Running upgrade 1a1cd8595579 -> 058efcf1e144, expand_instrument_registry_fields
# INFO  [alembic.runtime.migration] Running upgrade 058efcf1e144 -> a7b2c4d9e8f5, add_module_2_documents_storage
# Result: All migrations applied successfully (exit code 0)
```

### 13.3 Testing

```powershell
# Run Module 2 tests
pytest tests/test_documents_module.py -v
# Output:
# ======================== 16 passed, 1 warning in 0.29s ========================
# Result: All tests passing (exit code 0)
```

---

## 14. Files Added/Modified

### New Files Created
1. `backend/app/modules/documents/models.py` — Document, DocumentVersion, DocumentCategory SQLAlchemy models
2. `backend/app/modules/documents/schemas.py` — Pydantic schemas for API (DocumentCreateRequest, DocumentRead, etc.)
3. `backend/app/modules/documents/service.py` — DocumentService business logic
4. `backend/app/modules/documents/storage.py` — StorageProvider abstraction and LocalFileStorageProvider
5. `backend/app/modules/documents/__init__.py` — Module exports
6. `backend/alembic/versions/2026_10_24_2350-a7b2c4d9e8f5_add_module_2_documents_storage.py` — Migration
7. `backend/tests/test_documents_module.py` — 16 comprehensive tests

### Files Modified
1. `backend/app/main.py` — Added import for documents models
2. `backend/alembic/env.py` — Added import for documents models
3. `backend/app/common/exceptions.py` — Fixed missing `Any` type import
4. `backend/tests/conftest.py` — Enhanced foreign key handling for SQLite
5. `backend/pyproject.toml` — Removed problematic README path

### Files Preserved
- All Module 1 source code and tests
- All PRD and context documentation
- `.gitignore` (will need update for storage/ directory)

---

## 15. Next Steps for Prompt 2 (Module 3)

**Module 3 — Deterministic Validation & Anomaly Detection Engine** will:
1. Implement document validation rules (required field checks, date logic, amount sufficiency)
2. Build configurable rule engine for policy-based validation
3. Create "discrepancy" records for flagged items
4. Implement officer scrutiny workflow (assign, review, escalate)
5. Upgrade document trust level from L0 → L1 (Document-Consistent) based on passed validation
6. Add `/api/v1/documents/{id}/validate` and `/api/v1/discrepancies` endpoints
7. Build scrutiny officer dashboard and rule configuration UI

---

## 16. Architecture Diagram (High-Level)

```
┌─────────────────────────────────────────────────────────────────┐
│                       Module 2 Foundation                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  API Layer (Module 3+)                                          │
│  ├─ POST /documents                                             │
│  ├─ POST /documents/{id}/versions                               │
│  └─ GET  /documents/{id}                                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  DocumentService (Business Logic)                               │
│  ├─ create_document()                                           │
│  ├─ upload_version()                                            │
│  ├─ update_version_processing_status()                          │
│  └─ initialize_default_categories()                             │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Storage Abstraction Layer                                      │
│  ├─ StorageProvider (interface)                                 │
│  │  ├─ save_file()                                              │
│  │  ├─ read_file()                                              │
│  │  ├─ file_exists()                                            │
│  │  ├─ delete_file()                                            │
│  │  └─ get_metadata()                                           │
│  │                                                              │
│  └─ LocalFileStorageProvider                                    │
│     └─ ./storage/documents/ (UUID-keyed files)                 │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL / SQLite Database                                   │
│  ├─ document_categories (7 initial types)                       │
│  ├─ documents (logical documents)                               │
│  ├─ document_versions (immutable versions)                      │
│  ├─ instruments (Module 1, linked)                              │
│  └─ institutions (Module 1, linked)                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 17. Conclusion

**Module 2 Foundation is Complete.** The Secure Document Intake & Evidence Intelligence layer establishes a robust, extensible foundation for document management:

- ✓ **Immutable versioning** with integrity tracking
- ✓ **Pluggable storage** abstraction (local + extensible)
- ✓ **Explicit processing states** (no silent upgrades)
- ✓ **Audit integration** (all actions logged)
- ✓ **Clean database schema** (additive migrations; backward-compatible)
- ✓ **Comprehensive test coverage** (16 tests, all passing)

**Ready for Prompt 2** (Module 3: Deterministic Validation & Anomaly Detection).
