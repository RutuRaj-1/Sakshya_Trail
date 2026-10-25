# Module 7: Command Center, Search, Reporting & Audit — Implementation Progress

**Project:** FDR Sentinel (SIH 2026 Problem Statement ID 26265: “Streamline of Security Deposit/FDR Portal”)  
**Module:** Module 7 — Command Center, Search, Reporting & Audit  
**Status:** Complete (All 5 of 5 Prompts Implemented & Verified)  

---

## Executive Summary

Module 7 establishes the operational intelligence, search, reporting, and regulatory audit command center for FDR Sentinel. Prompt 1 delivers the backend foundation, central metric definitions dictionary, parameterized database aggregation APIs, role-scoped search engine, operational priority queue, and reporting query services.

All calculations adhere strictly to the principle of database aggregation (parameterized SQL `func.count`, `func.sum`, `group_by`), multi-tenant isolation prior to computation, and complete separation between administrative workflow status, evidentiary trust level, maturity conditions, and release case outcomes.

---

## Prompt 1: Command Center Backend Foundation, Metric Definitions & Aggregation APIs

### 1. Implemented Files

| File Path | Description |
|:---|:---|
| `backend/app/modules/dashboard/metrics.py` | Central Metric Dictionary defining metric IDs, display labels, categories, PRD mappings, inclusion/exclusion rules, date conventions, filter parameters, authorization scopes, and unconfigured policy handling. |
| `backend/app/modules/dashboard/schemas.py` | Typed Pydantic request and response schemas for all 7 metric categories, dictionary queries, priority queues, and the consolidated command center cockpit overview. |
| `backend/app/modules/dashboard/dashboard_service.py` | Core aggregation service implementing status counts (A), maturity window (B), overdue/escalated work (C), verification queue (D), document completeness (E), release blockers (F), month-wise maturity load (G), and command center overview. |
| `backend/app/modules/dashboard/priority_service.py` | Implements PRD-FR-075: Operational priority queue with transparent factor weights (urgency 35%, discrepancy 25%, trust 20%, overdue 20%) and explainable composite scoring (0.0–100.0). |
| `backend/app/modules/dashboard/search_service.py` | Implements PRD-FR-071: Role-scoped search with keyword filtering, date ranges, amount bounds, allowlisted sorting fields, and pagination controls. |
| `backend/app/modules/dashboard/report_service.py` | Implements PRD-FR-074: Query services for pending verification, upcoming maturities, missing documents, and operational interventions reports. |
| `backend/app/modules/dashboard/history_service.py` | Implements PRD-FR-072 & PRD-FR-073: Unified historical timeline combining registration, document version history, append-only field provenance, and lifecycle evaluations. |
| `backend/app/modules/dashboard/audit_query_service.py` | Implements PRD-FR-091 & PRD-FR-093: Tamper-evident audit event queries, security violation retrieval, and cryptographic sequence integrity checks. |
| `backend/app/modules/dashboard/router.py` | FastAPI endpoint definitions mounted on `/api/v1/dashboard/*` with role enforcement, query parameter validation, and backward compatibility for Module 1 `/dashboard/summary`. |
| `docs/module-7-metric-dictionary.md` | Formal Markdown documentation of all metrics with calculation formulas, source entities, filters, and PRD requirement mappings. |
| `backend/tests/test_module7_prompt1_foundation.py` | Automated test suite covering all 12 required test scenarios. |

---

### 2. Implemented Endpoints

All endpoints are versioned under the `/api/v1/dashboard` prefix and require active JWT authentication:

| HTTP Method | Endpoint Path | Function & PRD Mapping | Authorized Roles |
|:---|:---|:---|:---|
| `GET` | `/api/v1/dashboard/summary` | Preserved Module 1 summary counts (backward compatible). | All authenticated users (scoped) |
| `GET` | `/api/v1/dashboard/metrics/dictionary` | Returns the central Metric Dictionary catalog (PRD-FR-077). | All authenticated users |
| `GET` | `/api/v1/dashboard/command-center` | Consolidated high-level command center cockpit overview. | All authenticated users (scoped) |
| `GET` | `/api/v1/dashboard/status-counts` | Category A: Active, Expiring Soon, Matured, Renewed, Released, Pending (PRD-FR-070a). | All authenticated users (scoped) |
| `GET` | `/api/v1/dashboard/maturity-window` | Category B: Maturity window counts, volume, bank/office breakdown & drilldown (PRD-FR-070b). | All authenticated users (scoped) |
| `GET` | `/api/v1/dashboard/overdue-escalated` | Category C: Overdue compliance actions and escalated cases (PRD-FR-070c). | Bureau roles; Institution Users (assignees redacted) |
| `GET` | `/api/v1/dashboard/verification-queue` | Category D: Outstanding bank verification requests, aging, source-unavailable cases (PRD-FR-070d). | Bureau roles; Institution Users (scoped) |
| `GET` | `/api/v1/dashboard/document-completeness` | Category E: Document checklist outcomes (present, missing, unreadable, awaiting) (PRD-FR-070e). | All authenticated users (scoped) |
| `GET` | `/api/v1/dashboard/release-blockers` | Category F: Release/refund requests obstructed by unmet mandatory checklist items (PRD-FR-070f). | All authenticated users (scoped) |
| `GET` | `/api/v1/dashboard/maturity-load` | Category G: Deterministic month-wise count and amount totals for calendar year (PRD-FR-076). | All authenticated users (scoped) |
| `GET` | `/api/v1/dashboard/priority-queue` | Category H: Urgency-ranked priority queue with explainable 0–100 score (PRD-FR-075). | Officers, Branch Heads, Authorities, Admins |
| `GET` | `/api/v1/dashboard/search` | Role-scoped multi-parameter search with allowlisted sorting & pagination (PRD-FR-071). | All authenticated users (scoped) |
| `GET` | `/api/v1/dashboard/reports/{report_type}` | Standardized operational report datasets: `PENDING_VERIFICATION`, `UPCOMING_MATURITIES`, `MISSING_DOCUMENTS`, `INTERVENTIONS` (PRD-FR-074). | Bureau roles; Institution Users (scoped) |
| `GET` | `/api/v1/dashboard/history/{instrument_id}` | Unified audit and event timeline per instrument (PRD-FR-072). | Authorized instrument owners / Bureau staff |
| `GET` | `/api/v1/dashboard/audit/integrity` | Verifies tamper-evident sequential integrity of the audit log chain (PRD-FR-093). | `SYSTEM_ADMIN`, `AUDITOR`, `BRANCH_HEAD` |

---

### 3. Metric Definitions Summary

| Metric ID | Display Label | PRD Ref | Exact Rule / Inclusion Criteria | Handling of Missing / Unconfigured Policy |
|:---|:---|:---|:---|:---|
| `MTR-STAT-ACTIVE` | Active Instruments | FR-070a | Status in `('ACTIVE', 'REGISTERED', 'VERIFIED')`, `maturity_date > today + window_days`, not released, no active renewal successor. | Defaults to 0 if no records match scope. |
| `MTR-STAT-EXPIRING-SOON` | Expiring Soon | FR-070a | Status in `('ACTIVE', 'REGISTERED', 'VERIFIED')`, `today <= maturity_date <= today + window_days`, not released, no active renewal successor. | Defaults `window_days` to 90 if unconfigured. |
| `MTR-STAT-MATURED` | Matured Instruments | FR-070a | `maturity_date < today`, not released, not renewed, not in draft/intake status. | Returns 0 if none match. |
| `MTR-STAT-RENEWED` | Renewed Predecessors | FR-070a | Predecessor instrument in active `instrument_lineages` with status `ACTIVE` and type in `('RENEWAL', 'REPLACEMENT')`. | Returns 0 if no lineage edges exist. |
| `MTR-STAT-RELEASED` | Released Instruments | FR-070a | Administrative status is strictly `RELEASED` after executed release order. | Returns 0 if none match. |
| `MTR-STAT-PENDING` | Pending Registration | FR-070a | Status in `('DRAFT', 'SUBMITTED', 'UNDER_SCRUTINY', 'UNDER_REVIEW', 'RETURNED_FOR_CORRECTION')`. | Returns 0 if none match. |
| `MTR-MAT-WINDOW` | Maturity Window | FR-070b | `COUNT(id)`, `SUM(amount)` where `start_date <= maturity_date <= end_date` and `status != 'RELEASED'`. | Requires valid date bounds; rejects start > end. |
| `MTR-OVERDUE-ESCALATED` | Overdue & Escalated Cases | FR-070c | `LifecycleEvaluation` with `is_overdue = True` or `is_escalated = True` plus active release cases returned for correction. | Returns 0 if no cases overdue. |
| `MTR-VERIF-QUEUE` | Verification Desk Queue | FR-070d | Verification requests in `('PENDING', 'REQUESTED', 'SENT')`, age distribution `<7d`, `7-14d`, `15-30d`, `>30d`, and source-unavailable cases. | Returns 0 queue count when clear. |
| `MTR-DOC-COMPLETENESS` | Document Completeness | FR-070e | Document scan states (`present`, `unreadable`, `awaiting`) and missing required categories under active policy. | Returns explicit `POLICY_UNCONFIGURED` rather than misleading 0. |
| `MTR-REL-BLOCKERS` | Release Gate Blockers | FR-070f | Active release cases where latest assessment has `blockers_count > 0` or outcome is `BLOCKED`. | Reports `policy_configured: false` if checklist profile is absent. |
| `MTR-MAT-LOAD` | Month-Wise Maturity Load | FR-076 | Deterministic SQL `GROUP BY EXTRACT(MONTH FROM maturity_date)` for requested calendar year. | Returns 0 counts for calendar months with no maturities. |
| `MTR-PRIORITY-QUEUE` | Operational Priority Queue | FR-075 | Composite Score: `0.35 * Urgency + 0.25 * Discrepancy + 0.20 * Trust + 0.20 * Overdue` (range 0.0–100.0). | Weights disclosed as transparent assumptions. |

