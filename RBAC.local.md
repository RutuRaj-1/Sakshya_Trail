# SakshyaTrail — Comprehensive RBAC & Security Architecture Specification

This document provides an end-to-end specification of the **7 Role-Based Access Control (RBAC)** structures implemented in **SakshyaTrail** (SIH Problem Statement ID: 26265). It defines the exact capabilities, regulatory boundaries, tenant scopes, state-machine transitions, and audit accountabilities for every role in the platform.

---

## 1. Architectural Foundations of SakshyaTrail RBAC

The authorization model is built upon four fundamental security invariants:

1. **Deny-by-Default Execution:** Every API endpoint requires an authenticated JWT session (`HttpOnly` cookie or `Bearer` token) and explicitly declares permitted roles using FastAPI's `require_roles(...)` dependency.
2. **Multi-Tenant Boundary Isolation:** Tenant boundaries are strictly hardware-enforced at the database query layer. An `INSTITUTION_USER` is cryptographically and logically bound to their `institution_id` and can never query, mutate, or view another institution's instruments, documents, or cases.
3. **Strict Maker-Checker Separation (4-Eye Principle):** Regulatory actions—specifically **Release of Security Deposits** and **L2 Officer Trust Attestations**—enforce separation of duties. The officer who reviews findings and prepares the release readiness assessment (Maker) cannot be the same authority who sanctions the final discharge order (Checker).
4. **Append-Only Cryptographic Audit Invariance:** No role—including `SYSTEM_ADMIN`—can bypass, alter, rewrite, or delete events in the **SHA-256 sequential hash-chained audit ledger** (`audit_events`). Any manual database tampering breaks the cryptographic verification chain.

---

## 2. Overview of the 7 Application Roles

| Role Identifier | Role Category | Real-World Persona | Primary Jurisdiction |
|---|---|---|---|
| `INSTITUTION_USER` | External Tenant | College Principal / Registrar / Finance Head | Single Institution (Assigned `institution_id`) |
| `SCRUTINY_OFFICER` | Internal Regulator | AICTE Scrutiny Officer / Desk Reviewer | Desk Review, Findings Triage, L2 Trust Maker |
| `BRANCH_HEAD` | Internal Regulator | Regional Officer / Regional Director (WRO, SRO, etc.) | Regional Jurisdiction (Assigned Regional Office) |
| `COMPETENT_AUTHORITY` | Internal Regulator | Member Secretary / Bureau Head / Executive Committee | National Portfolio, Final Release Sanctions (Checker) |
| `FINANCE_OFFICER` | Internal Regulator | Director of Finance / Accounts Officer | Fiscal Surveillance, Amount Reconciliation, Refund Lineage |
| `SYSTEM_ADMIN` | Internal Governance | IT Infrastructure Admin / Platform Administrator | User Provisioning, System Health, Policy Config |
| `AUDITOR` | Independent Oversight| CAG Auditor / Independent Statutory Inspector | Read-Only Across All Modules & Hash-Chain Verification |

---

## 3. In-Depth Breakdown of Each Role

---

### 1. `INSTITUTION_USER` (External Institutional Tenant)

* **Real-World Persona:** College Principal, Registrar, or authorized Institutional Administrator submitting security deposits to satisfy statutory approval requirements.
* **Scope of Access:** **Strictly Single-Tenant (`user.institution_id`)**.

#### What They Control:
* **Deposit Intake & Registration (Module 1):** Can draft and register new Fixed Deposit Receipts (FDRs) referencing bank branch, term dates, and lien marking details for their assigned institution.
* **Certified Document Intake (Module 2):** Can upload certified PDF certificate scans and evidence receipts to the Evidence Vault. The system automatically computes deterministic SHA-256 byte digests and executes malware validation on upload.
* **Institutional Surveillance (Module 5):** Can monitor upcoming maturities (30/60/90/180-day calendar windows) and view renewal lineage for their own instruments.
* **Successor Renewal Drafting (Module 5):** Can initiate draft successor renewals that link to maturing predecessor deposits without breaking historical lineage.
* **Release Petitions (Module 6):** Can submit initial petitions for FDR release or refund with justification and course closure documentation.
* **Account Security:** Can change their own password and view their institution profile.

