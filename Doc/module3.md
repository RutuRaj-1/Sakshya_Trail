# Module 3 — Validation, Discrepancy & Explainable Intelligence
## Handover & Final Technical Specification

> **Status:** ✅ Complete (Prompt 5 of 5: End-to-End Integration, Security Review, Evaluation Metrics and Module 3 Handover)  
> **Alembic Head:** `f4a9b2c8e1d7`  
> **Test Suite:** **216 passed** across all backend modules in 8.68s — **0 failures**  
> **Frontend:** `tsc -b && vite build` built cleanly in 469ms — **0 type/build errors**  
> **Date:** October 2026  
> **Repository:** `FDR_Sentinel`

---

## 1. Executive Summary & Integration Scope

Module 3 delivers the **deterministic rule engine**, **cross-source evidence reconciliation**, **tenant-isolated duplicate detection**, **explainable finding persistence**, **authorized policy configuration**, and **officer discrepancy review workflow** with a **transparent review-priority ordering queue** for the FDR Sentinel platform.

Module 3 operates as a cohesive, read-only consumer across:
- **Module 1 (Registry):** Reads `Institution`, `Instrument`, `User`, and `AuditEvent` records via established SQLAlchemy models and services.
- **Module 2 (Document & Evidence):** Consumes `Document`, `DocumentVersion` (storage keys, SHA-256 byte hashes, processing statuses), `ChecklistResult`, and machine-extracted suggestions (`DocumentExtractedFields`).

### System Invariants Strictly Enforced
1. **Trust Level Invariance:** Module 3 validation runs, finding reviews, and priority scores **NEVER alter `trust_level` (L0–L3)**. Trust level progression remains the exclusive jurisdiction of the designated future module.
2. **Release / Refund Non-Interference:** No validation finding, dismissal, or review score possesses the legal or technical authority to approve or reject a financial deposit release or refund.
3. **Non-Destructive Reconciliation:** Machine-extracted suggestions from OCR or parsers never overwrite authoritative entered instrument fields.
4. **Tenant Isolation:** In cross-institution duplicate checks, foreign institution details (names, codes, contact info) are strictly masked (`[tenant-masked]`) to prevent confidential cross-tenant leakage.
5. **Non-Accusatory Classification:** Heuristic indicators (name similarity, file metadata) are explicitly branded as `[Advisory — human review required]` and never claim proof of fraud or forgery.

---

## 2. Architecture & Data Flow

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           MODULE 1: REGISTRY                              │
│   Institutions (Tenant Scope)  │  Instruments (Authority Fields)  │  Users  │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                    MODULE 2: DOCUMENT & EVIDENCE                          │
│   Documents  │  Versions (SHA-256)  │  Checklists  │  Extracted OCR Data  │
└─────────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│             MODULE 3: VALIDATION & EXPLAINABLE INTELLIGENCE               │
│                                                                           │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────┐  │
│  │ Policy Configuration │  │ 20 Registered Rules  │  │ Normalization   │  │
│  │ (Versioned / Min Amt)│  │ (Deterministic/Heur.)│  │ (Ref/Bank/Name) │  │
│  └──────────┬───────────┘  └──────────┬───────────┘  └────────┬────────┘  │
│             │                         │                       │           │
│             └─────────────────────────┼───────────────────────┘           │
│                                       ▼                                   │
│                        Validation Engine Orchestrator                     │
│                        (Post-Save Triggers / Batch API)                   │
│                                       │                                   │
│            ┌──────────────────────────┴──────────────────────────┐        │
│            ▼                                                     ▼        │
│  ValidationRun (Audit Log)                             ValidationFinding  │
│  • Status (PASSED/FLAGGED)                             • SHA-256 Fingerpr.│
│  • Rule Outcomes JSON                                  • Stored Evidence  │
│  • Engine Duration (ms)                                • Lifecycle State  │
│                                                        • Priority (0-100) │
└───────────────────────────────────────┬───────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      OFFICER DISCREPANCY WORKFLOW                         │
│   Review Queue (/findings/queue)  │  Filter Drawer  │  Reasoned Actions   │
│   OPEN ──► IN_REVIEW ──► RESOLVED / DISMISSED / SUPERSEDED                │
│   Return for Correction (with mandatory remarks to Institution)           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Complete 20-Rule Taxonomy & Catalogue

