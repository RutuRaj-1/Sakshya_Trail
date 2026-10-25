# FDR Sentinel — Complete UI/UX Feature Specification & Wireframe Blueprint

> **System Purpose:** Authoritative statutory regulatory platform for the **AICTE Regulation Bureau**, governing Fixed Deposit Receipts (FDRs), institutional security deposits, multi-tenant institutional isolation, 4-tier evidentiary trust verification (L0–L3), automated lifecycle renewals, tamper-evident hash-chained audit trails, and multi-stage release/refund workflows.
>
> **Document Purpose:** Complete, exhaustive page-by-page, component-by-component, and use-case-by-use-case feature breakdown derived directly from the complete production codebase. Use this document as the prompt and blueprint for AI UI/UX design tools (Figma, v0, Lovable, Claude Artifacts, Relume, Framer).

---

## 1. Executive Overview & Design System Tokens

### 1.1 Brand Identity & Design Personality
- **Domain:** Sovereign Regulatory Governance & Fintech Compliance.
- **Aesthetic Tone:** Authoritative, ultra-clean, high-density data cockpit, institutional trust, crisp typography, and high-visibility status indicators.
- **Color Palette (Current Theme):**
  - **Primary/Sentinel:** Deep Navy / Slate-950 (`#020617`), Indigo/Navy Slate-900 (`#0f172a`), Sentinel Brand (`#3b82f6` to `#1d4ed8`).
  - **Trust Levels:**
    - `L0 Declared`: Neutral Slate (`#64748b`) — Baseline self-declaration.
    - `L1 Document Consistent`: Blue (`#2563eb`) — OCR & document heuristic match.
    - `L2 Officer Verified`: Purple (`#9333ea`) — Manual scrutiny officer attestation.
    - `L3 Bank Confirmed`: Emerald / Green (`#059669`) — Cryptographic / SFTP host-to-host bank confirmation.
  - **Status Accents:**
    - `Active / Registered / Ready`: Emerald (`#10b981`)
    - `Expiring / Warning / Correction`: Amber (`#f59e0b`)
    - `Matured / Blocker / Danger / Down`: Rose / Crimson (`#e11d48`)
    - `In-Review / Processing`: Cyan / Blue (`#0284c7`)

### 1.2 User Personas & RBAC Matrix
The UI changes layout, action visibility, and data scope based on the active authenticated user's role:

| Role Code | Display Role | Permissions & Visible Modules |
| :--- | :--- | :--- |
| `SYSTEM_ADMIN` | System Administrator | Unrestricted access across all bureau features, user provisioning, audit chain verification, system diagnostics. |
| `COMPETENT_AUTHORITY` | Competent Authority | Final approval desk for FDR release/refund orders, audit ledger inspection, command center executive views. |
| `BRANCH_HEAD` | Regional Branch Head | Regional oversight, scrutiny approvals, audit history, operational report generation, queue reassignment. |
| `SCRUTINY_OFFICER` | Regulatory Scrutiny Officer | Primary operator: Discrepancy review queue, trust attestation (L2), scrutiny observations, report generation. |
| `FINANCE_OFFICER` | Bureau Finance Officer | Financial reconciliation, report generation, release order execution, deposit valuation. |
| `AUDITOR` | Independent Compliance Auditor | Read-only access across all institutions, ledger tamper-verification, full audit log inspection, evidence pack exports. |
| `INSTITUTION_USER` | Nodal Institutional Officer | Strictly isolated single-tenant view: Only views own college's deposits, records draft FDRs, requests release/refunds, password rotation. |

---

## 2. Global Shell & Navigation Framework

### 2.1 Top Application Header (`Header.tsx`)
- **Brand Identity Block:**
  - Sentinel shield icon badge with soft glow.
  - Title: **"FDR Sentinel"** with version tag badge (`v0.2.0 Identity & RBAC`).
  - Subtitle: *"AICTE Regulation Bureau · Security Deposit & FDR Lifecycle Integrity"*.
- **Real-Time Connectivity & Health Probes (Live Pills):**
  - **FastAPI Backend Liveness Probe:** Live pulse indicator (`online` / `offline`) with tooltip.
  - **Database Dialect & Readiness Probe:** Shows DB engine (`POSTGRESQL` / `SQLITE`), ping latency in ms (e.g., `4ms`), and status pill (`Ready` / `Not Connected`).
  - **Quick Probe Refresh Button:** Circular spin animation triggering asynchronous health re-check.
- **Authenticated Identity & Session Controls:**
  - User full name with departmental sub-text.
  - Role badge (color-coded by role hierarchy).
  - Avatar badge displaying computed uppercase initials.
  - **Change Password Quick Link:** Direct key icon link to `/change-password`.
  - **Logout Session Action:** Direct icon trigger terminating session and clearing HTTP-only JWT state.

### 2.2 Navigation Sidebar (`Sidebar.tsx`)
- **Header Section:** Sub-brand badge *"Lifecycle Platform"* with competition/statutory tag (`SIH 26265`).
- **Navigation Item List (Role-Aware):**
  1. **Dashboard** (`/`) — Icon: `LayoutDashboard`
  2. **Command Center** (`/command-center`) — Icon: `SlidersHorizontal` | Badge: *"Module 7"*
  3. **Unified Search** (`/search`) — Icon: `Search` | Badge: *"Search"*
  4. **Operational Reports** (`/reports`) — Icon: `FileSpreadsheet` | Badge: *"Reports"*
  5. **Release / Refund Cases** (`/release`) — Icon: `FileText` | Badge: *"Module 6"*
  6. **Review Queue** (`/findings/queue`) — Icon: `AlertTriangle` | Badge: *"Scrutiny"*
  7. **Trust & Verification** (`/verification`) — Icon: `ShieldCheck` | Badge: *"Trust"*
  8. **FDR Instruments** (`/instruments`) — Icon: `FileSpreadsheet` | Badge: *"Core"*
  9. **Institutions Directory** (`/institutions`) — Icon: `Building2`
  10. **User Admin** (`/users`) — Icon: `Users` | Badge: *"Admin"* *(System Admin Only)*
  11. **Audit History** (`/audit`) — Icon: `History` *(Admin / Auditor / Head / Authority)*
  12. **Password Security** (`/change-password`) — Icon: `KeyRound`
  13. **System Diagnostics** (`/health`) — Icon: `Activity`
