# SakshyaTrail — Comprehensive RBAC & Security Architecture Specification

**SIH Problem Statement ID:** 26265  
**Platform:** SakshyaTrail — Security Deposit & FDR Lifecycle Integrity Platform  
**Document Status:** Production Authoritative Specification  

---

## 1. Architectural Foundations of SakshyaTrail RBAC

The authorization architecture of **SakshyaTrail** is built upon five foundational security invariants designed to protect public funds, preserve regulatory sanctity, and ensure non-repudiable auditability:

1. **Deny-by-Default & Server-Side Enforcement:**
   Every API endpoint requires an authenticated JWT session (delivered via secure `HttpOnly` cookie or fallback `Bearer` token). Authorization is strictly declared using FastAPI's `require_roles(...)` dependency and executed server-side. Every request performs a fresh server-side user lookup, ensuring deactivated or modified accounts lose access immediately. Client-side route guards serve purely for UX routing and never replace backend security gates.

2. **Multi-Tenant Boundary Isolation:**
   Tenant boundaries are hardware- and query-enforced at the database layer. An `INSTITUTION_USER` is cryptographically and logically bound to their `user.institution_id`. Any attempt by an institutional user to query, mutate, or download instruments, evidence documents, or release cases belonging to another institution is intercepted by `enforce_institution_scope(...)` and rejected with `403 FORBIDDEN_CROSS_TENANT_ACCESS`. Internal regulatory roles (`SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, etc.) operate across institutions and must never have an `institution_id` assigned.

3. **Strict Maker-Checker Separation (The 4-Eye Principle):**
   Regulatory actions with legal or fiscal impact enforce mandatory separation of duties:
   - **FDR Release Sanction (Module 6):** The officer who scrutinizes the case and conducts readiness evaluations (Maker) **cannot** be the authority who sanctions the final discharge order (Checker).
   - The statutory approval endpoint (`POST /release/requests/{id}/approve`) is **strictly restricted to `COMPETENT_AUTHORITY`**. Even `SYSTEM_ADMIN` is barred from approving release requests to prevent administrative override of statutory release powers.
   - The backend service layer strictly enforces: `current_user.id != release_request.created_by_user_id` AND `current_user.id != release_request.primary_reviewer_id`.

4. **Independent Auditor Read-Only Invariance (PRD-FR-095):**
   The `AUDITOR` role has comprehensive read access across all 7 platform modules, operational reports, and the complete audit ledger. However, `AUDITOR` is barred from all state mutations (`POST`, `PUT`, `PATCH`, `DELETE`). The backend dependency `require_read_only_or_permitted` intercepts and blocks any state-changing attempts by an auditor with `HTTP 403 Forbidden`.

5. **Append-Only Cryptographic Audit Invariance (PRD-FR-093):**
   Every state mutation across all modules emits an audit event into the append-only ledger (`audit_events`). Each block computes a SHA-256 hash linking back to `GENESIS_HASH` through a strictly monotonic sequence (`sequence_number`, `previous_hash`, `current_hash`). SQLite and PostgreSQL append-only triggers prevent `UPDATE` or `DELETE` operations on this table. Any manual database tampering breaks the cryptographic verification chain.

---

## 2. Overview of the 7 Application Roles

| Role Identifier | Role Enum Constant | Real-World Persona | Operational Scope & Jurisdiction | Dedicated Workspace |
|---|---|---|---|---|
| `INSTITUTION_USER` | `ROLE_INSTITUTION_USER` | College Principal, Registrar, Nodal Officer | Single Institution (`user.institution_id`) | `<InstitutionWorkspace />` |
| `SCRUTINY_OFFICER` | `ROLE_SCRUTINY_OFFICER` | AICTE Scrutiny Officer, Desk Reviewer | National / Desk Queue, Maker Actions | `<ScrutinyOfficerWorkspace />` |
| `BRANCH_HEAD` | `ROLE_BRANCH_HEAD` | Regional Officer, Regional Director (WRO, SRO, etc.) | Regional Jurisdiction & Escalation Gate | `<BranchHeadWorkspace />` |
| `COMPETENT_AUTHORITY` | `ROLE_COMPETENT_AUTHORITY` | Member Secretary, Bureau Head, Sanctioning Authority | National Portfolio, Final Release Checker | `<CompetentAuthorityWorkspace />` |
| `FINANCE_OFFICER` | `ROLE_FINANCE_OFFICER` | Director of Finance, Accounts Officer | Fiscal Surveillance, Bank Order Settlement | `<FinanceOfficerWorkspace />` |
| `SYSTEM_ADMIN` | `ROLE_SYSTEM_ADMIN` | IT Infrastructure Admin, Platform Engineer | System Governance, Users, Policy Config | `<SystemAdminWorkspace />` |
| `AUDITOR` | `ROLE_AUDITOR` | CAG Inspector, Ministry Vigilance Auditor | Strict Read-Only & Hash-Chain Verification | `<AuditorWorkspace />` |

> **Structural Invariant**:
> - `INSTITUTION_USER` **MUST** have an assigned `institution_id`.
> - All internal regulatory roles (`SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, `FINANCE_OFFICER`, `AUDITOR`) **MUST NOT** have an `institution_id`.

