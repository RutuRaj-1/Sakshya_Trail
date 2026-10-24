# FDR Sentinel — Module 1 Architecture & Technical Specification
## Core Identity, RBAC, Institution Registry & Instrument Registry Foundation

**System:** FDR Sentinel (AICTE Security Deposit / FDR Lifecycle Integrity Platform)  
**Problem Statement ID:** 26265  
**Stage:** Module 1 Complete Handover  
**Document Classification:** Internal Architecture & Developer Reference  

---

## 1. Architectural Overview

Module 1 establishes the authoritative data models, security perimeter, tenant isolation mechanisms, and financial record registry for **FDR Sentinel**. 

```mermaid
graph TD
    Client[React 19 Frontend Client] -->|Vite Proxy /api/v1| FastAPIGateway[FastAPI Application Gateway]
    
    subgraph Security Layer
        FastAPIGateway --> CSRF[Origin / CSRF Verification]
        CSRF --> AuthMiddleware[JWT / HttpOnly Cookie Authenticator]
        AuthMiddleware --> RBAC[Role-Based Scoping & Scrutiny Engine]
    end

    subgraph Service Layer
        RBAC --> AuthService[Auth & User Admin Service]
        RBAC --> InstService[Institution Registry Service]
        RBAC --> InstruService[FDR Instrument Registry Service]
        RBAC --> DashService[Module 1 Dashboard Service]
        RBAC --> AuditService[Tamper-Evident Audit Ledger]
    end

    subgraph Persistence Layer
        AuthService --> DB[(SQLAlchemy 2.x / PostgreSQL / SQLite)]
        InstService --> DB
        InstruService --> DB
        DashService --> DB
        AuditService --> DB
    end
```

---

## 2. Component Structure

### 2.1 Backend Modules (`backend/app/modules/`)
1. **`auth`**:
   - `models.py`: `User` entity with Argon2id password hashing, mandatory password rotation flag (`must_change_password`), and optional foreign-key institution linkage (`institution_id`).
   - `dependencies.py`: `get_current_active_user`, `require_roles`, `verify_csrf_origin`.
   - `service.py`: Authentication, session generation, administrator user provisioning, last-admin protection, and temporary credential rotation.
   - `router.py`: Versioned endpoints (`/auth/login`, `/auth/logout`, `/auth/me`, `/auth/change-password`, `/auth/roles`, `/auth/users`).
2. **`institutions`**:
   - `models.py`: `Institution` entity with unique normalized AICTE permanent ID code, operating names, legal classifications, full postal address, nodal officer contact details, and soft-delete flag (`is_active`).
   - `service.py`: Validated registration, case-insensitive duplicate code rejection, permitted field patch logic, and auditable deactivation.
   - `router.py`: Versioned endpoints (`/institutions`, `/institutions/{id}`, `/institutions/{id}/status`).
3. **`instruments`**:
   - `models.py`: Statutory `Instrument` entity with UUID primary key, enforced `institution_id` foreign key, decimal currency precision (`Numeric(18, 2)`), administrative status (`status`), evidentiary trust tier (`trust_level`), and derived read-only maturity indicator (`maturity_indicator`).
   - `service.py`: Basic validation, conservative duplicate-reference warning path, scoped search/filtering, and permitted corrections.
   - `router.py`: Versioned endpoints (`/instruments`, `/instruments/{id}`, `/instruments/summary`).
4. **`dashboard`**:
   - `router.py`: Versioned scoped metrics endpoint (`/dashboard/summary`) dynamically returning institution counts, active/draft instruments, trust distribution, approaching maturities, and total deposit values.
5. **`audit`**:
   - `models.py`: Immutable `AuditEvent` ledger capturing actor user ID, email, role, action, entity type, target entity ID, IP address, and sanitized metadata.
   - `service.py`: Centralized audit logging utility with recursive credential stripping (`sanitize_dict`).

---

## 3. Data Relationships & Domain Schema

```mermaid
erDiagram
    INSTITUTION ||--o{ USER : "employs / nodal officer for"
    INSTITUTION ||--o{ INSTRUMENT : "holds / pledges"
    USER ||--o{ INSTRUMENT : "created_by / updated_by"
    USER ||--o{ AUDIT_EVENT : "actor"

    INSTITUTION {
        string id PK "UUIDv4"
        string code UK "AICTE Permanent ID (Normalized)"
        string legal_name "Registered Entity Name"
        string display_name "Common Campus Name"
        string institution_type "TECHNICAL_INSTITUTE | PHARMACY | etc"
        boolean is_active "Soft-delete regulatory status"
        string contact_name "Registrar / Nodal Officer"
        string contact_email "Official Contact Email"
        string address_line1 "Campus Address"
        string city "City"
        string state "State"
        string postal_code "PIN Code"
        string assigned_office "Regional Office Jurisdiction"
        boolean is_synthetic "Demo / Bootstrap Marker"
    }

    USER {
        string id PK "UUIDv4"
        string email UK "Normalized Official Email"
        string password_hash "Argon2id Hash"
        string full_name "Full Legal Name"
        string role "SYSTEM_ADMIN | SCRUTINY_OFFICER | etc"
        boolean is_active "Active Account Status"
        boolean must_change_password "Enforced Rotation Flag"
        string institution_id FK "Nullable FK to Institutions"
    }

    INSTRUMENT {
        string id PK "UUIDv4"
        string institution_id FK "FK to Institutions (Enforced)"
        string instrument_type "FDR"
        string bank_name "Issuing Commercial / PSU Bank"
        string bank_branch "Branch Location"
        string reference_number "Receipt / Account Reference"
        decimal amount "Exact Numeric(18,2) - Never Float"
        string currency "INR"
        date issue_date "Date of Deposit Placement"
        date maturity_date "Maturity Date (> issue_date)"
        string lien_holder "Designated Lien Beneficiary"
        string lien_details "Pledge Terms / Hypothecation"
        string assigned_office "Regional Bureau Jurisdiction"
        string status "DRAFT | REGISTERED"
        string trust_level "L0_DECLARED"
        boolean is_synthetic "Synthetic Demo Marker"
        string created_by_user_id FK "User Attribution"
        string updated_by_user_id FK "User Attribution"
    }

    AUDIT_EVENT {
        string id PK "UUIDv4"
        string action "INSTITUTION_CREATED | INSTRUMENT_CREATED | etc"
        string entity_type "institution | instrument | user | auth"
        string entity_id "Target Record UUID"
        string actor_user_id "Executing User UUID"
        string actor_email "Executing User Email"
        string actor_role "Executing User Role"
        json metadata "Sanitized Structured Context"
        datetime created_at "Immutable UTC Timestamp"
    }
```