- **Bottom Trust Hierarchy Reference Panel:**
  - Compact visual cheatsheet displaying trust tiers:
    - `L1 Declared` (Baseline)
    - `L2 Consistent` (OCR/Doc heuristics)
    - `L3 Verified` (Officer Verified)
    - `L4 Confirmed` (Bank Confirmed)

---

## 3. Detailed Page-by-Page Feature & Component Specification

---

### PAGE 1: Executive Dashboard (`/`)
*Route: `DashboardPage.tsx`*

#### Primary Purpose:
High-level situational awareness landing page tailored dynamically for either Bureau Officers or Institution Users.

#### Components & Visual Sections:
1. **Context-Aware Hero Welcome Banner:**
   - Badge toggling between *"AICTE Regulation Bureau"* vs *"Institutional Portal"*.
   - Dynamic heading: *"FDR Sentinel — Security Deposit & FDR Governance"* vs *"Security Deposit Management Vault"*.
   - Executive mission statement describing isolation, tiered trust, and immutability.
   - Quick Action buttons:
     - *Command Center (Module 7)*
     - *View FDR Registry*
     - *Institutions Directory*
     - *User Administration* (Admin only)
     - *Password Security*
2. **Primary Metric Cards Strip (4 KPI Grid):**
   - **Total Held Value:** Currency-formatted total INR (`₹ X,XX,XX,XXX`) with instrument count.
   - **Active Institutions:** Count of active colleges with historical/inactive count sub-label.
   - **Registered FDRs:** Total statutory formal records with draft record count.
   - **Expiring Soon (≤ 90 Days):** Amber warning card with approaching maturity count.
3. **Conceptual Breakdown Cards (2-Column Grid):**
   - **Administrative Status Distribution Card:**
     - Registered count (Formal statutory records).
     - Draft count (In-progress submissions).
   - **Evidentiary Trust Tiers Distribution Card:**
     - 4-column metric bar: `L0 DECLARED`, `L1 DOC OK`, `L2 VERIFIED`, `L3 BANK CONF`.
4. **Recent Security Deposits Widget:**
   - Embedded preview table of the 5 most recent deposits.
   - Columns: Reference #, Institution, Bank, Principal Amount, Maturity Date, Trust Badge, Action button linking to details.

---

### PAGE 2: Command Center Executive Cockpit (`/command-center`)
*Route: `CommandCenterPage.tsx`*

#### Primary Purpose:
Operational intelligence flight deck implementing PRD Module 7. Surfaces real-time multi-dimensional metrics, objective triage queues, and maturity forecasting.

#### Header Controls:
- Dynamic title (Bureau Cockpit vs Institution Command Center).
- **Metric Dictionary Button (PRD-FR-077):** Opens searchable definition modal for every metric calculation.
- **Refresh Live Data Button:** Re-aggregates live backend data with spin state.
- **Global Horizon Controls:** State synchronized to URL search parameters (`window_days`, `year`, `min_score`).

#### Section-by-Section Components:
1. **Status Overview Strip (`StatusOverviewCards.tsx`):**
   - 6 responsive KPI tiles, each clickable to navigate to pre-filtered search results:
     - `Active Instruments` (Beyond window horizon)
     - `Expiring Soon` (Within configured window days, default 90d)
     - `Matured Instruments` (Term elapsed, awaiting action)
     - `Renewed / Replaced` (Active successor present in lineage)
     - `Released Deposits` (Discharged by authority order)
     - `Pending Review / Draft` (Intake or deficiency scrutiny)
   - Info icon on each card linking directly to that metric's definition in the dictionary.
2. **Operational Priority Queue Desk (`PriorityQueueDesk.tsx` - PRD-FR-075):**
   - *Visible to Bureau Officers only.*
   - **Statutory Clarification Banner:** Mandatory legal notice clarifying the score is strictly a 0–100 workflow urgency ranking, **NOT** a fraud probability or credit score.
   - **Filter Controls:** Score threshold dropdown (`All Items 0+`, `Moderate 25+`, `Elevated 50+`, `Critical Urgency 75+`).
   - **Weights & Assumptions Drawer Toggle:** Displays disclosed formula weights:
     - *Urgency (Maturity Proximity): 35%*
     - *Discrepancy Severity: 25%*
     - *Evidentiary Trust Gap: 20%*
     - *Financial Exposure: 20%*
   - **Urgency Table:**
     - Columns: Rank & Priority Score pill (color-coded red/amber/blue), Instrument Ref, Institution Name, Bank, Held Value, Days to Maturity, Critical Flags / Discrepancy count, Explainability breakdown toggle, Quick Action button (`Review`).
3. **Maturity Window Monitor (`MaturityWindowSection.tsx` - PRD-FR-070b):**
   - Window Days Selector tabs: `30 Days`, `60 Days`, `90 Days`, `180 Days`, `365 Days`.
   - Aggregate sum of maturing capital within selected window.
   - Paginated table of maturing certificates with days-remaining countdown badges.
4. **Overdue & Escalated Work Items (`OverdueEscalatedQueue.tsx` - PRD-FR-070c):**
   - Tracks overdue notices and missed renewal milestones (T-90, T-60, T-30, T-15, T-0).
   - Escalation tiers (Tier 1 Scrutiny, Tier 2 Regional Head, Tier 3 Competent Authority).
   - Direct link to initiate renewal or record bank response.
5. **Verification Queue & Channel Health (`VerificationQueueWidget.tsx` - PRD-FR-070d):**
   - Real-time status of external bank verification channels (SFTP batch, Bank API, Manual Letter).
   - Pending verification items breakdown with aging indicator.
6. **Completeness & Release Blockers Widget (`CompletenessBlockersWidget.tsx`):**
   - **Document Completeness (PRD-FR-070e):** Tracks mandatory upload categories (FDR copy, Lien letter, Undertaking). Displays explicit `POLICY UNCONFIGURED` state if policy rules are inactive.
   - **Release Blockers (PRD-FR-070f):** Active refund/release cases halted due to unsatisfied prerequisites.