---

## 3. In-Depth Breakdown of Each Role

---

### 1. `INSTITUTION_USER` (External Institutional Tenant)

* **Persona:** Principal, Registrar, or authorized Financial Nodal Officer of an AICTE-affiliated institution.
* **Scope of Access:** **Strictly Single-Tenant (`user.institution_id`)**.
* **Dashboard Cockpit:** `<InstitutionWorkspace />` featuring deposit totals, upcoming maturities, returned instruments alert, and release tracking.

#### What They Have Access To:
* **FDR Registration (Module 1):** Register draft and active FDR certificates for their assigned institution (`POST /instruments`).
* **Document Ingestion (Module 2):** Upload certified PDF scans of FDR certificates and receipt evidence (`POST /instruments/{id}/documents`). Download uploaded documents belonging to their institution.
* **Discrepancy Visibility (Module 3):** View validation run summaries and discrepancy findings detected against their own instruments (`GET /instruments/{id}/findings`).
* **Surveillance & Renewals (Module 5):** Monitor 30/60/90/180-day maturity windows, view lineage trees, draft renewal successors, and link renewing deposits (`POST /instruments/{id}/renew`).
* **Release Applications (Module 6):** Initiate and submit formal FDR release/refund applications with course closure and NOC attachments (`POST /release/requests`).
* **Account Security:** Rotate their own password (`POST /auth/change-password`) and read their institutional inbox notifications (`GET /lifecycle/notifications/inbox`).

#### What They DO NOT Have Access To:
* **Cross-Tenant Access:** Cannot access, view, or download instruments, documents, or cases of any other institution (`403 Forbidden`).
* **Internal Review Queues:** Hidden from Review Queue (`/findings/queue`), Trust Verification Desk (`/verification`), Command Center (`/command-center`), and System User Directory (`/users`).
* **Trust Level Mutation:** Cannot attest or escalate trust levels (L1/L2/L3) or dismiss validation findings.
* **Decision Authority:** Cannot approve, recommend, reject, or record release orders.

---

### 2. `SCRUTINY_OFFICER` (Internal Regulatory Desk Reviewer)

* **Persona:** AICTE Scrutiny Officer conducting desk reviews, discrepancy analysis, and documentary validation.
* **Scope of Access:** Internal regulator across all institutions.
* **Dashboard Cockpit:** `<ScrutinyOfficerWorkspace />` featuring active triage counts, review queue priority breakdown, verification requests, and pending release cases.

#### What They Have Access To:
* **Discrepancy Triage (Module 3):** Full access to the Priority Review Queue (`GET /findings/queue`), assign findings to self, record officer observations (`POST /findings/{id}/observations`), transition finding status (`OPEN -> IN_REVIEW -> RESOLVED/DISMISSED`), and trigger re-evaluations.
* **Return for Correction (Module 3 & 6):** Return deficient instruments or release applications back to institutions with mandatory explanation notes (`POST /instruments/{id}/return-for-correction`).
* **Trigger Validation (Module 3):** Execute on-demand validation rule runs across any instrument (`POST /instruments/{id}/validation-runs`).
* **Trust Level Maker (Module 4):** Attest and record L2 Officer-Verified trust decisions with supporting documentation (`POST /instruments/{id}/trust/l2-officer-decision`).
* **Bank Verification Ingestion (Module 4):** Dispatch verification requests to bank adapters, record manual bank verification certificates, and trigger retries.
* **Release Case Scrutiny (Module 6):** Start review (`POST /release/requests/{id}/start-review`), record review observations, evaluate readiness gates (`POST /release/requests/{id}/evaluate-readiness`), and recommend compliant cases for competent authority approval (`POST /release/requests/{id}/recommend-for-authority`).
* **Oversight & Reports (Module 7):** Access Command Center, Unified Search, and generate Operational Reports (CSV/PDF).

#### What They DO NOT Have Access To:
* **Final Release Approval:** Cannot approve or reject release cases (exclusive to `COMPETENT_AUTHORITY`).
* **Release Order Recording:** Excluded from issuing financial release orders or bank settlement actions.
* **User & Tenant Administration:** Cannot provision users, modify user roles, or onboard institutions.
* **System Policy Configuration:** Cannot edit global validation policy threshold configurations (`SYSTEM_ADMIN` only).

---

### 3. `BRANCH_HEAD` (Regional Director / Senior Regulatory Officer)

* **Persona:** Regional Director or AICTE Branch Head overseeing regional operations, compliance escalations, and scrutiny queues.
* **Scope of Access:** Internal regional/national regulatory oversight.
* **Dashboard Cockpit:** `<BranchHeadWorkspace />` featuring regional queue summaries, high-value release cases, audit chain health, and scheduler diagnostics.

