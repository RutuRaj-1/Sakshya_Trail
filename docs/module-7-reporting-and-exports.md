# Module 7: Operational Reports, Record Drill-Down & Secure CSV/PDF Exports

**Implementation & Reference Documentation — Prompt 4 of 5**
**Project:** FDR Sentinel (SIH 2026 Problem Statement ID 26265, "Streamline of Security Deposit/FDR Portal")
**Specification Compliance:** PRD-FR-074 (Operational Reports), PRD-FR-093 (Audit Integrity Verification), Government Compliance Export Security Standards.

---

## 1. Architectural Overview & Design Principles

Prompt 4 provides authorized compliance officers, auditors, and administrators with an operational reports workspace and secure export pipelines. It bridges the gap between high-level Command Center metrics and line-item auditing.

### Key Architectural Tenets

1. **Reused Business Logic (No Disparate Implementations):**
   - The reports reuse the same underlying queries, models, and calculation rules established in Module 1 (Instruments), Module 4 (Validation & Findings), Module 5 (Lifecycle & Lineage), and Module 7 Prompt 1 (Command Center Metrics).
   - Upcoming maturities use the exact same calendar date calculation and renewal linkage logic as the Command Center maturity widgets.

2. **Server-Side Multi-Tenant Scope Isolation:**
   - Multi-tenant security boundaries (`enforce_scope_and_get_conditions`) are enforced on the database query before any metrics or rows are loaded into application memory.
   - An `INSTITUTION_USER` cannot query or export records belonging to another institution. Attempting to override the `institution_id` results in an immediate `403 Forbidden` and an immutable security audit event.

3. **Dedicated Export Authorization & Audit Trail:**
   - Viewing permission does **not** grant export rights.
   - Exports are strictly gated via `ExportService.verify_export_permission`: only `SYSTEM_ADMIN`, `SCRUTINY_OFFICER`, `AUDITOR`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`, and `FINANCE_OFFICER` may export records. An `INSTITUTION_USER` may only export their own institution's data if granted permission.
   - Every CSV and PDF export emits an audit event (`REPORT_EXPORT_CSV_*` or `REPORT_EXPORT_PDF_*`) with actor identity, timestamp, filter parameters, and row count, without leaking private document payload or credentials.

4. **Spreadsheet Formula Injection Defense (CSV):**
   - Any string value in the CSV export whose first character is `=`, `+`, `-`, `@`, `\t`, or `\r` is automatically sanitized by prefixing it with a single quote (`'`), neutralizing formula execution vulnerabilities when imported into Excel, Google Sheets, or LibreOffice.

5. **Official Regulatory PDF Generation (ReportLab):**
   - Implemented natively using Python's `reportlab` library (A4 Landscape, `NumberedCanvas` two-pass page numbering `Page X of Y`, alternating row highlights, metadata header box, and `CONFIDENTIAL - REGULATORY COMPLIANCE` sensitivity marking).

---

## 2. Core Operational Reports Catalog

### A. Pending Verification Report
- **Endpoint:** `GET /api/v1/dashboard/reports/pending-verification`
- **Export URLs:**
  - `GET /api/v1/dashboard/reports/pending-verification/export/csv`
  - `GET /api/v1/dashboard/reports/pending-verification/export/pdf`
- **Definition:** Instruments and verification requests awaiting bank confirmation or electronic verification response.
- **Source Models:** `Instrument`, `VerificationRequest`, `ValidationFinding`.
- **Distinguishing Simulated Requests:**
  - If a verification channel starts with `SIMULAT` or equals `SIMULATED`, the `is_simulated` flag is set to `true` and the UI renders an amber `SIMULATED` badge. The system explicitly prevents labeling simulated mocks as live bank confirmations.
- **Columns & Data Points:**
  - `instrument_id`, `reference_number`, `institution_id`, `institution_name`, `bank_name`, `branch`, `verification_status` (`PENDING`, `NOT_SUBMITTED`, `TIMEOUT`, `SOURCE_UNAVAILABLE`, `FAILED`), `channel`, `is_simulated`, `request_date`, `pending_age_days`, `assigned_office`, `discrepancy_count`, `drill_down_path`.

### B. Upcoming Maturities Report
- **Endpoint:** `GET /api/v1/dashboard/reports/upcoming-maturities`
- **Export URLs:**
  - `GET /api/v1/dashboard/reports/upcoming-maturities/export/csv`
  - `GET /api/v1/dashboard/reports/upcoming-maturities/export/pdf`
- **Definition:** Instruments approaching maturity within a selectable date window (30, 60, 90, 180, 365 days or custom date range).
- **Date Basis:** `Asia/Kolkata Calendar Date` (identical to Command Center widget).
- **Statutory Notice:** Maturity monitoring does not constitute release eligibility or confirm that a renewal has been verified.
- **Renewal Linkage:** Evaluates `InstrumentLineage` to distinguish `RENEWAL_LINKED` from `NO_RENEWAL_RECORDED`.
- **Columns & Data Points:**
  - `instrument_id`, `reference_number`, `institution_id`, `institution_name`, `bank_name`, `branch`, `amount`, `currency`, `issue_date`, `maturity_date`, `days_to_maturity`, `administrative_status`, `trust_level`, `renewal_status`, `successor_instrument_id`, `assigned_office`, `drill_down_path`.

### C. Missing Documents Report
- **Endpoint:** `GET /api/v1/dashboard/reports/missing-documents`
- **Export URLs:**
  - `GET /api/v1/dashboard/reports/missing-documents/export/csv`
  - `GET /api/v1/dashboard/reports/missing-documents/export/pdf`
