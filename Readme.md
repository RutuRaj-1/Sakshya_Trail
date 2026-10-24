# FDR Sentinel — Security Deposit & FDR Lifecycle Integrity Platform

**AICTE Regulation Bureau · Problem Statement ID: 26265**  
*Streamline of Security Deposit / FDR Portal · Theme: Smart Automation*  
**Team:** Ukdiche_Modak  
**Stage:** Module 1 Complete Handover (Identity, RBAC, Institution Registry, Instrument Registry & Audit Foundation)  

---

## 1. Project Overview

**FDR Sentinel** is an enterprise digital governance and lifecycle-integrity platform created for the **All India Council for Technical Education (AICTE) Regulation Bureau**. It establishes an authoritative single register for statutory Fixed Deposit Receipts (FDRs) and institutional security deposits submitted by technical education institutions across India.

### Key Capabilities & Completed Module 1 Deliverables
- **Authoritative Identity & Session Security**: Secure Argon2id password hashing, mandatory password rotation for provisioned nodal accounts, signed JWT sessions with `HttpOnly`, `SameSite=Lax` cookies, and origin CSRF protection.
- **Enforced Role-Based Scoping (RBAC)**: Fine-grained access control across 7 application roles. `INSTITUTION_USER` accounts are strictly scoped to their assigned institution and forbidden from cross-institution access or privilege tampering.
- **Statutory Institution Registry**: Full lifecycle management with normalized unique codes, state/type classification, verified nodal contacts, and non-destructive deactivation preserving audit history.
- **FDR Instrument Registry**: High-precision monetary storage (`Numeric(18, 2)` decimal; never float), parent institution foreign key, issuance and maturity date validation (`maturity_date > issue_date`).
- **Separation of Three Core Concepts**:
  - *Administrative Workflow Status*: `DRAFT`, `REGISTERED`.
  - *Evidentiary Trust Tier*: `L0 — DECLARED` (baseline default), `L1 — DOCUMENT_CONSISTENT` (Module 2 OCR), `L2 — OFFICER_VERIFIED` (Module 3 Scrutiny), `L3 — BANK_CONFIRMED` (Module 4 Direct Gateway). Ordinary registry endpoints cannot escalate trust levels.
  - *Derived Read-Only Maturity Indicator*: Derived dynamically as `ACTIVE`, `EXPIRING_SOON` (≤ 90-day warning window), or `EXPIRED`.
- **Conservative Duplicate-Reference Warning Path**: Normalized bank and reference number matching returns structured 409 warnings with existing record details without blocking legitimate records or merging data. Explicit authorized override (`confirm_duplicate: true`) records an auditable override.
- **Tamper-Evident Audit Ledger**: Immutable event trail capturing actor, timestamp, action, target record, and sanitized context without leaking passwords or secrets.
- **Scoped Executive Dashboard**: Role-scoped live counts and monetary sums derived directly from database queries.

---

## 2. Technology Stack

- **Backend**: Python 3.11+ (verified on Python 3.14.2), FastAPI, Pydantic v2 (`pydantic-settings`), Uvicorn.
- **Database & ORM**: SQLAlchemy 2.x declarative base, Alembic migrations.
  - **SQLite** (Default local zero-config development engine: `backend/fdr_sentinel.db`).
  - **PostgreSQL** (Production / Containerized staging via `psycopg[binary]` v3).
- **Frontend**: React 19, TypeScript, Vite 8 (with native reverse-proxy), Tailwind CSS v4, React Router v7, Lucide Icons.
- **Testing**: `pytest` + `httpx` (67 backend tests), `vitest` + `@testing-library/react` (4 frontend tests).

---

## 3. Directory & File Structure

