# SakshyaTrail — Sidebar Information Architecture and End-to-End Lifecycle Integration
## Comprehensive Architectural Audit & Implementation Plan

**Date:** 2026-10-26  
**Repository:** `SakshyaTrail` (`FDR_Sentinel`)  
**Objective:** Refactor frontend navigation, establish a differentiated Overview vs. Command Center, implement an interactive Nine-Stage Lifecycle Tracker backed by persisted backend domain entities, and connect stage cards to active work queues without altering backend state machines or breaking trust boundaries.

---

## 1. Executive Summary & Codebase Health Audit

A thorough static and dynamic inspection of both `backend` (FastAPI / SQLAlchemy / SQLite) and `frontend` (React 18 / TypeScript / Vite / TailwindCSS / Vitest) was performed.

### Key Inspection Results:
1. **Existing Test Baseline:**
   - **Frontend:** All 7 test suites (50 tests) currently pass (`npm test -- --run`).
   - **Backend:** 33 test files covering Modules 1 through 7 pass.
2. **Module Completeness:**
   All seven functional modules have working backend endpoints and data models. However, the frontend currently suffers from:
   - **Flat, uncluttered-but-static sidebar navigation:** 13 flat items with hardcoded, decorative badges (`"Module 7"`, `"Core"`, `"Trust"`, `"Scrutiny"`), no group collapse, no mobile drawer, and a hardcoded Trust Hierarchy legend pinned to the bottom of the navigation bar.
   - **Disconnected drill-downs:** Cards on the Command Center (`StatusOverviewCards`) navigate to `/instruments?status=ACTIVE` or `?status=EXPIRING_SOON`, but `InstrumentsPage.tsx` ignores URL query parameters (`searchParams`) and the backend `Instrument.status` enum only supports `["DRAFT", "REGISTERED", "SUBMITTED", "RETURNED_FOR_CORRECTION"]`.
   - **Missing routes:** In `ReleaseCasesPage.tsx`, the "New Request" button links to `/release/new`, but `router.tsx` only matches `release/:id`, treating `"new"` as an ID and failing with a 404 API error.
   - **Marketing vs. Operational discrepancy:** The 9 lifecycle workflow stages are prominently documented on the public `LandingPage.tsx`, but completely absent from the authenticated application (`CommandCenterPage.tsx` and `InstrumentDetailPage.tsx`).
   - **Overlap between Overview (`/dashboard`) and Command Center (`/command-center`):** Both pages attempt to show KPI cards and charts without a crisp operational division of labor.

---

## 2. Phase 1 — Comprehensive Inspection of Current State

### 2.1 Capability Inventory Across All Seven Modules

| Module # | Module Name | Backend Models & Services | API Endpoints | Current Frontend Route | Frontend State & Completeness |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Module 1** | **Institutions & Instruments** | `Institution`, `Instrument`, `instruments/service.py` | `/api/v1/institutions`, `/api/v1/instruments`, `/api/v1/instruments/summary` | `/instruments`, `/institutions`, `/instruments/:id`, `/institutions/:id` | **Functional:** Lists, filters, creates instruments and institutions. <br>⚠️ *Gap:* Does not parse URL `searchParams` for status/maturity filters. |
| **Module 2** | **Documents & Evidence** | `Document`, `DocumentVersion`, `DocumentService`, `scanner.py`, `storage.py` | `/api/v1/instruments/{id}/documents`, `/api/v1/documents/{id}/versions/{vid}/content` | Tab inside `/instruments/:id` | **Partially integrated:** Upload, download, and SHA-256 byte verification are functional, but there is no dedicated top-level Document Hub or Evidence Scrutiny page. |
| **Module 3** | **Validation & Scrutiny** | `ValidationFinding`, `ValidationPolicyConfig`, `validation/engine.py` | `/api/v1/findings/queue`, `/api/v1/findings/{id}/status`, `/instruments/{id}/return-for-correction` | `/findings/queue` (`ReviewQueuePage`) | **Fully functional:** Scrutiny officer queue with rule findings, severity badges, and maker-checker status transitions. |
| **Module 4** | **Trust & Verification Desk** | `VerificationRequest`, `VerificationResponse`, `TrustAssessment`, `FieldProvenance` | `/api/v1/verification/instruments/{id}/trust`, `/verification/requests`, `/trust/l2-officer-decision` | `/verification`, `/verification/:id` (`TrustVerificationDeskPage`) | **Fully functional:** L0–L3 trust evaluation, simulated SFTP/API bank connectors, manual officer entry, hash provenance inspector. |
| **Module 5** | **Lifecycle & Renewal Lineage** | `LifecycleEvaluation`, `InstrumentLineage`, `LifecycleNotification`, `evaluation_service.py` | `/api/v1/lifecycle/instruments/{id}/evaluation`, `/lineage`, `/renew`, `/notifications/inbox` | Embedded in `/instruments/:id` and widgets in `/command-center` | **Fully functional:** Automated maturity calculation, reminder dispatcher, successor renewal drafting, and lineage continuity checks. No standalone `/lifecycle` route. |
| **Module 6** | **Release & Refund Cases** | `ReleaseRequest`, `ReadinessAssessment`, `ReadinessCheckResult`, `ReleaseOrder`, `ReleaseDecision` | `/api/v1/release/requests`, `/readiness`, `/decisions`, `/orders`, `/confirm-bank` | `/release`, `/release/:id` (`ReleaseCasesPage`, `ReleaseDetailPage`) | **Mostly functional:** Readiness checklist with blockers, 4-eye approval workflow. <br>⚠️ *Gaps:* Missing `/release/new` route and draft modal. |
| **Module 7** | **Command Center, Search & Audit** | `AuditEvent`, `AuditQueryService`, `DashboardService`, `MetricsDictionary` | `/api/v1/dashboard/command-center`, `/status-counts`, `/reports/*`, `/audit/events`, `/audit/verify` | `/command-center`, `/search`, `/reports`, `/audit` | **Fully functional:** Executive cockpit, unified query engine, streaming CSV/PDF reports, and SHA-256 hash-chain verification. |

