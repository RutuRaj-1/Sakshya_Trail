# Module 5 — Lifecycle Orchestration, Policy Configuration and Renewal Lineage
## Comprehensive Architecture, Data Foundation & Technical Specifications Guide (Prompts 1 & 2 of 5)

> **Module Status:** Maturity Monitoring, Scheduler Engine & Demo Clock Implemented (Prompts 1 & 2 of 5 Verified)  
> **Alembic Revisions:**  
> • `b2c3d4e5f6a7` — Lifecycle Policies, Instrument Lineages & Lifecycle Evaluations  
> • `c3d4e5f6a7b8` — Lifecycle Job Runs & Idempotent Evaluation Constraint  
> **Backend Test Suite:** **320 passed** across all modules in 13.71s — **0 failures, 0 regressions**  
> **Prompt 1 Foundation Tests:** **15 passed** (100% green coverage on foundational criteria)  
> **Prompt 2 Scheduler & Monitoring Tests:** **15 passed** (100% green coverage on Prompt 2 criteria)  
> **Frontend Production Build:** **Compiled cleanly** with `tsc -b && vite build` in 449ms  
> **Repository:** `FDR_Sentinel`  
> **Author:** Senior Backend Architect, Workflow Engineer & PostgreSQL Data Modeller  
> **Date:** October 2026  

---

## 1. Executive Summary & Architectural Scope

Module 5 provides the **Lifecycle Orchestration, Monitoring & Renewal Lineage** subsystem of the AICTE FDR Sentinel platform. It oversees time-sensitive instrument monitoring, calendar date boundary calculations, configurable reminder rules, overdue and escalation flags, and explicit predecessor-to-successor renewal graphs.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MODULE 5 BOUNDARIES                                    │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│                  OWNS                     │               DOES NOT OWN                 │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ • Time-sensitive instrument monitoring    │ • Document upload & versioning (Mod 2)     │
│ • Days-to-maturity & due calculations     │ • Deterministic discrepancy rules (Mod 3)  │
│ • Versioned reminder & action policies    │ • Trust elevation or bank auth (Mod 4)     │
│ • Overdue indicators & escalation states  │ • Release / refund authorization gates     │
│ • Renewal / replacement lineage DAG       │ • Overall dashboard / reporting analytics  │
│ • Validity gap & overlap indicators       │ • Mutating Module 1 administrative states  │
│ • Demo date-advance execution mechanism   │ • Mutating Module 4 evidentiary trust      │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

---

## 2. Strict Concept Separation & State Invariants

A primary architectural requirement is to **never conflate separate operational states into a single overloaded column**. Module 5 maintains strict separation between administrative, evidentiary, and time-sensitive dimensions:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                    FDR INSTRUMENT                       │
                  └───────────────────────────┬─────────────────────────────┘
                                              │
            ┌─────────────────────────────────┼─────────────────────────────────┐
            ▼                                 ▼                                 ▼
   [ ADMINISTRATIVE STATUS ]         [ TRUST HIERARCHY ]            [ MATURITY & VALIDITY ]
     Column: `status`                  Column: `trust_level`          Table: `lifecycle_evaluations`
     Owner: Module 1                   Owner: Module 4                Owner: Module 5
     Values:                           Values:                        Values:
     • DRAFT                           • L0_DECLARED                  • ACTIVE
     • REGISTERED                      • L1_DOCUMENT_CONSISTENT       • MATURING_SOON
     • UNDER_REVIEW                    • L2_OFFICER_VERIFIED          • CRITICAL_WINDOW
     • PENDING_RELEASE                 • L3_BANK_CONFIRMED            • MATURED
     • RELEASED                                                       • EXPIRED
     • ENCASHED                                                       • NOT_EVALUABLE
```

### Core Invariants Enforced in Code & Database

1. **No Administrative Mutation by Time:** Approaching maturity dates or overdue action requirements **never** mutate `instruments.status`. Administrative status remains `REGISTERED` (or its current state) until authorized workflow actions occur.
2. **No Trust Mutation by Renewal:** Creating or linking a successor instrument **never** modifies predecessor or successor `trust_level`. The successor begins at `L0_DECLARED` and must independently earn evidentiary trust.
3. **No Automatic Release Eligibility:** A matured instrument does *not* automatically become eligible for release or encashment. Release requires explicit governance directives.
4. **Predecessor Immutability on Rollover:** Creating a renewal link preserves the predecessor record, historical values, amounts, and dates in their original state.
5. **Separation of Due Dates:** The institution compliance action deadline (`institution_action_due_date`) and the internal official review deadline (`officer_action_due_date`) are calculated independently based on configured policy lead times.
6. **Automatic Overdue Clearing on Renewal:** Once an instrument is linked to an active renewal successor in `instrument_lineages`, its overdue and escalation flags are suppressed (`due_condition = NORMAL`).

---

## 3. Database Schema & Migration Architecture

### Alembic Migration: `b2c3d4e5f6a7`
- **File:** [`backend/alembic/versions/2026_10_25_0700-b2c3d4e5f6a7_add_module_5_lifecycle_and_lineage.py`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/alembic/versions/2026_10_25_0700-b2c3d4e5f6a7_add_module_5_lifecycle_and_lineage.py)
- **Down Revision:** `a1b2c3d4e5f6` (Module 4 trust concurrency gate)
- **Engine Support:** PostgreSQL & SQLite batch alter compatible.

### Schema Details

```
                          ┌───────────────────────────┐
                          │    lifecycle_policies     │
                          ├───────────────────────────┤
                          │ id (PK, UUID)             │
                          │ policy_code (String)      │◄──┐
                          │ version (Integer)         │   │
                          │ status (DRAFT/ACTIVE/...) │   │
                          │ is_demo (Boolean)         │   │
                          │ reminder_intervals_json   │   │
                          │ lead_times & tolerances   │   │
                          └─────────────┬─────────────┘   │
                                        │                 │
                   ┌────────────────────┴─────────────────┼────────────────────┐
                   │                                      │                    │
                   ▼                                      ▼                    ▼
     ┌───────────────────────────┐          ┌───────────────────────────┐
     │    instrument_lineages    │          │   lifecycle_evaluations   │
     ├───────────────────────────┤          ├───────────────────────────┤
     │ id (PK, UUID)             │          │ id (PK, UUID)             │
     │ predecessor_id (FK->inst) │          │ instrument_id (FK->inst)  │
     │ successor_id (FK->inst)   │          │ policy_id (FK->policy)    │
     │ institution_id (FK->inst) │          │ evaluation_date (Date)    │
     │ relationship_type         │          │ days_to_maturity (Int)    │
     │ continuity_indicator      │          │ maturity_stage (Enum)     │
     │ validity_gap/overlap_days │          │ due_condition (Enum)      │
     │ concurrency_version (Int) │          │ is_overdue / is_escalated │
     └───────────────────────────┘          │ is_material_transition    │
                                            └───────────────────────────┘
