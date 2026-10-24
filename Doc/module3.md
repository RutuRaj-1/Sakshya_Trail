# Module 3 — Validation, Discrepancy & Explainable Intelligence
## Implementation Summary

> **Status:** ✅ Foundation implemented and verified  
> **Revision:** `b3c5d7e9f1a2` (Alembic head)  
> **Tests:** 43 new tests — 146 total across all modules — **0 failures**  
> **Date:** 2026-10-25

---

## 1. Scope

Module 3 implements the **rule-driven validation engine**, **finding persistence**, and **policy configuration** infrastructure for the FDR Sentinel platform. It consumes data from Module 1 (instruments, institutions, users) and Module 2 (documents, document versions) without duplicating their ownership or modifying their records.

### What Module 3 owns
| Concern | Owner |
|---------|-------|
| Rule definitions and registry | Module 3 |
| Deterministic validation checks | Module 3 |
| Cross-field consistency checks | Module 3 |
| Heuristic / advisory checks | Module 3 |
| Finding (discrepancy) persistence & lifecycle | Module 3 |
| Finding deduplication and supersession | Module 3 |
| Policy configuration (versioned, authorized) | Module 3 |
| Validation run log | Module 3 |
| Finding review interfaces (read + dismiss) | Module 3 (Prompt 1) |

### What Module 3 does NOT own
| Concern | Owner |
|---------|-------|
| Document uploads & immutable versioning | Module 2 |
| Authoritative bank verification | Module 4 (future) |
| FDR trust-level promotion (L0→L1→L2→L3) | Module 4 (future) |
| Maturity scheduling and reminders | Module 5 (future) |
| Release / refund authorization | Module 6 (future) |

---

## 2. Directory Structure

```
backend/app/modules/validation/
├── __init__.py                    # Package init; triggers rule self-registration
├── enums.py                       # RuleOutcome, FindingStatus, RuleSeverity, RuleType, FindingCategory
├── models.py                      # SQLAlchemy models
├── registry.py                    # Rule registry, BaseValidationRule, RuleResult, RuleContext
├── engine.py                      # Orchestration engine (run_validation)
├── finding_service.py             # Finding persistence, deduplication, dismissal
├── policy_service.py              # Policy config read/write/versioning
├── schemas.py                     # Pydantic request/response schemas
├── router.py                      # FastAPI API endpoints
└── rules/
    ├── __init__.py                # Imports all rules → self-registration
    ├── date_rules.py              # VAL-DATE-001, VAL-DATE-002
    ├── amount_rules.py            # VAL-AMT-001, VAL-AMT-002
    ├── reference_rules.py         # VAL-REF-001
    ├── lien_rules.py              # VAL-LIEN-001
    ├── document_rules.py          # VAL-DOC-001
    └── duplicate_rules.py         # VAL-DUP-001 (heuristic)
```

---

## 3. Database Models

### 3.1 `validation_policy_configs`

Versioned, authorized, append-only policy configuration records.

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) PK | UUID |
| `institution_id` | VARCHAR(36) FK→institutions | NULL = global |
| `config_key` | VARCHAR(100) | e.g. `MIN_DEPOSIT_AMOUNT_INR` |
| `display_name` | VARCHAR(255) | Human label |
| `config_value` | TEXT | Stored as string; typed by `value_type` |
| `value_type` | VARCHAR(20) | `decimal`, `integer`, `string`, `json_list`, `boolean` |
| `policy_version` | INTEGER | Incremented on each update |
| `is_active` | BOOLEAN | Only one active per (key, institution_id) |
| `authorized_by_user_id` | VARCHAR(36) | SYSTEM_ADMIN only |
| `created_at`, `updated_at` | DATETIME | TimestampMixin |

**Indexes:** `config_key`, `institution_id`, `is_active`, composite `(config_key, institution_id)`, composite `(is_active, config_key)`

### 3.2 `validation_runs`