### 2.2 Dashboard vs. Command Center Analysis

- **Current Dashboard (`/dashboard`):** Focuses on basic portfolio totals (`total_deposit_value`, `total_active_institutions`, `instruments_by_status`, and a simple list of recent instruments).
- **Current Command Center (`/command-center`):** Implements Module 7 operational telemetry: priority queue triage, maturity monitoring windows (30/60/90/180/365d), overdue work queue, bank channel health, completeness blockers, and month-wise maturity load.
- **Decision:** **Preserve both, with differentiated boundaries:**
  - **Overview (`/dashboard`):** High-level administrative portal. Displays statutory portfolio totals, institutional status, quick shortcuts, recent activities, and high-level trust distribution. Serves as the executive summary.
  - **Command Center (`/command-center`):** Active operational flight deck. Houses the **9-Stage Lifecycle Tracker**, real-time scrutiny and correction queues, release blocker triage, priority scoring, maturity forecasts, and direct action triggers for officers and competent authorities.

---

## 3. Phase 2 — Sidebar & Layout Information Architecture

### 3.1 Target Navigation Hierarchy & Role-Based Access Control (RBAC)

The sidebar will be restructured into four collapsible groups with strict RBAC visibility:

```
[WORKSPACE]
├── Overview                    → /dashboard          (All Authenticated Roles)
└── Command Center              → /command-center     (All Authenticated Roles; scoped for Institution)

[FDR LIFECYCLE]
├── Institutions & Instruments  → /instruments        (All Roles; Scoped to own institution for INSTITUTION_USER)
├── Documents & Evidence        → /documents          (All Roles; New Evidence Hub / Document Registry)
├── Validation & Review Queue   → /findings/queue     (SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD, CA) [Live Count Badge]
├── Trust & Verification        → /verification       (SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD, CA) [Live Count Badge]
├── Monitoring & Renewals       → /monitoring         (All Roles; Scoped maturity and lineage management)
└── Release / Refund Cases      → /release            (All Roles; Scoped request & decision management) [Live Count Badge]

[INTELLIGENCE & OVERSIGHT]
├── Unified Search              → /search             (All Roles)
├── Operational Reports         → /reports            (SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD, CA, AUDITOR)
└── Audit & Integrity           → /audit              (SYSTEM_ADMIN, AUDITOR, BRANCH_HEAD, CA)

[SYSTEM]
├── Institution Directory       → /institutions       (SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD, CA, AUDITOR)
├── Users & Access              → /users              (SYSTEM_ADMIN only)
├── Password Security           → /change-password    (All Authenticated Roles)
└── System Diagnostics          → /health             (SYSTEM_ADMIN, SCRUTINY_OFFICER, AUDITOR)
```