#### What They DO NOT Control:
* **Cannot View Other Institutions:** Strict SQL filter `where(Instrument.institution_id == user.institution_id)` blocks cross-institution data leakage.
* **Cannot Access Regulatory Desks:** Forbidden from accessing the Validation Review Queue (`/findings/queue`), Trust Desk (`/verification`), Operational Reports (`/reports`), Audit Ledger (`/audit`), and System Users (`/users`).
* **Cannot Self-Attest Trust Levels:** Cannot upgrade trust from `L0_DECLARED` to `L1`, `L2`, or `L3`. Trust upgrades are reserved exclusively for deterministic document match algorithms, human scrutiny officers, and bank confirmation responses.
* **Cannot Resolve Regulatory Findings:** Cannot dismiss or clear automated discrepancy findings flagged against their submission.
* **Cannot Approve Releases:** Cannot modify checklist readiness statuses or sanction their own release petitions.

---

### 2. `SCRUTINY_OFFICER` (Regulatory Reviewer / Maker)

* **Real-World Persona:** AICTE Technical Scrutiny Officer tasked with verifying institutional compliance, examining uploaded certificate scans, and investigating automated rule discrepancies.
* **Scope of Access:** Internal Regulatory (Multi-tenant read/write within regulatory workflows).

#### What They Control:
* **Validation Review Queue Triage (Module 3):** Full authority to inspect algorithmic discrepancy findings across date orders, amount thresholds, missing statutory lien notations, and duplicate certificate numbers.
* **Finding Investigation & Resolution:** Can transition findings between `OPEN`, `INVESTIGATING`, and `RESOLVED` with mandatory written explanatory rationales.
* **L2 Officer Trust Attestation (Module 4):** Authorized to upgrade an instrument to **L2 (`OFFICER_VERIFIED`)** after verifying document validity and recording formal attestation remarks in `TrustTransitionHistory`.
* **Bank Verification Ingestion (Module 4):** Can initiate manual bank confirmation requests and log offline banker communication references.
* **Readiness Assessment (Module 6 - Maker):** Can execute pre-release checklist assessments, evaluating whether no-dues, legal holds, or unresolved findings block the deposit.
* **Successor Instrument Scrutiny (Module 5):** Reviews renewal graph lineage to verify that successor instruments maintain unbroken continuous lien coverage.

#### What They DO NOT Control:
* **Cannot Sanction Final Release (Maker-Checker Boundary):** Strictly forbidden from executing the final `SANCTION_RELEASE` or `AUTHORIZE_DISCHARGE` action in Module 6. The reviewer who evaluates readiness cannot approve the discharge order.
* **Cannot Produce Production L3 Trust:** Cannot manually force an instrument to `L3_BANK_CONFIRMED` without an authenticated host-to-host or authenticated source bank reply. Simulated bank adapters are automatically flagged and cannot establish statutory L3.
* **Cannot Create or Deactivate Users:** User management is restricted to `SYSTEM_ADMIN`.
* **Cannot Alter Platform Validation Rules:** Cannot edit engine rules or policy parameters.

---

### 3. `BRANCH_HEAD` (Regional Director / Supervisory Officer)

* **Real-World Persona:** Regional Office Director (e.g., Western Regional Office - WRO, Southern Regional Office - SRO) responsible for regional institutional compliance, supervisory oversight, and escalated discrepancy management.
* **Scope of Access:** Regional Jurisdiction & Supervisory Oversight.

