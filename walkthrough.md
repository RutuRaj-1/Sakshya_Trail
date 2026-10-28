# SAKSHYATRAIL — PROTOTYPE DEMONSTRATION WALKTHROUGH & VIDEO PRODUCTION PLAN

**Platform:** SakshyaTrail — Security Deposit & Fixed Deposit Receipt (FDR) Lifecycle Integrity Platform  
**Smart India Hackathon 2026:** Problem Statement 26265 (Streamline of Security Deposit / FDR Portal)  
**Target Video Duration:** 4 Minutes 45 Seconds (285 Seconds) — Target Window: 4:30 to 5:00  
**Production Format:** High-Resolution Screen Recording of Live Running Application with Synchronized Voiceover  
**Repository Working Revision:** Commit `df430f2` (Verified & Remediated)  
**Authoritative Environments:** Frontend: `http://localhost:5173` | Backend: `http://127.0.0.1:8000`

---

## 1. Executive Overview & Narrative Arc

### 1.1 The Narrative Arc
The demonstration video communicates a rigorous, evidence-first regulatory story:
$$\text{Evidence Submission} \longrightarrow \text{Explainable Scrutiny} \longrightarrow \text{Lifecycle Monitoring} \longrightarrow \text{Controlled Release} \longrightarrow \text{Auditable Decision}$$

1. **The Administrative Problem:** Over 10,000 regulatory technical institutions deposit thousands of crores in Fixed Deposit Receipts (FDRs) with AICTE and state authorities. Paper certificates, manual PDF inspection, opaque renewals, unmonitored maturities, and fragmented release authorizations lead to high administrative overhead, compliance blindspots, and potential revenue leakages.
2. **The SakshyaTrail Solution:** A civic-tech financial-governance platform enforcing a strict **Nine-Stage Lifecycle Workflow**, an append-only **Trust Ledger (L0–L3)**, **Server-Side Release-Readiness Guardrails**, and an immutable **SHA-256 Hash-Chained Audit Ledger**.
3. **Institutional Design Language:** Authoritative, high-contrast, rectangular enterprise aesthetics (`border-radius: 0px`, `IBM Plex Sans`, `IBM Plex Mono`, and institutional navy `#123B5D` & regulatory teal `#0F766E`).

### 1.2 Video Production Specifications
- **Display Resolution:** 1920 × 1080 (1080p Full HD) or 2560 × 1440 (2K) at 60 FPS.
- **Browser State:** Google Chrome in a dedicated clean guest/incognito window, bookmarks bar hidden, zoom at exactly 100%.
- **Audio Delivery:** Dedicated voiceover recorded on a studio-quality condenser microphone, normalized to -14 LUFS, aligned with recorded visual cuts.
- **Authentication Method:** One-click synthetic demo account buttons on the `/login` screen (zero credential exposure, zero typed secrets on camera).

---

## 2. Master Demonstration Timeline (4:45 Total)

| Act | Scene | Scene Title | Timecode | Duration | Target Route | Actor Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Act 1** | **1.1** | Public Landing Page & Regulatory Motivation | `0:00 – 0:35` | 35s | `/` | Anonymous / Public |
| **Act 2** | **2.1** | Safe Demo Login & Authentication Shell | `0:35 – 0:50` | 15s | `/login` $\rightarrow$ `/dashboard` | System Admin |
| **Act 2** | **2.2** | Statutory FDR Registry & 9-Stage Lifecycle | `0:50 – 1:25` | 35s | `/instruments` $\rightarrow$ `/instruments/:id` | System Admin |
| **Act 2** | **2.3** | Documents Evidence Vault & Scrutiny Engine | `1:25 – 1:45` | 20s | `/documents` | Scrutiny Officer |
| **Act 2** | **2.4** | Trust Desk & Release Gate Readiness Blocker | `1:45 – 2:10` | 25s | `/release/:id` | Scrutiny Officer |
| **Act 3** | **3.1** | Scrutiny Officer Workspace & Review Queue | `2:10 – 2:35` | 25s | `/findings/queue` | Scrutiny Officer |
| **Act 3** | **3.2** | Competent Authority Statutory Sanction Desk | `2:35 – 2:55` | 20s | `/dashboard` $\rightarrow$ `/release` | Competent Authority |
| **Act 3** | **3.3** | Finance Officer Release Order Recording | `2:55 – 3:20` | 25s | `/dashboard` $\rightarrow$ `/release/:id` | Finance Officer |
| **Act 4** | **4.1** | Portfolio Monitoring & Renewal Lineage | `3:20 – 3:45` | 25s | `/monitoring` | System Admin |
| **Act 4** | **4.2** | Executive Command Center & SHA-256 Audit | `3:45 – 4:10` | 25s | `/command-center` $\rightarrow$ `/audit` | System Admin |
| **Act 5** | **5.1** | Core Technical USPs & Offline Hackathon Plan | `4:10 – 4:45` | 35s | `/` or `/dashboard` | System Admin |

---

## 3. Scene-by-Scene Production Plan

---

### Scene 1.1: Public Landing Page & Regulatory Motivation
- **Timecode:** `0:00 – 0:35` (Duration: 35 seconds)
- **Purpose:** Establish the institutional context, introduce Problem Statement 26265, and highlight the core mission of SakshyaTrail.
- **Starting Route:** `http://localhost:5173/`
- **Precondition & Role:** No active session (logged out). Clean viewport.
- **Step-by-Step Screen Actions:**
  1. `0:00 – 0:10`: Screen starts static at the top of the landing page showing the SakshyaTrail wordmark, `SIH 26265` badge, headline *"From FDR Submission to Release — Every Step Accountable."*, and the zero-radius preview card.
  2. `0:10 – 0:22`: Smoothly scroll down past the **Trust Principles Strip** to the **Nine Statutory Lifecycle Stages** section.
  3. `0:22 – 0:30`: Hover briefly across the **4-Tier Trust Ledger** card (`L0 Declared` to `L3 Bank Confirmed`).
  4. `0:30 – 0:35`: Smoothly scroll back to the top and hover over the rectangular **Access Portal** button. Click to navigate.