#### What They Have Access To:
* **All Scrutiny Officer Capabilities:** Inherits all operational capabilities of `SCRUTINY_OFFICER` (finding triage, L2 trust attestation, verification dispatch, readiness checks).
* **Policy Lifecycle Approval (Module 5):** Formally approve draft lifecycle and renewal policies (`POST /lifecycle/policies/{id}/approve`).
* **Lineage Correction (Module 5):** Authorize corrections or deactivations of erroneous predecessor-successor lineage edges (`POST /lifecycle/lineage/{id}/correct`).
* **Scheduler Execution (Module 5):** Manually trigger batch maturity scans and evaluate batch instruments (`POST /lifecycle/scheduler/trigger`).
* **Audit Chain Inspection (Module 7):** Full cryptographic verification of the SHA-256 hash ledger (`GET /audit/integrity` and `POST /audit/verify`).
* **Release Order & Bank Confirmation (Module 6):** Confirm bank-side release execution (`POST /release/requests/{id}/confirm-bank-action`) and close completed cases (`POST /release/requests/{id}/close-case`).

#### What They DO NOT Have Access To:
* **Final Release Sanction (Checker):** Cannot grant final statutory approval for deposit release (`COMPETENT_AUTHORITY` exclusive).
* **User Account Provisioning:** Cannot provision or alter IT user accounts.

---

### 4. `COMPETENT_AUTHORITY` (Statutory Sanctioning Official)

* **Persona:** Member Secretary, AICTE Bureau Head, or Chairman of the Executive Committee.
* **Scope of Access:** National portfolio sanctioning and statutory discharge authority.
* **Dashboard Cockpit:** `<CompetentAuthorityWorkspace />` featuring pending sanction cases, readiness gate metrics, statutory audit integrity status, and policy approvals.

#### What They Have Access To:
* **Exclusive Release Sanction (Module 6):** Sole authority empowered to sanction release orders (`POST /release/requests/{id}/approve`).
* **Release Rejection (Module 6):** Reject non-compliant release applications with mandatory statutory rationale (`POST /release/requests/{id}/reject`).
* **Policy Approval (Module 5):** Sanction and approve regulatory lifecycle policies (`POST /lifecycle/policies/{id}/approve`).
* **Readiness Evaluation (Module 6):** Inspect multi-factor release readiness checklists, blocker trees, and gate assessments.
* **Full Inspection Visibility:** View all instruments, documents, verification responses, and audit ledgers nationwide.
* **Cryptographic Verification (Module 7):** Execute audit chain cryptographic integrity scans (`/audit`).

#### What They DO NOT Have Access To:
* **Maker Separation Violation:** Cannot approve a release request if they were the initial submitter or primary desk reviewer (maker-checker separation enforced).
* **Routine Intake:** Does not draft deposit instruments or upload initial certificates.
* **Trust Level Mutation:** Does not perform operational L2 trust attestations.
* **User Management:** Cannot create or manage user credentials.

---

### 5. `FINANCE_OFFICER` (Fiscal Surveillance & Bank Operations)

* **Persona:** AICTE Director of Finance, Chief Accounts Officer, or Bank Reconciliation Specialist.
* **Scope of Access:** Fiscal surveillance, amount reconciliation, and post-sanction banking workflow.
* **Dashboard Cockpit:** `<FinanceOfficerWorkspace />` featuring sanctioned cases awaiting orders, bank execution tracking, cumulative deposit values, and financial compliance metrics.

#### What They Have Access To:
* **Record Release Order (Module 6):** Record official release letters, order numbers, dispatch dates, and bank routing directives (`POST /release/requests/{id}/record-order`).
* **Bank Action Confirmation (Module 6):** Ingest and record bank encashment/refund confirmations (`POST /release/requests/{id}/confirm-bank-action`).
* **Case Closure (Module 6):** Formally close release cases once financial settlement is verified (`POST /release/requests/{id}/close-case`).
* **Fiscal Reports & Analytics (Module 7):** Generate and export comprehensive operational reports, financial liability summaries, and upcoming maturity forecasts in CSV and PDF.
* **Portfolio Read Access:** Inspect instruments, validation findings, verification records, and release dossiers.

#### What They DO NOT Have Access To:
* **Release Approval:** Cannot approve or reject release petitions (exclusive to `COMPETENT_AUTHORITY`).
* **Scrutiny & Review Triage:** Excluded from initial desk reviews, finding resolution, and returning instruments for correction.
* **Trust Attestation:** Cannot grant L2 or L3 trust levels.
* **User Provisioning:** Cannot manage user accounts.

---

### 6. `SYSTEM_ADMIN` (IT Platform Administrator)

* **Persona:** Lead IT Infrastructure Engineer / Security Administrator.
* **Scope of Access:** Complete administrative, technical, and operational configuration authority.
* **Dashboard Cockpit:** `<SystemAdminWorkspace />` featuring system health indicators, account metrics, administrative oversight notification feeds, and policy engines.

