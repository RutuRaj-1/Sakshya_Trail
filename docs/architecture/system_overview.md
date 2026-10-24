# Architecture Overview — FDR Sentinel

## System Architecture

```text
[ Browser / Frontend Client ]
       │ React 19 + TypeScript + Vite + Tailwind CSS v4
       │ Centralized Typed API Client
       ▼
[ FastAPI Backend Gateway ]
       │ /api/v1 (CORS, Lifespan, Pydantic Validation)
       ├── Health & Diagnostics Probe (/health/live, /health/ready)
       ├── Auth & RBAC Module (/auth/roles, /auth/session)
       ├── Institutions Module (/institutions)
       ├── Instruments Module (/instruments, /instruments/summary)
       └── Audit Module (/audit)
       │
       ▼
[ SQLAlchemy 2.x ORM & Alembic ]
       ├── PostgreSQL (Production / Staging)
       └── SQLite (Local zero-config dev / fast test harness)
```

## Evidence Provenance Hierarchy
As defined in `Context.md` and PRD §6:
- **L1: Declared** — Self-reported values submitted by the institution.
- **L2: Document-Consistent** — Extracted values confirmed matching submitted certificate documents.
- **L3: Officer-Verified** — Formally scrutinised and approved by an authorized AICTE scrutiny officer.
- **L4: Bank-Confirmed** — Directly confirmed via authorized bank communication / API token.
