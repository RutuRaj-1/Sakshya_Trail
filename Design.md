# SakshyaTrail — Product Design System

**Document type:** Product UI/UX and frontend implementation specification  
**Product:** SakshyaTrail  
**Descriptor:** Security Deposit & FDR Lifecycle Integrity Platform  
**Primary tagline:** Every Record. Every Decision. Every Trail of Evidence.  
**Design direction:** Civic Ledger — Institutional Navy, Evidence Teal, Warm Paper, structured brutalism, selective glassmorphism  
**Status:** Proposed product design system for the SIH 2026 prototype; not an official AICTE visual identity standard.

---

## 1. Purpose and design intent

SakshyaTrail is an evidence-first lifecycle-integrity platform for tracking security deposits and Fixed Deposit Receipts (FDRs), from submission and scrutiny through verification, maturity, renewal, release/refund processing and audit.

The interface must feel like a carefully engineered institutional workflow product: credible, precise, calm, legible and accountable. It must not resemble a generic AI startup landing page or a decorative analytics dashboard.

The design combines:

- **Institutional visual language:** restrained navy, neutral surfaces, careful typography and consistent navigation.
- **Evidence-focused accents:** teal for supported evidence and progress; muted gold for selective emphasis and deadline attention.
- **Structured brutalism:** strong container boundaries, consistent grids, clear hierarchy and intentionally visible borders.
- **Selective glassmorphism:** translucent surfaces only where layering is meaningful, such as sticky navigation, command menus, dropdowns and modal overlays.
- **Operational clarity:** meaningful status labels, explainable blockers, readable tables, deterministic counts and clear next actions.
- **Accessible interaction:** keyboard support, sufficient contrast, responsive layouts, semantic HTML and non-colour status cues.

The public landing page may be more expressive. Authenticated operational screens must prioritize clarity, density and safe decision-making over visual effects.

### 1.1 Product identity

- Product name: **SakshyaTrail**
- Product descriptor: **Security Deposit & FDR Lifecycle Integrity Platform**
- Primary tagline: **Every Record. Every Decision. Every Trail of Evidence.**
- Landing-page headline: **From FDR Submission to Release — Every Step Accountable.**
- Supporting message: **Centralized records, evidence provenance, lifecycle monitoring and authorized release tracking in one traceable workflow.**

Use `SakshyaTrail` consistently in visible product branding. The SIH presentation sometimes uses `SAKSHYA-TRAIL`; camel-case is the recommended application wordmark. Do not blindly rename internal modules, Git repositories, package identifiers, environment variables, database tables or migration history when they are not user-facing.

Do not imply official AICTE endorsement, government ownership or affiliation that has not been authorized. Do not place the official AICTE emblem or State Emblem of India in product branding without proper authorization. SakshyaTrail should be described as a proposed complementary lifecycle-integrity layer, not a replacement for existing AICTE systems.

---

## 2. Design principles

### 2.1 Trust is communicated through evidence, not decoration

The UI should show what is known, the source of a value, who reviewed it, and which actions remain pending. Visual polish must never imply a stronger trust state than the underlying evidence supports.

### 2.2 Make status distinctions explicit

Keep these concepts separate everywhere:

- Administrative lifecycle status.
- Document completeness.
- Verification request/response status.
- Trust level (L0–L3).
- Maturity and validity state.
- Release/refund case state.
- Priority/urgency.

Never merge these concepts into a single generic “verified” or “healthy” badge.

### 2.3 Containerization first

Every meaningful UI region should have a clear boundary, title, purpose and consistent spacing. Use cards and panels intentionally rather than wrapping every small element in a separate card. Strong containment should make complex records easier to scan.

### 2.4 Effects are secondary

Glass blur, gradient, shadow and motion may reinforce visual hierarchy; they must not carry critical meaning. Core content remains clear and functional with effects disabled.

### 2.5 Honest system states

Distinguish zero results from loading, errors, unavailable policy, missing data, timeout and unconfigured functionality. Do not fabricate data to make a page appear finished.

### 2.6 Human-authorized decisions

