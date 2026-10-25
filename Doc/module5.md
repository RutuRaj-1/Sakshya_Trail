# Module 5 — Lifecycle Orchestration, Policy Configuration and Renewal Lineage
## Comprehensive Architecture, Data Foundation & Technical Specifications Guide (Prompt 1 of 5)

> **Module Status:** Foundational Architecture & Lineage Engine Implemented (Prompt 1 of 5 Verified)  
> **Alembic Revision:** `b2c3d4e5f6a7` — Lifecycle Policies, Instrument Lineages & Lifecycle Evaluations  
> **Backend Test Suite:** **305 passed** across all modules in 14.29s — **0 failures, 0 regressions**  
> **Module 5 Foundation Tests:** **15 passed** (100% green coverage on all Prompt 1 acceptance criteria)  
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

## 9. Next Steps for Prompt 2

With the foundational data models, policy versioning, and renewal-lineage graph engine verified, development proceeds to **Prompt 2**:
1. Implement the background worker and scheduler for periodic daily date-boundary evaluations.
2. Build missed-run recovery and backpressure controls.
3. Integrate notification delivery attempts and recipient role dispatching.