Every rule inherits from `BaseValidationRule` and registers in `rule_registry`. Rules return a structured `RuleResult` with `outcome` (`PASS`, `FAIL`, `WARNING`, `NOT_APPLICABLE`, `UNABLE_TO_EVALUATE`), plain-language explanation, itemized evidence inputs, and prescriptive next actions.

| Rule ID | Category | Type | Severity | Description & Operational Behavior |
|---------|----------|------|----------|------------------------------------|
| `VAL-REQ-001` | `CROSS_FIELD_CONSISTENCY` | Deterministic | HIGH | **Required Instrument Fields:** Evaluates configured mandatory fields from active `REQUIRED_INSTRUMENT_FIELDS` policy. |
| `VAL-AMT-001` | `AMOUNT_CONSISTENCY` | Deterministic | CRITICAL | **Positive Amount:** Asserts registered deposit amount is Decimal > 0.00. |
| `VAL-AMT-002` | `POLICY_COMPLIANCE` | Deterministic | HIGH | **Policy Minimum Amount:** Compares amount against `MIN_DEPOSIT_AMOUNT_INR`. Returns `UNABLE_TO_EVALUATE` if unconfigured; never invents expected amounts. |
| `VAL-DATE-001` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Date Ordering & Bounds:** Asserts calendar range (1990–2100) and that maturity date is strictly after issue date. |
| `VAL-DATE-002` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Maturity Expiry:** Evaluates active instruments against current date (warning within 90 days; fail if expired). |
| `VAL-DATE-003` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Validity Term Bounds:** Enforces `MIN_VALIDITY_DAYS` / `MAX_VALIDITY_DAYS` if policy active; returns `NOT_APPLICABLE` when unconfigured. |
| `VAL-INST-001` | `INSTITUTION_ELIGIBILITY` | Deterministic | HIGH | **Institution Association Consistency:** Compares instrument institution linkage against uploaded document context. |
| `VAL-DOC-001` | `DOCUMENT_COMPLETENESS` | Deterministic | MEDIUM | **FDR Copy Presence:** Verifies at least one `FDR_COPY` document is uploaded and cleanly processed. |
| `VAL-DOC-002` | `DOCUMENT_COMPLETENESS` | Deterministic | HIGH | **Module 2 Checklist Integration:** Consumes Module 2 completeness profile; returns `UNABLE_TO_EVALUATE` if profile unavailable. |
| `VAL-CONS-001` | `CROSS_FIELD_CONSISTENCY` | Deterministic | HIGH | **Basic Data Consistency:** Validates active institution status and asserts non-contradictory joint/lien flags. |
| `VAL-REF-001` | `REFERENCE_INTEGRITY` | Deterministic | HIGH | **Reference Integrity:** Rejects blank, length < 4, or placeholder references (e.g., `000000`, `TEST-REF`, `NA`). |
| `VAL-LIEN-001` | `LIEN_VALIDITY` | Deterministic | HIGH | **Lien Validity:** Asserts lien-marked instruments specify a non-empty lien holder name. |
| `VAL-XSRC-STALE` | `DOCUMENT_INTEGRITY` | Heuristic | MEDIUM | **Stale Extraction Detector:** Flags extractions performed on older document versions when a newer version exists. Quarantines cross-source comparisons until reprocessed. |
| `VAL-XSRC-001` | `CROSS_SOURCE_RECONCILIATION` | Deterministic | HIGH | **Amount Reconciliation:** Compares entered amount against extracted suggestion. Returns `UNABLE_TO_EVALUATE` if extraction absent. Never overwrites entered record. |
| `VAL-XSRC-002` | `CROSS_SOURCE_RECONCILIATION` | Deterministic | HIGH | **Reference Reconciliation:** Compares normalized entered reference with extracted certificate reference. |
| `VAL-XSRC-003` | `CROSS_SOURCE_RECONCILIATION` | Deterministic | HIGH | **Date Reconciliation:** Compares entered issue/maturity dates against extracted certificate dates. |
| `VAL-XSRC-004` | `CROSS_SOURCE_RECONCILIATION` | Heuristic | MEDIUM | **Bank Reconciliation:** Compares normalized issuing bank names across entered data and OCR. |
| `VAL-XSRC-006` | `LIEN_VALIDITY` | Heuristic | MEDIUM | **Lien Holder Reconciliation:** Evaluates lien holder text only when confidence >= 0.70; otherwise returns `NOT_APPLICABLE`. |
| `VAL-DUP-001` | `POTENTIAL_DUPLICATE` | Heuristic | HIGH | **Intra-Institution Duplicate Reference:** Bank-aware check detecting instruments sharing same bank + reference in the same institution. |
| `VAL-DUP-002` | `POTENTIAL_DUPLICATE` | Heuristic | HIGH | **Cross-Institution Duplicate Reference:** Bank-aware duplicate check across institutions with **tenant data masking** to protect confidentiality. |
| `VAL-DUP-003` | `POTENTIAL_DUPLICATE` | Deterministic | HIGH | **Exact SHA-256 Byte Hash Duplicate:** Detects identical document bytes across submissions. Explanation strictly states identical file bytes were uploaded; makes no fraud accusations. |
| `VAL-SIM-001` | `CROSS_SOURCE_RECONCILIATION` | Heuristic | MEDIUM | **Name Similarity Advisory:** Compares legal institution name vs extracted depositor name using `difflib.SequenceMatcher`. Displays both strings, ratio, and threshold. Advisory only. |
| `VAL-META-001` | `DOCUMENT_INTEGRITY` | Heuristic | LOW | **Document Metadata Advisory:** Inspects file metadata for conversion markers (e.g. iLovePDF, Sejda). Clearly labeled as advisory heuristic. |