Lightweight sweep execution log.

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) PK | UUID |
| `instrument_id` | VARCHAR(36) FK→instruments | CASCADE |
| `triggered_by_user_id` | VARCHAR(36) | NULL = system sweep |
| `run_at` | DATETIME | Index |
| `rules_evaluated_csv` | TEXT | Comma-separated rule IDs |
| `outcome_summary_json` | TEXT | `{"PASS":n, "FAIL":n, ...}` |
| `policy_version_ref` | VARCHAR(100) | Policy snapshot reference |
| `new_findings_count` | INTEGER | |
| `resolved_findings_count` | INTEGER | |
| `run_status` | VARCHAR(20) | COMPLETED, PARTIAL, FAILED |

### 3.3 `validation_findings`

Persisted discrepancy records. **Never deleted.**

| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) PK | UUID |
| `finding_fingerprint` | VARCHAR(64) | SHA-256 hex for deduplication |
| `instrument_id` | VARCHAR(36) FK→instruments | CASCADE |
| `institution_id` | VARCHAR(36) FK→institutions | Scope enforcement |
| `document_id` | VARCHAR(36) FK→documents | SET NULL, optional |
| `document_version_id` | VARCHAR(36) FK→document_versions | Exact version at detection |
| `rule_id` | VARCHAR(50) | e.g. `VAL-DATE-001` |
| `rule_version` | VARCHAR(20) | e.g. `1.0` |
| `rule_type` | VARCHAR(20) | `DETERMINISTIC` or `HEURISTIC` |
| `category` | VARCHAR(60) | `FindingCategory` value |
| `severity` | VARCHAR(20) | `CRITICAL/HIGH/MEDIUM/LOW/INFO` |
| `status` | VARCHAR(20) | `FindingStatus` lifecycle |
| `title` | VARCHAR(500) | Short human-readable title |
| `explanation` | TEXT | Full explanation |
| `observed_value` | VARCHAR(500) | Safe, non-sensitive |
| `expected_value` | VARCHAR(500) | Safe, non-sensitive |
| `evidence_refs_json` | TEXT | JSON list of reference UUIDs |
| `suggested_action` | VARCHAR(500) | Next action guidance |
| `policy_version_ref` | VARCHAR(100) | Policy version at evaluation |
| `first_detected_at` | DATETIME | When first seen |
| `last_evaluated_at` | DATETIME | Most recent evaluation |
| `resolved_at` | DATETIME | When status became terminal |
| `resolved_by_user_id` | VARCHAR(36) | Resolver |
| `resolution_note` | TEXT | Human or system note |
| `superseded_by_finding_id` | VARCHAR(36) | Self-FK, SET NULL |
| `validation_run_id` | VARCHAR(36) FK→validation_runs | SET NULL |
| `created_at`, `updated_at` | DATETIME | TimestampMixin |

**Composite Indexes:** `(instrument_id, status)`, `(instrument_id, rule_id)`, `(severity, status)`, `(category, status)`, `first_detected_at`, `last_evaluated_at`

> **Note:** `finding_fingerprint` is intentionally NOT globally unique — the same fingerprint can exist across different `rule_version` values. Deduplication is enforced at the service layer.

---

## 4. Enums

### 4.1 `RuleOutcome` — Single rule execution result

| Value | Meaning |
|-------|---------|
| `PASS` | All checks passed; no discrepancy |
| `FAIL` | Deterministic check failed; finding persisted |
| `WARNING` | Heuristic concern raised; finding persisted with advisory label |
| `NOT_APPLICABLE` | Rule not relevant for this instrument/configuration |
| `UNABLE_TO_EVALUATE` | Required inputs or policy configuration missing |

### 4.2 `FindingStatus` — Finding lifecycle

| Value | Meaning | Terminal? |
|-------|---------|-----------|
| `OPEN` | Newly detected; awaiting review | No |
| `IN_REVIEW` | Reviewer acknowledged | No |
| `DISMISSED` | Human reviewer: not actionable | Yes |
| `RESOLVED` | Underlying issue corrected | No (traceable) |
| `SUPERSEDED` | Replaced by newer rule version finding | Yes |

> **Distinct from:** `Instrument.status` (DRAFT/REGISTERED/RELEASED), `DocumentVersion.processing_status` (PENDING_SCAN/PROCESSED), and `Instrument.trust_level` (L0–L3).

