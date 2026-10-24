# Module 3 — Validation, Discrepancy & Explainable Intelligence
## Implementation Summary

> **Status:** ✅ Prompt 3: Evidence Reconciliation, Duplicate Detection & Explainable Advisory Indicators Implemented  
> **Revision:** `dde1c7162b37` (Alembic head)  
> **Tests:** 186 passed total across all modules (15 Prompt 3 tests + 25 Prompt 2 tests + 43 Prompt 1 tests + 103 prior modules) — **0 failures**  
> **Date:** 2026-10-25

---

## 1. Scope & Ownership

Module 3 implements the **rule-driven validation engine**, **cross-source evidence reconciliation**, **tenant-isolated duplicate detection**, **explainable finding persistence**, and **authorized policy configuration** infrastructure for the FDR Sentinel platform. It connects data from Module 1 (instruments, institutions, users) and Module 2 (documents, document versions, extracted OCR fields) without duplicating their ownership or overwriting authoritative records.

### What Module 3 owns
| Concern | Owner | Status |
|---------|-------|--------|
| Rule definitions and registry | Module 3 | Implemented (20 rules registered) |
| Deterministic validation checks (Rules A–F) | Module 3 | Fully Implemented & Tested |
| Cross-source evidence reconciliation (Amount, Reference, Dates, Bank, Lien) | Module 3 | Fully Implemented & Tested |
| Stale extraction detection against document version changes | Module 3 | Implemented (`VAL-XSRC-STALE`) |
| Bank-aware & reference-aware duplicate detection | Module 3 | Implemented (`VAL-DUP-001`, `VAL-DUP-002`) |
| Exact document-hash (SHA-256) byte duplicate detection | Module 3 | Implemented (`VAL-DUP-003`) |
| Name similarity advisory checks (difflib SequenceMatcher) | Module 3 | Implemented (`VAL-SIM-001`) |
| Document metadata & file tamper advisory indicators | Module 3 | Implemented (`VAL-META-001`) |
| Normalization utilities (reference, bank, depositor names) | Module 3 | Implemented (`normalization.py`) |
| Finding persistence, idempotency & lifecycle | Module 3 | Implemented (OPEN, IN_REVIEW, RESOLVED, DISMISSED, SUPERSEDED) |
| Finding deduplication & supersession linkages | Module 3 | Implemented (SHA-256 fingerprinting) |
| Policy configuration (versioned, authorized) | Module 3 | Implemented (`ValidationPolicyConfig`) |
| Validation run log & run history | Module 3 | Implemented (`ValidationRun`) |
| Versioned REST API endpoints | Module 3 | Implemented (`/api/v1/instruments/...`, `/api/v1/findings/...`) |
| Post-save validation triggers | Module 3 | Triggered on instrument edit, document upload, extraction save |

### What Module 3 does NOT own
| Concern | Owner | Reason |
|---------|-------|--------|
| Document intake, storage & file hashing | Module 2 | Module 2 stores raw files and computes SHA-256 upon upload |
| Document completeness checklist engine | Module 2 | Module 3 integrates with checklist; reports UNABLE_TO_EVALUATE if absent |
| Authoritative bank confirmation | Module 4 | Out of scope; machine extractions are suggestions, not bank confirmation |
| FDR trust-level promotion (L0→L1→L2→L3) | Module 4 | Safety constraint: validation never modifies trust level |
| Maturity scheduling and reminders | Module 5 | Future module |
| Release / refund authorization | Module 6 | Future module |

---

## 2. Directory Structure