---

## 4. Finding Lifecycle, Concurrency & Governance

```
                    ┌─────────────────────────┐
                    │      Validation Run     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                         ┌──────────────┐
       ┌─────────────────┤     OPEN     ├─────────────────┐
       │                 └───────┬──────┘                 │
       │                         │                        │
       │ (Assign/Start)          │ (Officer Resolve)      │ (Officer Dismiss)
       ▼                         ▼                        ▼
┌──────────────┐          ┌──────────────┐         ┌──────────────┐
│  IN_REVIEW   ├─────────►│   RESOLVED   │         │  DISMISSED   │
└──────┬───────┘ (Resolve)└──────────────┘         └──────────────┘
       │
       ▼ (Dismiss)
┌──────────────┐
│  DISMISSED   │
└──────────────┘
       
       * At any time, if inputs materially change or rule version updates:
         OPEN / IN_REVIEW ──► SUPERSEDED (pointing to new finding ID)
```

### Key Lifecycle Guarantees
- **Deduplication by Fingerprint:** Every finding computes a SHA-256 hash across `(instrument_id, rule_id, rule_version, evidence_fingerprint)`. Repeat runs on unchanged data update `last_evaluated_at` without duplicating rows.
- **Reason-Mandated Governance:** Status transitions to `RESOLVED` or `DISMISSED` reject blank reasons (`422 REASON_REQUIRED`). All transitions record actor ID, timestamp, and notes in `review_notes_json` and `audit_events`.
- **Optimistic Concurrency Control:** Every finding has a `concurrency_version: int`. Concurrent updates with mismatched versions return `409 ConflictException`.
- **Automatic Resolution on Fix:** When an issue is corrected and re-evaluation passes, open findings automatically transition to `RESOLVED` with automated audit notes.

---

## 5. Transparent Review-Priority Score (0–100)

The review queue includes a deterministic 0–100 prioritization score (`calculate_review_priority_score`) to assist officers in ordering high-risk or urgent submissions:

| Dimension | Max Points | Evaluation Logic |
|-----------|------------|------------------|
| **1. Days to Maturity** | 25 | Expired = 25 pts; <= 30 days = 22.5 pts; <= 90 days = 15 pts; <= 180 days = 7.5 pts; > 180 days = 0 pts. |
| **2. Finding Severity** | 30 | Critical finding = 30 pts; High = 20 pts; Medium = 10 pts; Low/Info = 5 pts; None = 0 pts. |
| **3. Unresolved Discrepancies** | 20 | Scales with count of open discrepancies (1 = 5 pts; 2 = 10 pts; 3 = 15 pts; >= 4 = 20 pts). |
| **4. Document Completeness** | 15 | Missing FDR document copy elevates review urgency (15 pts). |
| **5. Trust / Verification State** | 10 | Unverified `L0_DECLARED` receives 10 pts for initial scrutiny; verified `L2`/`L3` receive 0 pts. |

### Score Disclaimers & Protections
- **Missing Data Handling:** Unknown or omitted fields assign 0 points and are flagged with `is_missing: True` without penalizing the institution.
- **Strict Invariance:** The priority score carries an explicit disclaimer: *"This score is a transparent operational heuristic for review queue ordering and does NOT represent an AI-predicted fraud probability, credit rating, or financial risk model."*
- **No Authority to Release:** The score cannot authorize or reject deposit releases or refunds.