- **Focus UI Elements:**
  - Header badge: `SIH 26265`
  - Headline: *"From FDR Submission to Release — Every Step Accountable."*
  - Statutory 9-Stage flow tiles.
  - 4-Tier Trust Ledger explanation.
- **Intended Visual Result:** Crisp square-cornered enterprise aesthetics with high credibility. Zero animation jitter.
- **Voiceover Narration:**
  > *"Every year, regulatory authorities like the All India Council for Technical Education manage thousands of crores in Fixed Deposit Receipts pledged as security deposits by technical institutions. Yet today, this critical process remains burdened by physical certificates, manual PDF verification, untracked maturity windows, and fragmented release authorizations. Welcome to SakshyaTrail — a unified, regulatory-grade lifecycle integrity platform built for SIH Problem Statement 26265. SakshyaTrail replaces paper friction with an evidence-first, 9-stage statutory workflow, automated discrepancy detection, and an immutable audit trail."*
- **Transition to Next Scene:** Click **Access Portal** $\rightarrow$ instant transition to `/login`.
- **Common Failure Risks & Recovery:**
  - *Risk:* Page loads with cached scroll position.
  - *Recovery:* Press `Ctrl + F5` or `Home` key before recording to ensure start at exact top.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] Browser at 100% zoom.
  - [ ] No bookmarks bar visible.
  - [ ] Mouse cursor moves smoothly with deliberate pauses.

---

### Scene 2.1: Safe Demo Login & Authentication Shell
- **Timecode:** `0:35 – 0:50` (Duration: 15 seconds)
- **Purpose:** Demonstrate secure RBAC authentication without exposing typed credentials, showing the 1-click evaluator account selector.
- **Starting Route:** `http://localhost:5173/login`
- **Precondition & Role:** Logged out.
- **Step-by-Step Screen Actions:**
  1. `0:35 – 0:40`: Display the login card. Point cursor to the **SIH Evaluator Demo Accounts** grid.
  2. `0:40 – 0:45`: Click the **System Admin** button (`admin@aicte-india.org`). The email and masked password fields autofill instantly.
  3. `0:45 – 0:50`: Click **Sign In to SakshyaTrail**. Page transitions to the System Admin Cockpit (`/dashboard`).
- **Focus UI Elements:**
  - Demo accounts grid with 7 canonical roles.
  - Security disclaimer: *"Strictly authorized access. All sessions are signed & SHA-256 hash-chain audited."*
  - Rectangular `Sign In` button.
- **Intended Visual Result:** Zero credentials typed manually. Instant response from `/api/v1/auth/token`.
- **Voiceover Narration:**
  > *"To ensure maximum transparency during evaluation, SakshyaTrail implements a multi-tenant role-based access control engine with seven distinct statutory roles. We sign in as the AICTE System Administrator using isolated synthetic demonstration credentials."*
- **Transition to Next Scene:** Redirect to `/dashboard`.
- **Common Failure Risks & Recovery:**
  - *Risk:* Authentication takes longer than 1 second.
  - *Recovery:* Backend server is warm. Ensure SQLite DB is active.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] No browser autofill popups or password manager dropdowns appear.

---

### Scene 2.2: Statutory FDR Registry & 9-Stage Lifecycle Tracker
- **Timecode:** `0:50 – 1:25` (Duration: 35 seconds)
- **Purpose:** Showcase the core statutory instrument registry and examine an active FDR record exhibiting the Nine-Stage Lifecycle Tracker.
- **Starting Route:** `http://localhost:5173/dashboard`
- **Precondition & Role:** `SYSTEM_ADMIN` session active.
- **Step-by-Step Screen Actions:**
  1. `0:50 – 0:55`: Click **FDR Submission & Registry** on the sidebar to open `/instruments`.
  2. `0:55 – 1:05`: View the registry showing active records. Filter dropdowns show all statuses and trust levels. Focus on record **`DEMO-FDR-RELEASED-001`** (State Bank of India, ₹25,00,000, `L3 — Bank Confirmed`).
  3. `1:05 – 1:12`: Click **Details** on `DEMO-FDR-RELEASED-001` to navigate to `/instruments/b12f6bd2-e5eb-4c60-8bd9-d8cfe17cf7f5`.
  4. `1:12 – 1:25`: Pan down to the **Statutory Lifecycle Progress** container. Point to the 9 horizontal stage boxes: Stage 01 Submission, Stage 02 Documents, Stage 03 Validation, Stage 04 Scrutiny, Stage 05 Bank Verification, Stage 06 Monitoring, Stage 07 Renewal, Stage 08 Release Readiness, Stage 09 Maker-Checker Decision. Focus on the Stage 9 sub-events breakdown (9a Sanction, 9b Release Order, 9c Bank Confirmation, 9d Ledger Closure).
- **Focus UI Elements:**
  - Registry stat cards: Total Deposit Portfolio, Active Compliance, Expiring within 90 Days.
  - Instrument detail badge: `L3 — Bank Confirmed` (`#0F766E`).
  - Nine-Stage Horizontal Timeline with clear status colors.
  - Stage 9 Operational Sub-Events Progress box.
- **Intended Visual Result:** Perfectly rectangular stage cards, clean typography, unambiguous distinction between administrative status and trust level.
- **Voiceover Narration:**
  > *"At the heart of the platform is the Statutory FDR Registry, managing active deposits across all affiliated entities. Opening a registered deposit reveals SakshyaTrail's Nine-Stage Lifecycle Architecture. Rather than treating deposits as static records, our engine enforces statutory checkpoints across submission, document extraction, rule validation, scrutiny, bank confirmation, maturity monitoring, renewal lineage, release readiness, and authorized discharge. Notice Stage 9 — statutory release is decomposed into four discrete, non-bypassable sub-events: competent authority sanction, finance officer release order recording, bank disbursement confirmation, and permanent cryptographic closure."*