---

### 4. Database Migrations

No additional database migrations were required for Prompt 1. Module 7 successfully reuses existing database models (`Instrument`, `Institution`, `Document`, `DocumentVersion`, `ValidationFinding`, `ValidationPolicyConfig`, `VerificationRequest`, `VerificationResponse`, `LifecycleEvaluation`, `InstrumentLineage`, `ReleaseRequest`, `ReadinessAssessment`, `ReadinessCheckResult`, and `AuditEvent`). All queries leverage existing primary and composite indexes (`status`, `institution_id`, `maturity_date`, `created_at`, `workflow_status`).

---

### 5. Automated Tests & Verification Results

The automated test suite in `backend/tests/test_module7_prompt1_foundation.py` validates all 12 criteria specified in Prompt 1:

| Test Case Name | Objective Tested | Result |
|:---|:---|:---|
| `test_status_counts_aggregation` | Status counts match independent database queries on seeded test data. | ✅ PASS |
| `test_expiring_soon_boundary_conditions` | Expiring soon counts respond dynamically to window boundary days (30d, 50d, 90d). | ✅ PASS |
| `test_month_wise_maturity_load_aggregation` | Month-wise maturity load aggregates accurately across all 12 calendar months with non-forecast disclaimer. | ✅ PASS |
| `test_overdue_and_escalated_work_metrics` | Overdue and escalated metrics identify compliance failures from lifecycle evaluations. | ✅ PASS |
| `test_verification_queue_and_source_unavailability` | Outstanding bank verification requests and source-unavailable telemetry correctly aggregated. | ✅ PASS |
| `test_release_blockers_aggregation` | Release blockers count unmet mandatory checklist items from Module 6 readiness engine. | ✅ PASS |
| `test_maturity_window_drilldown` | Maturity window filters by bank, office, and date boundaries with paginated drilldown. | ✅ PASS |
| `test_empty_results_handling` | Empty database or zero-match queries return valid responses with zero amounts without crashing. | ✅ PASS |
| `test_tenant_isolation_and_cross_institution_rejection` | Institution A cannot query or aggregate Institution B records; cross-tenant attempts return 403 Forbidden. | ✅ PASS |
| `test_role_scoped_office_and_assignee_visibility` | Bureau staff view assignee breakdowns, while Institution Users have assignee analytics redacted. | ✅ PASS |
| `test_document_completeness_and_unconfigured_policy` | Missing policy configuration returns explicit `POLICY_UNCONFIGURED` state rather than silent zero. | ✅ PASS |
| `test_pagination_and_sorting_stability` | Allowlisted sorting (amount, maturity_date) and pagination limits are strictly enforced. | ✅ PASS |
| `test_operational_priority_queue_scoring` | Priority queue returns transparent composite score (0–100) and disclosed factor breakdowns. | ✅ PASS |
| `test_metric_dictionary_endpoint` | Central metric dictionary catalog accessible via REST endpoint with full PRD traceability. | ✅ PASS |

**Test Execution Summary:**
- Command: `pytest tests/test_module7_prompt1_foundation.py -v`
- Outcome: `14 passed in 0.78s` (100% passing)
- Regression Verification: `pytest tests/test_modules.py tests/test_module6_prompt1_foundation.py` → `14 passed in 0.59s` (0 regressions)

---

### 6. Known Limitations & Edge Cases Handled

1. **Simulated Verification Responses:** In accordance with PRD Section 19, verification adapters operating in simulation mode are flagged, and their requests are categorized under aging telemetry without promoting instrument trust to `L3_BANK_CONFIRMED`.
2. **Assignee Scoping:** Institution users are not permitted to see internal officer assignee IDs or officer workloads; these fields are automatically set to `None` in responses to `ROLE_INSTITUTION_USER`.
3. **Calendar Aggregation Guarantee:** The month-wise maturity load is explicitly documented and labeled as a deterministic calendar aggregation of recorded instrument maturity dates, not an algorithmic forecast or predictive model.

---

### 7. Next Steps for Module 7

- **Prompt 2:** Implement the Command Center Frontend Dashboard & Explainable Priority Queue (Completed below).
- **Prompt 3:** Implement Advanced Multi-Parameter Search, Faceted Navigation, and Drill-Down Views (rich search filters, full-text indexes, document preview links).
- **Prompt 4:** Implement Reporting & Export Engine (streaming CSV generation, audit evidence packs, PDF formatting with digital hash verifications).
- **Prompt 5:** Implement Tamper-Evident Audit Trail UI, Cryptographic Chain Verification, and E2E Acceptance Tests.

---

## Prompt 2: Command Center Frontend Dashboard & Explainable Priority Queue

