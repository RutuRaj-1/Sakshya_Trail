# Module 7: Command Center, Search, Reporting & Audit — Implementation Progress

**Project:** FDR Sentinel (SIH 2026 Problem Statement ID 26265: “Streamline of Security Deposit/FDR Portal”)  
**Module:** Module 7 — Command Center, Search, Reporting & Audit  
**Status:** In Progress (Prompt 1 of 5 Complete)  

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

- **Prompt 2:** Implement the Operational Queues & Priority Desk (detailed queue actions, triage workflows, bulk assignment, officer queues, and alert escalation rules).
- **Prompt 3:** Implement Advanced Multi-Parameter Search, Faceted Navigation, and Drill-Down Views (rich search filters, full-text indexes, document preview links).
- **Prompt 4:** Implement Reporting & Export Engine (streaming CSV generation, audit evidence packs, PDF formatting with digital hash verifications).
- **Prompt 5:** Implement Frontend Command Center Dashboard UI, Interactive Metric Cards, Queue Management, and E2E Acceptance Tests.
