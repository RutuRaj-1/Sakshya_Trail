# FDR Sentinel — Architecture, Identity & RBAC Foundation Report

**Project:** FDR Sentinel (AICTE Security Deposit / FDR Lifecycle Integrity Platform)  
**Problem Statement ID:** 26265  
**Department:** Regulation Bureau, All India Council for Technical Education (AICTE)  
**Stage:** Module 1 (Bootstrap, Identity, Authentication & RBAC Foundation)  
**Date:** October 2026  
**Status:** Completed & Verified  

---

## 1. Executive Summary

This document summarizes the complete implementation of **Module 1: Identity, Authentication, Role-Based Access Control (RBAC), and Database Foundation** for **FDR Sentinel**.

The application enforces an authoritative, multi-tier regulatory permission hierarchy designed specifically for the AICTE Regulation Bureau. It establishes cryptographic password security (Argon2id), signed short-lived session management via secure HttpOnly SameSite cookies, server-side identity validation, rigid institution scoping boundaries, tamper-evident audit logging, and Alembic database migrations.

All existing project source documents (`Context.md`, `FDR_Sentinel_PRD.md`, `FDR_Sentinel_Project_Synopsis.md`, `FDR_Sentinel_SRS.md`) remain strictly preserved. `FDR_Sentinel_Seven_Module_Prototype_Blueprint.docx` is preserved untouched.

---

## 2. Database Foundation & Models

### 2.1 Database Architecture
- **Dual SQL Engine**: SQLAlchemy 2.x declarative standard (`DeclarativeBase`).
  - **Local Development**: SQLite (`sqlite:///./fdr_sentinel.db`) and in-memory test harness (`sqlite:///:memory:`).
  - **Production / Staging**: PostgreSQL (`postgresql+psycopg://...`) via `psycopg[binary]` v3 driver with connection pooling (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`).
- **Firebase Web & Storage Integration**:
  - Initialized with project ID `sih-26265-fdr` in `frontend/src/lib/firebase.ts` and configured in `backend/app/core/config.py`.
- **Database Migrations (Alembic)**:
  - Migration script: `backend/alembic/versions/2026_10_24_2137-1a1cd8595579_create_initial_identity_models.py`
  - Applied via `alembic upgrade head`.

### 2.2 Models Implemented

#### `User` (`backend/app/modules/auth/models.py`)
- `id`: UUID primary key (String 36).
- `full_name`: Official legal name.
- `email`: Normalized lowercase unique email address.
- `password_hash`: Argon2id cryptographic hash (never plaintext).
- `role`: Validated enum string (`SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, `FINANCE_OFFICER`, `INSTITUTION_USER`, `AUDITOR`).
- `is_active`: Boolean status flag; deactivated accounts are denied immediately.
- `must_change_password`: Boolean flag for provisioned accounts requiring forced rotation on first login.
- `institution_id`: Optional foreign key to `institutions.id`.
- `created_at` & `updated_at`: UTC timestamps.

#### `Institution` (`backend/app/modules/institutions/models.py`)
- `id`: UUID primary key.
- `code`: Unique statutory institution code (AICTE Permanent ID e.g., `1-10924811`).
- `legal_name` & `display_name`: Official institute titles.
- `institution_type`: Flexible, bounded string (`TECHNICAL_INSTITUTE`, `ENGINEERING_COLLEGE`, `MANAGEMENT_INSTITUTE`, `PHARMACY_COLLEGE`, `POLYTECHNIC`, etc.).
- `is_active`: Regulatory status.
- `contact_name`, `contact_email`, `contact_phone`: Nodal officer communications.
- `address_line1`, `address_line2`, `city`, `state`, `postal_code`: Physical location.
- `assigned_office`: Regional AICTE jurisdiction.
- `is_synthetic`: Marker for prototype/demo data.

