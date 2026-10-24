# Module 4 — Trust, Provenance & Verification Desk
## Field-Level Provenance, Verification Requests, Responses & Adapter Architecture

> **Stage:** Module 4, Prompt 2 of 5 Complete  
> **Alembic Revisions:** `c5e8f1a3d9b4` (Foundational Tables) & `e7f2a1b9c3d4` (Adapter Columns)  
> **Backend Test Suite:** **246 passed** across all modules in 11.02s (18 new Prompt 2 tests + 12 Prompt 1 tests) — **0 failures**  
> **Frontend:** `tsc -b && vite build` built cleanly in 439ms — **0 errors**  
> **Date:** October 2026  
> **Repository:** `FDR_Sentinel`

---

## 1. Executive Summary & Architecture

Module 4 implements the core evidentiary trust foundation of FDR Sentinel:
1. **Field-Level Provenance:** Append-only custody chains tracking who declared or modified each field, when, and with what evidence (`field_provenances`).
2. **Four-Tier Trust State Model:** Separation of administrative status from evidentiary certainty (`L0_DECLARED`, `L1_DOCUMENT_CONSISTENT`, `L2_OFFICER_VERIFIED`, `L3_BANK_CONFIRMED`).
3. **Verification Request & Response Workflow:** Secure, non-guessable request codes (`VR-SEC-XXXXXXXXXXXX`), frozen snapshots, attempt counters, and field-by-field reconciliation.
4. **Adapter Architecture (3 Distinct Paths):**
   - **Manual Evidence Adapter (`MANUAL`):** External physical/speed-post correspondence recorded by authorized officers, linked to Module 2 documentary evidence with explicit non-machine disclaimers.
   - **Simulated Prototype Adapter (`SIMULATED`):** Reproducible, deterministic simulation of `MATCH`, `MISMATCH`, `TIMEOUT`, `SOURCE_UNAVAILABLE`, and `INCONCLUSIVE` outcomes for development and demos. Strictly disabled in production configuration; barred from granting `L3_BANK_CONFIRMED`.
   - **Live Bank Adapter Boundary (`LIVE_BANK_API`):** Integration interface for future direct core banking API or SFTP connections. Reports honestly that live integration is unconfigured when bank credentials are not provisioned.

---

## 2. Verification Request Lifecycle & State Model

```
       ┌──────────┐
       │  DRAFT   │
       └────┬─────┘
            │ (Initiate by authorized officer)
            ▼
       ┌──────────┐
       │ PENDING  │
       └────┬─────┘
            │ (Dispatch via adapter)
            ▼
       ┌──────────┐
       │   SENT   │
       └────┬─────┘
            ├───────────────────────────────────────────────────────┐
            │                                                       │
            ▼ (Adapter response ingested)                           ▼ (Network / provider error)
    ┌───────────────┐                                       ┌───────────────┐
    │     MATCH     │ (Reconciled with no discrepancies)    │    TIMEOUT    │
    └───────────────┘                                       └───────┬───────┘
            │                                                       │
    ┌───────────────┐                                       ┌───────┴───────┐
    │   MISMATCH    │ (Conflicting fields recorded)         │SOURCE_UNAVAIL.│
    └───────────────┘                                       └───────┬───────┘
            │                                                       │ (Retry if attempt < 3)
            │                                                       ▼
            │                                               ┌───────────────┐
            │                                               │   CANCELLED   │ (Reason required)
            │                                               │    / CLOSED   │
            │                                               └───────────────┘
```

### Request Lifecycle Guarantees
- **Non-Guessable Unique Reference Code:** Every request generates a secure code `VR-SEC-<unique-hex>` that is never reused across requests or instruments.
- **Frozen Fact Snapshot:** Freezes all registered instrument facts at dispatch time (`snapshot_data_json`).
- **No Premature Matches:** A request is never marked `MATCH` until a qualifying confirmation response has been evaluated.
- **Non-Destructive Mismatch Handling:** When divergent bank values are returned, instrument fields are **never overwritten**. Both registered facts and bank values are preserved side-by-side in `field_comparisons_json`.
- **Bounded Retries:** Requests in `TIMEOUT` or `SOURCE_UNAVAILABLE` can be retried up to `MAX_VERIFICATION_RETRY_ATTEMPTS` (3). The request code remains stable across attempts.

---

## 3. Verification Adapter Implementations

