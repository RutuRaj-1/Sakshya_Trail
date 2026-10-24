# Module 3 — Validation, Discrepancy & Explainable Intelligence
## Implementation Summary

> **Status:** ✅ Deterministic Rules, Validation Execution & Explainable Findings API Implemented  
> **Revision:** `dde1c7162b37` (Alembic head)  
> **Tests:** 171 passed total across all modules (25 new Prompt 2 tests + 43 Prompt 1 tests + 103 prior modules) — **0 failures**  
> **Date:** 2026-10-25

---

## 1. Scope & Ownership

Module 3 implements the **rule-driven validation engine**, **explainable finding persistence**, and **authorized policy configuration** infrastructure for the FDR Sentinel platform. It consumes data from Module 1 (instruments, institutions, users) and Module 2 (documents, document versions, extracted fields) without duplicating their ownership or modifying their records.

### What Module 3 owns
| Concern | Owner | Status |
|---------|-------|--------|
| Rule definitions and registry | Module 3 | Implemented (11 rules) |
| Deterministic validation checks (Rules A–F) | Module 3 | Fully Implemented & Tested |
| Cross-field consistency & institution checks | Module 3 | Fully Implemented & Tested |
| Heuristic / advisory checks (duplicates) | Module 3 | Implemented |
| Finding persistence, idempotency & lifecycle | Module 3 | Implemented (OPEN, IN_REVIEW, RESOLVED, DISMISSED, SUPERSEDED) |
| Finding deduplication & supersession linkages | Module 3 | Implemented (SHA-256 fingerprinting) |
| Policy configuration (versioned, authorized) | Module 3 | Implemented (`ValidationPolicyConfig`) |
| Validation run log & run history | Module 3 | Implemented (`ValidationRun`) |
| Versioned REST API endpoints | Module 3 | Implemented (`/api/v1/instruments/...`, `/api/v1/findings/...`) |
| Post-save validation trigger | Module 3 | Implemented (`trigger_post_save_validation`) |

### What Module 3 does NOT own
| Concern | Owner | Reason |
|---------|-------|--------|
| Document intake, storage & hashing | Module 2 | Module 2 stores raw files and versions |
| Document completeness checklist engine | Module 2 | Module 3 integrates with checklist; reports UNABLE_TO_EVALUATE if absent |
| Authoritative bank verification | Module 4 | Out of scope; validation does not verify with banks |
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
├── extracted_fields_service.py    # Service for reading/writing extracted document evidence
├── registry.py                    # Rule registry, BaseValidationRule, RuleResult, RuleContext
├── engine.py                      # Orchestration engine, run_validation, trigger_post_save_validation
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
    └── duplicate_rules.py         # VAL-DUP-001 (Heuristic duplicate sibling detection)