#### What They Have Access To:
* **User Provisioning & Access Control:** Create accounts (`POST /auth/users`), update profiles (`PATCH /auth/users/{id}`), toggle active/inactive status (`POST /auth/users/{id}/status`), and execute administrative temporary password resets (`POST /auth/users/{id}/reset-password`).
* **Institution Onboarding:** Register new institutions (`POST /institutions`), update details, and toggle active status (`POST /institutions/{id}/status`).
* **System Policy Management (Module 3 & 5):** Create and update global validation rules and threshold parameters (`POST /validation/policy`), create and activate lifecycle policies (`POST /lifecycle/policies`).
* **Operational Oversight Feed (Module 5):** Access the centralized administrative oversight alert feed (`GET /lifecycle/admin/oversight`).
* **Diagnostic & Clock Controls (Module 5):** Manage background scan schedulers, trigger batch evaluations, retry failed notifications, and manipulate demo clocks in development mode.
* **Cryptographic Ledger Verification (Module 7):** Full verification of the SHA-256 audit ledger (`/audit`).

#### What They DO NOT Have Access To:
* **Regulatory Release Decisions:** Strictly **prohibited** from approving or rejecting release petitions (`POST /release/requests/{id}/approve`, `POST /release/requests/{id}/reject`). Statutory authority cannot be exercised by IT platform administrators.
* **Routine Release-Order Recording:** Strictly **prohibited** from recording official financial release orders (`POST /release/requests/{id}/record-order`). Reserved exclusively for `FINANCE_OFFICER`.
* **Downstream Release Settlement:** Prohibited from confirming bank payouts or closing release cases (`POST /release/requests/{id}/confirm-bank-action`, `/close-case`). Reserved for `FINANCE_OFFICER` and supervisory `BRANCH_HEAD`.
* **Casework Scrutiny Triage:** Excluded from routine desk review triage, start-review transitions, deficiency returns, and recommending cases to the authority.
* **L2 Officer Trust Attestation:** Strictly barred from attesting to physical FDR certificates, wet ink stamps, or seals (`POST /verification/instruments/{id}/trust/l2-officer-decision`).
* **Finding Resolution & Dismissal:** Prohibited from dismissing or resolving discrepancy findings on individual FDRs. Policy tuning is permitted (`POST /validation/policy`), but individual finding adjudication belongs strictly to scrutiny officers.
* **Tampering with Audit Logs:** Absolutely cannot delete, alter, or rewrite records in `audit_events` (hardware/trigger-enforced).
* **Self-Deactivation / Lockout:** Cannot deactivate their own account or remove the final active `SYSTEM_ADMIN` (last-administrator protection).

---

### 7. `AUDITOR` (Independent Statutory Oversight)

* **Persona:** Comptroller and Auditor General (CAG) Inspector, Ministry of Education Vigilance Officer, or Independent Statutory Auditor.
* **Scope of Access:** **Strictly READ-ONLY across all 7 platform modules**.
* **Dashboard Cockpit:** `<AuditorWorkspace />` featuring cryptographic verification controls, sample-size chain re-hashing, compliance checklists, and immutable report exports.

#### What They Have Access To:
* **Cryptographic Hash Chain Verification (Module 7):** Full interactive access to replay and verify the SHA-256 hash-chained audit ledger (`GET /audit/integrity` and `POST /audit/verify`).
* **Complete Audit Trail Querying:** Query all historical audit events with date, actor, role, entity, and action filters (`GET /audit/events`).
* **Full Portfolio Read Inspection:** Read-only access to all institutions, instruments, document versions, validation runs, discrepancy findings, trust transitions, and release cases across all tenants.
* **Operational Reports (Module 7):** Generate and download formal compliance report exports in CSV and PDF formats (`/reports`).
* **System Health Diagnostics:** View system diagnostic telemetry (`/health`).

#### What They DO NOT Have Access To:
* **100% BLOCKED FROM ALL STATE MUTATIONS:** All `POST`, `PUT`, `PATCH`, and `DELETE` requests are rejected by `require_read_only_or_permitted` with `HTTP 403 Forbidden`.
* Cannot register instruments, upload files, modify trust levels, dismiss findings, or record scrutiny notes.

---

## 4. Comprehensive Cross-Module Permission Matrix

### Column Key:
* **SA:** `SYSTEM_ADMIN`
* **SO:** `SCRUTINY_OFFICER`
* **BH:** `BRANCH_HEAD`
* **CA:** `COMPETENT_AUTHORITY`
* **FO:** `FINANCE_OFFICER`
* **IU:** `INSTITUTION_USER`
* **AU:** `AUDITOR`

### Values:
* `Y` = Allowed
* `-` = Denied / Forbidden
* `Y*` = Allowed strictly within user's assigned institution (`user.institution_id`)
* `Y(r)` = Read-Only access permitted

---

### Module 1 — Institutional FDR Registry (`/instruments`)

