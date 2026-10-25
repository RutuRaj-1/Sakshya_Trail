# Audit Integrity, SHA-256 Hash Chaining & Cryptographic Verification

**Project:** FDR Sentinel (SIH 2026 Problem Statement ID 26265)  
**Module:** Module 7 — Prompt 5: Security Hardening & Audit Integrity  
**Applicable PRD Specifications:** PRD-FR-090, PRD-FR-091, PRD-FR-092, PRD-FR-093, PRD-FR-094, PRD-FR-095, PRD-FR-096  

---

## 1. Architectural Overview

FDR Sentinel implements a **tamper-evident, append-only regulatory audit ledger** where every material business and security operation is cryptographically linked using SHA-256 hash chains. The ledger ensures that any unauthorized retroactive modification, deletion, reordering, or injection of audit events is immediately detectable by automated verifiers.

```
       +-------------------------------------------------------+
       | Genesis Block: Sequence #1                            |
       | previous_hash: 00000000000000000000000000000000...   |
       | payload: {action, entity, actor, timestamp, ...}      |
       | current_hash: SHA-256(canonical(Block 1))             |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       | Block 2: Sequence #2                                  |
       | previous_hash: SHA-256(canonical(Block 1))            |
       | payload: {action, entity, actor, timestamp, ...}      |
       | current_hash: SHA-256(canonical(Block 2))             |
       +-------------------------------------------------------+
                                   |
                                   v
       +-------------------------------------------------------+
       | Block 3: Sequence #3                                  |
       | previous_hash: SHA-256(canonical(Block 2))            |
       | payload: {action, entity, actor, timestamp, ...}      |
       | current_hash: SHA-256(canonical(Block 3))             |
       +-------------------------------------------------------+
```

---

## 2. Central Audit Event Schema

All material actions across Modules 1 through 7 write to the central `audit_events` table managed via [models.py](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/audit/models.py):