#### `AuditEvent` (`backend/app/modules/audit/models.py`)
- `id`: UUID primary key.
- `actor_user_id`, `actor_email`, `actor_role`: Identity of the performing user.
- `action`: Material event type (`AUTH_LOGIN`, `AUTH_LOGOUT`, `AUTH_PASSWORD_CHANGE`, `USER_PROVISIONED`, `FDR_VERIFIED`, etc.).
- `entity_type` & `entity_id`: Target of the lifecycle action.
- `outcome`: `SUCCESS` or `FAILURE`.
- `request_id`: Correlation ID for traceability.
- `ip_address`: Client network context.
- `metadata_json`: Sanitized JSON payload. **Strict credential redaction**: passwords, tokens, hashes, and secrets are permanently stripped before persistence.

---

## 3. Roles and Access Control (RBAC)

### 3.1 Official Application Roles
The system enforces 7 validated roles:

| Role Identifier | Description | Internal / External | Scoping Constraint |
|---|---|---|---|
| `SYSTEM_ADMIN` | Technical administrator | Internal | Cannot be assigned an institution association |
| `SCRUTINY_OFFICER` | Scrutiny review official | Internal | Cannot be assigned an institution association |
| `BRANCH_HEAD` | Regional AICTE Bureau head | Internal | Cannot be assigned an institution association |
| `COMPETENT_AUTHORITY` | Statutory release approval authority | Internal | Cannot be assigned an institution association |
| `FINANCE_OFFICER` | Financial reconciliation officer | Internal | Cannot be assigned an institution association |
| `INSTITUTION_USER` | Institutional nodal representative | External | **Must be associated with exactly one valid institution** |
| `AUDITOR` | Independent compliance auditor | Internal | **Strictly read-only** across all records and audit events |

### 3.2 Authorization Principles Enforced
1. **Institution Isolation**: An `INSTITUTION_USER` is strictly scoped to records matching their assigned `institution_id`. Any attempt to access or modify records of another institution raises a `403 Forbidden`.
2. **Read-Only Auditor**: The `AUDITOR` role has full visibility into records and audit trails, but state-changing actions are blocked by `require_read_only_or_permitted`.
3. **Internal vs. External Separation**: Internal users cannot be associated with an institution to prevent regulatory rule bypass.
4. **Backend Authorization Boundary**: Role and scope checks are enforced in the API dependency layer (`backend/app/modules/auth/dependencies.py`), not solely on client UI elements.
5. **Fresh Server-Side Lookup**: Session validation retrieves the active user record on every authenticated call so that revoked roles or deactivated accounts immediately lose access without waiting for token expiry.

---

## 4. Authentication Architecture

- **Password Hashing**: Implemented with **Argon2id** (`argon2-cffi`) using secure parameters (memory cost 64MB, 2 iterations, 2 parallelism, 32-byte hash length). Plaintext passwords are never stored.
- **Session Tokens**: Short-lived signed JWTs (`HS256`, 60-minute expiry) signed with `SECRET_KEY`.
- **Cookie Security**:
  - Cookie name: `fdr_session`
  - Flags: `HttpOnly=True`, `SameSite=Lax`, `Path=/`, `Secure` (configurable via `AUTH_COOKIE_SECURE`).
  - Tokens are never stored in browser `localStorage`.
- **CSRF & Origin Protection**: All state-changing endpoints (`POST`, `PUT`, `DELETE`, `PATCH`) validate the `Origin` and `Referer` headers against the exact `CORS_ORIGINS` whitelist.

---

## 5. First Administrator Bootstrap Procedure

The system provides a dedicated CLI management script (`backend/scripts/bootstrap_admin.py`) to safely create the initial `SYSTEM_ADMIN` without exposing public registration routes or committing default credentials.

### Execution Command:
```powershell
# Interactive password prompt
python backend/scripts/bootstrap_admin.py --email admin@aicte-india.org --name "AICTE Administrator"

# Or pass securely via environment variable / flag:
$env:FDR_ADMIN_PASSWORD="YourSecurePassword@2026"
python backend/scripts/bootstrap_admin.py --email admin@aicte-india.org --name "AICTE Administrator"
```