AI/OCR output remains advisory. It cannot authorize verification, change trust state on its own, approve release or bypass the Release Gate. Simulated bank responses must visibly say `SIMULATED`.

---

## 3. Brand colour system

The following colours are the recommended **SakshyaTrail product palette**. They are design choices compatible with the product's existing navy/teal logo direction; they are not represented as official AICTE hex values.

### 3.1 Core palette

| Token | Hex | Usage | Avoid |
|---|---|---|---|
| `--st-navy` | `#123B5D` | Primary brand, primary buttons, links, selected navigation, headings | Using for every surface without contrast variation |
| `--st-ink` | `#0D2538` | Dense sidebar, footer, high-emphasis dark panels | Long blocks of tiny text without sufficient spacing |
| `--st-teal` | `#0F766E` | Evidence/progress accent, active indicators, positive workflow actions | Treating teal as proof of authenticity by itself |
| `--st-gold` | `#C69A48` | Decorative accent, small emphasis, selected markers, thin highlights | Small text on white or pale backgrounds; it is not a body-text colour |
| `--st-paper` | `#F5F4EF` | Main page background, warm neutral sections | Dense text directly over busy decorative backgrounds |
| `--st-white` | `#FFFFFF` | Cards, forms, modal surfaces and tables | Using white text on white or low-contrast glass |
| `--st-surface-muted` | `#EDF1F3` | Read-only groups, secondary panels, table headers | Confusing it with a warning state |
| `--st-text` | `#253746` | Primary body text, form labels, table contents | — |
| `--st-text-muted` | `#5D6A75` | Secondary text, helper copy and metadata on light surfaces | Using for very small low-contrast text over photography or glass |
| `--st-border` | `#8799A9` | Visible container boundaries, form outlines where contrast is needed | Using a faint border where a control's boundary is essential |
| `--st-border-subtle` | `#C9D3DB` | Dividers and non-critical card boundaries | Using as the only boundary for a critical interactive control if it is not distinguishable enough |

### 3.2 Semantic colours

| Token | Hex | Meaning |
|---|---|---|
| `--st-success` | `#18794E` | Successful operation; actual state still needs a text label |
| `--st-warning` | `#8A5A00` | Deadline attention, pending action, caution |
| `--st-danger` | `#B42318` | Critical blocker, rejected action, error or destructive-action warning |
| `--st-info` | `#245B7A` | Information, contextual help, neutral system state |
| `--st-neutral` | `#647482` | Neutral status, metadata and inactive states; use contrast-checked pairings |
| `--st-simulated-bg` | `#FFF3D6` | Background for a visibly simulated response label |
| `--st-simulated-text` | `#7A4B00` | Text in simulated-response indicators |
| `--st-focus` | `#145DA0` | Keyboard focus ring; ensure visible against adjacent surfaces |

Semantic colours identify workflow states; they do not independently establish trust or authenticity. Add text, icons and/or status descriptions. A simulated verification result must never be styled identically to a genuine bank-confirmed result without the visible `SIMULATED` label.

### 3.3 Colour usage ratio

As a practical guideline—not a strict mathematical rule—use:

- 65–75% neutral backgrounds and content surfaces.
- 15–25% navy/ink for structure, headings and navigation.
- 5–10% teal, gold and semantic accents combined.

Gold is a highlight, not a second primary colour. Reserve red for genuine critical states; do not use red as generic brand decoration.

### 3.4 Contrast requirements

Follow WCAG contrast guidance: target at least **4.5:1 for ordinary text** and **3:1 for large text**. Essential control boundaries and focus indicators must also remain perceptible. Do not rely on colour alone to communicate status.

Recommended initial pairings:

- `#123B5D` text on `#FFFFFF` or `#F5F4EF`.
- `#0D2538` text on `#FFFFFF`.
- `#253746` text on `#FFFFFF` or `#F5F4EF`.
- `#5D6A75` secondary text on `#FFFFFF` or `#F5F4EF`.
- White text on `#123B5D` or `#0D2538` for primary buttons and dark navigation.
- White text on `#0F766E` where the contrast has been verified for the actual component size and state.
- `#0D2538` or `#253746` text on the gold fill `#C69A48`.
- `#8A5A00` for warning text on white/light surfaces.

