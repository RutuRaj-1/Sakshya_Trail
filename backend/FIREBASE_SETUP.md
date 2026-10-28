# Firebase Storage Setup Guide — SakshyaTrail / FDR Sentinel

> **SIH Problem Statement 26265** | Firebase Project: `sih-26265-fdr`

---

## Overview

SakshyaTrail uses **Firebase Cloud Storage (Google Cloud Storage)** as the optional
document byte-storage backend. All access is **server-side only** — the browser never
receives bucket credentials, object paths, or signed URLs directly.

The relational SQLite/PostgreSQL database remains **authoritative for all metadata**
(ownership, institution, version lineage, SHA-256 digest, scan status, workflow state).
Firebase holds only the document bytes.

---

## Architecture

```
Browser
  │
  │  HTTPS (authenticated cookies / JWT)
  ▼
FastAPI Backend
  │  1. Authenticate user
  │  2. Authorise role + institution scope
  │  3. Validate file (magic bytes, size, type)
  │  4. Scan (DemoScannerProvider / VirusTotal)
  │  5. SHA-256 hash
  │  6. store bytes → FirebaseStorageProvider
  │  7. persist metadata → SQLite / PostgreSQL
  │  8. append audit event
  ▼
Firebase / GCS Bucket (private, server-access-only)
```

---

## Step 1 — Generate a Service Account Key

1. Open [Firebase Console](https://console.firebase.google.com) → project **sih-26265-fdr**.
2. Click the ⚙️ gear → **Project settings** → **Service accounts** tab.
3. Click **Generate new private key** → confirm → download the JSON file.
4. **Save it as `backend/serviceAccountKey.json`** (already in `.gitignore` — will not be committed).

> **IMPORTANT** — Keep this file secret.  
> Never commit it. Never paste its contents into source code, chat, or logs.  
> If it is accidentally exposed, revoke it immediately in the Firebase Console and generate a new one.

---

## Step 2 — Set Environment Variables

Edit `backend/.env` (never commit this file):

```dotenv
DOCUMENT_STORAGE_BACKEND=firebase
FIREBASE_STORAGE_ENABLED=true
FIREBASE_PROJECT_ID=sih-26265-fdr
FIREBASE_STORAGE_BUCKET=sih-26265-fdr.firebasestorage.app
GOOGLE_APPLICATION_CREDENTIALS=./serviceAccountKey.json
```

`GOOGLE_APPLICATION_CREDENTIALS` is relative to the directory from which you start
`uvicorn` (normally `backend/`).

---

## Step 3 — Set Firebase Storage Security Rules

Since all access goes through the privileged backend Admin SDK, **deny all browser-level
access** by setting the following rules in the Firebase Console:

1. Firebase Console → **Storage** → **Rules** tab.
2. Replace the existing rules with:

```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /{allPaths=**} {
      allow read, write: if false;
    }
  }
}
```

3. Click **Publish**.

The Admin SDK (used by the FastAPI backend) bypasses these rules and retains full access.
End users — including authenticated Firebase Auth users — cannot directly read or write
any object.

---

## Step 4 — Verify Encryption at Rest

Google Cloud Storage applies **AES-256 encryption at rest by default** for all objects
in all buckets, at no extra charge and with no configuration required. No additional
setup is needed to enable server-side encryption.

If you require **customer-managed encryption keys (CMEK)**, configure them in
GCP Console → Cloud Storage → bucket settings → Encryption. This is not required for
the current SakshyaTrail implementation.

---

## Step 5 — Start the Backend

```powershell
cd backend
.\.venv\Scripts\uvicorn app.main:app --reload
```

On startup you should see:
```
[Storage] Backend: Firebase Cloud Storage (bucket=sih-26265-fdr.firebasestorage.app)
```

If the service account file is missing or invalid, the backend logs a warning and
falls back to local storage automatically — it does not crash.

---

## Switching Back to Local Storage

```dotenv
DOCUMENT_STORAGE_BACKEND=local
FIREBASE_STORAGE_ENABLED=false
```

Documents already stored in Firebase remain accessible there; newly uploaded documents
will use local storage. The database always records which storage key each version uses.

---

## Running Tests

### Unit tests (no Firebase credentials needed — CI-safe)
```powershell
cd backend
.\.venv\Scripts\pytest tests/test_firebase_storage.py -v -m "not integration"
```

### Integration tests (require real credentials)
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = ".\serviceAccountKey.json"
.\.venv\Scripts\pytest tests/test_firebase_storage.py -v -m integration
```

### Full backend test suite
```powershell
.\.venv\Scripts\pytest tests/ -v --ignore=tests/test_document_extraction_validation.py
```

---

## Object Path Scheme

All objects are stored under the `sakshyatrail/` namespace prefix inside the bucket:

```
sakshyatrail/<uuid-storage-key>
```

The `<uuid-storage-key>` is a server-generated UUID4 stored in `DocumentVersion.storage_key`.
This key is opaque — it reveals no institution, FDR, or personal information.

---

## Security Principles

| Control | Implementation |
|---|---|
| Authentication | FastAPI JWT/session — every request verified |
| Authorisation | Role + institution scope checked server-side before any storage operation |
| Transport security | HTTPS/TLS — enforced in production via `AUTH_COOKIE_SECURE=true` |
| Encryption at rest | GCS default AES-256 — no action required |
| Secret handling | Service account JSON never committed; referenced via env var |
| Signed URLs | Short expiry (≤15 min), never logged, never sent to browser without auth |
| Path traversal | Storage keys validated server-side; user input never used as object path |
| Public access | Firebase Storage rules deny all browser access (`allow read, write: if false`) |
| Integrity | SHA-256 digest computed and stored on upload; verified on demand |
| Audit | Every upload/download/delete appended to immutable hash-chained audit log |

