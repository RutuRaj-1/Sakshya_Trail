# SIH 2026 — AICTE Security Deposit / FDR Portal
## Consolidated Project Context, Research Summary, Solution Design, and Implementation Guidance

**Problem Statement ID:** 26265 
**Official title:** *Streamline of security deposit / FDR portal*  
**Organization:** All India Council for Technical Education (AICTE)  
**Department:** Regulation Bureau  
**Category:** Software  
**Theme:** Smart Automation  
**Recommended working solution name:** **FDR Sentinel — Security Deposit / FDR Lifecycle Integrity**  
**Document purpose:** One expanded, consolidated context source for future discussions, solution design, implementation, testing, SIH presentation preparation, and jury-question preparation.

# 1. Original Problem Statement — Consolidated Requirements

## 1.1 Background

AICTE, under the Ministry of Education, Government of India, undertakes approval-related regulatory activities for technical institutions in accordance with applicable regulations, approval process handbooks, and administrative procedures. Depending on applicable requirements, institutions may have to submit or maintain security deposits or Fixed Deposit Receipts (FDRs).

Managing these instruments involves maintaining institution-wise records, verifying submitted financial instruments, monitoring validity and maturity, tracking renewal or replacement requirements, handling release/refund requests, and making documents available for regulatory scrutiny. When these activities rely on fragmented records, manual correspondence, or several tracking mechanisms, maintaining an accurate and current view of status, pending actions, and time-sensitive requirements can be difficult.

The stated need is a centralized digital portal that reduces repetitive administration, improves record accuracy, provides timely alerts, supports transparent lifecycle tracking, and remains compliant with applicable AICTE requirements and authorized financial procedures.

## 1.2 Detailed scope expressly described

The proposed portal is for the AICTE Regulation Bureau and other authorized stakeholders. It should:

1. Maintain institution-wise and instrument-wise records of relevant security deposits/FDRs.
2. Capture applicable instrument reference numbers, issuing bank details, deposit amount, issue date, maturity date, validity status, supporting documents, and current administrative status.
3. Enable digital submission and secure storage of FDRs and other prescribed supporting records.
4. Support authorized officials in reviewing submitted information and identifying incomplete records.
5. Where supported, facilitate verification through legitimate bank-issued mechanisms.
6. Distinguish institution-submitted information from information independently confirmed by a bank or other authorized financial source.
7. Flag missing fields, inconsistencies, and other discrepancies that require scrutiny.
8. Monitor maturity dates, validity periods, renewal/replacement requirements, and other prescribed timelines.
9. Generate configurable advance reminders and flag overdue or unresolved cases for follow-up.
10. Record and track release, discharge, or refund requests, subject to applicable rules, prescribed conditions, and competent-authority authorization.
11. Provide a centralized dashboard showing active, expiring, matured, renewed, released, and pending instruments.
12. Support search, review of document histories, updates to permitted fields, scrutiny observations, and case-status tracking.
13. Generate reports showing pending verification, upcoming maturity, missing documents, and cases requiring intervention.
14. Implement role-based access, secure document storage, appropriate encryption, audit trails, and controlled access to financial/institutional information.
15. Consider integration with existing AICTE systems and bank-verification services only where technically feasible and formally authorized.
16. Demonstrate measurable improvement in record accuracy, verification turnaround, timely renewal monitoring, manual tracking effort, and visibility into pending cases.
17. Test at least the scenarios named in the problem statement: new FDR submission, validity tracking, approaching maturity, renewal, discrepancy identification, and authorized release processing.

## 1.3 What the problem statement does not require

The supplied statement does **not** require the system to:

- Move money or operate as a payment gateway.
- Become a bank or independently determine banking facts without an authorized source.
- Replace AICTE's existing approval or e-governance systems.
- Make legal or regulatory determinations autonomously.
- Approve/refuse institutions or authorize financial releases through AI.
- Integrate with every bank, regardless of service availability or authorization.
- Depend on machine learning for its core functionality.

A portal may assist, validate, flag, route, remind, and record. It must not exceed the authority of the applicable policy or of the competent official.

---

# 2. End-to-End Problem Understanding

## 2.1 The real problem is lifecycle control and trust—not merely storage

A file-upload website is insufficient. A system could store every scanned FDR and still fail to tell AICTE whether the document has been independently confirmed, whether the relevant dates are current, whether a replacement has been received, whether a release condition remains open, or whether the last status change was authorized.

The central operational questions are:

- Which institution is associated with each instrument?
- What are the instrument's recorded facts and source documents?
- Which values were declared, extracted, checked by an officer, or independently confirmed?
- What is the current administrative and verification status?
- What deadline or next action applies, and to whom is it assigned?
- Is a renewal/replacement linked to its predecessor, preserving the chain of evidence?
- Are release conditions and approvals complete?
- Can an auditor reconstruct the history of a decision?

**Solution thesis:** Create a single trusted register and lifecycle workflow that makes instrument status, evidence, uncertainty, deadlines, and next actions visible to authorized users.

## 2.2 Problems stated versus hypotheses

The official statement explicitly describes fragmented records, manual correspondence/multiple tracking mechanisms, a need for better status visibility, deadline monitoring, verification, workflows, and auditability.

The longer research document also lists plausible problems such as missed maturity follow-ups, mismatches between portal records and actual held instruments, duplicated/reused documents, slow release due to scattered evidence, and context being lost when officers change. The document labels these as hypotheses to validate with AICTE staff—not established facts. They must be described as potential risks, not proven AICTE failures.

No public baseline statistic for delay, loss, error rate, or manual hours is established in the documents. These must be measured in a pilot or controlled evaluation before claiming impact.

## 2.3 Security deposit versus FDR

A security deposit is a required amount maintained under applicable rules. An FDR is one kind of bank-issued financial instrument that may evidence or support a deposit requirement under the applicable process. The terms should not be treated as identical in every case.

The data model should allow multiple permitted instrument/security types if AICTE's rules require them. The final types and required fields must be confirmed against the relevant current policy and operational forms. References to joint FDRs, liens/pledges, or alternative instruments in the research documents are design considerations to investigate, not confirmed universal requirements for all PS 26265 records.

---

# 3. Three Uploaded Documents — Individual Summaries

## 3.1 Document A: `SIH 2026 – Security Deposit FDR Portal Research, Solution Design & Jury Evaluation.docx` (38 pages)

### Purpose

This is the most extensive research/design blueprint. It decodes the official problem statement, discusses relevant AICTE context and stakeholders, specifies lifecycle stages, develops functional/non-functional requirements, suggests an architecture and stack, maps prototype phases and tests, and prepares the team for jury questions.

### Core interpretation

It defines the problem as lifecycle management plus trustworthy provenance. Each instrument needs a reliable institution-wise/instrument-wise record, evidence, verification state, time-based monitoring, controlled replacement history, release workflow, and a traceable audit trail.

### Research/context findings as reported in the document

- AICTE material referenced by the document describes institutions paying security deposits through the institute web portal when an application shows a “Deposit Requested” status; the document also mentions an exception for government institutions filing an affidavit in the cited older guide.
- An AICTE notice cited in the research described a historic refund process for an older institution cohort, including FDR interest and principal handling tied to an approval cycle.
- The document says requirements vary by handbook year and institution type, based on cited handbook/FAQ/workshop material. Therefore, policy should be configurable rather than hard-coded.
- It reports that an AICTE e-Governance process describes online security-deposit payment/amount checks and that a JFDR refund workflow exists in public AICTE material (the latter point is emphasized more directly in Document C).
- The document could not confirm whether live electronic bank verification for ordinary FDRs is available to the team. It warns against claiming a bank API without evidence.
- NeSL e-BG is discussed as an example of digital handling of electronic bank guarantees, but the document explicitly warns that a bank guarantee is not an FDR and does not establish an FDR-verification API.
- It reports no publicly established statistics for existing delay/loss rates.

These are findings and caveats reported in the uploaded research. Before using them in a formal pitch as current official facts, verify the underlying AICTE source/version.

### Stakeholders and their needs

- **Institution representative:** submit instrument details/documents, see its own records, know what is missing, correct deficiencies, receive reminders, initiate renewal/replacement or release requests.
- **Scrutiny officer / Regulation Bureau officer:** review fields/documents, compare declared versus confirmed values, enter scrutiny observations, request corrections, handle discrepancies, and see a prioritized queue.
- **Section/branch head:** monitor overdue and high-risk cases, reassign work, and escalate unresolved matters.
- **Competent authority:** review readiness evidence and authorize/reject release only within the assigned legal/administrative authority.
- **Finance/accounts official:** view appropriate financial fields, track release orders and bank-side actions, and reconcile status.
- **Issuing bank officer (optional external participant):** respond through a formally supported process if available. The research explicitly recognizes that banks may not participate in the prototype or in a common API.
- **System administrator:** manage users, roles, system parameters and configuration, without automatically acquiring financial approval authority.
- **Auditor:** review read-only evidence, action histories and audit logs.
- **External systems:** AICTE approval/e-governance portal, bank channel, identity systems, and email/SMS gateways; real access is not established.

### Proposed lifecycle

1. Submission of instrument details and documents.
2. Validation for completeness, date logic, amount requirements where policy is known, institution-name consistency, and probable duplicates.
3. Officer scrutiny and verification request/response recording.
4. Instrument monitoring and automatic reminders/escalations.
5. Renewal/replacement with explicit predecessor/successor linkage.
6. Release/refund request with supporting documentation and a readiness checklist.
7. Maker-checker/multi-level authorization according to policy.
8. Closure and recording of the resultant administrative/bank-side status.

### Trust levels proposed by the research

- **L0 — Declared:** entered by an institution or imported from a record.
- **L1 — Document-consistent:** values pass basic formatting/consistency rules; this does not establish authenticity.
- **L2 — Officer-verified:** authorized official has reviewed the evidence and recorded their decision.
- **L3 — Bank-confirmed:** a bank confirmation response is recorded. A simulated response must be visibly labeled “SIMULATED.”

The critical rule is that OCR output or internal rule checks must never silently upgrade a record to bank-confirmed.

### Functional requirements and acceptance-test ideas unique to this document

- Unique internal instrument record; likely duplicate instrument references should be flagged or constrained using a key appropriate to bank/reference rules rather than silently merged.
- Secure document upload should record a version/hash; re-uploads should create versions rather than overwrite evidence without history.
- OCR is optional and its fields are suggestions; a low-confidence value must be highlighted for human confirmation.
- The validation engine should produce flags with explicit reasons, policy/rule identity, and severity where appropriate.
- Verification requests should reference a specific instrument/request. A response mismatch creates a discrepancy; timeouts remain pending and may be retried.
- Date-processing jobs should be idempotent and have a catch-up mechanism after failures.
- Reminder configuration should be data-driven; sample intervals like 90/60/30/15/7 days are proposals, not official AICTE timelines.
- Escalation should reach the next authorized role after a configurable overdue period.
- Replacement lineage should preserve the old instrument and calculate any gap or overlap according to the relevant policy.
- Release should be blocked when mandatory documents, unresolved required flags, renewal confirmation, clearances, or authorizations remain outstanding, based on the configured policy.
- Search should support institution, bank, instrument reference, status, and date filters.
- Reports should cover pending verification, upcoming maturities, missing documents, and intervention cases.
- Institution users must not be able to access another institution's records.
- Bulk import of legacy CSV/spreadsheet records is an implied/secondary feature; imported data should begin as unverified/declared and produce a row-level quality report.
- If an integration is unavailable, the core process should remain functional with an explicitly recorded manual/simulated path.

