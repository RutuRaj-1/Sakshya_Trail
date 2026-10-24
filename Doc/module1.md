# FDR Sentinel — Module 1 Specification & Implementation Report
## Identity, Access Control, Institution Registry and User Administration

**Project:** FDR Sentinel (AICTE Security Deposit / FDR Lifecycle Integrity Platform)  
**Problem Statement ID:** 26265  
**Department:** Regulation Bureau, All India Council for Technical Education (AICTE)  
**Stage:** Module 1 (Identity, RBAC, Institution Registry & User Administration)  
**Date:** October 2026  
**Status:** Completed, Fully Tested & Verified (All 37 Backend Tests + 4 Frontend Tests Passing)  

---

## 1. Executive Summary

Module 1 of **FDR Sentinel** establishes the authoritative foundation for identity management, role-based access control (RBAC), the statutory **Institution Registry**, and **User Administration**.

Designed to replace fragmented and error-prone tracking across AICTE regional offices, Module 1 provides:
1. **Statutory Institution Registry API & Service Layer**: Complete lifecycle management (registration, metadata updates, address & contact management, and controlled deactivation/activation) with strict normalization, unique code validation, and historical continuity without physical deletions.
2. **Authoritative Role-Based Access Control (RBAC)**: Fine-grained enforcement covering 7 official application roles with server-side scoping. `INSTITUTION_USER` accounts are strictly scoped to their assigned institution and restricted to updating only verified contact fields.
3. **User Administration & Provisioning**: Secure administrator endpoints for provisioning accounts, role assignments, status management, last-administrator lockout protection, and auditable temporary password generation forcing initial password rotation.
4. **Rich Financial-Regulatory Frontend**: Responsive React 19 interface featuring searchable/filterable Institution lists, an Institution Detail profile with linked FDR instruments placeholder, and an administrator-only User Administration portal.
5. **Tamper-Evident Audit Trail**: Automatic recording of all material actions (institution creation, update, deactivation, user provisioning, password reset initiation) with automatic credential sanitization.
6. **Automated Verification Harness**: 37 automated backend tests (including the 14 Prompt 3 test cases and 14 Prompt 2 test cases) and 4 frontend tests passing cleanly.

All foundational source documents (`Context.md`, `FDR_Sentinel_PRD.md`, `FDR_Sentinel_Project_Synopsis.md`, `FDR_Sentinel_SRS.md`, `FDR_Sentinel_Seven_Module_Prototype_Blueprint.docx`) remain preserved intact.

---

## 2. Institution Registry Architecture

### 2.1 Domain Model (`backend/app/modules/institutions/models.py`)
Built with SQLAlchemy 2.x declarative mapping inheriting `Base` and `TimestampMixin`:

| Field | Type | Description | Constraints |
|---|---|---|---|
| `id` | String(36) | Primary Key (UUIDv4) | Indexed, Not Null |
| `code` | String(50) | AICTE Permanent Institution ID | Unique, Indexed, Normalized (Uppercase), Not Null |
| `legal_name` | String(255) | Official registered legal entity name | Indexed, Trimmed, Min 2 chars, Not Null |
| `display_name` | String(255) | Common operating/campus name | Nullable, Trimmed |
| `institution_type` | String(100) | Regulatory classification taxonomy | Default: `TECHNICAL_INSTITUTE`, Bounded |
| `is_active` | Boolean | Regulatory operating status | Default: `True`, Soft-delete flag |
| `contact_name` | String(255) | Nodal Officer / Registrar | Trimmed, Not Null |
| `contact_email` | String(255) | Official contact email | Validated Email format, Not Null |
| `contact_phone` | String(50) | Official telephone number | Default: `+91-11-29581000` |
| `address_line1` | String(255) | Physical campus street address | Not Null |
| `address_line2` | String(255) | Secondary address / locality | Nullable |
| `city` | String(100) | City / Municipality | Not Null |
| `state` | String(100) | State / Union Territory | Trimmed, Not Null |
| `postal_code` | String(20) | PIN Code | Validated, Not Null |
| `assigned_office` | String(100) | Regional AICTE Bureau Jurisdiction | Nullable (e.g. `Northern Regional Office`) |
| `is_synthetic` | Boolean | Marker for prototype bootstrap records | Default: `False` |
| `created_at` | DateTime(UTC) | Record registration timestamp | Automated |
| `updated_at` | DateTime(UTC) | Last modified timestamp | Automated |