- **Transition to Next Scene:** Click **Document Upload & Evidence** in sidebar $\rightarrow$ `/documents`.
- **Common Failure Risks & Recovery:**
  - *Risk:* Timeline displays incorrect active stage.
  - *Recovery:* `DEMO-FDR-RELEASED-001` has completed all 9 stages; Stage 9 will render with green completion ticks.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] Hover gently over Stage 01 through 09 to demonstrate hover tooltip hints.

---

### Scene 2.3: Documents Evidence Vault & Scrutiny Engine
- **Timecode:** `1:25 – 1:45` (Duration: 20 seconds)
- **Purpose:** Demonstrate evidence provenance, document versioning, and the deterministic discrepancy engine.
- **Starting Route:** `http://localhost:5173/documents`
- **Precondition & Role:** `SYSTEM_ADMIN` or `SCRUTINY_OFFICER`.
- **Step-by-Step Screen Actions:**
  1. `1:25 – 1:33`: Open Documents Vault. Select instrument `DEMO-FDR-CORRECTION-001` or `DEMO-FDR-SBI-2024-88091`.
  2. `1:33 – 1:40`: Display the document version history with cryptographic SHA-256 checksums, upload timestamps, and scan status.
  3. `1:40 – 1:45`: Show the extracted structured fields table comparing declared values against document-extracted values (account number, deposit amount, maturity date, joint-lien clause).
- **Focus UI Elements:**
  - SHA-256 document hash display in `IBM Plex Mono`.
  - Extracted fields table with discrepancy indicators.
  - Document version badge (`v1`, `v2`).
- **Intended Visual Result:** Clear side-by-side verification table showing declared vs extracted values.
- **Voiceover Narration:**
  > *"In our Documents and Evidence Vault, every uploaded fixed deposit receipt is assigned a SHA-256 cryptographic hash and processed by our deterministic extraction engine. Field-level provenance compares declared values against certificate evidence. If an institution declares twenty-five lakhs but the instrument reflects twenty lakhs, or if the mandatory joint-lien clause is missing, the engine automatically flags the discrepancy and triggers an explainable finding."*
- **Transition to Next Scene:** Navigate to `/release` in sidebar.
- **Common Failure Risks & Recovery:**
  - *Risk:* PDF preview fails to render.
  - *Recovery:* Focus on the structured extracted metadata table and validation indicators, which load instantly from SQLite.
- **Verification Status:** Implemented & Verified.
- **Recording Checklist:**
  - [ ] Point cursor to the SHA-256 hash string to emphasize data integrity.

---

### Scene 2.4: Trust Desk & Release Gate Readiness Blocker
- **Timecode:** `1:45 – 2:10` (Duration: 25 seconds)
- **Purpose:** Demonstrate the automated Release Gate evaluation and how open findings or immature terms strictly block discharge.
- **Starting Route:** `http://localhost:5173/release`
- **Precondition & Role:** Active session.
- **Step-by-Step Screen Actions:**
  1. `1:45 – 1:52`: Open `/release` showing the Release Cases list. Focus on case **`REL-DEMO-BLOCKED-001`** on instrument `DEMO-FDR-BLOCKED-001`.
  2. `1:52 – 2:02`: Click into the case detail (`/release/a125a939-8774-4e13-909f-def89e9c3a47`). Show the **Automated Release Readiness Assessment** panel.
  3. `2:02 – 2:10`: Highlight the red blockers: `BLOCKED` status, Lock-in Period Not Elapsed, Open Scrutiny Finding. Point out that the statutory approve button is disabled or blocked server-side.
- **Focus UI Elements:**
  - Case Number: `REL-DEMO-BLOCKED-001`
  - Automated Check Results: `CHK-01` (Lock-in Elapsed - FAIL), `CHK-02` (Zero Open Findings - FAIL).
  - Prominent Warning Banner: *"Release Gate Blocked — Cannot proceed to statutory sanction."*
- **Intended Visual Result:** High-visibility amber/red square containers clearly signaling why release cannot occur.
- **Voiceover Narration:**
  > *"When an institution applies for deposit release or refund, SakshyaTrail's Release Gate enforces strict server-side invariants. In case REL-DEMO-BLOCKED-001, the system automatically evaluates four mandatory readiness criteria. Because the statutory lock-in period has not elapsed and an unresolved validation finding remains open, the assessment outcome is strictly BLOCKED. Even an administrator cannot bypass these statutory guardrails."*
- **Transition to Next Scene:** Log out via Header and prepare role-switching demonstration.
- **Common Failure Risks & Recovery:**
  - *Risk:* Blocker list appears empty.
  - *Recovery:* Case `REL-DEMO-BLOCKED-001` has pre-seeded check results `CHK-01` and `CHK-02` with `FAIL` status.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] Verify red/amber badge colors stand out crisply against the white panel.

---

### Scene 3.1: Scrutiny Officer Workspace & Review Queue
- **Timecode:** `2:10 – 2:35` (Duration: 25 seconds)
- **Purpose:** Demonstrate the first specialized role — Scrutiny Officer Verma reviewing discrepancies in the priority-ranked review queue.
- **Starting Route:** `http://localhost:5173/login` $\rightarrow$ `/findings/queue`
- **Precondition & Role:** Log in as **Scrutiny Officer** (`scrutiny.verma@aicte-india.org`).
- **Step-by-Step Screen Actions:**
  1. `2:10 – 2:15`: On `/login`, click 1-click button **Scrutiny Officer**. Click **Sign In**.
  2. `2:15 – 2:22`: Land on the Scrutiny Desk (`/dashboard`). Show role badge: `SCRUTINY_OFFICER`. Note the tailored navigation: Scrutiny Queue, Verification Desk, Review History.
  3. `2:22 – 2:30`: Click **Validation & Discrepancies** to open `/findings/queue`. Display the priority-scored finding cards.
  4. `2:30 – 2:35`: Highlight a critical finding card (`CRITICAL` - Discrepant Deposit Principal). Show the structured actions: *Verify*, *Request Correction*, *Dismiss*.
