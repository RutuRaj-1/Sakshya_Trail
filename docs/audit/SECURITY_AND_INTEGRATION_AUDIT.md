# SECURITY, PRIVACY & INTEGRATION AUDIT
## Project: SakshyaTrail — Security Deposit / FDR Lifecycle Integrity Platform
**SIH Problem Statement:** 26265  
**Baseline Date:** 2026-10-28  
**Audit Evaluator:** Antigravity Autonomous Audit Engine  
**Repository Branch / Commit:** `main` @ `7f1fab86523f63d8c02912403fdf0f7281c2c073`  

---

## 1. Role-Based Access Control (RBAC) Matrix

The system implements 7 strictly separated regulatory and operational roles:

| API Domain / Capability | ADMIN | AICTE_ADMIN | AICTE_OFFICER | AICTE_VERIFIER | INSTITUTION_USER | FINANCE_OFFICER | AUDITOR |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **User & Tenant Provisioning** | **RW** | R | - | - | - | - | R |
| **Institutional Profiles** | **RW** | **RW** | **RW** | R | R (Own Tenant) | R | R |
| **FDR Deposit Creation** | - | - | - | - | **RW (Draft/Submit)**| - | - |
| **Document Upload & Versioning** | - | - | **RW (Notes)** | - | **RW (Own FDRs)** | - | - |
| **Document Download & Preview** | **R** | **R** | **R** | **R** | **R (Own FDRs)** | **R** | **R** |
| **OCR Finding Resolution** | **RW** | **RW** | **RW** | **RW** | - | - | R |
| **Bank Verification Dispatch** | - | **RW** | **RW** | - | - | - | R |
| **Stage Progression (Approve)** | - | **RW** | **RW** | - | - | - | R |
| **Release Recommendation (Maker)**| - | - | **RW** | - | - | - | R |
| **Release Approval (Checker)** | - | **RW** | - | - | - | - | R |
| **Claim Forfeiture Execution** | - | **RW** | - | - | - | - | R |
| **Audit Trail Inspection** | **R** | **R** | **R** | **R** | - | **R** | **R (Full)**|
| **Audit Chain Verification** | **RW** | **RW** | - | - | - | - | **RW** |

*Legend: RW = Read-Write (Mutation permitted), R = Read-Only, - = Explicitly Denied (HTTP 403 Forbidden).*

---

## 2. Multi-Tenant Data Isolation Audit

### Threat Model: Cross-Tenant Data Leakage
- **Mechanism:** In institutional operations, all queries for FDR instruments, documents, and notifications are filtered using the current session's `institution_id`.
- **Implementation:** Evaluated in `app/modules/institutions/dependencies.py` via `get_current_tenant_id()`.
- **Inspection Finding:**
  - Standard user endpoints strictly inject `filter(FDRInstrument.institution_id == current_user.institution_id)`.
  - Admin/AICTE endpoints require administrative privilege overrides to access cross-institution records.
  - Test suites confirm that an authenticated user from College A requesting an FDR owned by College B receives `HTTP 403 Forbidden` or `HTTP 404 Not Found`.

---

## 3. Cryptographic Audit Immutability & Hash Chaining

### Architectural Guarantee
Every state mutation event is converted to a canonical JSON string and hashed using SHA-256.
$$\text{EventHash}_n = \text{SHA-256}(\text{Index}_n \mathbin{\Vert} \text{PreviousHash}_{n-1} \mathbin{\Vert} \text{Timestamp}_n \mathbin{\Vert} \text{EventType}_n \mathbin{\Vert} \text{ActorID}_n \mathbin{\Vert} \text{PayloadHash}_n)$$

### Security Review Findings:
1. **Append-Only Enforcement:** Database routers do not expose `DELETE` or `PUT` endpoints on the `audit_events` table.
2. **Tamper Detection Tested:** Running the automated tamper diagnostic modifies an arbitrary row in the test SQLite database; the mathematical validator immediately flags the broken index and halts trust validation.
3. **Actor Attribution:** Every audit entry captures real IP address, user-agent, actor ID, and exact state delta (`diff_payload`).

---

## 4. Credential Hygiene & Secret Isolation Review

| Credential Type | Storage Mechanism | Git Status | Audit Verdict |
|---|---|:---:|:---:|
| **Firebase Service Account Key** | External file referenced via `FIREBASE_CREDENTIALS_PATH` | **IGNORED** | **SECURE** — Ignored by `.gitignore`; never committed to repo. |
| **JWT Secret Key** | Loaded via environment variable `JWT_SECRET_KEY` | **CONFIGURED** | **SECURE** — Default dev key provided in `.env.example`; prod requires injection. |
| **Database Connection Strings**| Loaded via `DATABASE_URL` / `DEMO_DATABASE_URL` | **CONFIGURED** | **SECURE** — Dedicated demo and dev SQLite files; zero credentials embedded. |
| **Bank Gateway HMAC Secrets** | Configured in `BANK_GATEWAY_WEBHOOK_SECRET` | **CONFIGURED** | **SECURE** — Mock secret used in tests; prod secret loaded from vault. |

---

## 5. External Integration Readiness Matrix

| Integration Target | Category Classification | Live Testing Status | Readiness Score | Blocking Prerequisite |
|---|---|:---:|:---:|---|
| **Firebase Cloud Storage** | **Category 1** (Implemented & Unit-Tested) | **VERIFIED** | **95%** | Production bucket provisioned: `sih-26265-fdr.firebasestorage.app`. Ready for production deployment. |
| **Bank FDR Gateway (API)** | **Category 5** (Simulated Sandbox Only) | **SIMULATED** | **70%** | Requires formal bank API credentials and SFPS / NeSL partner connectivity agreements. Simulated adapter handles all business flows with strict L3 lockouts. |
| **AICTE Approval Registry** | **Category 5** (Simulated Sandbox Only) | **SIMULATED** | **65%** | AICTE public portal does not expose a public verification API; simulated adapter serves synthetic accreditation standings. |
