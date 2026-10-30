# SAKSHYATRAIL PRODUCTION DEPLOYMENT GUIDE
## Frontend on Vercel & Backend on Render

**Project:** SakshyaTrail — Security Deposit / FDR Lifecycle Integrity Platform  
**SIH Problem Statement:** 26265  
**Target Architecture:**
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS -> **Hosted on Vercel**
- **Backend:** FastAPI + Python 3.11 + SQLAlchemy + Uvicorn -> **Hosted on Render (Web Service)**
- **Document Evidence Storage:** Firebase Cloud Storage (`sih-26265-fdr.firebasestorage.app`)
- **Database:** Auto-seeded demo SQLite (or Render Managed PostgreSQL)

---

## DEPLOYMENT OVERVIEW & SEQUENCE

Always deploy the **Backend on Render first**. This gives you your live backend URL (e.g. `https://sakshyatrail-backend.onrender.com`), which you will then plug into Vercel as `VITE_API_BASE_URL`.

```
[ Step 1: Git Push ] ──> [ Step 2: Render (Backend) ] ──> [ Step 3: Vercel (Frontend) ] ──> [ Step 4: Verification ]
                          - Python 3.11 Web Service         - Vite SPA with Rewrites          - Test 7 Roles & Storage
                          - Firebase SDK Credentials        - VITE_API_BASE_URL set
```

---

## PRE-DEPLOYMENT: PUSH CODE TO GITHUB

Before starting, commit all deployment configurations and push to your GitHub repository:

```powershell
git add .
git commit -m "Configure Vercel frontend and Render backend deployment"
git push origin main
```

*(Note: Sensitive items such as `.env`, local `.db` files, and `serviceAccountKey.json` are automatically protected by `.gitignore` and will never leak to GitHub.)*

---

## PHASE 1: DEPLOY BACKEND ON RENDER