### 1. Overview & Architectural Principles

Prompt 2 delivers the operational Command Center frontend cockpit located at `/command-center` and integrated with the backend APIs established in Prompt 1. The dashboard adheres strictly to the following principles:

1. **Production-Grade Data Binding:** Zero synthetic fallbacks or hard-coded mock values. Every widget is bound directly to the versioned `/api/v1/dashboard/*` endpoints.
2. **Transparent Workflow Scoring:** The 0–100 score in the Priority Queue is explicitly identified in the UI as an **operational workflow-priority score to guide scrutiny triage, NOT a fraud probability or authenticity score**.
3. **Statutory Integrity & Safeguards:**
   - Prominent statutory guard in the Maturity Window: *"Maturity elapsed or approaching does NOT constitute proof of release or refund eligibility."*
   - Verifiable distinction between genuinely confirmed bank telemetry and prototype simulators: any simulated adapter response is visibly and indelibly tagged with a prominent `SIMULATED` badge.
   - Explicit `POLICY_UNCONFIGURED` handling in document completeness to avoid misleading zero counts.
   - Accounting transparency disclaimer on the month-wise maturity load: labeled as a deterministic calendar aggregation in INR (₹), not an algorithmic forecast or predictive model.
4. **Role-Aware Scoping:** Automatic adaptation based on the user's role (`ROLE_INSTITUTION_USER`, `ROLE_SCRUTINY_OFFICER`, `ROLE_BRANCH_HEAD`, `ROLE_COMPETENT_AUTHORITY`, `ROLE_AUDITOR`, `ROLE_SYSTEM_ADMIN`). Assignees and internal workloads are redacted for institution users.
5. **URL-Preserved Query State:** Parameters such as `window_days`, `year`, and `min_priority` are synchronized with URL query params for bookmarking and sharing.

---

### 2. Implemented Frontend Components & Routes

| Component / File Path | Description & Role |
|:---|:---|
| `frontend/src/types/commandCenter.ts` | Comprehensive TypeScript interfaces matching backend Pydantic schemas for all 7 metric categories, priority queue items, and dictionary entries. |
| `frontend/src/api/commandCenter.ts` | Axios API client for all `/api/v1/dashboard/*` endpoints with typed error handling and cancelation. |
| `frontend/src/app/routes/CommandCenterPage.tsx` | Main cockpit container under `/command-center`. Coordinates parallel API queries, maintains URL query state, handles role-based rendering, empty states, and provides global refresh controls. |
| `frontend/src/features/commandCenter/components/StatusOverviewCards.tsx` | Category A: 6 interactive metric cards (Active, Expiring Soon, Matured, Renewed, Released, Pending) with direct navigation to pre-filtered search results and metric definition popups. |
| `frontend/src/features/commandCenter/components/MaturityWindowSection.tsx` | Category B: Maturity window selector (30d, 60d, 90d, 180d, 365d), count, deposit volume, issuing bank breakdown, instrument list with trust badges, and statutory release guard. |
| `frontend/src/features/commandCenter/components/OverdueEscalatedQueue.tsx` | Category C: Overdue compliance actions and escalation desk. Displays days overdue, escalation targets, and office assignments (redacting internal assignees for institution users). |
| `frontend/src/features/commandCenter/components/VerificationQueueWidget.tsx` | Category D: Real-time telemetry on in-flight bank verification requests, aging breakdown (`<7d`, `7-14d`, `15-30d`, `>30d`), prominent `SIMULATED` badges, and source-unavailable flags. |
| `frontend/src/features/commandCenter/components/CompletenessBlockersWidget.tsx` | Categories E & F: Document completeness health (present, missing, unreadable, awaiting), unconfigured policy alerts, and Module 6 release gate blockers with direct links. |
| `frontend/src/features/commandCenter/components/MaturityLoadChart.tsx` | Category G: Month-wise visual bar chart of maturity load in INR (₹) with toggleable accessible tabular view and accounting transparency notice. |
| `frontend/src/features/commandCenter/components/PriorityQueueDesk.tsx` | Category H: Explainable operational priority queue (0–100 score) with transparent factor breakdowns (Urgency 35%, Discrepancy 25%, Trust 20%, Overdue 20%), deterministic ordering, and weight disclosure panel. |
| `frontend/src/features/commandCenter/components/MetricDictionaryModal.tsx` | Searchable modal cataloging all formal metric definitions, formulas, data sources, and PRD requirements directly from the backend. |
| `frontend/src/components/navigation/Sidebar.tsx` | Navigation entry linking `/command-center` in the main application sidebar. |
| `frontend/src/app/routes/DashboardPage.tsx` | Added quick-access Command Center banner and launch button on the default dashboard. |

---

### 3. Priority Queue Scoring Architecture

In accordance with PRD-FR-075, the priority score is computed deterministically:

$$\text{Priority Score} = 0.35 \times \text{Urgency} + 0.25 \times \text{Discrepancy} + 0.20 \times \text{Trust} + 0.20 \times \text{Overdue}$$

