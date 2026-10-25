# Module 7: Unified Search, Record Drill-Down, Historical Timelines & Append-Only Scrutiny Observations

**Project:** FDR Sentinel (SIH 2026 Problem Statement ID 26265)  
**Module:** Module 7 — Command Center, Search, Reporting & Audit  
**Status:** Completed (Prompt 3 of 5)

---

## 1. Architecture Overview

Prompt 3 implements the unified search and deep historical drill-down capabilities needed to let authorized users locate an instrument or release case, understand its current administrative, trust, and term states, and reconstruct all relevant actions over its lifecycle.

```
+-----------------------------------------------------------------------------------------------------+
|                                          UNIFIED SEARCH DESK                                        |
|  - FDR Instruments Search (/dashboard/search/instruments)                                           |
|  - Release & Refund Cases Search (/dashboard/search/release-cases)                                   |
|  - Parameterized Backend SQL Queries | Role Scope Enforcement | Query Parameter URL Sync             |
+-----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+-----------------------------------------------------------------------------------------------------+
|                                 INSTRUMENT DETAIL & HISTORICAL DRILL-DOWN                           |
|  - Tab 1: Current Snapshot (Administrative Status vs Evidentiary Trust Level vs Term Window)        |
|  - Tab 2: Document History (v1..vN versions, SHA-256 byte hashes, protected download endpoint)     |
|  - Tab 3: Field Provenance (Audited value changes, previous values, actor ID, evidence provenance)  |
|  - Tab 4: Lifecycle & Lineage (Maturity evaluations, SIMULATED vs Live verifications, renewals)     |
|  - Tab 5: Append-Only Scrutiny Observations (Immutable notes, supersession chains, resolve reasons)  |
|  - Tab 6: Audit Timeline (Chronological material events with metadata inspection)                   |
+-----------------------------------------------------------------------------------------------------+
```

---

## 2. Unified Search Engine (`search_service.py`)

### Supported Filters

The search endpoints (`/api/v1/dashboard/search/instruments` and `/api/v1/dashboard/search/release-cases`) support the following parameterized query parameters:

| Filter Parameter | Target Field / Entity | Description & Behavior |
|:---|:---|:---|
| `q` | `reference_number`, `legal_name`, `bank_name` | Global case-insensitive substring search across reference, institution, or bank. |
| `institution` | `institutions.legal_name` / `display_name` | Filters by institution name. |
| `bank` | `instruments.bank_name` | Filters by issuing bank name. |
| `reference` | `instruments.reference_number` | Filters by exact or prefix reference number. |
| `status` | `instruments.status` / `release_requests.workflow_status` | Procedural administrative state (`REGISTERED`, `ACTIVE`, `MATURED`, `RELEASED`, etc.). |
| `trust_level` | `instruments.trust_level` | Evidentiary verification tier (`L0_DECLARED`, `L1_DOCUMENT_CONSISTENT`, `L2_OFFICER_VERIFIED`, `L3_BANK_CONFIRMED`). |
| `assigned_office` | `assigned_office` | Filters by regional office (e.g. `Northern Regional Office`, `Western Regional Office`, `HQ`). |
| `issue_date_from` / `to` | `instruments.issue_date` | Filters deposit issue dates within the specified date boundary. |
| `maturity_date_from` / `to`| `instruments.maturity_date` | Filters deposit maturity dates within the specified date boundary. |
| `has_discrepancies` | `validation_findings` | When `true`, returns only instruments with active (`OPEN`, `IN_REVIEW`) discrepancies. |
| `priority_category` | Derived score / flags | `CRITICAL_OVERDUE` (overdue > 30d), `EXPIRING_30D` (days <= 30), `DISCREPANCY_FLAGGED`, `UNVERIFIED` (L0). |
| `readiness_outcome` | `readiness_assessments.assessment_outcome` | Case readiness outcome (`READY`, `BLOCKED`, `CONDITIONAL`). |
| `sort_by` & `sort_order` | Allowlisted columns | Strictly validated against allowlist (`reference_number`, `amount`, `maturity_date`, `created_at`, `status`, `trust_level`, `bank_name`). |
| `skip` & `limit` | Pagination | Clamped pagination (limit max 100). |