### 3.2 Live Badge Architecture (No Hardcoded Badges)
All static decorative badges (`"Module 7"`, `"Core"`, `"Trust"`, `"Scrutiny"`) will be eliminated. Badges will strictly display **live counts fetched from active backend APIs**:
1. **Validation & Review Queue:** Count of `OPEN` and `INVESTIGATING` findings from `/api/v1/findings/queue`.
2. **Trust & Verification:** Count of `PENDING` and `DISPATCHED` bank verification requests from `/api/v1/dashboard/verification-queue`.
3. **Monitoring & Renewals:** Count of instruments maturing within ≤ 90 days from `/api/v1/dashboard/status-counts` (`expiring_soon_count`).
4. **Release Cases:** Count of active cases in `SUBMITTED`, `UNDER_REVIEW`, or `READY_FOR_AUTHORITY` from `/api/v1/release/requests`.

### 3.3 UX & Accessibility Enhancements
- **Collapsible Groups:** Groups can be collapsed or expanded, with state remembered in `localStorage`. If an active route is within a collapsed group, an indicator will highlight the group header.
- **Relocation of Trust Hierarchy Legend:** The bottom-pinned Trust Hierarchy legend will be removed from `Sidebar.tsx` and placed in the **Command Center** header and on `InstrumentDetailPage.tsx`.
- **Mobile Responsive Navigation:** Add a hamburger trigger in `Header.tsx` and an accessible sliding off-canvas drawer on screens `< 1024px` (`lg`), complete with backdrop click and `Escape` key listeners.

---

## 4. Phase 3 — End-to-End Nine Lifecycle Stages Integration

The platform will present the 9 lifecycle stages coherently across the Command Center and Instrument Details:

```
[1. Register] ──▶ [2. Submit & Evidence] ──▶ [3. Validate] ──▶ [4. Verify] ──▶ [5. Monitor]
                                                                                   │
                 ┌─────────────────────────────────────────────────────────────────┴────────┐
                 ▼                                                                          ▼
         [6. Renew or Replace]                                                    [7. Release Readiness Gate]
                 │                                                                          │
                 ▼                                                                          ▼
         (Cycles back to 1/2)                                                         [8. Authorize]
                                                                                            │
                                                                                            ▼
                                                                                   [9. Close & Audit]
```

### 4.1 Specification of the 9 Display Stages