Do not use `#C69A48` as small text on white. Do not assume that every palette combination passes contrast. Validate actual rendered states, especially disabled buttons, placeholders, borders, translucent panels and badges.

---

## 4. Typography system

### 4.1 Recommended font family

Use **IBM Plex Sans** as the primary UI typeface and **IBM Plex Mono** for identifiers, hashes and other technical values.

This pairing is intentional: IBM Plex Sans is a legible, mature UI family with a more distinctive editorial/technical character than the default Inter-like look common in generated dashboards. IBM Plex Mono makes instrument references, audit IDs, hashes, event IDs and timestamps visually distinct without changing the overall brand.

Recommended stacks:

```css
:root {
  --st-font-sans: "IBM Plex Sans", "Segoe UI", Roboto, Arial, sans-serif;
  --st-font-mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
}
```

Use IBM Plex Sans for headings, body text, labels, navigation, tables and buttons. Use IBM Plex Mono selectively for:

- FDR/instrument references.
- Audit event IDs.
- SHA-256 hashes.
- Request/correlation IDs.
- Technical timestamps or policy identifiers where alignment matters.

Do not use monospaced text for whole paragraphs, all labels or large amounts of financial content.

### 4.2 Font loading

Inspect existing dependencies and asset management before installing font packages. Prefer the project's established method and use only needed weights. If local font packages are used, import the weights/styles actually required and check bundle impact. If fonts are loaded externally, retain robust system fallbacks and avoid making page rendering dependent on a third-party font server.

Recommended weights:

- 400 Regular: body text and long-form content.
- 450/500 Medium: labels, navigation, table headings and default controls.
- 600 SemiBold: section headings, card titles and key values.
- 700 Bold: page heading and primary emphasis, used sparingly.

Avoid using ultra-light font weights for a high-stakes financial/governance interface.

### 4.3 Type scale

Use a responsive scale. These are starting values; adapt where existing components or dense tables need smaller text without becoming inaccessible.

| Token | Desktop target | Mobile target | Use |
|---|---:|---:|---|
| `display` | 44–56 px | 34–40 px | Landing hero headline only |
| `h1` | 32–40 px | 28–32 px | Page title |
| `h2` | 24–30 px | 22–26 px | Major section heading |
| `h3` | 19–22 px | 18–20 px | Card or subsection title |
| `h4` | 16–18 px | 16–18 px | Panel title |
| `body-lg` | 17–18 px | 16–17 px | Hero/supporting introduction |
| `body` | 15–16 px | 15–16 px | Main content and instructions |
| `body-sm` | 13–14 px | 13–14 px | Secondary content; ensure contrast |
| `caption` | 12–13 px | 12–13 px | Metadata and helper text only; use carefully |
| `data` | 14–16 px | 14–16 px | Amounts, dates and queue data |
| `technical` | 12–14 px | 12–14 px | IDs and hashes in IBM Plex Mono |

Body line-height should generally be 1.45–1.65. Heading line-height should generally be 1.15–1.3. Do not use tiny text merely to fit more content on screen; allow wrapping, responsive column changes or scrolling instead.

### 4.4 Typographic character

Use normal sentence case for most labels and headings. Reserve uppercase for short section eyebrows, metadata labels and compact navigation. Avoid excessive letter spacing, oversized all-caps headings, decorative serifs throughout, or mixing many unrelated font families.

Use tabular numerals for aligned amounts, dates and metric totals where supported. Financial amounts should have consistent decimal/currency formatting and must not be visually truncated.

---

## 5. Spacing, grid and containerization

### 5.1 Spacing scale

Use a 4 px base unit. Preferred steps:

`4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80 px`.

Common defaults:

- Icon-to-label spacing: 8 px.
- Input internal padding: 12–16 px.
- Compact table cell padding: 10–12 px vertical and 12–16 px horizontal.
- Standard card padding: 20–24 px.
- Section separation: 32–48 px.
- Landing-page section separation: 64–96 px on large screens; reduce on mobile.

