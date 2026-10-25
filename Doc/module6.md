# Module 6 — Release / Refund Case Management
## Domain Models, Checklists and Decision-History Foundation (Prompt 1 of 5)

> **Module Status:** Foundational Data Models, State Machine & Checklists Implemented (Prompt 1 of 5 Complete)  
> **Alembic Revision:** `f6a7b8c9d0e1` — `add_module_6_release_refund_foundation`  
> **Backend Test Suite:** **376 passed** across all modules in 0.30s — **0 failures, 0 regressions**  
> • Module 6 Prompt 1 Foundation Tests: **10 passed**  
> **Frontend Production Build:** **Compiled cleanly** with `tsc -b && vite build` in 587ms  
> **Repository:** `FDR_Sentinel`  
> **Author:** Senior Backend Architect, Financial-Workflow Engineer & PostgreSQL Data Modeller  
> **Date:** October 2026  

---

## 1. Executive Summary & Architectural Scope

Module 6 governs the **Release, Invocation & Closure Orchestration** subsystem of the AICTE FDR Sentinel platform. It manages administrative release, lien discharge, and security deposit refund requests initiated by technical institutions or regulatory bureaus.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 MODULE 6 BOUNDARIES                                    │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│                  OWNS                     │               DOES NOT OWN                 │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ • Release / discharge / refund cases      │ • Moving funds or initiating wire transfers│
│ • Case readiness checklists & blockers    │ • Raw document storage or PDF parsing (M2) │
│ • Historical readiness assessment audits  │ • Running OCR or discrepancy rules (M3)    │
│ • Officer review & deficiency notes       │ • Issuing bank confirmation tokens (M4)    │
│ • Authorized maker-checker decisions      │ • Days-to-maturity & renewal lineage (M5)  │
│ • Official release order letter tracking  │ • Letting AI decide financial approvals    │
│ • Post-approval bank action status states │ • Automatically closing matured deposits   │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Strict Administrative Non-Financial Boundary:**
> Module 6 records and controls an administrative regulatory governance workflow. It does **not** execute bank transfers, move money, issue legally binding financial instructions on its own, or allow AI to approve releases. An approved release case (`APPROVED`) does not mean funds were transferred; subsequent release order issuance and bank-side action confirmation are tracked as distinct, auditable milestones.

---

## 2. Core Domain Data Models

Implemented in [`backend/app/modules/release/models.py`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/release/models.py) and migrated via Alembic revision `f6a7b8c9d0e1`:

### 2.1 `ReleaseRequest` (`release_requests`)
Core administrative case record:
- `id`: UUID (String(36)), primary key.
- `case_number`: Stable human-readable identifier (e.g. `REL-2026-00001` or `REF-2026-00001`), unique and indexed.
- `instrument_id`: Foreign key to `instruments.id` (Module 1).
- `institution_id`: Foreign key to `institutions.id` (Module 1), validated server-side against the instrument.
- `request_type`: `RELEASE`, `DISCHARGE`, `REFUND`.
- `case_type`: `STANDARD_MATURITY_RELEASE`, `SUBSTITUTION_RELEASE`, `PROGRAM_CLOSURE_DISCHARGE`, `EXCESS_DEPOSIT_REFUND`, `SPECIAL_DISPENSATION`.
- `policy_profile_id`: Foreign key to `release_checklist_profiles.id`.
- `policy_version`: Integer version snapshot.
- `requester_id`: Foreign key to `users.id`.
- `request_reason`: Text, mandatory non-empty justification.
- `workflow_status`: Current state machine stage.
- `assigned_reviewer_id`: Foreign key to `users.id` (assigned scrutiny officer).
- `assigned_office`: Regional office jurisdiction.
- `latest_assessment_id`: Reference to most recent readiness snapshot.
- `submitted_at`, `closed_at`, `closure_notes`: Timestamps and metadata.
- `version`: Optimistic locking / concurrency counter.

### 2.2 `ReleaseChecklistProfile` (`release_checklist_profiles`)
Versioned configuration model defining eligibility criteria:
- `profile_code`: Stable identifier across versions (e.g. `DEMO_RELEASE_PROFILE`).
- `name`: Human-readable profile title.
- `version`: Monotonic version number within profile code.
- `request_type`, `case_type`: Criteria scope.
- `status`: `DRAFT`, `APPROVED`, `ACTIVE`, `SUPERSEDED`, `INACTIVE`.
- `is_demo`: Explicit boolean flag.
- `demo_disclaimer`: Mandatory warning banner: `DEMO RELEASE POLICY — NOT OFFICIAL AICTE POLICY`.
- `effective_from`, `effective_to`: Date boundaries.

