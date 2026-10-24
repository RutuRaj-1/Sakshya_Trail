# FDR Sentinel — Security Deposit & FDR Lifecycle Integrity Platform

**AICTE Regulation Bureau · Problem Statement ID: 26265**  
*Streamline of Security Deposit / FDR Portal · Theme: Smart Automation*  
**Team:** Ukdiche_Modak

---

## 1. Project Overview

**FDR Sentinel** is a digital governance and lifecycle-integrity platform created for the **All India Council for Technical Education (AICTE) Regulation Bureau**. It provides a single trusted register for statutory Fixed Deposit Receipts (FDRs) and security deposits submitted by technical institutions across India.

### Key Capabilities
- **Explicit Trust Provenance (L1–L4)**: Differentiates between declared data (L1), OCR/document-consistent data (L2), scrutiny officer-verified data (L3), and legitimate bank-confirmed data (L4).
- **Automated Lifecycle & Maturity Tracking**: Monitors deposit validity, sends configurable advance renewal notifications (90d/60d/30d), and tracks lien endorsements.
- **Renewal Lineage**: Preserves an unbroken historical chain across replacements and roll-overs without overwriting past certificates.
- **Gated Release & Refund Workflow**: Prevents unauthorized releases by verifying all regulatory conditions before competent-authority approval.
- **Tamper-Evident Audit Ledger**: Immutable event trail capturing all regulatory reviews, status changes, and administrative actions.

---

## 2. Technology Stack

- **Backend**: Python 3.11+ (tested on Python 3.14.2), FastAPI, Pydantic v2 (`pydantic-settings`).
- **ORM & Migrations**: SQLAlchemy 2.x (`DeclarativeBase`), Alembic.
- **Database**: 
  - **PostgreSQL** (Production / Staging / External service via `psycopg[binary]` v3).
  - **SQLite** (Local zero-config development and in-memory test harness).
  - **Firebase** (Adapter configuration placeholders for optional cloud storage).
- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`), React Router v7, Lucide Icons.
- **Testing**: `pytest` + `httpx` (Backend), `vitest` + `@testing-library/react` (Frontend).
- **Deployment Strategy**: Modular monolith. *(No Docker is required or utilized at this stage).*

---

## 3. Directory Structure

```text
FDR_Sentinel/
├── Context.md                                    # Consolidated context baseline (Preserved)
├── FDR_Sentinel_PRD.md                           # Product Requirements Document (Preserved)
├── FDR_Sentinel_Project_Synopsis.md              # Research & solution synopsis (Preserved)
├── FDR_Sentinel_SRS.md                           # Software Requirements Specification (Preserved)
├── FDR_Sentinel_Seven_Module_Prototype_Blueprint.docx # Blueprint source (Preserved)
├── README.md                                     # Complete project documentation
├── .gitignore                                    # Secrets, virtualenvs, caches, builds
├── .env.example                                  # Comprehensive environment template
├── Doc/
│   └── module1.md                                # Detailed Module 1 architecture summary
├── docs/
│   ├── architecture/
│   │   └── system_overview.md                    # Architecture diagram and trust levels
│   └── development/
│       └── getting_started.md                    # Developer onboarding guide
├── scripts/
│   ├── dev.ps1                                   # One-click dev launcher for backend & frontend
│   └── test.ps1                                  # Unified test runner (backend + frontend)
├── backend/
│   ├── pyproject.toml                            # Backend dependencies & pytest config
│   ├── alembic.ini                               # Database migration settings
│   ├── alembic/                                  # Alembic migration scripts
│   ├── app/
│   │   ├── main.py                               # FastAPI application entrypoint
│   │   ├── core/                                 # Config (Pydantic Settings) & security
│   │   ├── db/                                   # Session maker, engine, and base
│   │   ├── common/                               # Standard response envelopes & exceptions
│   │   ├── api/v1/                               # API v1 routes & health probes
│   │   └── modules/
│   │       ├── auth/                             # User models, roles, bootstrap
│   │       ├── institutions/                     # AICTE institution registry
│   │       ├── instruments/                      # FDR instruments & executive KPI summary
│   │       └── audit/                            # Tamper-evident audit event ledger
│   ├── scripts/
│   │   └── init_db.py                            # Database seed script with sample data
│   └── tests/
│       ├── conftest.py                           # Pytest fixtures & isolated in-memory DB
│       ├── test_health.py                        # Liveness & database readiness tests
│       └── test_modules.py                       # Integration tests for domain modules
└── frontend/
    ├── package.json                              # Vite, React 19, Tailwind v4, Vitest
    ├── vite.config.ts                            # Vite build & Vitest test runner setup
    ├── tsconfig.json                             # TypeScript project references
    ├── tsconfig.app.json                         # Strict frontend TypeScript configuration
    ├── index.html                                # Inter typography & SEO metadata
    └── src/
        ├── app/
        │   ├── App.tsx                           # Root component
        │   ├── router.tsx                        # React Router routes
        │   └── routes/                           # Dashboard, Instruments, Institutions, Health, Audit
        ├── components/
        │   ├── common/                           # Badge, Button, Card, StatusIndicator
        │   └── navigation/                       # Header (live health probe), Sidebar
        ├── layouts/
        │   └── MainLayout.tsx                    # Responsive administrative shell
        ├── features/
        │   ├── instruments/                      # InstrumentsList, InstrumentSummaryCards
        │   └── institutions/                     # InstitutionsList
        ├── api/
        │   ├── client.ts                         # Centralized typed HTTP client
        │   └── endpoints.ts                      # Typed API methods
        ├── hooks/
        │   └── useHealth.ts                      # Health & readiness polling hook
        ├── lib/
        │   └── utils.ts                          # formatINR, formatDate, cn
        └── types/
            └── index.ts                          # Domain TypeScript interfaces
