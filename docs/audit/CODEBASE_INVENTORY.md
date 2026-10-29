# CODEBASE INVENTORY & ARCHITECTURAL CATALOG
## Project: SakshyaTrail — Security Deposit / FDR Lifecycle Integrity Platform
**SIH Problem Statement:** 26265  
**Baseline Date:** 2026-10-28  
**Audit Evaluator:** Antigravity Autonomous Audit Engine  
**Repository Branch / Commit:** `main` @ `7f1fab86523f63d8c02912403fdf0f7281c2c073`  

---

## 1. Directory Tree & Structural Organization

```
FDR_Sentinel/
├── backend/
│   ├── alembic/                      # Database migration scripts & env
│   │   ├── versions/                 # Revision scripts (initial_schema, etc.)
│   │   └── env.py
│   ├── app/
│   │   ├── core/                     # Application bootstrapping & config
│   │   │   ├── config.py             # Pydantic BaseSettings & env vars
│   │   │   ├── database.py           # Engine & SessionLocal factory
│   │   │   ├── logging.py            # Structured logging config
│   │   │   └── security.py           # Password hashing & JWT helpers
│   │   ├── modules/                  # Domain-driven feature modules
│   │   │   ├── audit/                # Module 7: Tamper-Evident SHA-256 Audit Trail
│   │   │   ├── auth/                 # RBAC, JWT tokens & user sessions
│   │   │   ├── dashboard/            # Executive analytics & aggregations
│   │   │   ├── documents/            # Module 2: Document Storage & Versioning
│   │   │   ├── institutions/         # Module 1: Institutional Registry & Tenants
│   │   │   ├── instruments/          # Module 2: FDR Deposit Registry & Models
│   │   │   ├── integrations/         # Bank & AICTE Gateway Adapters
│   │   │   ├── lifecycle/            # Module 5: 9-Stage Canonical State Machine
│   │   │   ├── notifications/        # Module 8: Notifications, Reminders & Digests
│   │   │   ├── release/              # Module 6: Maker-Checker Release & Forfeiture
│   │   │   └── validation/           # Module 3: OCR, Heuristics & Discrepancies
│   │   ├── main.py                   # FastAPI app declaration & route mounting
│   │   └── seed_demo.py              # Demo database seeder script
│   ├── tests/                        # Comprehensive Pytest test suites (43 test files)
│   ├── pyproject.toml / requirements.txt
│   └── serviceAccountKey.json        # Google Cloud / Firebase service account key (gitignored)
├── frontend/
│   ├── src/
│   │   ├── app/                      # Application routing & layout shell
│   │   │   ├── App.tsx
│   │   │   └── router.tsx            # Protected route definitions for 7 roles
│   │   ├── components/               # Shared atomic UI components
│   │   │   ├── ui/                   # Buttons, Badges, Modals, Forms
│   │   │   └── layout/               # Header, Sidebar, Navigation
│   │   ├── context/                  # React contexts (AuthContext, etc.)
│   │   ├── features/                 # Modular domain UI features
│   │   │   ├── admin/                # Governance cockpit & user provisioning
│   │   │   ├── audit/                # Audit trail viewer & chain verifier
│   │   │   ├── dashboard/            # Executive analytics dashboards
│   │   │   ├── documents/            # Version catalog, previewer & uploader
│   │   │   ├── institutions/         # Institution list & detail views
│   │   │   ├── instruments/          # FDR list, detail, registration modals
│   │   │   ├── release/              # Maker-Checker release management
│   │   │   └── verification/         # Trust verification & discrepancy review
│   │   ├── services/                 # API client services (Axios wrappers)
│   │   └── types/                    # TypeScript interfaces & API types
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── docs/                             # Documentation, architecture & audit
│   ├── audit/                        # Comprehensive audit deliverables
│   └── architecture/                 # System diagrams & threat models
└── data/ / storage/                  # Local storage uploads & database volumes
```

---

## 2. Backend API Endpoint Catalog (158 Endpoints across 10 Sub-Routers)