```

#### Table: `lifecycle_policies`
| Column | Type | Constraints / Defaults | Description |
|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | PRIMARY KEY | Unique policy identifier. |
| `policy_code` | `VARCHAR(50)` | NOT NULL, INDEX | Stable identifier across monotonic versions (e.g. `DEFAULT_FDR_MONITORING`). |
| `version` | `INTEGER` | NOT NULL, DEFAULT 1 | Monotonic version number within `policy_code`. |
| `name` | `VARCHAR(255)` | NOT NULL | Human-readable title. |
| `status` | `VARCHAR(50)` | NOT NULL, DEFAULT `DRAFT` | Workflow status (`DRAFT`, `APPROVED`, `ACTIVE`, `INACTIVE`, `SUPERSEDED`). |
| `is_demo` | `BOOLEAN` | NOT NULL, DEFAULT `FALSE` | Explicit synthetic demo designation. |
| `label` | `VARCHAR(255)` | NOT NULL | Prominent disclaimer: `"DEMO POLICY — NOT OFFICIAL AICTE POLICY"`. |
| `timezone` | `VARCHAR(50)` | NOT NULL, DEFAULT `Asia/Kolkata` | Configured boundary timezone for calendar day evaluation. |
| `reminder_intervals_days_json` | `TEXT` | NOT NULL | Configurable JSON array (e.g. `[90, 60, 30, 15, 7]`). |
| `recipient_roles_by_interval_json`| `TEXT` | NOT NULL | Configurable role map per interval (JSON dictionary). |
| `institution_action_lead_days` | `INTEGER` | NOT NULL, DEFAULT 30 | Institution compliance lead time before maturity. |
| `officer_action_lead_days` | `INTEGER` | NOT NULL, DEFAULT 15 | Officer action lead time before maturity. |
| `escalation_interval_days` | `INTEGER` | NOT NULL, DEFAULT 7 | Grace period post-due before escalation triggers. |
| `escalation_target_role` | `VARCHAR(50)` | NOT NULL, DEFAULT `BRANCH_HEAD`| Escalation target official. |
| `maturity_critical_lead_days` | `INTEGER` | NOT NULL, DEFAULT 15 | Critical window threshold before maturity. |
| `renewal_comparison_method` | `VARCHAR(50)` | NOT NULL | Method: `ISSUE_DATE_TO_MATURITY_DATE`. |
| `max_allowed_gap_days` | `INTEGER` | NOT NULL, DEFAULT 0 | Strict continuous validity tolerance (0 = no gap allowed). |
| `max_allowed_overlap_days` | `INTEGER` | NOT NULL, DEFAULT 30 | Permitted pre-rollover overlap window. |

#### Table: `instrument_lineages`
| Column | Type | Constraints / Defaults | Description |
|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | PRIMARY KEY | Unique lineage relationship ID. |
| `predecessor_instrument_id` | `VARCHAR(36)` | FK -> `instruments.id` (RESTRICT) | Predecessor deposit ID. |
| `successor_instrument_id` | `VARCHAR(36)` | FK -> `instruments.id` (RESTRICT) | Successor rollover deposit ID. |
| `institution_id` | `VARCHAR(36)` | FK -> `institutions.id` (RESTRICT) | Enforces tenancy boundary. |
| `relationship_type` | `VARCHAR(50)` | NOT NULL, DEFAULT `RENEWAL` | `RENEWAL`, `REPLACEMENT`, `SPLIT_RENEWAL`. |
| `relationship_status` | `VARCHAR(50)` | NOT NULL, DEFAULT `ACTIVE` | `ACTIVE`, `SUPERSEDED`, `CANCELLED`. |
| `validity_gap_days` | `INTEGER` | Nullable | Calculated difference between dates. |
| `validity_overlap_days` | `INTEGER` | Nullable | Calculated overlap window in days. |
| `continuity_indicator` | `VARCHAR(50)` | NOT NULL | `CONTINUOUS`, `GAP_DETECTED`, `OVERLAP_DETECTED`. |
| `concurrency_version` | `INTEGER` | NOT NULL, DEFAULT 1 | Optimistic concurrency control counter. |
| **Check Constraint** | `ck_lineage_no_self_reference` | `predecessor_id != successor_id` | Anti-self-reference database constraint. |

#### Table: `lifecycle_evaluations`
| Column | Type | Constraints / Defaults | Description |
|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | PRIMARY KEY | Unique evaluation snapshot ID. |
| `instrument_id` | `VARCHAR(36)` | FK -> `instruments.id` (CASCADE) | Evaluated instrument reference. |
| `policy_id` | `VARCHAR(36)` | FK -> `lifecycle_policies.id` (SET NULL) | Policy active at evaluation instant. |
| `evaluation_date` | `DATE` | NOT NULL, INDEX | Calendar date at configured timezone boundary. |
| `evaluation_timestamp` | `TIMESTAMP` | NOT NULL (UTC) | Exact instant of calculation. |
| `days_to_maturity` | `INTEGER` | Nullable | Exact integer days (`maturity_date - evaluation_date`). |
| `maturity_stage` | `VARCHAR(50)` | NOT NULL, INDEX | Derived maturity category. |
| `institution_action_due_date`| `DATE` | Nullable | Calculated compliance action deadline. |
| `officer_action_due_date` | `DATE` | Nullable | Calculated internal review deadline. |
| `is_overdue` | `BOOLEAN` | NOT NULL, DEFAULT 0, INDEX | True if evaluation date exceeds action due date. |
| `is_escalated` | `BOOLEAN` | NOT NULL, DEFAULT 0, INDEX | True if overdue beyond escalation interval. |
| `is_material_transition` | `BOOLEAN` | NOT NULL, DEFAULT 0 | True if state changed from prior evaluation (audited).|

---

## 4. Date & Timezone Semantics

1. **Calendar Date Arithmetic:** Issue and maturity dates are stored as pure SQL `DATE` fields. Date arithmetic operations calculate exact integer day differences without UTC round-trip timezone shifting:
   $$\text{days\_to\_maturity} = \text{maturity\_date} - \text{evaluation\_date}$$
2. **Date Boundary Calculations:** The evaluation date is determined in the policy's configured timezone:
   ```python
   target_tz = ZoneInfo(policy.timezone)  # Default: Asia/Kolkata
   evaluation_date = datetime.now(target_tz).date()
   ```
3. **Pluggable Clock Harness (`Clock`):**
   - [`SystemClock`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/lifecycle/clock.py#L25-L33): Uses actual host time.
   - [`SimulatedClock`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/lifecycle/clock.py#L36-L84): Provides injectable calendar dates, fixed UTC datetimes, and `.advance_days(n)` offsets for deterministic testing and demo scenarios.
4. **Missing or Corrupted Dates:** When an instrument record lacks a valid maturity date, the engine handles it gracefully without throwing unhandled exceptions:
   - `days_to_maturity = None`
   - `maturity_stage = "NOT_EVALUABLE"`
   - `due_condition = "NORMAL"`
5. **Gated Demo Date Advance:** `ENABLE_LIFECYCLE_DATE_ADVANCE: bool = True` in [config.py](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/core/config.py#L85-L87) enables simulation testing. If attempted in a production environment with this flag disabled, the endpoint returns `403 DATE_ADVANCE_DISABLED`.

---

## 5. Lineage Graph Engine & Directed Acyclic Graph (DAG) Rules

The renewal lineage engine in [lineage_service.py](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/lifecycle/lineage_service.py) enforces 6 non-negotiable invariants:

```
                           ALLOWED RENEWAL CHAIN
               ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
               │ Instrument 1 │ ──► │ Instrument 2 │ ──► │ Instrument 3 │
               └──────────────┘     └──────────────┘     └──────────────┘

                          REJECTED: DIRECTED CYCLE
               ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
               │ Instrument 1 │ ──► │ Instrument 2 │ ──► │ Instrument 3 │
               └──────▲───────┘     └──────────────┘     └──────┬───────┘
                      │                                         │
                      └────────────────── X ────────────────────┘
                              (CYCLIC_LINEAGE_DETECTED)