### Security and non-functional considerations

- Least-privilege role-based access, institution-level isolation/tenant scoping, MFA for officials if available/required, encrypted data in transit and at rest, masked sensitive fields, controlled signed document links, rate limiting, upload validation and malware scanning, audit logging, retention policy, backup/recovery, monitoring and idempotent scheduled jobs.
- Protect audit records against normal update/delete paths. A hash chain can make tampering detectable, but it does not make a system absolutely immune to a privileged database administrator; external hash anchoring is described as a possible future mitigation.
- Privacy and retention policies require review with the competent authority. The document mentions India's DPDP Act, 2023 as part of its privacy considerations; obtain legal review before production rather than treating this summary as legal advice.
- Low-bandwidth regional offices, staff adoption, and continuity when network/notification systems fail should be considered.

### Architecture and stack suggested in Document A

A modular monolith plus a background worker, with:

- React or Next.js frontend and an official/institution workspace.
- FastAPI/Python or a similar backend.
- PostgreSQL for structured records, events, approvals, and reporting.
- Encrypted local/S3-compatible object storage (e.g. MinIO/S3) for documents.
- A scheduled worker using a scheduler such as APScheduler or Celery Beat; Redis can support queued jobs when needed.
- SMTP/email, with an SMS gateway or a clearly mocked notification service for demonstration.
- Optional OCR such as PaddleOCR/docTR/Tesseract; optional CV/duplicate methods only if they are actually implemented and tested.
- Versioned JSON/YAML policy rules.
- Role-based authentication such as an organization-approved identity system or a suitable role/JWT implementation.
- Append-only, hash-chained audit records and an audit verification screen.
- Docker Compose for reproducible demonstration; CI can be added if time permits.

This is a suggestion list, not a mandate to use every named tool. The third document recommends keeping the architecture simple and avoiding unneeded multi-agent/LLM infrastructure.

### Prototype phases and roles

- **Phase A — Core MVP:** register/instrument records, uploads and versioning, deterministic rules, trust levels, deadline state engine, reminders, renewal lineage, release workflow/checklist/approval, dashboard, 3–4 roles, audit, and test data.
- **Phase B — Demonstration differentiators:** simulated bank-confirmation page, risk-ranked queue, escalation, hash verification, duplicate checks, guided deficiency correction and exportable reports.
- **Phase C — Future roadmap:** OCR extraction, live bank/AICTE integration, SSO/DSC, multilingual templates, evidence package and pilot with an AICTE regional office, subject to access and resources.

The document models a possible 36-hour finale (an assumption, not a confirmed contest duration) with six suggested roles: team lead/demo/presentation; backend/data/RBAC; rules/scheduler; officer-dashboard frontend; institution/release-flow frontend; QA/DevOps/test data/metrics.

### Proposed test data and demonstration

This document proposes roughly 60 fictional institutions and about 120 instruments in mixed states. Its demonstration includes:

- Clean submission.
- Name mismatch and amount shortfall.
- Maturity approaching without renewal.
- Duplicate FDR reference across fictional institutions.
- Renewal chain A → B.
- Release request blocked by an open issue.
- Bank adapter timeout.
- Corrected resubmission retaining history.
- An unauthorized self-approval attempt.
- Audit verification passing, then failing when a test copy of an event is tampered with.

All such records are synthetic. This demonstrates software behavior, not live institutional facts.

### Evaluation measures proposed by Document A

- Record accuracy against source document data.
- Verification turnaround from submission/request to recorded result.
- Discrepancy precision/recall on a labelled synthetic set.
- Instruments expiring without action.
- Reminder reliability and duplicate-notification rate.
- Officer effort/time per case versus a measured baseline.
- Queue ranking usefulness for seeded high-risk cases.
- OCR exact-match accuracy if OCR is built.
- Job/system reliability and user usability metrics.

Suggested targets in the file are planning targets; none should be presented as achieved until actually measured. Small samples should be described as indicative rather than statistically conclusive.

### Jury question preparation in Document A

Be prepared to explain:

- What the system solves and why it is more than an upload portal.
- Whether AICTE already has a security-deposit process (acknowledge public processes; describe a potential complementary layer and validate the remaining gap with AICTE).
- Why the core design uses deterministic checks rather than AI decisions.
- How an FDR can be confirmed without a bank API (record structured manual/officer processing; keep L2 separate from L3; never claim simulated reply is real).
- How rules changing across handbook years are handled (versioned policy configuration, after requirements are confirmed).
- Who authorizes release (competent authority, not an AI model).
- How audit tampering is detected and what residual risks remain.
- How privacy, institutional isolation, failed reminders, no bank response, false positives and disputes are handled.
- How success will be measured versus a baseline.

The document's own final verdict is cautious: problem understanding is strong, feasibility is moderate-to-strong if scope is disciplined, demonstration quality depends on the live prototype, and real data/integration readiness is unverified.

## 3.2 Document B: `SIH 2026 Research SIH26261 vs SIH26265 (AICTE).pdf` (18 pages)

### Purpose

This PDF compares SIH26261 (AI-powered application validation/document authentication/compliance) with SIH26265 (FDR portal), then gives separate technical deep-dives and presentation recommendations. It contains the broader comparative context and some alternatives that do not need to be part of the final FDR MVP.

### Comparative conclusion

SIH26261 is more AI/ML/CV-heavy and may have greater visual “AI spectacle,” but it spans more document categories and data sources; OCR quality, source verification and scope management create risk. SIH26265 has a more contained workflow and can be demonstrated deterministically, but the danger is looking like a plain CRUD system.

The document's initial recommendation leans to SIH26261 if the team has ample AI/ML implementation capability, with SIH26265 as a safer fallback. This is a comparison note, not the final decision. Document C subsequently recommends SIH26265 based on its tighter demonstration scope and clear lifecycle-integrity differentiators.

It mentions portal submission counts (28/500 for SIH26261 and 15/500 for SIH26265) and a stated 28 October 2026 deadline in its snapshot. Treat these as time-specific data copied at the time of research, not current or independently verified values.

### External precedents discussed

- SIH 2025 prior problem statements/winners and an automated compliance-checker example are used as broad context for the viability of rules-based compliance workflows.
- An “Authenticity Validator for Academia” example is mentioned as a document-authenticity precedent.
- An IndiaAI/NHA/IISc AB PM-JAY hackathon challenge is cited as a government-related forgery/deepfake-detection precedent.
- Singapore GovTech's Borderless Trust is cited as a comparison for AI-supported document verification; its reported time reduction is a source-specific benchmark, **not a result for this FDR proposal**.
- NeSL e-BG is described as a digital bank-guarantee workflow precedent. It must not be cited as proof that FDR verification is supported.

These precedents belong mainly in background/research context. They do not establish the proposed system's performance or replace the direct PS 26265 requirements.

### Proposed FDR Vault concept

The PDF names the working proposal “FDR Vault.” It advocates a state machine for each instrument plus source/provenance labels for fields: institution-declared, system-extracted, officer-reviewed, and bank-confirmed. It outlines states such as Draft, Submitted, Under Scrutiny, Discrepancy Raised, Bank-confirmed/Verified, Active, Expiring Soon, Renewal/Replacement Due, Renewed, Matured, Release Requested, Release Approved, Released, Overdue and Escalated.

Every state transition should carry who made it, when, why, and the relevant document/evidence. This state list is a proposed model; the implementation should finalize mutually consistent states and allowed transitions rather than blindly implementing every label as a separate state.

### Optional features listed in Document B

- OCR auto-fill of FDR number, bank/branch, amount and dates, with human confirmation.
- Configurable reminder intervals, for example 90/60/30/15/7 days (examples only).
- Expiry/amount/name/duplicate/lien checks where relevant to the governing policy.
- A transparent rule-based risk score based on factors such as late renewal history, residual validity, discrepancy count and possibly other approved factors; avoid opaque scores and do not allow a score to make legal decisions.
- Monthly maturity/cash-flow forecasting by deposit amount.
- Duplicate/reused FDR-reference detection and optional analysis of suspicious-looking scans.
- SMS/WhatsApp nudges, one-click upload, natural-language search translated to parameterized database filters, Hindi/English UI, and downloadable audit report.

These are possible differentiators, not all essential MVP items. Prioritize only if the core workflow is already reliable and the feature can be demonstrated honestly.

### Architecture and test sizes in Document B

The PDF proposes a front end, API/RBAC/rate limiting, instrument and workflow services, document upload/OCR/virus scanning/hash, a notification service/scheduler, PostgreSQL, encrypted object storage, verification adapter, and reporting/analytics.

It gives a larger proposed synthetic data range of 200–500 instruments across 30–50 institutions, plus a day-by-day development sequence. That differs from Document A's smaller illustrative dataset. These are alternative suggested dataset sizes, not contradictions in the official requirement. Use the dataset size that supports the team's test objectives and can be reliably seeded, inspected and explained.

### Six-slide pitch guidance in Document B

It suggests a standard SIH six-slide story: title/team; idea/solution; technical approach; feasibility/viability; impact/benefits; research/references. It advises keeping the narrative concise, using diagrams, distinguishing prototype scope from integrations, showing the requirement-to-feature mapping, and preparing for judges' questions about data access, model errors, accuracy, privacy, existing alternatives, scalability and cost.

### Unique contribution of Document B

Its main unique value is the comparison of the two AICTE problem statements, broader technology and precedent research, and a menu of optional AI/analytics enhancements. Its initial selection advice is superseded by Document C's more focused recommendation for PS 26265.

## 3.3 Document C: `SIH_2026_AICTE_PS_Decision_and_6_Slide_Strategy.docx` (6 pages)

### Purpose and final recommendation

This is the most focused decision and presentation document. It recommends **SIH26265 with a provenance-first FDR lifecycle integrity layer**, under the working name **FDR Sentinel**, instead of a generic FDR CRUD portal.

It recommends the FDR problem because its core can be demonstrated with a deterministic state machine, source/provenance states, maturity escalation, renewal lineage, release controls and a hash-chained audit. It warns that UI polish, OCR, risk scores or a high count of agents are not a differentiator by themselves.

### Important correction: do not say AICTE has no FDR portal