### 5.2 Grid and widths

- Large desktop main content max width: approximately 1,280–1,440 px.
- Standard page gutters: 32 px on wide screens, 24 px on medium screens, 16 px on mobile.
- Use a consistent 12-column or equivalent responsive grid for the landing page and dashboard.
- Let data tables occupy available width within the page container; use responsive column hiding or controlled horizontal scrolling for genuinely two-dimensional data.
- Do not create layouts that require horizontal scrolling at a 320 CSS px viewport except for content whose meaning requires a two-dimensional layout.

### 5.3 Card and panel taxonomy

Use a small number of consistent container types:

1. **Page shell:** overall page/background and responsive gutters.
2. **Workspace container:** primary authenticated content region.
3. **Section panel:** a group of related controls or data.
4. **Metric card:** one clearly defined count/value and its label.
5. **Record card:** concise record summary or mobile presentation of a row.
6. **Evidence panel:** document/provenance/source information.
7. **Overlay:** menu, popover, command palette or modal.

Each substantial panel should have consistent padding, title placement and action alignment. Do not wrap every single line, icon or field in a separate card. Containerization should clarify hierarchy, not fragment the whole page into dozens of floating boxes.

### 5.4 Border, radius and shadow

- Standard panel border: 1 px `--st-border-subtle`.
- Important or selected boundary: 2 px `--st-navy` or `--st-teal` where semantically appropriate.
- Form/control boundary: sufficiently visible against the actual surface; do not rely on a very pale line.
- Standard card radius: 8–12 px.
- Buttons and inputs: 6–10 px depending on control type.
- Dialogs: 12–16 px.
- Pills: fully rounded only for compact badges, status tags and small categorical markers.
- Standard elevation: restrained shadow plus border.
- Brutalist emphasis: an occasional crisp offset shadow, primarily on landing-page highlights or one featured panel. Avoid giving every card a thick black offset shadow.

---

## 6. Structured brutalism specification

The design uses **structured brutalism**, not deliberately broken or hostile usability.

### Use it for

- Strong section boundaries.
- Clear layout grids and alignment.
- High-contrast headings and purposeful whitespace.
- Visible borders around record groups and operational panels.
- Clear distinction between navigation, control surfaces and data regions.
- An occasional 2 px accent border for a selected queue, highlighted workflow step or featured information panel.
- Clear action placement and explicit button hierarchy.

### Do not use it for

- Indiscriminate thick black borders on all elements.
- Randomly overlapping text or cards.
- Intentional misalignment that harms scanability.
- Small text over decorative backgrounds.
- Decorative shapes behind financial amounts or audit evidence.
- Unexpected control positions or inconsistent navigation.

The visual result should be precise, architectural and grounded: the container structure is visible, while the information remains easy to use.

---

## 7. Selective glassmorphism specification

Glassmorphism is a supporting surface treatment, not the core layout system.

### 7.1 Appropriate use cases

Use translucent/blurred surfaces selectively for:

- Sticky public landing-page navigation when content scrolls underneath.
- Dropdown menus and popovers.
- Command palette/search overlay.
- Modal backdrop and selected dialogs.
- A limited decorative panel in the landing-page hero.
- Floating navigation controls where layering has a clear function.

### 7.2 Avoid glass on

- Dense data tables.
- FDR detail fields and critical financial values.
- Long-form instructions.
- Trust-level evidence descriptions.
- Release/refund readiness checklists.
- Audit trails and document metadata.
- Status indicators whose meaning depends on immediate legibility.
- Forms with many fields or validation errors.

Those surfaces should remain solid, high contrast and stable.

### 7.3 Glass recipe

Starting point only; review against the actual background and accessibility needs:

```css
.st-glass-panel {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.78);
  box-shadow: 0 8px 24px rgba(13, 37, 56, 0.10);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
}

@supports not ((backdrop-filter: blur(1px))) {
  .st-glass-panel {
    background: #FFFFFF;
  }
}
```

