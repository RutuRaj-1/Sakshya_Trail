# Module 7: Command Center Metric Dictionary & Traceability Guide

**Document Reference:** `docs/module-7-metric-dictionary.md`  
**Standard:** AICTE / SIH 2026 Problem Statement ID 26265 (“Streamline of Security Deposit/FDR Portal”)  
**PRD Alignment:** PRD-FR-070 (070a–070f), PRD-FR-075, PRD-FR-076, PRD-FR-077  
**Timezone / Calendar Standard:** Indian Standard Time (`Asia/Kolkata`, UTC+05:30), Gregorian calendar date boundaries.

---

## 1. Governance Principles & Core Rules

1. **Separation of Concerns:** Administrative workflow status (`Instrument.status`) is strictly decoupled from evidentiary trust level (`Instrument.trust_level`), physical/provisional maturity dates (`Instrument.maturity_date`), and release case states (`ReleaseRequest.workflow_status`).
2. **Immutable Predecessor History:** Renewals and replacements create explicit directed edges in `instrument_lineages`. A renewal or replacement does **not** erase predecessor history or mark the predecessor as released.
3. **Database Aggregation:** All dashboard summary cards, counts, and sums are computed via parameterized SQL database aggregations (`func.count`, `func.sum`, `group_by`) rather than synthetic in-memory iteration.
4. **Tenant Isolation Before Aggregation:** Role boundaries are applied prior to aggregation queries. An `INSTITUTION_USER` is strictly confined to records where `institution_id == current_user.institution_id`. Cross-tenant query attempts trigger `403 Forbidden` and generate security audit records.
5. **No Silent Zeroes for Unconfigured Policies:** Where regulatory or institutional policy is absent (e.g., missing checklist profiles or unconfigured required document lists), the system returns an explicit `POLICY_UNCONFIGURED` state rather than a misleading zero.

---

## 2. Central Metric Catalog

### MTR-STAT-ACTIVE: Active In-Force Instruments
- **Display Label:** Active Instruments
- **Category:** Status Counts (`STATUS_COUNTS`)
- **PRD Mapping:** PRD-FR-070a
- **Definition:** Statutory security deposits currently valid, beyond immediate expiry warning window, and not released or superseded by renewal.
- **Calculation Rule:**
  ```sql
  COUNT(instruments.id)
  WHERE status IN ('ACTIVE', 'REGISTERED', 'VERIFIED')
    AND maturity_date > (today + window_days)
    AND status != 'RELEASED'
    AND id NOT IN (
      SELECT predecessor_instrument_id
      FROM instrument_lineages
      WHERE relationship_status = 'ACTIVE'
        AND relationship_type IN ('RENEWAL', 'REPLACEMENT')
    )
  ```
- **Source Entity & Fields:** `instruments.status`, `instruments.maturity_date`, `instrument_lineages.relationship_status`
- **Date Basis:** Calendar date comparison (`Instrument.maturity_date > today + window_days`) in `Asia/Kolkata`.
- **Supported Filters:** `institution_id`, `bank_name`, `assigned_office`, `trust_level`.
- **Authorization Scope:** Scoped to user's assigned institution or bureau jurisdiction.
- **Handling of Unconfigured Data:** Defaults `window_days` to 90 days if unconfigured.
- **API Endpoint:** `GET /api/v1/dashboard/status-counts`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_status_counts_aggregation`

---

### MTR-STAT-EXPIRING-SOON: Expiring Soon Instruments
- **Display Label:** Expiring Soon Instruments
- **Category:** Status Counts (`STATUS_COUNTS`)
- **PRD Mapping:** PRD-FR-070a
- **Definition:** Instruments maturing within the selectable monitoring window (default 90 days) requiring renewal action or scrutiny.
- **Calculation Rule:**
  ```sql
  COUNT(instruments.id)
  WHERE status IN ('ACTIVE', 'REGISTERED', 'VERIFIED')
    AND maturity_date >= today
    AND maturity_date <= (today + window_days)
    AND status != 'RELEASED'
    AND id NOT IN (
      SELECT predecessor_instrument_id
      FROM instrument_lineages
      WHERE relationship_status = 'ACTIVE'
        AND relationship_type IN ('RENEWAL', 'REPLACEMENT')
    )
  ```
- **Source Entity & Fields:** `instruments.status`, `instruments.maturity_date`, `instrument_lineages`
- **Date Basis:** `today <= maturity_date <= today + window_days` (`Asia/Kolkata`).
- **Supported Filters:** `window_days` (default 90), `institution_id`, `bank_name`, `assigned_office`.
- **Authorization Scope:** Role-scoped.
- **Handling of Unconfigured Data:** Defaults to 90 days.
- **API Endpoint:** `GET /api/v1/dashboard/status-counts`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_expiring_soon_boundary_conditions`