### Step 1.1: Create Web Service on Render
1. Log in to [dashboard.render.com](https://dashboard.render.com/).
2. In the top navigation bar, click **+ New** and select **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your GitHub repo.

### Step 1.2: Configure Service Parameters
Configure the settings as shown below:

| Setting | Value | Notes |
|---|---|---|
| **Name** | `sakshyatrail-backend` | Or any unique name you prefer |
| **Region** | Select closest (e.g., `Singapore` or `Frankfurt`) | Lower latency |
| **Branch** | `main` | Production branch |
| **Root Directory** | `backend` | **Important:** Points Render to the backend code folder |
| **Language / Runtime** | `Python` | |
| **Build Command** | `pip install -r requirements.txt` | Installs FastAPI, Uvicorn, SQLAlchemy, Firebase SDK, etc. |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` | Starts the production ASGI server |
| **Instance Type** | `Free` | |

---

### Step 1.3: Set Backend Environment Variables
Scroll down to the **Environment Variables** section and click **Add Environment Variable** for each:

| Environment Variable | Value | Description |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | Locks the exact Python runtime |
| `ENVIRONMENT` | `production` | Enables production mode |
| `DEBUG` | `false` | Hides debug tracebacks |
| `SECRET_KEY` | *(Click "Generate" in Render)* | 64-character secret for signing JWT session tokens |
| `DOCUMENT_STORAGE_BACKEND` | `firebase` | Uses Firebase Cloud Storage for FDR PDFs |
| `FIREBASE_STORAGE_ENABLED` | `true` | Activates Firebase Storage SDK |
| `FIREBASE_STORAGE_BUCKET` | `sih-26265-fdr.firebasestorage.app` | Pre-configured SIH bucket |
| `SAKSHYATRAIL_DEMO_MODE` | `true` | Auto-seeds 20 colleges, 80 deposits & test users on launch |
| `CORS_ORIGINS` | `https://*.vercel.app,http://localhost:5173` | Allows requests from your Vercel frontend |

---

### Step 1.4: Provide Firebase Service Account Credentials
Choose **one** of the following two safe methods to grant Firebase access without checking keys into Git:

#### Method A: Direct Environment Variable (Fastest)
1. Open your service account JSON file on your computer (`serviceAccountKey.json` or `sih-26265-fdr-firebase-adminsdk-fbsvc-4f7b832651.json`).
2. Copy the entire contents of the file: `{"type": "service_account", ...}`.
3. In Render -> **Environment Variables**, add:
   - **Key:** `FIREBASE_SERVICE_ACCOUNT_JSON`
   - **Value:** *(Paste the entire JSON string)*

#### Method B: Render Secret File
1. In Render Dashboard, go to your service's **Environment** tab.
2. Under **Secret Files**, click **Add Secret File**:
   - **Filename:** `serviceAccountKey.json`
   - **Contents:** Paste the contents of your service account JSON.
3. Render saves this at `/etc/secrets/serviceAccountKey.json`, which SakshyaTrail automatically discovers.

---

### Step 1.5: Deploy & Validate Backend
1. Click **Create Web Service**.
2. Wait 2–3 minutes for the build to complete until Status shows **Live**.
3. Test your live endpoints in a browser:
   - **Health Check:** `https://<your-render-name>.onrender.com/healthz`  
     *Expected response:* `{"status":"ok","timestamp":"..."}`
   - **Interactive API Docs:** `https://<your-render-name>.onrender.com/docs`  
     *Verifies all 158 OpenAPI endpoints are live.*

> [!IMPORTANT]
> **Copy your Render URL** (e.g. `https://sakshyatrail-backend.onrender.com`). You will need it in Phase 2 for Vercel.

---

## PHASE 2: DEPLOY FRONTEND ON VERCEL

### Step 2.1: Import Project into Vercel
1. Log in to [vercel.com](https://vercel.com/).
2. Click **Add New...** -> **Project**.
3. Connect your GitHub repository and click **Import**.

### Step 2.2: Configure Project Settings
In the **Configure Project** setup screen:

1. **Root Directory:**
   - Click **Edit** next to Root Directory.
   - Select the `frontend` folder and click **Continue**.
2. **Framework Preset:**
   - Vercel automatically selects **Vite**.
3. **Build and Output Settings:**
   - **Build Command:** `npm run build` *(or leave default)*
   - **Output Directory:** `dist` *(or leave default)*
   - **Install Command:** `npm install` *(or leave default)*

---

### Step 2.3: Set Frontend Environment Variable
Expand the **Environment Variables** section and add:

| Key | Value | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `https://<your-render-name>.onrender.com/api/v1` | Replace with your live Render backend URL |

> [!TIP]
> SakshyaTrail's API client is intelligent: even if you enter `https://<your-render-name>.onrender.com` without `/api/v1`, it automatically normalizes and appends the `/api/v1` prefix.

---

### Step 2.4: Deploy & Verify
1. Click **Deploy**.
2. Vercel will install dependencies, compile TypeScript, and build Vite assets in ~30-45 seconds.
3. You will receive your production URL (e.g. `https://sakshyatrail.vercel.app`).

---

## PHASE 3: VERIFICATION & PRE-SEEDED CREDENTIALS

Open your Vercel URL in your browser. The platform arrives pre-seeded with synthetic institutional data, deposit lifecycles, and accounts for all 7 regulatory roles:

| Regulatory Role | Email Address | Password | Primary Workspace / Capabilities |
|---|---|---|---|
| **System Administrator** | `admin@aicte-india.org` | `Admin@12345` | Platform Governance, User Provisioning, System Health |
| **Scrutiny Officer** | `officer@aicte-india.org` | `Admin@12345` | Scrutiny Queue, Maker Release Recommendations |
| **Competent Authority** | `authority@aicte-india.org` | `Admin@12345` | Executive Dashboard, Checker Dual-Control Approvals |
| **Finance Officer** | `finance@aicte-india.org` | `Admin@12345` | Financial Reconciliation & Guarantee Ledger |
| **Compliance Auditor** | `auditor@aicte-india.org` | `Admin@12345` | Read-only Audit Trail & SHA-256 Chain Verification |
| **Nodal Officer (COEP Pune)** | `nodal.pun001@coep.ac.in` | `Admin@12345` | Institutional Portal, Deposit Submission, Renewal |
| **Nodal Officer (VJTI Mumbai)** | `nodal.mum001@vjti.ac.in` | `Admin@12345` | Institutional Portal, Deposit Submission, Renewal |

---

## PHASE 4: ARCHITECTURAL SAFEGUARDS BUILT-IN

### 1. SPA Deep Linking (`vercel.json`)
A common issue in React Single-Page Applications on Vercel is getting a `404 Not Found` when refreshing a page like `/instruments/1` or `/verification`.  
- **Solution:** [`frontend/vercel.json`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/frontend/vercel.json) includes route rewrites (`"source": "/(.*)", "destination": "/index.html"`) ensuring all direct links resolve properly.

### 2. Cross-Domain Cookie & Bearer Token Authentication
Because Vercel (`*.vercel.app`) and Render (`*.onrender.com`) reside on different top-level domains, modern browsers block cross-site cookies by default.
- **Solution:** [`frontend/src/api/client.ts`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/frontend/src/api/client.ts) automatically stores the JWT token upon login and attaches it as `Authorization: Bearer <token>` on all requests.
- **Backend CSRF Exemption:** The backend CSRF validator recognizes Bearer-authenticated API calls as secure against CSRF, allowing cross-domain communication without browser friction.

### 3. Dynamic CORS Origin Whitelisting
- **Solution:** The backend CORS middleware utilizes the regex:
  `^https?:\/\/(.*\.vercel\.app|localhost|127\.0\.0\.1)(:[0-9]+)?$`
  This guarantees that every preview deployment, branch deploy, and production deploy on Vercel is automatically authorized to communicate with your Render backend.

---

## PHASE 5: TROUBLESHOOTING & FAQ

### Q1: The initial page load takes ~30-45 seconds when calling the backend.
- **Cause:** Render's free tier spins down web services after 15 minutes of inactivity.
- **Behavior:** The first request spins up the container. Subsequent requests respond instantly (<100ms).

### Q2: How can I confirm Firebase Storage is operating?
- Log into the portal as `admin@aicte-india.org`.
- Go to any FDR detail page (`/instruments/1`) and upload a test PDF in the Documents tab.
- Check that:
  1. The SHA-256 byte digest is calculated.
  2. The file is uploaded to `sih-26265-fdr.firebasestorage.app`.
  3. Clicking "Preview" or "Download" securely streams the file bytes.

### Q3: How do I verify the Tamper-Evident Audit Chain?
- Navigate to the **Audit Cockpit** (`/audit`).
- Click **Verify Audit Chain**.
- The backend iterates through all cryptographic hashes in the SQLite database and confirms:
  `"valid": true, "broken_index": null`.