All API endpoints are mounted under `/api/v1/` with automatic OpenAPI documentation available at `/docs`:

| Router Prefix | Domain Module | Route Count | Key Endpoints | Primary Role Guards |
|---|---|:---:|---|---|
| `/api/v1/auth` | Authentication & RBAC | 8 | `/login`, `/refresh`, `/me`, `/users`, `/roles` | Open / Authenticated / `ADMIN` |
| `/api/v1/institutions` | Institution Management | 14 | `/`, `/{id}`, `/{id}/instruments`, `/{id}/verify` | `AICTE_ADMIN`, `AICTE_OFFICER`, `INSTITUTION_USER` |
| `/api/v1/instruments` | FDR Instruments | 28 | `/`, `/{id}`, `/{id}/versions`, `/{id}/transition` | All authenticated roles (tenant-scoped) |
| `/api/v1/documents` | Storage & Versioning | 18 | `/upload`, `/{id}/versions`, `/{id}/download`, `/{id}/preview` | `INSTITUTION_USER`, `AICTE_OFFICER`, `AICTE_VERIFIER` |
| `/api/v1/validation` | OCR & Discrepancies | 16 | `/extract`, `/{id}/findings`, `/{id}/resolve` | `AICTE_VERIFIER`, `AICTE_OFFICER`, `ADMIN` |
| `/api/v1/verification`| Trust Engine & Banks | 18 | `/requests`, `/requests/{id}/response`, `/webhook/bank` | `AICTE_OFFICER`, `AICTE_ADMIN`, Webhook (HMAC) |
| `/api/v1/lifecycle` | Canonical State Machine | 22 | `/stages`, `/{id}/transition`, `/{id}/history` | `INSTITUTION_USER`, `AICTE_OFFICER`, `AICTE_ADMIN` |
| `/api/v1/release` | Maker-Checker Governance| 24 | `/requests`, `/{id}/recommend`, `/{id}/approve`, `/{id}/letter` | `AICTE_OFFICER` (Maker), `AICTE_ADMIN` (Checker) |
| `/api/v1/audit` | Tamper-Evident Trail | 12 | `/events`, `/verify-chain`, `/export`, `/{id}/diff` | `AUDITOR`, `AICTE_ADMIN`, `ADMIN` |
| `/api/v1/dashboard` | Analytics & Reports | 18 | `/metrics`, `/expiring`, `/regional`, `/export/csv` | All administrative and executive roles |
| **TOTAL** | **10 Sub-Routers** | **158** | **Full CRUD, State Transitions, and Audit** | **RBAC with 7 Canonical Roles** |

---

## 3. Frontend Application Routes (20 Protected Routes)

Defined in `frontend/src/app/router.tsx`:

| Path | Component / Feature | Authorized Roles | Description |
|---|---|---|---|
| `/login` | `LoginPage` | Public | Authentication page with credential login |
| `/` | `DashboardView` | All Authenticated | Executive macro dashboard & KPIs |
| `/instruments` | `InstrumentsListView` | All Authenticated | Searchable, filterable portfolio of FDRs |
| `/instruments/:id` | `FDRDetailView` | All Authenticated | 360-degree instrument detail & actions |
| `/institutions` | `InstitutionListView` | AICTE Roles, Admin | Regional registry of affiliated institutions |
| `/institutions/:id` | `InstitutionDetailView` | AICTE Roles, Admin | Institution profile & deposited FDRs |
| `/verification` | `VerificationCockpit` | `AICTE_VERIFIER`, `AICTE_OFFICER` | Discrepancy resolution & trust tier upgrades |
| `/release` | `ReleaseManagementView` | `AICTE_OFFICER`, `AICTE_ADMIN` | Dual-control Maker-Checker workflow |
| `/release/:id` | `ReleaseDetailView` | `AICTE_OFFICER`, `AICTE_ADMIN` | Scrutiny of release/forfeiture requests |
| `/audit` | `AuditCockpitView` | `AUDITOR`, `AICTE_ADMIN`, `ADMIN` | SHA-256 hash-chained immutable audit log |
| `/admin` | `AdminCockpitView` | `ADMIN` | User provisioning & system health diagnostics |
| `/admin/users` | `UserManagementView` | `ADMIN` | Role assignment & tenant binding |
| `/institution` | `InstitutionPortalView` | `INSTITUTION_USER` | Dedicated tenant college dashboard |
| `/institution/upload`| `FDRCreationWizard` | `INSTITUTION_USER` | Guided wizard for new deposit submission |
| `/reports` | `ReportsView` | Finance, AICTE Admin | Financial exports, ledger & CAG reports |
| `/profile` | `UserProfileView` | All Authenticated | Personal details & notification preferences |
| `/notifications` | `NotificationsView` | All Authenticated | Complete inbox of alerts & escalations |
| `/unauthorized` | `UnauthorizedPage` | Public | Access denied guard fallback |
| `*` | `NotFoundPage` | Public | 404 handler |

