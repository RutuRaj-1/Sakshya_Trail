# FDR Sentinel — Module 1 Specification & Implementation Report
## Identity, RBAC, Institution Registry, Instrument Registry, Integration & Acceptance Verification

**Project:** FDR Sentinel (AICTE Security Deposit / FDR Lifecycle Integrity Platform)  
**Problem Statement ID:** 26265  
**Department:** Regulation Bureau, All India Council for Technical Education (AICTE)  
**Stage:** Module 1 Complete (Integration, Security, Testing & Handover)  
**Date:** October 2026  
**Status:** Completed, Fully Tested & Verified (All 67 Backend Tests + 4 Frontend Tests Passing, Clean Production Build)  

---

## 1. Executive Summary

Module 1 of **FDR Sentinel** establishes the authoritative foundation for identity management, role-based access control (RBAC), the statutory **Institution Registry**, **User Administration**, the core **FDR / Instrument Registry**, and the **Scoped Executive Dashboard**.

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
7. **Module 1 Scoped Dashboard**: Centralized operational summary endpoint (`/api/v1/dashboard/summary`) dynamically returning active/inactive institutions, draft/registered instruments, trust level distribution, 90-day approaching maturities, and total monetary deposits strictly respecting caller permissions and tenant isolation.
8. **Tamper-Evident Audit Trail**: Automatic recording of all material actions (creation, updates, duplicate overrides, deactivations, credential events) with automatic sanitization of sensitive values.
9. **Automated Verification Harness**: 67 automated backend tests (including the 18 dedicated acceptance tests M1-AC-01 through M1-AC-18) and 4 frontend tests passing cleanly.

All foundational source documents (`Context.md`, `FDR_Sentinel_PRD.md`, `FDR_Sentinel_Project_Synopsis.md`, `FDR_Sentinel_SRS.md`, `FDR_Sentinel_Seven_Module_Prototype_Blueprint.docx`) remain preserved intact.

---

## 2. End-to-End Workflow Verification

### Workflow A — Initial Administrator Setup
1. **Startup & Schema Initialization**: Application boots cleanly with SQLite (`backend/fdr_sentinel.db`) or PostgreSQL. Alembic migrations apply automatically to head (`058efcf1e144`).
2. **Secure CLI Bootstrap**: First administrator is provisioned via `python scripts/bootstrap_admin.py --email admin@aicte-india.org --name "AICTE Master Admin"`, interactively prompting for a secure 8+ character password.
3. **Frontend Authentication**: User logs in through the React frontend via `/api/v1/auth/login`. On authentication, signed JWT session cookie (`HttpOnly`, `SameSite=Lax`) is issued.
4. **Route Protection**: Protected views (`/`, `/institutions`, `/instruments`, `/users`, `/audit`) strictly require an active authenticated session; unauthenticated attempts redirect to `/login`.
5. **Session Termination**: Logging out invokes `/api/v1/auth/logout`, clearing the cookie on the server and clearing client credentials.

### Workflow B — Institution Management
1. **Creation**: Administrator registers an institution with legal name, AICTE permanent ID code, operating name, classification, and contact details via `POST /api/v1/institutions`.
2. **Permitted Edits**: Administrator edits fields via `PATCH /api/v1/institutions/{id}`.
3. **Duplicate Code Rejection**: Submitting an existing code returns HTTP 409 Conflict with code `DUPLICATE_INSTITUTION_CODE`.
4. **Non-Destructive Deactivation**: Calling `POST /api/v1/institutions/{id}/status` with `is_active=False` preserves all historical audit trails, linked FDRs, and user accounts without physical deletions.
5. **RBAC Isolation**: Non-admin roles (e.g. `SCRUTINY_OFFICER`, `AUDITOR`, `INSTITUTION_USER`) cannot perform administrative modifications.

### Workflow C — Institution User Provisioning & Isolation
1. **Provisioning**: Administrator provisions an `INSTITUTION_USER` associated with one institution ID via `POST /api/v1/auth/users`.
2. **Enforced Password Rotation**: User account is flagged with `must_change_password=True`. On initial login, the user is redirected to `/change-password` before accessing dashboard views.
3. **Tenant Scoping**: Institution users see only their own institution and only their institution's FDR instruments.
4. **Cross-Tenant Blockade**: Attempting to read or edit another institution via URL parameter, query filter, or payload returns HTTP 403 Forbidden.
5. **Privilege Tampering Protection**: Institution users cannot change their role, assign themselves an administrator status, or provision user accounts.