Use only over a carefully controlled background. Do not put text over arbitrary images or high-frequency gradients beneath glass. Text contrast must remain compliant after transparency and blur are rendered. Keep critical controls functional when backdrop filtering is unsupported or reduced-motion preferences are enabled.

---

## 8. Component specifications

### 8.1 Buttons

Define four consistent variants:

- **Primary:** navy fill, white text, strong clear focus ring.
- **Secondary:** white or paper fill, navy text, visible border.
- **Tertiary/quiet:** transparent or neutral fill, clear hover/focus state.
- **Destructive:** danger fill or outline, used only for genuinely destructive actions.

Buttons must have clear labels and clear hover, focus, pressed, disabled and loading states. Do not communicate disabled state with opacity alone if the label becomes hard to read. Keep primary and destructive actions visually distinct.

### 8.2 Inputs and forms

- Place visible, associated labels above inputs by default.
- Use helper text for expected formats or meaningful constraints.
- Display validation errors adjacent to the relevant field and summarize multiple errors where appropriate.
- Keep entered values after recoverable network errors.
- Distinguish disabled, read-only and invalid fields.
- Use clear focus rings and field boundaries that remain visible on white and paper surfaces.
- Do not rely only on placeholder text as the field label.

### 8.3 Navigation and sidebar

- Use dark navy/ink for the primary authenticated sidebar or shell navigation.
- Use a lighter solid surface for the main content.
- Mark active routes with a visible accent and accessible state, not colour alone.
- Use consistent icon sizing and labels.
- Group routes by task/domain: Registry, Documents, Validation, Verification, Lifecycle/Renewal, Release/Refund, Command Center, Reports/Audit and Administration where available.
- Hide or disable navigation according to user role as a usability feature, but always enforce access on the backend.
- Keep glass limited to small overlays, not the entire sidebar behind unreadable content.

### 8.4 Cards and metric tiles

Each metric card includes a clear metric name, value, optional explanatory caption or date window and a sensible drill-down action. It should not rely on a trend arrow or chart icon without context. Do not show fictitious values as real metrics.

Use a white or very light solid surface, a clear boundary, consistent padding and restrained shadow. Prefer one accent detail over a full-card gradient.

### 8.5 Data tables

Tables are core operational surfaces and must favour precision over effects.

- Solid backgrounds with visible row/column structure.
- Sticky headers only when helpful and tested on mobile.
- Align numbers and amounts consistently; use tabular numerals.
- Keep date formats consistent.
- Provide accessible sorting indicators and clear sort state.
- Preserve readable row heights and adequate clickable targets.
- Allow a row to open detail only when this does not conflict with buttons or keyboard interaction inside the row.
- Use explicit empty, loading and error states.
- Keep sensitive identifiers masked in list views where required by policy.
- Do not put a blurred glass layer behind tabular text.

### 8.6 Status badges

Use compact tags with a text label and, where helpful, an icon. Status colour must be consistent across the entire application. Use semantic colours only for their documented meanings. `SIMULATED` is a separate explicit label and must be visible in lists, details, reports and audit views.

### 8.7 Trust-level component

The L0–L3 component should show the level, label and evidence context without implying that progress is automatic. On detail pages, show source, actor, timestamp and associated evidence when available. Distinguish:

- L0 — Declared.
- L1 — Document-consistent; not authenticity proof.
- L2 — Officer-verified with recorded evidence/reason.
- L3 — Bank-confirmed only with a qualifying authorized response record.

A timeout or source-unavailable outcome must never look like confirmation. Simulated results must be clearly marked.

### 8.8 Evidence and audit panels

Use structured fields for source, actor, timestamp, evidence reference, policy version, outcome and chain-verification state where available. Use IBM Plex Mono selectively for IDs and hashes. Allow long hashes to wrap or be copied; do not force them into a tiny truncated line without a copy/view mechanism.

Label hash-chained audit history as **tamper-evident**, not tamper-proof. A valid hash does not prove the authenticity of the underlying FDR.

### 8.9 Dialogs and overlays