- **Focus UI Elements:**
  - User profile in top header: `Officer Ramesh Verma [DEMO]` | `SCRUTINY_OFFICER`.
  - Severity badge: `CRITICAL` (Red) / `HIGH` (Amber).
  - Priority score chip: `Score: 85`.
- **Intended Visual Result:** Scrutiny-focused workspace with zero administrative bloat.
- **Voiceover Narration:**
  > *"Role separation is vital for regulatory integrity. Logging in as Scrutiny Officer Ramesh Verma, the interface adapts specifically to review duties. The Review Queue aggregates all algorithmic findings, ranked by rule severity and institutional priority. Scrutiny officers can examine document discrepancies, request institutional corrections, or escalate issues to the bank verification desk without possessing the statutory authority to release funds."*
- **Transition to Next Scene:** Log out and prepare Competent Authority sign-in.
- **Common Failure Risks & Recovery:**
  - *Risk:* Review queue takes a moment to load.
  - *Recovery:* Wait 1 second before scrolling. Cards will render cleanly.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] Confirm top header clearly displays `SCRUTINY_OFFICER`.

---

### Scene 3.2: Competent Authority Statutory Sanction Desk
- **Timecode:** `2:35 – 2:55` (Duration: 20 seconds)
- **Purpose:** Demonstrate the second specialized role — Competent Authority statutory sign-off.
- **Starting Route:** `http://localhost:5173/login` $\rightarrow$ `/dashboard`
- **Precondition & Role:** Log in as **Competent Authority** (`authority.member@aicte-india.org`).
- **Step-by-Step Screen Actions:**
  1. `2:35 – 2:40`: On `/login`, click **Competent Authority**. Click **Sign In**.
  2. `2:40 – 2:47`: Land on the Authority Cockpit. Top header displays `COMPETENT_AUTHORITY` in royal purple. Notice the navigation differences: No user admin, but Statutory Release Sanction queue is prominent.
  3. `2:47 – 2:55`: Open `/release`. Point out that the Competent Authority possesses the exclusive statutory sanction capability once Release Gate criteria pass.
- **Focus UI Elements:**
  - Header badge: `COMPETENT_AUTHORITY` (Purple).
  - Authority Cockpit summary: Sanction Requests Pending, Approved Releases, Blocked Cases.
  - Exclusive statutory approval affordance.
- **Intended Visual Result:** Clear visual distinction from the Scrutiny Officer view.
- **Voiceover Narration:**
  > *"Next, we transition to the Competent Authority. This role represents the statutory decision-maker. Notice the distinct scope: authority members cannot create deposit records or alter verification findings. Their sole purview is evaluating fully scrutinized cases and recording statutory approval decisions backed by formal council meeting minutes."*
- **Transition to Next Scene:** Log out and prepare Finance Officer sign-in.
- **Common Failure Risks & Recovery:**
  - *Risk:* Session token retains prior role.
  - *Recovery:* Clicking the header logout button invokes `authStore.logout()` which purges all local storage tokens.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] Emphasize the purple `COMPETENT_AUTHORITY` badge.

---

### Scene 3.3: Finance Officer Release Order Recording
- **Timecode:** `2:55 – 3:20` (Duration: 25 seconds)
- **Purpose:** Demonstrate the third specialized role — Finance Officer executing Stage 9b order recording.
- **Starting Route:** `http://localhost:5173/login` $\rightarrow$ `/dashboard`
- **Precondition & Role:** Log in as **Finance Officer** (`finance.officer@aicte-india.org`).
- **Step-by-Step Screen Actions:**
  1. `2:55 – 3:00`: Click **Finance Officer** on `/login`. Click **Sign In**.
  2. `3:00 – 3:08`: Land on the Finance Workspace. Header displays `FINANCE_OFFICER`. Navigation highlights Release Orders, Bank Advice Reconciliation, and Disbursal Logs.
  3. `3:08 – 3:15`: Open case detail `/release/7af4a769-51e4-4c09-8c5c-388c4a0d0723` (`REL-DEMO-CLOSED-001`).
  4. `3:15 – 3:20`: Show the **Finance Release Order Recording** section: Sanction order number, payment reference, bank IFSC, and voucher attachment.
- **Focus UI Elements:**
  - Header badge: `FINANCE_OFFICER`.
  - Finance order details: Voucher number, Payment Advice reference.
  - Strict maker-checker invariant banner.
- **Intended Visual Result:** Financial ledger layout with tabular monetary amounts.
- **Voiceover Narration:**
  > *"Finally, we sign in as the Finance Officer. Under regulatory maker-checker governance, neither the scrutiny officer nor the competent authority can disburse funds. The Finance Officer enters official payment order numbers, bank disbursement advice references, and reconciliation proofs. Backend permissions enforce that only this role can execute Stage 9b order recording, preventing fraudulent or unilateral deposit liquidations."*
- **Transition to Next Scene:** Log back in as `admin@aicte-india.org` for global operational oversight.
- **Common Failure Risks & Recovery:**
  - *Risk:* Attempting to record an order on a non-approved case.
  - *Recovery:* Show the pre-seeded completed case `REL-DEMO-CLOSED-001` where the order is already recorded.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] Show the maker-checker banner explaining role boundaries.

---