### 2.3 `ReleaseChecklistItem` (`release_checklist_items`)
Individual criteria within a profile:
- `item_code`: Stable code (e.g. `ITEM_DOC_COMPLETENESS`, `ITEM_MIN_TRUST_LEVEL`).
- `title`, `explanation`: Clear regulatory guidance.
- `requirement_type`: `DOCUMENT_COMPLETENESS` (M2), `TRUST_LEVEL` (M4), `VALIDATION_FINDINGS` (M3), `LIFECYCLE_MATURITY` (M5), `LINEAGE_CONTINUITY` (M5), `AFFIDAVIT_OR_NOC`, `MANUAL_CLEARANCE`.
- `is_mandatory_blocker`: Boolean flag (True = hard blocker, False = advisory note).
- `evaluation_type`: `AUTOMATED`, `HUMAN_REVIEW`, `HYBRID`.
- `expected_evidence_source`: Module origin identifier.
- `sort_order`, `is_active`: Display sequence and active status.

### 2.4 `ReadinessAssessment` (`readiness_assessments`)
Point-in-time, reproducible evaluation snapshot:
- `release_request_id`, `profile_id`, `profile_version`.
- `assessment_outcome`: `READY_FOR_APPROVAL`, `BLOCKED`, `PENDING_REVIEW`, `INCOMPLETE`.
- `satisfied_count`, `blockers_count`, `pending_count`, `advisory_flags_count`.
- `evaluated_by_user_id`: System or officer evaluator.
- `evaluated_at`: Immutable timestamp.

### 2.5 `ReadinessCheckResult` (`readiness_check_results`)
Detailed per-item evaluation output:
- `assessment_id`, `checklist_item_id`, `item_code`.
- `status`: `SATISFIED`, `UNSATISFIED`, `PENDING`, `NOT_APPLICABLE`, `UNABLE_TO_EVALUATE`.
- `is_mandatory_blocker`: Boolean flag.
- `explanation`: Detailed explanation of pass/fail/pending reason.
- `evidence_references_json`: Linked document IDs, finding IDs, verification IDs.
- `source_module`: Originating module tag.

### 2.6 `ReleaseReviewObservation` (`release_review_observations`)
Scrutiny review notes and deficiency return instructions recorded by officers.

### 2.7 `ReleaseDecision` (`release_decisions`)
Authorized maker-checker decision log:
- `actor_user_id`, `actor_role`: Decision maker snapshot.
- `decision_type`: `SUBMIT`, `RETURN_FOR_CORRECTION`, `RECOMMEND_FOR_AUTHORITY`, `APPROVE`, `REJECT`, `CANCEL`.
- `reason`: Mandatory non-empty text justification.
- `previous_status`, `new_status`: Audited status transition.

### 2.8 `ReleaseOrderRecord` (`release_order_records`)
Official AICTE release order tracking and bank-side action state:
- `order_reference_number`: Government/bureau sanction reference.
- `order_date`: Date issued.
- `responsible_officer_id`: Signing officer.
- `supporting_document_id`: Linked uploaded sanction letter PDF.
- `status`: `DRAFT_RECORDED`, `EXECUTED`, `CANCELLED`.
- `bank_action_status`: `PENDING`, `CONFIRMED`, `DISPUTED`, `NOT_APPLICABLE`.
- `bank_action_notes`, `bank_action_confirmed_at`: Follow-up tracking.

---

## 3. Strict State Machine Invariants

```
 [ DRAFT ]
     │ (Submit by Institution)
     ▼
 [ SUBMITTED ] ◄─────────────────────────────────────────────┐
     │                                                       │
     ▼                                                       │
 [ UNDER_REVIEW ] ──► [ RETURNED_FOR_CORRECTION ] ───────────┘
     │ (Officer Scrutiny)   (Institution fixes deficiency)
     ▼
 [ READY_FOR_AUTHORITY ]
     │
     ├──────────────────────────┐
     │ (Authority Approve)      │ (Authority Reject)
     ▼                          ▼
 [ APPROVED ]               [ REJECTED ]
     │
     ▼ (Officer Dispatches Release Order)
 [ RELEASE_ORDER_RECORDED ]
     │
     ▼ (Awaiting Bank Lien Removal / Rollover)
 [ BANK_SIDE_ACTION_PENDING ]
     │
     ▼ (Bank Confirmation Recorded)
 [ COMPLETED ] ──► [ CLOSED ]
```