### 2.2 Validation & Lifecycle Rules
1. **Code Normalization & Uniqueness**: Institution codes are trimmed, converted to uppercase, and checked for uniqueness. Duplicate attempts return HTTP 409 Conflict with code `DUPLICATE_INSTITUTION_CODE`.
2. **String Bounds & Sanitization**: Mandatory fields (`legal_name`, `contact_name`, `state`, `postal_code`) are validated to be non-empty after whitespace trimming.
3. **Soft-Delete / Historical Preservation**: Institutions are **never physically deleted** from the database. Deactivating an institution sets `is_active = False` with an auditable administrative reason. Inactive institutions remain retrievable for historical statutory records, audit chains, and past FDR instruments.
4. **Instrument Registration Gate**: Inactive institutions are blocked from registering new security deposit instruments in downstream modules.

---

## 3. Role-Based Access Control (RBAC) & Authorization Matrix

Module 1 enforces the official AICTE Regulation Bureau authorization matrix across backend service and dependency layers:

| Role | Institution Registry Access | User Administration Access | Contact Field Self-Update |
|---|---|---|---|
| `SYSTEM_ADMIN` | **Full**: Create, update all fields, activate/deactivate | **Full**: Provision users, edit profiles, reset passwords, toggle status | Yes |
| `SCRUTINY_OFFICER` | **Read-Only**: Authorized institutions across bureau | None | No |
| `BRANCH_HEAD` | **Read-Only**: Authorized institutions across bureau | None | No |
| `COMPETENT_AUTHORITY` | **Read-Only**: Authorized institutions across bureau | None | No |
| `FINANCE_OFFICER` | **Read-Only**: Authorized institutions across bureau | None | No |
| `AUDITOR` | **Read-Only**: Authorized inspection across all institutions | None | No |
| `INSTITUTION_USER` | **Scoped**: Can read **only their own** institution | None | **Permitted Contact Fields Only** |

### 3.1 Institution User Field Restrictions
An `INSTITUTION_USER` is strictly forbidden from modifying administrative, taxonomic, or security fields.
- **Explicitly Permitted Fields**: `contact_name`, `contact_email`, `contact_phone`, `address_line1`, `address_line2`, `city`, `state`, `postal_code`.
- **Strictly Prohibited Fields**: `code`, `legal_name`, `is_active`, `institution_type`, `assigned_office`, `is_synthetic`. Attempts to alter prohibited fields or access another institution return HTTP 403 Forbidden.