```

1. **Self-Reference Protection:** An instrument cannot be linked as its own predecessor or successor.
2. **Graph Cycle Detection:** Before any link $(P \to S)$ is persisted, the engine traverses ancestor chains using breadth-first search. If $S$ is already an ancestor of $P$, the operation is aborted with `400 CYCLIC_LINEAGE_DETECTED`.
3. **Tenancy Integrity:** Cross-institution renewals are blocked with `400 CROSS_INSTITUTION_LINEAGE_PROHIBITED`. Cross-institution linking is only permitted when explicit authorized merger documentation is provided (`allow_authorized_transfer=True`).
4. **MVP Single-Chain Constraint:** An instrument can have at most one active predecessor and one active successor. Duplicate rollover attempts return `409 DUPLICATE_PREDECESSOR_LINEAGE` or `409 DUPLICATE_SUCCESSOR_LINEAGE`.
5. **Full Lineage Tree Traversal:** The `get_lineage_tree` service traverses both backward (ancestor rollovers with negative depth) and forward (successor rollovers with positive depth) up to 20 generations.
6. **Continuity Assessment:**
   - **Continuous Rollover:** $\text{Successor Issue Date} == \text{Predecessor Maturity Date}$ ($\text{Gap} = 0$, $\text{Overlap} = 0$).
   - **Gap Detected:** $\text{Successor Issue Date} > \text{Predecessor Maturity Date}$ and gap exceeds policy tolerance.
   - **Overlap Detected:** $\text{Successor Issue Date} < \text{Predecessor Maturity Date}$ and overlap exceeds policy window.

---

## 6. Time-Sensitive Evaluation & Material Audit Logging

The evaluation engine distinguishes between routine background checks and significant lifecycle events:

```python
# Material transition condition:
is_material = (
    prior is None
    or prior.maturity_stage != new.maturity_stage
    or prior.is_overdue != new.is_overdue
    or prior.is_escalated != new.is_escalated
    or prior.due_condition != new.due_condition
)
```

- **Routine Daily Checks:** Idempotently records an evaluation snapshot in `lifecycle_evaluations` without flooding system logs.
- **Material State Transitions:** When an instrument crosses into `MATURING_SOON`, `CRITICAL_WINDOW`, `OVERDUE`, or `ESCALATED`, the service generates an immutable audit record via `log_audit_event("LIFECYCLE_STAGE_TRANSITION")`.

---

## 7. REST API Endpoints

Registered under `/api/v1/lifecycle` and `/api/v1/instruments`:

| Method | Endpoint | Access Role | Description |
|:---|:---|:---|:---|
| `POST` | `/api/v1/lifecycle/policies` | `SYSTEM_ADMIN` | Create a new draft policy version. |
| `GET` | `/api/v1/lifecycle/policies` | Authenticated | List all versioned policies (including demo policies). |
| `GET` | `/api/v1/lifecycle/policies/{id}`| Authenticated | Get policy details by ID. |
| `POST` | `/api/v1/lifecycle/policies/{id}/approve` | `SYSTEM_ADMIN`, `COMPETENT_AUTHORITY` | Formally approve a draft policy. |
| `POST` | `/api/v1/lifecycle/policies/{id}/activate` | `SYSTEM_ADMIN` | Activate policy; atomically supersedes prior active version. |
| `POST` | `/api/v1/lifecycle/lineage/renew` | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD` | Link predecessor to successor with cycle validation. |
| `GET` | `/api/v1/lifecycle/lineage/{id}` | Authenticated | Fetch specific lineage edge details. |
| `GET` | `/api/v1/instruments/{id}/lineage` | Authenticated | Fetch full lineage tree (ancestors, successors, direct links). |
| `POST` | `/api/v1/lifecycle/evaluate` | Authenticated | Perform on-demand or demo date-advance evaluation. |
| `GET` | `/api/v1/instruments/{id}/lifecycle`| Authenticated | Fetch latest lifecycle evaluation snapshot. |
| `POST` | `/api/v1/lifecycle/batch-evaluate` | Officer / Admin | Run batch evaluation across multiple instruments. |