#### What They Control:
* **Regional Escalation Desk (Module 3 & Command Center):** Reviews and adjudicates findings escalated past officer SLA thresholds (e.g., uncorrected discrepancies > 14 days).
* **Supervisory Trust Attestation (Module 4):** Can attest L2 trust levels and verify high-value deposits that exceed standard scrutiny officer thresholds.
* **Regional Readiness Gate Adjudication (Module 6):** Can evaluate release readiness for regional institutions and issue supervisory endorsements.
* **Delegated Release Approval (Module 6 - Checker):** In defined administrative structures, can execute final release sanctions for institutions under their regional jurisdiction, provided they did not act as the initial Scrutiny Officer (Maker).
* **Cryptographic Audit Ledger Inspection (Module 7):** Full read access to inspect the SHA-256 hash-chained audit log and verify regional activity integrity.
* **Regional Operational Reports:** Can generate and download compliance and maturity load reports filtered by regional office code.

#### What They DO NOT Control:
* **Cannot Bypass Release Gate Blockers:** If mandatory legal hold or missing document blockers are active, the system mechanically prevents the Branch Head from executing an approval.
* **Cannot Mutate Historical Audit Records:** Audit events are immutable; cannot alter logs of previous decisions.
* **Cannot Manage Cross-Regional Users:** Cannot modify admin users outside designated administrative delegation.

---

### 4. `COMPETENT_AUTHORITY` (Bureau Head / Final Sanction Authority)

* **Real-World Persona:** Member Secretary, Council Executive, or Bureau Approval Committee possessing apex statutory authority for financial discharge and regulatory closures.
* **Scope of Access:** Apex National Regulatory Authority (Checker).

#### What They Control:
* **Apex Release Sanction (Module 6 - Checker):** The primary authority permitted to approve `SANCTION_RELEASE` and sign off on statutory FDR refund/release orders.
* **Discharge Order Authorization:** Formally transitions instruments from `READY_FOR_AUTHORITY` to `RELEASED`, generating official tamper-evident discharge orders.
* **Legal Hold Adjudication:** Can formally register, review, or lift statutory/court legal holds against security deposits.
* **Executive Command Center Oversight:** Full national visibility into portfolio values, high-risk institutions, maturity clusters, and systemic compliance bottlenecks.
* **Audit Chain Integrity Verification:** Can inspect audit ledger health and verify cryptographic hash chains across all national regions.

#### What They DO NOT Control:
* **Cannot Violate Maker-Checker Segregation:** Cannot act as Checker for a case where they themselves initiated or prepared the initial scrutiny checklist.
* **Cannot Overrule Algorithmic Zero-Blockers:** Even apex authority cannot force a release through the software if hard blockers (e.g. unresolved fraud findings, active injunctions) evaluate to `BLOCKED`. The blocker must first be resolved through formal statutory procedures.
* **Cannot Rewrite Hash Chained Ledger:** Subject to the same tamper-evident cryptographic constraints as all other users.

---

### 5. `FINANCE_OFFICER` (Financial Surveillance & Fiscal Governance)

* **Real-World Persona:** Director of Finance, Chief Accounts Officer, or Fiscal Reconciler responsible for AICTE's multi-crore deposit security portfolio.
* **Scope of Access:** Internal Fiscal & Portfolio Financial Governance.

#### What They Control:
* **Deposit Value Reconciliation (Module 1 & 5):** Verifies that FDR certificate amounts reconcile against approved institutional intake norms and bank guarantee standards.
* **Maturity Load Surveillance (Command Center & Module 5):** Analyzes month-wise and quarterly maturity load curves (`MaturityLoadChart`) to anticipate institutional renewal cycles and liquidity requirements.
* **Lineage Financial Integrity (Module 5):** Verifies that renewal chains accurately track principal rollover versus interest disbursement, flagging improper capital deductions.
* **Fiscal Checklist Verification (Module 6):** Validates bank account details, IFSC codes, refund payee particulars, and penalty deduction calculations during release reviews.
* **Financial Reporting & Ledger Reconciliation (Module 7):** Generates financial compliance summaries, bank-wise deposit concentrations, and maturity forecasting reports.