```

---

## 3. Implemented Rule Catalogue

| Rule ID | Category | Type | Severity | Description & Policy Version Behavior |
|---------|----------|------|----------|---------------------------------------|
| `VAL-REQ-001` | `CROSS_FIELD_CONSISTENCY` | Deterministic | HIGH | **Rule A — Required instrument fields.** Evaluates configured fields required for instrument/case type. Reads `REQUIRED_INSTRUMENT_FIELDS` from policy; falls back to standard required set if unconfigured. Never invents universal mandates. |
| `VAL-AMT-001` | `AMOUNT_CONSISTENCY` | Deterministic | CRITICAL | **Rule B — Amount positivity.** Verifies registered amount is Decimal > 0.00. |
| `VAL-AMT-002` | `POLICY_COMPLIANCE` | Deterministic | HIGH | **Rule B — Policy minimum amount.** Compares amount against `MIN_DEPOSIT_AMOUNT_INR` in active policy. Returns `UNABLE_TO_EVALUATE` if policy is unconfigured. Never hard-codes an amount threshold. |
| `VAL-DATE-001` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Rule C — Date ordering & bounds.** Checks issue and maturity dates are present, parseable, fall within supported calendar bounds (1990–2100), and maturity is strictly after issue date. |
| `VAL-DATE-002` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Rule C — Maturity expiry.** Checks active instruments have not passed maturity date (warning within 90 days; fail if passed). |
| `VAL-DATE-003` | `DATE_CONSISTENCY` | Deterministic | HIGH | **Rule C — Configured validity period.** Applied **ONLY** when `MIN_VALIDITY_DAYS` or `MAX_VALIDITY_DAYS` is configured in active policy. Returns `NOT_APPLICABLE` when unconfigured. Does not infer universal renewal requirements. |
| `VAL-INST-001` | `INSTITUTION_ELIGIBILITY` | Deterministic | HIGH | **Rule D — Institution consistency.** Compares instrument institution association and master data to available document evidence (e.g. OCR depositor name). Conflicting sources produce an explicit finding with source references without modifying records. |
| `VAL-DOC-001` | `DOCUMENT_COMPLETENESS` | Deterministic | MEDIUM | **Rule E — FDR Copy Document.** Checks at least one FDR_COPY document is uploaded and processed. |
| `VAL-DOC-002` | `DOCUMENT_COMPLETENESS` | Deterministic | HIGH | **Rule E — Module 2 Checklist Integration.** Reads Module 2 checklist result. If Module 2 has no applicable checklist profile, explicitly returns `UNABLE_TO_EVALUATE` rather than declaring all categories missing. |
| `VAL-CONS-001` | `CROSS_FIELD_CONSISTENCY` | Deterministic | HIGH | **Rule F — Basic data consistency.** Enforces inactive institution restrictions (active instrument under inactive institution), detects contradictory joint/lien flags, and verifies valid field combinations. |
| `VAL-REF-001` | `REFERENCE_INTEGRITY` | Deterministic | HIGH | **Reference integrity.** Ensures reference number is non-blank, length >= 4, and not a placeholder (e.g. 'none', 'tbd', 'test'). |
| `VAL-LIEN-001` | `LIEN_VALIDITY` | Deterministic | HIGH | **Lien validity.** Ensures FDR has lien marked and lien holder specified. |
| `VAL-DUP-001` | `POTENTIAL_DUPLICATE` | Heuristic | MEDIUM | **Duplicate sibling advisory.** Advisory finding (`[Advisory — human review required]`) when identical bank + reference exists in registry. |

---

## 4. Structured Finding Explanations

Every generated `ValidationFinding` record contains complete, non-accusatory structured metadata:

- **Rule Provenance:** `rule_id`, `rule_version`, `rule_type` (`DETERMINISTIC` / `HEURISTIC`)
- **Policy Version Reference:** `policy_version_ref` (stores exact policy version evaluated, e.g. `POL-MIN-3M` or `no-policy`)
- **Instrument Identification:** `instrument_id`, `institution_id`
- **Evidence References:** `evidence_refs_json` (JSON list of UUIDs, e.g. document version IDs, audit IDs; never raw documents or secrets)
- **Comparison Basis:** `observed_value` and `expected_value` (safe, factual values)
- **Classification:** `category` (enum) and `severity` (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`)
- **Lifecycle Status:** `status` (`OPEN`, `IN_REVIEW`, `RESOLVED`, `DISMISSED`, `SUPERSEDED`)
- **Plain-Language Explanation:** Factual, neutral phrasing (e.g., "The recorded maturity date is 12 March 2027, while the recorded issue date is 20 March 2027.")
- **Suggested Action:** Prescriptive reviewer guidance (e.g., "Review the source document and correct the data if necessary.")
- **Temporal Tracking:** `first_detected_at`, `last_evaluated_at`, `resolved_at`

---

## 5. Finding Lifecycle, Idempotency & Supersession

```
                 [First Evaluation: Rule Fires]
                                │
                                ▼
                       ┌────────────────┐
                       │     OPEN       │◄────────────────┐
                       └───────┬────────┘                 │
                               │                          │
              ┌────────────────┼────────────────┐         │ (Condition fails
              ▼                ▼                ▼         │  again with same
      [Reviewer Ack]    [Condition Fix]  [Human Dismiss]  │  inputs)
              │                │                │         │
              ▼                │                ▼         │
       ┌─────────────┐         │        ┌─────────────┐   │
       │  IN_REVIEW  │         │        │  DISMISSED  │   │
       └──────┬──────┘         │        └──────┬──────┘   │
              │                │               │          │
              └────────┐       │               │          │
                       ▼       ▼               ▼          │
                     ┌───────────┐      [Unchanged Run:   │
                     │ RESOLVED  │       Stays Dismissed] │
                     └─────┬─────┘                        │
                           │                              │
                           └──────────────────────────────┘
                                  
    [Input Materially Changes OR Rule Version Updated]
                           │
                           ▼
                     ┌────────────┐
                     │ SUPERSEDED │  (Points to new finding via
                     └────────────┘   superseded_by_finding_id;
                                      original evidence preserved)
```

### Idempotency & Transition Semantics
1. **Unchanged Inputs:** Running validation repeatedly on unchanged inputs calculates the identical SHA-256 fingerprint. It updates `last_evaluated_at` only. No duplicate findings are created.
2. **Manually Dismissed Findings:** If a finding was marked `DISMISSED` and validation re-runs with unchanged inputs, the status remains `DISMISSED`. It is **never automatically re-opened**.
3. **Changed Inputs (Same Rule):** If underlying fields change (e.g. amount or dates edited) but the condition still fails with new values, the existing open finding is transitioned to `SUPERSEDED` with `superseded_by_finding_id` linking to the newly created finding. Historical evidence is **never mutated**.
4. **Condition Cleared:** When a rule returns `PASS` or `NOT_APPLICABLE`, all previously `OPEN` or `IN_REVIEW` findings for that rule on that instrument transition to `RESOLVED` with an automated resolution note and timestamp.

---

## 6. API Endpoints

All endpoints are versioned under `/api/v1`, enforce authentication, enforce institution tenant scoping, and log material actions to the audit trail.