### Scene 4.1: Portfolio Monitoring & Renewal Lineage
- **Timecode:** `3:20 – 3:45` (Duration: 25 seconds)
- **Purpose:** Demonstrate lifecycle monitoring, the 90-day maturity window, and Stage 7 Predecessor-Successor Renewal Lineage.
- **Starting Route:** `http://localhost:5173/monitoring`
- **Precondition & Role:** `SYSTEM_ADMIN` session active.
- **Step-by-Step Screen Actions:**
  1. `3:20 – 3:28`: Click **Lifecycle Monitoring** $\rightarrow$ `/monitoring`. Display the maturity timeline showing deposits categorized by maturity: Overdue, Expiring in 30 Days, Expiring in 90 Days.
  2. `3:28 – 3:35`: Point out **`DEMO-FDR-HDFC-2026-11029`** (Maturity in 45 days, amber tag `Maturity Review Required`).
  3. `3:35 – 3:45`: Scroll to the **Renewal & Successor Lineage** section. Show paired instruments: Predecessor `DEMO-FDR-PREDECESSOR-001` linked to Successor `DEMO-FDR-SUCCESSOR-001` with status `CONTINUOUS` and relationship `RENEWAL`.
- **Focus UI Elements:**
  - Maturity category tabs: `Approaching (90d)`, `Critical (30d)`, `Matured / Overdue`.
  - Renewal Lineage tree showing Predecessor $\rightarrow$ Successor linkage.
  - Continuity indicator: `CONTINUOUS` (Green badge).
- **Intended Visual Result:** Immediate visual clarity on which deposits require institutional renewal notices.
- **Voiceover Narration:**
  > *"Long-term deposit governance requires continuous surveillance. The Lifecycle Monitoring workspace tracks instruments against statutory maturity horizons. Instruments entering the 90-day window trigger automated renewal notifications. In Stage 7, SakshyaTrail establishes complete Predecessor-Successor Lineage. When an institution renews an FDR, the successor deposit is cryptographically linked to its predecessor, guaranteeing unbroken continuity of pledged security without duplicate counting."*
- **Transition to Next Scene:** Click **Overview** in sidebar $\rightarrow$ `/command-center`.
- **Common Failure Risks & Recovery:**
  - *Risk:* Lineage table displays empty state.
  - *Recovery:* Lineage records are pre-seeded linking `DEMO-FDR-PREDECESSOR-001` to `DEMO-FDR-SUCCESSOR-001`.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] Point cursor to the predecessor-successor arrow icon.

---

### Scene 4.2: Executive Command Center & SHA-256 Audit Ledger
- **Timecode:** `3:45 – 4:10` (Duration: 25 seconds)
- **Purpose:** Showcase the high-level Command Center metrics and the tamper-evident cryptographic audit ledger.
- **Starting Route:** `http://localhost:5173/command-center` $\rightarrow$ `/audit`
- **Precondition & Role:** `SYSTEM_ADMIN` session active.
- **Step-by-Step Screen Actions:**
  1. `3:45 – 3:55`: Open `/command-center`. Highlight the aggregated executive dashboard: ₹125+ Crores Total Portfolio Value, Trust Level Distribution (L0 through L3), and Month-by-Month Maturity Load Chart.
  2. `3:55 – 4:02`: Click **Audit Ledger Closure** or navigate to `/audit`.
  3. `4:02 – 4:10`: Display the **Audit Explorer**. Point out the live telemetry badge: `CHAIN INTACT (PASS)`. Show consecutive audit events with SHA-256 current and previous hashes forming an unbreakable Merkle-style chain.
- **Focus UI Elements:**
  - Command Center summary metrics and rectangular maturity bar chart.
  - Audit status chip: `SHA-256 Chain Intact: VERIFIED`.
  - Audit log table columns: Event Type, Actor, Target Reference, SHA-256 Hash.
- **Intended Visual Result:** Authoritative, high-density regulatory dashboard followed by cryptographic proof of ledger integrity.
- **Voiceover Narration:**
  > *"For council leadership, the Command Center provides real-time portfolio visibility across active deposits, trust levels, and regional distribution. Underpinning every action is SakshyaTrail's tamper-evident audit ledger. Every login, document upload, scrutiny finding, and release authorization generates an immutable event signed with a cryptographic SHA-256 hash linked to the prior event. If any record in the database is modified out-of-band, the verification algorithm immediately flags the broken chain."*
- **Transition to Next Scene:** Smooth transition to concluding slide or return to Landing Page (`/`).
- **Common Failure Risks & Recovery:**
  - *Risk:* Audit integrity verification shows calculating state.
  - *Recovery:* The audit query service returns cached hash chain status within 15ms.
- **Verification Status:** Implemented & Verified in live browser.
- **Recording Checklist:**
  - [ ] Confirm green `CHAIN INTACT` indicator is clearly visible in the recording frame.

---

### Scene 5.1: Core Technical USPs & Offline Hackathon Plan
- **Timecode:** `4:10 – 4:45` (Duration: 35 seconds)
- **Purpose:** Summarize the unique value propositions, differentiate from generic portal solutions, and present the credible offline hackathon roadmap.
- **Starting Route:** `http://localhost:5173/` (Landing Page)
- **Precondition & Role:** Concluding screen framing.
- **Step-by-Step Screen Actions:**
  1. `4:10 – 4:25`: Return to the Landing Page hero view. Slowly pan across the core value proposition pillars.
  2. `4:25 – 4:45`: Display closing title card or framing with SakshyaTrail descriptor, AICTE problem statement reference, and offline roadmap highlights.
- **Focus UI Elements:**
  - SakshyaTrail logo and wordmark.
  - Problem Statement ID: `SIH26265`.
  - Closing summary graphics / bullet overlay.
- **Intended Visual Result:** Confident, polished, highly professional closing.
- **Voiceover Narration:**
  > *"To summarize: SakshyaTrail transforms FDR governance through five key architectural pillars: first, an evidence-first nine-stage statutory lifecycle; second, an explainable trust ledger separating declared data from verified facts; third, server-side release gates with non-bypassable maker-checker controls; fourth, continuous renewal lineage tracking; and fifth, a tamper-evident cryptographic audit trail. During the upcoming offline hackathon, our team will integrate direct SFMS banking gateway webhooks, expand multilingual institutional notifications, and deploy hardware-backed digital signature tokens. Thank you — SakshyaTrail: Streamlining Security Deposits with Total Accountability."*