7. **Month-Wise Maturity Load Distribution (`MaturityLoadChart.tsx` - PRD-FR-076):**
   - Calendar Year selector (`2025`, `2026`, `2027`, etc.).
   - Visual 12-month bar chart / distribution strip showing monthly capital exposure (INR) and certificate volumes.
8. **Interactive Metric Dictionary Modal (`MetricDictionaryModal.tsx` - PRD-FR-077):**
   - Searchable catalog of all PRD metrics.
   - Category filters: Status, Maturity, Verification, Priority, Lifecycle.
   - Detail view displaying: Formula, Raw query logic, Inclusions, Exclusions, Refresh SLA.

---

### PAGE 3: Operational Reports Workspace (`/reports`)
*Route: `ReportsPage.tsx` & `OperationalReportsWorkspace.tsx`*

#### Primary Purpose:
Official regulatory reporting desk (PRD-FR-074) supporting dynamic filtering, official CSV export, formal PDF export, and individual instrument Audit Evidence Packs.

#### Header & Global Actions:
- Title & Bureau description.
- **Role-Gated Export Actions:**
  - **Export CSV Button:** Secure streamed CSV export of active tab data with applied filters.
  - **Export PDF Button:** Formal compliance PDF generation with institutional headers and signatures.
  - Disabled with explanatory tooltip for unauthorized roles.

#### 4 Operational Report Tabs:
1. **Pending Verification Report Tab:**
   - Instruments awaiting L1/L2/L3 verification.
   - Record count badge.
2. **Upcoming Maturities Report Tab:**
   - Instruments expiring within configurable time horizons.
3. **Missing Documents & Deficiencies Report Tab:**
   - Instruments lacking required statutory attachments.
4. **Interventions & Escalation Queue Report Tab:**
   - Blocked releases, overdue notices, and unresolved discrepancies.

#### Universal Filter Drawer / Bar:
- Time Horizon: `30d`, `60d`, `90d`, `180d`, `365d`.
- Date Range: `Date From` to `Date To`.
- Bank Name (free text / select).
- Assigned Regional Office.
- Trust Level filter (`L0`, `L1`, `L2`, `L3`).
- Administrative Status filter.
- Verification Status.
- Discrepancy Severity filter.
- Reset Filters button.

#### Report Table Features:
- High-density columns: Instrument Ref, Institution Name & AISHE/DISE code, Bank & Branch, Amount (INR), Issue Date, Maturity Date, Current Trust Tier, Discrepancy count.
- Action: **"View Evidence Pack" button** triggering the full audit snapshot modal.

#### Audit Evidence Pack Modal:
- Displays point-in-time cryptographic audit snapshot of an FDR.
- Checksums (SHA-256), chain state, full verification provenance, and exportable evidentiary dossier.

---

### PAGE 4: Unified Search & Query Desk (`/search`)
*Route: `UnifiedSearchPage.tsx`*

#### Primary Purpose:
Single-pane search index across all statutory FDR certificates and release/refund cases with multi-criteria Boolean filtering.

#### Components:
1. **Search Domain Switcher Tabs:**
   - **Statutory Instruments** (Default)
   - **Release / Refund Cases**
2. **Primary Search Input Bar:**
   - Large global search input querying FDR number, institution name, bank name, AISHE code, or case reference.
   - Real-time synchronization to URL (`?q=...`).
   - Clear query (`X`) button.
3. **Advanced Filter Toggle Drawer:**
   - Bank Name dropdown / input.
   - Institution Code / Name.
   - Status Filter (ALL, DRAFT, REGISTERED, MATURED, LIQUIDATED, RELEASE_PENDING, RELEASED, FORFEITED, ENCASHED).
   - Evidentiary Trust Tier (L0, L1, L2, L3).
   - Regional Office.
   - Issue Date Range (From / To).
   - Maturity Date Range (From / To).
   - **Has Discrepancies Only Toggle** (Checkbox filter).
   - Priority Urgency Category (CRITICAL, HIGH, MEDIUM, LOW).
   - Reset All Filters action.
4. **Sorting Controls:**
   - Sort Field selector: `Created Date`, `Deposit Amount`, `Maturity Date`, `Issue Date`, `Trust Level`.
   - Sort Order toggle: Ascending / Descending.
5. **Results View (Cards & Table Toggle):**
   - Total matching records count header.
   - Dynamic cards showing: FDR reference, Institution title, Bank logo/name, formatted INR amount, maturity countdown badge, trust level badge, discrepancy alerts, and direct link to `/instruments/:id`.
6. **Pagination Footer:**
   - Previous / Next navigation, page number indicators, results range summary.

---

### PAGE 5: Release / Refund Cases Desk (`/release`)
*Route: `ReleaseCasesPage.tsx`*

#### Primary Purpose:
Workflow tracking desk for security deposit release, forfeiture, partial liquidation, and refund requests (Module 6).

#### Components:
1. **Header Action:**
   - **"New Request" button:** Visible to `INSTITUTION_USER` to submit a new FDR release application.
2. **Filter & Search Toolbar:**
   - Search input (by Case Number or Instrument ID).
   - Status Filter Dropdown covering the 12-state workflow:
     - `DRAFT`
     - `SUBMITTED`
     - `UNDER_REVIEW`
     - `RETURNED_FOR_CORRECTION`
     - `READY_FOR_AUTHORITY`
     - `APPROVED`
     - `REJECTED`
     - `RELEASE_ORDER_RECORDED`
     - `BANK_SIDE_ACTION_PENDING`
     - `COMPLETED`
     - `CLOSED`
     - `CANCELLED`
3. **Cases Table / Cards:**
   - Case Reference Number.
   - Target Instrument Reference.
   - Applicant Institution.
   - Request Type (Full Release, Partial Refund, Substitution).
   - Amount Requested.
   - Workflow Status Badge (color-coded per state).
   - Creation Date.
   - Action: View Case Detail (`/release/:id`).
4. **Empty State & Role Guidance:**
   - Friendly empty illustration prompting institution users to initiate their first deposit release request.

---

### PAGE 6: Release Case Detail & Approval Workspace (`/release/:id`)
*Route: `ReleaseDetailPage.tsx`*

