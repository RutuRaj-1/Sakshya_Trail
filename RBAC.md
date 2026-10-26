# SakshyaTrail RBAC — Canonical Permission Model (Source of Truth)

> **This document is the single authoritative RBAC reference for SakshyaTrail.**
> All backend `require_roles()` guards, service-layer checks, state-machine transition matrices,
> frontend `allowedRoles` guards, and tests MUST align with this document.
> Last reconciled: 2026-10-27 against codebase commit `61f41af`.

---

## 1. Role Catalogue

| Role Constant | Value | Tenant | Description |
|---|---|---|---|
| `ROLE_SYSTEM_ADMIN` | `SYSTEM_ADMIN` | None (internal) | Platform superuser; full read/write across all modules |
| `ROLE_SCRUTINY_OFFICER` | `SCRUTINY_OFFICER` | None (internal) | L1/L2 regulatory examiner; reviews instruments and release cases |
| `ROLE_BRANCH_HEAD` | `BRANCH_HEAD` | None (internal) | Senior officer; approves policies, oversees officer actions |
| `ROLE_COMPETENT_AUTHORITY` | `COMPETENT_AUTHORITY` | None (internal) | Final approver for release/discharge decisions |
| `ROLE_FINANCE_OFFICER` | `FINANCE_OFFICER` | None (internal) | Records release orders and confirms bank-side actions |
| `ROLE_INSTITUTION_USER` | `INSTITUTION_USER` | institution_id | Nodal officer for an AICTE-registered institution |
| `ROLE_AUDITOR` | `AUDITOR` | None (internal) | Read-only compliance auditor; never mutates state |

> **Invariant**: Internal roles MUST NOT have `institution_id`. `INSTITUTION_USER` MUST have `institution_id`.

---

## 2. Column Key

`SA=SYSTEM_ADMIN  SO=SCRUTINY_OFFICER  BH=BRANCH_HEAD  CA=COMPETENT_AUTHORITY`
`FO=FINANCE_OFFICER  IU=INSTITUTION_USER  AU=AUDITOR`
`Y=Allowed  -=Denied  Y*=Allowed (own institution scope only)  Y(r)=Read-only`

---

## 3. Permission Matrix by Module

### Module 1 — Instrument Registry

| Operation | SA | SO | BH | CA | FO | IU | AU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Register / create instrument | Y | Y | Y | - | - | Y* | - |
| Edit instrument (pre-L2) | Y | Y | Y | - | - | Y* | - |
| Archive instrument | Y | Y | Y | - | - | - | - |
| View instrument list / detail | Y | Y | Y | Y | Y | Y* | Y |
| Update trust level | Y | Y | Y | - | - | - | - |

### Module 2 — Document Evidence

| Operation | SA | SO | BH | CA | FO | IU | AU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Upload document | Y | Y | Y | - | - | Y* | - |
| List / view / download documents | Y | Y | Y | Y | Y | Y* | Y |

### Module 3 — Validation Engine

| Operation | SA | SO | BH | CA | FO | IU | AU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Trigger validation run | Y | Y | Y | Y | - | - | - |
| View runs / findings | Y | Y | Y | Y | Y | Y* | Y |
| Review queue (L2) | Y | Y | Y | Y | - | - | Y(r) |
| Dismiss / override finding | Y | Y | Y | - | - | - | - |

### Module 4 — Trust, Provenance and Verification

| Operation | SA | SO | BH | CA | FO | IU | AU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| View provenance / trust state / history | Y | Y | Y | Y | Y | Y* | Y |
| Generic trust transition (L0/L1) | Y | Y | Y | - | - | - | - |
| L1 reassessment | Y | Y | Y | - | - | - | - |
| L2 officer decision | Y | Y | Y | - | - | - | - |
| L3 bank confirmation | Y | Y | Y | - | - | - | - |
| Trust downgrade | Y | Y | Y | - | - | - | - |
| Create / dispatch / retry / cancel verification | Y | Y | Y | - | - | - | - |
| Record manual evidence | Y | Y | Y | - | - | - | - |
| View verification requests | Y | Y | Y | Y | Y | Y* | Y |