- **Transition to Next Scene:** Video ends cleanly at `4:45` with fade to black.
- **Common Failure Risks & Recovery:**
  - *Risk:* Video ends abruptly.
  - *Recovery:* Leave 2 seconds of ambient silence after the final word before stopping the video capture.
- **Verification Status:** Implemented & Verified.
- **Recording Checklist:**
  - [ ] Video ends between 4:30 and 5:00.

---

## 4. Complete Voiceover Script (Aligned by Timecode)

```
[0:00 - 0:35 | ACT 1: MOTIVATION & PROBLEM]
"Every year, regulatory authorities like the All India Council for Technical Education 
manage thousands of crores in Fixed Deposit Receipts pledged as security deposits by 
technical institutions. Yet today, this critical process remains burdened by physical 
certificates, manual PDF verification, untracked maturity windows, and fragmented release 
authorizations. Welcome to SakshyaTrail — a unified, regulatory-grade lifecycle integrity 
platform built for SIH Problem Statement 26265. SakshyaTrail replaces paper friction with 
an evidence-first, 9-stage statutory workflow, automated discrepancy detection, and an 
immutable audit trail."

[0:35 - 0:50 | ACT 2.1: DEMO AUTHENTICATION]
"To ensure maximum transparency during evaluation, SakshyaTrail implements a multi-tenant 
role-based access control engine with seven distinct statutory roles. We sign in as the 
AICTE System Administrator using isolated synthetic demonstration credentials."

[0:50 - 1:25 | ACT 2.2: FDR REGISTRY & 9-STAGE LIFECYCLE]
"At the heart of the platform is the Statutory FDR Registry, managing active deposits across 
all affiliated entities. Opening a registered deposit reveals SakshyaTrail's Nine-Stage 
Lifecycle Architecture. Rather than treating deposits as static records, our engine enforces 
statutory checkpoints across submission, document extraction, rule validation, scrutiny, 
bank confirmation, maturity monitoring, renewal lineage, release readiness, and authorized 
discharge. Notice Stage 9 — statutory release is decomposed into four discrete, non-bypassable 
sub-events: competent authority sanction, finance officer release order recording, bank 
disbursement confirmation, and permanent cryptographic closure."

[1:25 - 1:45 | ACT 2.3: EVIDENCE VAULT & SCRUTINY ENGINE]
"In our Documents and Evidence Vault, every uploaded fixed deposit receipt is assigned a 
SHA-256 cryptographic hash and processed by our deterministic extraction engine. Field-level 
provenance compares declared values against certificate evidence. If an institution declares 
twenty-five lakhs but the instrument reflects twenty lakhs, or if the mandatory joint-lien 
clause is missing, the engine automatically flags the discrepancy and triggers an explainable 
finding."

[1:45 - 2:10 | ACT 2.4: RELEASE GATE READINESS BLOCKER]
"When an institution applies for deposit release or refund, SakshyaTrail's Release Gate 
enforces strict server-side invariants. In case REL-DEMO-BLOCKED-001, the system automatically 
evaluates four mandatory readiness criteria. Because the statutory lock-in period has not 
elapsed and an unresolved validation finding remains open, the assessment outcome is strictly 
BLOCKED. Even an administrator cannot bypass these statutory guardrails."

[2:10 - 2:35 | ACT 3.1: SCRUTINY OFFICER DESK]
"Role separation is vital for regulatory integrity. Logging in as Scrutiny Officer Ramesh 
Verma, the interface adapts specifically to review duties. The Review Queue aggregates all 
algorithmic findings, ranked by rule severity and institutional priority. Scrutiny officers 
can examine document discrepancies, request institutional corrections, or escalate issues 
to the bank verification desk without possessing the statutory authority to release funds."

[2:35 - 2:55 | ACT 3.2: COMPETENT AUTHORITY SANCTION]
"Next, we transition to the Competent Authority. This role represents the statutory decision-maker. 
Notice the distinct scope: authority members cannot create deposit records or alter verification 
findings. Their sole purview is evaluating fully scrutinized cases and recording statutory approval 
decisions backed by formal council meeting minutes."

[2:55 - 3:20 | ACT 3.3: FINANCE OFFICER ORDER RECORDING]
"Finally, we sign in as the Finance Officer. Under regulatory maker-checker governance, neither 
the scrutiny officer nor the competent authority can disburse funds. The Finance Officer enters 
official payment order numbers, bank disbursement advice references, and reconciliation proofs. 
Backend permissions enforce that only this role can execute Stage 9b order recording, preventing 
fraudulent or unilateral deposit liquidations."

[3:20 - 3:45 | ACT 4.1: MONITORING & RENEWAL LINEAGE]
"Long-term deposit governance requires continuous surveillance. The Lifecycle Monitoring workspace 
tracks instruments against statutory maturity horizons. Instruments entering the 90-day window 
trigger automated renewal notifications. In Stage 7, SakshyaTrail establishes complete Predecessor-
Successor Lineage. When an institution renews an FDR, the successor deposit is cryptographically 
linked to its predecessor, guaranteeing unbroken continuity of pledged security without duplicate 
counting."

[3:45 - 4:10 | ACT 4.2: COMMAND CENTER & CRYPTOGRAPHIC AUDIT]
"For council leadership, the Command Center provides real-time portfolio visibility across active 
deposits, trust levels, and regional distribution. Underpinning every action is SakshyaTrail's 
tamper-evident audit ledger. Every login, document upload, scrutiny finding, and release 
authorization generates an immutable event signed with a cryptographic SHA-256 hash linked to 
the prior event. If any record in the database is modified out-of-band, the verification algorithm 
immediately flags the broken chain."

[4:10 - 4:45 | ACT 5: USPs & OFFLINE HACKATHON VISION]
"To summarize: SakshyaTrail transforms FDR governance through five key architectural pillars: 
first, an evidence-first nine-stage statutory lifecycle; second, an explainable trust ledger 
separating declared data from verified facts; third, server-side release gates with non-bypassable 
maker-checker controls; fourth, continuous renewal lineage tracking; and fifth, a tamper-evident 
cryptographic audit trail. During the upcoming offline hackathon, our team will integrate direct 
SFMS banking gateway webhooks, expand multilingual institutional notifications, and deploy hardware-
backed digital signature tokens. Thank you — SakshyaTrail: Streamlining Security Deposits with 
Total Accountability."
```