```text
FDR_Sentinel/
├── Context.md                                    # Consolidated context baseline (Preserved)
├── FDR_Sentinel_PRD.md                           # Product Requirements Document (Preserved)
├── FDR_Sentinel_Project_Synopsis.md              # Research & solution synopsis (Preserved)
├── FDR_Sentinel_SRS.md                           # Software Requirements Specification (Preserved)
├── FDR_Sentinel_Seven_Module_Prototype_Blueprint.docx # Blueprint source (Preserved)
├── README.md                                     # Complete project documentation & developer guide
├── .gitignore                                    # Secrets, virtualenvs, caches, builds
├── .env.example                                  # Comprehensive environment template
├── Doc/
│   └── module1.md                                # Comprehensive Module 1 specification & test log
├── docs/
│   └── architecture/
│       └── module1_architecture.md               # Architecture, ERD, and trust model
├── scripts/
│   ├── dev.ps1                                   # Dev launcher for backend & frontend
│   └── test.ps1                                  # Unified test runner (backend + frontend)
├── backend/
│   ├── pyproject.toml                            # Backend dependencies & pytest config
│   ├── alembic.ini                               # Database migration settings
│   ├── alembic/                                  # Alembic migration scripts
│   ├── app/
│   │   ├── main.py                               # FastAPI application entrypoint & CORS
│   │   ├── core/                                 # Config (Pydantic Settings) & security
│   │   ├── db/                                   # Session maker, engine, Base & TimestampMixin
│   │   ├── common/                               # Envelopes, exceptions & error handlers
│   │   ├── api/v1/                               # API v1 aggregate router & health probes
│   │   └── modules/
│   │       ├── auth/                             # User models, RBAC dependencies, sessions
│   │       ├── institutions/                     # AICTE institution registry
│   │       ├── instruments/                      # FDR instrument registry & validation
│   │       ├── dashboard/                        # Scoped Module 1 dashboard summary
│   │       └── audit/                            # Tamper-evident audit event ledger
│   ├── scripts/
│   │   ├── bootstrap_admin.py                    # CLI command to securely bootstrap first admin
│   │   └── init_db.py                            # Idempotent synthetic demo seeding script
│   └── tests/
│       ├── conftest.py                           # Pytest fixtures & isolated DB harness
│       ├── test_health.py                        # Liveness & readiness probe tests
│       ├── test_auth_rbac.py                     # Authentication & RBAC enforcement tests
│       ├── test_institutions_users.py            # Institution CRUD & User administration tests
│       ├── test_instruments_registry.py          # FDR registry, validation & duplicate tests
│       ├── test_module1_acceptance.py            # Complete M1-AC-01 to M1-AC-18 acceptance tests
│       └── test_modules.py                       # Integration tests
└── frontend/
    ├── package.json                              # Vite, React 19, Tailwind v4, Vitest
    ├── vite.config.ts                            # Vite configuration & native /api reverse proxy
    ├── tsconfig.json                             # TypeScript references
    ├── index.html                                # SEO metadata & Inter typography
    └── src/
        ├── app/
        │   ├── App.tsx                           # Root component & providers
        │   ├── router.tsx                        # Client routing & ProtectedRoute
        │   └── routes/                           # Dashboard, Instruments, Institutions, etc.
        ├── components/
        │   ├── common/                           # Badge, Button, Card, StatusIndicator
        │   └── navigation/                       # Header, Sidebar
        ├── features/
        │   ├── auth/                             # AuthContext & Session management
        │   ├── instruments/                      # InstrumentsList, InstrumentModal
        │   └── institutions/                     # InstitutionsList, InstitutionModal
        ├── api/
        │   ├── client.ts                         # Centralized typed HTTP client (/api/v1)
        │   └── endpoints.ts                      # Typed API methods
        └── types/
            └── index.ts                          # Shared TypeScript domain contracts
```

---

## 4. Developer Handover & Getting Started Guide

### 4.1 Prerequisites
- **Python**: 3.11 or higher (tested on Python 3.14.2)
- **Node.js**: v18.0.0 or higher (tested on v22.19.0)
- **Package Managers**: `pip` (Python), `npm` 10+ (Node)
- **PowerShell**: 5.1+ (Windows) or bash (macOS/Linux)

---

### 4.2 Environment Configuration

Create your `.env` file in the root directory (or `backend/.env`):