```
backend/app/modules/validation/
├── __init__.py                    # Package init; exports models, registry, enums, routers
├── enums.py                       # RuleOutcome, FindingStatus, RuleSeverity, RuleType, FindingCategory
├── models.py                      # SQLAlchemy models: ValidationPolicyConfig, ValidationRun, ValidationFinding
├── extracted_fields_model.py      # SQLAlchemy model: DocumentExtractedFields
├── extracted_fields_service.py    # Service for reading/writing extracted document evidence & auto-triggering
├── normalization.py               # Deterministic reference, bank, and name normalizations
├── registry.py                    # Rule registry, BaseValidationRule, RuleResult, RuleContext
├── engine.py                      # Orchestration engine, duplicate matcher, hash scanner, trigger_post_save
├── finding_service.py             # Finding persistence, idempotency, supersession, dismissal, re-evaluation
├── policy_service.py              # Policy config read/write/versioning
├── schemas.py                     # Pydantic request/response schemas
├── router.py                      # FastAPI endpoints (versioned & backward-compatible)
└── rules/
    ├── __init__.py                # Imports all rules → triggers self-registration
    ├── required_rules.py          # VAL-REQ-001 (Rule A: Configurable required instrument fields)
    ├── amount_rules.py            # VAL-AMT-001 (Rule B: Positive amount), VAL-AMT-002 (Policy minimum)
    ├── date_rules.py              # VAL-DATE-001 (Rule C: Ordering & bounds), VAL-DATE-002 (Expiry), VAL-DATE-003 (Validity term)
    ├── institution_rules.py       # VAL-INST-001 (Rule D: Institution consistency & evidence mismatch)
    ├── document_rules.py          # VAL-DOC-001 (FDR copy present), VAL-DOC-002 (Rule E: Module 2 checklist integration)
    ├── consistency_rules.py       # VAL-CONS-001 (Rule F: Basic data consistency & inactive institution)
    ├── reference_rules.py         # VAL-REF-001 (Reference format & placeholder rejection)
    ├── lien_rules.py              # VAL-LIEN-001 (Lien marked & holder validity)
    ├── reconciliation_rules.py    # Cross-source rules (VAL-XSRC-STALE, VAL-XSRC-001, -002, -003, -004, -006)
    ├── duplicate_rules.py         # Duplicate rules (VAL-DUP-001, VAL-DUP-002, VAL-DUP-003)
    ├── name_similarity_rules.py   # VAL-SIM-001 (Name similarity advisory comparison)
    └── metadata_advisory_rules.py # VAL-META-001 (Document metadata & conversion tool advisory)
```

---

## 3. Implemented Rule Catalogue