### 3.2 Internal vs. External Account Boundary
- An `INSTITUTION_USER` must be associated with exactly one existing institution ID (`INSTITUTION_ASSOCIATION_REQUIRED`).
- Internal roles (`SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, etc.) cannot be assigned an institution association (`INTERNAL_ROLE_CANNOT_HAVE_INSTITUTION`).

---

## 4. User Administration & Security Safeguards

### 4.1 Last-Administrator Protection (`LAST_ADMIN_PROTECTED`)
To eliminate the risk of accidental administrative lockout:
1. When deactivating a user account (`POST /api/v1/auth/users/{user_id}/status` with `is_active=False`), the service checks the count of active `SYSTEM_ADMIN` accounts.
2. If the target user is the sole remaining active system administrator, the operation is blocked with HTTP 400 Bad Request and error code `LAST_ADMIN_PROTECTED`.
3. When updating a user profile (`PATCH /api/v1/auth/users/{user_id}`), attempting to demote or change the role of the last active administrator is similarly rejected.

### 4.2 Authorized Password Reset Procedure
When an administrator initiates a password reset:
1. Endpoint: `POST /api/v1/auth/users/{user_id}/reset-password`.
2. A high-entropy temporary password (12 characters combining uppercase, lowercase, digits, and symbols) is generated (or explicitly specified).
3. The password is cryptographically hashed with Argon2id and saved.
4. `must_change_password` is set to `True`.
5. An audit event `USER_PASSWORD_RESET_INITIATED` is appended. **Raw passwords and tokens are never logged**.
6. The temporary password is returned in the HTTP response for the administrator to securely communicate. On next login, the user is required to rotate their password before accessing protected application views.

---

## 5. API Endpoints Reference

### 5.1 Institution Registry Endpoints (`/api/v1/institutions`)

| Method | Endpoint | Authorization | Description |
|---|---|---|---|
| `GET` | `/api/v1/institutions` | Authenticated | List visible institutions (search, state, type, is_active filters; paginated). Scoped for `INSTITUTION_USER`. |
| `GET` | `/api/v1/institutions/{id}` | Authenticated | Retrieve one authorized institution. Scoped for `INSTITUTION_USER`. Historical inactive records accessible. |
| `POST` | `/api/v1/institutions` | `SYSTEM_ADMIN` | Register a new institution with unique normalized code validation. |
| `PATCH` | `/api/v1/institutions/{id}` | Authenticated | Update permitted fields. `SYSTEM_ADMIN` can edit all; `INSTITUTION_USER` can edit contact fields only. |
| `POST` | `/api/v1/institutions/{id}/status` | `SYSTEM_ADMIN` | Controlled activation/deactivation with auditable reason. |

### 5.2 User Administration Endpoints (`/api/v1/auth/users`)

| Method | Endpoint | Authorization | Description |
|---|---|---|---|
| `GET` | `/api/v1/auth/users` | `SYSTEM_ADMIN` | List user accounts with search (name, email), role, and status filtering; paginated. |
| `GET` | `/api/v1/auth/users/{id}` | `SYSTEM_ADMIN` or Self | Retrieve an authorized user profile. |
| `POST` | `/api/v1/auth/users` | `SYSTEM_ADMIN` | Provision a new user with role validation and institution scoping. |
| `PATCH` | `/api/v1/auth/users/{id}` | `SYSTEM_ADMIN` | Update permitted user profile fields (role, name, institution) with last-admin guard. |
| `POST` | `/api/v1/auth/users/{id}/status` | `SYSTEM_ADMIN` | Activate or deactivate a user account with last-admin protection. |
| `POST` | `/api/v1/auth/users/{id}/reset-password` | `SYSTEM_ADMIN` | Reset password, generating temporary credentials and setting `must_change_password=True`. |

---

## 6. Frontend Pages & Components

### 6.1 Implemented User Interfaces

1. **Institution Registry List (`InstitutionsPage.tsx` & `InstitutionsList.tsx`)**:
   - Real-time search across institution codes, legal entity names, and operating names.
   - Filter controls for operating status (`Active`, `Inactive/Historical`) and classification taxonomies (`Technical Institute`, `Pharmacy`, `Polytechnic`, etc.).
   - Role-aware UI: "Register Institution" button and edit/status controls visible only to `SYSTEM_ADMIN`.
   - Distinctive status badges (`ACTIVE` in emerald, `INACTIVE` in slate).
   - Server-side pagination controls (offset and page size).

2. **Institution Create & Edit Modal (`InstitutionModal.tsx`)**:
   - Comprehensive form with field bounds, format checks, and client-side validation.
   - Distinct operational modes: Full admin creation/editing vs. Institution User nodal contact editing.
   - Duplicate code error feedback with field-level highlighting.
   - Double-submission protection with interactive loading spinner.

3. **Institution Detail Profile (`InstitutionDetailPage.tsx`)**:
   - High-density institutional profile showing permanent identifiers, legal and display names, classification, and regional office assignment.
   - Verified contact card with direct links, phone numbers, and physical addresses.
   - Audit timestamps (`created_at`, `updated_at`).
   - Dedicated placeholder section for linked statutory FDR instruments (scheduled for full lifecycle integration in Module 2 / Prompt 4).
   - Administrative action buttons for editing and status deactivation/reactivation.

4. **User Administration Portal (`UserAdminPage.tsx`)**:
   - Restricted exclusively to `SYSTEM_ADMIN` via `ProtectedRoute allowedRoles={['SYSTEM_ADMIN']}` and navigation gating.
   - Searchable table displaying user full name, email, role badge, institution association, active status, and password rotation state.
   - Account Provisioning modal with dynamic institution dropdown for `INSTITUTION_USER`.
   - Administrative password reset modal displaying high-entropy temporary passwords with one-click copy and clear policy warnings.
   - Account status toggle with last-administrator protection handling.

5. **Navigation Shell (`Sidebar.tsx` & `router.tsx`)**:
   - Dynamically renders "User Admin" navigation link for `SYSTEM_ADMIN` accounts.
   - Integrated routes for `/institutions`, `/institutions/:id`, and `/users`.

---

## 7. Audit Logging & Credential Sanitization

Every material operation generates an immutable `AuditEvent`:
- Actions: `INSTITUTION_CREATED`, `INSTITUTION_UPDATED`, `INSTITUTION_ACTIVATED`, `INSTITUTION_DEACTIVATED`, `USER_PROVISIONED`, `USER_PROFILE_UPDATED`, `USER_ACTIVATED`, `USER_DEACTIVATED`, `USER_PASSWORD_RESET_INITIATED`, `AUTH_LOGIN`, `AUTH_LOGOUT`, `AUTH_PASSWORD_CHANGED`.
- Actor attribution: `actor_user_id`, `actor_email`, `actor_role`, `request_id`, client IP address.
- **Strict Credential Sanitization**: `sanitize_dict` permanently strips keys matching `password`, `token`, `secret`, `access_token`, `authorization`, or replaces them with `[REDACTED]`. Plaintext secrets or password hashes are never persisted to audit trails.

---

## 8. Automated Test Results

The unified test runner (`scripts/test.ps1`) executes both the backend Pytest suite and the frontend Vitest suite.

### 8.1 Backend Pytest Execution (37 Passed, 0 Failed)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\bhome\OneDrive\Desktop\VIT\SIH\SIH 2026\TOP 75\FDR_Sentinel\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0

backend/tests/test_auth_rbac.py ..............                           [ 37%]
backend/tests/test_health.py .....                                       [ 51%]
backend/tests/test_institutions_users.py ..............                  [ 89%]
backend/tests/test_modules.py ....                                       [100%]

======================= 37 passed, 2 warnings in 3.34s ========================
```

### 8.2 Prompt 3 Verification Matrix (14 / 14 Required Tests Verified)
1. `test_create_institution_success`: Creating an institution with full attributes.
2. `test_duplicate_institution_code_rejection`: Case-insensitive duplicate code rejection returning 409 `DUPLICATE_INSTITUTION_CODE`.
3. `test_invalid_fields_validation`: Empty strings, invalid email, and missing fields return 422.
4. `test_update_and_deactivate_institution`: Updating permitted fields and setting `is_active=False`.
5. `test_historical_institution_retrieval_after_deactivation`: Inactive institutions remain retrievable by ID and in filtered queries.
6. `test_admin_only_institution_creation`: Non-admin roles (e.g. `SCRUTINY_OFFICER`) get 403 Forbidden on institution creation.
7. `test_institution_user_reads_own_institution`: Institution user reads their own institution record.
8. `test_institution_user_denied_other_institution`: Institution user receives 403 when attempting to access another institution.
9. `test_institution_user_denied_administrative_modifications`: Institution user permitted to update contact info, but denied changes to code, name, or status.
10. `test_user_provisioning_valid_and_invalid_roles`: Provisioning with valid role succeeds; invalid roles return 400 `INVALID_ROLE`.
11. `test_required_institution_association_for_institution_users`: Institution user without institution is rejected with 400 `INSTITUTION_ASSOCIATION_REQUIRED`.
12. `test_auditor_read_only_enforcement`: Auditor can read institutions but is blocked with 403 on create, update, or deactivate attempts.
13. `test_last_administrator_protection`: Deactivation or role demotion of the sole active administrator is blocked with 400 `LAST_ADMIN_PROTECTED`.
14. `test_audit_creation_for_material_actions`: Audit records created for all actions without credential leaks.

### 8.3 Frontend Vitest Execution (4 Passed, 0 Failed)
```text
 ✓ src/app/__tests__/App.test.tsx (4 tests) 153ms
 Test Files: 1 passed (1) | Tests: 4 passed (4)
```

### 8.4 Production Build Verification
`npm run build` executed in `frontend/`:
```text
vite v8.3.5 building client environment for production...
✓ 1970 modules transformed.
dist/index.html                   1.05 kB │ gzip:   0.58 kB
dist/assets/index-INeaCZ4n.css   42.13 kB │ gzip:   7.86 kB
dist/assets/index-CH9F70s9.js   458.10 kB │ gzip: 131.89 kB
✓ built in 539ms (Zero TypeScript or Linting Errors)
```

---

## 9. Known Limitations & Extensibility Points

1. **Regional Office Scoping**: Assigned offices (e.g., `Northern Regional Office`, `Western Regional Office`) are recorded as text attributes on institutions. Branch Head scoping is currently global across registered institutions; fine-grained regional boundaries can be configured in future regulatory rules without schema alteration.
2. **Email Delivery Provider**: Automated SMTP / transactional email delivery is not yet connected. Password resets generate a secure temporary password displayed directly to the authorized administrator for secure out-of-band communication, with enforced rotation on next login.
3. **Linked FDR Instruments**: The linked instruments section on the Institution Detail page displays a structured placeholder; full multi-party deposit instruments will be linked in Module 2 (Prompt 4).