### Primary Resource Endpoints
| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `POST` | `/api/v1/instruments/{instrument_id}/validation-runs` | SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD, COMPETENT_AUTHORITY | Trigger full or selective validation run |
| `GET` | `/api/v1/instruments/{instrument_id}/validation-runs` | All authenticated (tenant-scoped) | List validation run logs with pagination |
| `GET` | `/api/v1/instruments/{instrument_id}/findings` | All authenticated (tenant-scoped) | List findings with status/severity/category filters and allow-listed sort |
| `GET` | `/api/v1/findings/{finding_id}` | All authenticated (tenant-scoped) | Get single finding by ID |
| `POST` | `/api/v1/findings/{finding_id}/re-evaluate` | SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD | Re-evaluate specific finding's rule |
| `POST` | `/api/v1/instruments/{instrument_id}/rules/{rule_id}/evaluate` | SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD | Evaluate single allow-listed rule (no arbitrary code execution) |

### Module Compatibility Endpoints
| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `POST` | `/api/v1/validation/instruments/{id}/run` | Internal review roles | Alias for validation run |
| `GET` | `/api/v1/validation/instruments/{id}/findings` | All authenticated (tenant-scoped) | Alias for instrument findings |
| `GET` | `/api/v1/validation/instruments/{id}/findings/{fid}` | All authenticated (tenant-scoped) | Alias for single finding |
| `POST` | `/api/v1/validation/instruments/{id}/findings/{fid}/dismiss` | SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD | Dismiss finding with mandatory reason |
| `GET` | `/api/v1/validation/rules` | All authenticated | List registered rules in rule registry |
| `GET` | `/api/v1/validation/policy` | Review & audit roles | List active policy configurations |
| `POST` | `/api/v1/validation/policy` | SYSTEM_ADMIN only | Create / update versioned policy configuration |

---

## 7. Validation Modes & Summary Metadata

### Supported Modes
1. **Explicit Full Evaluation:** Evaluates all enabled rules registered in the system.
2. **Selective Evaluation by Rule IDs:** Evaluates a server-side allow-listed subset (`payload.rule_ids`).
3. **Selective Evaluation by Category:** Evaluates rules belonging to a specific category (`payload.category`).
4. **Single Rule Execution:** Evaluates a single allow-listed rule via `/instruments/{id}/rules/{rule_id}/evaluate`.
5. **Post-Save Safe Trigger:** Automatic trigger (`trigger_post_save_validation`) called after an instrument is created or materially updated. Does not fail instrument operations if a rule errors.

### Validation Run Execution Summary
Every `ValidationRun` persists aggregate execution metadata and returns:
- `rules_evaluated`: List of rule IDs evaluated
- `passes_count`: Count of `PASS` outcomes
- `failures_count`: Count of `FAIL` outcomes
- `warnings_count`: Count of `WARNING` outcomes
- `not_applicable_count`: Count of `NOT_APPLICABLE` outcomes
- `unable_to_evaluate_count`: Count of `UNABLE_TO_EVALUATE` outcomes
- `new_findings_count`: Count of newly created findings
- `resolved_findings_count`: Count of cleared findings
- `policy_version_ref`: Snapshot of policy version in effect

---

## 8. Safety & Separation of Concerns

1. **No Trust Level Changes:** Validation rules produce findings only. The engine asserts that `Instrument.trust_level` is unmodified before and after evaluation.
2. **No Administrative Lifecycle Changes:** Failed rules never mark an instrument fraudulent, never perform bank confirmation, and never approve or reject a release.
3. **No Direct Client Injections:** Clients cannot directly POST finding severity, outcomes, evidence, or status overrides.
4. **Safe Error Isolation:** Any rule raising an unhandled exception is caught and recorded as `UNABLE_TO_EVALUATE` without crashing the sweep or other rules.

---

## 9. Database Migrations

Two Alembic revisions define Module 3 persistence:

1. `b3c5d7e9f1a2` (`2026_10_25_0100`):
   - `validation_policy_configs`: Versioned policy configurations
   - `validation_runs`: Run execution log
   - `validation_findings`: Persisted discrepancy records

2. `dde1c7162b37` (`2026_10_25_0219`):
   - `document_extracted_fields`: Structured OCR/pipeline extracted document metadata for cross-validation

---

## 10. Automated Test Results

Total test suite across all modules: **171 passed, 0 failures, 0 errors**.

```
tests/test_auth_rbac.py ...........................                       [ 15%]
tests/test_health.py ..........                                           [ 21%]
tests/test_institutions_users.py ..................................       [ 41%]
tests/test_instruments_registry.py ....................                  [ 53%]
tests/test_module1_acceptance.py .........                                [ 58%]
tests/test_module3_deterministic_rules.py .........................       [ 73%]
tests/test_module3_validation.py ........................................ [ 98%]
                                 ...
tests/test_modules.py ..                                                  [100%]
============================== 171 passed in 6.5s ==============================
```

Exact command to run Module 3 tests:
```bash
pytest backend/tests/test_module3_deterministic_rules.py backend/tests/test_module3_validation.py
```
Output: **68 passed, 0 failures**.
