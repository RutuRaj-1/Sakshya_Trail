# Module 4 — Trust, Provenance & Verification Desk
## Field-Level Provenance, Trust Assessment & Verification Data Foundation

> **Stage:** Module 4, Prompt 1 of 5 Complete  
> **Alembic Revision:** `c5e8f1a3d9b4`  
> **Backend Test Suite:** **228 passed** across all modules in 9.86s (12 new Module 4 tests) — **0 failures**  
> **Frontend:** `tsc -b && vite build` built cleanly in 478ms — **0 errors**  
> **Date:** October 2026  
> **Repository:** `FDR_Sentinel`

---

## 1. Executive Summary & Boundaries

Module 4 implements the foundational data models, business rules, and security enforcement for **Field-Level Provenance**, **Evidentiary Trust Assessment (L0–L3)**, and the **Bank Verification Desk**.

It establishes the core architectural thesis of FDR Sentinel: **the challenge of statutory security deposit oversight is lifecycle control and evidentiary trust, not mere document storage.**

### Boundaries & Ownership
- **Module 4 Owns:**
  - Field-level provenance custody chains (`field_provenances`).
  - Evidentiary trust state assessments at both field and aggregate levels (`trust_assessments`).
  - Authorized regulatory scrutiny officer verification decisions (L2).
  - Outbound bank verification requests (`verification_requests`).
  - Inbound bank and external verification responses with simulation flags (`verification_responses`).
  - Centralized trust transition gatekeeping and audited reassessment/downgrade workflows.
  - Durable, immutable trust transition audit logs (`trust_transition_history`).
- **Module 4 Consumes (Without Duplication):**
  - **Module 1 (Registry):** Authoritative instrument and institution records (`Instrument`, `Institution`, `User`).
  - **Module 2 (Document & Evidence):** Document versions, storage keys, SHA-256 byte hashes, and OCR extracted fields (`Document`, `DocumentVersion`, `DocumentExtractedFields`).
  - **Module 3 (Validation & Discrepancies):** Validation runs, deterministic rule results, and explainable discrepancies (`ValidationRun`, `ValidationFinding`).
- **Module 4 Does NOT Own:**
  - Maturity monitoring, expiry alerts, and replacement workflows (owned by Module 5).
  - Financial release gates, deposit refunds, or maker-checker disbursement authorizations (owned by Module 6).

---

## 2. Field-Level Provenance Architecture

Field-level provenance provides fine-grained, auditable lineage for each tracked field of an instrument. It prevents unverified machine extractions from silently overwriting authoritative records, and ensures that corrections create provenance history rather than erasing prior sources.

### Tracked Fields Allow-List
```python
TRACKED_INSTRUMENT_FIELDS = [
    "amount",
    "currency",
    "issue_date",
    "maturity_date",
    "bank_name",
    "branch",
    "reference_number",
    "lien_marked",
    "lien_holder",
    "joint_with_aicte",
    "instrument_type",
]
```

### Supported Source Vocabulary
- `INSTITUTION_ENTERED`: Value declared by institution portal user during registration or update.
- `OFFICER_ENTERED`: Value entered or amended by regulatory scrutiny officer.
- `IMPORTED`: Value migrated from legacy database or external batch import.
- `OCR_EXTRACTED`: Machine extraction from Module 2 OCR pipeline (advisory suggestion).
- `VISION_LLM_EXTRACTED`: Multimodal vision LLM parsing suggestion.
- `DOCUMENT_EVIDENCE`: Value backed by an immutable document version (`DocumentVersion`).
- `MANUAL_BANK_EVIDENCE`: Value backed by an uploaded bank confirmation letter or branch certificate.
- `AUTHORIZED_BANK_RESPONSE`: Value received via automated bank interface or SFTP batch.
- `SYSTEM_DERIVED`: Value calculated deterministically by server-side logic.

### Immutability & Custody Chain Guarantees
- Provenance rows are **append-only**. Application endpoints cannot update or delete rows from `field_provenances`.
- When an instrument field is updated, the active provenance record is marked `is_active = False` with `superseded_by_id` pointing to the new record.
- The new record sets `prior_provenance_id` pointing to the old record, forming a bidirectional, traceable custody chain.

---

## 3. Four-Tier Evidentiary Trust Hierarchy