---

## 5. Verified Demonstration Records & Routes

| Demonstration Scenario | Exact Record Reference | Primary Database ID | Associated Institution | Expected Visible Status | Route |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fully Completed 9-Stage Deposit** | `DEMO-FDR-RELEASED-001` | `b12f6bd2-e5eb-4c60-8bd9-d8cfe17cf7f5` | Delhi Institute of Technology | `REGISTERED` / `L3 — Bank Confirmed` | `/instruments/:id` |
| **Release Blocked by Guardrail** | `DEMO-FDR-BLOCKED-001` | `c1761f4d-e192-4f9f-95f4-127579d133e2` | Delhi Institute of Technology | `REGISTERED` / `L0 — Declared` | `/instruments/:id` |
| **Active Release Case (Blocked)** | `REL-DEMO-BLOCKED-001` | `a125a939-8774-4e13-909f-def89e9c3a47` | Delhi Institute of Technology | `UNDER_REVIEW` / `BLOCKED` | `/release/:id` |
| **Completed Release Case** | `REL-DEMO-CLOSED-001` | `7af4a769-51e4-4c09-8c5c-388c4a0d0723` | Delhi Institute of Technology | `CLOSED` / `DISBURSED` | `/release/:id` |
| **Document Discrepancy Case** | `DEMO-FDR-CORRECTION-001` | `12eea5fe-e5ef-433a-bda5-3b28384f6852` | Delhi Institute of Technology | `REGISTERED` / Open Finding | `/documents` |
| **Approaching Maturity (<90d)** | `DEMO-FDR-HDFC-2026-11029` | `809148bf-4e89-4727-959b-0deed6a8862d` | MIMS Pune | Expiring within 45 days | `/monitoring` |
| **Overdue Lifecycle Case** | `DEMO-FDR-OVERDUE-001` | `75b8915b-fb5a-4fc0-9cfa-9be8e713147e` | Delhi Institute of Technology | `OVERDUE` | `/monitoring` |
| **Predecessor Renewal Deposit** | `DEMO-FDR-PREDECESSOR-001` | `c96905a9-26de-437f-8f64-8a86dd935a0a` | Delhi Institute of Technology | `RENEWED` / `L2 Verified` | `/monitoring` |
| **Successor Renewal Deposit** | `DEMO-FDR-SUCCESSOR-001` | `c0cf333c-7d51-4d2e-9bbc-e3cb7c90f8f7` | Delhi Institute of Technology | `REGISTERED` / `L1 Consistent` | `/monitoring` |

---

## 6. Role-Switching Execution Plan

To execute smooth transitions without password leaks:

```
[Start as Public / Logged Out]
  └── Landing Page (/)
        ↓ Click "Access Portal"
[Login Screen (/login)]
  ├── Click Button: "System Admin" (admin@aicte-india.org)
  │     ↓ Act 2: Instruments, Details, Documents, Release Blockers
  ├── Click Header: Logout ──→ (/login)
  ├── Click Button: "Scrutiny Officer" (scrutiny.verma@aicte-india.org)
  │     ↓ Act 3.1: Findings Queue & Review Desk
  ├── Click Header: Logout ──→ (/login)
  ├── Click Button: "Competent Authority" (authority.member@aicte-india.org)
  │     ↓ Act 3.2: Authority Sanction Desk & Approval Boundary
  ├── Click Header: Logout ──→ (/login)
  ├── Click Button: "Finance Officer" (finance.officer@aicte-india.org)
  │     ↓ Act 3.3: Finance Order Recording (Stage 9b)
  ├── Click Header: Logout ──→ (/login)
  └── Click Button: "System Admin" (admin@aicte-india.org)
        ↓ Act 4: Lifecycle Monitoring, Command Center & Audit Ledger
```

*Safety Rule:* The `fillDemoAccount` handler in `LoginPage.tsx` populates credentials into React state without making them visible in the clear. The browser password manager must be disabled to prevent "Save Password" prompts from interrupting the recording.

---

## 7. Feature Verification & Simulation Notes

To maintain absolute academic and technical credibility during SIH evaluation:

| System Capability | Implementation Reality | Safe Demonstration Phrasing | Strictly Prohibited Phrasing |
| :--- | :--- | :--- | :--- |
| **Bank Verification** | Simulated structured responses via internal verification engine (`VerificationChannel.SIMULATED`). | *"Our bank verification desk generates structured verification dispatches and processes traceable confirmation payloads."* | DO NOT say: *"We are connected live to SBI's Core Banking System via real API."* |
| **PDF Extraction** | Deterministic structured PDF extractor parsing text-based certificate markers. | *"The deterministic document extraction engine parses structured evidence markers and compares them against declared registry values."* | DO NOT say: *"Our proprietary computer vision AI performs neural OCR on photographed paper."* |
| **Maker-Checker Security** | Enforced by FastAPI server-side role dependency guards (`require_role(...)`). | *"Backend authorization invariants guarantee that only the Finance Officer role can execute Stage 9b release orders."* | DO NOT say: *"The frontend button is hidden so other users cannot click it."* |
| **Audit Ledger** | SHA-256 cryptographic hash-chain calculated and verified on SQLite/PostgreSQL. | *"The platform computes an append-only SHA-256 Merkle-style hash chain over all regulatory audit events."* | DO NOT say: *"This is deployed on the Ethereum blockchain / hyperledger fabric."* |
| **Notification Engine** | Simulated multi-channel dispatch records tracked in database. | *"Maturity notices and escalation alerts are generated and tracked in the operational dispatch ledger."* | DO NOT say: *"Real SMS and emails were delivered to institutional mobile phones."* |

