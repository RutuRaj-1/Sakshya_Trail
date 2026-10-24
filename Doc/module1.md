# FDR Sentinel — Module 1 Specification & Implementation Report
## Identity, Access Control, Institution Registry, User Administration & FDR Instrument Registry

**Project:** FDR Sentinel (AICTE Security Deposit / FDR Lifecycle Integrity Platform)  
**Problem Statement ID:** 26265  
**Department:** Regulation Bureau, All India Council for Technical Education (AICTE)  
**Stage:** Module 1 Complete (Identity, RBAC, Institution Registry, User Administration & FDR Instrument Registry)  
**Date:** October 2026  
**Status:** Completed, Fully Tested & Verified (All 49 Backend Tests + 4 Frontend Tests Passing, Clean Production Build)  

---

## 1. Executive Summary

Module 1 of **FDR Sentinel** establishes the authoritative foundation for identity management, role-based access control (RBAC), the statutory **Institution Registry**, **User Administration**, and the core **FDR / Instrument Registry**.

Designed to replace fragmented, error-prone manual spreadsheets and physical deposit files across AICTE regional offices, Module 1 provides:
1. **Authoritative Role-Based Access Control (RBAC)**: Fine-grained enforcement covering 7 official application roles with server-side record scoping. `INSTITUTION_USER` accounts are strictly scoped to their assigned institution.
2. **Statutory Institution Registry API & Service Layer**: Complete lifecycle management (registration, metadata updates, address & contact management, controlled deactivation/activation) with strict normalization, unique code validation, and historical continuity without physical deletions.
3. **User Administration & Provisioning**: Secure administrator endpoints for provisioning accounts, role assignments, status management, last-administrator lockout protection, and auditable temporary password generation.
4. **Authoritative FDR / Instrument Registry**: Full lifecycle management of statutory Fixed Deposit Receipts (FDRs) with UUID primary key, enforced institution foreign-key relationship, decimal monetary precision (`Numeric(18, 2)`), and strict server-side validation.
5. **Architectural Separation of Three Core Concepts**:
   - **Administrative Workflow Status**: Initial registry state (`DRAFT`, `REGISTERED`).
   - **Trust Level**: Tiered confidence model (`L0 — DECLARED`, `L1 — DOCUMENT_CONSISTENT`, `L2 — OFFICER_VERIFIED`, `L3 — BANK_CONFIRMED`). New instruments start at `L0 — DECLARED` and cannot be escalated through registry endpoints.
   - **Derived Maturity Indicator**: Read-only timeline indicator (`ACTIVE`, `EXPIRING_SOON` within 90 days, `EXPIRED`).
6. **Conservative Duplicate-Reference Warning Path**: Intelligent case-insensitive bank name and reference comparison returning structured warning details without silently merging records or preventing review. Authorized users can override only through an explicit `confirm_duplicate: true` parameter, producing a full audit trail.
7. **Rich Financial-Regulatory Frontend**: Responsive React 19 interface featuring searchable/filterable Instrument lists, reference masking toggles, dual-badge administrative/trust displays, duplicate warning modal flow, comprehensive instrument detail profile with clearly demarcated "Future Module" placeholders, and real linked instruments within institution profiles.
8. **Tamper-Evident Audit Trail**: Automatic recording of all material actions (creation, updates, duplicate overrides, deactivations, credential events) with automatic sanitization of sensitive values.
9. **Automated Verification Harness**: 49 automated backend tests and 4 frontend tests passing cleanly.

All foundational source documents (`Context.md`, `FDR_Sentinel_PRD.md`, `FDR_Sentinel_Project_Synopsis.md`, `FDR_Sentinel_SRS.md`, `FDR_Sentinel_Seven_Module_Prototype_Blueprint.docx`) remain preserved intact.

---

## 2. FDR / Instrument Registry Architecture

### 2.1 Domain Model (`backend/app/modules/instruments/models.py`)
Built with SQLAlchemy 2.x declarative mapping inheriting `Base` and `TimestampMixin`:

| Field | Type | Description | Constraints |
|---|---|---|---|
| `id` | String(36) | Primary Key (UUIDv4) | Indexed, Not Null |
| `institution_id` | String(36) | Parent Institution Foreign Key | FK to `institutions.id`, Indexed, Not Null |
| `instrument_type` | String(50) | Instrument classification taxonomy | Default: `FDR` (prototype primary) |
| `bank_name` | String(255) | Issuing Bank Name | Trimmed, Min 2 chars, Indexed, Not Null |
| `bank_branch` | String(255) | Issuing Bank Branch / Location | Nullable, Trimmed |
| `reference_number` | String(100) | FDR / Receipt Reference Number | Indexed (Non-unique in DB), Normalized, Not Null |
| `amount` | Numeric(18, 2) | Exact Deposit Amount | High-precision decimal, > 0, Never Float |
| `currency` | String(10) | Currency Denomination | Default: `INR`, Upper-case |
| `issue_date` | Date | Instrument Effective Issue Date | Not Null |
| `maturity_date` | Date | Instrument Maturity Date | `maturity_date > issue_date`, Not Null |
| `lien_holder` | String(255) | Designated Lien / Pledge Beneficiary | Nullable (e.g. `AICTE / Regional Office`) |
| `lien_details` | Text | Pledge terms, remarks, endorsement | Nullable |
| `assigned_office` | String(100) | Regional Jurisdiction Office | Nullable |
| `status` | String(50) | Administrative Workflow Status | Default: `REGISTERED` (`DRAFT`, `REGISTERED`) |
| `trust_level` | String(50) | Verification Confidence Tier | Default: `L0_DECLARED`, Registry locked |
| `is_synthetic` | Boolean | Marker for demo/bootstrap records | Default: `False` |
| `created_by_user_id` | String(36) | Registration Author Identifier | FK to `users.id`, Nullable |
| `updated_by_user_id` | String(36) | Last Modification Author | FK to `users.id`, Nullable |
| `created_at` | DateTime(UTC) | Instrument Registration Timestamp | Automated |
| `updated_at` | DateTime(UTC) | Last Modified Timestamp | Automated |

### 2.2 Strict Separation of Three Core Concepts

The API and UI deliberately avoid collapsing different business states into a single generic status:

1. **Administrative Status (`status`)**:
   - Represents the instrument's operational workflow lifecycle state.
   - Initial supported registry values: `DRAFT` and `REGISTERED`.
   - Downstream verification and release lifecycle stages belong to future modules.
2. **Trust Level (`trust_level`)**:
   - Distinct confidence tier representing authentication rigor:
     - `L0 — DECLARED`: Self-reported by institution or imported baseline.
     - `L1 — DOCUMENT_CONSISTENT`: Document metadata and OCR consistency validated (Module 2).
     - `L2 — OFFICER_VERIFIED`: Authorized Scrutiny Officer manual verification with evidence (Module 3).
     - `L3 — BANK_CONFIRMED`: Official bank direct API or signed confirmation (Module 4).
   - **Enforcement**: Newly created instruments always initialize to `L0_DECLARED`. Ordinary create and update endpoints strictly reject arbitrary trust-level escalations.
3. **Maturity Indicator (`maturity_indicator`)**:
   - Derived, read-only operational state computed server-side:
     - `ACTIVE`: `maturity_date - today > 90 days`.
     - `EXPIRING_SOON`: `0 <= maturity_date - today <= 90 days` (Provisional regulatory notice window).
     - `EXPIRED`: `maturity_date < today`.
   - Never conflated with administrative status or trust level.

---

## 3. Conservative Duplicate-Reference Warning Path

To handle real-world scenarios where institutions mistakenly submit duplicates or re-pledge existing receipts, the system implements a conservative duplicate-warning path:

### 3.1 Detection Algorithm
- When a new instrument is submitted (or bank/reference updated), the system searches for existing instruments matching:
  - `lower(trim(bank_name)) == lower(trim(incoming_bank_name))`
  - `lower(trim(reference_number)) == lower(trim(incoming_reference_number))`
- Non-unique database index: A global unique database constraint is **not** enforced, ensuring potential duplicates are not lost and can be recorded for scrutiny.