---

## 6. Security Review & Threat Defenses

| Threat Vector | Mitigation Strategy & Verified Implementation |
|---------------|-----------------------------------------------|
| **SQL Injection** | All queue filters (`status`, `rule_id`, `severity`, `institution_id`, `search_term`) execute via parameterized SQLAlchemy column filters (`ilike()`, `==`), preventing dynamic SQL concatenation. |
| **Cross-Tenant Data Leakage** | In cross-institution duplicate findings (`VAL-DUP-002`), foreign institution names and IDs are replaced with `[tenant-masked]`. Institution users can only view findings belonging to their own tenant. |
| **Privilege Escalation** | `INSTITUTION_USER` and `AUDITOR` roles are rejected with `403 Forbidden` if attempting to resolve, dismiss, assign findings, or return instruments for correction. |
| **Direct Client Tampering** | Clients cannot directly write severity, rule outcomes, or priority scores. All findings and scores are generated exclusively server-side during engine execution. |
| **Stale Evidence Poisoning** | `VAL-XSRC-STALE` quarantines extractions performed on older document versions, preventing comparison against obsolete evidence. |
| **XSS & Untrusted Text** | Extracted text and file names rendered in the frontend are sanitized and displayed via React JSX text nodes, preventing raw HTML injection. |
| **Accusatory Defamation** | All heuristic and duplicate findings use objective, non-accusatory language. Exact-hash duplicates explicitly state identical file bytes were found without alleging fraud or tampering. |

---

## 7. Synthetic Evaluation Metrics & Benchmark Report

Executed via the reproducible test script `backend/scripts/evaluate_module3_metrics.py` against 20 labelled synthetic test fixtures:

```
================================================================================
FDR SENTINEL — MODULE 3 EVALUATION METRICS BENCHMARK
Executing evaluation over labelled synthetic test fixtures...
================================================================================

--- SYNTHETIC EVALUATION METRICS REPORT ---
Total Labelled Records Tested: 20
Deterministic Rule Precision:  100.0% (8/8)
Deterministic Rule Recall:     80.0% (8/10)
Deterministic Rule F1 Score:   88.89%
Duplicate Reference Accuracy:  100.0% (4/4)
SHA-256 Hash Duplicate Acc:   100.0% (2/2)
Cross-Source Reconciliation:   100.0% (2/2)
Idempotency Repeat Stability:  100.0% (20/20)
Review Queue Rank Agreement:   100.0% (5/5)
Average Engine Latency:        16.32 ms/instrument
================================================================================
```

### Metrics Formula Breakdown
- **Deterministic Rule Precision:**
  $$\text{Precision} = \frac{TP}{TP + FP} = \frac{8}{8 + 0} = 100.0\%$$
- **Deterministic Rule Recall:**
  $$\text{Recall} = \frac{TP}{TP + FN} = \frac{8}{8 + 2} = 80.0\%$$
  *(Note: 2 edge cases produced advisory `WARNING` rather than deterministic `FAIL`, appropriately yielding 0 false positives).*
- **Deterministic Rule F1 Score:**
  $$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}} = 2 \times \frac{1.0 \times 0.80}{1.0 + 0.80} = 88.89\%$$
- **Duplicate Reference Accuracy:** $4 / 4 = 100.0\%$ (correctly identifying intra/cross bank duplicates while ignoring matching references from distinct banks).
- **Exact SHA-256 Byte Duplicate Accuracy:** $2 / 2 = 100.0\%$.
- **Finding Idempotency Repeat Stability:** $20 / 20 = 100.0\%$ (zero spurious duplicate rows on re-runs).
- **Review Queue Rank Agreement:** Kendall Tau / Rank Concordance $= 100.0\%$ against expected priority tiers.
- **Engine Latency:** 16.32 ms per instrument on local SQLite environment.

*(Disclaimer: Metrics reflect synthetic prototype test fixtures designed for boundary verification and do not represent production AICTE operational fraud rates).*

---

## 8. Frontend & Accessibility Review

- **Review Queue Page (`ReviewQueuePage.tsx`):**
  - Connects to real backend endpoints (`GET /api/v1/findings/queue`).
  - Implements multi-criteria filtering: Status, Severity, Rule Category, and Text Search.
  - Features quick-filter tabs: All, Unresolved Discrepancies, Advisory Warnings, High Priority.