Module 4 enforces strict separation between:
1. **Administrative Status** (`REGISTERED`, `RETURNED_FOR_CORRECTION`, etc.)
2. **Derived Maturity Indicator** (`ACTIVE`, `EXPIRING_SOON`, `EXPIRED`)
3. **Evidentiary Trust Level** (`L0` to `L3`)

```
   ┌────────────────────────────────────────────────────────┐
   │                     L0_DECLARED                        │
   │  Institution-entered or imported baseline declaration  │
   └───────────────────────────┬────────────────────────────┘
                               │ (Requires clean document version & no blocking flags)
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                L1_DOCUMENT_CONSISTENT                  │
   │  Verified against clean, scanned documentary evidence  │
   └───────────────────────────┬────────────────────────────┘
                               │ (Requires authorized officer role, reason & evidence ref)
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                  L2_OFFICER_VERIFIED                   │
   │  Scrutiny officer physical inspection / human review   │
   └───────────────────────────┬────────────────────────────┘
                               │ (Strictly requires matching non-simulated bank response)
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                   L3_BANK_CONFIRMED                    │
   │  Independently confirmed by issuing bank / official API│
   └────────────────────────────────────────────────────────┘
```

### Trust Entry Preconditions

| Level | Name | Authorized Roles | Mandatory Preconditions & Entry Rules |
|:---:|:---|:---|:---|
| **L0** | `L0_DECLARED` | System / Institution | Initial state for registered or imported records. Preserves source actor and timestamp without implying independent verification. |
| **L1** | `L1_DOCUMENT_CONSISTENT` | System / Scrutiny Officer | Strictly requires `supporting_document_version_id`. Supporting version must exist, belong to the instrument, and have `processing_status` in (`CLEAN`, `PROCESSED`, `ACCEPTED`). Quarantined or unread evidence rejected. |
| **L2** | `L2_OFFICER_VERIFIED` | `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `SYSTEM_ADMIN` | Non-officer roles (`INSTITUTION_USER`, `AUDITOR`) rejected with `403 Forbidden`. Meaningful non-empty reason is strictly mandatory. Must cite documentary or manual inspection evidence. Audited in `audit_events`. |
| **L3** | `L3_BANK_CONFIRMED` | Verification Desk / Automated Bank Adapter | Strictly requires `related_verification_response_id`. Response must exist, belong to the **same instrument** (cross-instrument injection rejected), have `is_simulated = False` (simulated responses barred from L3), and have `result = MATCH`. |

### Reassessment & Downgrades
- When underlying evidence is superseded or corrected, or an officer discovers a material discrepancy, trust level transitions down (e.g., L2 → L0).
- Downgrades require a mandatory justification reason and are flagged with `is_downgrade = True`.
- Prior assessments transition to `SUPERSEDED`, and an immutable entry is appended to `trust_transition_history`.

---

## 4. Verification Requests & Responses

### Verification Request (`verification_requests`)
- Unique traceable reference code: `reference_code` (e.g. `VR-20261025-XXXXXX`).
- Channels: `SIMULATED`, `SFTP_BATCH`, `DIRECT_API`, `AUTHORIZED_MANUAL`.
- Freezes a JSON snapshot of the instrument fields at dispatch time (`snapshot_data_json`).

### Verification Response (`verification_responses`)
- Contains confirmation outcome: `MATCH`, `MISMATCH`, `INDETERMINATE`.
- Carries strict boolean simulation flag (`is_simulated`).
- Database check constraints:
  - `ck_vr_sim_consistency`: Enforces that `channel == 'SIMULATED'` if and only if `is_simulated = True`.
  - `ck_vr_manual_evidence`: Enforces that `AUTHORIZED_MANUAL` correspondence must reference an evidence document.
- Unique `idempotency_key` prevents replay attacks and duplicate response logging.

---

## 5. Security & Tenant Scoping Controls

1. **Cross-Tenant Isolation:**
   - Institution users (`INSTITUTION_USER`) can only query provenance and trust records for instruments belonging to their own institution. Access to foreign instruments returns `403 Forbidden` (`FORBIDDEN_CROSS_TENANT_ACCESS`).
2. **Privilege Escalation Denial:**
   - Registry create/update endpoints reject client attempts to set `trust_level` directly.
   - Non-officer roles attempting trust transitions (`POST /verification/instruments/{id}/trust/transition`) are rejected with `403 Forbidden`.
3. **Auditor Read-Only Enforcement:**
   - Auditors (`AUDITOR`) have read-only access to provenance and transition history, but are barred from executing trust transitions or dispatching verification requests.
4. **Cross-Instrument Linkage Prevention:**
   - Verification responses tied to Instrument A cannot be referenced to promote Instrument B (`CROSS_INSTRUMENT_RESPONSE_REJECTED`).
5. **Database-Level Invariant Constraints:**
   - `ck_ta_l3_response`: Trust assessment table check constraint asserts that `trust_level != 'L3_BANK_CONFIRMED'` or `related_verification_response_id IS NOT NULL`.

---

## 6. Database Schema & Migration Details

**Alembic Revision ID:** `c5e8f1a3d9b4`  
**Revises:** `f4a9b2c8e1d7`  
**Tables Added:**
1. `field_provenances`: 17 columns, 5 indexes, foreign keys to instruments, users, documents, document_versions, validation_runs, self-referential lineage.
2. `verification_requests`: 9 columns, 2 indexes, unique constraint on `reference_code`.
3. `verification_responses`: 15 columns, 4 indexes, check constraints for simulation and manual evidence, unique constraint on `idempotency_key`.
4. `trust_assessments`: 16 columns, 4 indexes, check constraint for L3 response presence.
5. `trust_transition_history`: 16 columns, 1 index, immutable audit log.

---

## 7. Verification Test Suite Report

Implemented in [`backend/tests/test_module4_trust_provenance.py`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/tests/test_module4_trust_provenance.py):

| Test Scenario | Verifies | Status |
|:---|:---|:---:|
| `test_provenance_creation_entered_imported` | Provenance creation for entered/imported values; allow-list enforcement. | ✅ PASSED |
| `test_provenance_linked_to_document_version` | Provenance accurately links to document and document version IDs. | ✅ PASSED |
| `test_historical_provenance_retention_after_correction` | Corrections create history; prior rows marked superseded, not erased. | ✅ PASSED |
| `test_l0_initialization` | Initial registration generates baseline L0 field provenance rows. | ✅ PASSED |
| `test_rejection_l1_without_required_evidence` | L1 rejected without document version, or if version status is quarantined. | ✅ PASSED |
| `test_rejection_l2_unauthorized_or_no_reason` | L2 rejected for non-officers (403) or blank reason (422). | ✅ PASSED |
| `test_rejection_l3_without_qualifying_response` | L3 rejected without response record or when response is MISMATCH. | ✅ PASSED |
| `test_rejection_l3_simulated_response` | Simulated responses (`is_simulated=True`) barred from promoting to L3. | ✅ PASSED |
| `test_rejection_cross_instrument_links` | Response from Instrument B cannot be used to promote Instrument A. | ✅ PASSED |
| `test_preservation_of_trust_history_after_reassessment_downgrade` | Downgrade (L2→L0) records audit history with `is_downgrade=True` and reason. | ✅ PASSED |
| `test_database_migrations_module4` | Verifies existence of all 5 Module 4 tables, columns, and constraints. | ✅ PASSED |
| `test_role_and_institution_scope_enforcement` | Scoping blocks cross-tenant reads; auditor restricted to read-only. | ✅ PASSED |

**All 228 backend tests passed in 9.86s (0 failures across Modules 1–4).**

---

## 8. Incomplete Dependencies & Recommended Next Step

### Incomplete Dependencies (To Be Addressed in Prompts 2–5)
1. **Verification Adapters (Prompt 2):** Automated simulated bank adapters, SFTP batch processors, and mock bank API connectors are not yet implemented.
2. **Officer Verification Desk UI (Prompt 3):** Frontend verification queue, field-by-field side-by-side comparison workspace, and officer approval drawer.
3. **Automated Trust Conflict Reconciliation (Prompt 4):** Automatic downgrade triggers when Module 2 uploads a newer document version or Module 3 detects discrepancies on previously confirmed fields.
4. **End-to-End Module 4 Integration & Evaluation (Prompt 5):** End-to-end integration across all 4 modules and handover documentation.

### Recommended Next Step
Proceed to **Module 4, Prompt 2 of 5: Verification Request Dispatch, Bank Adapter Simulation & Response Ingestion Engine**.