### 3.2 Structured Warning Interception
1. If matches are found and the request does **not** specify `confirm_duplicate: true`:
   - Returns HTTP 409 Conflict with error code `DUPLICATE_REFERENCE_WARNING`.
   - Payload includes structured `details` array containing:
     - `matching_instruments`: List of matched instruments with ID, bank, reference, amount, issue/maturity dates, and institution name/code.
     - `warning`: Clear, non-accusatory warning message explaining that matching records exist and require explicit authorized confirmation.
   - The system **never falsely accuses the user of fraud or forgery**, nor does it silently merge or overwrite records.
2. If the user inspects the matches and explicitly submits with `confirm_duplicate: true`:
   - Registration proceeds safely as an independent record.
   - An immutable audit entry `INSTRUMENT_CREATED` is persisted with metadata `duplicate_warning_overridden: true` and matched IDs for forensic scrutiny.

---

## 4. Role-Based Access Control (RBAC) & Permission Matrix

Module 1 applies record-scoped authorization across every registry endpoint:

| Role | Instrument Registry Access | Create Instruments | Edit Permitted Fields | Trust Level Escalation |
|---|---|---|---|---|
| `SYSTEM_ADMIN` | Full Bureau Access | Yes (for any active institution) | Permitted fields only | **Denied** (Audit gate) |
| `SCRUTINY_OFFICER` | Full Bureau Access | Yes | Permitted registry corrections | **Denied** (Requires Mod 3 workflow) |
| `BRANCH_HEAD` | Bureau / Regional Read-Only | Denied | Denied | Denied |
| `COMPETENT_AUTHORITY`| Read-Only Inspection | Denied | Denied | Denied |
| `FINANCE_OFFICER` | Read-Only Inspection | Denied | Denied | Denied |
| `AUDITOR` | Read-Only Inspection | Denied | Denied | Denied |
| `INSTITUTION_USER` | **Scoped to own institution only** | Yes (own institution only) | Permitted fields (own draft/registered) | **Denied** |

### 4.1 Security Constraints
1. **Ownership Enforcement**: `INSTITUTION_USER` accounts can never access, query, or edit instruments belonging to another institution.
2. **Immutable Institution Linkage**: Clients cannot change an instrument's parent `institution_id` via update requests.
3. **No Physical Deletions**: Financial records cannot be deleted. Future cancellation or release transitions are handled via status and reason tracking.
4. **Active Institution Gate**: New instruments cannot be created under inactive institutions.

---

## 5. API Endpoints Reference

### 5.1 Instrument Registry Endpoints (`/api/v1/instruments`)

| Method | Endpoint | Authorization | Description |
|---|---|---|---|
| `GET` | `/api/v1/instruments` | Authenticated | List instruments with search (bank, reference, institution), filters (`institution_id`, `status`, `trust_level`, `maturity_indicator`, date range), allow-listed sorting, and pagination. Scoped for `INSTITUTION_USER`. |
| `GET` | `/api/v1/instruments/{id}` | Authenticated | Retrieve complete instrument record with parent institution details and derived maturity state. Scoped for `INSTITUTION_USER`. |
| `POST` | `/api/v1/instruments` | Authenticated | Register new instrument. Scoped to caller's institution for `INSTITUTION_USER`. Intercepts duplicates with 409 unless `confirm_duplicate: true`. Initializes at `L0_DECLARED`. |
| `PATCH` | `/api/v1/instruments/{id}` | Authenticated | Update permitted fields (`bank_branch`, `amount`, `maturity_date`, `lien_holder`, `lien_details`). Strictly blocks `institution_id` or `trust_level` alterations. |
| `GET` | `/api/v1/instruments/summary` | Authenticated | Aggregated KPI metrics: total count, total deposit value (decimal sum), active count, expiring soon count, and trust tier distribution. Scoped for `INSTITUTION_USER`. |

### 5.2 Institution Registry Endpoints (`/api/v1/institutions`)

| Method | Endpoint | Authorization | Description |
|---|---|---|---|
| `GET` | `/api/v1/institutions` | Authenticated | List visible institutions (search, state, type, is_active filters; paginated). Scoped for `INSTITUTION_USER`. |
| `GET` | `/api/v1/institutions/{id}` | Authenticated | Retrieve one authorized institution. Scoped for `INSTITUTION_USER`. Historical inactive records accessible. |
| `POST` | `/api/v1/institutions` | `SYSTEM_ADMIN` | Register a new institution with unique normalized code validation. |
| `PATCH` | `/api/v1/institutions/{id}` | Authenticated | Update permitted fields. `SYSTEM_ADMIN` can edit all; `INSTITUTION_USER` can edit contact fields only. |
| `POST` | `/api/v1/institutions/{id}/status` | `SYSTEM_ADMIN` | Controlled activation/deactivation with auditable reason. |

