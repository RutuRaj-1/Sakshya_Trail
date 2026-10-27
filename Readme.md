# SakshyaTrail — Security Deposit & FDR Lifecycle Integrity Platform

<div align="center">

<img src="./SakshyaTrail%20Security%20Logo.png" alt="SakshyaTrail Logo" width="240" style="margin-bottom: 12px;" />

### *Every Record. Every Decision. Every Trail of Evidence.*

**All India Council for Technical Education (AICTE) Regulation Bureau**  
**Smart India Hackathon (SIH) 2026 · Problem Statement ID: 26265**  
*Theme: Smart Automation · Streamline of Security Deposit / FDR Portal*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4.0-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Pytest](https://img.shields.io/badge/Pytest-539%20Passed-success.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Vitest](https://img.shields.io/badge/Vitest-94%20Passed-success.svg?logo=vitest&logoColor=white)](https://vitest.dev/)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20Regulatory-blue.svg)](#)

</div>

---

## 1. Executive Summary

**SakshyaTrail** is an enterprise-grade sovereign digital governance and cryptographic lifecycle integrity platform built specifically for the **AICTE Regulation Bureau**.

Under statutory regulations (AICTE Approval Process Handbook), technical education institutions across India are mandated to maintain Fixed Deposit Receipts (FDRs) pledged jointly in favor of the Council as security deposits against institutional establishment, program expansion, and compliance covenants.

Historically, this critical financial safeguard suffered from significant structural vulnerabilities:
1. **Physical Custody Risks**: Paper deposit certificates scattered across regional offices, exposed to loss, physical decay, or unverified custody.
2. **Lien & Maturity Blindspots**: Lack of automated tracking for term expiries, bank mergers, or premature encashments without Council knowledge.
3. **Evidence & Trust Ambiguity**: Difficulty verifying genuine banking gateway confirmations versus self-declared photocopies or forged certificates.
4. **Discharge Vulnerabilities**: Informal release approvals lacking server-enforced dual-officer maker-checker validation and non-repudiable audit trails.

**SakshyaTrail** replaces fragmented paper workflows with an end-to-end, multi-tenant digital custody platform. It provides **4-tier evidentiary trust hierarchy (L0–L3)**, **automated OCR intake**, **deterministic cross-source rule validation**, **continuous maturity monitoring**, **server-enforced 10-point release gates**, an **Executive Command Center cockpit**, and a **tamper-evident SHA-256 cryptographic hash-chained audit ledger**.

---

## 2. Key Architectural Innovations

```
                                      SAKSHYATRAIL SYSTEM ARCHITECTURE
   
   +----------------------------------------------------------------------------------------------------+
   |                                      PUBLIC LANDING & AUTH PORTAL                                  |
   |   - Expressive Public Landing Page (9 Workflow Stages, Trust Ledger, Capability Matrix, FAQ)       |
   |   - Argon2id Password Hashing, Signed HTTP-Only JWT Sessions, SIH Evaluator 1-Click Autofill       |
   +-------------------------------------------------+--------------------------------------------------+
                                                     |
                                                     v
   +-------------------------------------------------+--------------------------------------------------+
   |                         MODULE 1: CORE FOUNDATION & MULTI-TENANT RBAC                              |
   |   - 7 Application Roles (Admin, Authority, Branch Head, Scrutiny, Finance, Auditor, Institution)    |
   |   - Strict Multi-Tenant Institutional Isolation (Colleges strictly scoped to their own records)     |
   |   - Statutory Institution & FDR Instrument Registry (High-precision Numeric(18,2) storage)        |
   +-------------------------------------------------+--------------------------------------------------+
                                                     |
                     +-------------------------------+-------------------------------+
                     |                               |                               |
                     v                               v                               v
   +---------------------------------+  +----------------------------+  +-------------------------------+
   |      MODULE 2: INTAKE & OCR     |  |    MODULE 3: VALIDATION    |  |  MODULE 4: TRUST LEDGER       |
   | - Multi-version Document Vault  |  | - 25+ Deterministic Rules  |  | - 4-Tier Trust: L0 -> L3      |
   | - SHA-256 Hash Deduplication    |  | - Discrepancy Scrutiny     |  | - Direct Host-to-Host Adapters|
   | - Tesseract OCR Text Extraction |  | - Priority Scoring (0-100) |  | - Simulated Gateway Tagger    |
   | - Mandatory Document Checklist  |  | - Append-Only Observations |  | - Channel Health Probes       |
   +---------------------------------+  +----------------------------+  +-------------------------------+
                     |                               |                               |
                     +-------------------------------+-------------------------------+
                                                     |
                                                     v
   +-------------------------------------------------+--------------------------------------------------+
   |                  MODULE 5: LIFECYCLE MONITORING & RENEWAL LINEAGE TREES                            |
   |   - Automated Daily Maturity Evaluator (ACTIVE -> EXPIRING_SOON [<=90d] -> EXPIRED)               |
   |   - Parent-Child Succession Trees for Reinvestments, Rollovers, and Split Replacements             |
   |   - Multi-Channel Escalation Alerts (90d, 60d, 30d, 15d, 7d, 0d Expiry Notices)                   |
   +-------------------------------------------------+--------------------------------------------------+
                                                     |
                                                     v
   +-------------------------------------------------+--------------------------------------------------+
   |                     MODULE 6: SERVER-SIDE RELEASE GATE & MAKER-CHECKER                             |
   |   - Non-Bypassable 10-Point Release Gate Evaluation (Server-Side Logic Only)                       |
   |   - Strict Dual-Officer Maker-Checker Workflow (Scrutiny Recommends -> Competent Authority Orders)  |
   |   - Discharge Orders, Partial Refunds, and Bank-Side Settlement Reconciliation                     |
   +-------------------------------------------------+--------------------------------------------------+
                                                     |
                                                     v
   +-------------------------------------------------+--------------------------------------------------+
   |              MODULE 7: EXECUTIVE COMMAND CENTER & TAMPER-EVIDENT AUDIT CHAIN                       |
   |   - Executive Cockpit & Metric Dictionary (PRD-FR-070 to FR-077) with Explainable Urgency Triage   |
   |   - Unified Multi-Dimensional Search across Instruments, Cases, Institutions, and Audit History     |
   |   - Operational Reports Desk with Formula-Injection-Defended CSV & PDF Export Generation           |
   |   - Tamper-Evident SHA-256 Forward-Linked Cryptographic Hash Chain with Replay Verification Screen |
   +----------------------------------------------------------------------------------------------------+
```

---

## 3. The 7 Core Application Modules

| Module | Name | Primary Regulatory Function | Security & Compliance Guarantees |
| :--- | :--- | :--- | :--- |
| **Module 1** | **Authoritative Registry & Multi-Tenant RBAC** | Single register for statutory FDR instruments, joint liens, and institutions across 7 role tiers. | Strict record-level multi-tenant isolation; non-destructive deactivation; Argon2id password security with mandatory rotation. |
| **Module 2** | **Document Intake, OCR & Vault** | Ingests deposit receipts, joint lien letters, and bank letters with OCR text extraction. | Cryptographic SHA-256 file hashing; versioned immutable storage; policy-driven mandatory completeness checklist. |
| **Module 3** | **Validation Engine & Scrutiny Review** | Deterministic 25+ business rule checks detecting value mismatches, bank discrepancies, and date anomalies. | Objective 0–100 urgency priority scoring; append-only officer observations; advisory AI/OCR bounds. |
| **Module 4** | **Trust Ledger & Channel Verification** | Governs tiered evidentiary trust: **L0 (Declared)** $\rightarrow$ **L1 (Doc-Consistent)** $\rightarrow$ **L2 (Officer-Verified)** $\rightarrow$ **L3 (Authorized Response)**. | Distinct simulated vs live banking gateway channels; synthetic responses visibly tagged with `SIMULATED` badge; channel health probes. |
| **Module 5** | **Lifecycle Monitoring & Renewal Lineage** | Tracks 90/60/30-day maturity windows; records replacement FDRs with parent-child lineage trees. | Automated background schedulers; prevents orphan replacement records; historical preservation of mature terms. |
| **Module 6** | **Release Gate & Maker-Checker Workflow** | Enforces statutory discharge requirements before any security deposit is released or refunded. | **Server-side 10-point gate**: Scrutiny Officer cannot approve release; Competent Authority cannot act without valid checklist; zero UI bypass shortcuts. |
| **Module 7** | **Command Center, Reports & Tamper-Evident Audit** | Executive situational cockpit, unified search, operational reporting, and audit replay. | **Cryptographic SHA-256 hash chaining**: each audit event binds the hash of the preceding event ($H_n = \text{SHA256}(H_{n-1} + E_n)$); replayable integrity verification screen. |

---

## 4. Design System: Structured Brutalism & Civic Ledger

SakshyaTrail adheres strictly to the **Civic Ledger Design System** documented in [Design.md](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/Design.md):

* **Civic Ledger Palette**:
  - **Navy** (`#123B5D`) — Primary action surfaces and prominent headers.
  - **Deep Ink** (`#0D2538`) — Authenticated sidebar, hero banners, and authoritative text.
  - **Evidence Teal** (`#0F766E`) — Interactive accents, verified badges, and active sidebar border indicator.
  - **Heritage Gold** (`#C69A48`) — Strategic milestone accents; *strictly never used as small text on light backgrounds*.
  - **Warm Paper** (`#F5F4EF`) — Primary application background; eliminates harsh sterile glare.
  - **White** (`#FFFFFF`) — Solid opaque surface for data tables, forms, and cards.
  - **Subtle Divider** (`#C9D3DB`) & **Visible Border** (`#8799A9`) — Clear structural container boundaries.
* **Structured Brutalism Principles**:
  - Restrained physical corner radii (`rounded-[8px]` for controls, `rounded-[10px]` for cards).
  - 1px visible structural borders on all data containers; 2px boundaries reserved exclusively for active/selected items.
  - Zero translucent glass behind dense tables, financial figures, audit logs, or release checklists.
* **Selective Glassmorphism**:
  - `.st-glass-panel` treatment applied strictly to elevated floating surfaces (sticky landing navbar, modal dialog overlays) with solid white fallback for browsers without backdrop-filter support.
* **Typography**:
  - **IBM Plex Sans** for UI hierarchy, buttons, forms, and data grids.
  - **IBM Plex Mono** with tabular numerals (`font-variant-numeric: tabular-nums`) for currency amounts (`₹`), SHA-256 digests, FDR references, and block sequence numbers.

---

## 5. Technology Stack

### Backend Architecture
- **Language & Runtime**: Python 3.11+ (tested on Python 3.11, 3.12, and 3.14.2).
- **Web Framework**: FastAPI (high-concurrency ASGI with Pydantic v2 schemas).
- **ORM & Database Engine**: SQLAlchemy 2.0 (Declarative Base, TimestampMixin, optimistic concurrency versioning).
- **Database Support**:
  - **SQLite** (zero-config, high-performance embedded local engine: `fdr_sentinel.db`).
  - **PostgreSQL** (production enterprise engine via `psycopg` v3 binary driver).
- **Database Migrations**: Alembic.
- **Security & Cryptography**:
  - Password Hashing: `passlib` with `argon2-cffi` (memory-hard, GPU-resistant).
  - Sessions: Signed JSON Web Tokens (JWT) via `python-jose` stored in `HttpOnly`, `SameSite=Lax`, `Secure` cookies.
  - Audit Ledger: Cryptographic SHA-256 sequential state linking.
- **Reporting & Exports**: Native streaming CSV generator with formula-injection mitigation (`=`, `+`, `-`, `@` escaping) and ReportLab PDF compilation.

### Frontend Architecture
- **Framework**: React 19 (Hooks, Context, Suspense).
- **Language**: TypeScript 5.7 (strict mode, zero `any` in core models).
- **Build Tool**: Vite 8 (Hot Module Replacement, production chunk optimization, sub-700ms builds).
- **Styling**: Tailwind CSS v4 (`@theme` token definitions, native CSS variables).
- **Client Routing**: React Router v7 with RBAC `ProtectedRoute` guards and post-login path preservation.
- **Icons**: Lucide React.
- **Typography Engine**: Google Fonts CDN (`IBM Plex Sans` + `IBM Plex Mono`).

---

## 6. Directory Structure

```text
FDR_Sentinel/
├── SakshyaTrail Security Logo.png            # Official high-resolution brand logo
├── Readme.md                                 # Complete project documentation & guide
├── project.md                                # End-to-end technical walkthrough
├── Design.md                                 # Civic Ledger design system specifications
├── Context.md                                # Problem statement & statutory context
├── FDR_Sentinel_PRD.md                       # Product Requirements Document
├── FDR_Sentinel_SRS.md                       # Software Requirements Specification
├── .env.example                              # Master environment variables template
├── backend/
│   ├── pyproject.toml                        # Backend build dependencies & pytest configuration
│   ├── alembic.ini                           # Alembic database migration configuration
│   ├── alembic/                              # Migration revisions (versioned schemas)
│   ├── app/
│   │   ├── main.py                           # FastAPI application entrypoint, CORS, routers
│   │   ├── core/
│   │   │   ├── config.py                     # Pydantic Settings (env validation, secrets)
│   │   │   └── security.py                   # Argon2id hashing, JWT encoding/decoding
│   │   ├── db/
│   │   │   ├── session.py                    # Engine creation, scoped session generator
│   │   │   └── base.py                       # SQLAlchemy DeclarativeBase & TimestampMixin
│   │   ├── common/
│   │   │   ├── envelopes.py                  # Standardized API response envelopes
│   │   │   └── exceptions.py                 # Custom HTTP exception hierarchy
│   │   ├── api/v1/
│   │   │   ├── router.py                     # Central v1 endpoint aggregation
│   │   │   └── health.py                     # Liveness and DB latency readiness probes
│   │   └── modules/
│   │       ├── auth/                         # User models, RBAC dependencies, sessions
│   │       ├── institutions/                 # College registry, AISHE codes, nodal contacts
│   │       ├── instruments/                  # FDR registry, validation, duplicate warnings
│   │       ├── documents/                    # File vault, SHA-256 deduplication, OCR service
│   │       ├── validation/                   # 25+ business rules, discrepancies, observations
│   │       ├── verification/                 # Trust ledger (L0-L3), simulated/live banking
│   │       ├── lifecycle/                    # Maturity scheduler, renewals, lineage trees
│   │       ├── release/                      # Release gate, 10-point checklist, maker-checker
│   │       ├── dashboard/                    # Command center aggregations, reports, metrics
│   │       └── audit/                        # Tamper-evident SHA-256 chained audit ledger
│   ├── scripts/
│   │   ├── bootstrap_admin.py                # CLI script to provision system admin
│   │   └── init_db.py                        # Idempotent synthetic database seed script
│   └── tests/                                # 476 comprehensive automated backend tests
└── frontend/
    ├── package.json                          # Vite, React 19, Tailwind v4, Vitest scripts
    ├── vite.config.ts                        # Vite configuration & native /api reverse-proxy
    ├── tsconfig.json                         # TypeScript compiler options
    ├── index.html                            # Root HTML template, SEO, IBM Plex fonts
    └── src/
        ├── index.css                         # Tailwind v4 theme, tokens, glassmorphism
        ├── layouts/
        │   └── MainLayout.tsx                # Authenticated application shell & gutters
        ├── components/
        │   ├── common/                       # Button, Badge, Card, StatusIndicator
        │   └── navigation/                   # Header (probes & user), Sidebar (RBAC items)
        ├── features/
        │   ├── auth/                         # AuthContext, ProtectedRoute, auth utilities
        │   ├── commandCenter/                # Cockpit widgets, priority desk, reports
        │   ├── institutions/                 # Institution directory, modals, tables
        │   ├── instruments/                  # FDR instrument cards, forms, tables
        │   └── lifecycle/                    # Notification history, lineage tree viewer
        └── app/
            ├── App.tsx                       # Root component with providers
            ├── router.tsx                    # Client-side router configuration
            └── routes/                       # All 15 operational page views
```

---

## 7. Quick Start & Installation Guide

### Prerequisites
- **Python**: Version 3.11 or higher.
- **Node.js**: Version 18.x or higher (Node 20+ recommended).
- **Package Managers**: `pip` (Python) and `npm` (Node).
- **Git**.

---

### Step 1: Clone Repository & Configure Environment

```bash
git clone https://github.com/RutuRaj-1/FDR_Sentinal.git
cd FDR_Sentinel

# Copy environment configuration
cp .env.example backend/.env
```

The default `.env` is configured for immediate zero-config development using embedded SQLite.

---

### Step 2: Backend Setup & Database Initialization

```bash
cd backend

# Create and activate virtual environment
# Windows (PowerShell):
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
# python3 -m venv .venv
# source .venv/bin/activate

# Install backend dependencies
pip install -e .

# Run database migrations
alembic upgrade head

# Seed synthetic regulatory data (Institutions, FDRs, Users, Audit Chains)
python scripts/init_db.py

# Launch FastAPI backend server (Runs on port 8000)
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

*Backend interactive OpenAPI documentation will be accessible at: `http://127.0.0.1:8000/docs`.*

---

### Step 3: Frontend Setup & Development Server

Open a second terminal window:

```bash
cd frontend

# Install frontend dependencies
npm install

# Launch Vite development server (Runs on port 5173 with proxy to backend)
npm run dev
```

*The SakshyaTrail application will be accessible at: `http://localhost:5173/`.*

---

---

## 8. Synthetic Demonstration Environment (20 Institutions, 10 Pune / 10 Mumbai, 80 FDRs)

SakshyaTrail incorporates a dedicated, isolated, and fully deterministic **Synthetic Demonstration Environment** designed for reproducible SIH evaluation without contaminating or altering the persistent development database.

### 8.1 Dedicated Database Architecture & Safety Invariants

- **Isolated Target Database**: Configured via `SAKSHYATRAIL_DEMO_DATABASE_URL` (defaults to `sqlite:///./fdr_sentinel_demo.db`).
- **Persistent Data Protection**: The primary development database (`fdr_sentinel.db`) is strictly guarded against destructive operations. Destructive reset commands (`--reset-demo`) assert that the target database explicitly contains `demo` in its path and will hard-fail if targeted against the persistent development database.
- **Append-Only Audit Guard**: Audit events are cryptographically chained ($H_n = \text{SHA256}(H_{n-1} + E_n)$) and protected by SQLite database triggers prohibiting `UPDATE` or `DELETE`. Demonstration resets re-initialize a fresh schema rather than modifying historical ledger rows.

### 8.2 Seeder CLI Workflow

```bash
cd backend
.\.venv\Scripts\Activate.ps1

# 1. Dry Run Mode: Inspect planned entities and validations with ZERO database modifications
python scripts/demo_seed.py --dry-run

# 2. Apply Mode: Reconcile or provision the 20 institutions, 80 FDRs, and nine-stage workflows
python scripts/demo_seed.py --apply

# 3. Verify Mode: Assert exact counts, foreign key integrity, and audit chain continuity
python scripts/demo_seed.py --verify

# 4. Clean Reset (Demo DB Only): Safely re-initialize the isolated demonstration schema
python scripts/demo_seed.py --reset-demo --apply
```

### 8.3 The 20 Synthetic Institutions Directory

All 20 institutions are visibly labelled `DEMO DATA — SYNTHETIC INSTITUTION` and use reserved example domains.

#### Group A — Pune Jurisdiction (10 Institutions)

| Code | Legal Name / Display Name | City | State | Nodal Officer Account |
| :--- | :--- | :--- | :--- | :--- |
| `DEMO-PUN-001` | DEMO — Deccan Valley Institute of Technology (SYNTHETIC) | Pune | Maharashtra | `nodal.pun001@example.com` |
| `DEMO-PUN-002` | DEMO — Sahyadri Applied Sciences College (SYNTHETIC) | Pune | Maharashtra | `nodal.pun002@example.com` |
| `DEMO-PUN-003` | DEMO — Mula-Mutha Engineering Institute (SYNTHETIC) | Pune | Maharashtra | `nodal.pun003@example.com` |
| `DEMO-PUN-004` | DEMO — Hinjawadi School of Technical Studies (SYNTHETIC) | Pune | Maharashtra | `nodal.pun004@example.com` |
| `DEMO-PUN-005` | DEMO — Kothrud Institute of Applied Engineering (SYNTHETIC) | Pune | Maharashtra | `nodal.pun005@example.com` |
| `DEMO-PUN-006` | DEMO — Pashan College of Technology (SYNTHETIC) | Pune | Maharashtra | `nodal.pun006@example.com` |
| `DEMO-PUN-007` | DEMO — Baner Institute of Digital Engineering (SYNTHETIC) | Pune | Maharashtra | `nodal.pun007@example.com` |
| `DEMO-PUN-008` | DEMO — Hadapsar Technical Sciences College (SYNTHETIC) | Pune | Maharashtra | `nodal.pun008@example.com` |
| `DEMO-PUN-009` | DEMO — Pimpri Centre for Engineering Studies (SYNTHETIC) | Pune | Maharashtra | `nodal.pun009@example.com` |
| `DEMO-PUN-010` | DEMO — Warje Institute of Industrial Technology (SYNTHETIC) | Pune | Maharashtra | `nodal.pun010@example.com` |

#### Group B — Mumbai Jurisdiction (10 Institutions)

| Code | Legal Name / Display Name | City | State | Nodal Officer Account |
| :--- | :--- | :--- | :--- | :--- |
| `DEMO-MUM-001` | DEMO — Harbourview Institute of Technology (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum001@example.com` |
| `DEMO-MUM-002` | DEMO — Western Bay College of Engineering (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum002@example.com` |
| `DEMO-MUM-003` | DEMO — Sahar Institute of Applied Sciences (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum003@example.com` |
| `DEMO-MUM-004` | DEMO — Powai Technical Studies College (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum004@example.com` |
| `DEMO-MUM-005` | DEMO — Dadar Institute of Engineering (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum005@example.com` |
| `DEMO-MUM-006` | DEMO — Chembur Applied Technology College (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum006@example.com` |
| `DEMO-MUM-007` | DEMO — Borivali Centre for Technical Education (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum007@example.com` |
| `DEMO-MUM-008` | DEMO — Andheri Institute of Engineering Studies (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum008@example.com` |
| `DEMO-MUM-009` | DEMO — Goregaon Technical Sciences College (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum009@example.com` |
| `DEMO-MUM-010` | DEMO — Vikhroli College of Industrial Technology (SYNTHETIC) | Mumbai | Maharashtra | `nodal.mum010@example.com` |

### 8.4 The 80-Instrument Portfolio & 20 Scenario Categories

Each institution holds exactly 4 synthetic FDR instruments (80 total across Pune and Mumbai), covering 20 distinct statutory scenario categories:

1. **Draft FDRs**: Newly initiated deposit records pending submission (`DRAFT`).
2. **Submitted Instruments**: Registered records awaiting bureau scrutiny (`SUBMITTED`).
3. **Complete Evidence Vault**: Valid text-extractable PDFs with verified SHA-256 byte hashes.
4. **Missing Evidence Vault**: Instruments flagged for missing mandatory deposit certificate uploads.
5. **Amount / Date Discrepancies**: Discrepancies detected by the deterministic validation engine (e.g. certificate principal differs from declared).
6. **Suspected Duplicates**: Detected duplicate instruments requiring human reviewer scrutiny.
7. **Scrutiny Officer Provenance**: Preserved review observations, correction requests, and officer notes.
8. **Pending Bank Verification**: Dispatched verification requests awaiting channel response.
9. **Simulated Matching Bank Confirmations**: Simulated gateway responses confirming matching details.
10. **Simulated Mismatching Responses**: Gateway responses indicating deposit details discrepancy.
11. **Verification Timeouts**: Unresponsive banking channel simulated fallback states.
12. **Approaching Maturity (≤ 90 Days)**: Active instruments in the warning window triggering compliance reminders.
13. **Matured / Overdue Term**: Expired deposits evaluated by the business clock requiring reinvestment.
14. **Recorded Lifecycle Reminders**: Multi-tier notifications (90d, 60d, 30d, overdue) in the notification inbox.
15. **Successor Renewal Lineages**: Acyclic parent-child lineage records linking matured deposits to renewed receipts.
16. **Release Blocked by Mandatory Checklist**: Release applications blocked by active lien or incomplete evidence.
17. **Release Blocked by Open Discrepancies**: Release cases gated due to unresolved scrutiny findings.
18. **Awaiting Competent Authority Decision**: Verified cases pending statutory approval by `COMPETENT_AUTHORITY`.
19. **Approved Cases with Recorded Orders**: Cases with statutory approval and Finance Officer release order (`RELEASE_ORDER_RECORDED`).
20. **Executed Settlement & Closure**: Fully settled release cases with confirmed downstream bank actions and closure.

### 8.5 Live Database Metrics Inventory (`fdr_sentinel_demo.db`)

*Verified directly from the database via `python scripts/demo_seed.py --verify`:*

| Metric Category | Database Count | Statutory Verification Status |
| :--- | :--- | :--- |
| **Active Synthetic Institutions** | **20** | Exactly 10 in Pune, 10 in Mumbai, 0 in other cities [PASS] |
| **Synthetic FDR Instruments** | **80** | Exactly 4 per institution, Numeric(18,2) exact precision [PASS] |
| **Document Files & Versions** | **80** | SHA-256 hashed, watermarked, deterministic text extracted [PASS] |
| **Deterministic Validation Findings**| **8** | Discrepancies (amount, date) and duplicate flags [PASS] |
| **Bank Verification Requests** | **16** | Simulated match, mismatch, and timeout requests [PASS] |
| **Lifecycle Evaluations** | **12** | Active, Expiring-Soon (≤90d), and Matured states [PASS] |
| **Predecessor-Successor Lineages** | **4** | Valid renewal chains, anti-cycle enforced [PASS] |
| **Release & Discharge Cases** | **20** | Incomplete, Blocked, Approved, and Settled cases [PASS] |
| **Statutory Release Decisions** | **8** | Exclusive to `COMPETENT_AUTHORITY` [PASS] |
| **Release Orders Recorded** | **8** | Exclusive to `FINANCE_OFFICER` [PASS] |
| **Cryptographic Audit Events** | **106** | Complete SHA-256 forward-linked chain verified [PASS] |

### 8.6 Evidentiary & Integration Limitations

1. **PDF Text Extraction vs. OCR**: Deterministic text extraction parses digitally generated PDFs containing text layers. It does not perform optical character recognition (OCR) on rasterized scans.
2. **Simulated Host-to-Host Banking Gateways**: Bank verification requests and responses are simulated through internal adapters. Simulated confirmations are visibly flagged and cannot establish Level-3 bank confirmation without authorized external cryptographic tokens.
3. **Simulated Telecommunications**: Notification dispatches (Email, SMS, WhatsApp) record delivery state events in the database inbox without invoking live external telecommunication gateways.

---

## 9. Pre-Configured Demo Accounts (1-Click Autofill)

On the Sign In page (`/login`), click any role card under **"SIH Evaluator Demo Accounts"** to autofill verified credentials:

| Role Code | Official Email | Default Password | Primary Portal Permissions |
| :--- | :--- | :--- | :--- |
| `SYSTEM_ADMIN` | `admin@aicte-india.org` | `AdminPassword@2026` | Bureau administration, user provisioning, cryptographic audit chain verification. |
| `SCRUTINY_OFFICER` | `scrutiny.verma@aicte-india.org` | `OfficerPassword@2026` | Discrepancy review queue, L2 officer verification, scrutiny observations. |
| `BRANCH_HEAD` | `branch.head.north@aicte-india.org` | `BranchPassword@2026` | Regional oversight, queue reassignment, operational reporting, audit review. |
| `COMPETENT_AUTHORITY`| `authority.member@aicte-india.org`| `AuthorityPassword@2026`| **Exclusive statutory authority** to approve release/refund orders. |
| `FINANCE_OFFICER` | `finance.officer@aicte-india.org` | `FinancePassword@2026` | Financial reconciliation, deposit valuation, release order recording. |
| `AUDITOR` | `auditor.compliance@aicte-india.org`| `AuditorPassword@2026` | **Strictly read-only access**: audit chain verification, evidence pack export. |
| `INSTITUTION_USER` (Pune) | `nodal.pun001@example.com` | `NodalPassword@2026` | **Tenant-isolated**: Scoped strictly to Deccan Valley Institute (DEMO-PUN-001). |
| `INSTITUTION_USER` (Mumbai)| `nodal.mum001@example.com` | `NodalPassword@2026` | **Tenant-isolated**: Scoped strictly to Harbourview Institute (DEMO-MUM-001). |

---

## 10. Comprehensive Testing & Verification

The codebase includes an exhaustive test suite covering unit, integration, authorization, multi-tenancy, and cryptographic acceptance criteria.

### Run Backend Tests (Pytest)

```bash
cd backend
.\.venv\Scripts\Activate.ps1

# Run the complete test suite (527 tests)
pytest

# Run tests with execution duration and coverage summary
pytest -v --durations=10

# Run specific demonstration environment test suite
pytest tests/test_demo_environment_20_institutions.py -v
```
*Current test status: **527 passed**, 0 failed.*

### Run Frontend Tests (Vitest)

```bash
cd frontend

# Run all component and route integration tests (94 tests)
npm test

# Or run Vitest directly
npx vitest run
```
*Current test status: **94 passed**, 0 failed.*

### Run Static Type Check & Production Bundle Build

```bash
cd frontend

# Verify TypeScript type checking (0 errors)
npx tsc -b

# Compile production bundle
npm run build
```
*Production build completes cleanly in ~680ms with 0 errors.*

---

## 10. Security Invariants & Cryptographic Guarantees

1. **Non-Repudiable SHA-256 Hash Chaining**: Every state transition writes an immutable audit record containing $H_n = \text{SHA256}(H_{n-1} + \text{canonical}(E_n))$. The database rejects any `UPDATE` or `DELETE` on the audit table. The integrity of the chain can be verified anytime from the `/audit` screen.
2. **Server-Side Release Gate**: An FDR can only be released when the server-side checklist confirms all statutory criteria: no active lien, maturity condition met, zero open high-severity discrepancies, and verified trust status. No UI client can bypass these checks.
3. **Maker-Checker Separation of Duties**: The Scrutiny Officer who recommends a release cannot approve it. The Competent Authority who approves cannot create the initial case.
4. **Multi-Tenant College Scoping**: Institutional users are bounded by row-level database filters. Any cross-institution query returns HTTP 403 Forbidden and writes an immediate security audit record.
5. **No Blind Trust / Simulation Transparency**: Automated OCR heuristics and simulated banking gateway responses are advisory. Synthetic responses are watermarked with an explicit `SIMULATED` badge and cannot promote an instrument to L3 trust without authorized response tokens.

---

## 11. Core REST API Endpoints Overview

| Method | Endpoint | Description | Permitted Roles |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Authenticate user & issue signed session cookie | Public |
| `GET` | `/api/v1/auth/me` | Fetch active authenticated identity & scoped permissions | Authenticated |
| `POST` | `/api/v1/auth/change-password` | Mandatory / elective password rotation | Authenticated |
| `GET` | `/api/v1/instruments` | List FDR instruments with multi-tenant scoping | Scoped by Role |
| `POST` | `/api/v1/instruments` | Register new FDR instrument with duplicate check | Admin, Officer, Institution |
| `GET` | `/api/v1/instruments/{id}` | Detailed FDR view with lineage, audit trail & documents | Scoped by Role |
| `GET` | `/api/v1/command-center/status-counts` | Aggregate KPI counts across bureau records | Bureau Roles |
| `GET` | `/api/v1/command-center/priority-queue` | Explainable priority triage queue (0–100 score) | Bureau Roles |
| `GET` | `/api/v1/command-center/search/instruments` | Unified multi-dimensional search with filter pills | All Authenticated |
| `GET` | `/api/v1/reports/{report_type}/csv` | Formula-injection-defended secure CSV export | Officer, Auditor, Admin |
| `GET` | `/api/v1/reports/{report_type}/pdf` | Official compliance PDF report generation | Officer, Auditor, Admin |
| `GET` | `/api/v1/audit/events` | Paginated immutable audit ledger query | Admin, Auditor, Branch Head, Authority |
| `POST` | `/api/v1/audit/verify-chain` | Cryptographic SHA-256 chain replay & tamper check | Admin, Auditor, Branch Head, Authority |
| `POST` | `/api/v1/release/cases/{id}/decision` | Record release approval, rejection, or return | Competent Authority Only |

---

## 12. Team & Project Information

- **Project**: SakshyaTrail (SIH 2026 Problem Statement ID: 26265)
- **Ministry / Regulatory Body**: All India Council for Technical Education (AICTE), Ministry of Education, Govt. of India
- **Theme**: Smart Automation
- **Team**: Ukdiche_Modak

For a complete architectural analysis, entity-relationship models, detailed walkthrough of all 7 modules, and evaluator demonstration script, refer to [project.md](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/project.md).