- **Urgency (35%):** Scales as maturity approaches (100 for $\le 7\text{ days}$, 80 for $\le 30\text{ days}$, 50 for $\le 90\text{ days}$, 20 for $> 90\text{ days}$).
- **Discrepancy (25%):** Unresolved OCR or validation discrepancies (100 for high severity, 60 for medium, 20 for low, 0 if clean).
- **Trust Factor (20%):** Higher priority for lower trust states requiring scrutiny (100 for unverified/draft, 70 for physical only, 30 for officer verified, 0 for bank verified).
- **Overdue Factor (20%):** Active overdue or escalated flags (100 if escalated, 75 if overdue $>14\text{ days}$, 50 if overdue $\le 14\text{ days}$, 0 if on schedule).
- **Deterministic Tie-Breaking:** If two records have identical priority scores, tie-breaks are ordered by `maturity_date ASC`, then `created_at DESC`, then `id ASC`.

---

### 4. Automated Tests & Build Verification

The frontend test suite in `frontend/src/features/commandCenter/__tests__/CommandCenter.test.tsx` and full suite validate all criteria:

| Test Name | Verification Focus | Result |
|:---|:---|:---|
| `renders StatusOverviewCards` | Verifies real counts, active definitions, and pre-filtered search links. | ✅ PASS |
| `renders MaturityWindowSection` | Verifies statutory warning, window selector, and instrument list with trust badges. | ✅ PASS |
| `renders OverdueEscalatedQueue` | Verifies days overdue, escalation roles, and role-appropriate office display. | ✅ PASS |
| `renders VerificationQueueWidget` | Verifies aging brackets, source-unavailable telemetry, and prominent `SIMULATED` badges. | ✅ PASS |
| `renders CompletenessBlockersWidget`| Verifies `POLICY_UNCONFIGURED` handling and release blocker gate cards. | ✅ PASS |
| `renders MaturityLoadChart` | Verifies INR labels, chart bars, non-forecast disclaimer, and accessible table toggle. | ✅ PASS |
| `renders PriorityQueueDesk` | Verifies 0–100 workflow score disclaimer, factor breakdowns, and weight disclosures. | ✅ PASS |
| `renders full CommandCenterPage` | End-to-end integration with mocked API client, query param parsing, and page rendering. | ✅ PASS |

**Build & Verification Summary:**
- **Frontend Test Suite:** `12 passed in 1.67s` (`vitest run`)
- **TypeScript & Vite Build:** `tsc -b && vite build` completed cleanly with **0 errors**.
- **Backend Test Suite:** `pytest tests/test_module7_prompt1_foundation.py` → `14 passed in 0.46s` (0 regressions).

---

## Prompt 3: Unified Search, Record Drill-Down, Historical Timelines & Append-Only Scrutiny Observations

### 1. Implemented Files

| File Path | Description |
|:---|:---|
| `backend/app/modules/dashboard/models.py` | Additive domain model `ScrutinyObservation` with immutable note text, category, authorship, bidirectional revision links (`supersedes_id`, `superseded_by_id`), reasoned resolution fields, and internal-only visibility flags. |
| `backend/alembic/versions/2026_10_25_1200-a8b9c0d1e2f3_add_module_7_scrutiny_observations.py` | Database migration adding the `scrutiny_observations` table and indexes. |
| `backend/app/modules/dashboard/schemas.py` | Pydantic response and request models for instrument search, release case search, document history, field provenance, lifecycle events, scrutiny observations, and snapshot aggregations. |
| `backend/app/modules/dashboard/search_service.py` | Parameterized SQL search queries for instruments and release cases supporting status, bank, reference, trust level, date ranges, assigned office, discrepancy flags, and priority queue categories. |
| `backend/app/modules/dashboard/observation_service.py` | Business logic for append-only scrutiny notes. Disallows silent overwrites, enforces mandatory amendment rationales, links superseding notes, logs audit trail, and prevents unauthorized auditor modifications. |
| `backend/app/modules/dashboard/history_service.py` | Complete multi-dimensional history builder unifying current snapshot, versioned documents with SHA-256 hashes, field provenance with policy masking, lifecycle evaluations with `SIMULATED` verification tags, and chronological audit trail. |
| `backend/app/modules/dashboard/router.py` | Endpoints on `/api/v1/dashboard/search/instruments`, `/api/v1/dashboard/search/release-cases`, `/api/v1/dashboard/instruments/{id}/detail`, and observation create/amend/resolve operations. |
| `frontend/src/types/commandCenter.ts` | TypeScript interfaces for all Prompt 3 search, observation, and history models. |
| `frontend/src/api/commandCenter.ts` | Client API methods for unified instrument search, release case search, detail snapshots, and observation actions. |
| `frontend/src/app/routes/UnifiedSearchPage.tsx` | Full-featured unified search page mounted at `/search`. Dual tabs for Instruments and Release Cases, filter drawer, URL synchronization, sortable allowlisted headers, active filter pills, reset button, and pagination. |
| `frontend/src/app/routes/InstrumentDetailPage.tsx` | Enriched detail view with 6 dedicated tabs: Current Snapshot (with conceptual clarity notice), Documents & SHA-256 Hashes, Field Provenance, Lifecycle & Lineage (with `SIMULATED ADAPTER` tags), Scrutiny Observations (with Add/Amend/Resolve modals), and Audit Timeline. |
| `frontend/src/app/router.tsx` | Registered `/search` route in the application router. |
| `frontend/src/components/navigation/Sidebar.tsx` | Added Unified Search navigation entry with search icon. |
| `docs/module-7-search-and-history.md` | Formal handover guide detailing supported filters, scope enforcement, timeline sources, observation revision semantics, and security rules. |
| `backend/tests/test_module7_prompt3_search_history.py` | 7 automated backend tests verifying filters, tenant isolation, SHA-256 ordering, simulation labelling, append-only supersession, and auditor read-only enforcement. |
| `frontend/src/features/commandCenter/__tests__/UnifiedSearchAndHistory.test.tsx` | 9 automated frontend Vitest tests validating search interactions, tab switching, and observation management. |