### 5.3 User Administration Endpoints (`/api/v1/auth/users`)

| Method | Endpoint | Authorization | Description |
|---|---|---|---|
| `GET` | `/api/v1/auth/users` | `SYSTEM_ADMIN` | List user accounts with search, role, and status filtering; paginated. |
| `GET` | `/api/v1/auth/users/{id}` | `SYSTEM_ADMIN` or Self | Retrieve an authorized user profile. |
| `POST` | `/api/v1/auth/users` | `SYSTEM_ADMIN` | Provision a new user with role validation and institution scoping. |
| `PATCH` | `/api/v1/auth/users/{id}` | `SYSTEM_ADMIN` | Update permitted user profile fields with last-admin guard. |
| `POST` | `/api/v1/auth/users/{id}/status` | `SYSTEM_ADMIN` | Activate or deactivate a user account with last-admin protection. |
| `POST` | `/api/v1/auth/users/{id}/reset-password` | `SYSTEM_ADMIN` | Reset password, generating temporary credentials and setting `must_change_password=True`. |

---

## 6. Frontend Pages & Components

### 6.1 Implemented User Interfaces

1. **Instrument Registry List (`InstrumentsPage.tsx` & `InstrumentsList.tsx`)**:
   - Search across bank name, reference number, and institution legal name/code.
   - Filter dropdowns for Administrative Status, Trust Tier (`L0` to `L3`), and Maturity Window (`Active`, `Expiring Soon`, `Expired`).
   - KPI metrics strip displaying Total Held Value (formatted in INR), Active Deposits, Expiring Soon, and L0 Unverified count.
   - Reference masking toggle (e.g. `•••••• 7890`) for privacy in public bureau displays.
   - Separate status and trust badges.
   - Server-side pagination controls (offset and page size).

2. **Instrument Registration Modal (`InstrumentModal.tsx`)**:
   - Selects institution strictly within caller's allowed scope (disabled and fixed for `INSTITUTION_USER`).
   - Server & client side input validation for bank name, reference number, decimal amount, and issue/maturity dates (`maturity_date > issue_date`).
   - Clearly marked default badge: `L0 — DECLARED`.
   - **Conservative Duplicate Warning Flow**: Intercepts 409 responses, displays warning dialog with details of existing matching records, and provides an explicit "Confirm & Register Anyway" button to proceed with `confirm_duplicate: true`.

3. **Instrument Detail Profile (`InstrumentDetailPage.tsx`)**:
   - Complete statutory profile with linked institution card, financial terms, and lien details.
   - Independent display of Administrative Status, Trust Level, and Derived Maturity Indicator.
   - Audit metadata: creation and update timestamps with actor attribution.
   - **Future Module Placeholders**: Clearly labelled placeholder panels for:
     - *Document Evidence & OCR Extraction* (Scheduled for Module 2).
     - *Scrutiny Verification & Defect Log* (Scheduled for Module 3).
     - *Direct Bank Confirmation* (Scheduled for Module 4).
     - *Renewal & Release Lineage* (Scheduled for Module 5).

4. **Institution Detail Profile (`InstitutionDetailPage.tsx`)**:
   - High-density institutional profile showing permanent identifiers, classification, and contact info.
   - Real-time connected table of linked FDR security deposit instruments with amounts and maturity indicators.

5. **User Administration Portal (`UserAdminPage.tsx`)**:
   - Provisioning, role assignment, status toggling with last-administrator protection, and password reset flows.

---

## 7. Database Migrations

Database schema versioning managed via Alembic:

| Revision ID | Description | Changes Applied |
|---|---|---|
| `2026_10_24_1720-639fe1012ab9` | Initial core tables | `users`, `institutions`, `instruments`, `audit_events` |
| `2026_10_24_2120-e3745348bbab` | Institution registry expansion | Extended contact fields, classification types, regional offices |
| `2026_10_24_2246-058efcf1e144` | FDR Instrument registry expansion | Added `instrument_type`, `lien_holder`, `lien_details`, `assigned_office`, `created_by_user_id`, `updated_by_user_id`, removed unique constraint on `reference_number` for duplicate review support |