### Safety Rules Enforced by Bootstrap:
1. Validates email format and minimum 8-character password length.
2. Prompts securely using `getpass` (does not display typed characters on screen).
3. Refuses duplicate administrators: if an account with the specified email already exists, it exits with error code 1 and logs the refusal.
4. Plaintext passwords are never saved.

---

## 6. Frontend Authentication & Shell

### Implemented UI Components:
1. **`LoginPage.tsx`**: Clean financial-administration interface with input validation, friendly error banners, and one-click evaluator demo account buttons.
2. **`AuthContext.tsx`**: Manages global session state, initial session restoration via `GET /api/v1/auth/me`, and login/logout handlers.
3. **`ProtectedRoute.tsx`**:
   - Guards authenticated routes, redirecting unauthenticated users to `/login`.
   - Forces users with `must_change_password: true` to `/change-password`.
   - Enforces role restrictions (`allowedRoles`), rendering an accessible `403 Access Restricted` screen for unauthorized roles.
4. **`ChangePasswordPage.tsx`**: Enables provisioned users to update their temporary credentials, clearing `must_change_password`.
5. **`Header.tsx`**: Displays active user full name, official role badge, and an interactive sign-out button.

---

## 7. Automated Test Suite & Verification

A dedicated test suite (`backend/tests/test_auth_rbac.py`) verifies all 14 required Prompt 2 test scenarios alongside health probes and module integration tests.

### Test Results Summary:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.1.1, pluggy-1.7.0
rootdir: C:\Users\bhome\OneDrive\Desktop\VIT\SIH\SIH 2026\TOP 75\FDR_Sentinel\backend
configfile: pyproject.toml
plugins: anyio-4.15.1, asyncio-1.4.0

backend/tests/test_auth_rbac.py::test_successful_login PASSED            [ 4%]
backend/tests/test_auth_rbac.py::test_invalid_password PASSED            [ 8%]
backend/tests/test_auth_rbac.py::test_unknown_user PASSED                [ 13%]
backend/tests/test_auth_rbac.py::test_inactive_account PASSED            [ 17%]
backend/tests/test_auth_rbac.py::test_logout_and_session_clearing PASSED [ 21%]
backend/tests/test_auth_rbac.py::test_current_user_endpoint PASSED       [ 26%]
backend/tests/test_auth_rbac.py::test_password_change PASSED             [ 30%]
backend/tests/test_auth_rbac.py::test_invalid_role_assignment PASSED     [ 34%]
backend/tests/test_auth_rbac.py::test_institution_user_without_institution PASSED [ 39%]
backend/tests/test_auth_rbac.py::test_unauthorized_role_access PASSED   [ 43%]
backend/tests/test_auth_rbac.py::test_cors_and_csrf_origin_behavior PASSED [ 47%]
backend/tests/test_auth_rbac.py::test_password_hashes_are_not_plaintext PASSED [ 52%]
backend/tests/test_auth_rbac.py::test_administrator_bootstrap_refuses_duplicate_accounts PASSED [ 56%]
backend/tests/test_auth_rbac.py::test_audit_entries_do_not_contain_passwords_or_tokens PASSED [ 60%]
backend/tests/test_health.py::test_root_welcome PASSED                   [ 65%]
backend/tests/test_health.py::test_liveness_probe PASSED                 [ 69%]
backend/tests/test_health.py::test_liveness_alias_healthz PASSED         [ 73%]
backend/tests/test_health.py::test_readiness_probe_success PASSED        [ 78%]
backend/tests/test_health.py::test_readiness_alias_readyz PASSED         [ 82%]
backend/tests/test_modules.py::test_auth_roles_endpoint PASSED          [ 86%]
backend/tests/test_modules.py::test_create_and_list_institution PASSED  [ 91%]
backend/tests/test_modules.py::test_create_and_summarize_instruments PASSED [ 95%]
backend/tests/test_modules.py::test_audit_trail_listing PASSED           [100%]

======================== 23 passed, 1 warning in 1.37s ========================