### Critical Invariants:
1. **Approval Does Not Mean Transfer:** `APPROVED` indicates regulatory sanction only; release order issuance and bank-side action remain pending.
2. **Mandatory Non-Empty Justifications:** Submissions, returns, recommendations, approvals, and rejections strictly reject empty or whitespace-only reasons (`EMPTY_DECISION_REASON`).
3. **Cross-Tenant Barrier:** Institution users can only view and act on instruments belonging to their own AISHE/institution ID.
4. **Historical Assessment Preservation:** New evidence or document re-uploads generate a new `ReadinessAssessment`; previous snapshots remain intact and queryable.

---

## 4. Reused Modules 1–5 Infrastructure

- **Module 1 (Identity, Registry, Tenancy, RBAC & Audit):** Instruments, institutions, users, roles (`INSTITUTION_USER`, `SCRUTINY_OFFICER`, `COMPETENT_AUTHORITY`, `SYSTEM_ADMIN`), and non-repudiable audit logging (`log_audit_event`).
- **Module 2 (Document Repository & Completeness):** Verifies required document types (`FDR_RECEIPT`, `SANCTION_ORDER`, `BOARD_RESOLUTION`) are uploaded and uncorrupted.
- **Module 3 (Deterministic Rules & Discrepancies):** Evaluates absence of open blocking findings before release clearance.
- **Module 4 (Trust & Verification Hierarchy):** Requires evidentiary trust rating (minimum `L2` or `L3` bank-confirmed) for release eligibility.
- **Module 5 (Lifecycle Monitoring & Lineage):** Checks statutory maturity boundaries and verifies valid successor continuity links for substitution releases.

---

## 5. Verification Test Suite Results

Test suite: [`backend/tests/test_module6_prompt1_foundation.py`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/tests/test_module6_prompt1_foundation.py)

| Specification | Test Function | Result | Notes |
|:---:|:---|:---:|:---|
| 1 | `test_1_create_draft_release_request` | **PASSED** | Draft case created with `REL-YYYY-XXXXX` case number and correct tenant linkage. |
| 2 | `test_2_cross_institution_rejection` | **PASSED** | College B user attempting to create release request for College A's FDR rejected (HTTP 403). |
| 3 | `test_3_empty_or_whitespace_reason_rejected` | **PASSED** | Whitespace-only justification rejected with `EMPTY_REASON` (HTTP 400). |
| 4 | `test_4_synthetic_demo_profile_seeded_and_labelled` | **PASSED** | Demo profile seeded with 6 criteria and `DEMO RELEASE POLICY` disclaimer. |
| 5 | `test_5_versioned_checklist_profile_lookup_and_unconfigured_policy` | **PASSED** | Resolves active profile; unconfigured case types reported cleanly. |
| 6 | `test_6_preservation_of_historical_readiness_assessments` | **PASSED** | Sequential assessments preserved without overwriting prior blocked snapshots. |
| 7 | `test_7_review_observation_recording` | **PASSED** | Scrutiny officers can record observations and deficiency return notices. |
| 8 | `test_8_authorized_workflow_decisions_and_state_transitions` | **PASSED** | End-to-end state transitions from `DRAFT` to `APPROVED` with version bumps. |
| 9 | `test_9_release_order_recording_and_bank_action_tracking` | **PASSED** | Release order records advance status to `RELEASE_ORDER_RECORDED` with `PENDING` bank action. |
| 10 | `test_10_rest_api_endpoints_integration` | **PASSED** | Full HTTP API flow via TestClient with RBAC and JWT authentication. |

---

## 6. Unresolved Official Policy Dependencies

1. **Statutory AICTE Release Profiles:** The synthetic demo profile `DEMO_RELEASE_PROFILE` is strictly labelled as a non-official prototype. Actual official AICTE Approval Process Handbook (APH) release requirements (specific affidavits, court clearance formats, university NOCs, and delegated sanction thresholds) must be configured through authorized administrative channels prior to production deployment.
2. **Bank Gateway Integration:** Direct core banking webhooks for lien discharge confirmation are currently represented by the structured `BankActionStatus` administrative state and mock records.