#### Primary Purpose:
Multi-stage decisioning and readiness assessment workspace for bureau officers and competent authorities.

#### Components:
1. **Case Status Header Banner:**
   - Case number, creation timestamp, and large workflow state pill.
   - **Demo Policy Disclaimer Banner:** Displays if policy profile is running in simulation mode.
   - 4-Column Metadata Grid: Request Type, Case Type, Target Instrument ID (with link), Policy Version.
2. **Request Reason & Justification Section:**
   - Formatted institutional explanation for deposit refund or course closure.
3. **Automated Readiness Assessment Widget (Checklist Engine):**
   - KPI Summary Strip: `Total Checklist Items`, `Satisfied Count`, `Blockers Count` (Red alert), `Pending Count`.
   - Assessment Outcome Banner:
     - `READY_FOR_APPROVAL` (Green) vs `BLOCKED_BY_DEFICIENCIES` (Amber/Red).
     - Automated summary notes explaining the evaluation.
   - **Detailed Checklist Items Accordion/List:**
     - Each item displays: Code (e.g., `DOC-COMPLETENESS`, `LIEN-DISCHARGE-NOC`, `MIN-TENURE`), item explanation, status (`SATISFIED`, `FAILED`, `PENDING`), source module, and prominent `BLOCKER` badge if mandatory.
4. **Decision History & Immutable Audit Trail:**
   - Chronological card timeline of past workflow decisions.
   - Displays: Decision Type (`RECOMMEND_APPROVAL`, `RETURN_CORRECTION`, `FINAL_AUTHORITY_SANCTION`), Actor role, Timestamp, Justification reason, Status change arrow (`UNDER_REVIEW → READY_FOR_AUTHORITY`).

---

### PAGE 7: Review Queue / Findings Scrutiny (`/findings/queue`)
*Route: `ReviewQueuePage.tsx`*

#### Primary Purpose:
Operational discrepancy scrutiny workbench (Module 3) where officers investigate, assign, and resolve algorithmic and OCR validation findings.

#### Components:
1. **Queue Filters Toolbar:**
   - Search by finding title, field, or institution.
   - Status Tabs: `ACTIVE` (Open + In-Review), `OPEN`, `IN_REVIEW`, `RESOLVED`, `DISMISSED`, `ALL`.
   - Discrepancy Severity filter: `CRITICAL`, `MAJOR`, `MODERATE`, `MINOR`.
   - Discrepancy Category filter: `OCR_MISMATCH`, `FIELD_INCONSISTENCY`, `DATE_ANOMALY`, `AMOUNT_DISCREPANCY`, `LIEN_DEFECT`.
   - Institution filter dropdown.
   - Sort by Priority Score vs Date.
2. **Findings Table:**
   - Priority Urgency score pill.
   - Finding Title & Error Code.
   - Affected Instrument Reference & Institution.
   - Source Module (`Module 2 OCR`, `Module 4 Bank SFTP`, `Module 5 Renewal`).
   - Assignee Officer badge (or `Unassigned`).
   - Creation Date & SLA timer.
   - Action: **"Investigate Finding" button**.
3. **Finding Detail & Action Modal / Drawer:**
   - **Discrepancy Comparison Block:** Side-by-side comparison of `Declared Value` vs `Detected/Extracted Value` with percentage variance.
   - **Priority Score Explainability Widget:** Breakdown showing how the score was calculated.
   - **Observation & Action Desk:**
     - *Assign / Reassign:* Dropdown of eligible scrutiny officers with assignment notes.
     - *Change Status:* Transition to `IN_REVIEW`.
     - *Resolve Finding:* Enter mandatory resolution rationale and mark `RESOLVED`.
     - *Dismiss Finding:* Enter false-positive justification and mark `DISMISSED`.
     - *Return for Correction:* Sends immediate alert to institution with remediation instructions.
     - *Add Scrutiny Observation:* Appends notes to the audit history.

---

### PAGE 8: Trust & Verification Desk (`/verification` & `/verification/:id`)
*Route: `TrustVerificationDeskPage.tsx`*

#### Primary Purpose:
The core evidentiary engine of FDR Sentinel (Module 4). Manages the multi-tier trust progression (L0 Declared → L1 Consistent → L2 Officer Verified → L3 Bank Confirmed), bank outreach, SFTP verification, and downgrade protocols.

#### Components & Modes:
1. **Instrument Search & Selection Mode (When no ID selected):**
   - Quick-picker search to find and load any FDR certificate into the desk.
2. **Active Desk Workspace (When instrument loaded):**
   - **Header Card:** Instrument Reference, Bank, Principal, Current Trust Badge, Maturity Date.
   - **4 Main Investigation Tabs:**

#### Tab 1: Trust Hierarchy & Attestation (`trust`)
- **Aggregate Trust Summary Card:** Visual Stepper showing progression across L0, L1, L2, and L3.
- **Trust Assessments Checklist:** Granular rules checked (Document integrity, signature verification, bank confirmation matching).
- **Officer Decision Actions (Role-gated):**
  - **L2 Officer Verification Button:** Opens dialog to attest document authenticity, enter evidence references, specify document version, and submit formal L2 status.
  - **L3 Bank Confirmation Button:** Opens dialog to record SFTP host-to-host or API bank confirmation response ID.
  - **Downgrade Trust Level Button (Red):** Demotes instrument back to L1 or L0 if fraudulent or conflicting bank data surfaces. Requires mandatory trigger selection (`CONFLICTING_BANK_EVIDENCE`, `DOCUMENT_FORGERY_SUSPECTED`, etc.) and audit justification.
- **Trust Transition History Timeline:** Immutable chronological ledger of all past trust promotions and demotions with actor stamps.

#### Tab 2: Field Provenance (`provenance`)
- Field-by-field source tracking (Bank Name, Amount, Maturity Date, Lien Clause).
- Shows exact source: `Institution Self-Declaration`, `OCR Extracted`, `Manual Officer Entry`, or `Direct Bank SFTP Feed`.
- Confidence score percentage and timestamp of last verification.