The decision brief says the publicly available AICTE e-Governance RFP describes a JFDR refund process for matured fixed deposits, with review steps involving regional, vigilance and headquarters cells, and application-status tracking. Therefore, the team should not claim that AICTE has no portal or process.

Recommended positioning: **FDR Sentinel is a complementary lifecycle-integrity, provenance, monitoring, renewal-lineage and release-readiness layer for use alongside existing AICTE processes, subject to authorized integration and validation of the actual gap.**

The exact public document and section cited by Document C are listed in the reference section at the end of this file. Verify the relevant version before final external use.

### Five main value propositions

1. **Trust Ledger:** a field's source and trust status remain explicit.
2. **Explainable discrepancies:** exact reason, source value, expected/policy value, rule version and next action are shown.
3. **Renewal lineage:** predecessor and successor are linked; prior history is not overwritten.
4. **Maturity escalation:** configurable deadline checks and a demo clock show reminders and escalation live.
5. **Release Gate plus verifiable audit:** the system lists blockers and requires the appropriate authorization; audit history can be checked for tampering.

### Strongest design rules from Document C

- L0–L3 must represent evidence progression, not decorative status badges.
- OCR alone cannot establish authenticity.
- Simulated bank responses must be labeled “SIMULATED” in both UI and audit data.
- Release must remain a human/competent-authority decision; the software checks readiness and enforces workflow rules.
- A different authorized role should approve a release where maker-checker separation is required.
- No renewal should overwrite its predecessor.
- “Pending,” “unconfirmed,” and “source unavailable” are legitimate states. A timeout cannot be converted to “confirmed.”
- An audit hash chain should be replayed and checked in the demonstration; a controlled test modification should fail verification.
- The UI is not the source of truth; the backend/data model must enforce allowed transitions.

### Recommended simple architecture

Institution/officer user interface → API + role-based access → FDR rules/state engine → PostgreSQL and document storage, with supporting components:

- Scheduler/reminder worker.
- Verification adapter (simulator for the demo; a real connector only if authorized/available).
- Release gate and maker-checker approval logic.
- Append-only/hash-chained audit history.

Suggested stack: React + Tailwind; FastAPI/Python; PostgreSQL; local or S3-compatible object storage; background scheduler/worker; JSON policy rules with effective dates; optional PaddleOCR/Tesseract for field prefill. The recommendation is a modular monolith plus worker. The core does not need distributed multi-agent architecture, a vector database, or an LLM in the release decision path.

### Flagship demo and scenario table

The flagship demo uses one fictional FDR from submission through discrepancy handling, simulated bank confirmation, maturity alert, renewal and release. The document's scenario matrix includes:

- **S1 Clean submission:** data passes rules; trust remains unconfirmed until confirmation evidence exists.
- **S2 Discrepancy:** seed a name mismatch and amount shortfall; both flags show clear reasons.
- **S3 Maturity:** instrument matures in roughly 28–30 days with no renewal; reminder and risk queue trigger under the demo policy.
- **S4 Duplicate:** the same fictional reference appears across two institutions; flag for officer review.
- **S5 Renewal chain:** new FDR is linked to the original and history remains intact.
- **S6 Release blocked:** open scrutiny flag or missing clearance prevents transition; show blockers.
- **S7 Source unavailable:** simulated bank service times out; status remains pending/manual review, never bank-confirmed.

The six scenarios required by the official problem statement still need to be explicitly covered: new submission, validity tracking, approaching maturity, renewal, discrepancy, and authorized release. S4 and S7 are valuable additional tests.

### Evaluation gates, not invented outcomes

Document C proposes functional pass/fail gates:

- Zero L3/bank-confirmed states without a verification response record.
- Zero release transitions when mandatory blockers remain.
- Renewal history is never overwritten.
- Audit-chain tampering is detected.
- Required scenarios pass.

It also suggests measuring seeded discrepancy precision/recall, reminder timeliness under simulated time, time to find instruments maturing within a defined period, pending-verification age and audit-replay completeness. These are to-be-measured metrics, not proven results.

### Detailed six-slide presentation plan

1. **Title:** FDR Sentinel; PS ID SIH26265; AICTE; Smart Automation; Software; team information; lifecycle graphic with “Declared ≠ Confirmed.” Avoid “India's first” or “AICTE has no portal.”
2. **Idea/Solution:** lifecycle trust problem, existing-process caveat, solution flow, and five value propositions.
3. **Technical approach:** architecture, L0–L3 trust levels, renewal lineage, deterministic checks, optional OCR, and simulated bank adapter.
4. **Feasibility/viability:** MVP scope, security, versioned policies, simulated/manual bank fallback, scheduler recovery, OCR human confirmation, missing-authorization release block, and explicit integration status.
5. **Impact/benefits:** a single fictional lifecycle, prioritized risk queue, and proposed metrics. Mark metrics as targets/evaluation metrics until measured.
6. **Research/references:** PS 26265, AICTE Approval Process Handbook 2024–27, AICTE e-Governance RFP JFDR section, NeSL e-BG with clear distinction from FDRs, requirement-to-feature mapping, and status labels for implemented/simulated/requires authorization.

### Three claims the team must be able to defend

1. “We are not replacing AICTE's existing portal; we propose a lifecycle-integrity layer that integrates only through authorized interfaces.”
2. “The system never treats institution-declared information as bank-confirmed, and simulated confirmation is visibly labeled.”
3. “Release is not an AI decision. The system checks readiness, explains blockers, enforces the approval workflow and records the event.”

### Unique contribution of Document C

It resolves the product direction and finalizes a defensible name and pitch. It is the source for the recommended **FDR Sentinel** positioning, the “existing process” caveat, the five differentiators, the simple architecture, the flagship demo, and the six-slide presentation blueprint.

---

# 4. Consolidated Recommended Product — FDR Sentinel

## 4.1 Product definition

**FDR Sentinel is a proposed trust-first lifecycle-integrity layer for security deposits/FDRs associated with AICTE approval-related processes.** It maintains institution-wise and instrument-wise records, records the provenance and verification state of important data, detects discrepancies through transparent rules, monitors deadlines, preserves renewal/replacement relationships, routes release requests through approved checks, and keeps a reviewable audit history.

It is not a bank, payment gateway, legal decision-maker, replacement approval portal, or claim of a universally available live bank API.

## 4.2 Product principles

1. **Provenance before automation:** preserve where data came from and what kind of confirmation supports it.
2. **Explicit uncertainty:** pending, incomplete, disputed, or unconfirmed information must be visible.
3. **Rules in the backend:** enforce lifecycle transitions server-side, not by disabling a button only in the UI.
4. **No silent overwrite:** corrections and replacements create history, not destructive edits.
5. **Release is gated:** all policy-required checks and human authorizations must be complete.
6. **Policy is versioned/configurable:** rules vary by applicable handbook year, institution type or case; the authorized owner must validate the actual rules.
7. **Integration-ready but honest:** use adapters; label mocks/simulation; real integration requires formal authorization and technical support.
8. **Auditable by design:** record who/what/when/why/evidence for material actions.
9. **Minimize AI decision risk:** deterministic rules handle core dates, completeness, access and authorization; optional AI assists data-entry or flags cases for human review.
10. **Measure before claiming impact:** record a baseline and report test/pilot outcomes honestly.

## 4.3 Main user roles and permissions

### Institution user

- Access only its own institution's records.
- Submit instrument details and documents.
- View status and actionable deficiencies.
- Correct/resubmit where the workflow allows it.
- Receive authorized reminders.
- Submit renewal/replacement or release/refund requests as permitted.
- See request progress and relevant decisions without unauthorized access to internal-only notes or other institutions' data.

### Scrutiny / verification officer

- Review assigned submissions.
- View source documents and extracted/entered values.
- Compare institution-declared values with other evidence.
- Record observations, request corrections, and raise/resolve discrepancies under permitted rules.
- Initiate/record verification requests and evidence.
- Assign or route cases according to permissions.
- Not automatically authorize a release merely because they can scrutinize an FDR.

### Section/branch head

- View scoped queues, overdue cases, unresolved discrepancies and escalations.
- Reassign work and escalate according to policy.
- Review trends and pending-case reports.
- Exercise only the approvals explicitly assigned by the relevant workflow.

### Finance/accounts official

- Access permitted financial information.
- Track clearance/release-order status and bank-side follow-up as authorized.
- Record relevant action evidence without bypassing the competent authority.

### Competent authority / approver

- Review readiness checklist and complete evidence pack.
- Approve/reject/return an action within the person's actual delegated authority.
- Provide a reason where required.
- Must not simply receive an AI-generated approval recommendation as a final decision.

### Administrator

- Manage accounts, role assignments, policy versions, notification settings and technical configuration.
- Cannot automatically gain authority to approve financial decisions through the administrator role.
- Changes to policy configuration must themselves be authorized, versioned and audited.

### Auditor

- Read-only/restricted access to the relevant history and evidence.
- Verify audit history and review decisions.

### External bank or system integration

- Optional. Only supported through an officially approved mechanism. In a prototype, use a simulated service/manual record and label it accurately.

---

# 5. Detailed Functional Design

## 5.1 Institution and instrument repository

Keep institution master data separately from each instrument record. An institution may have multiple financial instruments, and each instrument needs a stable internal identifier.

Suggested fields (the final schema requires policy/AICTE validation):

- Institution ID, official name, AICTE identifier where applicable, institution type, permitted contact information.
- Internal instrument ID and instrument type.
- Bank name and relevant branch/reference details; IFSC or other fields only if required/available.
- Instrument/FDR reference number, amount/currency, issue date, maturity date, validity status and any applicable lien/pledge details.
- Document references and versions.
- Current administrative state and separate verification/trust state.
- Assigned office/owner, pending action, timestamps and observations.
- Predecessor/successor links for renewal/replacement.
- Verification evidence and audit references.

Do not treat a bank reference number as globally unique without confirming the key rules; a realistic duplicate key may need to combine bank identity and reference. A suspected duplicate should be flagged for review rather than assumed to prove fraud.

## 5.2 Secure document handling

- Allow only configured file types and sizes.
- Perform malware scanning and safe file handling.
- Store files in protected object storage, not a public web directory.
- Keep metadata, uploader, upload time, document category, file hash, version and parent instrument/case reference.
- Preserve previous versions when a corrected document is uploaded.
- Restrict viewing/download through authorization checks and time-limited access URLs if suitable.
- Provide preview/download only to permitted roles.
- A cryptographic file hash helps detect changes to a stored file or exact duplicates, but **does not prove that a source document is authentic**.

## 5.3 OCR and Vision-LLM field extraction (optional, not core)

### Purpose and candidate fields

An institution can upload a scanned FDR image or PDF. A conventional OCR engine or a vision-capable large language model (Vision-LLM) may assist by extracting structured fields such as:

- Bank name and branch, where visible.
- FDR/instrument reference number.
- Principal/deposit amount and currency.
- Issue date and maturity date.
- Depositor/institution name.
- Whether AICTE appears to be named as lien holder/beneficiary/pledgee, when the wording is present and legible.
- Other explicitly required fields confirmed against the applicable form/policy.

A Vision-LLM implementation can send an image or PDF-rendered page to an approved vision-capable API with a schema-constrained prompt requesting structured JSON. The system should reject malformed output, validate types/date formats, preserve the source page/region where feasible, and show the results in a review screen. The institution user or authorized officer confirms or corrects each field before those values become the accepted application data.

### Required provenance and comparisons

- Tag automatically extracted values as **`OCR-Extracted`** or **`Vision-LLM-Extracted`**, not “verified.” These tags describe the extraction method, not authenticity or independent confirmation.
- Keep institution-entered values, machine-extracted suggestions, human-corrected values, officer-reviewed values and bank-confirmed evidence distinguishable.
- Compare form-entered values with extracted document values. If the institution-entered amount/date/name differs from the extracted value, create an explainable discrepancy for review rather than silently choosing one source.
- Store the extraction timestamp, model/provider identifier where appropriate, schema/version, confidence if reliably available, document version and reviewer correction. Keep only the evidence required for audit and evaluation.
- Low-confidence, missing or ambiguous output should remain blank/uncertain and be sent for human review. Never let the model invent a value to complete the JSON schema.
- OCR/Vision-LLM output does not establish bank confirmation, authenticity, release eligibility or legal compliance.

### Why this may be useful

Structured extraction can reduce repetitive typing and make comparison between the submitted form and the FDR document easier. A vision model may cope with varied document layouts better than a basic OCR-only pipeline in some cases, but this must be tested on representative scans; it is not guaranteed to be more accurate for every bank, scan quality or script.

### Limits and privacy safeguards

Blurry, skewed, low-resolution, handwritten, cropped or multilingual scans can lead to incorrect values. Use human confirmation and evaluate exact field-level accuracy on labelled test documents. Do not state a generic accuracy figure without measurement. Because FDR scans contain sensitive financial/institutional information, do not send raw documents to an external LLM API in production unless AICTE has approved the provider, data handling, security terms and deployment path. Prefer an approved/self-hosted model or a controlled/redacted workflow where appropriate. For the hackathon, use synthetic or authorized anonymized documents and label the integration status honestly.

If Vision-LLM extraction is out of MVP scope, manual entry plus deterministic checks is an acceptable core implementation. Do not list any extraction feature as implemented unless it runs in the actual prototype.

## 5.4 Deterministic validation, tamper/anomaly flags, and explainable discrepancies

Use versioned, authorized rules for checks such as:

- Required field/document present.
- Issue date precedes maturity date.
- Validity covers the required period when that rule applies.
- Amount meets the applicable required amount when the rule is known and correctly configured.
- Institution name/reference details are consistent across records/documents.
- Potential duplicate instrument references exist across records or institutions.
- An identical file hash has already been submitted.
- Required supporting documents are missing or the uploaded file appears to be of the wrong type.
- Declared details differ from OCR/Vision-LLM extraction or authorized verification evidence.
- Replacement link/chronology appears inconsistent.
- Instrument terms appear internally inconsistent, but only when the required authoritative terms are available.

### Proposed anomaly/tamper indicators

The following checks can be added as explainable flags:

1. **Duplicate reference:** the same FDR reference appears on another record/institution. Use a bank-aware/reference-aware comparison key where appropriate and route possible duplicates to an officer.
2. **Exact duplicate file:** the same cryptographic file hash is already present. This proves a byte-identical upload, not that the underlying instrument is fake or incorrectly reused.
3. **Document metadata:** PDF metadata suggests later editing, an image-editor producer, or a creation/modification timestamp after the claimed issue date. This is a weak signal only: legitimate scanning, printing, conversion and re-saving can change metadata, so it must never prove tampering by itself.
4. **Date logic:** maturity before issue date, malformed dates, or an expiry/validity period inconsistent with a correctly configured rule.
5. **Financial-term consistency:** compare an amount against interest rate/tenure only if the relevant principal, rate, tenure, compounding/payout terms, amount meaning and authoritative instrument terms are available. Do not assume a standard interest calculation or flag a mismatch from incomplete terms.
6. **Name/value comparisons:** different institution names, reference numbers or amounts across form, FDR scan and authorized bank response should be shown side by side with the compared sources.

### Evidence and language

Every flag should identify the rule/check, source value, expected value or comparison basis, severity/priority if used, supporting evidence, current status and suggested next action. Distinguish deterministic rule results from heuristic metadata/image indicators. Use wording such as **“Advisory indicator — human review required”** for heuristic flags. These checks indicate inconsistency or unusual properties; they do not prove fraud or forgery.

A deterministic check is reproducible, but its correctness still depends on accurate inputs and an approved rule. Do not call every rule result “fully reliable” if the governing policy or source data has not been confirmed. Do not use unexplained black-box “AI risk” numbers.

Where no authoritative rule is configured, the system should not invent one. It can report “rule not configured / manual review required.”

## 5.5 Verification workflow and trust model

Trust is a separate axis from the administrative state. An instrument may be “submitted” while still only declared; an instrument can have an open discrepancy; a bank response can be pending; an officer can review a document without independent bank confirmation.

Recommended trust levels:

- **L0 — Declared:** supplied by the institution or imported from an unverified legacy record.
- **L1 — Document-consistent:** passed configured internal consistency checks; not proof of authenticity.
- **L2 — Officer-verified:** an authorized officer reviewed evidence and recorded the outcome.
- **L3 — Bank-confirmed:** an actual authorized bank confirmation response/evidence is recorded. In demos, the status must say **“Simulated bank confirmation”**, not merely “Bank-confirmed” without qualification.

L3 needs a confirmation record with the source/method, response reference, timestamp, result, and evidence. In case of missing response, mismatch, unavailable service or timeout, the state stays pending/unconfirmed or discrepancy-raised.

The model should preserve conflicting information and avoid upgrading the trust level silently. Define whether a field, instrument, and verification request each have their own status; do not conflate them.

## 5.6 Maturity, validity and reminders

The system needs a background monitor that computes time-to-maturity and triggers configured actions. Example intervals such as 90, 60, 30, 15 and 7 days are illustrations from the documents only, not official deadlines. The policy owner must approve the actual intervals and recipients.

Needed behaviors:

- Calculate day-based conditions consistently using relevant local date/time conventions.
- Trigger reminders at configured intervals.
- Maintain notification history, recipient/channel, timestamp, delivery result, retry count and related instrument/action.
- Avoid duplicate reminders for the same event/interval, using idempotency keys or equivalent controls.
- Flag overdue actions and apply escalation rules.
- Handle worker outage by detecting failure and performing a catch-up run on restart.
- Offer a demo-only “advance date/clock” control so judges can see reminders fire without waiting days or weeks.
- Distinguish maturity date, validity period, due date for institution action, due date for officer action, and any other dates that apply.

A maturing or matured instrument does not automatically become eligible for release. Date status and release eligibility are different concerns.

## 5.7 Renewal/replacement lineage

Represent renewal/replacement as a relationship between separate instrument records rather than an edit to the same row. For example:

`Original FDR A → Replacement FDR B → Later replacement FDR C`

For every successor, record the predecessor link, submission date, dates/amounts, documents, checks, verification state, and decision. Preserve the original instrument record, document history and closure status. Flag gaps or unusual timing for review using the approved policy.

The system should not mark the old instrument as released merely because a successor document was uploaded. Replacement submission, review, verification, approval and release are separate events where the rules require them.

## 5.8 Release / discharge / refund workflow

This is a controlled administrative workflow, not a money-moving mechanism.

Possible path:

1. Institution submits a request and prescribed supporting evidence.
2. The system loads the correct checklist for case type and applicable policy version.
3. The system checks required documents, unresolved observations, pending verification, renewal conditions and clearances where those conditions are configured.
4. An officer reviews the case and records observations.
5. Any missing evidence or issue is returned with reason, or the case is routed onward.
6. A readiness report lists satisfied checks, unmet checks and evidence for each.
7. The request moves to the authorized approver(s), respecting separation of duties/maker-checker rules where applicable.
8. An authorized decision is recorded with actor, timestamp, reason and evidence.
9. Relevant release order or bank-side process tracking is recorded as appropriate to policy.
10. Closure retains the complete history and evidence.

If mandatory conditions are open, the Release Gate must block the transition and show the reasons. Clearing a UI flag alone must not bypass authorization. The actual requirements, document list, chain of clearances, and roles must be validated against current AICTE rules and not invented from generic assumptions.

The uploaded decision brief cites an AICTE Approval Process Handbook clause on release and an AICTE e-Governance RFP JFDR section. Those sources should be checked directly for the exact case before encoding production policy. Requirements might vary by case, instrument type, handbook version or institution category.

## 5.9 Dashboard, explainable risk prioritization, maturity forecast, and reports

Role-appropriate dashboards should provide:

- Number of instruments by administrative status.
- Instruments nearing maturity within a selected timeframe.
- Matured/overdue instruments needing action.
- Pending verification, age of pending requests, unavailable-source cases.
- Missing documents and unresolved discrepancies.
- Renewal/replacement submissions due and lineage history.
- Release/refund requests and checklist blockers.
- Cases by assigned officer/office and escalation level, within permissions.
- A document-completeness view showing which required document types are present, missing, unreadable, or awaiting confirmation.
- A monthly maturity distribution chart showing the **count and/or amount** of instruments maturing in each month, based on recorded maturity dates. This is a deterministic aggregation, not an AI prediction.

### Optional transparent FDR risk-priority score

An optional 0–100 score can prioritize work using a configurable weighted formula over operational factors such as days to maturity, unconfirmed verification, missing required documents, open/high-severity discrepancies, overdue actions and recorded past renewal delays where such history exists.

- The score should help determine **what an officer should look at first**; it is not a fraud probability, legal determination or approval decision.
- Show the factor-by-factor score contribution, source data, policy/configuration version and next action. Use an understandable formula and let authorized administrators adjust weights through an audited configuration process.
- Initial weights are design assumptions, not trained or validated against real AICTE outcomes. Clearly label the score as a prototype rule-based priority indicator and evaluate it against seeded cases.
- Missing history should not be treated as evidence of poor performance. If the data needed for a factor is absent, disclose or omit that factor rather than inventing a value.

### Maturity forecast and renewal-risk prediction

The month-by-month maturity chart can be built directly from instrument dates and amounts and can support workload planning. A prediction of which institutions are likely to miss renewal is different: it would require relevant historical, labelled renewal/action data and validation. Synthetic-data results only reflect the patterns planted in the synthetic dataset. Keep the predictive component out of the core MVP unless adequate data and evaluation are available.