---

## 8. Acceptance Verification Results

The test suite in [`backend/tests/test_module5_lifecycle_foundation.py`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/tests/test_module5_lifecycle_foundation.py) verifies all 15 required specifications:

| Test Index | Test Name | Result | Verification Notes |
|:---:|:---|:---:|:---|
| 1 | `test_policy_creation_and_validation` | **PASSED** | Validates monotonic versioning and interval parsing. |
| 2 | `test_rejection_of_invalid_policy_values` | **PASSED** | Rejects empty intervals, negative days, and unapproved activation. |
| 3 | `test_clearly_labelled_synthetic_demo_policy`| **PASSED** | Verifies `is_demo=True` and `"DEMO POLICY — NOT OFFICIAL AICTE POLICY"`.|
| 4 | `test_preservation_of_historical_policy_versions`| **PASSED**| Historical v1 policy retained and queryable after v2 activation. |
| 5 | `test_separate_maturity_and_due_date_concepts` | **PASSED** | Proves administrative status remains unchanged while due status updates. |
| 6 | `test_date_calculations_at_timezone_boundary` | **PASSED** | Confirms UTC 18:45 corresponds to next calendar day in `Asia/Kolkata`. |
| 7 | `test_missing_and_invalid_date_behavior` | **PASSED** | Graceful degradation to `NOT_EVALUABLE` without exceptions. |
| 8 | `test_self_referential_lineage_rejection` | **PASSED** | Rejects linking instrument as its own predecessor. |
| 9 | `test_cyclic_lineage_rejection` | **PASSED** | Blocks directed cycle $i_1 \to i_2 \to i_3 \to i_1$. |
| 10 | `test_cross_institution_lineage_restrictions`| **PASSED** | Blocks cross-college links unless authorized transfer flag is set. |
| 11 | `test_duplicate_link_attempts_rejection` | **PASSED** | Rejects branching duplicate successors in single-chain MVP. |
| 12 | `test_predecessor_history_preservation` | **PASSED** | Proves amount, reference, and trust level remain unmodified. |
| 13 | `test_successor_creation_does_not_release_predecessor`| **PASSED** | Predecessor status remains `REGISTERED`, not `RELEASED`. |
| 14 | `test_lineage_tree_traversal` | **PASSED** | Accurately reconstructs 3-node ancestor and successor tree. |
| 15 | `test_lifecycle_api_endpoints` | **PASSED** | Full HTTP REST endpoint execution via FastAPI TestClient. |

### Global Regression Test Summary
- **Backend Test Suite:** **305 passed** (0 failures, 0 regressions in Modules 1–4).
- **Frontend Test Suite:** **4 passed** (0 failures).
- **Frontend Production Build:** **Compiled cleanly** with `tsc -b && vite build` in 739ms.

---

## 9. Date Calculation Rules & Day-Zero Conventions (Prompt 2)

The lifecycle evaluation engine implements exact, deterministic calendar date semantics:

### Exact Formulae
1. **Days to Maturity:**
   $$\text{days\_to\_maturity} = \text{maturity\_date} - \text{evaluation\_date}$$
2. **Day Zero Semantics:**
   - $\text{days\_to\_maturity} > 0$: The instrument is active. Classified as `MATURING_SOON` or `CRITICAL_WINDOW` if within configured lead days, otherwise `ACTIVE`.
   - $\text{days\_to\_maturity} == 0$: **The maturity date counts as Day Zero** and evaluates to `MaturityStage.MATURED`.
   - $\text{days\_to\_maturity} < 0$: The instrument has passed its maturity date and evaluates to `MaturityStage.EXPIRED`.