#### Tab 3: Verification Requests & Channel Dispatch (`requests`)
- List of sent verification inquiries to banks.
- **"New Verification Request" Action:** Dispatches inquiry via selected channel:
  - `SFTP_RECONCILIATION` (Batch SFTP)
  - `BANK_API` (Direct Host-to-Host)
  - `EMAIL_OUTREACH` (Signed digital email)
  - `MANUAL_LETTER` (Physical postal dispatch)
- **Simulate Dispatch & Response Action (Testing/Demonstration):** Dispatches normal match, discrepancy match, or timeout scenario.
- **Record Manual Bank Confirmation Action:** Enables officer to record physical bank confirmation letter, certificate reference, date, and verified values.

#### Tab 4: Conflicts & Discrepancies (`conflicts`)
- Side-by-side discrepancy review between bank-reported values and institution-declared values.

---

### PAGE 9: Statutory FDR Instruments Registry (`/instruments`)
*Route: `InstrumentsPage.tsx`*

#### Primary Purpose:
Central tabular repository of all Fixed Deposit Receipts pledged to the AICTE Regulation Bureau.

#### Components:
1. **Header Action:**
   - **"Record FDR Instrument" button:** Opens creation modal (accessible to Admin, Officer, and Institution User).
2. **KPI Overview Strip (4 Metric Tiles):**
   - Total Deposit Portfolio (INR).
   - Active Compliance Count.
   - Approaching Maturity Count.
   - Evidentiary Trust Distribution.
3. **Filter & Search Bar:**
   - Search by Reference Number, Bank, or Institution.
   - Status Filter: `ALL`, `REGISTERED`, `DRAFT`, `MATURED`, `RELEASED`, `FORFEITED`.
   - Trust Level Filter: `ALL`, `L0`, `L1`, `L2`, `L3`.
   - Institution Picker Filter (for internal bureau users).
4. **Instruments Data Table (`InstrumentsList.tsx`):**
   - Columns:
     - Reference Number (Monospace font with quick copy button).
     - Institution Name & Regional Office.
     - Issuing Bank & Branch.
     - Principal Amount (Formatted INR).
     - Issue Date & Maturity Date (with remaining days badge).
     - Administrative Status Badge.
     - Trust Level Badge (`L0` to `L3`).
     - Actions: Details Button (`/instruments/:id`), Quick Edit Button.
5. **Pagination & Page Size Controls.**

---

### PAGE 10: Instrument Detail & Lifecycle Dossier (`/instruments/:id`)
*Route: `InstrumentDetailPage.tsx`*

#### Primary Purpose:
Comprehensive 360-degree regulatory dossier for a single FDR certificate, encompassing metadata, attachments, renewal lineage, scrutiny notes, and notification dispatch logs.

#### Header Summary Banner:
- Instrument Reference Number, Bank Name, and Status.
- Principal Amount formatted prominently.
- Maturity date with visual countdown tag (`Expiring in 42 days` or `Matured 10 days ago`).
- Primary Actions:
  - **Edit Instrument Registry Details**
  - **Navigate to Trust Verification Desk**

#### 6 Dossier Tabs:
1. **Snapshot Tab:**
   - **Primary Certificate Metadata Card:** Instrument Type, Bank, Branch, Ref #, Amount in INR, Issue Date, Maturity Date, Tenure, Lien Holder, Lien Details, Regional Office, Remarks.
   - **Evidentiary Trust Card:** Current level, verification status, and one-click link to Verification Desk.
   - **Cryptographic Tamper-Evident Integrity Strip:** Displays SHA-256 Record Hash, Merkle root reference, and copyable signature.
   - **Lifecycle Milestone Radar:** Proximity to next renewal notice (T-90, T-60, T-30, etc.).
2. **Documents & Attachments Tab:**
   - Upload new document attachment (FDR Scan, Lien Endorsement, Bank NOC).
   - Document list with MIME type, file size, SHA-256 checksum, OCR processing status, and download action.
3. **Field History & Provenance Tab:**
   - Chronological audit diff of every field modification over time (Old Value → New Value, Changed By, Reason).
4. **Renewal Lineage & Roll-Over Tree Tab (`RenewalLineageSection.tsx` - Module 5):**
   - **Interactive Visual Lineage Tree:** Displays ancestor instruments (predecessors), current instrument, and renewed successors.
   - **Deposit Continuity Assessment:**
     - Capital Continuity Check: Flags if renewal amount is less than original principal.
     - Temporal Continuity Check: Flags uncollateralized gaps between maturity date and renewal start date.
     - Lien Clause Continuity Check: Verifies AICTE pledge status remained unbroken.
   - **"Record Successor / Renewal" Action:** Pre-fills successor creation dialog with predecessor terms.
   - **"Lineage Correction" Action:** Fixes erroneous lineage links with administrative override.
   - **Lifecycle Notification Timeline (`LifecycleNotificationHistory.tsx`):**
     - Full dispatch log of statutory automated notices sent to institution nodal officers (Email / SMS).
     - Delivery statuses (`DELIVERED`, `QUEUED`, `FAILED`).
     - **Manual Retry Action:** Re-triggers failed notice delivery.
     - **"Evaluate & Dispatch Due Notices" Action:** Proactively checks and sends due reminders.
5. **Scrutiny Observations Tab:**
   - Official chronological thread of scrutiny notes left by officers.
   - **"Add Scrutiny Observation" Action:** General, Lien, Maturity, or Compliance note with internal-only privacy toggle.
   - **"Amend Observation" Action:** Append-only correction creating an audit supersession.
   - **"Resolve Observation" Action:** Closes finding with mandatory resolution reason.
6. **Audit Trail Tab:**
   - Full immutable log of every action executed against this certificate.

---

### PAGE 11: Institution Directory (`/institutions`)
*Route: `InstitutionsPage.tsx`*

#### Primary Purpose:
Master institutional registry of all colleges, universities, and technical bodies under AICTE regulation.

#### Components:
1. **Header Action:**
   - **"Register Institution" button:** Visible to `SYSTEM_ADMIN` to register a new college.
2. **Search & Filter Toolbar:**
   - Search by Institution Name, AISHE/DISE code, or City.
   - Status Filter: `ALL`, `ACTIVE`, `INACTIVE`.
   - Institution Type Filter: `ALL`, `TECHNICAL_INSTITUTE`, `ENGINEERING_COLLEGE`, `PHARMACY_INSTITUTE`, `MANAGEMENT_STUDIES`, `POLYTECHNIC_COLLEGE`.