```

---

## 4. Quick Start & Execution Commands

### Prerequisites
- Python 3.11+
- Node.js 18+ (tested with v22.19.0)
- npm 10+ (tested with 11.11.0)

### 4.1 Backend Setup
```powershell
# Navigate to project root
cd FDR_Sentinel

# Create and activate virtual environment (if not already created)
python -m venv backend/.venv

# Install dependencies
backend\.venv\Scripts\python -m pip install -e backend

# Initialize and seed database with sample AICTE institutions & FDRs
backend\.venv\Scripts\python backend/scripts/init_db.py

# Start FastAPI backend server
backend\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

### 4.2 Frontend Setup
```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

### 4.3 One-Click Development Launcher (PowerShell)
From the project root:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

---

## 5. Running Quality Checks and Tests

Execute both test suites in one command via the unified runner:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
```

Or execute them individually:

### Backend Tests (pytest)
```powershell
backend\.venv\Scripts\pytest backend/tests -v
```
*Current status: 10 passed in 0.11s.*

### Frontend Tests (vitest)
```powershell
cd frontend
npm test
```
*Current status: 3 passed in 1.18s.*

### Frontend Typecheck & Production Build
```powershell
cd frontend
npm run build
```
*Current status: Successfully built client bundle in ~400ms.*

---

## 6. Health & Diagnostics Endpoints

The system exposes live observability probes:

| Endpoint | Method | Purpose | Response Sample |
|---|---|---|---|
| `/api/v1/health/live` | `GET` | Liveness probe verifying API worker is responding | `{"status": "alive", "service": "FDR Sentinel", "version": "0.1.0"}` |
| `/api/v1/health/ready` | `GET` | Readiness probe checking database reachability via `SELECT 1` | `{"status": "ready", "is_ready": true, "components": {"database": {"status": "connected", "dialect": "sqlite", "latency_ms": 0.36}}}` |
| `/healthz` | `GET` | Root alias for orchestrator liveness | `{"status": "alive"}` |
| `/readyz` | `GET` | Root alias for orchestrator readiness | `{"is_ready": true}` |
| `/api/v1/instruments/summary` | `GET` | Live executive metrics for administrative dashboard | Total deposits, active count, expiring soon (<90d), under scrutiny |

---

## 7. Roadmap & Next Modules

- **Module 1 (Completed)**: Foundational modular-monolith scaffold, database layer (PostgreSQL/SQLite dual engine), health/readiness observability, centralized frontend API client, and administrative UI shell.
- **Module 2**: End-to-end FDR submission wizard, document upload with SHA-256 integrity hashing, and scrutiny review workflow.
- **Module 3**: Automated maturity & validity rule engine with advance notifications (90d/60d/30d) and renewal lineage tracking.
- **Module 4**: Gated release/refund authorization workflow, competent authority sign-off, and policy compliance verification.
- **Module 5**: Role-based access enforcement, security hardening, simulated bank confirmation adapter, and final prototype demonstration.