| Rule ID | Category | Type | Severity | Description & Operational Behavior |
|---------|----------|------|----------|------------------------------------|
| `VAL-REQ-001` | `CROSS_FIELD_CONSISTENCY` | Deterministic | HIGH | **Required instrument fields.** Evaluates configured fields required for instrument/case type via `REQUIRED_INSTRUMENT_FIELDS` policy. |
| `VAL-AMT-001` | `AMOUNT_CONSISTENCY` | Deterministic | CRITICAL | **Amount positivity.** Verifies registered amount is Decimal > 0.00. |
| `VAL-AMT-002` | `POLICY_COMPLIANCE` | Deterministic | HIGH | **Policy minimum amount.** Compares amount against `MIN_DEPOSIT_AMOUNT_INR` in active policy. Returns `UNABLE_TO_EVALUATE` if unconfigured. |
| `VAL-DATE-001` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Date ordering & bounds.** Checks issue and maturity dates are present, valid calendar dates (1990–2100), and maturity is strictly after issue date. |
| `VAL-DATE-002` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Maturity expiry.** Checks active instruments have not passed maturity date (warning within 90 days; fail if passed). |
| `VAL-DATE-003` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Configured validity period.** Enforces `MIN_VALIDITY_DAYS` / `MAX_VALIDITY_DAYS` only when configured. Returns `NOT_APPLICABLE` when unconfigured. |
| `VAL-INST-001` | `INSTITUTION_ELIGIBILITY` | Deterministic | HIGH | **Institution consistency.** Compares instrument institution association to document evidence. |
| `VAL-DOC-001` | `DOCUMENT_COMPLETENESS` | Deterministic | MEDIUM | **FDR Copy Document.** Checks at least one FDR_COPY document is uploaded and processed. |
| `VAL-DOC-002` | `DOCUMENT_COMPLETENESS` | Deterministic | HIGH | **Module 2 Checklist Integration.** Reads Module 2 checklist result. If no profile exists, returns `UNABLE_TO_EVALUATE`. |
| `VAL-CONS-001` | `CROSS_FIELD_CONSISTENCY` | Deterministic | HIGH | **Basic data consistency.** Enforces inactive institution restrictions and detects contradictory joint/lien flags. |
| `VAL-REF-001` | `REFERENCE_INTEGRITY` | Deterministic | HIGH | **Reference integrity.** Ensures reference number is non-blank, length >= 4, and not a placeholder. |
| `VAL-LIEN-001` | `LIEN_VALIDITY` | Deterministic | HIGH | **Lien validity.** Ensures FDR has lien marked and lien holder specified. |
| `VAL-XSRC-STALE` | `DOCUMENT_INTEGRITY` | Heuristic | MEDIUM | **Stale extraction detector.** Detects extractions performed on older document versions when a newer version has been uploaded. Requires reprocessing. |
| `VAL-XSRC-001` | `CROSS_SOURCE_RECONCILIATION` | Deterministic | HIGH | **Amount reconciliation.** Reconciles entered amount against machine-extracted suggestion. Returns `UNABLE_TO_EVALUATE` if extraction missing/invalid. Never silently overwrites. |
| `VAL-XSRC-002` | `CROSS_SOURCE_RECONCILIATION` | Deterministic | HIGH | **Reference reconciliation.** Compares normalized entered reference with extracted certificate reference. |
| `VAL-XSRC-003` | `CROSS_SOURCE_RECONCILIATION` | Deterministic | HIGH | **Date reconciliation.** Compares entered issue/maturity dates against extracted certificate dates. |
| `VAL-XSRC-004` | `CROSS_SOURCE_RECONCILIATION` | Heuristic | MEDIUM | **Bank reconciliation.** Compares normalized issuing bank names. |
| `VAL-XSRC-006` | `LIEN_VALIDITY` | Heuristic | MEDIUM | **Lien holder reconciliation.** Compares lien holder text only where explicit, readable, and confident (>= 0.70). Otherwise returns `NOT_APPLICABLE`. |
| `VAL-DUP-001` | `POTENTIAL_DUPLICATE` | Heuristic | HIGH | **Intra-institution duplicate reference.** Bank-aware duplicate check detecting instruments sharing same bank + reference in the same institution. Includes permitted summaries. |
| `VAL-DUP-002` | `POTENTIAL_DUPLICATE` | Heuristic | HIGH | **Cross-institution duplicate reference.** Bank-aware duplicate check across institutions. **Preserves tenant isolation by masking foreign institution data.** Routes to authorized officer review. |
| `VAL-DUP-003` | `POTENTIAL_DUPLICATE` | Deterministic | HIGH | **Exact document-hash duplicate bytes.** Detects identical SHA-256 file bytes across instruments. Uses prescribed wording: *"Identical file bytes were previously uploaded. Review the associated instruments and submission context."* Does NOT claim proof of forgery or improper reuse. |
| `VAL-SIM-001` | `CROSS_SOURCE_RECONCILIATION` | Heuristic | MEDIUM | **Name similarity advisory.** Compares registered institution legal name vs extracted depositor name using `difflib.SequenceMatcher`. Shows both strings, method, score, and threshold. Advisory only. |
| `VAL-META-001` | `DOCUMENT_INTEGRITY` | Heuristic | LOW | **Document metadata advisory.** Inspects metadata for conversion tool markers (e.g. iLovePDF, Sejda) or timestamp inversions. Disclaims scanning/conversion artifacts. |

---

## 4. Cross-Source Validation Principles

1. **Extraction is a Suggestion, Not Authoritative Truth:**
   Machine-extracted values (OCR/parsers) are advisory suggestions. They never override or silently overwrite authoritative entered instrument fields.
2. **Missing Extraction is Not a Mismatch:**
   When an extraction is missing, disabled, failed, or unparseable, rules return `UNABLE_TO_EVALUATE`. No false mismatch findings are created.
3. **Stale Extractions are Quarantined:**
   If a new document version is uploaded after extraction, `VAL-XSRC-STALE` flags the discrepancy. Downstream cross-source comparison rules refuse to evaluate against stale versions until reprocessed.
4. **Extraction Never Establishes Legal Authenticity:**
   Machine extractions do not confirm bank validity or release eligibility.

---

## 5. Duplicate Detection & Tenant Privacy Isolation

### Strategy
- **Bank-Aware Reference Matching:**
  Normalizes bank names and reference strings (`[\s\-\/\._]` stripped, uppercase).
  Naive matching across different banks is strictly prevented (e.g., ref `12345` in SBI and ref `12345` in ICICI are recognized as different instruments and produce no duplicate finding).