3. **Institutions Table (`InstitutionsList.tsx`):**
   - College Name & AICTE Approval Code.
   - Type Badge.
   - State & Regional Jurisdiction.
   - Nodal Officer Contact (Name, Email, Phone).
   - Active Status Toggle / Badge.
   - Associated Deposit Count & Total Held Portfolio.
   - Actions: View Details (`/institutions/:id`), Edit Profile.
4. **Deactivate / Activate Confirmation Modal:**
   - Prompts for mandatory administrative reason before suspending or restoring an institution.

---

### PAGE 12: Institution Detail & Compliance Profile (`/institutions/:id`)
*Route: `InstitutionDetailPage.tsx`*

#### Primary Purpose:
Detailed compliance dossier of an educational institution, its active nodal officers, and its complete portfolio of pledged security deposit FDRs.

#### Components:
1. **Header Profile Card:**
   - College Name, AISHE Code, Category, Affiliation Status.
   - Status toggle (Active / Suspended) for Admins.
   - **"Edit Institution / Update Nodal Contact" button**.
2. **Key Compliance Metrics Grid:**
   - Total Pledged Deposits (INR).
   - Number of Active FDRs.
   - Compliance Deficiencies Count.
3. **Pledged Instruments Portfolio Table:**
   - Full list of FDR certificates belonging strictly to this institution.
   - Status badges, maturity countdowns, and quick link to `/instruments/:id`.
   - **"Record New FDR for Institution" Action**.
4. **Official Contact & Nodal Officer Card:**
   - Head of Institute details, email, contact telephone, physical campus address.

---

### PAGE 13: User Administration & Provisioning (`/users`)
*Route: `UserAdminPage.tsx`*
*(Accessible exclusively to `SYSTEM_ADMIN`)*

#### Primary Purpose:
Regulatory identity management, role-based provisioning, password reset dispatch, and institutional account assignment.

#### Components:
1. **Header Action:**
   - **"Provision User Account" button:** Opens account creation modal.
2. **Filters & Search Toolbar:**
   - Search by user full name or email address.
   - Role Filter Dropdown: `SYSTEM_ADMIN`, `COMPETENT_AUTHORITY`, `BRANCH_HEAD`, `SCRUTINY_OFFICER`, `FINANCE_OFFICER`, `INSTITUTION_USER`, `AUDITOR`.
   - Account Status Filter: `ALL`, `ACTIVE`, `INACTIVE`.
3. **Users Table:**
   - Name & Avatar initials.
   - Email address.
   - Role Badge (color-coded).
   - Associated Institution (Mandatory for `INSTITUTION_USER`, displays college name; shows `AICTE Bureau` for officers).
   - Temporary Password / Must-Change-Password indicator.
   - Account Status (Active / Disabled).
   - Actions:
     - **Administrative Password Reset Button** (Generates secure temporary password).
     - **Toggle Account Active / Inactive Button**.
4. **Provision User Modal Dialog:**
   - Full Name, Official Email Address.
   - Initial Password (min 8 characters).
   - Role Selector dropdown.
   - Institution Association Dropdown (Dynamically enabled/required when `INSTITUTION_USER` is selected).
   - *"Require password rotation on first login"* checkbox (Enabled by default).
5. **Password Reset Success Modal:**
   - Displays newly generated temporary password with a **1-Click Copy to Clipboard** button and security advisory.

---

### PAGE 14: Tamper-Evident Audit Ledger (`/audit`)
*Route: `AuditPage.tsx`*
*(Accessible to: `SYSTEM_ADMIN`, `AUDITOR`, `BRANCH_HEAD`, `COMPETENT_AUTHORITY`)*

#### Primary Purpose:
Cryptographically verifiable, immutable audit trail guaranteeing non-repudiation of all regulatory modifications, status shifts, and logins.

#### Components:
1. **Ledger Header & Integrity Action:**
   - Title & Bureau non-repudiation notice.
   - **"Verify Hash Chain Integrity" Button:** Executes cryptographic SHA-256 block-by-block hash verification across the entire database ledger.
2. **Chain Integrity Verification Result Banner:**
   - Appears upon verification execution:
     - *Verified Blocks Count* (e.g., `1,420 blocks verified`).
     - *Broken Chains / Tamper Flags* (`0 tampered records`).
     - *Root Merkle Hash* (Monospace string with copy button).
     - *Timestamp of Verification Run*.
3. **Audit Event Filters:**
   - Search keyword (Actor, Resource ID, Action).
   - Action Type filter (CREATE, UPDATE, STATUS_CHANGE, TRUST_TRANSITION, LOGIN, EXPORT).
   - Outcome filter: `ALL`, `SUCCESS`, `DENIED`, `FAILURE`.
   - Date From & Date To inputs.
   - Reset Filters button.
4. **Audit Events Table:**
   - Timestamp (ISO + localized relative time).
   - Action Name (e.g., `INSTRUMENT_REGISTERED`, `TRUST_L2_ATTESTED`, `RELEASE_ORDER_SANCTIONED`).
   - Outcome Badge (`SUCCESS` Green, `DENIED` Amber, `FAILURE` Red).
   - Actor Name, Email & Role.
   - Target Resource Type & Monospace Resource ID.
   - Client IP Address.
   - Action: **"Inspect Event Cryptography" button**.
5. **Audit Event Detail & Cryptography Modal:**
   - SHA-256 Block Hash (with 1-click copy).
   - Previous Block Hash (demonstrating cryptographic parent link).
   - User Agent & Request Trace ID.
   - **Payload State Snapshot:** Side-by-side JSON diff of `State Before Action` vs `State After Action`.

---

### PAGE 15: System Diagnostics & Health Probes (`/health`)
*Route: `HealthPage.tsx`*

#### Primary Purpose:
Operational DevOps observability page displaying live probe responses, database latency, and system environment info.

#### Components:
1. **Header Action:**
   - **"Run Health Check" button:** Immediate re-probe with live spinner.
