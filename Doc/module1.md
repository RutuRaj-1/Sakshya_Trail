# FDR Sentinel — Module 1 Architecture & Bootstrap Report

**Project:** FDR Sentinel (AICTE Security Deposit / FDR Lifecycle Integrity Platform)  
**Problem Statement ID:** 26265  
**Department:** Regulation Bureau, All India Council for Technical Education (AICTE)  
**Stage:** Module 1 of 5 (Foundational Bootstrap & Initial Runnable System)  
**Date:** October 2026  

---

## 1. Executive Summary

This document summarizes the complete bootstrap and foundational architecture implemented for **FDR Sentinel** during Prompt 1. 

The baseline architecture establishes a clean, decoupled modular monolith designed to solve PS 26265 for the AICTE Regulation Bureau: providing authoritative lifecycle governance, explicit evidence provenance (L1–L4 trust levels), automated maturity monitoring, and tamper-evident audit trails over institutional Fixed Deposit Receipts (FDRs) and security deposits.

All existing project documents (`Context.md`, `FDR_Sentinel_PRD.md`, `FDR_Sentinel_Project_Synopsis.md`, `FDR_Sentinel_SRS.md`) have been strictly preserved. `FDR_Sentinel_Seven_Module_Prototype_Blueprint.docx` was encountered with locked file permissions (`[Errno 13] Permission denied`, held open by an external application on Windows) and has been preserved completely untouched without modification.

---

## 2. Architectural Decisions & Material Choices

### 2.1 Modular Monolith
In accordance with the PRD (§17, §19) and `Context.md`, FDR Sentinel is implemented as a **modular monolith** with clear domain boundaries:
- **Authentication & Roles (`backend/app/modules/auth`)**: Role-based access control (RBAC) scaffolding covering AICTE Administrator, Scrutiny Officer, Institution Representative, Compliance Auditor, and Read-Only Observer.
- **Institutions (`backend/app/modules/institutions`)**: Higher education technical institute registry (permanent AICTE ID, state, discipline category, nodal contact).
- **Instruments (`backend/app/modules/instruments`)**: Financial instrument register (bank name, branch, FDR receipt number, principal amount, issue/maturity dates, joint AICTE lien flag, and trust levels).
- **Audit Ledger (`backend/app/modules/audit`)**: Append-only event trail recording actor, action, timestamp, entity ID, and metadata.
- **Common & Core (`backend/app/common`, `backend/app/core`)**: Typed response envelopes (`StandardResponse`, `ErrorResponse`), domain exceptions, configuration, and security constants.

### 2.2 Database Layer: PostgreSQL & SQLite Dual Engine
- Built with **SQLAlchemy 2.x** declarative models (`DeclarativeBase`) and **Alembic** migrations.
- Configured with environment-based `DATABASE_URL`.
- Default local configuration automatically uses SQLite (`sqlite:///./fdr_sentinel.db`) for immediate zero-friction local execution without requiring an active external database server.
- Seamlessly connects to PostgreSQL (`postgresql+psycopg://...`) via the installed `psycopg[binary]` v3 driver with connection pooling (`pool_size`, `max_overflow`, `pool_pre_ping=True`).
- Firebase adapter configuration placeholders provided in `app/core/config.py` for cloud storage integration.

### 2.3 Health Observability Probes
- **Liveness (`GET /api/v1/health/live` & `/healthz`)**: Verifies the FastAPI worker process is active and receiving requests.
- **Readiness (`GET /api/v1/health/ready` & `/readyz`)**: Actively probes the configured database via a live `SELECT 1` ping. Measures latency in milliseconds and reports status (`connected` or `unreachable`), database dialect (`sqlite` or `postgresql`), and component operational health.

### 2.4 Frontend Architecture
- **React 19 + TypeScript + Vite 8**: Extremely fast development cycle with full static typing.
- **Tailwind CSS v4 (`@tailwindcss/vite`)**: Professional, restrained institutional theme with tailored color tokens (`sentinel`, `slate-850`, `slate-950`).
- **React Router**: Client-side routing with clean modular views:
  - `/`: Executive Dashboard with live KPI summary cards, quick action links, and recent security deposits.
  - `/instruments`: Lifecycle FDR registry with status filtering and trust level tags.
  - `/institutions`: AICTE registered technical institutions directory with search.
  - `/audit`: Tamper-evident regulatory audit trail ledger.
  - `/health`: Real-time system diagnostics displaying live API liveness, database latency, and raw JSON probe payloads.
- **Centralized Typed API Client (`frontend/src/api/client.ts`)**: Reads `VITE_API_BASE_URL` with typed error handling and endpoint mappings.

---

## 3. Directory Structure Created