3. **Daily Boundary Timezone:**
   - Daily boundaries are calculated strictly within the policy's configured timezone (`Asia/Kolkata` by default).
   - Evaluating at 19:00 UTC on October 25 translates to 00:30 IST on October 26, evaluating under the October 26 boundary.
4. **Action Deadlines vs Maturity:**
   - $$\text{institution\_action\_due\_date} = \text{maturity\_date} - \text{institution\_action\_lead\_days}$$
   - $$\text{officer\_action\_due\_date} = \text{maturity\_date} - \text{officer\_action\_lead\_days}$$
   - When $\text{evaluation\_date} > \text{institution\_action\_due\_date}$, the action is overdue (`is_overdue = True`).
   - When $\text{evaluation\_date} > \text{institution\_action\_due\_date} + \text{escalation\_interval\_days}$, the action is escalated (`is_escalated = True`, `due_condition = ESCALATED`).
5. **Missing or Corrupted Dates:**
   - Missing maturity date evaluates safely to `maturity_stage = NOT_EVALUABLE`, `days_to_maturity = None`, `due_condition = NORMAL`, and `is_overdue = False`.

---

## 10. Scheduled Batch Worker & Concurrency Lease Protection (Prompt 2)

### Bounded Batch Processing
To maintain bounded memory usage, the scheduler processes instruments in discrete batches (default: 50, configurable up to 500) using primary-key ordering:
```sql
SELECT id FROM instruments 
WHERE status IN ('REGISTERED', 'DRAFT', 'UNDER_REVIEW') 
ORDER BY id OFFSET :offset LIMIT :batch_size;
```

### Concurrency Protection via Distributed Job Leases
- **Distributed Lease Locking:** The worker acquires an exclusive lease in `lifecycle_job_runs` before starting.
- **Concurrent Rejection:** If another worker holds an active lease where `status == "RUNNING"` and `lease_expires_at > UTC_NOW()`, incoming runs are rejected with HTTP 409 `CONCURRENT_JOB_RUNNING`.
- **Automatic Crash Recovery:** If a prior worker died leaving an unexpired lease that has since passed (`lease_expires_at <= UTC_NOW()`), the incoming worker marks the stale run as `FAILED` (with diagnostic error reason) and reacquires a fresh lease.
- **Per-Record Error Isolation:** A single malformed record (e.g. corrupted cryptographic verification) does not abort the entire batch. The failed instrument error is logged in `error_summary_json`, `error_count` is incremented, and remaining instruments evaluate normally. The job finishes as `PARTIAL_FAILURE`.

### Evaluation Idempotency
- Running the evaluation multiple times on the same calendar date updates existing `lifecycle_evaluations` records in-place.
- Backed by database unique constraint `uq_eval_instrument_date(instrument_id, evaluation_date)`.
- Eliminates duplicate entries and spurious audit transitions.

---

## 11. Demo Date Advancement & Production Isolation (Prompt 2)

Module 5 provides an injectable simulation clock (`SimulatedClock`) allowing authorized demonstrations and integration tests to move the evaluation date forward without modifying stored database dates.

### Security & Operational Boundaries

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DEMO CLOCK ISOLATION ARCHITECTURE                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Production Lockout:                                                                 │
│    If settings.ENVIRONMENT == "production" OR ENABLE_LIFECYCLE_DATE_ADVANCE is False,  │
│    all advance and reset endpoints return HTTP 403 Forbidden with code                 │
│    "DEMO_CONTROL_DISABLED_IN_PRODUCTION".                                              │
│                                                                                        │
│ 2. Real Data Immutability:                                                             │
│    Advancing the clock shifts only the active Clock provider perspective. Actual       │
│    FDR issue dates and maturity dates in `instruments` remain 100% untouched.          │
│                                                                                        │
│ 3. Explicit Audit Trail:                                                               │
│    Every simulated date advance generates an immutable audit record:                    │
│    action="DEMO_DATE_ADVANCED", entity_id="SIMULATED_CLOCK", with before/after dates.  │
│                                                                                        │
│ 4. Visual Compliance Notice:                                                           │
│    The API returns `disclaimer="DEMO DATE SIMULATION — NOT REAL TIME"`, ensuring the   │
│    frontend banner visibly alerts the user that simulation mode is active.             │
│                                                                                        │
│ 5. Boundary Protection:                                                                │
│    Simulation clock can never elevate trust (L0-L3) or approve releases/refunds.       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Monitoring & Diagnostic APIs (Prompt 2)

Registered under `/api/v1/lifecycle`:

| Method | Endpoint | Access Role | Description |
|:---|:---|:---|:---|
| `GET` | `/api/v1/lifecycle/assessments/{instrument_id}` | Authenticated | Real-time lifecycle assessment for an instrument. |
| `GET` | `/api/v1/lifecycle/monitoring/approaching-maturity` | Tenancy-Scoped | Approaching-maturity instruments (`MATURING_SOON`, `CRITICAL_WINDOW`). |
| `GET` | `/api/v1/lifecycle/monitoring/matured` | Tenancy-Scoped | Matured and expired instruments (`MATURED`, `EXPIRED`). |
| `GET` | `/api/v1/lifecycle/monitoring/overdue` | Tenancy-Scoped | Overdue institution or officer actions (`is_overdue=True` or `is_escalated=True`). |
| `POST` | `/api/v1/lifecycle/scheduler/trigger` | Admin / Officer | Manually trigger bounded evaluation scan. |
| `GET` | `/api/v1/lifecycle/scheduler/runs` | Admin / Officer | List recent job execution logs with error summaries. |
| `GET` | `/api/v1/lifecycle/scheduler/runs/latest` | Authenticated | Fetch latest attempted vs latest successful run status. |
| `GET` | `/api/v1/lifecycle/demo/clock` | Authenticated | Inspect current clock status (real vs simulated). |
| `POST` | `/api/v1/lifecycle/demo/advance-clock` | Admin / Officer | Advance simulation clock forward (Demo/Dev mode only). |
| `POST` | `/api/v1/lifecycle/demo/reset-clock` | `SYSTEM_ADMIN` | Reset simulation clock to host OS time. |