#### What They DO NOT Control:
* **Cannot Grant Statutory Approvals:** Cannot approve or issue AICTE institutional recognition or academic approvals.
* **Cannot Unilaterally Grant L2 Trust:** Cannot attest to document authenticity without concurrence from the Scrutiny Officer.
* **Cannot Execute Release Orders:** Release authorization is strictly reserved for `COMPETENT_AUTHORITY` / `BRANCH_HEAD`.
* **Cannot Create User Accounts:** No platform user provisioning rights.

---

### 6. `SYSTEM_ADMIN` (Platform Administrator & Superuser)

* **Real-World Persona:** AICTE National Informatics Center (NIC) / IT Infrastructure Lead managing user identity, regional tenant mappings, system liveness, and configuration.
* **Scope of Access:** Global Platform Administration & Configuration.

#### What They Control:
* **User Management & Provisioning (Module 7):** Can create, update, activate, and deactivate user accounts across all 7 roles (`/users`), and enforce mandatory password rotation.
* **Institution Onboarding & Directory:** Can onboard institutions, assign unique AICTE permanent IDs, and bind institutions to their designated Regional Offices (`/institutions`).
* **Platform Health Diagnostics:** Accesses system health metrics, database latency monitors, and API liveness endpoints (`/health`).
* **Policy Configuration:** Can configure release checklist profiles, validation policy rules, and system-wide threshold parameters.
* **Emergency Maintenance:** Full read/write operational capability for system recovery and administrative correction.

#### What They DO NOT Control:
* **Cannot Mutate Audit Hash Chain:** Invariant cryptographic rule: `audit_events` rows are immutable. A database administrator or System Admin updating rows will alter the hash, causing `verifyChain()` to immediately fail on integrity checks.
* **Cannot Bypass Bank Ingestion Authentication:** Cannot use synthetic simulated responses to produce an authentic statutory `L3_BANK_CONFIRMED` record in a production environment.
* **Cannot Bypass Multi-Factor Auditing:** Every administrative action performed by `SYSTEM_ADMIN` is automatically recorded into the hash chain with their user ID, IP address, and previous hash link.

---

### 7. `AUDITOR` (Independent Statutory Inspector / CAG)

* **Real-World Persona:** Comptroller and Auditor General (CAG) Inspector, Ministry of Education Vigilance Officer, or Independent Statutory Auditor.
* **Scope of Access:** **Strictly READ-ONLY across all 7 Modules**.

#### What They Control:
* **Cryptographic Hash Chain Inspection (Module 7):** Full read access to the append-only audit ledger (`/audit`).
* **Interactive Chain Verification Tool:** Can run the mathematical verification tool `auditApi.verifyChain({ sample_size: N })` to independently compute and assert that every block in the SHA-256 chain is unblemished and unbroken.
* **Full Portfolio Read Access:** Can inspect every institution, instrument, document digest, scrutiny finding, trust transition, renewal tree, and release petition.
* **Operational & Analytical Reports (`/reports`):** Can generate and download comprehensive audit trail exports and compliance analytics.

#### What They DO NOT Control:
* **100% BLOCKED FROM ALL STATE-CHANGING ENDPOINTS:** The backend dependency `require_read_only_or_permitted` in [dependencies.py](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/backend/app/modules/auth/dependencies.py) explicitly intercepts and rejects all `POST`, `PUT`, `PATCH`, and `DELETE` requests from `AUDITOR` with `HTTP 403 Forbidden`.
* **Cannot Register Instruments, Upload Files, or Add Notes.**
* **Cannot Modify Trust Levels, Findings, or Decisions.**

---

## 4. Comprehensive Cross-Module Permission Matrix

The following matrix documents the exact permissions across the platform's seven functional modules:

| Functional Capability | `INSTITUTION_USER` | `SCRUTINY_OFFICER` | `BRANCH_HEAD` | `COMPETENT_AUTHORITY` | `FINANCE_OFFICER` | `SYSTEM_ADMIN` | `AUDITOR` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **M1: Register Draft FDR** |  (Own Inst) |  |  |  |  |  |  (Read Only) |
| **M1: View FDR Registry** |  (Own Inst) |  (All) |  (Regional/All) |  (All) |  (All) |  (All) |  (All) |
| **M2: Upload Evidence Scan** |  (Own Inst) |  |  |  |  |  |  |
| **M2: View Evidence & SHA-256** |  (Own Inst) |  |  |  |  |  |  |
| **M3: View Discrepancy Findings** |  |  |  |  |  |  |  |
| **M3: Resolve / Update Finding** |  |  |  |  |  |  |  |
| **M4: Attest L2 Trust Level** |  |  |  |  |  |  |  |
| **M4: Bank Verification Ingestion** |  |  |  |  |  |  |  (Read Only) |
| **M5: Surveillance Windows** |  (Own Inst) |  |  |  |  |  |  |
| **M5: Create Successor Renewal** |  (Own Inst) |  |  |  |  |  |  |
| **M6: Submit Release Petition** |  (Own Inst) |  |  |  |  |  |  |
| **M6: Evaluate Readiness Gate** |  |  (Maker) |  |  |  (Financial) |  |  (Read Only) |
| **M6: Sanction Release Order** |  |  |  (Regional) |  (Checker) |  |  |  |
| **M7: Inspect Hash-Chain Ledger** |  |  |  |  |  |  |  |
| **M7: Run Chain Verify Tool** |  |  |  |  |  |  |  |
| **M7: Export Formal Reports** |  |  |  |  |  |  |  |
| **System: User Provisioning** |  |  |  |  |  |  |  |
| **System: Institution Onboarding** |  |  |  |  |  |  |  |

---

## 5. Frontend Navigation & UI Enforcement

The user interface dynamically adapts based on the active role authenticated in [AuthContext.tsx](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/frontend/src/features/auth/AuthContext.tsx):

1. **Collapsible Navigation Groups ([Sidebar.tsx](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/frontend/src/components/navigation/Sidebar.tsx)):**
   * **Workspace Group:** Overview (`/dashboard`) and Command Center (`/command-center`) are visible to all authenticated roles. For `INSTITUTION_USER`, metrics are strictly filtered to their college's records.
   * **FDR Lifecycle Group:**
     * `Validation & Review Queue` and `Trust & Verification` are hidden for `INSTITUTION_USER`.
     * Live badge counters (`reviewQueueCount`, `verificationQueueCount`) only query backend APIs for internal roles.
   * **Intelligence & Oversight Group:**
     * `Operational Reports` is accessible to internal regulatory staff and auditors.
     * `Audit & Integrity` (`/audit`) is exclusively visible to `SYSTEM_ADMIN`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, and `AUDITOR`.
   * **System Group:**
     * `Users & Access` (`/users`) is rendered only for `SYSTEM_ADMIN`.
2. **Action Buttons & Form Controls:**
   * Action buttons (e.g., "Sanction Release", "Resolve Finding", "Attest L2") evaluate `user.role` before rendering. If unauthorized, buttons are omitted rather than simply disabled.
3. **Audit Notice Banners:**
   * When an `AUDITOR` logs in, an informational banner reminds the user: *"Statutory Audit Session: Platform is operating in strict read-only inspection mode."*

---

## 6. Verification and Compliance Checklist

* [x] **Zero Hardcoded Bypass:** Role checks are never evaluated via client-side booleans alone; every FastAPI router applies `require_roles(...)`.
* [x] **Tenant Scoping:** SQL statements for `INSTITUTION_USER` consistently inject `where(Instrument.institution_id == user.institution_id)`.
* [x] **Argon2id Passwords:** Password hashes use memory-hard Argon2id (`time_cost=2`, `memory_cost=65536`).
* [x] **Cryptographic Audit Invariance:** All state-changing transitions invoke `log_audit_event(...)` to compute sequential SHA-256 hashes linking back to `GENESIS_HASH`.
* [x] **476 Pytest Tests:** 100% of backend tests pass, explicitly testing RBAC boundaries, forbidden transitions, and tenant isolation.
