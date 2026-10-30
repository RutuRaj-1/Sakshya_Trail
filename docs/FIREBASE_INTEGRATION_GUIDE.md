# SAKSHYATRAIL — FIREBASE INTEGRATION & SECURITY RULES GUIDE
## Complete Frontend & Backend Setup for SIH Problem Statement 26265

**Project:** SakshyaTrail — Security Deposit / FDR Lifecycle Integrity Platform  
**Firebase Project ID:** `sih-26265-fdr`  
**Storage Bucket:** `sih-26265-fdr.firebasestorage.app`  

---

## 1. ARCHITECTURAL OVERVIEW & CREDENTIALS MATRIX

SakshyaTrail divides Firebase responsibilities between client-side analytics/services and server-side privileged document storage:

```
┌────────────────────────────────────────────────────────┐
│                  FRONTEND (Vercel)                     │
│  - Modular Firebase Client SDK (v13.x)                 │
│  - Initialized with public Web App Credentials         │
│  - Analytics tracking (G-YYNCY2BVT9)                   │
│  - Optional real-time Firestore sync & client Auth     │
└──────────────────────────┬─────────────────────────────┘
                           │ Authenticated REST (Bearer JWT)
                           ▼
┌────────────────────────────────────────────────────────┐
│                  BACKEND (Render)                      │
│  - Privileged Firebase Admin SDK (Python)              │
│  - Authenticated via Service Account Key (Private)     │
│  - Computes SHA-256 byte digest on certified FDR PDFs  │
│  - Streams document bytes to Cloud Storage bucket      │
│  - Records versioned metadata in Relational Database   │
│  - Logs event in SHA-256 cryptographic audit chain     │
└──────────────────────────┬─────────────────────────────┘
                           │ Privileged Admin Access
                           ▼
┌────────────────────────────────────────────────────────┐
│           GOOGLE CLOUD / FIREBASE SERVICES             │
│  - Firebase Cloud Storage (sih-26265-fdr.firebasestorage.app)
│  - Cloud Firestore (Governed by firestore.rules)       │
│  - Cloud Storage Rules (Governed by storage.rules)     │
└────────────────────────────────────────────────────────┘
```

### Credentials Comparison:

| Credential Type | Intended Component | Confidentiality | Environment Variable | Location in Repository |
|---|---|---|---|---|
| **Firebase Web Config** | Frontend React App | **Public** (bundled in client JS) | `VITE_FIREBASE_*` | `.env`, `frontend/.env`, `frontend/src/lib/firebase.ts` |
| **Service Account JSON** | Backend FastAPI | **Strict Secret** (NEVER commit to Git) | `FIREBASE_SERVICE_ACCOUNT_JSON` or `GOOGLE_APPLICATION_CREDENTIALS` | `backend/serviceAccountKey.json` (gitignored) |

---

## 2. FRONTEND INTEGRATION (REACT / VITE)

### 2.1 Client SDK Configuration (`frontend/src/lib/firebase.ts`)
The client SDK is initialized using Firebase modular syntax (v13.x) with automatic fallbacks:

```typescript
import { initializeApp, getApps, getApp } from "firebase/app";
import { getAnalytics, isSupported } from "firebase/analytics";
import { getFirestore } from "firebase/firestore";
import { getStorage } from "firebase/storage";

export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "AIzaSyAqqvkCHZutYjILCXT6Q-SzvGn88holAps",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "sih-26265-fdr.firebaseapp.com",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "sih-26265-fdr",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "sih-26265-fdr.firebasestorage.app",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "2017740195",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "1:2017740195:web:ed1355f7fd21cd3ad80616",
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID || "G-YYNCY2BVT9",
};

export const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();
export const firestore = getFirestore(app);
export const storage = getStorage(app);
```

### 2.2 Frontend Environment Variables (`frontend/.env`)
Add these variables to `frontend/.env` locally and in **Vercel Project Settings -> Environment Variables**:

```dotenv
VITE_FIREBASE_API_KEY=AIzaSyAqqvkCHZutYjILCXT6Q-SzvGn88holAps
VITE_FIREBASE_AUTH_DOMAIN=sih-26265-fdr.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=sih-26265-fdr
VITE_FIREBASE_STORAGE_BUCKET=sih-26265-fdr.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=2017740195
VITE_FIREBASE_APP_ID=1:2017740195:web:ed1355f7fd21cd3ad80616
VITE_FIREBASE_MEASUREMENT_ID=G-YYNCY2BVT9
```

---

## 3. BACKEND INTEGRATION (FASTAPI & ADMIN SDK)