Frontend Vitest Suite:
✓ src/app/__tests__/App.test.tsx (4 tests) 154ms
Test Files: 1 passed (1) | Tests: 4 passed (4)
```

---

## 8. Verified Files List

```text
FDR_Sentinel/
├── Doc/
│   └── module1.md                                # Comprehensive Module 1 documentation
├── docs/
│   ├── module1.md                                # Reference link
│   ├── architecture/system_overview.md           # Architecture and trust hierarchy
│   └── development/getting_started.md            # Setup and execution guide
├── scripts/
│   ├── dev.ps1                                   # Local development launcher
│   └── test.ps1                                  # Unified cross-stack test runner
├── backend/
│   ├── pyproject.toml                            # Dependencies (argon2-cffi, pyjwt, etc.)
│   ├── alembic.ini                               # Alembic migration configuration
│   ├── alembic/versions/2026_10_24_2137-...      # Initial database migration script
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py                         # Settings, JWT, Cookie, and Firebase config
│   │   │   └── security.py                       # Argon2 hasher, JWT, and sanitize_dict
│   │   ├── db/
│   │   │   ├── base.py                           # DeclarativeBase and TimestampMixin
│   │   │   └── session.py                        # Engine, SessionLocal, connection probe
│   │   └── modules/
│   │       ├── auth/
│   │       │   ├── models.py                     # User SQLAlchemy model
│   │       │   ├── schemas.py                    # Login, UserRead, PasswordChange schemas
│   │       │   ├── service.py                    # Provisioning and authentication logic
│   │       │   ├── dependencies.py               # RBAC and institution scoping guards
│   │       │   └── router.py                     # /auth/login, /auth/logout, /auth/me, /auth/change-password
│   │       ├── institutions/
│   │       │   ├── models.py                     # Institution model
│   │       │   ├── schemas.py                    # Institution schemas
│   │       │   └── router.py                     # Institution endpoints
│   │       ├── instruments/
│   │       │   ├── models.py                     # Financial instrument model
│   │       │   └── router.py                     # FDR registry endpoints
│   │       └── audit/
│   │           ├── models.py                     # AuditEvent model
│   │           ├── service.py                    # Sanitized event logging
│   │           └── schemas.py                    # Audit event schemas
│   ├── scripts/
│   │   ├── bootstrap_admin.py                    # Secure CLI admin bootstrap script
│   │   └── init_db.py                            # Idempotent database seeder
│   └── tests/
│       ├── test_auth_rbac.py                     # 14 required Prompt 2 tests
│       ├── test_health.py                        # Liveness & readiness probe tests
│       └── test_modules.py                       # Integration tests
└── frontend/
    ├── src/
    │   ├── lib/firebase.ts                       # Official Firebase Web SDK initialization
    │   ├── api/
    │   │   ├── client.ts                         # Fetch client with credentials: 'include'
    │   │   └── endpoints.ts                      # Typed authApi, healthApi, instrumentsApi
    │   ├── types/index.ts                        # TypeScript domain interfaces
    │   ├── features/auth/
    │   │   ├── AuthContext.tsx                   # React session context & useAuth hook
    │   │   └── ProtectedRoute.tsx                # Role-gated route protector
    │   ├── components/navigation/Header.tsx      # Header with user avatar, role, and logout
    │   └── app/
    │       ├── App.tsx                           # Root app wrapped in AuthProvider
    │       ├── router.tsx                        # Router with public & protected routes
    │       ├── routes/
    │       │   ├── LoginPage.tsx                 # Accessible login page with demo accounts
    │       │   └── ChangePasswordPage.tsx        # Forced password rotation view
    │       └── __tests__/App.test.tsx            # Component unit tests
```

---

## 9. Next Steps for Prompt 3

1. **Module 2 & 3: FDR Submission Wizard & File Storage**: Multi-step deposit submission wizard supporting PDF/TIFF upload with SHA-256 integrity hashing and Firebase Storage / local object storage backup.
2. **Deficiency & Scrutiny Workflow**: Scrutiny queue allowing scrutiny officers to review submissions, raise observations, flag anomalies, and advance trust levels from L1 to L3.
3. **Lineage Preservation**: Data models linking renewals and replacements to parent instruments to prevent breaking the chain of evidence.