---

### MTR-STAT-MATURED: Matured Instruments
- **Display Label:** Matured Instruments
- **Category:** Status Counts (`STATUS_COUNTS`)
- **PRD Mapping:** PRD-FR-070a
- **Definition:** Instruments whose term has elapsed without a confirmed release or verified renewal successor.
- **Calculation Rule:**
  ```sql
  COUNT(instruments.id)
  WHERE maturity_date < today
    AND status != 'RELEASED'
    AND id NOT IN (
      SELECT predecessor_instrument_id
      FROM instrument_lineages
      WHERE relationship_status = 'ACTIVE'
        AND relationship_type IN ('RENEWAL', 'REPLACEMENT')
    )
    AND status NOT IN ('DRAFT', 'SUBMITTED', 'UNDER_SCRUTINY', 'UNDER_REVIEW', 'RETURNED_FOR_CORRECTION')
  ```
- **Source Entity & Fields:** `instruments.maturity_date`, `instruments.status`
- **Date Basis:** `maturity_date < today` (`Asia/Kolkata`).
- **Supported Filters:** `institution_id`, `bank_name`, `assigned_office`, `trust_level`.
- **Authorization Scope:** Role-scoped.
- **API Endpoint:** `GET /api/v1/dashboard/status-counts`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_status_counts_aggregation`

---

### MTR-STAT-RENEWED: Renewed Predecessors
- **Display Label:** Renewed / Replaced Instruments
- **Category:** Status Counts (`STATUS_COUNTS`)
- **PRD Mapping:** PRD-FR-070a
- **Definition:** Predecessor instruments that have been successfully renewed or replaced with an active edge in the lineage graph.
- **Calculation Rule:**
  ```sql
  COUNT(DISTINCT instrument_lineages.predecessor_instrument_id)
  WHERE relationship_status = 'ACTIVE'
    AND relationship_type IN ('RENEWAL', 'REPLACEMENT')
  ```
- **Source Entity & Fields:** `instrument_lineages.relationship_status`, `instrument_lineages.relationship_type`
- **Supported Filters:** `institution_id`, `assigned_office`.
- **Authorization Scope:** Role-scoped.
- **API Endpoint:** `GET /api/v1/dashboard/status-counts`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_renewed_instruments_lineage_accounting`

---

### MTR-STAT-RELEASED: Formally Discharged / Released
- **Display Label:** Released Instruments
- **Category:** Status Counts (`STATUS_COUNTS`)
- **PRD Mapping:** PRD-FR-070a
- **Definition:** Instruments formally discharged or released following an executed competent authority release order.
- **Calculation Rule:**
  ```sql
  COUNT(instruments.id) WHERE status = 'RELEASED'
  ```
- **Source Entity & Fields:** `instruments.status`
- **Supported Filters:** `institution_id`, `bank_name`, `assigned_office`.
- **Authorization Scope:** Role-scoped.
- **API Endpoint:** `GET /api/v1/dashboard/status-counts`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_status_counts_aggregation`

---

### MTR-STAT-PENDING: Intake Scrutiny / Draft Records
- **Display Label:** Pending Registration / Review
- **Category:** Status Counts (`STATUS_COUNTS`)
- **PRD Mapping:** PRD-FR-070a
- **Definition:** Records in intake stages prior to active statutory registry: `DRAFT`, `SUBMITTED`, `UNDER_SCRUTINY`, `UNDER_REVIEW`, `RETURNED_FOR_CORRECTION`.
- **Calculation Rule:**
  ```sql
  COUNT(instruments.id)
  WHERE status IN ('DRAFT', 'SUBMITTED', 'UNDER_SCRUTINY', 'UNDER_REVIEW', 'RETURNED_FOR_CORRECTION')
    AND status != 'RELEASED'
  ```
- **API Endpoint:** `GET /api/v1/dashboard/status-counts`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_status_counts_aggregation`

---

### MTR-MAT-WINDOW: Maturity Window Query & Drilldown
- **Display Label:** Maturity Window Count & Volume
- **Category:** Maturity Window (`MATURITY_WINDOW`)
- **PRD Mapping:** PRD-FR-070b
- **Definition:** Total instruments, sum of amounts, bank breakdown, office breakdown, and paginated records maturing within `[start_date, end_date]`.
- **Calculation Rule:**
  ```sql
  SELECT COUNT(id), SUM(amount)
  FROM instruments
  WHERE maturity_date >= :start_date AND maturity_date <= :end_date AND status != 'RELEASED'
  ```