| Stage # & Display Label | Owning Module | Persisted Domain Entities & State Flags | Entry Condition | Exit Condition | Next Permitted Action | Blocking / Deferral Conditions | Target Route & Filtered Queue |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Register** | **Module 1** (Instruments) | `Instrument.status == 'DRAFT'`, `Instrument.created_at` | Institution or Officer creates new record. | Deposit parameters and certificate numbers saved. | Upload FDR certificate scan and bank advice. | Duplicate reference number warning without confirmation. | `/instruments/:id` or `/instruments?status=DRAFT` |
| **2. Submit & Attach Evidence** | **Module 2** (Documents) | `Document`, `DocumentVersion` (`processing_status == 'COMPLETED'`), `sha256_hash`, `Instrument.status in ['DRAFT', 'SUBMITTED']` | Draft instrument saved; awaiting evidence upload. | Mandatory FDR document uploaded, virus scanned, and form formally submitted (`SUBMITTED`). | Review automated validation findings. | Malware scan failure, unreadable file format, missing mandatory certificate. | `/documents?instrument_id=:id` or `/instruments/:id?tab=documents` |
| **3. Validate** | **Module 3** (Validation & Rules) | `ValidationFinding` (`status in ['OPEN', 'INVESTIGATING', 'RESOLVED', 'WAIVED']`), `severity` | Instrument submitted or field edited; post-save rule engine triggers. | All blocking discrepancies resolved or waived; or case returned for correction. | Scrutiny Officer resolves/waives findings or clicks "Return for Correction". | Open critical findings (amount mismatch, date order error, invalid bank). | `/findings/queue?instrument_id=:id` |
| **4. Verify** | **Module 4** (Trust Desk) | `VerificationRequest` (`status in ['PENDING', 'DISPATCHED', 'COMPLETED']`), `TrustAssessment` (`trust_level in ['L0_DECLARED', 'L1_DOCUMENT_CONSISTENT', 'L2_OFFICER_VERIFIED', 'L3_BANK_CONFIRMED']`) | Document validated; deposit requires independent officer or bank verification. | Officer verifies evidence (L2) or qualifying bank confirmation received (L3). | Dispatch electronic bank request or record manual officer verification. | Bank channel timeout, simulated adapter offline, unauthenticated response. *(Note: L3 is not required for progression if policy accepts L2)*. | `/verification/:id` |
| **5. Monitor** | **Module 5** (Lifecycle Scheduler) | `LifecycleEvaluation` (`maturity_stage in ['ACTIVE', 'MATURING_SOON', 'MATURED', 'EXPIRED']`), `due_condition` | Instrument formally registered (`REGISTERED`). | Instrument enters critical maturity window (≤ 90 days) or matures. | View days remaining; review automated reminder notifications. | Overdue institution compliance action. | `/monitoring?stage=ACTIVE` or `/instruments/:id?tab=lineage` |
| **6. Renew or Replace** | **Module 5** (Renewal Lineage) | `InstrumentLineage` (`relationship_type in ['RENEWAL', 'REPLACEMENT']`, `relationship_status == 'ACTIVE'`), Successor `Instrument` | Instrument reaches maturity window or requires early replacement. | Successor FDR drafted and linked with cryptographic continuity check. | Draft successor instrument; link lineage to predecessor. | Amount shortfall without authorization, non-matching institution tenancy. *(Skipped if case is destined for release)*. | `/monitoring?filter=renewals` or `/instruments/:id?tab=lineage` |
| **7. Release Readiness Gate** | **Module 6** (Readiness Assessment) | `ReleaseRequest` (`workflow_status in ['DRAFT', 'SUBMITTED', 'UNDER_REVIEW']`), `ReadinessAssessment` (`outcome in ['READY_FOR_APPROVAL', 'BLOCKED']`) | Institution/Officer files release, discharge, or refund request. | 100% mandatory checklist items pass; 0 blockers remaining (`READY_FOR_APPROVAL`). | Reviewer evaluates checklist blockers and recommends case to authority. | Active lien hold, open scrutiny finding, unverified deposit, minimum tenure not elapsed. *(Not applicable for active/renewed FDRs)*. | `/release/:id` |
| **8. Authorize** | **Module 6** (Authority Governance) | `ReleaseRequest` (`workflow_status == 'APPROVED'`), `ReleaseDecision` (`APPROVE`), `ReleaseOrder` | Case passes Release Gate and is recommended to Competent Authority. | Competent Authority signs sanction order and records formal release order. | Competent Authority records sanction number and signs approval. | Maker-checker segregation (scrutiny officer cannot approve; requires Competent Authority). | `/release/:id` |
| **9. Close & Audit** | **Module 6 & 7** (Discharge & Hash Chain) | `ReleaseRequest` (`workflow_status in ['RELEASE_ORDER_RECORDED', 'BANK_SIDE_ACTION_PENDING', 'CLOSED']`), `AuditEvent` (SHA-256 chain) | Release order issued; awaiting bank discharge execution. | Bank discharge verified, deposit closed, tamper-evident audit pack generated. | Officer confirms bank discharge; auditor verifies cryptographic hash chain. | Disputed bank disbursement, unbroken hash chain failure. | `/release/:id` or `/audit` |

### 4.2 Non-Linear / Branching Lifecycle Rules
- **No Forced Linear Flow:** Not every deposit passes through all 9 stages.
  - A deposit that undergoes continuous renewal loops through Stages `1 ➔ 2 ➔ 3 ➔ 4 ➔ 5 ➔ 6 ➔ 1...` indefinitely without entering Stages 7, 8, or 9.
  - A deposit that reaches end-of-term and is released moves from Stage 5 directly to Stage 7 (bypassing Stage 6).
- **Returned for Correction:** If Stage 3 reveals deficiencies, the case transitions to `RETURNED_FOR_CORRECTION`, returning control to the institution at Stage 1/2 without resetting historical provenance.
- **Explainable Progress Calculation:** Lifecycle completion will **never be shown as a fixed or misleading percentage** (e.g., "55% completed"). Instead, the UI will display a **Stage Progress Badge & Breadcrumb** indicating current state (e.g., `Stage 5: Monitored (Active)`, `Stage 3: Scrutiny Blocker`, or `Stage 7: Release Gate (2 Blockers)`).

---

## 5. Phase 4 — Command Center Cockpit Refactoring

### 5.1 Command Center Layout Architecture

The refreshed `/command-center` page will be organized into distinct operational zones:

1. **Flight Deck Header & Trust Legend:**
   - Operational context, scoped institution indicator, Metric Dictionary modal trigger, and manual aggregation refresh button.
   - Integrated **Trust Hierarchy Guide (L0–L3)** relocated from the sidebar.
