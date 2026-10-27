# SakshyaTrail — Comprehensive Demonstration Environment Audit & Inventory
**SIH Problem Statement ID:** 26265 — Streamline of Security Deposit / FDR Portal  
**Document Type:** Phase 1 Deliverable — Repository Audit & Baseline Inventory  
**Date:** 2026-10-27

---

## 1. Existing Institutions and City Distribution

Inspection of the primary development database (`fdr_sentinel.db`) revealed:
- **Total Registered Institutions:** 482
- **Synthetic Institutions:** 6 (primarily `DEMO-AICTE-001`, `DEMO-AICTE-002`, `DEMO-AICTE-003`, and previous iteration seeds)
- **Non-Synthetic / Test Fixture Institutions:** 476 (generated across test runs with codes such as `ALP-xxxxxx`, `BET-xxxxxx`, `REP-A-xxxxxx`, `REP-B-xxxxxx` located in "New Delhi")
- **City Values in DB:** "New Delhi" (478), "Pune" (2), "Bengaluru" (1), other test values.

## 2. Distinguishing Synthetic vs Non-Synthetic Records

- **Flag:** `Institution.is_synthetic` (Boolean) and `Instrument.is_synthetic` (Boolean) reliably partition demonstration records from non-synthetic or operational fixtures.
- **Naming Conventions:** All demonstration institutions and instruments carry explicit labels:
  - Institutions: `DEMO — <Name> (SYNTHETIC)` in display name and `[SYNTHETIC DEMO]` in legal name.
  - Instruments: Marked with `is_synthetic=True` and `remarks="DEMO / SYNTHETIC — NOT A REAL FINANCIAL INSTRUMENT"`.
  - Documents: Marked with text watermarks `DEMO / SAMPLE ONLY — NOT A REAL FINANCIAL INSTRUMENT`.

## 3. Current Seed Commands and Idempotency Status

- `backend/scripts/init_db.py`: Seeds 3 institutions (`DEMO-AICTE-001`, `DEMO-AICTE-002`, `DEMO-AICTE-003`), 7 role users, and basic instruments. Idempotent via existence checks, but targets `DATABASE_URL` directly.
- `backend/scripts/bootstrap_admin.py`: Seeds `SYSTEM_ADMIN` user idempotently.
- `backend/scripts/demo_seed.py`: Initial prototype created in earlier iteration. Needs full Phase 2–7 CLI architecture (`--dry-run`, `--apply`, `--verify`, `--reset-demo`) targeting the isolated demonstration database.

## 4. Entities Required for a Coherent Demonstration Portfolio

To realize the 20-institution, 80-instrument portfolio across the canonical 9-stage lifecycle:
1. `Institution`: Exactly 20 active synthetic entities (10 Pune, 10 Mumbai).
2. `User`: 20 `INSTITUTION_USER` accounts (`nodal.pun001@example.com` ... `nodal.mum010@example.com`) + 6 internal role accounts (`SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, `FINANCE_OFFICER`, `AUDITOR`).
3. `Instrument`: 80 synthetic FDRs (4 per institution) spanning 20 scenario categories.
4. `Document` & `DocumentVersion`: Stored text PDFs with deterministic extraction & SHA-256 hashes.
5. `DocumentExtractedFields`: Structured candidate field records matching PDF contents.
6. `ValidationFinding`: Rule findings (matching, amount discrepancy, date discrepancy, duplicate certificate).
7. `ScrutinyObservation`: Officer observations with corrections and resubmission tracking.
8. `VerificationRequest` & `VerificationResponse`: Bank verification states (simulated match, simulated discrepancy, timeout).
9. `LifecycleEvaluation` & `LifecycleNotification`: Active, approaching maturity (30–90d), overdue (<0d).
10. `InstrumentLineage`: Predecessor-successor graphs for renewed deposits.
11. `ReleaseChecklistProfile`, `ReleaseRequest`, `ReadinessAssessment`, `ReleaseDecision`, `ReleaseOrderRecord`: Release lifecycle with inspectable blockers and maker-checker separation.
12. `AuditEvent`: Append-only hash chain integrity verified via `verify_audit_chain()`.

## 5. Existing Modules & APIs Reused

- **Module 1 (Identity & Institutions):** `/institutions`, `/auth`, `/users`
- **Module 2 (Instruments & Registry):** `/instruments`, `/instruments/{id}`
- **Module 2b (Documents & Storage):** `/documents`, deterministic PDF parser, local storage provider.
- **Module 3 (Validation & Discrepancy Engine):** Rule execution, finding status management.
- **Module 4 (Trust & Verification Desk):** L0–L3 trust levels, simulated bank verification adapter.
- **Module 5 (Lifecycle, Clock & Lineage):** `SimulatedClock`, maturity evaluation, lineage graph.
- **Module 6 (Release & Refunds):** Checklist readiness engine, CA statutory decision, FO release order, bank settlement.
- **Module 7 (Scrutiny Observations):** Deficiencies, correction loops.
- **Command Center & Audit:** `/command-center`, `/audit/verify-chain`.

## 6. Hardcoded Frontend Data or Metrics Conflict Assessment

- Frontend dashboards (`ExecutiveDashboard`, `CommandCenterPage`, `NineStageLifecycleTracker`) fetch data exclusively through backend REST endpoints (`/command-center/*`, `/instruments`, `/institutions`, `/audit/*`).
- No static hardcoded array metrics exist in the production frontend.
- Added city filtering (`city=Pune`, `city=Mumbai`) to `/institutions` and `/instruments` APIs so that UI city selectors derive directly from database queries.

## 7. Schema and Policy Limitations

- Unique constraints on `Institution.code` (`DEMO-PUN-001` ... `DEMO-MUM-010`) and `Instrument.reference_number` (`DEMO-PUN-001-FDR-001` ... `DEMO-MUM-010-FDR-004`).
- Strict RBAC: Statutory release decisions are restricted to `COMPETENT_AUTHORITY`, release orders to `FINANCE_OFFICER`, and `SYSTEM_ADMIN` is prevented from bypassing release gates.
- Append-only audit ledger: Test resets must never rewrite or delete from the established development audit ledger.

## 8. Safest Database and Reset Strategy

- **Dedicated Demo Database:** `SAKSHYATRAIL_DEMO_DATABASE_URL` defaulting to `sqlite:///./fdr_sentinel_demo.db`.
- **Fail-Safe Guard:** The seeder refuses to run `--reset-demo` against the persistent development database (`fdr_sentinel.db`) or any production target.
- **Clean Isolated Rebuild:** In the dedicated demonstration database, reset safely recreates schema via `Base.metadata.create_all()` and seeds deterministically from scratch, ensuring clean cryptographic audit chains and exactly 20 active institutions.