- **Source Entity & Fields:** `instruments.maturity_date`, `instruments.amount`, `instruments.bank_name`
- **Date Basis:** Inclusive range `[start_date, end_date]` in `Asia/Kolkata`.
- **Supported Filters:** `start_date`, `end_date`, `window_days`, `institution_id`, `bank_name`, `assigned_office`, `page`, `page_size`.
- **Authorization Scope:** Role-scoped.
- **API Endpoint:** `GET /api/v1/dashboard/maturity-window`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_maturity_window_drilldown`

---

### MTR-OVERDUE-ESCALATED: Overdue Compliance & Escalated Cases
- **Display Label:** Overdue & Escalated Cases
- **Category:** Overdue & Escalated (`OVERDUE_ESCALATED`)
- **PRD Mapping:** PRD-FR-070c
- **Definition:** Instruments and release cases past recorded deadlines or escalated across administrative levels.
- **Calculation Rule:**
  Count distinct items from `lifecycle_evaluations` where `is_overdue = TRUE` or `is_escalated = TRUE` plus active release cases returned for correction. Grouped by assigned office and assignee.
- **Source Entity & Fields:** `lifecycle_evaluations.is_overdue`, `lifecycle_evaluations.is_escalated`, `release_requests.workflow_status`, `instruments.assigned_office`
- **Supported Filters:** `assigned_office`, `institution_id`.
- **Authorization Scope:** Bureau staff view full breakdown; institution users view only their institution's overdue items without staff assignee analytics.
- **API Endpoint:** `GET /api/v1/dashboard/overdue-escalated`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_overdue_and_escalated_work_metrics`

---

### MTR-VERIF-QUEUE: Bank Verification Desk Queue & Health
- **Display Label:** Verification Queue & Channel Health
- **Category:** Verification Queue (`VERIFICATION_QUEUE`)
- **PRD Mapping:** PRD-FR-070d
- **Definition:** Outstanding bank verification requests (`PENDING`, `REQUESTED`, `SENT`), age distribution buckets (`<7d`, `7-14d`, `15-30d`, `>30d`), average age, and source-unavailable cases (`SOURCE_UNAVAILABLE`, `TIMEOUT`, `FAILED`).
- **Calculation Rule:**
  ```sql
  COUNT(id) WHERE status IN ('PENDING', 'REQUESTED', 'SENT');
  Age = (today - created_at.date());
  Average Age = SUM(Age) / COUNT(outstanding);
  ```
- **Source Entity & Fields:** `verification_requests.status`, `verification_requests.created_at`, `verification_requests.channel`
- **Supported Filters:** `institution_id`, `bank_name`.
- **Authorization Scope:** Role-scoped.
- **API Endpoint:** `GET /api/v1/dashboard/verification-queue`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_verification_queue_and_source_unavailability`

---

### MTR-DOC-COMPLETENESS: Document Completeness Checklist Aggregation
- **Display Label:** Document Completeness Breakdown
- **Category:** Document Completeness (`DOCUMENT_COMPLETENESS`)
- **PRD Mapping:** PRD-FR-070e
- **Definition:** Aggregate counts of document status: `present` (clean upload), `missing` (required categories unfulfilled under active policy), `unreadable` (scan failed or infected), `wrong_category` (discrepancy findings), and `awaiting_confirmation` (pending scan).
- **Calculation Rule:**
  Compares active `ValidationPolicyConfig` for `REQUIRED_DOCUMENT_CATEGORIES` against uploaded `Document` categories and `ValidationFinding` discrepancies.
- **Handling of Unconfigured Policy:** If no active policy config exists, returns `policy_configured: false`, `policy_version: null`, and `policy_status_message: "POLICY_UNCONFIGURED"`.
- **API Endpoint:** `GET /api/v1/dashboard/document-completeness`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_document_completeness_and_unconfigured_policy`

---

### MTR-REL-BLOCKERS: Release & Refund Gate Blockers
- **Display Label:** Release & Refund Blockers
- **Category:** Release Blockers (`RELEASE_BLOCKERS`)
- **PRD Mapping:** PRD-FR-070f
- **Definition:** Active release/refund cases obstructed by unmet mandatory checklist items or `BLOCKED` readiness outcome according to Module 6 Release Gate engine.
- **Calculation Rule:**
  Counts active `release_requests` where latest `readiness_assessments` has `blockers_count > 0` or outcome is `BLOCKED`. Summarizes blocker requirement types (`DOCUMENT_COMPLETENESS`, `TRUST_LEVEL`, etc.).