| Column Name | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | PRIMARY KEY | Stable UUID v4 identifier. |
| `sequence_number` | `BIGINT` | UNIQUE, INDEXED | Continuous monotonic ledger sequence index (Block #1, #2, ...). |
| `action` | `VARCHAR(100)` | NOT NULL, INDEXED | Structured action code (e.g., `INSTRUMENT_CREATED`, `RELEASE_APPROVED`). |
| `entity_type` | `VARCHAR(50)` | NOT NULL, INDEXED | Target domain model (`INSTRUMENT`, `RELEASE_CASE`, `USER`, etc.). |
| `entity_id` | `VARCHAR(100)` | NOT NULL, INDEXED | Stable identifier of the affected domain entity. |
| `actor_user_id` | `VARCHAR(36)` | NULLABLE, INDEXED | UUID of the performing user, or NULL for background system jobs. |
| `actor_email` | `VARCHAR(255)` | NULLABLE, INDEXED | Authenticated email of the actor. |
| `actor_role` | `VARCHAR(50)` | NULLABLE | Assigned RBAC role at the moment of execution. |
| `outcome` | `VARCHAR(20)` | NOT NULL, DEFAULT `'SUCCESS'` | Execution outcome: `SUCCESS`, `FAILURE`, or `DENIED`. |
| `request_id` | `VARCHAR(64)` | NULLABLE | Correlation ID linking audit event to the HTTP request tracing context. |
| `ip_address` | `VARCHAR(45)` | NULLABLE | Client IP address (sanitized). |
| `policy_version` | `VARCHAR(50)` | NULLABLE | Effective regulatory policy version governing the operation. |
| `metadata_json` | `TEXT` | NULLABLE | Sanitized JSON before/after state diffs and context parameters. |
| `previous_hash` | `CHAR(64)` | NOT NULL | Hex SHA-256 digest of the immediately preceding audit event. |
| `current_hash` | `CHAR(64)` | NOT NULL, INDEXED | Cryptographic SHA-256 digest over the canonicalized event payload. |
| `created_at` | `DATETIME` | NOT NULL, INDEXED | Immutable UTC timestamp recorded upon commit. |

---

## 3. Cryptographic Hashing & Deterministic Canonicalization

### 3.1 Algorithm & Genesis Representation
- **Hashing Algorithm:** Cryptographic SHA-256 (`hashlib.sha256`) outputting a 64-character lowercase hexadecimal string.
- **Genesis Block:** Sequence #1 links to `previous_hash = "0" * 64` (`0000000000000000000000000000000000000000000000000000000000000000`).

### 3.2 Canonical JSON Serialization Rules
To prevent hash divergence caused by whitespace differences, dictionary key ordering, or timestamp formatting, [service.py](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/audit/service.py) enforces:
1. **Sorted Keys:** `json.dumps(..., sort_keys=True)` guarantees invariant alphabetical attribute ordering.
2. **Compact Separators:** `separators=(',', ':')` eliminates variable indentation, trailing spaces, and newlines.
3. **Strict UTC Timestamp Normalization:** Datetime objects are converted to UTC and serialized using RFC 3339 / ISO 8601 (`YYYY-MM-DDTHH:MM:SS.mmmmmm+00:00`). Naive datetimes are explicitly bound to `timezone.utc`.
4. **Ascii Safety:** `ensure_ascii=True` escapes Unicode characters into deterministic ASCII byte representations.
5. **Masking Sensitive Data:** `sanitize_dict` recursively replaces passwords, authentication tokens, API keys, and session secrets with `[REDACTED]`.

### 3.3 Hashed Field Specification
The SHA-256 digest covers the exact payload dictionary:
```json
{
  "action": "INSTRUMENT_CREATED",
  "actor_email": "officer@aicte.gov.in",
  "actor_role": "SCRUTINY_OFFICER",
  "actor_user_id": "usr-123",
  "created_at": "2026-10-25T17:06:06.646489+00:00",
  "entity_id": "inst-456",
  "entity_type": "INSTRUMENT",
  "id": "18c801f0-380b-40f0-bea1-2262ccf544ab",
  "metadata": {"amount": "1000000.00", "reference_number": "FDR-2026-001"},
  "outcome": "SUCCESS",
  "policy_version": "v1.0.0",
  "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "request_id": "req-999",
  "sequence_number": 1
}
```

---

## 4. Append-Only Database Protection & Mutation Rejection

### 4.1 Database-Level Triggers
Alembic migration [2026_10_25_1300-b9c0d1e2f3a4_add_audit_hash_chain.py](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/alembic/versions/2026_10_25_1300-b9c0d1e2f3a4_add_audit_hash_chain.py) configures native database triggers that reject raw SQL `UPDATE` and `DELETE` queries:
- **SQLite:** Triggers `prevent_audit_update` and `prevent_audit_delete` execute `SELECT RAISE(ABORT, 'Mutation of audit records is strictly prohibited: audit_events table is append-only')`.
- **PostgreSQL:** PL/pgSQL function `prevent_audit_events_mutation()` raises exception `SQLSTATE 42501 (insufficient_privilege)`.

### 4.2 Application ORM Event Listeners
In [models.py](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/audit/models.py), SQLAlchemy event listeners intercept `before_update` and `before_delete` on `AuditEvent`:
```python
@event.listens_for(AuditEvent, "before_update")
def receive_before_update(mapper, connection, target):
    if getattr(target, "_allow_audit_migration", False):
        return
    raise PermissionError("Mutation of audit records is strictly prohibited: audit_events table is append-only.")
```

### 4.3 Endpoint Absence
The backend application has **no** REST endpoint for editing or deleting audit events. All audit router operations are strictly `GET` (for listing and inspection) and `POST` (for invoking the verification engine).

---

## 5. Cryptographic Verification & Replay Engine

The verification engine [audit_query_service.py](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/dashboard/audit_query_service.py) re-evaluates the cryptographic validity of the entire sequence:

```python
POST /api/v1/audit/verify
```

### 5.1 Verification Checks
1. **Sequence Monotonicity:** Verifies continuous increments ($1, 2, 3, \dots, n$). Any skipped index triggers `SEQUENCE_GAP_OR_REORDER`.
2. **Previous Hash Linkage:** Verifies that event $n$'s `previous_hash` exactly equals event $n-1$'s `current_hash`. Any broken link triggers `BROKEN_CHAIN_LINK`.
3. **Canonical Payload Recomputation:** Recomputes the canonical SHA-256 digest across all fields and compares against stored `current_hash`. Any altered field, whitespace, or tampering triggers `PAYLOAD_TAMPERED`.
4. **Timestamp Monotonicity:** Verifies non-decreasing timestamps across the sequence.

### 5.2 Verification Response Example (Pass)
```json
{
  "status": "PASS",
  "is_chain_intact": true,
  "total_events_in_scope": 42,
  "verified_count": 42,
  "latest_sequence_number": 42,
  "chain_head_hash": "86cd8157c91e8c5c79f969b0eaeac74d5e9a084836adb2e598107caff065c233",
  "first_inconsistency": null,
  "verification_timestamp": "2026-10-25T17:19:38.113410+00:00",
  "verification_scope_description": "Full audit sequence (Blocks #1 to #42) verified intact."
}
```

### 5.3 Forensic Diagnosis on Inconsistency (Tamper Detected)
If tampering occurs, the verifier stops at the earliest corrupted block without rewriting data:
```json
{
  "status": "TAMPER_DETECTED",
  "is_chain_intact": false,
  "total_events_in_scope": 42,
  "verified_count": 14,
  "latest_sequence_number": 14,
  "chain_head_hash": "a1b2c3d4...",
  "first_inconsistency": {
    "sequence_number": 15,
    "event_id": "9a8b7c6d-1234-4567-8901-abcdef123456",
    "failure_type": "PAYLOAD_TAMPERED",
    "expected_hash": "c38f0a843c9c66988ea6d3059bd742d3ded3dd45a0688b3a062fd75716fa2e8d",
    "actual_hash": "86cd8157c91e8c5c79f969b0eaeac74d5e9a084836adb2e598107caff065c233",
    "safe_explanation": "Payload modification detected at sequence #15: recorded current_hash does not match canonical payload digest."
  },
  "verification_timestamp": "2026-10-25T17:25:00.000000+00:00",
  "verification_scope_description": "Verification failed at sequence #15."
}
```

---

## 6. Access Control, Scoping & Separation of Duties

1. **Auditor Role (PRD-FR-095):**
   - Read-only access across all audit events and operational reports.
   - Authorized to execute `/api/v1/audit/verify`.
   - Strictly forbidden from initiating or approving release requests, editing instruments, or changing policies.
2. **System Administrator Boundary (Maker-Checker):**
   - System administrators cannot approve security deposit releases or refunds. Release approval is exclusively restricted to `COMPETENT_AUTHORITY`.
3. **Multi-Tenant Scoping (PRD-FR-090):**
   - Institution users (`INSTITUTION_USER`) can only query audit events belonging to instruments owned by their institution (`instrument.institution_id == user.institution_id`). Cross-institution queries return empty sets or `403 Forbidden`.
4. **Security Violation Auditing (PRD-FR-094):**
   - All unauthorized cross-tenant query attempts, failed logins, and prohibited role escalation attempts write `DENIED` audit events to the ledger.

---

## 7. Residual Risks & Security Disclaimers

> [!IMPORTANT]
> **Cryptographic Tamper-Evidence vs. Absolute Immutability:**
> A SHA-256 hash chain provides mathematical **tamper-evidence**: any retroactive change to recorded payloads or ordering is detectable upon verification.
> However, an internal hash chain stored within a relational database does not prevent a database superuser from dropping the database or rewriting all blocks from genesis.
>
> **Production Recommendations for External Anchoring:**
> 1. Periodic external anchoring via RFC 3161 Trusted Timestamp Authority (TSA) or signed transparency logs.
> 2. Database user privilege separation where the application runtime database user has only `INSERT` and `SELECT` privileges on the `audit_events` table, while `UPDATE` and `DELETE` privileges are revoked entirely.
> 3. Write-once, read-many (WORM) storage mirroring for archived audit log partitions.