Reports should support filters (institution, bank, reference, status, dates, assigned office, issue/priority), drill-down to source records, and export to a suitable format if authorized. Dashboard numbers must be defined consistently and match the underlying records.

## 5.10 Audit trail and tamper evidence

For material events, record:

- Actor/service identity.
- Timestamp.
- Action and affected record.
- Before/after values where appropriate.
- Reason/comment where required.
- Document version/hash or evidence reference.
- Policy/rule version relevant to the decision.
- Verification/approval outcome.

An append-only event approach and a hash chain can make ordinary alteration detectable. Each event hash can include the previous event hash; a verification screen should replay the chain and report failures. A tamper test should edit a copied/test event and show that the chain check fails.

Do not claim absolute immutability. A sufficiently privileged database/system operator may be a residual threat without external anchoring or independent controls. The prototype can prove tamper detection in its chosen test, not impossibility of all tampering.


## 5.11 AI-Assisted Intelligence and Smart-Automation USP Catalogue

This section incorporates eight candidate differentiators supplied after the original context was prepared. These are **proposed optional enhancements**, not additional requirements expressly mandated by PS 26265. The official requirements remain the controlling scope. Add these features only where the core lifecycle workflow is reliable, privacy is protected, and the feature can be demonstrated and evaluated honestly.

### USP 1 — Vision-LLM FDR extraction and field reconciliation

**User value:** reduce repeated typing and make it easier to compare the institution's form values with the uploaded FDR.

**Proposed flow:** upload FDR scan/PDF → render/extract pages → call an approved vision-capable model with a fixed JSON schema → validate output types and fields → display extracted values alongside institution-entered values and document evidence → user/officer confirms or corrects → accepted values are saved with provenance and an audit event.

Candidate output fields: bank name, branch where visible, FDR number, amount, issue date, maturity date, depositor/institution name, and whether AICTE is mentioned as lien holder/beneficiary where the document explicitly says so.

**Controls:** output is tagged `Vision-LLM-Extracted` (or `OCR-Extracted`), never “verified”; low-confidence/ambiguous values need human review; extracted-versus-entered conflicts produce flags; the model must not make up missing values; schema validation and field-level tests are required. Use synthetic or authorized anonymized files for demos, and do not send sensitive raw FDRs to an external API without formal approval and appropriate data-handling safeguards.

**Priority:** optional Phase B/C, after manual submission and deterministic validation work. This is useful document-entry assistance, not a trust upgrade.

### USP 2 — Explainable tamper and anomaly flags

**User value:** identify records needing further scrutiny and make the reason visible to officers.

Candidate checks: same FDR reference across institutions; identical file hash; metadata suggestive of editing or timestamps that appear inconsistent with claimed issue dates; maturity before issue date; mismatches between form and document; and financial-term inconsistencies only when the underlying terms are present and authoritative.

**Output:** flags list the rule/check, input evidence, comparison result, severity if configured, and next action. Distinguish deterministic date/field rules from heuristic metadata/image indicators. Use the label “Advisory — human review required” for uncertain signs. A re-saved legitimate PDF can produce metadata indicators; a hash match proves only byte identity; neither is proof of fraud.

**Priority:** basic deterministic checks belong in the core; exact-file-hash and reference duplicate detection are high-value extensions; PDF forensic/image heuristics are later and must be described as weak indicators.

### USP 3 — Transparent risk-priority score (0–100)

**User value:** turn a flat list into a work queue that helps officials decide which case needs attention first.

A simple configurable weighted formula may combine days to maturity, trust/verification state, missing required documents, unresolved discrepancy severity, overdue action age, and prior renewal delays where recorded history exists. Example logic: an instrument nearing maturity while still unconfirmed and missing required evidence should rank higher than a complete, verified instrument with ample time remaining.

The exact weights should be chosen and documented by the team for the prototype, not presented as an AICTE-approved policy or learned model. Show the score breakdown, factors, data source and configuration version. Never interpret the number as a probability of fraud or use it to authorize/deny release. Missing data must remain unknown rather than be automatically scored as misconduct.

**Priority:** Phase B if time permits. The simpler alternative is a transparent filter/sort by urgency, discrepancy and trust state; never sacrifice correct underlying state transitions to add scoring.

### USP 4 — Natural-language search over records

**User value:** allow officers to ask operational questions in everyday language, e.g., “Show FDRs maturing in the next 30 days that are not bank-verified.”

**Proposed flow:** LLM maps the question to a restricted structured-filter schema (approved fields, operators, bounded date ranges, sort and pagination) → backend validates the schema and user permissions → parameterized read-only query executes → results include the filter interpretation and matching records.

The model must not receive direct database credentials or generate/execute arbitrary SQL. Enforce access permissions in the backend even if the LLM requests broader results; restrict tables/fields and operations using an allow-list; log the query interpretation; and test ambiguous or malformed requests. If meaning is ambiguous, ask for clarification or show the interpreted filter before execution.

**Priority:** Phase C. Regular search/filter controls and reports already satisfy the core PS and should be built first.

### USP 5 — Evidence-grounded scrutiny summary

**User value:** help an officer or senior reviewer understand an older case without re-reading every item from scratch.

**Proposed output:** a short draft note summarizing what was submitted; which values are institution-declared, extracted, officer-reviewed or bank-confirmed; what documents are missing; current discrepancies and pending actions; maturity/deadline status; and a suggested next administrative step supported by recorded facts.

Generate only from structured system records and linked evidence. Each material assertion should be traceable to a field, document, event or verification record. If the source does not establish a fact, say it is unavailable/unknown. The officer must edit/review the draft. When accepted, store it as the officer's adopted note with user identity, time and audit history; do not attribute an unreviewed model output to the officer.

**Priority:** Phase C or a later UX enhancement, after the evidence and audit models are complete. The summary must not become an independent regulatory opinion.

### USP 6 — Auto-drafted notices and bilingual communication

**User value:** reduce repetitive correspondence for renewal reminders, deficiency notices and release/refund status updates.

**Preferred design:** begin with approved templates populated with verified system fields (institution name, instrument reference, deadline, missing item, case reference, status and contact instructions). Template-driven notices are predictable and may be sufficient without an LLM. A language model may optionally help create a Hindi translation or improve clarity/tone, but must preserve fixed legal/administrative wording and exact dates/references.

Every notice must be validated against its source case and approved template. An authorized officer should approve notices before external dispatch, at least for the prototype and any legally material message. Record the generated version, reviewer, approval and dispatch outcome. Do not let a model invent regulatory requirements or promise a release date.

**Priority:** basic template-based notifications belong in the core workflow; LLM drafting/translation is optional Phase C and a weaker differentiator than trust, lineage, deadline controls and gated release.

### USP 7 — Maturity-load forecast and optional renewal-risk prediction

**User value:** give the Regulation Bureau an early view of upcoming maturity workload.

**Maturity-load chart:** group recorded instrument maturities by month and show counts and total recorded amounts. This is deterministic analysis of the current database and should be feasible before advanced AI work.

**Renewal-miss prediction:** estimating which institutions may miss renewal requires representative historical data about due dates, notification delivery, actual renewal submissions, delays and outcomes. Such data is not established as available in the documents. On a synthetic dataset, a model would only demonstrate the patterns deliberately built into that dataset and must not be marketed as validated prediction.

**Priority:** include deterministic maturity aggregation in dashboard/reporting if time allows; defer predictive renewal risk until authorized historical data and a sound validation set exist.

### USP 8 — Document-type classification and completeness checking

**User value:** identify what a user actually uploaded, not merely whether some file was uploaded.

**Proposed flow:** classify each upload (candidate classes could include FDR copy, bank-confirmation evidence, lien/pledge letter, release/refund request letter, affidavit or payment evidence where applicable) → compare the detected/confirmed document type with the checklist for the relevant case and policy version → identify missing, unreadable, wrong-category or pending documents → show the institution a clear deficiency list and the officer a case-level completeness view.

The required document set must be configurable by case type, institution/instrument type and effective policy version. The uploaded research references specific examples of release documentation, but the team must validate current prescribed requirements with the applicable AICTE source and authorized personnel before encoding them. Do not infer that every example is mandatory for every case. Classification should have confidence/manual correction; a file's presence does not prove its content is adequate or valid.

**Priority:** configurable checklist and missing-document tracking are core requirements. Automatic classification is an optional Phase B/C enhancement; manual category selection is an acceptable reliable fallback.

### Recommended prioritization of the eight USPs

| USP | Value for PS 26265 | Suggested priority | Key guardrail |
|---|---|---|---|
| Vision-LLM extraction | Reduces data entry and enables form/document comparison | Optional Phase B/C | Human confirmation; extracted is not verified; protect sensitive files |
| Tamper/anomaly flags | Supports discrepancy scrutiny | Core deterministic checks + optional advanced indicators | Flags are advisory; metadata/image signs do not prove fraud |
| Transparent 0–100 risk score | Prioritizes officer workload | Phase B | Explainable heuristic, not fraud probability or release decision |
| Natural-language search | Improves ad-hoc record discovery | Phase C | Read-only restricted schema; backend authorization; no arbitrary SQL |
| Scrutiny summary | Speeds case handover and review | Phase C | Grounded only in records/evidence; officer adopts final note |
| Auto-drafted notices | Reduces repetitive correspondence | Template notices core; LLM translation optional | Officer approval; no invented legal terms or deadlines |
| Maturity forecast | Helps plan upcoming workload | Deterministic chart as dashboard enhancement | Prediction requires real labelled history; synthetic predictions are not evidence |
| Document completeness/classification | Strongly supports missing-document requirement | Completeness checklist core; classifier optional | Configurable policy-specific checklist; human correction |

**Overall recommendation:** do not build all eight AI additions at once. Build the secure lifecycle, trust model, deterministic validation, deadline engine, lineage and release gate first. Add explainable duplicate/discrepancy checks and basic document completeness next. Vision extraction and transparent prioritization are the most directly demonstrable intelligent additions. Natural-language search, AI-generated summaries, LLM notice drafting and renewal-miss prediction are later options.

---

# 6. Proposed Lifecycle States and Data Model

## 6.1 Separate instrument state from trust state

A robust design should not use one status field for all meanings.

### Illustrative administrative lifecycle states

`Draft → Submitted → Under Scrutiny → (Correction Required / Discrepancy Raised) → Active / Monitored → Expiring Soon → Renewal/Replacement Due → Renewed or Matured → Release Requested → Approved/Rejected/Returned → Released/Closed`

Additional operational states may include `Overdue`, `Escalated`, `Verification Pending`, `Source Unavailable`, and `Disputed`. Some of these are better represented as flags or separate sub-statuses instead of mutually exclusive lifecycle states. Final state machine should be internally consistent and validated against the actual process.

### Trust state

Use L0/L1/L2/L3 as described in Section 5.5, independent from the administrative state.

### Why separation matters