```bash
# General
ENVIRONMENT=development
PROJECT_NAME="FDR Sentinel"
VERSION=0.2.0
API_V1_STR=/api/v1
SECRET_KEY=fdr-sentinel-regulatory-secret-key-2026-production-grade
DEBUG=True

# Server Bindings
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# Database Connection (Default: SQLite for local dev)
DATABASE_URL=sqlite:///./fdr_sentinel.db

# If using PostgreSQL:
# DATABASE_URL=postgresql+psycopg://fdr_admin:SecurePass2026@localhost:5432/fdr_sentinel_db

# CORS Allowed Origins
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:5174","http://127.0.0.1:5174"]
```

---

### 4.3 Database Setup & Migrations

The repository uses Alembic for schema migrations:

```powershell
# Navigate to backend
cd backend

# Run pending migrations to head
.\.venv\Scripts\alembic.exe upgrade head
```

---

### 4.4 PostgreSQL & Optional Docker Compose Setup

To run a dedicated PostgreSQL instance instead of SQLite:

```powershell
# 1. Start PostgreSQL with Docker (optional)
docker run --name fdr-postgres -e POSTGRES_USER=fdr_admin -e POSTGRES_PASSWORD=SecurePass2026 -e POSTGRES_DB=fdr_sentinel_db -p 5432:5432 -d postgres:16-alpine

# 2. Set environment variable in your .env:
# DATABASE_URL=postgresql+psycopg://fdr_admin:SecurePass2026@localhost:5432/fdr_sentinel_db

# 3. Apply migrations to PostgreSQL
cd backend
.\.venv\Scripts\alembic.exe upgrade head
```

---

### 4.5 Secure First-Administrator Bootstrap

To create the initial `SYSTEM_ADMIN` account safely through the CLI (prompts securely for password without committing credentials):

```powershell
cd backend
.\.venv\Scripts\python scripts/bootstrap_admin.py --email admin@aicte-india.org --name "AICTE Master Administrator"
```
*(Prompts interactively for an 8+ character password and verifies confirmation before saving).*

---

### 4.6 Synthetic Demonstration Data Seeding

To populate idempotent synthetic institutions, users across all roles, and sample FDR instruments (including an intentional duplicate for testing):

```powershell
cd backend
.\.venv\Scripts\python scripts/init_db.py
```

*This command is 100% idempotent and can be safely executed multiple times without generating duplicate records.*

**Pre-seeded Evaluator Demo Accounts:**
| Role | Email | Password | Scope & Characteristics |
|---|---|---|---|
| `SYSTEM_ADMIN` | `admin@aicte-india.org` | `AdminPassword@2026` | Bureau-wide technical setup, user provisioning, institution management |
| `SCRUTINY_OFFICER` | `scrutiny.verma@aicte-india.org` | `OfficerPassword@2026` | Bureau-wide review of institutions and instruments, scrutiny corrections |
| `BRANCH_HEAD` | `branch.head.north@aicte-india.org` | `BranchPassword@2026` | Regional AICTE jurisdiction oversight (Read-Only) |
| `AUDITOR` | `auditor.compliance@aicte-india.org` | `AuditorPassword@2026` | Independent oversight, read-only inspection of records and audit ledger |
| `INSTITUTION_USER` | `nodal@diet-delhi.ac.in` | `NodalPassword@2026` | Scoped to DIET Delhi (`DEMO-AICTE-001`). Forces password rotation on first login |
| `INSTITUTION_USER` | `nodal.pune@mims-demo.ac.in` | `NodalPassword@2026` | Scoped to MIMS Pune (`DEMO-AICTE-002`). Proves multi-tenant isolation |

---

### 4.7 Starting Backend & Frontend

#### Terminal 1 — FastAPI Backend:
```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Swagger API Docs: `http://127.0.0.1:8000/docs`
- Health Probe: `http://127.0.0.1:8000/healthz`

#### Terminal 2 — React Frontend (Vite):
```powershell
cd frontend
npm install
npm run dev
```
- Web Application Portal: `http://localhost:5173` (or `http://localhost:5174`)

---