| Operation / Endpoint | SA | SO | BH | CA | FO | IU | AU | Enforcing Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| List / search instruments (`GET /instruments`) | Y | Y | Y | Y | Y | Y* | Y | Service & query scoping |
| View instrument detail (`GET /instruments/{id}`) | Y | Y | Y | Y | Y | Y* | Y | Service & query scoping |
| View summary metrics (`GET /instruments/summary`) | Y | Y | Y | Y | Y | Y* | Y | Service layer aggregation |
| Register new instrument (`POST /instruments`) | Y | Y | Y | - | - | Y* | - | `service.py:276` |
| Update registry fields (`PATCH /instruments/{id}`) | Y | Y | Y | - | - | Y* | - | `service.py:481` (Draft only for IU) |
| Escalate trust level via registry update | - | - | - | - | - | - | - | **Blocked:** Restrained to Module 4 |

---

### Module 2 — Document Evidence Vault (`/documents`)

| Operation / Endpoint | SA | SO | BH | CA | FO | IU | AU | Enforcing Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| Upload document version (`POST /instruments/{id}/documents`) | Y | Y | Y | - | - | Y* | - | `enforce_institution_scope` + `require_read_only_or_permitted` |
| List documents for instrument (`GET /instruments/{id}/documents`) | Y | Y | Y | Y | Y | Y* | Y | `enforce_institution_scope` |
| Get document metadata (`GET /documents/{id}`) | Y | Y | Y | Y | Y | Y* | Y | `enforce_institution_scope` |
| Download file content (`GET /documents/{id}/versions/{vid}/content`) | Y | Y | Y | Y | Y | Y* | Y | Quarantine / malware guard + scoping |

---

### Module 3 — Validation Engine & Review Queue (`/validation`, `/findings`)

| Operation / Endpoint | SA | SO | BH | CA | FO | IU | AU | Enforcing Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| Trigger validation run (`POST /instruments/{id}/validation-runs`) | Y | Y | Y | Y | - | - | - | `require_roles(SA, SO, BH, CA)` |
| List validation runs (`GET /instruments/{id}/validation-runs`) | Y | Y | Y | Y | Y | Y* | Y | `_enforce_instrument_scope` |
| List findings for instrument (`GET /instruments/{id}/findings`) | Y | Y | Y | Y | Y | Y* | Y | `_enforce_instrument_scope` |
| Access Review Queue (`GET /findings/queue`) | Y | Y | Y | Y | Y | - | Y(r) | Route guard + `ReviewQueuePage` |
| Transition finding status (`POST /findings/{id}/status`) | - | Y | Y | - | - | - | - | `require_roles(SO, BH)` |
| Assign finding (`POST /findings/{id}/assign`) | - | Y | Y | - | - | - | - | `require_roles(SO, BH)` |
| Add review observation note (`POST /findings/{id}/observations`) | - | Y | Y | - | - | - | - | `require_roles(SO, BH)` |
| Return for correction (`POST /instruments/{id}/return-for-correction`) | - | Y | Y | - | - | - | - | `require_roles(SO, BH)` |
| Dismiss finding (`POST /validation/.../dismiss`) | - | Y | Y | - | - | - | - | `require_roles(SO, BH)` |
| List registered validation rules (`GET /validation/rules`) | Y | Y | Y | Y | Y | Y | Y | Authenticated user |
| View active policy configs (`GET /validation/policy`) | Y | Y | Y | - | - | - | Y | `require_roles(SA, SO, BH, AU)` |
| Create / update policy config (`POST /validation/policy`) | Y | - | - | - | - | - | - | **Strictly `require_roles(SA)`** |

---

### Module 4 — Trust, Provenance & Verification (`/verification`)

| Operation / Endpoint | SA | SO | BH | CA | FO | IU | AU | Enforcing Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| View provenance & trust summary (`GET /verification/...`) | Y | Y | Y | Y | Y | Y* | Y | Tenant assertion |
| Generic trust transition (`POST /.../trust/transition`) | Y | Y | Y | - | - | - | - | `trust_service.py` gating |
| L1 document-consistent request (`POST /.../l1-reassessment`) | Y | Y | Y | - | - | - | - | Clean document version required |
| **L2 Officer trust attestation** (`POST /.../l2-officer-decision`) | - | Y | Y | - | - | - | - | Strictly `OFFICER_ROLES (SO, BH)` |
| **L3 Bank confirmation** (`POST /.../l3-bank-confirmation`) | - | Y | Y | - | - | - | - | Policy gate + non-simulated MATCH |
| Trust downgrade / reassessment (`POST /.../trust/downgrade`) | Y | Y | Y | - | - | - | - | Mandatory triggering reason |
| Create verification request (`POST /.../requests`) | - | Y | Y | - | - | - | - | `_assert_officer_access (SO, BH)` |
| Dispatch request to adapter (`POST /requests/{id}/dispatch`) | - | Y | Y | - | - | - | - | `_assert_officer_access (SO, BH)` |
| Record manual bank letter (`POST /requests/{id}/manual-record`) | - | Y | Y | - | - | - | - | `_assert_officer_access (SO, BH)` |
| Retry or cancel request (`POST /requests/{id}/retry|cancel`) | Y | Y | Y | - | - | - | - | `_assert_officer_access` |
| View verification requests & responses | Y | Y | Y | Y | Y | Y* | Y | Scoped query |