### 4.3 `RuleSeverity`
`CRITICAL` > `HIGH` > `MEDIUM` > `LOW` > `INFO`

### 4.4 `RuleType`
- `DETERMINISTIC` — conclusive logical/mathematical check
- `HEURISTIC` — advisory; findings carry `[Advisory — human review required]` prefix

### 4.5 `FindingCategory`
`DATE_CONSISTENCY`, `AMOUNT_CONSISTENCY`, `REFERENCE_INTEGRITY`, `DOCUMENT_COMPLETENESS`, `LIEN_VALIDITY`, `CROSS_FIELD_CONSISTENCY`, `POTENTIAL_DUPLICATE`, `POLICY_COMPLIANCE`, `INSTITUTION_ELIGIBILITY`, `ADVISORY`, `OTHER`

---

## 5. Rule Registry

### Architecture

All rules are **explicit Python classes** inheriting from `BaseValidationRule`. No `eval()`, no `exec()`, no unrestricted dynamic loading. The `rule_registry` singleton maps stable `rule_id` strings to class instances.

Rules self-register by being imported in `rules/__init__.py`. The registry is read-only after application startup.

### Interface

```python
class BaseValidationRule(abc.ABC):
    rule_id: str        # e.g. "VAL-DATE-001"
    rule_version: str   # e.g. "1.0"
    rule_type: RuleType
    category: FindingCategory
    severity: RuleSeverity
    description: str
    enabled: bool

    @abc.abstractmethod
    def evaluate(self, context: RuleContext) -> RuleResult: ...
```

### Registered Rules (Prompt 1 Foundation)

| Rule ID | Category | Type | Severity | Description |
|---------|----------|------|----------|-------------|
| `VAL-DATE-001` | DATE_CONSISTENCY | Deterministic | HIGH | Maturity date must be after issue date |
| `VAL-DATE-002` | DATE_CONSISTENCY | Deterministic | HIGH | Active instruments must not have past maturity |
| `VAL-AMT-001` | AMOUNT_CONSISTENCY | Deterministic | CRITICAL | Amount must be > 0 |
| `VAL-AMT-002` | POLICY_COMPLIANCE | Deterministic | HIGH | Amount >= policy minimum (UNABLE_TO_EVALUATE if no config) |
| `VAL-REF-001` | REFERENCE_INTEGRITY | Deterministic | HIGH | Reference number non-blank, minimum length, not a placeholder |
| `VAL-LIEN-001` | LIEN_VALIDITY | Deterministic | HIGH | FDR must have lien marked and lien holder set |
| `VAL-DOC-001` | DOCUMENT_COMPLETENESS | Deterministic | MEDIUM | FDR_COPY document must be present and processed |
| `VAL-DUP-001` | POTENTIAL_DUPLICATE | **Heuristic** | MEDIUM | Advisory: same bank+reference exists in registry |

---

## 6. Rule Execution Context

`RuleContext` is a read-only dataclass populated by the engine from live DB data. It carries:
- Instrument fields (status, trust_level, dates, amount, reference, lien, etc.)
- Institution fields (is_active, institution_type)
- Document metadata list (category, processing_status, version IDs — **no content**)
- Policy dict (config values + engine-internal signals like `_duplicate_sibling_count`)

Rules **must not** modify the context, the database, or the instrument.

---

## 7. Finding Deduplication

The finding service uses a SHA-256 fingerprint computed from `(instrument_id, rule_id, rule_version, fingerprint_key)`:

1. **Exact match** (same fingerprint + same rule_version, OPEN/IN_REVIEW): update `last_evaluated_at` only — idempotent re-runs create no duplicates.
2. **New rule version** (same rule_id, different rule_version, OPEN/IN_REVIEW): mark old finding `SUPERSEDED`, create fresh finding.
3. **Rule clears** (PASS or NOT_APPLICABLE): resolve all open findings for that rule — mark `RESOLVED` with automated note.
4. **No matching open finding**: create new finding.

Historical findings are **never deleted**.

---

## 8. Policy Configuration