### Multi-Tenant Scope & Security Enforcement

Search queries apply tenant isolation **before** executing SQL filters:
- **`INSTITUTION_USER`**: Enforced to `Instrument.institution_id == current_user.institution_id`. Any query attempting to specify another institution is overridden or denied. Cross-tenant search queries return 0 results without leaking the existence of other records.
- **Bureau Roles (`SCRUTINY_OFFICER`, `BRANCH_HEAD`, `SYSTEM_ADMIN`, `AUDITOR`)**: Permitted to search across all authorized institutions and regional offices.
- **Auditor Role**: Search and history access is strictly read-only. Attempting to create or modify observations returns `403 FORBIDDEN`.

---

## 3. Instrument Detail & Multi-Dimensional Snapshot (`history_service.py`)

Accessed via `GET /api/v1/dashboard/instruments/{instrument_id}/detail`.

### A. Current Snapshot & Concept Distinction

The UI and API strictly distinguish three orthogonal state concepts:
1. **Administrative Status:** Procedural workflow state (`DRAFT`, `REGISTERED`, `LODGED`, `ACTIVE`, `EXPIRED`, `MATURED`, `INVOKED`, `DISCHARGED`, `RELEASED`).
2. **Evidentiary Trust Level:** Verified trustworthiness (`L0_DECLARED`, `L1_DOCUMENT_CONSISTENT`, `L2_OFFICER_VERIFIED`, `L3_BANK_CONFIRMED`).
3. **Maturity / Validity Window:** Calendar-based deposit status (`ACTIVE`, `EXPIRING_SOON`, `OVERDUE`).

### B. Document History & Cryptographic Hashes

- Returns all document versions (`DocumentVersion`) associated with the instrument.
- Exposes version number, upload timestamp, uploader name/role, and SHA-256 byte digest.
- **Protected Access:** Never exposes raw internal storage paths or public URLs. Downloads are brokered through `/api/v1/documents/{document_id}/versions/{version_number}/content` with strict authorization checks.
- **Integrity Notice:** Hash equality verifies identical bytes; it does not substitute for substantive legal/bank verification.

### C. Field History & Provenance

- Returns field-level changes recorded in `field_provenances`.
- Exposes `field_name`, `recorded_value`, `previous_value`, `source_type` (`OCR_EXTRACTION`, `USER_MANUAL`, `BANK_API`, `ADMIN_OVERRIDE`), `actor_name`, `evidence_reference`, and `reason`.
- **Policy Masking:** Sensitive internal notes or officer remarks are masked at the service layer as `*** MASKED PER POLICY ***` for `INSTITUTION_USER` roles.

### D. Lifecycle, Lineage & Simulated Verification Labeling

- Merges `lifecycle_evaluations`, `verification_requests`, and `instrument_lineage`.
- **Simulation Flagging:** Verification requests that utilize simulated banking adapters or simulation channels are tagged with `is_simulated: true` and rendered with a distinct, prominent `SIMULATED ADAPTER` badge. Simulated bank responses are never masqueraded as real host-to-host bank confirmation.
- **Lineage:** Preserves bidirectional renewal links (`predecessor_instrument_id` and `successor_instrument_id`) with relationship status.

### E. Material Audit Timeline

- Aggregates chronological events from `audit_events` matching the instrument ID or reference.
- Exposes action, timestamp, actor ID/email, summary, and parsed metadata.

---

## 4. Append-Only Scrutiny Observations (`observation_service.py`)

Implements PRD-FR-072 and PRD-FR-073 requirements that scrutiny observations retain immutable authorship and complete revision history.