---

### Module 5 — Lifecycle Continuity, Renewals & Monitoring (`/lifecycle`, `/monitoring`)

| Operation / Endpoint | SA | SO | BH | CA | FO | IU | AU | Enforcing Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| Create lifecycle policy (`POST /lifecycle/policies`) | Y | - | - | - | - | - | - | `require_roles(SA)` |
| Approve lifecycle policy (`POST /policies/{id}/approve`) | Y | - | Y | Y | - | - | - | `require_roles(SA, CA)` |
| Activate lifecycle policy (`POST /policies/{id}/activate`) | Y | - | - | - | - | - | - | `require_roles(SA)` |
| List / view lifecycle policies (`GET /policies`) | Y | Y | Y | Y | Y | Y | Y | Authenticated user |
| Pre-validate renewal lineage (`POST /lineage/validate`) | Y | Y | Y | - | - | Y* | - | Scoped tenant check |
| Create predecessor-successor renewal (`POST /instruments/{id}/renew`) | Y | Y | Y | - | - | Y* | - | Continuity evaluation |
| View lineage tree & continuity (`GET /instruments/{id}/lineage`) | Y | Y | Y | Y | Y | Y* | Y | Scoped tenant check |
| Correct / deactivate lineage link (`POST /lineage/{id}/correct`) | Y | Y | Y | - | - | - | - | `require_roles(SA, SO, BH)` |
| Trigger on-demand evaluation (`POST /lifecycle/evaluate`) | Y | Y | Y | Y | Y | Y* | Y | Scoped tenant check |
| Trigger batch evaluation (`POST /lifecycle/batch-evaluate`) | Y | Y | Y | - | - | - | - | `require_roles(SA, SO, BH)` |
| Monitoring lists (approaching, matured, overdue) | Y | Y | Y | Y | Y | Y* | Y | Scoped tenant check |
| Trigger scheduler scan job (`POST /scheduler/trigger`) | Y | Y | Y | - | - | - | - | `require_roles(SA, SO, BH)` |
| View scheduler run logs (`GET /scheduler/runs`) | Y | Y | Y | - | - | - | - | `require_roles(SA, SO, BH)` |
| Admin oversight feed (`GET /lifecycle/admin/oversight`) | Y | - | - | - | - | - | - | `require_roles(SA)` |
| Advance / reset demo clock (`POST /demo/advance|reset-clock`) | Y | Y* | - | - | - | - | - | Development mode only |

---

### Module 6 — Release & Refund Case Management (`/release`)

| Operation / Endpoint | SA | SO | BH | CA | FO | IU | AU | Enforcing Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| Create draft release request (`POST /release/requests`) | Y | - | - | - | - | Y* | - | Institutional intake |
| List / view release requests (`GET /release/requests`) | Y | Y | Y | Y | Y | Y* | Y | Scoped tenant check |
| Add review observation note (`POST /requests/{id}/observations`) | Y | Y | Y | Y | - | - | - | `require_roles(SA, SO, BH, CA)` |
| Start scrutiny review (`POST /requests/{id}/start-review`) | - | Y | Y | - | - | - | - | `require_roles(SO, BH)` |
| Return for correction (`POST /requests/{id}/return-for-correction`) | - | Y | Y | - | - | - | - | `require_roles(SO, BH)` |
| Recommend for authority (`POST /requests/{id}/recommend-for-authority`) | - | Y | Y | - | - | - | - | `require_roles(SO, BH)` |
| Evaluate readiness snapshot (`POST /requests/{id}/evaluate-readiness`) | Y | Y | Y | Y | - | - | - | `require_roles(SA, SO, BH, CA)` |
| Check release gate (`POST /requests/{id}/check-gate`) | Y | Y | Y | Y | - | - | - | `require_roles(SA, SO, BH, CA)` |
| **Approve release request** (`POST /requests/{id}/approve`) | - | - | - | **Y** | - | - | - | **Strictly `require_roles(CA)` + 4-Eye Gate** |
| Reject release request (`POST /requests/{id}/reject`) | - | - | - | **Y** | - | - | - | **Strictly `require_roles(CA)`** |
| **Record release order** (`POST /requests/{id}/record-order`) | - | - | - | - | **Y** | - | - | **Strictly `require_roles(FO)`** |
| **Confirm bank action** (`POST /requests/{id}/confirm-bank-action`) | - | - | Y | - | Y | - | - | `require_roles(FO, BH)` |
| **Close release case** (`POST /requests/{id}/close-case`) | - | - | Y | - | Y | - | - | `require_roles(FO, BH)` |

> **Statutory Invariant (Module 6 Approval)**:
> - Even `SYSTEM_ADMIN` is barred from approving release requests (`POST /release/requests/{id}/approve`).
> - The final sanction is reserved **exclusively** for `COMPETENT_AUTHORITY`.
> - The service layer enforces Maker-Checker separation: `current_user != requester` AND `current_user != primary_reviewer`.