---

### 2. Implemented Endpoints

| HTTP Method | Endpoint Path | Function & PRD Mapping | Authorized Roles |
|:---|:---|:---|:---|
| `GET` | `/api/v1/dashboard/search/instruments` | Parameterized search for FDR instruments with multi-attribute filters, sorting, and pagination. | Authenticated (scoped) |
| `GET` | `/api/v1/dashboard/search/release-cases` | Parameterized search for Release & Refund cases with workflow status and readiness outcome filters. | Authenticated (scoped) |
| `GET` | `/api/v1/dashboard/instruments/{id}/detail` | Multi-dimensional snapshot unifying snapshot, documents, field provenance, lifecycle lineage, observations, and audit events. | Authorized users (scoped) |
| `GET` | `/api/v1/dashboard/instruments/{id}/observations` | Retrieves append-only scrutiny observation thread with supersession lineage. | Authorized users (scoped) |
| `POST` | `/api/v1/dashboard/instruments/{id}/observations` | Creates a new immutable scrutiny observation. | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDIT_EXAMINER` |
| `POST` | `/api/v1/dashboard/observations/{id}/amend` | Amends an existing observation by creating a superseding note and updating pointers. | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDIT_EXAMINER` |
| `POST` | `/api/v1/dashboard/observations/{id}/resolve` | Resolves an observation with mandatory documented justification. | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDIT_EXAMINER` |

---

### 3. Automated Tests & Build Verification

- **Backend Pytest Suite:** `pytest tests/test_module7_prompt3_search_history.py` → **7 passed** in 0.80s.
- **Backend Non-Regression Suite:** `pytest tests/test_module7_prompt1_foundation.py` → **14 passed** in 0.50s.
- **Combined Backend:** `21 passed` with 0 failures.
- **Frontend Vitest Suite:** `npx vitest run src/features/commandCenter/__tests__/UnifiedSearchAndHistory.test.tsx` → **9 passed** in 0.58s.
- **Full Frontend Suite:** `npx vitest run` → **21 passed** across 3 test files in 2.09s.
- **Production Build:** `npm run build` (`tsc -b && vite build`) completed cleanly with **0 errors**.

---

## Prompt 4: Operational Reports, Consistent Drill-Down and Secure CSV/PDF Exports

### 1. Implemented Files & Architecture

| File Path | Description |
|:---|:---|
| `backend/pyproject.toml` | Added `reportlab>=5.0.0` dependency for native high-performance, audit-compliant PDF generation. |
| `backend/app/modules/dashboard/schemas.py` | Typed Pydantic models for Report Filter Metadata, Pending Verification, Upcoming Maturities, Missing Documents, Interventions, and Audit Evidence Pack extractions. |
| `backend/app/modules/dashboard/report_service.py` | Query services for the 4 core operational reports and per-instrument audit evidence pack. Reuses underlying lifecycle, instrument, and validation models without duplicating rules. Distinguishes `SIMULATED` verifications from live bank feeds. |
| `backend/app/modules/dashboard/export_service.py` | Secure export engine: `sanitize_csv_cell` (spreadsheet formula injection defense), `generate_csv` (UTF-8 BOM, metadata header, streaming output), and `generate_pdf` (ReportLab A4 landscape, `NumberedCanvas` two-pass page numbering, sensitivity banner). Emits audit events on every export. |
| `backend/app/modules/dashboard/router.py` | API endpoints for `/reports/pending-verification`, `/reports/upcoming-maturities`, `/reports/missing-documents`, `/reports/interventions`, `/reports/evidence-pack/{id}`, `/reports/{type}`, and CSV/PDF export endpoints. |
| `frontend/src/types/commandCenter.ts` | TypeScript interfaces for all operational report response payloads, filters, and audit evidence pack documents. |
| `frontend/src/api/commandCenter.ts` | API client methods for querying reports, retrieving evidence packs, and triggering browser file downloads for CSV and PDF. |
| `frontend/src/features/commandCenter/components/OperationalReportsWorkspace.tsx` | Comprehensive reporting workspace featuring tab navigation, dynamic filter drawer, summary counters, record drill-down links to `/instruments/:id`, export buttons with role gating, and an Audit Evidence Pack modal. |
| `frontend/src/app/routes/ReportsPage.tsx` | Route page wrapper mounted at `/reports`. |
| `frontend/src/app/router.tsx` | Registered `/reports` route. |
| `frontend/src/components/navigation/Sidebar.tsx` | Added Operational Reports navigation entry with `FileSpreadsheet` icon. |
| `docs/module-7-reporting-and-exports.md` | Complete technical documentation covering report specifications, data sources, security boundaries, formula injection mitigation, and audit logging. |
| `backend/tests/test_module7_prompt4_reports_exports.py` | 8 automated backend acceptance tests covering simulated channel labeling, renewal status, checklist outcomes, neutral intervention states, tenant isolation, formula injection defense, PDF generation, and evidence pack checks. |
| `frontend/src/features/commandCenter/__tests__/OperationalReports.test.tsx` | 6 automated frontend Vitest tests covering workspace rendering, tab navigation, filter triggers, export actions, and modal extraction. |

---

### 2. Implemented Endpoints

| HTTP Method | Endpoint Path | Function & PRD Mapping | Authorized Roles |
|:---|:---|:---|:---|
| `GET` | `/api/v1/dashboard/reports/pending-verification` | Authorized instruments awaiting verification with pending age and explicit `SIMULATED` flagging. | Authenticated (scoped) |
| `GET` | `/api/v1/dashboard/reports/upcoming-maturities` | Approaching deposit maturities with identical Command Center date basis and renewal linkage. | Authenticated (scoped) |
| `GET` | `/api/v1/dashboard/reports/missing-documents` | Non-compliant or missing checklist items mapped against versioned policies. | Authenticated (scoped) |
| `GET` | `/api/v1/dashboard/reports/interventions` | Operational follow-up items (overdue tasks, escalations, failed verifications) in neutral terminology. | Authenticated (scoped) |
| `GET` | `/api/v1/dashboard/reports/evidence-pack/{instrument_id}` | Structured audit evidence pack with document SHA-256 hashes, uncertified disclaimer, and audit chain verification. | Authenticated (scoped) |
| `GET` | `/api/v1/dashboard/reports/{report_type}` | Generic parameterized dispatcher for operational report datasets. | Authenticated (scoped) |
| `GET` | `/api/v1/dashboard/reports/{report_type}/export/csv` | Secure CSV export with formula injection defense and metadata header block. | Dedicated export permission |
| `GET` | `/api/v1/dashboard/reports/{report_type}/export/pdf` | Official ReportLab PDF export with landscape tabular layout, sensitivity label, and pagination. | Dedicated export permission |

---

### 3. Automated Tests & Build Verification

- **Backend Pytest Suite:** `pytest tests/test_module7_prompt4_reports_exports.py` → **8 passed** in 2.56s.
- **Full Module 7 Backend Suite:** `pytest tests/test_module7_prompt1_foundation.py tests/test_module7_prompt3_search_history.py tests/test_module7_prompt4_reports_exports.py` → **29 passed** in 3.10s (0 regressions).
- **Frontend Vitest Suite:** `npx vitest run src/features/commandCenter/__tests__/OperationalReports.test.tsx` → **6 passed** in 0.54s.
- **Combined Module 7 Frontend Suite:** `npx vitest run src/features/commandCenter/__tests__/` → **23 passed** across 3 test files in 1.89s.
- **Production Build:** `npm run build` (`tsc -b && vite build`) completed cleanly with **0 errors**.
---

## Prompt 5: Complete Audit Integrity, Audit-Chain Verification, Security Hardening & End-to-End Integration

### 1. Implemented Files & Architecture

| File Path | Description |
|:---|:---|
| `backend/alembic/versions/2026_10_25_1300-b9c0d1e2f3a4_add_audit_hash_chain.py` | Database migration adding `sequence_number`, `previous_hash`, `current_hash`, `policy_version`, and creating database-level triggers rejecting any `UPDATE` or `DELETE` on `audit_events`. |
| `backend/app/modules/audit/models.py` | Updated SQLAlchemy model for `AuditEvent` with monotonic sequence, block hashes, and ORM event listeners (`before_update`, `before_delete`) raising `PermissionError`. |
| `backend/app/modules/audit/schemas.py` | Pydantic response models for `AuditEventRead`, `AuditInconsistencyDetail`, and `AuditChainVerificationResponse`. |
| `backend/app/modules/audit/service.py` | Hardened central logging service with deterministic SHA-256 canonical hashing (`compute_canonical_event_hash`), monotonic sequence numbering, parent hash linking (`previous_hash`), and credential sanitization (`sanitize_dict`). |
| `backend/app/modules/dashboard/audit_query_service.py` | Query service providing multi-attribute audit filtering, row-level tenant authorization, and the cryptographic verification engine (`verify_audit_log_integrity`). |
| `backend/app/modules/audit/router.py` | REST API routes for `/audit/events`, `/audit/events/{id}`, `/audit/integrity`, and `/audit/verify`. |
| `backend/app/modules/release/router.py` & `decision_service.py` | Security hardening: Release approval authority strictly restricted to `COMPETENT_AUTHORITY`. System Administrator role denied release approval authority. |
| `frontend/src/api/endpoints.ts` | Added `auditApi` with `list()`, `get()`, and `verifyChain()` methods. |
| `frontend/src/app/routes/AuditPage.tsx` | Complete Audit Explorer interface with live "Verify Audit Chain" action, cryptographic pass/tamper status banner, sequence filters, copyable hashes, and forensic inspection drawer. |
| `docs/audit-integrity-and-verification.md` | Formal technical specification covering hashing rules, canonicalization, database triggers, verification engine, and residual risk disclosures. |
| `docs/module-7-architecture.md` | Comprehensive architectural documentation of all Module 7 components, data flows, and security boundaries. |
| `docs/module-7-acceptance-checklist.md` | PRD functional requirement mapping (PRD-FR-070 to PRD-FR-096) and verification summary. |
| `backend/tests/test_module7_prompt5_audit_integrity.py` | 14 automated acceptance and security tests covering hash chaining, sanitization, mutation rejection, tamper detection, RBAC boundaries, cross-tenant isolation, and Scenarios A–F. |
| `frontend/src/features/commandCenter/__tests__/AuditExplorer.test.tsx` | 5 automated Vitest tests verifying Audit Explorer rendering, table sequences, verifyChain invocation, forensic tamper alert rendering, and inspection modal. |

---

### 2. Implemented Endpoints

| HTTP Method | Endpoint Path | Function & PRD Mapping | Authorized Roles |
|:---|:---|:---|:---|
| `GET` | `/api/v1/audit/events` | List audit events with multi-attribute filtering, search, and row-level tenant scoping (PRD-FR-090, PRD-FR-091). | All authenticated users (scoped) |
| `GET` | `/api/v1/audit/events/{event_id}` | Retrieve full cryptographic details and state diffs for a single audit event (PRD-FR-091). | All authenticated users (scoped) |
| `POST` | `/api/v1/audit/verify` | Cryptographically replays and verifies SHA-256 chain continuity, reporting earliest inconsistency (PRD-FR-093). | `SYSTEM_ADMIN`, `AUDITOR`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY` |
| `GET` | `/api/v1/audit/integrity` | Alias to verify audit chain integrity for compliance dashboards. | `SYSTEM_ADMIN`, `AUDITOR`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY` |

---

### 3. Verification & Acceptance Journey Scenarios (A through F)

- **Scenario A (New Instrument Creation):** Registered instrument with strict decimal currency, uploaded PDF document, recorded `INSTRUMENT_CREATED` in audit chain with monotonic sequence #.
- **Scenario B (Discrepancy & Verification):** Flagged date mismatch finding, recorded officer scrutiny observation, verified resolution and cryptographic linking.
- **Scenario C (Maturity & Renewal Lineage):** Approaching maturity instrument linked to successor renewal, preserving predecessor history without silent state mutation.
- **Scenario D (Release/Refund Maker-Checker):** Release Gate blocks unauthorized advancement; officer review and Competent Authority approval enforced; System Admin denied approval authority.
- **Scenario E (Operational Reports & Export):** Operational metrics match database calculations; CSV and PDF exported with statutory banners and export audit logging.
- **Scenario F (Audit Integrity & Tamper Detection):** Intact chain verified with `status: "PASS"`; simulated payload tampering detected with `PAYLOAD_TAMPERED`; database trigger rejects direct SQL update/delete.

---

### 4. Automated Tests & Build Verification

- **Backend Pytest Suite (Prompt 5):** `pytest tests/test_module7_prompt5_audit_integrity.py` → **14 passed** in 10.02s.
- **Full Module 7 Backend Suite:** `pytest tests/test_module7_*.py` → **43 passed** in 15.42s (0 regressions).
- **Frontend Vitest Suite (Prompt 5):** `npx vitest run src/features/commandCenter/__tests__/AuditExplorer.test.tsx` → **5 passed** in 0.47s.
- **Combined Module 7 Frontend Suite:** `npx vitest run src/features/commandCenter/__tests__/` → **28 passed** across 4 test files in 1.99s.
- **Frontend Production Build:** `npm run build` (`tsc -b && vite build`) completed cleanly with **0 errors**.