- **Tenant Isolation:**
  - When a duplicate reference or identical SHA-256 document appears in *another institution*, details of the other institution (legal name, code, contact information, internal IDs) are **masked** (`[tenant-masked]`).
  - Standard institution users cannot see another institution's confidential records through the duplicate detector.
  - The finding is routed exclusively to authorized regulatory scrutiny officers for privileged cross-case investigation.
- **SHA-256 Exact Byte Checks:**
  Uses hashes generated by Module 2 at upload time (never browser-supplied or unverified storage reads).
  Produces neutral, factual advisory findings without accusatory language.

---

## 6. Name Similarity Advisory Architecture

- **Algorithm:** Python standard library `difflib.SequenceMatcher` (Gestalt pattern matching) after prefix, honorific, punctuation, and whitespace normalization.
- **Output:** Explainable output detailing:
  - Both original strings (String A and String B).
  - Normalization and comparison method.
  - Exact similarity score (e.g. `0.880`).
  - Active threshold (default: `0.85`, configurable via policy).
- **Non-Accusatory Classification:**
  - Prefix: `[Advisory — human review required]`
  - Explicit disclaimer: The similarity metric is an advisory heuristic and does not determine legal identity. Borderline matches do not reject a submission or modify instrument trust level.

---

## 7. Finding Lifecycle & Idempotency

- **SHA-256 Fingerprint Deduplication:** Re-running validation sweeps with unchanged inputs updates `last_evaluated_at` idempotently. No duplicate database rows are created.
- **Dismissal Preservation:** Findings dismissed by human reviewers with justification notes remain dismissed on subsequent sweeps unless inputs materially change.
- **Supersession on Changed Inputs:** If inputs change on re-evaluation (e.g. amount corrected, but still failing another threshold), the previous finding transitions to `SUPERSEDED` with `superseded_by_finding_id` pointing to the fresh finding.
- **Resolution on Cleared Condition:** When an issue is fixed and the rule returns `PASS` or `NOT_APPLICABLE`, open/in-review findings for that rule automatically transition to `RESOLVED` with an automated resolution note.

---

## 8. Verification & Test Suite

All 186 unit, integration, and scenario tests pass with **0 failures**:

```
====================== 186 passed in 7.04s ======================
- test_auth_rbac.py:                                    14 passed
- test_documents_module.py:                             16 passed
- test_documents_upload_download.py:                    20 passed
- test_health.py:                                        5 passed
- test_institutions_users.py:                           14 passed
- test_instruments_registry.py:                         12 passed
- test_module1_acceptance.py:                           18 passed
- test_module3_deterministic_rules.py:                  25 passed
- test_module3_prompt3_evidence_reconciliation.py:      15 passed
- test_module3_validation.py:                           43 passed
- test_modules.py:                                       4 passed
```

### Prompt 3 Test Scenarios Verified:
1. Entered amount differs from extracted amount (`VAL-XSRC-001` fires `FAIL`).
2. Matching entered and extracted values produce no discrepancy (`VAL-XSRC-001` passes).
3. Missing extraction creates no false mismatch (`UNABLE_TO_EVALUATE`).
4. Invalid/unparseable extraction output handled gracefully (`UNABLE_TO_EVALUATE`).
5. Stale extraction against older document version identified (`VAL-XSRC-STALE` fires).
6. Intra-institution reference duplicate detected with permitted summaries (`VAL-DUP-001`).
7. Bank-aware cross-institution reference duplicate detected with tenant masking (`VAL-DUP-002`).
8. Similar-looking references from different banks handled conservatively (no false duplicate).
9. Duplicate SHA-256 file bytes across instruments flagged with prescribed neutral wording (`VAL-DUP-003`).
10. Duplicate hash results do not leak cross-tenant records (tenant isolation preserved).
11. Name similarity explains method, strings, score, and threshold (`VAL-SIM-001`).
12. Name similarity does not reject or modify instrument trust level.
13. Metadata advisory labelled as heuristic with disclaimer (`VAL-META-001`).
14. No finding promotes trust level or authorizes financial release.
15. Repeat runs remain idempotent (fingerprints identical, no duplicate rows).
16. Module 1 and Module 2 regression test suites stay 100% green.