---

### Module 7 — Command Center, Reports & Audit Ledger (`/dashboard`, `/reports`, `/audit`)

| Operation / Endpoint | SA | SO | BH | CA | FO | IU | AU | Enforcing Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| Command Center Cockpit (`GET /dashboard/command-center`) | Y | Y | Y | Y | - | - | - | `ProtectedRoute` allowedRoles |
| Dashboard Overview (`GET /dashboard`) | Y | Y | Y | Y | Y | Y* | Y | Dedicated workspace per role |
| Unified Search (`GET /dashboard/search`) | Y | Y | Y | Y | Y | Y* | Y | Scoped tenant results |
| Create scrutiny observation (`POST /dashboard/.../observations`) | Y | Y | Y | Y | Y | - | - | Non-auditor internal staff |
| Resolve scrutiny observation (`POST /observations/{id}/resolve`) | Y | Y | Y | Y | - | - | - | `require_roles(SA, SO, BH, CA)` |
| Amend scrutiny observation (`POST /observations/{id}/amend`) | Y | Y | Y | Y | Y | - | - | Non-auditor internal staff |
| Operational Reports (Pending, Maturities, Missing, Interventions) | Y | Y | Y | Y | Y | Y* | Y | Scoped query |
| Export Reports (CSV / PDF) (`/reports/.../export/...`) | Y | Y | Y | Y | Y | Y* | Y | `ExportService.verify_export_permission` |
| Query Audit Ledger (`GET /audit/events`) | Y | Y | Y | Y | Y | Y*(own) | Y | Row-level tenant filter |
| **Cryptographic Hash Chain Verification** (`POST /audit/verify`) | **Y** | - | **Y** | **Y** | - | - | **Y** | `require_roles(SA, AU, BH, CA)` |

---

### System Administration & User Provisioning (`/auth/users`, `/institutions`, `/health`)

| Operation / Endpoint | SA | SO | BH | CA | FO | IU | AU | Enforcing Boundary |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| List application user accounts (`GET /auth/users`) | **Y** | - | - | - | - | - | - | `require_roles(SA)` |
| Provision new user (`POST /auth/users`) | **Y** | - | - | - | - | - | - | `require_roles(SA)` |
| Update user profile / role (`PATCH /auth/users/{id}`) | **Y** | - | - | - | - | - | - | `require_roles(SA)` |
| Toggle user active status (`POST /auth/users/{id}/status`) | **Y** | - | - | - | - | - | - | `require_roles(SA)` + Last-Admin Guard |
| Administrative password reset (`POST /auth/users/{id}/reset-password`) | **Y** | - | - | - | - | - | - | `require_roles(SA)` |
| Register new institution (`POST /institutions`) | **Y** | - | - | - | - | - | - | `require_roles(SA)` |
| Update institution profile (`PATCH /institutions/{id}`) | **Y** | - | - | - | - | - | - | `require_roles(SA)` |
| Toggle institution status (`POST /institutions/{id}/status`) | **Y** | - | - | - | - | - | - | `require_roles(SA)` |
| System Diagnostics (`GET /health`) | Y | Y | - | - | - | - | Y | Route guard (`SA, SO, AU`) |

---

## 5. Frontend Navigation, Workspaces & Route Guard Reference

The user interface dynamically tailors navigation links, workspace views, action buttons, and live badge counters according to the authenticated user's role:

### 5.1 Route Guard Matrix (`frontend/src/app/router.tsx`)

| Path | Allowed Roles | Default Gating Behavior |
|---|---|---|
| `/dashboard` | All authenticated roles | Dynamically mounts role-specific workspace |
| `/command-center` | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY` | Redirects to `/dashboard` if unauthorized |
| `/search` | All authenticated roles | Scoped tenant results |
| `/instruments` | All authenticated roles | Scoped tenant results |
| `/documents` | All authenticated roles | Scoped tenant results |
| `/monitoring` | All authenticated roles | Scoped tenant results |
| `/release` | All authenticated roles | Scoped tenant results |
| `/findings/queue` | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, `FINANCE_OFFICER`, `AUDITOR` | Hidden from `INSTITUTION_USER` |
| `/verification` | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, `FINANCE_OFFICER`, `AUDITOR` | Hidden from `INSTITUTION_USER` |
| `/institutions` | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, `FINANCE_OFFICER`, `AUDITOR` | Hidden from `INSTITUTION_USER` |
| `/reports` | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, `FINANCE_OFFICER`, `AUDITOR` | Hidden from `INSTITUTION_USER` |
| `/audit` | `SYSTEM_ADMIN`, `AUDITOR`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY` | Accessible to oversight & admin roles |
| `/users` | `SYSTEM_ADMIN` | Accessible to platform administrator only |
| `/health` | `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDITOR` | Technical diagnostic console |
| `/change-password` | All authenticated roles | Self-service credential rotation |