### Tenancy & Scoping Rules
- **Institution Scope:** Users with role `ROLE_INSTITUTION_USER` only see instruments belonging to their own `institution_id`.
- **Officer/Admin Scope:** Officers and System Admins see all instruments across institutions with optional filtering by `institution_id` or `office`.
- **Cross-Module Surfacing:** The monitoring items surface Module 3 open findings count (`unresolved_findings_count`) and Module 4 bank verification status (`verification_status`) without duplicate data storage.

---

## 13. Operational Startup Guide

### Starting the API Server
```powershell
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running the Scheduled Batch Worker
The batch scan engine can be invoked as a standalone CLI job or via a cron/scheduled task:
```powershell
cd backend
python -c "from app.db.session import SessionLocal; from app.modules.lifecycle.scheduler import execute_lifecycle_scan_job; db = SessionLocal(); execute_lifecycle_scan_job(db, job_type='DAILY_MATURITY_SCAN', trigger_source='CRON_WORKER'); db.close()"
```

---

## 14. Acceptance Verification Matrix

### Prompt 1: Foundation & Lineage Tests (`test_module5_lifecycle_foundation.py`)
15/15 tests passed covering policy versioning, cycle detection, and lineage DAGs.

### Prompt 2: Scheduler & Monitoring Tests ([`backend/tests/test_module5_prompt2_scheduler.py`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/tests/test_module5_prompt2_scheduler.py))

| Specification | Test Function | Result | Verification Notes |
|:---:|:---|:---:|:---|
| 1 | `test_maturity_calculation_before_on_and_after_date` | **PASSED** | Verifies future ($>0$), Day Zero ($=0$), and past ($<0$) maturity calculations. |
| 2 | `test_configured_approaching_maturity_thresholds` | **PASSED** | Instruments $\le 30$ days evaluated as `MATURING_SOON`, $> 30$ days as `ACTIVE`. |
| 3 | `test_unconfigured_threshold_behavior` | **PASSED** | Sparse policy intervals return `DueCondition.NORMAL` without inventing AICTE rules. |
| 4 | `test_separate_institution_and_officer_due_dates` | **PASSED** | Proves separate lead days (15d vs 7d) and distinct overdue transitions. |
| 5 | `test_timezone_boundary_behavior` | **PASSED** | 19:00 UTC Oct 25 evaluates to Oct 26 under `Asia/Kolkata` daily boundary. |
| 6 | `test_missing_and_invalid_date_handling` | **PASSED** | Missing maturity date evaluates to `NOT_EVALUABLE` without exceptions. |
| 7 | `test_evaluation_idempotency` | **PASSED** | Repeated runs on same date update existing row in-place; count remains 1. |
| 8 | `test_multiple_worker_concurrent_evaluation_protection`| **PASSED** | Active unexpired lease rejects concurrent worker with HTTP 409. |
| 9 | `test_partial_batch_failure_and_recovery` | **PASSED** | Isolated error logs error summary; other instruments succeed; `PARTIAL_FAILURE`. |
| 10 | `test_worker_restart_and_stale_lease_recovery` | **PASSED** | Crashed run marked `FAILED`; fresh worker reacquires lease without deadlock. |
| 11 | `test_accurate_job_run_summaries` | **PASSED** | Job run record persists accurate eligible, evaluated, success, error, and stage counts. |
| 12 | `test_demo_date_advancement_changes_simulation_results_only` | **PASSED** | Shifted perspective modifies evaluation output; real FDR dates remain untouched. |
| 13 | `test_demo_date_control_unavailable_in_production` | **PASSED** | `ENVIRONMENT="production"` blocks demo clock endpoints with HTTP 403 Forbidden. |
| 14 | `test_no_trust_promotion_or_release_approval_from_maturity_evaluation` | **PASSED** | Evaluating matured FDR does not promote `trust_level` or approve release. |
| 15 | `test_monitoring_apis_tenancy_and_filtering` | **PASSED** | Institution user sees only own college; officer sees cross-institution records. |

### Global Regression Test Summary
- **Total Backend Tests:** **320 passed** in 13.71s (0 failures, 0 regressions across Modules 1–5).
- **Frontend Production Bundle:** **Compiled cleanly** in 449ms with zero TypeScript or build errors.

---

---

## 15. Policy-Driven Reminders, Delivery History, Escalation and Failure Recovery (Prompt 3 Architecture)

Prompt 3 builds an auditable, multi-channel reminder and escalation engine integrated directly with the maturity monitoring engine from Prompt 2.

### 15.1 Core Architecture Principles
1. **Separation of Policy Configuration from Regulatory Reality:** Reminder milestones (e.g., 90, 60, 30, 15, 7 days) and escalation delays are stored in versioned policies (`LifecyclePolicy`). If a policy is unconfigured, intervals are not invented.
2. **Honest Delivery Attribution:**
   - `IN_APP` notifications are immediately marked `DELIVERED` upon database persistence into the recipient's inbox.
   - `EMAIL` notifications without delivery-receipt webhooks are marked `ACCEPTED` when handed to the SMTP server, or `MOCKED` (`QUEUED_FOR_LOCAL_MAIL_CATCHER`) when in development/mock mode. They are **never** falsely claimed as `DELIVERED` merely because a request was constructed.
   - External mock channels (SMS / WhatsApp) are explicitly marked `MOCKED` with disclaimer metadata.
3. **Strict Tenancy and Recipient Resolution:**
   - Institution reminders strictly resolve to active users of that specific institution (`INSTITUTION_USER`).
   - If an institution or regional office has no active user, the system records an audited `CONFIGURATION_ERROR` with status `FAILED` rather than silently routing the notice to an arbitrary administrator.
4. **Idempotency & Concurrent Dispatch Safety:** Stable composite idempotency key prevents duplicate communications across scheduler reruns, worker restarts, or concurrent dispatches.
5. **No Side-Effect State Alterations:** The notification engine never alters an instrument's trust level (L0–L3), never authorizes release, and never marks a renewal complete.

---

## 16. Multi-Channel Notification Providers

The channel subsystem implements a pluggable provider interface in `app/modules/lifecycle/channels/`:

```
backend/app/modules/lifecycle/channels/
├── base.py         # Abstract NotificationChannelProvider & DeliveryResult
├── in_app.py       # InAppNotificationProvider (in-app inbox, status=DELIVERED)
├── email.py        # EmailNotificationProvider (SMTP/local catcher, status=ACCEPTED/MOCKED)
├── mock_sms.py     # MockSmsProvider (explicitly simulated, status=MOCKED)
├── registry.py     # Provider factory registry with custom provider support
└── __init__.py     # Package exports
```

### Channel Delivery Semantics

| Channel | Provider Class | Development Status | Production Status | Delivery Receipt Attribution |
|:---:|:---:|:---:|:---:|:---|
| `IN_APP` | `InAppNotificationProvider` | `DELIVERED` | `DELIVERED` | Immediate database persistence into user notification inbox. |
| `EMAIL` | `EmailNotificationProvider` | `MOCKED` / `ACCEPTED` | `ACCEPTED` | Handshake confirmed with MTA. Labeled `QUEUED_FOR_LOCAL_MAIL_CATCHER` in dev. |
| `MOCK_SMS` | `MockSmsProvider` | `MOCKED` | Disabled / Mock | Explicitly simulated with label `MOCKED — LOCAL DEMO ENVIRONMENT`. |

---

## 17. Notification Data Models & Migration

Applied migration `2026_10_25_0900-d4e5f6a7b8c9_add_lifecycle_notifications.py` introducing two primary tables:

### 17.1 `lifecycle_notifications`
- **Identity & Idempotency:** `id` (UUID), `idempotency_key` (Unique composite string).
- **Relationships:** `instrument_id`, `institution_id`, `policy_id`, `policy_version`.
- **Event Metadata:** `event_type` (`MATURITY_MILESTONE_REMINDER`, `INSTITUTION_ACTION_DUE`, `OFFICER_ACTION_DUE`, `ACTION_OVERDUE`, `ACTION_ESCALATED`), `reminder_milestone_days`, `trigger_date`.
- **Recipient Identity:** `recipient_role`, `recipient_user_id`, `recipient_email`, `recipient_name`.
- **Delivery State:** `channel`, `status` (`CREATED`, `ATTEMPTED`, `ACCEPTED`, `DELIVERED`, `FAILED`, `MOCKED`).
- **Audit & Timestamps:** `scheduled_at`, `first_attempted_at`, `last_attempted_at`, `delivered_at`, `failed_at`.
- **Retry Mechanics:** `retry_count`, `max_retries`, `next_retry_at`, `failure_category`, `failure_reason`.
- **Simulation Disclaimer:** `is_mock` (Boolean), `mock_disclaimer` (Text).

### 17.2 `notification_delivery_attempts`
- **Attempt Tracking:** `id`, `notification_id` (Foreign Key), `attempt_number`.
- **Execution Log:** `attempted_at`, `channel`, `status`, `duration_ms`.
- **Provider Feedback:** `provider_response_code`, `provider_reference_id`.
- **Failure Diagnostics:** `error_category` (`INVALID_RECIPIENT`, `PROVIDER_UNAVAILABLE`, `AUTHENTICATION_ERROR`, `CONFIGURATION_ERROR`, `RETRY_EXHAUSTED`), `error_message`.

---

## 18. Deduplication & Idempotency Key Semantics

The composite idempotency key is deterministically generated via:
```python
idempotency_key = f"notif:{instrument_id}:{event_type}:{milestone_days}:{trigger_date.isoformat()}:{recipient_identifier}:{channel}"
```
- **Rerun Invariance:** Rerunning daily batch scans on the same calendar date for the same milestone produces zero duplicate database rows.
- **Worker Concurrency:** Enforced via `UNIQUE CONSTRAINT (idempotency_key)` on the database table.
- **Retry Distinction:** Retries reuse the exact same `LifecycleNotification` record, appending a new row to `notification_delivery_attempts` and incrementing `retry_count`.

---

## 19. Bounded Retry & Failure Recovery

The recovery engine handles external failure modes without infinite retry loops:
- **Missing Recipient:** Instantly fails with `failure_category="CONFIGURATION_ERROR"`, `status="FAILED"`. Does not route to random admin.
- **Provider Outage:** Increments `retry_count`, logs `PROVIDER_UNAVAILABLE`, calculates `next_retry_at`.
- **Retry Exhaustion:** When `retry_count >= max_retries`, transitions permanently to `RETRY_EXHAUSTED` with `status="FAILED"`.
- **Manual Administrative Retry:** Privileged operators (`SYSTEM_ADMIN`, `SCRUTINY_OFFICER`) can trigger controlled retries via `POST /api/v1/lifecycle/notifications/{id}/retry`.

---

## 20. Module 5 Prompt 3 REST APIs

| Method | Endpoint | Authorized Roles | Purpose |
|:---:|:---|:---:|:---|
| `GET` | `/api/v1/lifecycle/instruments/{id}/notifications` | Tenancy Scoped | List complete notification history and attempt logs for an instrument. |
| `GET` | `/api/v1/instruments/{id}/notifications` | Tenancy Scoped | Direct alias for instrument notification history. |
| `GET` | `/api/v1/lifecycle/notifications/inbox` | Authenticated | List current user's in-app inbox notifications. |
| `POST` | `/api/v1/lifecycle/notifications/{id}/read` | Notification Recipient | Mark in-app notification as read. |
| `GET` | `/api/v1/lifecycle/notifications/failed` | Admin / Officer / Branch Head | Audit queue of failed deliveries requiring operator intervention. |
| `POST` | `/api/v1/lifecycle/notifications/{id}/retry` | Admin / Scrutiny Officer | Controlled manual retry of a failed notification. |
| `POST` | `/api/v1/lifecycle/notifications/dispatch-due` | Admin / Scrutiny Officer | On-demand batch evaluation and reminder dispatch. |

---

## 21. Frontend UI Integration

### 21.1 Lifecycle Notification History Component
Implemented in `frontend/src/features/lifecycle/LifecycleNotificationHistory.tsx` and embedded directly in `InstrumentDetailPage.tsx`:
- **Real-Time Lifecycle Health Bar:** Displays current maturity stage, days remaining, statutory validity, action due dates, and escalation condition.
- **Audited Reminder Timeline:** Visual cards for each dispatched reminder showing event type badge, T-Minus milestone badge, channel badge (`IN_APP`, `EMAIL`, `MOCK_SMS`), and delivery status badge.
- **Delivery Receipt Transparency:** Clearly displays `CONFIRMED DELIVERED` (green) for in-app, `PROVIDER ACCEPTED` (blue) for SMTP relay, `MOCKED` (amber) with local mail catcher notice, or `DELIVERY FAILED` (red).
- **Expandable Attempt Logs:** Drill-down view of each transmission attempt with attempt numbers, provider reference IDs, timestamps, and failure explanations.
- **Administrative Action:** Controlled manual retry button on failed deliveries, and batch due-reminder dispatch trigger for officers.

---

## 22. Acceptance Verification Matrix

### Prompt 3: Reminders, Delivery History & Escalation ([`backend/tests/test_module5_prompt3_reminders.py`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/tests/test_module5_prompt3_reminders.py))

| Specification | Test Function | Result | Verification Notes |
|:---:|:---|:---:|:---|
| 1 | `test_01_reminders_generated_at_configured_milestones` | **PASSED** | Generates `MATURITY_MILESTONE_REMINDER` records at T-30d with `IN_APP` and `EMAIL` channels. |
| 2 | `test_02_unconfigured_policy_does_not_produce_invented_intervals` | **PASSED** | Sparse policy with empty milestones generates 0 invented reminder notices. |
| 3 | `test_03_correct_institution_recipient_resolution` | **PASSED** | `INSTITUTION_USER` recipient strictly matches institution; never leaks to other colleges. |
| 4 | `test_04_role_based_escalation` | **PASSED** | Overdue actions exceeding escalation delay generate `ACTION_ESCALATED` to `BRANCH_HEAD`. |
| 5 | `test_05_idempotency_under_rerun_and_restart` | **PASSED** | Rerunning dispatch on same day creates 0 duplicate notifications; IDs and counts identical. |
| 6 | `test_06_concurrent_dispatch_protection` | **PASSED** | Database unique constraint on composite idempotency key blocks concurrent duplication. |
| 7 | `test_07_failed_provider_retry` | **PASSED** | Manual retry increments `retry_count`, creates audited attempt, updates delivery state. |
| 8 | `test_08_permanent_failure_and_retry_exhaustion` | **PASSED** | Notifications reaching `max_retries` are rejected with `RETRY_EXHAUSTED` (HTTP 400). |
| 9 | `test_09_accurate_notification_history` | **PASSED** | Full attempt history preserved with attempt numbers, provider response codes, and errors. |
| 10 | `test_10_no_false_delivered_state` | **PASSED** | Email marked `ACCEPTED`/`MOCKED`, never falsely claimed `DELIVERED`. In-app is `DELIVERED`. |
| 11 | `test_11_missing_recipient_handling` | **PASSED** | Empty institution records `CONFIGURATION_ERROR` (status `FAILED`); no arbitrary admin routing. |
| 12 | `test_12_resolved_actions_stop_escalating_appropriately` | **PASSED** | Closed/resolved instruments produce 0 reminders and 0 escalation notices. |
| 13 | `test_13_cross_tenant_notification_privacy` | **PASSED** | College A user cannot access College B notification history (HTTP 403) or inbox items. |
| 14 | `test_14_demo_and_mock_labels` | **PASSED** | Unconfigured/mock providers set `is_mock=True` and clear disclaimer notices. |
| 15 | `test_15_no_trust_or_release_changes_as_reminder_side_effect` | **PASSED** | Reminders and escalations leave `trust_level` and instrument status strictly unaltered. |

### Global Quality Check Status
- **Backend Test Suite:** **335 passed** across all modules (Modules 1–4 and Module 5 Prompts 1, 2, and 3).
- **Frontend Production Bundle:** **Compiled cleanly** with `tsc -b && vite build` in 455ms.
- **Database Schema:** Alembic migration `d4e5f6a7b8c9` applied and verified.