Dialogs must have a clear title, purpose, close action, keyboard focus management and a stable solid content surface. A backdrop may be translucent; the dialog content itself should remain opaque for critical workflows. Destructive or consequential actions require explicit description and a clear cancel path.

---

## 9. Page-level design patterns

### 9.1 Public landing page

- Light paper/white foundation.
- Strong navy wordmark and headline.
- Selective teal accent for evidence and progress.
- Small gold accents, not gold body text.
- Hero uses an original dashboard/lifecycle composition rather than generic AI artwork.
- Clear primary CTA to sign in.
- Sections explaining the lifecycle, trust ledger, capabilities, security and FAQ.
- Responsive navigation and a readable footer.
- Do not use fabricated adoption metrics or imply live integrations.

### 9.2 Login

- Focused, low-distraction layout.
- Solid white form surface on paper or deep-navy background area.
- Logo and product name.
- Strong field labels, visible errors and clear loading states.
- Optional restrained glass on an outer decorative panel only; the login form itself remains high contrast and legible.
- Sign-in routes to the correct authorized dashboard after successful real authentication.

### 9.3 Command Center

- Page title, date/filter context and primary scope controls at top.
- Summary cards in a consistent grid.
- Work queues and maturity/completeness panels grouped by operational purpose.
- Transparent priority factors instead of unexplained risk scores.
- Charts accompanied by labels and accessible data summaries.
- Show a clear difference between zero, loading, stale, error and unconfigured metrics.

### 9.4 Instrument detail

- Compact summary header for institution, instrument reference, status and key dates.
- Clear tabs or sections for Overview, Documents, Validation, Verification, Lifecycle, Renewal Lineage and Audit where available.
- Keep admin state, trust state, date state and release case state distinct.
- Use solid evidence panels and tables; no glass behind critical values.

### 9.5 Release/refund case

- Clear case status and policy version.
- Checklist with satisfied, unmet, pending, not applicable and unable-to-evaluate states where supported.
- Blockers listed in plain language with evidence and next action.
- Distinct officer review and competent-authority decision areas.
- Maker-checker requirements made visible.
- Never visually suggest that the frontend itself grants approval or releases money.

### 9.6 Search and reports

- Stable filter panel and visible active filters.
- Clear report timestamp and effective scope.
- Server-authorized results and exports.
- Clear distinction between operational reports and formal audit evidence.
- Solid table surfaces, readable metadata and no unnecessary glass effects.

---

## 10. Responsive behaviour

### Breakpoint guidance

Adapt to the repository's existing Tailwind breakpoints if they are established; otherwise use the following as design targets:

- Small mobile: under 640 px.
- Tablet/medium: 640–1023 px.
- Desktop: 1024–1279 px.
- Wide desktop: 1280 px and above.

### Mobile rules

- Collapse primary navigation to an accessible menu.
- Stack metric cards into one or two columns as space permits.
- Convert complex record summaries into readable cards or use controlled horizontal scrolling for genuine tabular data.
- Keep key statuses and actions visible without requiring hover.
- Dialogs must fit viewport height and allow internal scrolling when necessary.
- Never make essential content accessible only by hover.
- Keep touch targets comfortable and provide enough spacing between actions.

### Responsive test targets

Test at minimum at 320, 375, 768, 1024 and 1440 CSS pixels. Check navigation, long names, FDR identifiers, hashes, table actions, charts, modals, validation errors and empty states.

---

## 11. Motion and interaction

Motion should clarify state changes and make the interface feel responsive without becoming theatrical.

- Typical hover/focus transition: 120–180 ms.
- Small state transition: 150–220 ms.
- Dialog/menu entry: 160–240 ms, with short opacity/transform changes.
- Avoid long spring animations, exaggerated bounce, cursor-following visuals and scroll-jacking.
- Do not animate important numeric values in a way that could imply financial change or live data when none occurred.
- Respect `prefers-reduced-motion: reduce` and remove non-essential motion for that setting.
- Ensure focus movement and status changes remain understandable without animation.

---

## 12. Icons, imagery and decorative graphics