### Path A: Manual Evidence Path (`ManualVerificationAdapter`)
- **Channel:** `MANUAL` / `AUTHORIZED_MANUAL`.
- **Use Case:** An authorized regulatory scrutiny officer receives an official branch letter, bank seal certificate, or registered speed-post confirmation.
- **Requirements:**
  - Requires `SCRUTINY_OFFICER`, `BRANCH_HEAD`, or `SYSTEM_ADMIN` role.
  - External communication date/time and external reference number.
  - Mandatory justification reason.
  - Mandatory link to Module 2 document version (`DocumentVersion`).
- **Classification:** Stored with `source_classification = MANUAL_EVIDENCE` and `is_simulated = False`.
- **Statutory Disclaimer:**
  > *"The system recorded an authorized officer's manual verification evidence, NOT a machine-authenticated direct bank response. Governed by regulatory scrutiny review."*
- **Trust Implications:** Can support `L2_OFFICER_VERIFIED` promotion, but does **NOT** automatically grant `L3_BANK_CONFIRMED`.

### Path B: Simulated Adapter (`SimulatedBankAdapter`)
- **Channel:** `SIMULATED`.
- **Use Case:** Controlled demonstration and testing of automated verification without external network calls.
- **Deterministic Scenarios:**
  - `MATCH`: Returns identical instrument facts.
  - `MISMATCH`: Returns conflicting deposit amount (85% of registered) and divergent maturity date (+1 year).
  - `TIMEOUT`: Simulates gateway socket read timeout (30,000ms).
  - `SOURCE_UNAVAILABLE`: Simulates core banking portal downtime / HTTP 503 maintenance.
  - `INCONCLUSIVE`: Simulates unverified deposit state (e.g. `PENDING_CLEARANCE`).
- **Production Safety Controls:**
  - Strictly blocked if `settings.ENVIRONMENT == "production"` or `settings.ENABLE_SIMULATED_VERIFICATION == False` (`403 SIMULATION_DISABLED_IN_PRODUCTION`).
  - Carries `is_simulated = True` and `source_classification = SIMULATION`.
  - **Barred from Production L3:** Centralized trust gatekeeper strictly rejects simulated responses for `L3_BANK_CONFIRMED` (`422 SIMULATED_RESPONSE_CANNOT_AUTHORIZE_L3`).

### Path C: Live Bank Adapter Interface (`LiveBankVerificationAdapter`)
- **Channel:** `LIVE_BANK_API` / `DIRECT_API` / `SFTP_BATCH`.
- **Use Case:** Future direct banking integrations (e.g. NPCI, SFMS, or bilateral core banking APIs).
- **Honest Boundary Enforcement:**
  - Current AICTE project documents establish no live banking partner credentials.
  - If invoked while `settings.LIVE_BANK_ADAPTER_ENABLED == False`, it returns `503 LIVE_BANK_INTEGRATION_UNCONFIGURED` with an explanation that banking credentials are not provisioned.
  - Does **NOT** fabricate fake live credentials or endpoints.

---

## 4. API Endpoints

All endpoints are versioned under `/api/v1/verification` and enforce role-based access control and tenant isolation:

| Method | Endpoint | Authorized Roles | Description |
|:---|:---|:---|:---|
| `POST` | `/instruments/{id}/requests` | Officers | Initiates a verification request with frozen snapshot. |
| `GET` | `/instruments/{id}/requests` | Scoped Users / Officers | Lists all verification requests for an instrument. |
| `GET` | `/requests/{id}` | Scoped Users / Officers | Retrieves a specific request with attempt history and responses. |
| `POST` | `/requests/{id}/dispatch` | Officers | Dispatches request via adapter and ingests response. |
| `POST` | `/requests/{id}/manual-record` | Officers | Records an authorized manual external verification letter. |
| `POST` | `/requests/{id}/retry` | Officers | Bounded retry for timed-out or unavailable requests (max 3). |
| `POST` | `/requests/{id}/cancel` | Officers | Cancels/closes a request with mandatory reason. |
| `GET` | `/responses/{id}` | Scoped Users / Officers | Retrieves response details with field-by-field comparisons. |
| `GET` | `/instruments/{id}/provenance` | Scoped Users / Officers | Active field-level provenance. |
| `GET` | `/instruments/{id}/provenance/{field}/history` | Scoped Users / Officers | Full chronological field custody chain. |
| `GET` | `/instruments/{id}/trust` | Scoped Users / Officers | Active trust assessments. |
| `GET` | `/instruments/{id}/trust/history` | Scoped Users / Officers | Durable trust transition audit log. |
| `POST` | `/instruments/{id}/trust/transition` | Officers | Centralized gatekeeper for trust level changes (L0–L3). |

---

## 5. Security & Tenant Scoping Controls