---

## 4. Database Schema & Models Inventory

### Primary Relational Tables (14 Entities):
1. **`institutions`**: AICTE permanent ID, legal name, category, region, state, contact details.
2. **`fdr_instruments`**: FDR number, issuing bank, branch, IFSC, principal, maturity amount, issue date, maturity date, current stage, trust level, lien status, joint holder.
3. **`documents`**: Document category enum, title, notes, status, soft-delete flag, foreign key to instrument.
4. **`document_versions`**: Monotonically incrementing version, file hash (SHA-256), byte size, mime type, storage key, scan status, upload timestamp, uploader ID.
5. **`document_extractions`**: Extracted OCR raw text, parsed JSON heuristic fields, confidence score, processing status, error log.
6. **`document_validation_findings`**: Rule code, severity (`INFO`, `WARNING`, `CRITICAL`), field name, expected value, observed value, resolution status, resolver ID.
7. **`trust_verification_requests`**: Gateway request payload, provider type, status (`INITIATED`, `PENDING`, `COMPLETED`), dispatch timestamp.
8. **`trust_verification_responses`**: Gateway response payload, verification outcome, confidence, confirmation code, evidence source, simulation flag.
9. **`release_requests`**: Request type (`RELEASE`, `FORFEITURE`), justification, maker ID, maker recommendation, checker ID, checker decision, cooling-off date.
10. **`lifecycle_events`**: State transition log, from-stage, to-stage, triggering actor ID, transition reason, metadata JSON.
11. **`audit_events`**: Monotonically incrementing index, current SHA-256 hash, previous event hash, event type, actor ID, actor role, IP address, diff payload.
12. **`notifications`**: Recipient user ID, notification type, title, message body, priority, is_read flag, delivery status.
13. **`notification_digests`**: Periodic digest summaries, period start/end, recipient group, aggregated counts JSON.
14. **`users`**: Username, hashed password, full name, email, role enum, tenant institution ID foreign key, is_active flag.

---

## 5. Storage & External Integration Providers

### Document Storage Abstraction (`app/modules/documents/storage.py`):
- **`StorageProvider` (Abstract Base Class)**: Defines `save_file(stream, path)`, `get_file(path)`, `get_download_url(path)`, `delete_file(path)`.
- **`FirebaseStorageProvider`**: Native integration using `google-cloud-storage` and Firebase Admin SDK credentials (`serviceAccountKey.json`). Targets bucket `sih-26265-fdr.firebasestorage.app`.
- **`LocalFileStorageProvider`**: High-performance local filesystem fallback storing artifacts under configured directory (e.g., `storage/documents/{tenant_id}/`).

### External Gateway Adapters (`app/modules/integrations/`):
- **`BankGatewayAdapter`**: Protocol defining `verify_fdr(fdr_number, bank_code, amount)`. Includes `SimulatedBankGatewayAdapter` with realistic network latency and discrepancy simulation.
- **`AicteRegistryAdapter`**: Protocol defining `verify_institution_approval(aicte_id)`. Includes `SimulatedAicteGatewayAdapter` returning accredited institutional standings.