---

## 4. Separation of the Three Core Concepts

Module 1 explicitly avoids collapsing distinct business states into a single generic status:

| Concept | Field / Property | Supported Values | Mutability & Enforcement |
|---|---|---|---|
| **Administrative Workflow Status** | `status` (DB column) | `DRAFT`, `REGISTERED` | Represents current lifecycle workflow stage. Initial values for registry module. Downstream release stages belong to Module 5. |
| **Evidentiary Trust Level** | `trust_level` (DB column) | `L0_DECLARED`, `L1_DOCUMENT_CONSISTENT`, `L2_OFFICER_VERIFIED`, `L3_BANK_CONFIRMED` | Initialized strictly to `L0_DECLARED` upon registration. Ordinary registry endpoints reject escalation attempts. Promotions occur only through Module 2 OCR, Module 3 Scrutiny, and Module 4 Bank Confirmation. |
| **Derived Maturity Indicator** | `maturity_indicator` (Computed property) | `ACTIVE`, `EXPIRING_SOON`, `EXPIRED` | Computed dynamically from `maturity_date - today`. Warning window: `EXPIRING_SOON` when remaining days are between `0` and `90`. Never stored as a database status. |

---

## 5. Conservative Duplicate-Reference Warning Path

Financial instrument registries require resilient fraud and error prevention without accidentally suppressing records needed for investigation:

1. **Non-Unique Database Index**:
   - `reference_number` is indexed for fast lookup, but a unique constraint is intentionally not placed in the schema to ensure duplicate submissions are never rejected at the transport level.
2. **Normalized Query Comparison**:
   - `lower(trim(bank_name))` and `lower(trim(reference_number))` are compared against existing instruments.
3. **Structured Warning Interception (HTTP 409)**:
   - When matches exist and `confirm_duplicate: true` is absent, the API returns:
     ```json
     {
       "success": false,
       "error": "A security deposit with matching bank and reference number already exists in the registry.",
       "code": "DUPLICATE_REFERENCE_WARNING",
       "details": {
         "warning_message": "A record with this bank and reference number already exists...",
         "matching_records": [ ... ]
       }
     }
     ```
   - The UI displays an explainable dialog with existing record details and a prominent "Confirm & Register Anyway" button.
4. **Auditable Override**:
   - Submitting with `confirm_duplicate: true` creates an independent record and logs `duplicate_warning_overridden: true` with matched IDs in the audit ledger. Records are **never silently merged**.

---

## 6. Multi-Tenant Isolation & Role Scoping

| Role | Scope | Permitted Registry Actions |
|---|---|---|
| `SYSTEM_ADMIN` | Bureau-wide | Create/update institutions, provision users, edit permitted instrument fields. |
| `SCRUTINY_OFFICER` | Bureau-wide | View all institutions and instruments; record scrutiny notes and permitted corrections. |
| `BRANCH_HEAD` | Bureau-wide | Read-only oversight of institutions, instruments, and queues. |
| `COMPETENT_AUTHORITY`| Bureau-wide | Read-only inspection across all records and audit histories. |
| `FINANCE_OFFICER` | Bureau-wide | Read-only inspection of instruments, bank details, and values. |
| `AUDITOR` | Bureau-wide | Read-only compliance inspection of records, metadata, and audit events. |
| `INSTITUTION_USER` | **Strictly Scoped** | Can read and edit permitted contact fields on **own institution only**; can create and manage instruments for **own institution only**. All cross-institution reads or edits are rejected with HTTP 403. |

---

## 7. Future Extension Points

- **Module 2 (Document Ingestion & Multi-OCR Pipeline)**: Uploaded deposit receipt PDF documents will attach directly to `Instrument.id`, triggering automated text extraction and elevation to `L1_DOCUMENT_CONSISTENT`.
- **Module 3 (Deterministic Validation & Anomaly Detection Engine)**: Scrutiny officer verification interface to record verification checklists, elevation to `L2_OFFICER_VERIFIED`, and defect logging.
- **Module 4 (Official Bank Confirmation Gateway)**: Bank direct API integrations or SFTP statement reconciliation to promote instruments to `L3_BANK_CONFIRMED`.
- **Module 5 (Lien Tracking, Renewal Workflows & Release Governance)**: Full lifecycle state machine (`RELEASED`, `ENCASHED`, `REPLACED`), renewal lineage graphs, and competent authority approval gates.