- **Definition:** Instruments with missing, unreadable, wrong-category, or awaiting-confirmation checklist items against versioned policies.
- **Source Models:** `ValidationFinding`, `Instrument`, `Institution`.
- **Columns & Data Points:**
  - `finding_id`, `instrument_id`, `reference_number`, `institution_id`, `institution_name`, `bank_name`, `rule_id`, `document_category`, `policy_version`, `checklist_outcome`, `severity`, `finding_title`, `last_updated`, `drill_down_path`.

### D. Interventions Report
- **Endpoint:** `GET /api/v1/dashboard/reports/interventions`
- **Export URLs:**
  - `GET /api/v1/dashboard/reports/interventions/export/csv`
  - `GET /api/v1/dashboard/reports/interventions/export/pdf`
- **Definition:** Cases requiring administrative follow-up: overdue renewals, escalations, unresolved discrepancies, failed/source-unavailable verifications, or release blockers.
- **Tone & Terminology:** Neutral, regulatory language. Discrepancies and anomalies are reported as compliance follow-up items rather than assertions of fraud.
- **Columns & Data Points:**
  - `intervention_type` (`OVERDUE_ESCALATION`, `UNRESOLVED_DISCREPANCY`, `VERIFICATION_FAILED`, `RELEASE_BLOCKER`), `entity_id`, `reference_number`, `institution_id`, `institution_name`, `reason_description`, `severity`, `age_days`, `deadline_date`, `assigned_office`, `next_appropriate_action`, `drill_down_path`.

### E. Audit Evidence Pack
- **Endpoint:** `GET /api/v1/dashboard/reports/evidence-pack/{instrument_id}`
- **Definition:** Structured extract of an instrument's regulatory timeline, immutable document versions, SHA-256 integrity digests, field provenance count, scrutiny observations, and audit chain verification result.
- **Disclaimer:** Expressly labeled as an administrative compilation and not presented as an independently certified external forensic guarantee. If the hash chain is missing or broken, it reports `TAMPER_DETECTED` or `NOT_VERIFIED`.

---

## 3. Supported Export Formats & Security Defenses

| Format | Library / Mechanism | Security Controls Applied |
|:---|:---|:---|
| **CSV** | Python `csv.writer` with `utf-8-sig` BOM | - Formula injection neutralization (prefixes `=`, `+`, `-`, `@`, `\t`, `\r` with `'`).<br>- Metadata header block `# Report Type`, `# Generated At`, `# Security Classification`.<br>- Paged memory batching.<br>- Streaming HTTP attachment response. |
| **PDF** | `reportlab.platypus` (SimpleDocTemplate, Table, Paragraph) | - A4 Landscape format with autowrapping text.<br>- Two-pass `NumberedCanvas` footer (`Page X of Y`).<br>- Applied filter criteria table.<br>- Regulatory sensitivity label banner.<br>- Audit event emitted on dispatch. |

### Export Limits & Guardrails
- **Max CSV Row Limit:** Default 5,000 rows (clamped to 10,000).
- **Max PDF Row Limit:** Default 1,000 rows (clamped to 2,000) to ensure predictable generation latency and prevent memory exhaustion.
- **No Side Effects:** Generating a report or downloading an export is strictly read-only; it does not change instrument status, resolve discrepancies, or dispatch notifications.

---

## 4. Test Verification & Acceptance Status

### Automated Pytest Suite (`backend/tests/test_module7_prompt4_reports_exports.py`)
| Test Name | Focus Area | Status |
|:---|:---|:---|
| `test_pending_verification_report_simulation_flag` | Pending age calculation, source status, simulated vs live channel labeling | **PASSED** |
| `test_upcoming_maturities_report_renewal_status` | Calendar date window, deposit aggregation, renewal linkage | **PASSED** |
| `test_missing_documents_report` | Finding status `OPEN`, policy version, severity, drill-down path | **PASSED** |
| `test_interventions_report_overdue_and_failed` | Neutral overdue descriptions, failed verifications, next steps | **PASSED** |
| `test_cross_institution_isolation` | Multi-tenant scoping: institution user denied cross-institution query with 403 | **PASSED** |
| `test_secure_csv_export_with_formula_injection_defense` | Formula injection defense (`'=CMD|...`), UTF-8 BOM, metadata header, audit log | **PASSED** |
| `test_secure_pdf_export_generation` | Valid `%PDF-` bytes, ReportLab layout, audit event recorded | **PASSED** |
| `test_audit_evidence_pack_extract` | Cryptographic SHA-256 hashes, uncertified disclaimer, chain check | **PASSED** |

**Backend Pytest Result:** `8 passed in 2.56s` (Total Module 7 tests: `29 passed in 3.10s`).

### Automated Vitest Suite (`frontend/src/features/commandCenter/__tests__/OperationalReports.test.tsx`)
| Test Name | Focus Area | Status |
|:---|:---|:---|
| `renders operational reports workspace...` | Workspace layout, default tab, simulated badge, pending age | **PASSED** |
| `switches tabs to Upcoming Maturities...` | Statutory notice callout, total deposit value, renewal status | **PASSED** |
| `switches tabs to Missing Documents...` | Policy version, checklist outcome, severity badges | **PASSED** |
| `switches tabs to Interventions Required...` | Neutral descriptions, age/deadline, next actions | **PASSED** |
| `triggers CSV and PDF downloads...` | CSV & PDF export button triggers with download params | **PASSED** |
| `opens and displays the Audit Evidence Pack modal...` | SHA-256 checksum table, disclaimer, audit counters | **PASSED** |

**Frontend Vitest Result:** `6 passed in 542ms` (Total Module 7 vitest: `23 passed in 1.89s`).
**Frontend Production Bundle:** `npm run build` (`tsc -b && vite build`) passed with **0 errors**.