---

## 8. Recording & Post-Production Checklist

### Pre-Recording Environment Setup
- [ ] **Display Setup:** Native resolution set to 1920 × 1080 (1080p Full HD) or 2560 × 1440. Scaling set to 100%.
- [ ] **Clean Profile:** Use Google Chrome in Guest Mode or a dedicated clean profile with all extensions (e.g. ad blockers, password managers) disabled.
- [ ] **Hide Distractions:** Windows Taskbar set to auto-hide. Browser bookmarks bar hidden (`Ctrl + Shift + B`).
- [ ] **Application Servers:**
  - Backend running: `http://127.0.0.1:8000` (FastAPI / uvicorn reload).
  - Frontend running: `http://localhost:5173` (Vite dev server).
- [ ] **Database State:** Verified that `fdr_sentinel.db` is populated with demo records (`DEMO-FDR-RELEASED-001`, `DEMO-FDR-BLOCKED-001`, etc.).
- [ ] **Cursor Discipline:** Move cursor with steady, deliberate pacing. Avoid rapid circular hovering, erratic gestures, or nervous clicking. Pause on each UI element for at least 1.5 seconds.

### Audio & Voiceover Production
- [ ] **Acoustic Environment:** Quiet recording space with minimal echo/reverb.
- [ ] **Hardware:** Dedicated external microphone with pop filter.
- [ ] **Voiceover Pacing:** Measured, clear, authoritative cadence (~130 to 140 words per minute).
- [ ] **Audio Post-Processing:**
  - High-pass filter at 80 Hz.
  - Mild noise gate to eliminate room tone.
  - Loudness normalization to -14 LUFS (YouTube / SIH video submission standard).
  - Zero background music, or subtle institutional ambient bed mixed at -26 dB.

### Video Editing & Synchronization
- [ ] **Cut Alignment:** Synchronize video cuts precisely to the timecodes in Section 2.
- [ ] **Captions / Callouts:** Add subtle rectangular lower-third callouts for:
  - *SIH Problem Statement 26265*
  - *Nine-Stage Lifecycle Workflow*
  - *L0–L3 Trust Ledger Architecture*
  - *Maker-Checker Separation of Duties*
  - *SHA-256 Tamper-Evident Audit Ledger*
- [ ] **Final Runtime Gate:** Total export duration must be between **4:30 and 5:00**.

---

## 9. Critical Demo Risks & Recovery Protocols

| Identified Risk | Probability | Impact | Immediate Recovery Protocol |
| :--- | :--- | :--- | :--- |
| **Accidental Session Role Spillover** | Low | Medium | Click Header **Logout** $\rightarrow$ verifies clean state before next 1-click login. |
| **Browser Password Manager Prompt** | Medium | High | Disable "Offer to save passwords" in Chrome Settings (`chrome://settings/passwords`) before recording. |
| **Slow API Response or Network Error** | Very Low | High | Backend runs locally on SQLite; keep queries within local loopback. If backend stalls, restart uvicorn process. |
| **Voiceover Finishes Before Footage** | Medium | Low | Hold final scene framing on the Command Center or Landing Page for 3-5 seconds. |
| **Accidental Database Mutation** | Low | High | Use only read and inspect views during video capture. Do not submit new delete or alter commands during recording. |
| **Exposing Personal Credentials** | Low | Critical | Use ONLY the 1-click evaluator account buttons on `/login`. Never type real passwords on camera. |

---

## 10. Final Rehearsal & Acceptance Checklist

Before hitting the final record button, verify:

- [ ] **Backend Health Check:** `http://127.0.0.1:8000/api/v1/health` returns `status: alive`, database connected.
- [ ] **Frontend Build Verification:** `npm run build` succeeds cleanly in under 1 second.
- [ ] **Landing Page Review:** Visual inspection confirms zero-radius geometry, sharp typography, working navigation.
- [ ] **Demo Accounts Check:**
  - `admin@aicte-india.org` logs in as `SYSTEM_ADMIN`.
  - `scrutiny.verma@aicte-india.org` logs in as `SCRUTINY_OFFICER`.
  - `authority.member@aicte-india.org` logs in as `COMPETENT_AUTHORITY`.
  - `finance.officer@aicte-india.org` logs in as `FINANCE_OFFICER`.
- [ ] **Key Records Inspection:**
  - `DEMO-FDR-RELEASED-001` displays all 9 stages complete.
  - `REL-DEMO-BLOCKED-001` displays `BLOCKED` status with 2 failing checks.
  - `DEMO-FDR-PREDECESSOR-001` and `SUCCESSOR-001` render connected in Lineage table.
- [ ] **Audit Ledger Telemetry:** `/audit` displays `CHAIN INTACT (PASS)`.
- [ ] **Timing Rehearsal:** Run a silent dry-run with a stopwatch. Confirm all navigation actions fit inside 4:45.

---

## 11. List of Unverified Routes & Handled Fallbacks

| Route / Capability | Code Status | Verification Assessment | Walkthrough Handling |
| :--- | :--- | :--- | :--- |
| `/institutions/:id` | Implemented | Verified in router, but not essential for core narrative. | Omitted from video to protect 4:45 time budget. Mentioned as supported. |
| `/health` | Implemented | Detailed technical diagnostics page. | Covered via Header health badge indicator rather than full page view. |
| SFMS Gateway Webhooks | Architecture Ready | External banking gateway simulated. | Clearly identified as simulated; presented as hackathon phase-2 integration. |
| Digital Signature Token (e-Sign) | Architecture Ready | Simulated audit signing. | Explicitly highlighted as offline hackathon milestone. |

---
*Document produced and verified against the live SakshyaTrail application runtime. Grounded in actual database records, registered router endpoints, and verified RBAC authorization guards.*