2. **Diagnostics Grid (2 Primary Cards):**
   - **FastAPI Backend (Liveness) Card:**
     - Status Badge (`ALIVE` / `DOWN`).
     - Service name, version, runtime environment (`development` / `production`).
     - Probe Endpoint URL (`/api/v1/health/live`).
     - API Base URL.
   - **Database Layer (Readiness) Card:**
     - Status Badge (`READY` / `DEGRADED`).
     - Engine Dialect (`POSTGRESQL` / `SQLITE`).
     - Ping Latency in milliseconds (`4ms`).
     - Readiness Probe Endpoint (`/api/v1/health/ready`).
     - Connection error diagnostics block (if degraded).
3. **Raw Diagnostic Payloads Card:**
   - Formatted JSON response viewers displaying raw backend outputs from `/live` and `/ready`.

---

### PAGE 16: Authentication / Login Portal (`/login`)
*Route: `LoginPage.tsx`*

#### Primary Purpose:
Official entry point supporting multi-role authentication, session cookie issuance, and evaluator demo logins.

#### Components:
1. **Central Institutional Card:**
   - AICTE Bureau crest / Sentinel shield emblem.
   - Subtitle: *"AICTE Regulation Bureau · Security Deposit & FDR Lifecycle Portal"*.
2. **Credential Form:**
   - Email Input field with mail icon.
   - Password Input field with lock icon.
   - Sign In submit button with loading spinner state.
   - Error alert box for invalid credentials.
3. **One-Click Evaluator Demo Accounts Panel:**
   - 4 quick-switch buttons that immediately populate valid test credentials for jury/evaluator assessment:
     - **System Admin:** `admin@aicte-india.org`
     - **Scrutiny Officer:** `scrutiny.verma@aicte-india.org`
     - **Institution User:** `nodal@diet-delhi.ac.in` (Triggers password rotation prompt)
     - **Auditor:** `auditor.compliance@aicte-india.org` (Read-only view)
4. **Session Security Footer Notice:**
   - *"Session security: Signed JWT · HttpOnly SameSite Cookie · Argon2id Hashes"*.

---

### PAGE 17: Password Security & Rotation (`/change-password`)
*Route: `ChangePasswordPage.tsx`*

#### Primary Purpose:
Mandatory password rotation page for newly provisioned accounts or self-service security updates.

#### Components:
1. **Header Advisory:**
   - Key icon badge.
   - Title: *"Password Rotation Required"* or *"Update Security Credentials"*.
   - Explanatory note explaining that temporary passwords must be replaced before bureau access is granted.
2. **Password Form:**
   - Current / Temporary Password input.
   - New Password input (enforces min 8 characters).
   - Confirm New Password input.
   - Client-side validation: Checks matching passwords and disallows new password identical to temporary password.
   - Submit Button: *"Update Password & Authenticate"*.
3. **Success State & Auto-Redirect:**
   - Success badge and notification confirming Argon2 encryption update.
   - Auto-redirects to `/` after 1.5 seconds.

---

## 4. Complete Dialog & Modal Catalog

The redesign must accommodate the following **15 interactive modals and drawers**:

| Modal Component | File Location | Triggered From | Key Inputs & Interactive Controls |
| :--- | :--- | :--- | :--- |
| **Record / Edit FDR Instrument** | `InstrumentModal.tsx` | Instruments Page, Dashboard, Institution Detail | Institution picker, Bank dropdown, Branch, Reference #, Amount (INR), Issue Date, Maturity Date, Lien holder, Duplicate detection warning banner. |
| **Register / Edit Institution** | `InstitutionModal.tsx` | Institutions Page, Institution Detail | College name, AISHE code, Institution type, Address, City, State, Nodal officer full name, email, phone. |
| **Metric Dictionary** | `MetricDictionaryModal.tsx` | Command Center, Status Overview Cards | Search bar, category filter pills, metric formula, calculation logic, inclusions/exclusions, refresh SLA. |
| **Audit Evidence Pack** | `OperationalReportsWorkspace.tsx` | Reports Workspace Table | Point-in-time tamper-evident snapshot, Merkle hash, SHA-256 certificate, verification trace, print/export. |
| **L2 Officer Attestation** | `TrustVerificationDeskPage.tsx` | Trust Desk (`trust` tab) | Document version selection, evidence references, verification justification, attestation submit. |
| **L3 Bank Confirmation** | `TrustVerificationDeskPage.tsx` | Trust Desk (`trust` tab) | Bank SFTP response ID, authentication channel, confirmation notes, promote to L3. |
| **Trust Downgrade** | `TrustVerificationDeskPage.tsx` | Trust Desk (`trust` tab) | Target tier (L0/L1), downgrade trigger reason dropdown, mandatory justification note. |
| **New Verification Request** | `TrustVerificationDeskPage.tsx` | Trust Desk (`requests` tab) | Channel picker (SFTP, API, Email, Letter), verification field checkboxes, notes. |
| **Record Manual Bank Evidence**| `TrustVerificationDeskPage.tsx` | Trust Desk (`requests` tab) | Bank confirmation letter ref, date, match outcome (Match/Discrepancy), verified amount, verified maturity. |
| **Simulate Bank Dispatch** | `TrustVerificationDeskPage.tsx` | Trust Desk (`requests` tab) | Scenario selector (Normal match, Discrepant match, Timeout) for live demo testing. |
| **Create Successor Renewal** | `RenewalLineageSection.tsx` | Instrument Detail (`lineage` tab) | Pre-filled terms from predecessor, new FDR ref #, amount, adjusted dates, continuity justification. |
| **Lineage Link Correction** | `RenewalLineageSection.tsx` | Instrument Detail (`lineage` tab) | Action (Deactivate link, Supersede, Update reason), correction rationale. |
| **Create Scrutiny Observation**| `InstrumentDetailPage.tsx` | Instrument Detail (`observations`) | Observation text, category (General, Lien, Maturity, Trust), internal-only toggle. |
| **Amend Observation** | `InstrumentDetailPage.tsx` | Instrument Detail (`observations`) | Revised text, mandatory amendment reason (creates audit supersession). |
| **Provision User Account** | `UserAdminPage.tsx` | User Admin Page | Full name, email, password, role dropdown, college selector, must-rotate toggle. |
| **Admin Password Reset** | `UserAdminPage.tsx` | User Admin Page | 1-Click generated temporary password with clipboard copy button. |
| **Deactivate Institution** | `InstitutionsPage.tsx` | Institutions Page | Suspension reason text area and confirmation buttons. |
| **Inspect Event Cryptography** | `AuditPage.tsx` | Audit Ledger Page | SHA-256 block hash, previous hash, IP, trace ID, side-by-side JSON before/after state diff. |