Current database state: `058efcf1e144 (head)` applied cleanly.

---

## 8. Automated Test Results

The unified test runner (`scripts/test.ps1`) executes both the backend Pytest suite and the frontend Vitest suite.

### 8.1 Backend Pytest Execution (49 Passed, 0 Failed)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\bhome\OneDrive\Desktop\VIT\SIH\SIH 2026\TOP 75\FDR_Sentinel\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0

backend/tests/test_auth_rbac.py ..............                           [ 28%]
backend/tests/test_health.py .....                                       [ 38%]
backend/tests/test_institutions_users.py ..............                  [ 67%]
backend/tests/test_instruments_registry.py ............                  [ 91%]
backend/tests/test_modules.py ....                                       [100%]

======================= 49 passed, 4 warnings in 3.60s ========================
```

### 8.2 Prompt 4 Verification Matrix (12 / 12 Required Tests Verified)
1. `test_instrument_creation`: Successful creation of FDR instrument with UUID PK, institution FK, and initial `L0_DECLARED` trust level.
2. `test_amount_and_date_validation`: Rejection of zero/negative amounts, missing bank/reference, and maturity dates earlier than issue dates.
3. `test_unknown_or_inactive_institution_rejection`: Registration blocked when target institution is non-existent or inactive.
4. `test_institution_user_ownership_scoping`: Institution users only see instruments belonging to their own institution.
5. `test_cross_institution_reads_and_edits_denied`: Cross-institution read and edit attempts rejected with 403 Forbidden.
6. `test_trust_level_escalation_denied`: Attempts to upgrade trust level from `L0_DECLARED` to `L1`/`L2`/`L3` rejected by schema and endpoint validation.
7. `test_unsupported_administrative_status_transitions_denied`: Attempts to set invalid administrative status values rejected.
8. `test_duplicate_bank_reference_warning`: Initial duplicate bank/reference returns 409 with structured warning and matching records.
9. `test_duplicate_detection_not_silently_merging`: Overriding duplicate warning with `confirm_duplicate: true` creates a distinct new record without merging or corrupting existing records.
10. `test_pagination_search_and_filters`: Filtering by bank, reference, status, trust level, maturity indicator, and search terms with accurate pagination.
11. `test_decimal_monetary_precision`: Decimal monetary amounts preserved with exact cents/paise precision (`12500000.75`).
12. `test_authorization_and_audit_coverage`: Verification that creation and updates generate structured audit events without sensitive leaks.

### 8.3 Frontend Vitest Execution (4 Passed, 0 Failed)
```text
 ✓ src/app/__tests__/App.test.tsx (4 tests) 148ms
 Test Files: 1 passed (1) | Tests: 4 passed (4)
```

### 8.4 Production Build Verification
`npm run build` executed in `frontend/`:
```text
vite v8.3.5 building client environment for production...
✓ 1972 modules transformed.
dist/index.html                   1.05 kB │ gzip:   0.58 kB
dist/assets/index-hf1XpnKl.css   43.96 kB │ gzip:   8.14 kB
dist/assets/index-DarYn8k8.js   500.71 kB │ gzip: 139.36 kB
✓ built in 470ms (Zero TypeScript or Linting Errors)
```

---

## 9. Known Limitations & Extensibility Points

1. **Document Evidence & OCR Ingestion**: Handled in **Module 2 (Document Ingestion & Multi-OCR Pipeline)**. Instruments currently store metadata; PDF deposit receipts and OCR confidence scores will link directly into `instrument_id`.
2. **Scrutiny Verification & Trust Escalation**: Handled in **Module 3 (Deterministic Validation & Anomaly Detection Engine)** and Verification Workflow. Promotion to `L1` (Document Consistent) and `L2` (Officer Verified) requires formal verification workflows.
3. **Direct Bank Confirmation**: Handled in **Module 4 (Official Bank Confirmation Gateway)**. Direct API or SFTP confirmation will establish `L3` trust tier.
4. **Renewal and Release Workflows**: Handled in **Module 5 (Lien Tracking, Renewal Workflows & Release Governance)**.