```text
FDR_Sentinel/
├── Context.md                                    # Preserved source document
├── FDR_Sentinel_PRD.md                           # Preserved source document
├── FDR_Sentinel_Project_Synopsis.md              # Preserved source document
├── FDR_Sentinel_SRS.md                           # Preserved source document
├── FDR_Sentinel_Seven_Module_Prototype_Blueprint.docx # Preserved untouched (locked)
├── Readme.md                                     # Legacy readme
├── README.md                                     # Complete new project readme
├── .gitignore                                    # Secrets, venv, node_modules, logs
├── .env.example                                  # Comprehensive configuration template
├── Doc/
│   └── module1.md                                # This Module 1 summary
├── docs/
│   ├── module1.md
│   ├── architecture/
│   │   └── system_overview.md
│   └── development/
│       └── getting_started.md
├── scripts/
│   ├── dev.ps1                                   # Local dev server launcher
│   └── test.ps1                                  # Unified test runner
├── backend/
│   ├── pyproject.toml                            # Python project config & dependencies
│   ├── alembic.ini                               # Alembic migration configuration
│   ├── alembic/
│   │   ├── env.py                                # Dynamic DB URL & model discovery
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                               # FastAPI application entrypoint
│   │   ├── core/                                 # Settings & security constants
│   │   ├── db/                                   # SQLAlchemy session, engine, base
│   │   ├── common/                               # Common schemas & exception handlers
│   │   ├── api/v1/                               # Versioned routing & health probes
│   │   └── modules/                              # Domain modules (auth, institutions,
│   │                                             # instruments, audit)
│   ├── scripts/
│   │   └── init_db.py                            # Database seed & test data populator
│   └── tests/
│       ├── conftest.py                           # Pytest fixtures & isolated in-memory DB
│       ├── test_health.py                        # Health & readiness probe tests
│       └── test_modules.py                       # Integration tests for domain modules
└── frontend/
    ├── package.json                              # Vite, React, Tailwind v4, Vitest
    ├── vite.config.ts                            # Path alias & @tailwindcss/vite
    ├── tsconfig.json & tsconfig.app.json         # Strict TypeScript configuration
    ├── index.html                                # Inter typography & SEO metadata
    └── src/
        ├── app/                                  # App, router, route pages
        ├── components/                           # Reusable UI (Badge, Card, Button,
        │                                         # StatusIndicator, Header, Sidebar)
        ├── layouts/                              # Main application shell
        ├── features/                             # Domain feature components
        ├── api/                                  # Centralized API client & endpoints
        ├── hooks/                                # useHealth custom hook
        ├── lib/                                  # utils (formatINR, formatDate, cn)
        └── types/                                # Core domain TypeScript interfaces
```

---

## 4. Verification and Execution Results

### 4.1 Backend Pytest Suite
Ran command: `pytest backend/tests -v`
```text
backend/tests/test_health.py::test_root_welcome PASSED
backend/tests/test_health.py::test_liveness_probe PASSED
backend/tests/test_health.py::test_liveness_alias_healthz PASSED
backend/tests/test_health.py::test_readiness_probe_success PASSED
backend/tests/test_health.py::test_readiness_alias_readyz PASSED
backend/tests/test_modules.py::test_auth_roles_endpoint PASSED
backend/tests/test_modules.py::test_auth_session_bootstrap PASSED
backend/tests/test_modules.py::test_create_and_list_institution PASSED
backend/tests/test_modules.py::test_create_and_summarize_instruments PASSED
backend/tests/test_modules.py::test_audit_trail_listing PASSED

10 passed in 0.11s
```

### 4.2 Frontend Vitest Suite
Ran command: `npm test`
```text
✓ src/app/__tests__/App.test.tsx (3 tests) 116ms

Test Files  1 passed (1)
     Tests  3 passed (3)
```

### 4.3 Frontend Production Bundle Build
Ran command: `npm run build`
```text
vite v8.3.5 building client environment for production...
✓ 1963 modules transformed.
dist/index.html                   1.05 kB
dist/assets/index-BPA-OYlW.css   31.91 kB
dist/assets/index-B8WN_CbM.js   382.81 kB
✓ built in 430ms
```

### 4.4 Live API Endpoints Verification
Ran live server queries against running FastAPI uvicorn daemon:
- **Liveness (`/api/v1/health/live`)**: Status `alive`, Service `FDR Sentinel`, Version `0.1.0`.
- **Readiness (`/api/v1/health/ready`)**: Status `ready`, is_ready `true`, Database `connected`, Dialect `sqlite`, Latency `0.36ms`.
- **Instruments Summary (`/api/v1/instruments/summary`)**: Total instruments `3`, Total deposit value `7,500,000 INR`.

---

## 5. Next Steps for Prompt 2

With the foundational modular monolith, centralized API layer, and database ORM operational:
1. **Module 2: Complete FDR Submission & Verification Lifecycle**: Implement multi-step submission wizard, file upload handling with SHA-256 integrity hashing, and scrutiny review workflow.
2. **Lineage Tracking**: Preserving historical chains across renewals, replacements, and roll-overs without overwriting past certificates.
3. **Automated Validity & Maturity Scheduling**: Rule engine for configurable reminder triggers (90d, 60d, 30d, 15d).