Rules that depend on configurable thresholds (e.g. minimum deposit amount) consult `ValidationPolicyConfig` records through `policy_service.py`.

**Read path:** institution-specific values take precedence over global; if no active record exists, the rule returns `UNABLE_TO_EVALUATE` with a clear message.

**Write path (SYSTEM_ADMIN only):**
- Deactivates current active record for `(config_key, institution_id)`
- Inserts new versioned record with `policy_version + 1`
- Audited via `log_audit_event()`

> **No threshold values are hard-coded** in the codebase. All policy-dependent rules return `UNABLE_TO_EVALUATE` when no active config exists.

---

## 9. API Endpoints

| Method | Path | Roles | Description |
|--------|------|-------|-------------|
| `POST` | `/api/v1/validation/instruments/{id}/run` | SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD, COMPETENT_AUTHORITY | Trigger validation run |
| `GET` | `/api/v1/validation/instruments/{id}/findings` | All authenticated (institution-scoped) | List findings |
| `GET` | `/api/v1/validation/instruments/{id}/findings/{fid}` | All authenticated (institution-scoped) | Get single finding |
| `POST` | `/api/v1/validation/instruments/{id}/findings/{fid}/dismiss` | SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD | Dismiss finding |
| `GET` | `/api/v1/validation/rules` | All authenticated | List registered rules |
| `GET` | `/api/v1/validation/policy` | SYSTEM_ADMIN, SCRUTINY_OFFICER, BRANCH_HEAD, AUDITOR | Read policy configs |
| `POST` | `/api/v1/validation/policy` | SYSTEM_ADMIN only | Create/update policy config |

> **None of these endpoints modify `Instrument.trust_level`.**

---

## 10. Safety & Integrity Guarantees

| # | Guarantee | Implementation |
|---|-----------|----------------|
| 1 | Validation does not authenticate an FDR | Engine produces findings only; no auth status changed |
| 2 | No finding silently raises trust level | `run_validation()` has a post-execution assertion; trust_level unchanged |
| 3 | No finding independently approves/rejects release | Router has no release endpoints; Module 6 is future scope |
| 4 | Heuristic findings labelled advisory | `_make_result()` prepends `[Advisory — human review required]` for HEURISTIC rules |
| 5 | No fraud/forgery label for rule failure | All finding titles and explanations use neutral, factual language |
| 6 | Missing evidence = UNABLE_TO_EVALUATE | VAL-DOC-001 and VAL-AMT-002 explicitly return `UNABLE_TO_EVALUATE` |
| 7 | Every finding has traceable rule and reason | `rule_id`, `rule_version`, `explanation`, `policy_version_ref` stored on every finding |
| 8 | Evidence scoped to instrument's institution | `institution_id` FK on findings; `_enforce_instrument_scope()` in router |
| 9 | Old document version findings remain traceable | `document_version_id` stored immutably at detection time; never overwritten |

---

## 11. Alembic Migration

**Revision ID:** `b3c5d7e9f1a2`  
**Parent revision:** `a7b2c4d9e8f5` (Module 2 documents)  
**File:** `alembic/versions/2026_10_25_0100-b3c5d7e9f1a2_add_module_3_validation_engine.py`

Tables created (additive — no existing tables modified):
- `validation_policy_configs`
- `validation_runs`
- `validation_findings`

---

## 12. Test Coverage

**Test file:** `tests/test_module3_validation.py` — **43 tests, 0 failures**