- Use a single consistent icon family already in the repository; if none exists, choose a coherent lightweight library and standardize size/stroke.
- Use icons to reinforce labels, not replace them.
- Avoid emoji as the primary interface iconography.
- Use diagrams for the FDR lifecycle, trust ledger and audit chain only when they improve understanding.
- Prefer real UI composition built from components over generic AI-generated stock illustrations.
- Mark decorative SVGs as hidden from assistive technology; provide an accessible description for meaningful diagrams.
- Never use fabricated official logos or seals.

---

## 13. Content and microcopy standards

Use plain, non-accusatory and operational language.

Preferred examples:

- “Source unavailable” instead of “Verification failed” when the source did not respond.
- “Discrepancy requires review” instead of “Fraud detected.”
- “Document-consistent” instead of “Authentic.”
- “Simulated bank response” instead of “Bank verified” for demo responses.
- “Release blocked: mandatory checklist items remain” instead of an unexplained red alert.
- “No records match these filters” for a legitimate empty result.
- “Metrics unavailable because the policy is not configured” instead of presenting an unjustified zero.

Keep button labels direct: “Save draft”, “Submit for review”, “Return with reason”, “Open evidence”, “Export report”, “Verify audit chain”.

---

## 14. Accessibility and usability requirements

Build towards WCAG 2.2 AA-informed practice and consult the applicable Government of India website/app guidance (GIGW) where relevant. This document is design guidance; it does not itself certify GIGW or WCAG conformance.

Requirements:

- Semantic HTML and logical heading hierarchy.
- Visible keyboard focus that is not obscured by sticky headers or overlays.
- Keyboard-accessible navigation, filters, tables, menus and dialogs.
- Labels programmatically associated with form fields.
- Error identification and instructions that do not rely on colour alone.
- Text alternatives for meaningful non-text content.
- Minimum contrast targets specified in Section 3.4.
- No essential text embedded only in images.
- Responsive layouts without loss of information at narrow widths, except where a two-dimensional presentation is essential.
- Respect text resizing and zoom; avoid fixed heights for text containers.
- Reduced-motion support.
- Appropriate focus management in modals and after navigation.
- Status announced accessibly where live updates change relevant state.

Run automated accessibility checks where available and manually test keyboard use, focus order, form errors and representative contrast combinations. Automated tooling alone does not prove conformance.

---

## 15. Technical design tokens and CSS implementation

Use the current project's styling approach. Do not introduce a second styling system. If Tailwind is already used, define equivalent theme tokens in the existing Tailwind configuration or CSS variables. Keep reusable tokens centralized.

Starter CSS token block:

```css
:root {
  /* Brand */
  --st-navy: #123B5D;
  --st-ink: #0D2538;
  --st-teal: #0F766E;
  --st-gold: #C69A48;

  /* Surfaces */
  --st-paper: #F5F4EF;
  --st-white: #FFFFFF;
  --st-surface-muted: #EDF1F3;
  --st-border: #8799A9;
  --st-border-subtle: #C9D3DB;

  /* Type */
  --st-text: #253746;
  --st-text-muted: #5D6A75;
  --st-font-sans: "IBM Plex Sans", "Segoe UI", Roboto, Arial, sans-serif;
  --st-font-mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;

  /* Semantic */
  --st-success: #18794E;
  --st-warning: #8A5A00;
  --st-danger: #B42318;
  --st-info: #245B7A;
  --st-focus: #145DA0;
  --st-simulated-bg: #FFF3D6;
  --st-simulated-text: #7A4B00;

  /* Shape and spacing */
  --st-radius-control: 8px;
  --st-radius-card: 10px;
  --st-radius-dialog: 16px;
  --st-space-1: 4px;
  --st-space-2: 8px;
  --st-space-3: 12px;
  --st-space-4: 16px;
  --st-space-5: 20px;
  --st-space-6: 24px;
  --st-space-8: 32px;
  --st-space-10: 40px;
  --st-space-12: 48px;

  /* Selective glass */
  --st-glass-bg: rgba(255, 255, 255, 0.82);
  --st-glass-border: rgba(255, 255, 255, 0.78);
  --st-glass-blur: 12px;
}

html {
  font-family: var(--st-font-sans);
  color: var(--st-text);
  background: var(--st-paper);
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

code,
.st-mono,
.st-reference,
.st-audit-hash {
  font-family: var(--st-font-mono);
  font-variant-numeric: tabular-nums;
}

.st-glass-panel {
  background: var(--st-glass-bg);
  border: 1px solid var(--st-glass-border);
  box-shadow: 0 8px 24px rgba(13, 37, 56, 0.10);
  -webkit-backdrop-filter: blur(var(--st-glass-blur));
  backdrop-filter: blur(var(--st-glass-blur));
}

@supports not ((backdrop-filter: blur(1px))) {
  .st-glass-panel { background: var(--st-white); }
}

:focus-visible {
  outline: 3px solid var(--st-focus);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

Treat this as a reference implementation. Merge it into the actual project's theme without overwriting useful current tokens or breaking existing styles. Verify the font loading strategy and compatibility with the installed Tailwind version before making configuration changes.

---

## 16. Do / Don't summary

### Do

- Use navy, teal and warm neutrals consistently.
- Use IBM Plex Sans for the interface and IBM Plex Mono for technical identifiers.
- Define clear containers and a stable grid.
- Use solid surfaces for sensitive or dense operational content.
- Reserve glass for selected overlays and navigation.
- Keep trust, verification, admin state and maturity visibly distinct.
- Provide accessible labels, focus states and status text.
- Use authentic, measured data in the application; label illustrative demo content.
- Use reusable components and shared design tokens.

### Don't

- Don't imply that this palette is an official AICTE palette.
- Don't use official government seals without authorization.
- Don't put glass blur behind financial tables, long text or critical evidence.
- Don't use gold as small text on white.
- Don't use colour alone to indicate status.
- Don't show simulated bank responses as real bank confirmation.
- Don't call the audit trail tamper-proof.
- Don't use AI, visual styling or frontend flags to imply release approval.
- Don't replace working functionality with decorative static screens.
- Don't make up metrics, integrations, certifications or measured outcomes.

---

## 17. Acceptance checklist

The implementation conforms to this design direction when:

- [ ] Product branding consistently uses SakshyaTrail in user-facing UI.
- [ ] Brand colours and typography are implemented as shared tokens.
- [ ] IBM Plex Sans and IBM Plex Mono are loaded or fall back cleanly.
- [ ] Layouts use consistent spacing, container boundaries and responsive grids.
- [ ] Brutalist treatment improves structure without harming usability.
- [ ] Glassmorphism is selective and has a solid fallback.
- [ ] Tables, forms, evidence and audit views remain solid and readable.
- [ ] Status indicators include meaningful text and respect trust-state distinctions.
- [ ] Simulated verification is visibly labelled.
- [ ] Primary navigation, login and dashboard routes continue to work.
- [ ] All existing module workflows still work.
- [ ] Pages remain usable at mobile, tablet and desktop widths.
- [ ] Keyboard navigation, visible focus and reduced-motion behaviour work.
- [ ] Contrast has been tested on rendered component states.
- [ ] No fabricated endorsements, live integrations or real-world metrics are presented.
- [ ] Type checking, linting, tests and production build have been run and their outcomes recorded honestly.

---

## 18. Reference guidance

These references inform the accessibility, usability and typography recommendations; they do not establish a specific official AICTE colour palette.

1. **Guidelines for Indian Government Websites and Apps (GIGW):** https://guidelines.india.gov.in/  
2. **GIGW accessibility guidelines:** https://guidelines.india.gov.in/accessibility-guidelines-and-attributes/  
3. **W3C Web Content Accessibility Guidelines (WCAG):** https://www.w3.org/TR/wcag/  
4. **IBM Plex type family specifications:** https://www.ibm.com/plex/specs/  
5. **IBM Plex project and package information:** https://github.com/IBM/plex/

**Final design statement:** SakshyaTrail should feel like a durable, evidence-led institutional product. Make the structure visible, keep the data legible, use effects sparingly, and let the trust model—not decoration—communicate what the system actually knows.