An instrument can be submitted, near maturity, and unconfirmed simultaneously. One field cannot represent all three facts without losing meaning. A well-designed data model makes current status derived from a record of events, data and policy checks.

## 6.2 Suggested relational entities

Illustrative logical entities:

- `Institutions`
- `Users`
- `Roles`, `UserRoles`
- `Instruments`
- `InstrumentEvents` or `WorkflowActions`
- `Documents` / `DocumentVersions`
- `VerificationRequests`
- `VerificationResponses` / `VerificationRecords`
- `Discrepancies` / `ScrutinyObservations`
- `ReleaseRequests`
- `ChecklistItems` / `ReadinessAssessments`
- `Approvals`
- `Reminders` / `Notifications`
- `PolicyRules` / `PolicyVersions`
- `AuditEvents`

Recommended relationships:

- One institution → many instruments.
- One instrument → many documents, verifications, observations and lifecycle events.
- An instrument can point to a predecessor and/or successor, with constraints that prevent cycles or ambiguous lineage.
- One release request → required checklist items, observations and approvals.
- Every important workflow transition → related actor, evidence and audit event.
- Policy version → rule outcome/decision, so a historical decision can be interpreted under the rules that were in force at that time.

Do not build a vector database or complex AI orchestration as a default requirement for this structured workflow. Use database constraints and server-side transaction handling for integrity.

---

# 7. Suggested Technical Architecture

## 7.1 High-level flow

`Institution / Officer UI → API + Authentication/RBAC → Rules and State Engine → PostgreSQL + Secure Document Store`

Supporting components:

- Background scheduler/worker for deadline checks, reminder dispatch, retries and catch-up jobs.
- Verification adapter to a bank channel when authorized, or a clearly labelled mock/manual workflow in the prototype.
- Release gate/maker-checker logic for readiness and role separation.
- Append-only/hash-chain audit and verification screen.
- Notification provider (in-app/email for MVP; SMS/WhatsApp only if implemented/approved).
- Report/export service.

## 7.2 Recommended stack (one reasonable option)

| Layer | Suggested option | Purpose / caution |
|---|---|---|
| Frontend | React + TypeScript + Tailwind | Institution portal and official console; the UI should make source/verification states explicit. |
| Backend | FastAPI + Python | APIs, validation, state transitions, permissions, release workflow, reports. |
| Database | PostgreSQL | Structured records, relational integrity, workflow/audit events, indexes and reports. |
| Document store | Local or S3-compatible object storage such as MinIO/S3 | Secure instrument documents and versions; permissions and encryption required. |
| Scheduler/worker | APScheduler/Celery Beat or equivalent | Reliable deadline jobs, reminder dispatch, retries and escalation. A queue/Redis can be added if needed. |
| OCR / Vision-LLM (optional) | PaddleOCR/docTR/Tesseract, or an approved vision-capable model | Structured field suggestions only; schema validation, provenance labels, and human confirmation required. A real external model call needs approval and data safeguards. |
| Optional LLM helper service | Approved provider or self-hosted deployment | Restricted to structured extraction, read-only query-to-filter mapping, or evidence-grounded draft summaries/notices; never release decisions or unrestricted database access. |
| Notification | SMTP/local mail catcher for demo; approved gateway later | Demonstrate notification events and logs; mock SMS/WhatsApp clearly. |
| Authentication | Organization-approved identity provider or secure role-based implementation | RBAC and least privilege; official SSO/MFA only if accessible and required. |
| Audit | Append-only event records with hash chaining | Detect alteration in a verification test; explain residual privileged-admin risk. |
| Deployment | Docker Compose initially | Reproducible local demo and test environment; production architecture depends on AICTE IT/security requirements. |
| Tests | Unit/API/integration tests | State machine, rule engine, permissions, reminder idempotency and audit integrity. |

This is a recommended option, not the only valid architecture. The project should avoid unnecessary distributed services and AI orchestration. A modular monolith plus a worker is simpler to build and explain.

## 7.3 Data/security safeguards

- Role and record-scoped authorization on every endpoint.
- Institution tenant isolation; test that Institution A cannot read Institution B's records.
- Encryption in transit and at rest where available.
- Mask sensitive fields in overview lists.
- Validate and scan uploaded files; restrict file type and size.
- Do not send confidential raw records/FDR scans to external LLM services without explicit authorization, approved provider/data-handling terms, and appropriate security review. If optional LLM features are added, use approved/self-hosted processing or a controlled redacted input where suitable. For the core lifecycle application, an LLM is unnecessary; optional model calls must never become the source of truth or the release decision-maker.
- Back up records and test recovery according to target deployment needs.
- Protect audit logs and log authorization failures.
- Use versioned, approved policy; audit configuration changes.
- Define retention and privacy controls with the relevant authority/legal review.

---

# 8. Prototype Scope and Build Priorities

## 8.1 Phase A — Must work end-to-end

1. Institution and instrument registry.
2. Authentication and 3–4 practical roles (institution, scrutiny/verifier, approver/finance as needed, administrator/auditor with appropriate restrictions).
3. Instrument submission and secure document upload/versioning.
4. Deterministic rule engine and explainable discrepancy flags.
5. Trust-level/provenance model.
6. Instrument state machine with permitted server-side transitions.
7. Maturity/validity monitor and configurable reminders.
8. Renewal/replacement lineage.
9. Release/refund request, checklist, blocker display and controlled approval.
10. Dashboard and essential reports.
11. Append-only audit history and verification.
12. Automated tests for the mandatory PS scenarios.

## 8.2 Phase B — High-value demonstration differentiators

- Simulated bank response page/request flow, clearly marked SIMULATED.
- Cross-institution probable duplicate reference detection and exact-file hash detection, with officer review.
- Required-document completeness checklist and guided deficiency/correction flow that preserves document versions. Manual document-category selection is an acceptable fallback.
- Transparent work-priority queue based on days to maturity, overdue age, discrepancy severity, missing evidence and trust state. A 0–100 heuristic score is optional and must show its breakdown and disclose that weights are prototype assumptions.
- Escalation beyond a first reminder.
- Hash-chain verification and controlled tamper test.
- Deterministic maturity-load chart by month (instrument counts and/or amounts).
- Optional Vision-LLM/OCR field prefill only if the core flow is stable, approved/synthetic documents are available, and the demo can show extraction provenance plus human correction.
- Exportable report and a visible log of notifications.
- Test-only date-advance control for demonstrating deadline logic.

## 8.3 Phase C — Roadmap, not necessary for a credible core demo

- Better Vision-LLM/OCR extraction for varied layouts, with confidence/uncertainty handling and human confirmation.
- More advanced document metadata/image anomaly indicators, always advisory and subject to false positives.
- Natural-language search translated into a restricted, validated, read-only filter schema; no arbitrary SQL or unrestricted database access.
- Evidence-grounded scrutiny summaries that the officer edits and adopts.
- LLM-assisted Hindi/English drafting/translation on top of approved notice templates; officer approval before dispatch.
- Prediction of missed renewals only after authorized historical data and an evaluated labelled dataset are available; synthetic-only prediction is a demo, not a real-world claim.
- Authorized live bank-verification interface.
- Authorized AICTE/legacy-system integration or SSO/DSC.
- Further bilingual interface/templates, pilot with an AICTE/authorized stakeholder, after access approval.

Do not claim Phase B/C work is implemented unless the actual code/demo supports the claim.

## 8.4 Suggested work ownership for a six-member team

This is a planning suggestion from the main research document, not a required team structure:

1. Team lead/product owner, demo storyline, presentation and integration coordination.
2. Backend/data model/API/RBAC.
3. Rules engine, state machine, scheduler, notifications and escalations.
4. Officer console/dashboard and queue UI.
5. Institution submission and release workflow UI; simulated bank interface.
6. QA/DevOps, synthetic data, test automation, audit verification and metrics.

## 8.5 Suggested short-build critical path

`Data model → authentication → submission/upload → rules → state machine → scheduler/reminders → renewal lineage → release gate → audit/tests → demo rehearsal`

If time is constrained, protect the core lifecycle and six required test scenarios. Cut OCR or advanced analytics before cutting release gating, trust-state honesty, replacement history or auditing.

---

# 9. Synthetic Data and Demonstration Plan

All examples must be visibly fictional. Do not use real institution or bank details unless formally authorized. Documents A and B suggest different illustrative dataset sizes (about 60 institutions/120 instruments versus 30–50 institutions/200–500 instruments); the official problem statement sets no dataset-size requirement. Pick a size the team can validate and explain.

## 9.1 Mandatory scenarios from the problem statement

1. New FDR submission.
2. Validity tracking.
3. Approaching maturity and notification.
4. Renewal/replacement.
5. Discrepancy identification.
6. Authorized release processing.

## 9.2 Valuable additional scenarios from the research

7. Clean submission: all required fields/documents present; no rule flags; trust remains at the correct level pending verification.
8. Name mismatch plus amount shortfall: two separate explainable flags; no silent activation.
9. Duplicate FDR reference across fictional institutions: probable duplicate flagged for human scrutiny.
10. Bank verification timeout/source unavailable: status remains pending/unconfirmed and retries/alerts are logged.
11. Correction/resubmission: earlier version remains in history.
12. Renewal chain A → B: old record not overwritten; successor link and dates are visible.
13. Release request with an unresolved observation or missing clearance: blocked with reasons.
14. After blockers are resolved, one authorized role submits/reviews and a different permitted role approves where maker-checker applies.
15. Institution A tries to access Institution B's record: denied.
16. Unauthorized user tries to alter trust level or approve a release: denied and logged.
17. Audit chain passes before a controlled test alteration and fails afterward.
18. Reminder job failure/restart: catch-up happens without duplicate notifications.

## 9.3 Suggested demo narrative

A recommended story:

1. An institution submits a synthetic FDR; the screen shows L0 — Declared.
2. Deterministic validation identifies a deliberately seeded mismatch; the officer sees the source/expected values and rule explanation.
3. The institution corrects/resubmits, preserving the earlier document/field history.
4. The officer records the verification review and initiates bank confirmation.
5. The demo bank adapter returns a matching result, mismatch, or timeout, with the response explicitly labelled simulated.
6. The admin advances the demo clock to a policy-configured maturity threshold; the scheduler creates the reminder and queues escalation if no action occurs.
7. A new instrument is submitted as a replacement; the original and successor are visibly linked.
8. The institution asks for release while a required observation remains unresolved; the gate blocks release and lists blockers.
9. After blockers are resolved, the authorized approval path is completed.
10. An auditor checks the timeline/hash chain, then runs a controlled tamper test and sees verification fail.

This demo shows the product's core guarantee: no silent trust upgrade, no loss of lineage, no unauthorized release and an auditable event history.

## 9.4 Truthful demo disclosure

The presentation should have a clear status legend:

- **Implemented:** functioning in the actual prototype.
- **Simulated:** test bank responses, fictional records, mocked SMS/WhatsApp or test-clock actions.
- **Planned / integration-dependent:** live AICTE systems, real bank API, institutional SSO/DSC, or any service not available to the team.