**Key invariant**: L2 and L3 are gated in `trust_service.py` (service layer) regardless of router-level auth.

### Module 5 — Lifecycle and Renewal

| Operation | SA | SO | BH | CA | FO | IU | AU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Create lifecycle policy | Y | - | - | - | - | - | - |
| Approve policy | Y | - | - | Y | - | - | - |
| Activate policy | Y | - | - | - | - | - | - |
| List / view policies | Y | Y | Y | Y | Y | Y | Y |
| Create lineage link | Y | Y | Y | - | - | Y* | - |
| View lineage / continuity | Y | Y | Y | Y | Y | Y* | Y |
| Correct lineage | Y | Y | Y | - | - | - | - |
| Create renewal successor | Y | Y | Y | - | - | Y* | - |
| Lifecycle evaluate | Y | Y | Y | Y | Y | Y* | Y |
| Trigger scheduler / demo clock | Y | - | - | - | - | - | - |
| View notifications | Y | Y | Y | Y | Y | Y* | Y |

### Module 6 — Release and Refund Case Management

| Operation | SA | SO | BH | CA | FO | IU | AU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Create release request (draft) | Y | - | - | - | - | Y | - |
| Submit draft | Y | - | - | - | - | Y | - |
| List / view release requests | Y | Y | Y | Y | Y | Y* | Y |
| Add review observation | Y | Y | Y | Y | - | - | - |
| Start review (submitted → under_review) | Y | Y | Y | - | - | - | - |
| Return for correction | Y | Y | Y | - | - | - | - |
| Recommend for authority | Y | Y | Y | - | - | - | - |
| **Approve release** | - | - | - | Y | - | - | - |
| **Reject release** | Y | - | - | Y | - | - | - |
| Evaluate readiness | Y | Y | Y | Y | - | - | - |
| Check release gate | Y | Y | Y | Y | - | - | - |
| **Record release order** | Y | - | - | Y | Y | - | - |
| **Confirm bank action** | Y | - | Y | Y | Y | - | - |
| **Close release case** | Y | - | Y | Y | Y | - | - |

**Maker-checker invariant**: APPROVE is strictly restricted to `COMPETENT_AUTHORITY` (even `SYSTEM_ADMIN` cannot bypass this regulatory approval gate) and enforces `current_user != requester` AND `current_user != primary_reviewer`.

### Module 7 — Command Center and Audit

| Operation | SA | SO | BH | CA | FO | IU | AU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Dashboard / command center / priority queue | Y | Y | Y | Y | Y | Y* | Y |
| Search / instrument snapshot | Y | Y | Y | Y | Y | Y* | Y |
| View scrutiny observations | Y | Y | Y | Y | Y | Y* | Y |
| Create scrutiny observation | Y | Y | Y | Y | Y | - | - |
| Resolve scrutiny observation | Y | Y | Y | Y | - | - | - |
| Amend scrutiny observation | Y | Y | Y | Y | Y | - | - |
| Query audit events | Y | Y | Y | Y | Y | Y*(own) | Y |
| **Verify audit chain integrity** | Y | - | Y | Y | - | - | Y |
| Reports / export CSV / PDF | Y | Y | Y | Y | Y | Y* | Y |

---

## 4. Cross-Cutting Security Invariants

### 4.1 Tenant Isolation
- `INSTITUTION_USER` is always scoped to `user.institution_id` at service/dependency layer
- Cross-institution access returns `403 FORBIDDEN_CROSS_TENANT_ACCESS`
- Tenant scope is NOT enforced via query-param alone

### 4.2 Auditor Read-Only (PRD-FR-095)
- `AUDITOR` has NO write access on any endpoint
- `create_observation` is blocked for `AUDITOR` in `observation_service.py`
- `AUDITOR` cannot trigger validation, verification, trust transitions, or release decisions