2. **Interactive 9-Stage Lifecycle Tracker Matrix:**
   - 9 interactive stage cards displaying:
     - Real-time count of records in that stage.
     - Status indicator (Normal, Pending Action, Critical Blocker).
     - Single-click drill-down linking directly to the filtered queue or record.
3. **Operational Triage & Review Queues:**
   - **Explainable Priority Queue (PRD-FR-075):** Multi-factor priority score table with direct links to scrutiny actions.
   - **Overdue & Escalated Actions (PRD-FR-070c):** Flagging missed institution due dates and supervisor escalations.
   - **Release Blocker Triage (PRD-FR-070f):** Real-time list of release requests currently halted by gate criteria.
4. **Maturity & Channel Health Analytics:**
   - **Maturity Window Slider (PRD-FR-070b):** 30 / 60 / 90 / 180 / 365 days monitoring selector.
   - **Bank Verification Channel Health (PRD-FR-070d):** Health status of simulated SFTP, manual verification, and API adapters.
   - **Month-Wise Maturity Load (PRD-FR-076):** Annual distribution chart of maturing deposits.
5. **Cryptographic Audit Integrity Status Widget:**
   - Live banner showing recent audit events and the latest SHA-256 chain verification status (`PASS` or `TAMPER_DETECTED`).

### 5.2 Connecting Stage Cards to Active Filtered Queues

To fix the broken drill-downs, `InstrumentsPage.tsx` and query parameters will be updated:
- `/instruments?status=DRAFT` ➔ Shows intake records.
- `/instruments?maturity_indicator=EXPIRING_SOON` ➔ Connects to backend maturity filters.
- `/instruments?maturity_indicator=MATURED` ➔ Shows matured deposits awaiting renewal/release.
- `/findings/queue?status=OPEN` ➔ Directly opens the Module 3 scrutiny queue.
- `/release?status=READY_FOR_AUTHORITY` ➔ Opens the Competent Authority decision queue.

---

## 6. Phase 5 — Trust, Verification, and Release Safeguards

Strict adherence to PRD and statutory guardrails will be maintained:

1. **Evidentiary Trust Independence:**
   - Administrative status (`Instrument.status`), maturity stage (`LifecycleEvaluation.maturity_stage`), evidentiary trust (`Instrument.trust_level`), and release readiness (`ReadinessAssessment.assessment_outcome`) must remain decoupled.
   - `L0_DECLARED`: Raw self-declared institution data.
   - `L1_DOCUMENT_CONSISTENT`: Document OCR consistency check passed.
   - `L2_OFFICER_VERIFIED`: Human officer verified with attested rationale.
   - `L3_BANK_CONFIRMED`: Qualifying authorized bank host-to-host or signed response.
2. **Simulation Transparency:**
   - All simulated SFTP or synthetic bank responses must be prominently flagged with `[SIMULATED]` in the UI.
3. **No Automated Trust Escalation:**
   - OCR passes, SHA-256 hashes, or AI/deterministic validation passes **must never** automatically escalate trust to L2 or L3.
4. **Release Gate Boundary:**
   - The UI will enforce that no case with an active mandatory blocker can be approved.
   - Competent Authority approval, release order generation, bank disbursement, and case closure will remain distinct sequential states.
5. **Append-Only Immutability:**
   - Document versions, predecessor/successor lineage relationships, and audit log entries will remain immutable.

---

## 7. Step-by-Step Implementation Roadmap