The example implementation plan in Document A mentions a local email catcher for demo email. Use it only if actually implemented. Do not convert a design plan into a claim of current implementation.

---

# 10. Evaluation Metrics and Proof Requirements

## 10.1 Core functional gates

- All problem-statement test scenarios pass.
- No L3/bank-confirmed record exists without a corresponding confirmation record/evidence.
- A source timeout/unavailable response cannot cause a confirmed state.
- No instrument replacement overwrites its predecessor's history.
- No release transition succeeds with mandatory blockers still open.
- Unauthorized cross-institution access is denied.
- Audit-chain tampering in the controlled test is detected.
- Reminder processing is idempotent and failed jobs can be recovered.

These are proposed acceptance tests, not claims of existing test results.

## 10.2 Performance/impact metrics to collect

| Metric | Definition / method | Important limitation |
|---|---|---|
| Record completeness/accuracy | Share of mandatory fields present; compare values to source documents on a reviewed sample | Requires source review and agreed definitions. |
| Verification turnaround | Elapsed time from verification request/submission to recorded outcome | Real-world timing depends on bank/authority response; a simulation only measures the local flow. |
| Discrepancy precision/recall | Compare flags against deliberately seeded and labelled discrepancies | Synthetic performance does not establish real-world performance. |
| Reminder timeliness | Eligible reminders generated/delivered within configured thresholds in a time-advance test | Test metrics are not production notification SLAs. |
| Notification reliability | Successful delivery attempts / eligible reminders; count duplicates and failures | Depends on actual channel and test environment. |
| Time to answer a maturity query | Time required to find all instruments due within a specified window | Define data volume and test conditions. |
| Manual effort | Compare staff minutes per case using a baseline or controlled test | Do not invent savings or percentages before measurement. |
| Overdue/lapse visibility | Count cases whose defined due condition was not surfaced/actioned | Real lapse-reduction claims need an authorized pilot. |
| Release-block enforcement | Count attempted releases correctly blocked with relevant reasons | Core pass/fail test. |
| Audit completeness | Share of sampled material actions with actor/time/reason/evidence | Requires an agreed definition of a material action. |
| Audit tamper detection | Controlled mutation changes hash-chain verification outcome from pass to fail | Demonstrates the test design, not absolute immunity. |
| Usability | Task success/time or an agreed survey such as SUS with identified participants | Student testers are not necessarily representative AICTE staff. |
| Field-extraction quality (if OCR/Vision-LLM is built) | Exact-match rate per field/document type; separately report missing/uncertain values and human correction rate | Requires labelled scans; synthetic results may not generalize to real bank layouts. |
| Form/document reconciliation | Number and type of planted form-versus-document differences correctly flagged | Compare with a seeded answer key and report false positives/negatives. |
| Anomaly-flag quality | Precision/recall separately for reference duplicates, identical-file hashes, date rules and heuristic metadata indicators | Do not pool hard deterministic rules and weak forensic signals into one misleading accuracy number. |
| Completeness-check quality | Required document types correctly identified as present/missing/wrong-category against the configured checklist | Checklist must be correct and versioned; document presence does not prove adequacy. |
| Risk-priority queue usefulness | Share of seeded urgent cases ranked in the selected top-N; report each score factor | Prototype weights are assumptions and do not establish real-world risk prediction. |
| Natural-language search safety | Correctly interpreted structured filters; rate of rejected unsafe/unsupported requests; authorization leakage tests | Must remain read-only and enforce permissions in backend. |
| Summary/notice grounding | Percentage of generated factual claims matched to source records; officer correction rate; wrong/missing date or identifier count | Requires reviewed test cases; model output remains a draft. |
| Maturity aggregation accuracy | Monthly count and total amount match independently computed database results | Deterministic calculation should be testable; predictive renewal-risk measures need separate historical validation. |

Never put target percentages on the presentation as completed performance. Label each result as **measured**, **target**, **simulation result**, or **future pilot metric**.

---

# 11. Six-Slide SIH Presentation — Consolidated Blueprint

## Slide 1 — Title and identity

**Title:** FDR SENTINEL — Security Deposit / FDR Lifecycle Integrity  
Include: SIH 2026, Problem Statement ID 26265, complete PS title, AICTE, Regulation Bureau, Smart Automation, Software, registered team name/ID and members.

Visual: one lifecycle line — Submit → Validate → Verify → Monitor → Renew/Replace → Release Gate → Audit. Highlight **“Declared ≠ Confirmed.”**

Avoid claims such as “India's first” or “AICTE has no FDR portal.”

## Slide 2 — Idea / proposed solution

Core message: **The challenge is lifecycle trust, not just record storage.**

Describe the problem: instrument details, documents, confirmation status, deadlines, renewals and release conditions need to remain connected and current.

Acknowledge existing AICTE online deposit/refund-related processes found in the research. Position the product as a complementary lifecycle-integrity and monitoring layer, subject to validation and authorized integration.

Show five solution cards: Trust Ledger; Explainable Discrepancies; Renewal Lineage; Maturity Escalation; Release Gate + Verifiable Audit.

## Slide 3 — Technical approach

Show:

- Institution/officer UI.
- API and RBAC.
- Deterministic rule/state engine.
- PostgreSQL and document store.
- Scheduler/worker and alerting.
- Verification adapter with SIMULATED response in prototype.
- Release gate/maker-checker.
- Append-only/hash-chain audit.

Include L0–L3 trust levels and a simple predecessor/successor chain. Distinguish deterministic checks from optional OCR field suggestions. No LLM/AI path for release decisions.

Suggested sentence to say: “Our differentiator is an enforced lifecycle: status can only advance when the required evidence and authorization exist. The UI reflects the rules; it is not the source of truth.”

## Slide 4 — Feasibility and viability

Show MVP scope, stack, one modular architecture, and risk/fallback matrix:

- No bank API → labelled simulator/manual confirmation workflow.
- Rules vary → versioned/configurable policy, validated by authorized AICTE personnel.
- Scheduler downtime → health alert and catch-up job.
- OCR uncertainty → human confirmation.
- Missing authorization → release remains blocked.
- Real AICTE/bank integration → only if formally authorized and available.

Do not suggest that all integrations already exist or are approved.

## Slide 5 — Impact and benefits

Demonstrate one fictional FDR from declared state through discrepancy, confirmation state, maturity reminder, renewal link, release gate and audit.

Show a transparent queue based on days to maturity, overdue age, discrepancy severity and trust state. If a score is used, show how it is calculated.

Metrics: time to answer “what matures in the next N days?”, verification-state coverage, reminder timeliness, seeded discrepancy detection, blocked release attempts and audit tamper detection. Label as evaluation metrics until measured.

## Slide 6 — Research and references

Suggested references supplied by Document C:

- SIH PS 26265 text (the document describes this as a mirror; compare against the official SIH portal before citation): https://zaidsayyed.in/tools/sih-problem-statements/sih26265
- AICTE e-Governance RFP, cited JFDR section 7.2.2: https://aicte.gov.in/sites/default/files/RFPeGov.pdf
- AICTE Approval Process Handbook 2024–27: https://aicte.gov.in/sites/default/files/APH%20Final.pdf
- NeSL electronic bank guarantee overview: https://www.nesl.co.in/electronic-bank-guarantee-e-bg/ — use only as an e-BG precedent; explicitly state that a bank guarantee is not an FDR and this does not prove the existence of an FDR API.

Finish with a requirement-to-feature mapping and a simple “implemented / simulated / requires authorization” legend.

---

# 12. Likely Jury Questions and Defensible Answer Points

These are preparation notes, not claims that the team has already delivered the described functions.

### What problem are you solving?

The lifecycle control and trust problem for security deposits/FDRs: authorized stakeholders need to know what is recorded versus confirmed, what deadlines are approaching, what actions remain outstanding, and whether release conditions and authorization are complete.

### Doesn't AICTE already have a security-deposit system?

The research identifies public AICTE material describing online deposit-payment/amount-checking and a JFDR refund/status workflow. Do not claim there is no system. Explain that FDR Sentinel is proposed as a complementary lifecycle-integrity, provenance, monitoring and release-readiness enhancement; the exact gap needs validation with AICTE stakeholders.

### What is genuinely differentiated?

Not the choice of framework or the number of AI components. The proposed differentiators are enforced trust transitions, field-level source provenance, explainable flags, unbroken renewal lineage, a release gate with authorization, and a verifiable event history.

### How will you verify without a bank API?

Use an explicit manual confirmation workflow and/or a simulated adapter for the prototype. Keep officer-reviewed L2 separate from bank-confirmed L3. A simulated response must be labeled and cannot be described as live integration.

### Does OCR prove that an FDR is genuine?

No. OCR extracts possible fields. Rules check consistency. An authorized bank confirmation or accepted verification mechanism is different evidence. The system flags inconsistencies and routes them for review; it does not claim that image analysis proves forgery.

### Why not use AI for approvals?

The central workflow is made of explainable rule checks, dates, permitted transitions and explicit authorities. AI may assist with optional document extraction, read-only search, prioritization or draft writing, but every such output is advisory and auditable. Legal/financial approval remains with the competent authority.

### What are the proposed AI/automation USPs beyond basic FDR tracking?

The candidate additions are: (1) Vision-LLM extraction with human confirmation; (2) explainable duplicate/tamper/anomaly flags; (3) a transparent rule-based 0–100 priority score; (4) natural-language search translated into safe read-only filters; (5) evidence-grounded scrutiny summaries; (6) template-first notices with optional Hindi/English LLM assistance; (7) deterministic maturity-load charts, with renewal-miss prediction deferred until suitable historical data exists; and (8) document-type classification against a configurable completeness checklist. These are optional enhancements, not all core requirements. The team should implement only a few after the lifecycle fundamentals work.

### How will Vision-LLM extraction be kept trustworthy?

Show extracted fields as suggestions, retain document/source provenance, compare them against the form, highlight uncertain/conflicting fields and require human confirmation. Extraction is not verification and cannot upgrade the record to bank-confirmed.

### How can anomaly flags avoid falsely accusing an institution of fraud?

State the exact rule/evidence and label heuristic metadata/image indicators “advisory — human review required.” A duplicate hash or edited-looking metadata does not prove fraud. Use officer review and record how each flag is resolved.

### Why add a risk score if the model is not trained?

It is a transparent, configurable work-priority heuristic, not a learned probability or fraud score. Show the factors and their weights, disclose that initial weights are assumptions, and test usefulness on labelled synthetic scenarios.

### How can an LLM search records without exposing the database?

The LLM translates a natural-language question into an allow-listed structured filter. The backend validates the schema, applies the user's access permissions and executes a parameterized read-only query. The LLM has no direct database credentials and cannot run arbitrary SQL.

### Can an LLM write official notices or scrutiny notes?