| Test Class | Cases |
|-----------|-------|
| `TestRuleRegistrationAndExecution` | Registry contents, rule execution, expired instrument detection |
| `TestRuleDefinitions` | No rule_id raises ValueError, duplicate rule_id raises ValueError, heuristic advisory prefix |
| `TestRuleVersionPersistence` | Finding stores correct rule_version |
| `TestFindingCreationAndRetrieval` | Create finding, retrieve finding, required fields present |
| `TestFindingStatusValidation` | Double-dismiss rejected, status enum values, no overlap with instrument statuses |
| `TestEvidenceLinkIntegrity` | Evidence refs stored as JSON, parsed as list |
| `TestIdempotentEvaluation` | Same input x 2 runs = 1 finding (upsert) |
| `TestFindingPreservation` | Resolved finding preserved in DB, superseded finding preserved |
| `TestUnconfiguredPolicy` | UNABLE_TO_EVALUATE without config, PASS with config, policy set/retrieve |
| `TestTrustLevelProtection` | Service layer assertion, API layer — trust_level unchanged after run |
| `TestAuthorizationIntegration` | INSTITUTION_USER cannot trigger, AUDITOR read-only, cross-institution blocked, policy write ADMIN-only |
| `TestMigrationSchemaPresence` | All 3 new tables present, Module 1/2 tables preserved, fingerprint index exists |
| `TestEngineIntegration` | Full run structure, findings created, run log created, 404 for unknown, rule_ids filter, fingerprint determinism |
| `TestAPIEndpoints` | Run via API, list findings via API, list rules, dismiss finding via API |

**Full regression:** 146 total tests across all modules — **0 failures, 0 errors**

---

## 13. Interfaces Reused from Module 1 & 2

| Interface | Source | Usage |
|-----------|--------|-------|
| `Instrument` model | Module 1 | Rule context, engine queries, FK on findings |
| `Institution` model | Module 1 | Scope enforcement, FK on policy configs |
| `User` model | Module 1 | Auth dependencies, actor fields |
| `Document` / `DocumentVersion` models | Module 2 | Document metadata in rule context, FK on findings |
| `log_audit_event()` | Module 1 audit service | Policy updates, finding creation, dismissal |
| `get_current_active_user()`, `require_roles()`, `enforce_institution_scope()` | Module 1 auth | All validation endpoints |
| `AppException`, `NotFoundException`, `ForbiddenException` | Module 1 common | Exception handling |
| `Base`, `TimestampMixin` | Module 1 db.base | All three new models |
| `get_db()` | Module 1 db.session | FastAPI dependencies |

---

## 14. Incomplete Dependencies / Unresolved Decisions

| Item | Notes |
|------|-------|
| `VAL-AMT-002` threshold | Requires SYSTEM_ADMIN to configure `MIN_DEPOSIT_AMOUNT_INR` before it can evaluate. No default invented. |
| `VAL-DOC-001` accepted states | Checks `PROCESSED`, `CLEAN`, `ACCEPTED`, `SCAN_COMPLETE`. Will align with Module 2's actual scan states. |
| Trust-level promotion | Intentionally out of scope. Module 4 will own L0→L3 promotion. |
| Finding `IN_REVIEW` transition | Data model supports it; the PATCH reviewer workflow is deferred to Prompt 2. |
| Bulk sweep / background scheduler | Prompt 2 scope. Currently findings are produced on-demand via `POST /run`. |
| `psycopg` production driver | Listed in pyproject.toml; SQLite used in tests. PostgreSQL needed for production deployment. |

---

## 15. Files Created / Modified

### New files
```
backend/app/modules/validation/__init__.py
backend/app/modules/validation/enums.py
backend/app/modules/validation/models.py
backend/app/modules/validation/registry.py
backend/app/modules/validation/engine.py
backend/app/modules/validation/finding_service.py
backend/app/modules/validation/policy_service.py
backend/app/modules/validation/schemas.py
backend/app/modules/validation/router.py
backend/app/modules/validation/rules/__init__.py
backend/app/modules/validation/rules/date_rules.py
backend/app/modules/validation/rules/amount_rules.py
backend/app/modules/validation/rules/reference_rules.py
backend/app/modules/validation/rules/lien_rules.py
backend/app/modules/validation/rules/document_rules.py
backend/app/modules/validation/rules/duplicate_rules.py
backend/alembic/versions/2026_10_25_0100-b3c5d7e9f1a2_add_module_3_validation_engine.py
backend/tests/test_module3_validation.py
Doc/module3.md
```

### Modified files
```
backend/app/main.py              — added: import app.modules.validation.models
backend/alembic/env.py           — added: import app.modules.validation.models
backend/app/api/v1/router.py     — added: validation_router registration
```