1. **Cross-Tenant Access Denial:** Institution users (`INSTITUTION_USER`) can only access instruments belonging to their assigned institution. Cross-institution access returns `403 FORBIDDEN_CROSS_TENANT_ACCESS`.
2. **Privilege Escalation Denial:** Institution users and auditors cannot dispatch requests, record manual verifications, or transition trust levels.
3. **Audit Logging:** Every material action (`VERIFICATION_REQUEST_CREATED`, `VERIFICATION_RESPONSE_RECEIVED`, `MANUAL_VERIFICATION_RECORDED`, `VERIFICATION_REQUEST_RETRIED`, `VERIFICATION_REQUEST_CANCELLED`) generates an immutable row in `audit_events`.
4. **Trust Gatekeeper Invariance:** Ingesting a matching verification response does **NOT** directly alter `Instrument.trust_level`. Trust levels can only change through the audited `transition_trust_level` service.

---

## 6. Verification Test Suite Report

Implemented in [`backend/tests/test_module4_verification_adapters.py`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/tests/test_module4_verification_adapters.py):

| Test Case | Description & Verification Outcome | Status |
|:---|:---|:---:|
| `test_creating_unique_verification_request` | Verification request created with non-guessable code, frozen snapshot, and pending state. | ✅ PASSED |
| `test_request_code_uniqueness` | Request codes are cryptographically unique and non-guessable. | ✅ PASSED |
| `test_correct_matching_response` | Matching response sets request status to `MATCH` and itemizes field comparisons. | ✅ PASSED |
| `test_incorrect_request_code` | Unknown request ID returns `404 REQUEST_NOT_FOUND`. | ✅ PASSED |
| `test_response_linked_to_wrong_instrument` | Response for Instrument B cannot satisfy Instrument A (`CROSS_INSTRUMENT_RESPONSE_REJECTED`). | ✅ PASSED |
| `test_duplicate_response_delivery` | Duplicate delivery with identical idempotency token returns existing response idempotently. | ✅ PASSED |
| `test_mismatch_response_and_conflict_preservation` | Mismatch response preserves both registered and bank values without overwriting instrument. | ✅ PASSED |
| `test_timeout_handling` | Timeout outcome updates status to `TIMEOUT` and never upgrades trust level. | ✅ PASSED |
| `test_source_unavailable_handling` | Source unavailable records provider diagnostics and status. | ✅ PASSED |
| `test_bounded_retry_behavior` | Attempt count increments; request code stays stable; exceeds max retries (3) triggers `422`. | ✅ PASSED |
| `test_manual_evidence_path_and_evidence_permissions` | Manual record requires officer role, reason, and Module 2 document version reference. | ✅ PASSED |
| `test_simulated_scenarios_comprehensive` | Verifies all 5 scenarios (MATCH, MISMATCH, TIMEOUT, SOURCE_UNAVAILABLE, INCONCLUSIVE). | ✅ PASSED |
| `test_simulation_disabled_in_production_configuration` | Setting `ENVIRONMENT='production'` blocks simulated adapter with `403 Forbidden`. | ✅ PASSED |
| `test_simulated_response_cannot_satisfy_production_l3` | Simulated response strictly barred from granting `L3_BANK_CONFIRMED`. | ✅ PASSED |
| `test_unconfigured_live_provider_fails_honestly` | Live bank adapter reports `503 LIVE_BANK_INTEGRATION_UNCONFIGURED` when unconfigured. | ✅ PASSED |
| `test_cross_tenant_access_denial` | Institution user blocked from reading or dispatching other institutions' requests (`403`). | ✅ PASSED |
| `test_audit_events_for_material_transitions` | Request creation, response, retry, and cancellation generate audit records. | ✅ PASSED |
| `test_no_direct_endpoint_can_bypass_trust_service` | Recording verification response does not mutate `Instrument.trust_level`. | ✅ PASSED |

**All 246 backend tests passed in 11.02s (0 failures across Modules 1–4).**

---

## 7. Incomplete Dependencies & Recommended Next Step

### Incomplete Dependencies (To Be Addressed in Prompts 3–5)
1. **Officer Verification Desk UI (Prompt 3):** Frontend verification queue, field-by-field side-by-side comparison workspace, manual letter recording modal, and officer approval drawer.
2. **Automated Trust Conflict Reconciliation (Prompt 4):** Automatic trust downgrade triggers when Module 2 uploads a newer document version or Module 3 detects discrepancies on previously confirmed fields.
3. **End-to-End Module 4 Integration & Evaluation (Prompt 5):** End-to-end integration across all 4 modules, synthetic evaluation metrics, and final Module 4 handover.

### Recommended Next Step
Proceed to **Module 4, Prompt 3 of 5: Verification Desk Interface, Side-by-Side Comparison Workspace and Scrutiny Actions**.