It may draft from approved templates and recorded system facts, but the officer reviews and adopts the final text. No unsupported regulatory requirement, date, confirmation or release promise may be introduced. The final saved note/notice is attributed to the responsible official and audited.

### Is renewal-miss prediction feasible without real historical data?

Not as a validated real-world prediction. The monthly maturity-load chart is a deterministic count/amount aggregation. A missed-renewal predictor requires authorized, representative historical data and a labelled evaluation set; synthetic data can only show a limited demonstration.

### How do you handle rule changes?

Use versioned policy configurations with effective dates and an authorized process for changing them. The actual rule content and approval owner must be validated against current AICTE procedures.

### How do you prevent release without authorization?

Enforce release readiness and role separation on the backend. A request with mandatory blockers cannot advance. A different authorized role approves where the workflow requires maker-checker. Every attempt and decision is audited.

### What if the bank never responds or a channel fails?

Keep the status pending/unconfirmed, log the failed attempt, retry/route according to policy and notify the assigned official. Do not mark the instrument confirmed because a deadline has passed or an adapter has failed.

### How will you prove improvement?

Run the required scenarios, use seeded synthetic discrepancies with an answer key, and measure rule outcomes and reminder behavior. Compare manual-processing time to a measured baseline where feasible. Be transparent that synthetic tests do not prove real-world impact.

### How is audit integrity ensured?

Record an append-only, hash-chained event history and demonstrate verification. A controlled mutation should fail the test. Explain that this detects the tested alteration path but is not a claim of absolute immunity against every privileged operator.

### Can institutions view one another's records?

They should not. Enforce institution-level authorization on every relevant query/API and include a cross-tenant negative test.

### What will the prototype not do?

It will not move money, autonomously release/refund deposits, interpret regulations as a legal authority, or claim an unverified live bank/AICTE integration.

---

# 13. Risks, Unresolved Questions, and Mitigations

| Risk / unresolved question | Why it matters | Recommended response |
|---|---|---|
| Exact current AICTE lifecycle gap not independently validated | Could lead to a redundant product claim | Describe as a proposed complementary layer; validate with AICTE/authorized staff. |
| FDR bank API availability/access unknown | Cannot claim live verification | Manual workflow + clearly labelled mock adapter until an authorized integration exists. |
| Applicable deposit/release rules vary | Wrong hard-coded rules could cause a false block/approval | Version rules, use effective dates, and validate the applicable rule with AICTE. |
| Existing JFDR workflow | Proposal should not be framed as replacement | Position as lifecycle integrity/provenance/monitoring enhancement. |
| No real baseline metrics | Impact claims unsupported | Establish a baseline or present metric as planned evaluation. |
| Synthetic dataset limitation | Does not prove real-world accuracy | Identify it as synthetic; seek authorized data for a pilot later. |
| Scope creep from OCR, CV, forecasting, natural language | Could weaken the core demonstration | Prioritize workflow correctness and six mandated scenarios. |
| OCR errors / poor scans | Wrong field suggestions can become damaging if treated as facts | Confidence labels, evidence and mandatory human confirmation. |
| False-positive discrepancy flags | Name formatting or reference variations may trigger flags | Explain rules; allow reasoned review/dismissal where permitted; audit resolution. |
| Reminder worker downtime | Missed deadlines | Health monitoring, retry and catch-up processing, idempotency. |
| Institution data exposure | Confidential records | Tenant isolation, least privilege, encrypted storage, protected links and access logs. |
| Audit hash-chain overclaim | A chain is not absolute immutability | Describe exactly what is protected and what the tamper test proves. |
| Approval role ambiguity | Wrong official could approve release | Confirm roles/authority matrix; implement least privilege and maker-checker as required. |
| Unknown production IT requirements | Stack/deployment could be incompatible with AICTE | Treat stack as prototype recommendation; confirm approved hosting/security architecture before production. |
| User adoption/legacy data | Staff may retain existing spreadsheets or duplicate work | Consider controlled bulk import, clear guidance, familiar tables and a pilot. |

## Questions to resolve before a real deployment

1. Which current handbook/rule version applies to each institution type and instrument/case type?
2. What is the official release checklist for the particular FDR/security deposit cases in scope?
3. Which officers/sections can scrutinize, verify, recommend, clear, approve and close a case?
4. What systems currently record deposit payment, FDR records, release requests and JFDR application status?
5. Is there an approved bank verification channel, and for which banks/instrument types?
6. What are the approved document formats, retention periods, audit retention and privacy/security standards?
7. Which identity provider/SSO and hosting environment must be used?
8. What notification channels are permitted and who receives each category of reminder?
9. Is legacy-data migration in scope, and what data-cleaning/ownership process applies?
10. Which metrics and baseline process can an authorized pilot measure?

---

# 14. Product Naming and Positioning Decisions

The uploaded documents use two working names:

- **FDR Vault** in the 18-page comparative research PDF.
- **FDR Sentinel** in the main design document's later recommendation and the final 6-page decision brief.

For continuity, the recommended project name for presentation and future work is **FDR Sentinel**. It is a proposed name, not an existing official AICTE system.

Recommended one-line positioning:

> **FDR Sentinel is a trust-first lifecycle-integrity layer for AICTE-related security deposits/FDRs: it distinguishes declared from confirmed information, preserves renewal lineage, monitors deadlines, gates release on required evidence and authorization, and maintains a verifiable audit history.**

Recommended short tagline from Document C:

> **Know what is declared. Know what is proven. Never silently lose a lifecycle event.**

Avoid claims such as:

- “AICTE does not have any FDR portal.”
- “Real-time bank verification is integrated” unless it actually is and can be substantiated.
- “AI detects forged FDRs” as a proven guarantee.
- “The solution reduces processing time by X%” until measured.
- “The audit log is impossible to tamper with.”
- “The system automatically approves or releases a deposit.”
- “NeSL e-BG verifies ordinary FDRs.”

---

# 15. Source Documents and References

## Uploaded source files summarized here

1. **`SIH 2026 – Security Deposit FDR Portal Research, Solution Design & Jury Evaluation.docx`** — 38 pages. Broad problem analysis, AICTE context research, stakeholders, user stories, functional/non-functional requirements, architecture, MVP plan, evaluation, jury Q&A and final recommendation.
2. **`SIH 2026 Research SIH26261 vs SIH26265 (AICTE).pdf`** — 18 pages. Comparison between PS 26261 and PS 26265; detailed FDR design, alternative features and technology choices.
3. **`SIH_2026_AICTE_PS_Decision_and_6_Slide_Strategy.docx`** — 6 pages. Focused recommendation for FDR Sentinel, existing-process caveat, Trust Ledger, flagship demo, evaluation gates and six-slide pitch plan.
4. **User-provided official problem statement text in the conversation** — controlling functional scope for PS 26265.

## External URLs cited by Document C (verify before formal submission)

- SIH PS 26265 public mirror mentioned in the decision brief (verify against official SIH portal): https://zaidsayyed.in/tools/sih-problem-statements/sih26265
- AICTE e-Governance RFP, cited JFDR section 7.2.2: https://aicte.gov.in/sites/default/files/RFPeGov.pdf
- AICTE Approval Process Handbook 2024–2027: https://aicte.gov.in/sites/default/files/APH%20Final.pdf
- NeSL Electronic Bank Guarantee overview: https://www.nesl.co.in/electronic-bank-guarantee-e-bg/

**Citation discipline:** The existence of an official document does not mean every claim in these summaries has been independently rechecked against its latest version. Check the current source and relevant clause/page before relying on legal/regulatory detail or presenting a claim as definitive. NeSL e-BG pertains to bank guarantees and must not be treated as evidence of FDR API access.

---

# 16. Final Consolidated Summary

Problem Statement 26265 asks for a secure, centralized and user-friendly way to manage security deposits/FDRs across their administrative lifecycle: recordkeeping, document submission, verification support, discrepancy handling, validity and maturity monitoring, reminders/escalation, renewal/replacement, release/refund requests, dashboards, reports, audit trails and secure access.

The three documents converge on a proposed solution called **FDR Sentinel**, a complementary lifecycle-integrity layer designed around four core guarantees:

1. **Trust is explicit:** institution-declared, document-consistent, officer-verified and bank-confirmed information cannot be confused.
2. **Lifecycle history is preserved:** renewal/replacement events link old and new instruments instead of overwriting history.
3. **Time-sensitive actions are surfaced:** policy-configured reminders, overdue flags and escalation make pending work visible.
4. **Financial actions are controlled:** release readiness is checked, blockers are explained, competent-authority approval is required, and each action is auditable.

The minimum credible prototype should implement the repository, document history, deterministic validation, trust status, reminder scheduler, renewal lineage, release gate, RBAC, dashboard and audit history. It should pass the official six PS scenarios and preferably also demonstrate a duplicate case, source timeout, cross-tenant authorization denial and controlled audit-tamper test.

Optional OCR/Vision-LLM and other AI-assisted features may improve data entry, document completeness, case prioritization, safe read-only search and draft preparation, but they remain advisory and are not the core decision-maker. Candidate USPs are: Vision-LLM FDR-field extraction with human confirmation; explainable tamper/duplicate/anomaly flags; a transparent 0–100 work-priority score; natural-language-to-filter search; evidence-grounded scrutiny summaries; template-first notices with optional bilingual LLM assistance; deterministic maturity-load reporting (and only later, data-backed renewal-risk prediction); and document-type classification against a configurable checklist. Add these selectively after the core workflow is proven. Protect sensitive financial documents when using model APIs, and never treat extracted values as verified. Simulated bank responses must be clearly labelled, no live integration should be claimed without authorization/evidence, and the design should acknowledge that AICTE has public deposit/refund-related processes already. The strongest positioning is as a complementary layer that adds trust provenance, lifecycle visibility and enforced controls, pending validation of the actual institutional gap.

All impact improvements must be measured rather than invented. Synthetic test success can demonstrate correctness of the prototype's rules/workflow, but not real-bank connectivity, production-level accuracy or proven operational savings.

**The core project principle:**

> Automate repetitive administrative work; make evidence, uncertainty and next actions visible; preserve the entire lifecycle; and keep financial/regulatory decisions within the prescribed authorization process.

---

## Future-session instruction

When continuing this project, use this `context.md` as the consolidated working reference. Keep official PS requirements separate from optional design choices; retain the FDR Sentinel name unless the user changes it; do not turn assumptions into facts; do not claim functionality is implemented unless there is code/demo evidence; and always keep the simulated-versus-real integration distinction explicit. Treat the eight AI/automation USPs in Section 5.11 as candidates, not commitments: prioritize core lifecycle correctness, document completeness, deterministic discrepancy checks, and provenance before advanced LLM features. Any external model use involving financial documents requires appropriate authorization and privacy/security review; all model-generated fields, searches, summaries and notices need the safeguards stated in this context.