## 5. Automated Testing & Verification

Execute the unified test runner from the root directory:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
```

### 5.1 Backend Pytest Suite (67 / 67 Passed in ~5.5s)
```powershell
backend\.venv\Scripts\pytest backend/tests -v
```
Test modules executed:
- `test_health.py` (5 tests): Liveness, readiness, database dialect probes.
- `test_auth_rbac.py` (14 tests): Argon2 hashing, JWT cookies, role permissions, CSRF origin.
- `test_institutions_users.py` (14 tests): Institution CRUD, unique code, soft-delete, user provisioning, last-admin lockout.
- `test_instruments_registry.py` (12 tests): Amount/date validation, L0 trust lock, duplicate warning override, decimal precision.
- `test_module1_acceptance.py` (18 tests): Explicit coverage for **M1-AC-01 through M1-AC-18**.
- `test_modules.py` (4 tests): End-to-end integration flows.

### 5.2 Frontend Vitest Suite (4 / 4 Passed)
```powershell
cd frontend
npm test
```

### 5.3 Production Bundle Build
```powershell
cd frontend
npm run build
```
*(Runs TypeScript compiler `tsc -b` and Vite production bundler with 0 errors).*

---

## 6. Role-Based Access Control (RBAC) Matrix

| Operation / Endpoint | `SYSTEM_ADMIN` | `SCRUTINY_OFFICER` | `BRANCH_HEAD` | `COMPETENT_AUTHORITY` | `FINANCE_OFFICER` | `AUDITOR` | `INSTITUTION_USER` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Institution: List / Read** | Full | Full | Full | Full | Full | Full (Read-Only) | **Own Institution Only** |
| **Institution: Create** | Allowed | Denied | Denied | Denied | Denied | Denied | Denied |
| **Institution: Edit Contact Info** | Allowed | Allowed | Denied | Denied | Denied | Denied | **Own Contact Fields Only** |
| **Institution: Deactivate/Activate** | Allowed | Denied | Denied | Denied | Denied | Denied | Denied |
| **User Administration Portal** | Full | Denied | Denied | Denied | Denied | Denied | Denied |
| **Instruments: List / Read** | Full | Full | Full | Full | Full | Full (Read-Only) | **Own FDRs Only** |
| **Instruments: Create** | Allowed | Allowed | Denied | Denied | Denied | Denied | **Own FDRs Only** |
| **Instruments: Edit Permitted** | Allowed | Allowed | Denied | Denied | Denied | Denied | **Own Draft/Reg FDRs** |
| **Instruments: Escalate Trust Level** | **Blocked** | **Blocked** | **Blocked** | **Blocked** | **Blocked** | **Blocked** | **Blocked** |
| **Dashboard: Scoped Metrics** | Bureau | Bureau | Bureau | Bureau | Bureau | Bureau | **Own Scoped Totals** |
| **Audit Trails: Inspect** | Allowed | Denied | Denied | Denied | Denied | Allowed | Denied |

---

## 7. Known Limitations & Module 2 Roadmap

### Limitations in Current Scope
1. **Physical Document Extraction**: In Module 1, instruments store statutory metadata. PDF attachment, SHA-256 document hashing, and multi-OCR extraction are scheduled for **Module 2**.
2. **Scrutiny Verification Queue**: Promotion from `L0_DECLARED` to `L1` (Document Consistent) and `L2` (Officer Verified) requires the formal discrepancy detection engine in **Module 3**.
3. **Live Bank API Confirmation**: Promotion to `L3_BANK_CONFIRMED` requires the SFTP / direct bank gateway adapters in **Module 4**.
4. **Renewal & Release State Transitions**: Formal release approvals, encashment directives, and renewal lineage graphs belong to **Module 5**.
5. **Email Delivery**: Password reset credentials generate a secure temporary password displayed to the administrator for secure transmission; automated SMTP mail delivery will be integrated in future phases.

### Recommended Next Step
Proceed to **Module 2: Document Ingestion, Multi-Engine OCR Pipeline, and SHA-256 Evidence Hashing**.