### Data Model (`scrutiny_observations` table)

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | Primary Key | UUID identifier. |
| `instrument_id` | `VARCHAR(36)` | FK to `instruments.id`, Index | Associated instrument. |
| `release_request_id` | `VARCHAR(36)` | FK to `release_requests.id`, Index | Associated release case (if applicable). |
| `observation_category` | `VARCHAR(50)` | Not Null | `GENERAL`, `DISCREPANCY`, `DOCUMENT`, `MANDATE`, `COMPLIANCE`. |
| `observation_text` | `TEXT` | Not Null | Content of the scrutiny note (immutable once written). |
| `author_user_id` | `VARCHAR(36)` | FK to `users.id`, Index | Immutable author ID. |
| `author_role` | `VARCHAR(50)` | Not Null | Author role at time of writing. |
| `status` | `VARCHAR(30)` | Not Null | `RECORDED`, `AMENDED`, `SUPERSEDED`, `RESOLVED`. |
| `supersedes_id` | `VARCHAR(36)` | FK to `scrutiny_observations.id` | Backlink to the prior observation this note supersedes. |
| `superseded_by_id` | `VARCHAR(36)` | FK to `scrutiny_observations.id` | Forward pointer to the replacement observation note. |
| `resolution_reason` | `TEXT` | Nullable | Mandatory rationale supplied upon resolving a note. |
| `resolved_at` | `TIMESTAMP WITH TIME ZONE` | Nullable | Timestamp of resolution. |
| `resolved_by_user_id`| `VARCHAR(36)` | FK to `users.id` | Resolver user ID. |
| `is_internal_only` | `BOOLEAN` | Default `False` | When `True`, note is concealed from institution users. |
| `created_at` / `updated_at` | `TIMESTAMP WITH TIME ZONE` | Not Null | Audit timestamps. |

### Revision Semantics

1. **No In-Place Overwriting:** When an observation is corrected or updated via `POST /api/v1/dashboard/observations/{id}/amend`, the original observation is marked `SUPERSEDED` with `superseded_by_id` set to the new record ID. The original text and author are preserved untouched.
2. **Mandatory Amendment Rationale:** The amendment payload requires `amendment_reason` (min 3 chars). The new observation record is created with `supersedes_id` pointing to the previous note, establishing a bidirectional audit trail.
3. **Reasoned Resolution:** Resolving an observation via `POST /api/v1/dashboard/observations/{id}/resolve` requires a non-empty `resolution_reason` explaining why the observation was resolved.
4. **Discrepancy Separation:** Scrutiny observations cannot directly clear or dismiss validation discrepancy findings. Dismissal or resolution of discrepancy findings must use the formal review workflow on `/api/v1/findings/*`.

---

## 5. Security & Access Control Matrix

| Endpoint | Method | Allowed Roles | Isolation Rule |
|:---|:---|:---|:---|
| `/api/v1/dashboard/search/instruments` | GET | All authenticated | Scoped to own institution for `INSTITUTION_USER`. |
| `/api/v1/dashboard/search/release-cases` | GET | All authenticated | Scoped to own institution for `INSTITUTION_USER`. |
| `/api/v1/dashboard/instruments/{id}/detail` | GET | Authorized users | 404 if record belongs to another institution. |
| `/api/v1/dashboard/instruments/{id}/observations` | GET | Authorized users | Internal notes excluded for `INSTITUTION_USER`. |
| `/api/v1/dashboard/instruments/{id}/observations` | POST | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDIT_EXAMINER` | Denied for `AUDITOR` and `INSTITUTION_USER`. |
| `/api/v1/dashboard/observations/{id}/amend` | POST | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDIT_EXAMINER` | Denied for `AUDITOR` and `INSTITUTION_USER`. |
| `/api/v1/dashboard/observations/{id}/resolve` | POST | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDIT_EXAMINER` | Denied for `AUDITOR` and `INSTITUTION_USER`. |

---

## 6. Unavailable History Fields & Future Scope

- **Raw Storage Paths:** Internal file system paths and private object-store keys are withheld to prevent security leakage.
- **Cryptographic Audit Chain Verification:** Full Merkle tree / HMAC sequence verification of the audit chain is implemented in Prompt 5.
- **Natural Language / Vector Search:** Semantic similarity search is planned as an optional future capability and is not part of this deterministic SQL search engine.