---

## 5. Comprehensive Use-Case & Workflow Architecture

### Use Case 1: Recording & Pledging a New Security Deposit
1. Institution Nodal Officer or Bureau Scrutiny Officer clicks **"Record FDR Instrument"**.
2. User fills in: Issuing Bank (selected from top PSU/scheduled banks), Branch, Certificate Ref Number, Principal Amount in INR, Issue Date, Maturity Date (defaults to 5 years), and AICTE Joint Pledge Lien details.
3. **Duplicate Detection System** activates on reference number input. If an existing active FDR matches, a prominent warning alert appears showing existing matching records to prevent duplicate pledging.
4. User clicks **Save**: Record is created in `REGISTERED` administrative status with initial `L0_DECLARED` trust tier.
5. Tamper-evident ledger generates an immutable creation block hash.

### Use Case 2: Document Ingestion, OCR Verification & L1 Promotion
1. User opens `/instruments/:id` and navigates to the **Documents Tab**.
2. User uploads scanned PDF / image of the FDR certificate and Joint Lien Undertaking.
3. System runs OCR extraction (Module 2) and compares extracted fields against declared fields.
4. If fields match within tolerance thresholds, instrument automatically promotes to `L1_DOCUMENT_CONSISTENT`.
5. If discrepancies are found (e.g., amount mismatch or missing lien clause), an algorithmic finding is logged and pushed to the **Review Queue** (`/findings/queue`).

### Use Case 3: Regulatory Scrutiny Officer Verification (L2 Promotion)
1. Scrutiny Officer navigates to **Trust & Verification Desk** (`/verification/:id`).
2. Officer inspects the document scan side-by-side with OCR provenance.
3. Officer clicks **"L2 Officer Decision"**, enters evidence document version and attestation notes.
4. Officer confirms: Instrument elevates to `L2_OFFICER_VERIFIED`.
5. Audit event recorded with officer user ID and timestamp.

### Use Case 4: Bank Confirmation & SFTP Reconciliation (L3 Promotion)
1. Bureau dispatches batch verification requests to bank via **SFTP Host-to-Host** or **Direct API**.
2. Inbound reconciliation feed returns a validated match on certificate number, amount, maturity date, and active lien status.
3. System records the bank response ID and elevates instrument to `L3_BANK_CONFIRMED`.
4. If conflicting bank evidence arrives (e.g., deposit prematurely closed or lien not marked), the system flags the conflict and allows the officer to execute a **Trust Downgrade** back to L1 or L0 with mandatory justification.

### Use Case 5: Automated Maturity Monitoring & Renewal Lineage
1. Command Center monitors all deposits against the 90-day expiration window (`/command-center`).
2. Automated scheduler triggers milestone notifications (T-90, T-60, T-30, T-15, T-0) alerting the college nodal officer.
3. Upon renewal, the officer opens `/instruments/:id` → **Lineage Tab** → **"Record Successor / Renewal"**.
4. The system pre-fills the successor deposit modal, checks **Deposit Continuity** (ensuring no reduction in pledged capital or uncollateralized calendar gaps), and links the two certificates into a visual multi-hop lineage tree.

### Use Case 6: FDR Release & Refund Application Workflow
1. Institution completes educational mandate / closure and applies for deposit release at `/release`.
2. Institution user selects target instrument and enters statutory justification. Case is created in `SUBMITTED` state.
3. Scrutiny Officer inspects the case at `/release/:id`. The automated **Readiness Assessment Engine** checks all prerequisites (e.g., minimum statutory tenure elapsed, clean verification status, no pending liabilities).
4. If prerequisites pass, officer marks case `READY_FOR_AUTHORITY`.
5. Competent Authority reviews the dossier, evidence pack, and signs the release order (`APPROVED` → `RELEASE_ORDER_RECORDED`).

### Use Case 7: Independent Audit & Ledger Integrity Verification
1. Independent Auditor logs in and navigates to `/audit`.
2. Auditor clicks **"Verify Hash Chain Integrity"**.
3. Cryptographic engine iterates every block in the ledger, recalculating SHA-256 hashes against parent block hashes.
4. Screen displays verified block count and confirms zero tamper events.
5. Auditor exports an official compliance PDF or inspects JSON diffs for specific transactions.

---

## 6. Blueprint & Prompt Guide for AI Design Tools (v0 / Lovable / Figma)

When feeding this specification into an AI design generator or Figma prompt, structure your prompts using the following layout hierarchy:

### Recommended Page Layout Architecture
- **Desktop Grid:** Fluid 12-column grid, max-width `1440px`, gutters `24px`.
- **Navigation:**
  - Left Sidebar: `w-64` (256px fixed width, dark theme `#0f172a`, sticky full-height).
  - Top Header: `h-16` (64px fixed height, light theme `#ffffff`, border-b `#e2e8f0`, sticky top).
  - Main Canvas: Responsive padding `p-6` to `p-8` with slate-50 (`#f8fafc`) neutral canvas background.

### Component Design Style Guide
- **Cards:** Rounded-2xl (`16px`), white background, subtle border (`#e2e8f0`), soft shadow (`shadow-xs` / `shadow-sm`).
- **Typography:** Modern clean sans-serif (Inter, Outfit, or Plus Jakarta Sans).
  - Headings: Bold / Extra-bold (`font-bold`, `tracking-tight`, slate-900).
  - Monospace Data: Monospace font (JetBrains Mono / Roboto Mono) for FDR numbers, hashes, and dates.
- **Pills & Badges:** Rounded-full or rounded-md, uppercase font-semibold, 10px-11px text size.
- **Interactive States:** Distinct hover rings, subtle scale transitions, skeleton loading states, clear empty-state illustrations, and explicit error banners with retry triggers.