### 4.3 FINANCE_OFFICER Scope
- `FINANCE_OFFICER` has no L2/L3 trust transition rights
- Handles ONLY: post-approval release order recording, bank action confirmation, case closure
- Excluded from: instrument creation, validation triggers, review decisions, scrutiny observation resolution

### 4.4 Maker-Checker (PRD-FR-Module 6)
- Institution user submits → Officer reviews → Competent Authority approves
- `check_maker_checker_separation()` enforces: requester cannot approve own request;
  primary reviewer cannot be final approver

### 4.5 COMPETENT_AUTHORITY Scope
- Does NOT participate in instrument registration, document uploads, or trust transitions
- Acts only in release approval workflow and lifecycle policy approval

---

## 5. Resolved Gaps (Prompt 1 Audit)

| # | Module | Gap | Resolution |
|---|---|---|---|
| 1 | audit_query_service.py | `User` under `TYPE_CHECKING` = `NameError` at runtime | Fixed: direct import |
| 2 | DB schema | `audit_events` missing `sequence_number`, `previous_hash`, `current_hash`, `policy_version` | Fixed: DDL applied |
| 3 | DB schema | `instruments` missing `effective_date` | Fixed: DDL applied |
| 4 | DB schema | `lifecycle_notifications` missing `batch_id` | Fixed: DDL applied |
| 5 | DB schema | `validation_findings` missing `assigned_to_user_id`, `assigned_at`, `review_notes_json`, `concurrency_version` | Fixed: DDL applied |
| 6 | Alembic | Stamp at `a1b2c3d4e5f6`, head at `b9c0d1e2f3a4` | Fixed: stamped to head |
| 7 | DB triggers | SQLite append-only triggers for `audit_events` not applied | Fixed: triggers created |
| 8 | release/router.py | `evaluate-readiness` missing `BRANCH_HEAD` | Fixed in router |
| 9 | release/router.py | `check-gate` missing `BRANCH_HEAD` | Fixed in router |
| 10 | release/router.py | `record-order` and `/orders` allowed `SCRUTINY_OFFICER`, `BRANCH_HEAD` (violates state machine) | Fixed: aligned to `FINANCE_OFFICER`, `COMPETENT_AUTHORITY`, `SYSTEM_ADMIN` |
| 11 | release/router.py | `confirm-bank-action` missing `FINANCE_OFFICER` | Fixed in router |
| 12 | release/router.py | `close-case` allowed `SCRUTINY_OFFICER`, missing `FINANCE_OFFICER` | Fixed in router |
| 13 | release/router.py | `approve` endpoint maker-checker separation of duties | Enforced: strictly `COMPETENT_AUTHORITY` only (`SYSTEM_ADMIN` excluded to prevent administrative override of statutory release decision) |
| 14 | export_service.py | Phantom role `AUDIT_EXAMINER` in `ALLOWED_EXPORT_ROLES` | Fixed: removed; `FINANCE_OFFICER` added |

---

## 6. Frontend Route Guard Reference

| Route | allowedRoles guard | Notes |
|---|---|---|
| `/dashboard` | None (auth only) | All roles; content gated |
| `/command-center` | None (auth only) | All roles |
| `/instruments` | None (auth only) | Backend tenant scoping |
| `/documents` | None (auth only) | Backend enforced |
| `/monitoring` | None (auth only) | Backend enforced |
| `/institutions` | None (auth only) | INSTITUTION_USER sees own only |
| `/release` | None (auth only) | Backend enforced |
| `/findings/queue` | None (auth only) | Backend enforced |
| `/verification` | None (auth only) | Backend enforced |
| `/audit` | `[SYSTEM_ADMIN, AUDITOR, BRANCH_HEAD, COMPETENT_AUTHORITY]` | Frontend + backend |
| `/users` | `[SYSTEM_ADMIN]` | Frontend + backend |
| `/search` | None (auth only) | Backend enforced |
| `/reports` | None (auth only) | Backend enforced |

---

*Generated by Prompt 1 — SakshyaTrail RBAC Audit and Permission Reconciliation.*
*This document supersedes all prior RBAC documentation.*