---

### 5.2 Sidebar Navigation Structure (`Sidebar.tsx`)

The navigation menu organizes destinations into four logical groups with permission filtering:

1. **Workspace:**
   - `Overview` (`/dashboard`): Visible to all roles.
   - `Command Center` (`/command-center`): Restricted to internal regulatory officers (`SA`, `SO`, `BH`, `CA`).
2. **FDR Lifecycle:**
   - `Institutions & Instruments` (`/instruments`): Visible to all roles.
   - `Documents & Evidence` (`/documents`): Visible to all roles.
   - `Validation & Review Queue` (`/findings/queue`): Internal regulatory & audit roles (`SA`, `SO`, `BH`, `CA`, `FO`, `AU`).
   - `Trust & Verification` (`/verification`): Internal regulatory & audit roles (`SA`, `SO`, `BH`, `CA`, `FO`, `AU`).
   - `Monitoring & Renewals` (`/monitoring`): Visible to all roles.
   - `Release / Refund Cases` (`/release`): Visible to all roles.
3. **Intelligence & Oversight:**
   - `Unified Search` (`/search`): Visible to all roles.
   - `Operational Reports` (`/reports`): Internal regulatory & audit roles.
   - `Audit & Integrity` (`/audit`): Exclusively visible to `SYSTEM_ADMIN`, `AUDITOR`, `BRANCH_HEAD`, and `COMPETENT_AUTHORITY`.
4. **System:**
   - `Institution Directory` (`/institutions`): Internal regulatory & audit roles.
   - `Users & Access` (`/users`): Exclusively visible to `SYSTEM_ADMIN`.
   - `Password Security` (`/change-password`): Visible to all roles.
   - `System Diagnostics` (`/health`): Visible to `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDITOR`.

---

### 5.3 UI Control Invariants & Action Button Omission

To prevent unauthorized interactions and confusion:
1. **Omission Rather Than Disabling:**
   Action buttons requiring privileged roles (e.g., "Sanction Release", "Record Release Order", "Attest L2 Trust", "Return for Correction") are omitted from the DOM entirely when the current user's role is not authorized.
2. **Auditor Notice Banner:**
   When an `AUDITOR` logs in, an informational amber banner alerts the user:
   > *"Statutory Audit Session: Platform is operating in strict read-only inspection mode. State-changing actions and submissions are disabled."*
3. **Badge Counter Scoping:**
   Live badge counters (`reviewQueueCount`, `verificationQueueCount`) only execute backend requests when the user holds an internal regulatory role, avoiding unnecessary requests for institutional users.

---

## 6. Security Invariants & Cross-Cutting Controls

### 6.1 Cryptographic Password Security
- Passwords are hash-encoded using memory-hard **Argon2id** (`time_cost=2`, `memory_cost=65536` [64 MB], `parallelism=2`, `hash_len=32`).
- Plaintext passwords or secrets are never logged in audit trails, request headers, or database records.

### 6.2 CSRF Protection & Origin Validation
- All state-changing HTTP requests (`POST`, `PUT`, `PATCH`, `DELETE`) pass through `verify_csrf_origin(...)`.
- The `Origin` and `Referer` headers are validated against configured CORS whitelists (`CORS_ORIGINS`).

### 6.3 Last-Administrator Lockout Defense
- An administrator cannot deactivate their own active session.
- An administrator cannot deactivate or change the role of the last active `SYSTEM_ADMIN` in the database, preventing accidental complete administrative lockout.

### 6.4 Cryptographic Verification Chain Specification
- Each audit log entry is chained using:
  $$\text{current\_hash} = \text{SHA256}(\text{previous\_hash} \parallel \text{sequence\_number} \parallel \text{canonical\_json\_payload})$$
- The genesis entry is anchored at `GENESIS_HASH` (`"0" * 64`).
- Any modification, deletion, or out-of-order insertion breaks the hash link of subsequent records, immediately alerting auditors during `/audit/verify` execution.

---

## 7. Verification & Compliance Checklist

- [x] **Zero Client-Side Reliance:** All authorization decisions are strictly enforced by backend FastAPI dependencies (`require_roles`, `require_read_only_or_permitted`, `enforce_institution_scope`).
- [x] **Hardware & Query Tenant Scoping:** SQL statements for `INSTITUTION_USER` consistently inject `where(Instrument.institution_id == user.institution_id)`.
- [x] **Maker-Checker Regulatory Gate:** Approving deposit releases is strictly isolated to `COMPETENT_AUTHORITY`, barring even `SYSTEM_ADMIN` from administrative override.
- [x] **Tamper-Evident Ledger:** Append-only database triggers protect `audit_events` from `UPDATE` or `DELETE` statements.
- [x] **Comprehensive Test Suite:** All backend tests (unit, integration, and security RBAC boundary tests) and frontend Vitest guard suites execute with 100% pass rate.

---

*SakshyaTrail Regulatory Access Control Architecture — Verified and Approved for AICTE Compliance.*