- **Drawer Detail & Observation View:**
  - Displays explainable rule breakdown, rule version, evaluated inputs, and next action.
  - Renders explicit visual badge separation between deterministic findings (`ERROR` / `FAIL`) and heuristic advisories (`[Advisory — human review required]`).
  - Includes modal workflows for **Resolve**, **Dismiss**, and **Return for Correction**, with mandatory reason validation before submission.
- **Accessibility & State Handling:**
  - Full support for `Loading`, `Empty`, `Error`, and `Unauthorized` UI states.
  - WCAG-compliant status badges incorporating icons and text labels, avoiding color-only indicators.
- **Production Build:**
  - Executed `npm run build` (`tsc -b && vite build`) -> **Built in 469ms with 0 errors**.

---

## 9. Final Definition of Done & Acceptance Checklist

| Item | Requirement | Verification Method | Status |
|------|-------------|---------------------|--------|
| **1** | Scenario A (Valid Record) | Automated test `test_scenario_a_valid_record` | ✅ PASSED |
| **2** | Scenario B (Invalid Date Order) | Automated test `test_scenario_b_invalid_date_combination` (`VAL-DATE-001`) | ✅ PASSED |
| **3** | Scenario C (Policy Minimum Amount) | Automated test `test_scenario_c_policy_dependent_amount` (`VAL-AMT-002`) | ✅ PASSED |
| **4** | Scenario D (Entered vs Extracted) | Automated test `test_scenario_d_entered_vs_extracted_discrepancy` (`VAL-XSRC-001`) | ✅ PASSED |
| **5** | Scenario E (Reused Reference & Masking) | Automated test `test_scenario_e_reused_reference_tenant_isolation` (`VAL-DUP-002`) | ✅ PASSED |
| **6** | Scenario F (Identical Byte Hash) | Automated test `test_scenario_f_identical_document_bytes` (`VAL-DUP-003`) | ✅ PASSED |
| **7** | Scenario G (Corrected Evidence Auto-Resolve) | Automated test `test_scenario_g_corrected_evidence_auto_resolves` | ✅ PASSED |
| **8** | Scenario H (Officer Resolution & Audit) | Automated test `test_scenario_h_officer_resolution_and_audit` | ✅ PASSED |
| **9** | Scenario I (Advisory Warning Invariance) | Automated test `test_scenario_i_advisory_warning_invariance` (`VAL-SIM-001`) | ✅ PASSED |
| **10** | Scenario J (Priority Queue & Non-Release) | Automated test `test_scenario_j_priority_queue_and_release_invariance` | ✅ PASSED |
| **11** | SQL Injection Defense | Automated test `test_sql_injection_defense_in_queue_search` | ✅ PASSED |
| **12** | Return for Correction Workflow | Automated test `test_return_for_correction_workflow` | ✅ PASSED |
| **13** | Metrics Benchmark Script | Automated test `test_evaluation_metrics_benchmark_execution` | ✅ PASSED |
| **14** | Complete Test Suite | `pytest tests/` (216 tests passed in 8.68s) | ✅ PASSED |
| **15** | Frontend Production Build | `npm run build` in `frontend/` (0 errors, 469ms) | ✅ PASSED |
| **16** | Documentation Matches Implementation | Updated `Doc/module3.md` | ✅ PASSED |

---

## 10. Known Limitations & Module 4 Prerequisite Checks

### Known Limitations
1. **Machine Extractions are Suggestions:** Module 3 treats OCR and extracted fields strictly as advisory suggestions. Extractions do not establish legal authenticity or replace official bank verification.
2. **Local SQLite Concurrency:** In production environments, SQLite should be replaced with PostgreSQL to enable row-level locking during heavy concurrent evaluation sweeps.
3. **Similarity Threshold Tuning:** The name similarity threshold (default `0.85`) uses Python `difflib.SequenceMatcher`. Phonetic variations (e.g. Soundex/Metaphone) are not yet integrated.

### Prerequisite Checks for Module 4 (Bank Verification & Trust Promotion)
Before commencing Module 4, verify that:
1. Module 3 validation findings are accessible via `/api/v1/findings/instrument/{id}` so Module 4 can check for blocking discrepancies prior to dispatching bank verification requests.
2. Module 4 services consume `instrument.trust_level` directly, ensuring validation rules continue to have **read-only** access to trust levels.
3. Bank confirmation webhooks and direct API integrations in Module 4 do not overwrite Module 1 user-entered fields, but instead write to independent bank confirmation audit records.