### Workflow D — Instrument Registration
1. **FDR Registration**: Institution user creates an FDR record for their institution.
2. **Server-Side Validation**: Negative or zero amounts, blank bank names, missing reference numbers, or maturity dates preceding issue dates return HTTP 422 Unprocessable Content.
3. **Evidentiary Baseline**: Newly registered instruments are strictly initialized at `trust_level="L0_DECLARED"`.
4. **Instrument Detail Profile**: Displays issuing bank, branch location, reference number, exact decimal amount in INR, issue/maturity dates, and derived maturity indicator.
5. **Immutable Linkage & Trust Lock**: Patching an instrument cannot alter its parent `institution_id` or elevate its `trust_level`.
6. **Conservative Duplicate Warning**: Existing bank and reference matches return HTTP 409 Conflict with details of matched records. An explicit `confirm_duplicate: true` creates an independent record and logs an auditable override.
7. **Cross-Institution Inspection**: Authorized scrutiny officers and branch heads can view permitted bureau-wide records.
8. **Auditor Read-Only Enforcement**: Auditors can inspect all records and audit events, but cannot create or modify data.

### Workflow E — Auditability
1. **Material Action Coverage**: Immutable audit events are recorded for `INSTITUTION_CREATED`, `INSTITUTION_UPDATED`, `INSTITUTION_DEACTIVATED`, `USER_PROVISIONED`, `USER_STATUS_UPDATED`, `INSTRUMENT_CREATED`, and `AUTH_LOGIN`.
2. **Actor Attribution**: Every entry records `actor_user_id`, `actor_email`, `actor_role`, `action`, `entity_type`, `entity_id`, IP address, and UTC timestamp.
3. **Credential Sanitization**: The recursive sanitization engine permanently strips passwords, tokens, and authorization headers (`[REDACTED]`).
4. **Ledger Immutability**: No API endpoints exist to update or delete audit events.

---

## 3. Scoped Executive Dashboard (`/api/v1/dashboard/summary`)

Provides live metrics derived directly from real database queries:
- **`total_active_institutions`**: Total active technical institutions within caller scope.
- **`total_inactive_institutions`**: Total historical/inactive institutions within caller scope.
- **`total_instruments`**: Total registered deposit instruments within caller scope.
- **`total_deposit_value`**: High-precision decimal monetary sum of deposits.
- **`instruments_by_status`**: Count grouped by administrative status (`DRAFT`, `REGISTERED`).
- **`instruments_by_trust_level`**: Count grouped by evidentiary trust tier (`L0_DECLARED`, `L1_DOCUMENT_CONSISTENT`, `L2_OFFICER_VERIFIED`, `L3_BANK_CONFIRMED`).
- **`instruments_approaching_maturity`**: Count of instruments maturing within the 90-day provisional warning window (`0 <= maturity_date - today <= 90 days`).

**Tenant Scope Enforcement**:
- `INSTITUTION_USER` accounts receive counts computed strictly for their assigned institution ID.
- Bureau administrative roles receive bureau-wide aggregated counts.

---

## 4. Acceptance Criteria Verification Matrix (M1-AC-01 through M1-AC-18)