```
┌────────────────────────────────────────────────────────────────────────┐
│ STEP 1: ROUTING, NEW PAGES & SHARED NAVIGATION LAYOUT                  │
│ • Fix router.tsx: Add /documents, /monitoring, and /release/new       │
│ • Update Header.tsx with mobile hamburger drawer                       │
│ • Refactor Sidebar.tsx into 4 collapsible groups with live count hooks  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│ STEP 2: FIX SEARCHPARAMS & FILTERED DRILL-DOWNS                        │
│ • Update InstrumentsPage.tsx to sync with URL searchParams             │
│ • Update backend instruments service if derived filters needed         │
│ • Connect StatusOverviewCards to proper target queues                  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│ STEP 3: NINE-STAGE LIFECYCLE TRACKER COMPONENT                         │
│ • Create NineStageLifecycleTracker.tsx component                       │
│ • Implement presentation mapping for stages 1 to 9                     │
│ • Integrate tracker into CommandCenterPage.tsx and InstrumentDetailPage│
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│ STEP 4: COMMAND CENTER & OVERVIEW DIFFERENTIATION                      │
│ • Relocate Trust Hierarchy Legend from Sidebar to Command Center       │
│ • Add Audit Chain Integrity live status card                           │
│ • Polish Overview (/dashboard) vs Command Center (/command-center)     │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│ STEP 5: DOCUMENTS & MONITORING HUBS                                    │
│ • Build DocumentsEvidencePage.tsx for Module 2                         │
│ • Build MonitoringRenewalsPage.tsx for Module 5                        │
│ • Ensure institution scoping is preserved                              │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│ STEP 6: VERIFICATION, TESTING & AUDIT                                  │
│ • Run unit tests, component tests, and TypeScript build checks         │
│ • Add regression test suite for sidebar, RBAC, and lifecycle tracker   │
│ • Perform end-to-end synthetic user walk-through                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Specific Code Changes Required

### 8.1 Frontend Changes

1. **`frontend/src/app/router.tsx`**:
   - Add route `/documents` ➔ `DocumentsPage` (Module 2 Hub).
   - Add route `/monitoring` ➔ `MonitoringPage` (Module 5 Maturity & Lineage Hub).
   - Add route `/release/new` ➔ `ReleaseDetailPage` (or create request modal).
   - Update navigation redirects.

2. **`frontend/src/components/navigation/Sidebar.tsx`**:
   - Reorganize items into the 4 defined categories (`Workspace`, `FDR Lifecycle`, `Intelligence & Oversight`, `System`).
   - Add collapsible sections with state persistence in `localStorage`.
   - Remove static decorative badges; introduce dynamic badges powered by live counts.
   - Remove the bottom-pinned `Trust Hierarchy` container.
   - Implement role-based item filtering.

3. **`frontend/src/components/navigation/Header.tsx`**:
   - Add a mobile hamburger menu toggle.
   - Implement responsive drawer integration with accessible backdrop.

4. **`frontend/src/features/lifecycle/components/NineStageLifecycleTracker.tsx`** *(New)*:
   - Visual stage pipeline and card grid rendering Stages 1 through 9.
   - Displays stage name, current status, active blocker count, and direct navigation button.
   - Handles non-linear and conditional paths (e.g. skipped stages, returned cases).

5. **`frontend/src/app/routes/CommandCenterPage.tsx`**:
   - Mount the `NineStageLifecycleTracker`.
   - Embed the relocated `Trust Hierarchy Guide`.
   - Connect live metrics to each lifecycle card.

6. **`frontend/src/app/routes/InstrumentsPage.tsx`**:
   - Connect `useSearchParams` to synchronize state with incoming query parameters (`?status=`, `?maturity_indicator=`, `?institution_id=`).

7. **`frontend/src/app/routes/ReleaseCasesPage.tsx` & `ReleaseDetailPage.tsx`**:
   - Support `/release/new` route to enable creation of draft release cases.

### 8.2 Backend Minor Alignment (If Necessary)

1. **`backend/app/modules/instruments/service.py`**:
   - Allow `maturity_indicator` filter query (`ACTIVE`, `EXPIRING_SOON`, `EXPIRED`) in `list_instruments` so that drill-downs from Command Center maturity cards filter records directly in the SQL query.

---

## 9. Verification & Quality Assurance Strategy

1. **Automated Unit & Integration Tests:**
   - Run Vitest frontend suite: `npm test -- --run` (ensure 100% pass rate).
   - Run Pytest backend suite: `pytest` (ensure 100% pass rate).
   - Add new tests in `frontend/src/features/lifecycle/__tests__/LifecycleTracker.test.tsx` verifying stage mapping and branching logic.
   - Add sidebar navigation tests in `frontend/src/components/navigation/__tests__/Sidebar.test.tsx` verifying role-based visibility.
2. **Type Safety & Build Checks:**
   - Execute TypeScript compiler: `npx tsc --noEmit`.
   - Execute Vite production build: `npm run build`.
3. **Tenancy & RBAC Verification:**
   - Verify that an `INSTITUTION_USER` cannot see administrative queue items (`Review Queue`, `User Admin`, `System Diagnostics`).
   - Verify that cross-institution query parameters are rejected by backend dependencies.
4. **Browser & Responsive Usability:**
   - Verify desktop (1280px+), tablet (768px–1024px), and mobile (<768px) viewport rendering.

---

*This document serves as the complete, authoritative implementation blueprint. Per instructions, no code changes have been executed yet.*