- **Source Entity & Fields:** `release_requests`, `readiness_assessments`, `readiness_check_results`
- **API Endpoint:** `GET /api/v1/dashboard/release-blockers`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_release_blockers_aggregation`

---

### MTR-MAT-LOAD: Deterministic Month-Wise Maturity Load
- **Display Label:** Month-Wise Maturity Load
- **Category:** Maturity Load (`MATURITY_LOAD`)
- **PRD Mapping:** PRD-FR-076
- **Definition:** Deterministic monthly aggregation of instrument counts and total monetary volume maturing in each calendar month of a given year.
- **Calculation Rule:**
  ```sql
  SELECT EXTRACT(MONTH FROM maturity_date) AS mo, COUNT(id), SUM(amount)
  FROM instruments
  WHERE EXTRACT(YEAR FROM maturity_date) = :calendar_year AND status != 'RELEASED'
  GROUP BY mo ORDER BY mo
  ```
- **Source Entity & Fields:** `instruments.maturity_date`, `instruments.amount`
- **Supported Filters:** `calendar_year`, `institution_id`, `bank_name`, `assigned_office`.
- **Disclaimer:** Deterministic calendar aggregation, not a predictive forecast.
- **API Endpoint:** `GET /api/v1/dashboard/maturity-load`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_month_wise_maturity_load_aggregation`

---

### MTR-PRIORITY-QUEUE: Operational Priority Queue
- **Display Label:** Operational Priority Queue
- **Category:** Priority Queue (`PRIORITY_QUEUE`)
- **PRD Mapping:** PRD-FR-075
- **Definition:** Urgency-ranked queue of instruments requiring administrative attention, weighted by urgency, discrepancy severity, trust state, and overdue age.
- **Calculation Formula:**
  $$\text{Score} = (0.35 \times \text{Urgency}) + (0.25 \times \text{Discrepancy}) + (0.20 \times \text{Trust}) + (0.20 \times \text{Overdue})$$
  - `Urgency` (0–100): Maturity proximity ($\le 0$ days: 100, $\le 15$ days: 90, $\le 30$ days: 75, $\le 60$ days: 50, $\le 90$ days: 30, $>90$ days: 10).
  - `Discrepancy` (0–100): Open finding severity (Critical: 100, High: 75, Medium: 50, Low/Info: 25, None: 0).
  - `Trust` (0–100): Evidentiary trust state (L0: 80, L1: 50, L2: 25, L3: 0).
  - `Overdue` (0–100): Escalated: 100, Overdue: 80, Action Due: 50, Normal: 0.
- **API Endpoint:** `GET /api/v1/dashboard/priority-queue`
- **Tests:** `backend/tests/test_module7_prompt1_foundation.py::test_operational_priority_queue_scoring`

---

## 3. PRD Traceability Matrix

| Metric ID | Display Label | PRD Requirement | API Endpoint | Test Target |
|:---|:---|:---|:---|:---|
| `MTR-STAT-ACTIVE` | Active Instruments | PRD-FR-070a | `/api/v1/dashboard/status-counts` | `test_status_counts_aggregation` |
| `MTR-STAT-EXPIRING-SOON` | Expiring Soon | PRD-FR-070a | `/api/v1/dashboard/status-counts` | `test_expiring_soon_boundary_conditions` |
| `MTR-STAT-MATURED` | Matured Instruments | PRD-FR-070a | `/api/v1/dashboard/status-counts` | `test_status_counts_aggregation` |
| `MTR-STAT-RENEWED` | Renewed Predecessors | PRD-FR-070a | `/api/v1/dashboard/status-counts` | `test_renewed_instruments_lineage_accounting` |
| `MTR-STAT-RELEASED` | Released Instruments | PRD-FR-070a | `/api/v1/dashboard/status-counts` | `test_status_counts_aggregation` |
| `MTR-STAT-PENDING` | Pending Registration | PRD-FR-070a | `/api/v1/dashboard/status-counts` | `test_status_counts_aggregation` |
| `MTR-MAT-WINDOW` | Maturity Window | PRD-FR-070b | `/api/v1/dashboard/maturity-window` | `test_maturity_window_drilldown` |
| `MTR-OVERDUE-ESCALATED` | Overdue & Escalated | PRD-FR-070c | `/api/v1/dashboard/overdue-escalated` | `test_overdue_and_escalated_work_metrics` |
| `MTR-VERIF-QUEUE` | Verification Desk Queue | PRD-FR-070d | `/api/v1/dashboard/verification-queue` | `test_verification_queue_and_source_unavailability` |
| `MTR-DOC-COMPLETENESS` | Document Completeness | PRD-FR-070e | `/api/v1/dashboard/document-completeness` | `test_document_completeness_and_unconfigured_policy` |
| `MTR-REL-BLOCKERS` | Release Gate Blockers | PRD-FR-070f | `/api/v1/dashboard/release-blockers` | `test_release_blockers_aggregation` |
| `MTR-MAT-LOAD` | Month-Wise Maturity Load | PRD-FR-076 | `/api/v1/dashboard/maturity-load` | `test_month_wise_maturity_load_aggregation` |
| `MTR-PRIORITY-QUEUE` | Priority Queue (0–100) | PRD-FR-075 | `/api/v1/dashboard/priority-queue` | `test_operational_priority_queue_scoring` |