| ID | Acceptance Criterion | Test Implementation (`test_module1_acceptance.py`) | Status |
|---|---|---|---|
| **M1-AC-01** | Clean environment starts application and initializes database | `test_m1_ac_01_clean_environment_db_init` | **PASS** |
| **M1-AC-02** | Administrator can be securely bootstrapped and log in | `test_m1_ac_02_admin_bootstrap_and_login` | **PASS** |
| **M1-AC-03** | Unauthenticated requests to protected endpoints are rejected | `test_m1_ac_03_unauthenticated_requests_rejected` | **PASS** |
| **M1-AC-04** | Authorized administrators can create and manage institutions | `test_m1_ac_04_admin_create_manage_institutions` | **PASS** |
| **M1-AC-05** | Duplicate institution codes cannot be created | `test_m1_ac_05_duplicate_institution_code_rejected` | **PASS** |
| **M1-AC-06** | Administrators can provision users with valid roles and institutions | `test_m1_ac_06_admin_provision_users` | **PASS** |
| **M1-AC-07** | Institution users cannot access another institution's records | `test_m1_ac_07_institution_user_tenant_isolation` | **PASS** |
| **M1-AC-08** | Institution users cannot change own role or institution assignment | `test_m1_ac_08_institution_user_cannot_elevate_privileges` | **PASS** |
| **M1-AC-09** | Authorized users can register and view FDR records | `test_m1_ac_09_register_and_view_fdr` | **PASS** |
| **M1-AC-10** | Amount and date validation works on the backend | `test_m1_ac_10_amount_and_date_validation` | **PASS** |
| **M1-AC-11** | Every new instrument starts at `L0 — DECLARED` | `test_m1_ac_11_new_instrument_starts_at_l0` | **PASS** |
| **M1-AC-12** | Ordinary instrument edits cannot elevate the trust level | `test_m1_ac_12_instrument_patch_cannot_escalate_trust` | **PASS** |
| **M1-AC-13** | Potential duplicates are warned about and never silently merged | `test_m1_ac_13_duplicate_warning_not_silently_merged` | **PASS** |
| **M1-AC-14** | Auditor access is strictly read-only | `test_m1_ac_14_auditor_read_only` | **PASS** |
| **M1-AC-15** | Important actions create audit events without leaking secrets | `test_m1_ac_15_audit_events_without_secret_leakage` | **PASS** |
| **M1-AC-16** | Dashboard counts respect role and institution scope | `test_m1_ac_16_dashboard_counts_respect_scope` | **PASS** |
| **M1-AC-17** | Frontend production build and backend quality checks pass | `test_m1_ac_17_backend_quality_health` | **PASS** |
| **M1-AC-18** | Synthetic seeding is repeatable and does not duplicate records | `test_m1_ac_18_synthetic_seeding_idempotency` | **PASS** |

---

## 5. Automated Test Results

The unified test runner ([scripts/test.ps1](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/scripts/test.ps1)) executed with zero failures:

### Backend Pytest Execution (67 Passed, 0 Failed in 6.39s)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\bhome\OneDrive\Desktop\VIT\SIH\SIH 2026\TOP 75\FDR_Sentinel\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0

backend/tests/test_auth_rbac.py ..............                           [ 20%]
backend/tests/test_health.py .....                                       [ 28%]
backend/tests/test_institutions_users.py ..............                  [ 49%]
backend/tests/test_instruments_registry.py ............                  [ 67%]
backend/tests/test_module1_acceptance.py ..................              [ 94%]
backend/tests/test_modules.py ....                                       [100%]

======================= 67 passed, 5 warnings in 6.39s ========================
```

### Frontend Vitest Execution (4 Passed, 0 Failed in 1.63s)
```text
 ✓ src/app/__tests__/App.test.tsx (4 tests) 139ms
 Test Files: 1 passed (1) | Tests: 4 passed (4)
```

### Frontend Production Build
```text
vite v8.3.5 building client environment for production...
✓ 1971 modules transformed.
dist/index.html                   1.05 kB │ gzip:   0.58 kB
dist/assets/index-CPzoGUrn.css   44.41 kB │ gzip:   8.19 kB
dist/assets/index-D5iF1lwC.js   505.19 kB │ gzip: 139.72 kB
✓ built in 744ms (Zero TypeScript or Linting Errors)
```

---

## 6. Known Limitations & Recommended Module 2 Scope

### Explicit Boundaries of Module 1
1. **Document Attachment & Extraction**: Module 1 establishes the metadata register. Real PDF document ingestion, SHA-256 evidence hashing, and multi-engine OCR extraction will be implemented in **Module 2**.
2. **Officer Scrutiny & Verification**: Promotion of trust levels from `L0_DECLARED` to `L1` (Document Consistent) and `L2` (Officer Verified) requires the discrepancy detection and scrutiny interface in **Module 3**.
3. **Direct Bank Gateway**: Direct API / SFTP connectivity for `L3_BANK_CONFIRMED` belongs to **Module 4**.
4. **Renewal and Release Workflows**: Formal release governance and renewal lineage tracking belong to **Module 5**.
5. **Email Service**: Out-of-band communication is used for temporary passwords; automated transactional SMTP delivery can be added in future production phases.

### Recommended Next Milestone
Proceed with **Module 2: Document Ingestion, Multi-Engine OCR Pipeline, and SHA-256 Evidence Hashing**.