### 3.1 Document Storage Provider (`backend/app/modules/documents/firebase_storage.py`)
SakshyaTrail uses the `FirebaseStorageProvider` to securely stream certified FDR deposit certificates to Google Cloud Storage.

**Key Security Guarantees:**
1. **Server-Side Uploads:** End users never upload directly to the bucket. The FastAPI backend inspects magic bytes (preventing `.exe` renaming), runs malware scans, computes the SHA-256 hash, and then stores the byte stream.
2. **Path Isolation:** Files are written under `sakshyatrail/{storage_key}` so other applications sharing the bucket are isolated.
3. **Short-Lived Signed URLs:** Download URLs are generated only after backend authentication and expire in ≤ 15 minutes.

### 3.2 Backend Environment Configuration (`backend/.env`)
Set these variables in `backend/.env` for local execution, or in **Render Web Service -> Environment Variables**:

```dotenv
DOCUMENT_STORAGE_BACKEND=firebase
FIREBASE_STORAGE_ENABLED=true
FIREBASE_PROJECT_ID=sih-26265-fdr
FIREBASE_STORAGE_BUCKET=sih-26265-fdr.firebasestorage.app
GOOGLE_APPLICATION_CREDENTIALS=./serviceAccountKey.json
```

### 3.3 Deploying Service Account to Render
To deploy to Render without checking `serviceAccountKey.json` into Git:
- **Option 1 (Recommended):** Add an environment variable in Render named `FIREBASE_SERVICE_ACCOUNT_JSON` and paste the entire JSON string as its value.
- **Option 2:** Under Render -> **Environment** -> **Secret Files**, add `serviceAccountKey.json` and paste the JSON contents. Render mounts it at `/etc/secrets/serviceAccountKey.json`.

---

## 4. HOW TO SET UP FIREBASE SECURITY RULES

### 4.1 Cloud Firestore Rules (`firestore.rules`)
The project includes a production-hardened [`firestore.rules`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/firestore.rules) file enforcing zero-trust:
- Direct client writes to FDR deposit balances, stages, and audit events are **blocked**.
- Audit trail logs are strictly immutable (append-only via backend).
- Multi-tenant isolation ensures college users cannot inspect other colleges.

#### How to apply in Firebase Console:
1. Open the [Firebase Console](https://console.firebase.google.com/) and select project **sih-26265-fdr**.
2. Click **Build** -> **Firestore Database** in the left sidebar.
3. Navigate to the **Rules** tab.
4. Copy the entire contents of [`firestore.rules`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/firestore.rules) from this repository and paste it into the editor.
5. Click **Publish**.

---

### 4.2 Cloud Storage Rules (`storage.rules`)
The project includes [`storage.rules`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/storage.rules) to protect document storage:
- Blocks direct client writes (`allow write: if false;`).
- Requires uploads to flow through the backend API proxy for SHA-256 verification and antivirus inspection.

#### How to apply in Firebase Console:
1. In the Firebase Console, click **Build** -> **Storage**.
2. Click the **Rules** tab.
3. Copy the contents of [`storage.rules`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/storage.rules) and paste it into the editor.
4. Click **Publish**.

---

### 4.3 Deploying via Firebase CLI (Automated Method)
If you have the Firebase CLI installed on your computer (`npm install -g firebase-tools`):

```bash
# 1. Login to your Firebase account
firebase login

# 2. Select the project
firebase use sih-26265-fdr

# 3. Deploy both Firestore and Storage rules simultaneously
firebase deploy --only firestore:rules,storage
```

---

## 5. DATABASE LINKAGE & VERIFICATION TEST

SakshyaTrail connects the relational database (metadata, lifecycle state, audit hashes) with Firebase Storage (binary bytes).

### Verify Live Connectivity:
You can verify the entire backend storage and database linkage by running the following command:

```powershell
backend\.venv\Scripts\python.exe -c "
import os
from app.core.config import settings
from app.modules.documents.storage import get_storage_provider
from app.db.session import SessionLocal, check_database_connection
from app.modules.instruments.models import Instrument

print('1. Checking Database Connection:', check_database_connection())
db = SessionLocal()
inst_count = db.query(Instrument).count()
print(f'2. Active Instruments in Database: {inst_count}')

provider = get_storage_provider()
print(f'3. Storage Provider Initialized: {provider.__class__.__name__}')
"
```

Expected result:
- Database status: `connected` (with 80+ synthetic demo instruments loaded).
- Storage Provider: `FirebaseStorageProvider` (targeting bucket `sih-26265-fdr.firebasestorage.app`).

