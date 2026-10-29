# SAKSHYATRAIL CLOUD DEPLOYMENT GUIDE (VERCEL + RENDER)

**Project:** SakshyaTrail — Security Deposit / FDR Lifecycle Integrity Platform  
**Architecture:**
- **Frontend:** React 19 + TypeScript + Vite + Tailwind CSS -> **Deployed on Vercel**
- **Backend:** FastAPI + Python 3.11 + SQLAlchemy + Pydantic -> **Deployed on Render**
- **Document Storage:** Firebase Cloud Storage (`sih-26265-fdr.firebasestorage.app`) with local disk fallback
- **Database:** SQLite (Bundled synthetic demo DB) or Render PostgreSQL

---

## PART 1: DEPLOY BACKEND ON RENDER

Deploy the backend first so you obtain your live Render backend URL (e.g., `https://sakshyatrail-api.onrender.com`).

### Option A: 1-Click Render Blueprint (Recommended)

1. Push your repository to **GitHub**.
2. Log in to [dashboard.render.com](https://dashboard.render.com/).
3. Click **New +** (top right) and select **Blueprint**.
4. Connect your GitHub repository.
5. Render will automatically detect [`render.yaml`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/render.yaml) and configure the web service with all build and start commands.
6. Under **Environment Variables**, supply your Firebase credentials (see below).
7. Click **Apply**.

---

### Option B: Manual Web Service Setup on Render

If you prefer to configure manually:

1. In Render Dashboard, click **New +** -> **Web Service**.
2. Select **Build and deploy from a Git repository** and pick your repository.
3. Configure the following service settings:
   - **Name:** `sakshyatrail-backend` (or your chosen name)
   - **Language / Runtime:** `Python`
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`

4. Scroll down to **Environment Variables** and add the following keys:

| Environment Variable | Recommended Value | Notes |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | Ensures compatibility with Python dependencies |
| `ENVIRONMENT` | `production` | Enables production mode |
| `DEBUG` | `false` | Disables debug stack traces in errors |
| `SECRET_KEY` | *(Click "Generate" in Render)* | Random 64-char string for signing JWT tokens |
| `DOCUMENT_STORAGE_BACKEND` | `firebase` | Uses Firebase Cloud Storage for uploaded documents |
| `FIREBASE_STORAGE_ENABLED` | `true` | Activates Firebase Storage SDK |
| `FIREBASE_STORAGE_BUCKET` | `sih-26265-fdr.firebasestorage.app` | SIH assigned bucket |
| `SAKSHYATRAIL_DEMO_MODE` | `true` | Auto-seeds 20 demo institutions and all 7 test roles |
| `CORS_ORIGINS` | `https://*.vercel.app,http://localhost:5173` | Allows cross-origin requests from your Vercel frontend |

---

### Supplying Firebase Credentials on Render (Choose 1 of 2 Methods)

To allow the backend to upload documents to Firebase Storage without checking sensitive keys into Git:

#### Method 1: Environment Variable (Easiest)
1. Open your private service account JSON file (`sih-26265-fdr-firebase-adminsdk-fbsvc-4f7b832651.json` or `serviceAccountKey.json`).
2. Copy the **entire JSON string** (including the curly braces `{ "type": "service_account", ... }`).
3. In Render -> **Environment Variables**, add:
   - Key: `FIREBASE_SERVICE_ACCOUNT_JSON`
   - Value: *(Paste the entire JSON string)*

#### Method 2: Render Secret File
1. In Render Dashboard, go to your service -> **Environment** -> **Secret Files**.
2. Click **Add Secret File**:
   - **Filename:** `serviceAccountKey.json`
   - **Contents:** Paste the contents of your service account JSON.
3. Render saves this file to `/etc/secrets/serviceAccountKey.json` automatically, and SakshyaTrail's backend detects it at startup.

---

### Step 3: Verify the Live Backend

Once Render finishes deploying (Status: `Live`), test the endpoints in your browser:
- Welcome probe: `https://<your-render-name>.onrender.com/`
- Health probe: `https://<your-render-name>.onrender.com/healthz`
- OpenAPI Swagger Docs: `https://<your-render-name>.onrender.com/docs`

Copy your Render URL (e.g. `https://sakshyatrail-backend.onrender.com`). You will need it for Vercel.

---

## PART 2: DEPLOY FRONTEND ON VERCEL

### Step 1: Import Project into Vercel
1. Log in to [vercel.com](https://vercel.com/).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository.

### Step 2: Configure Project Settings
In the **Configure Project** screen:

1. **Root Directory:**
   - Click **Edit** next to Root Directory.
   - Select the `frontend` folder and click **Continue**.
2. **Framework Preset:**
   - Vercel will auto-detect **Vite**.
3. **Build and Output Settings:**
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
   - **Install Command:** `npm install`
4. **Environment Variables:**
   - Expand the **Environment Variables** section.
   - Add:
     - **Key:** `VITE_API_BASE_URL`
     - **Value:** `https://<your-render-name>.onrender.com/api/v1`  
       *(Note: Even if you enter `https://<your-render-name>.onrender.com` without `/api/v1`, SakshyaTrail's client automatically resolves and normalizes it!)*

### Step 3: Deploy
1. Click **Deploy**.
2. Vercel will build the React + TypeScript application and output your production domain:
   `https://sakshyatrail.vercel.app` (or similar).

---

## PART 3: ARCHITECTURAL SAFEGUARDS BUILT-IN

### 1. SPA Deep Linking (`vercel.json`)
Client-side routes such as `/instruments/1`, `/verification`, or `/release` will not return 404 on page refresh because [`frontend/vercel.json`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/frontend/vercel.json) rewrites all incoming paths to `/index.html`.

### 2. Cross-Domain Authentication & Bearer Injection
When frontend and backend reside on different domains (`*.vercel.app` vs `*.onrender.com`), browsers frequently block cross-site cookies. SakshyaTrail overcomes this:
- On login, the JWT is stored in `localStorage` under `fdr_token`.
- Every outgoing request automatically includes `Authorization: Bearer <token>`.
- The backend's CSRF guard exempts requests bearing a valid Authorization header.

### 3. Automatic Database Seeding
When launching on Render, if an empty database is detected (such as a newly provisioned PostgreSQL or SQLite instance), the application automatically seeds:
- 20 Synthetic Colleges across Pune and Mumbai
- 80 FDR instruments with realistic life-cycle statuses
- Demo login accounts for all 7 RBAC roles:
  - System Admin: `admin@aicte-india.org` (Password: `Admin@12345`)
  - Scrutiny Officer: `officer@aicte-india.org`
  - Competent Authority: `authority@aicte-india.org`
  - Nodal Institutional User: `nodal.pun001@coep.ac.in`

---

## PART 4: PRODUCTION VERIFICATION CHECKLIST

Once deployed:
1. Open your Vercel URL in your browser: `https://your-app.vercel.app`.
2. Log in using `admin@aicte-india.org` / `Admin@12345`.
3. Check the **Dashboard** metrics — verify that total FDR counts and amounts load.
4. Navigate to **Instruments** (`/instruments`) — verify search and filtering.
5. Upload an FDR document — check that the SHA-256 byte digest computes and the file streams to Firebase Cloud Storage.
6. Verify the **Audit Trail** (`/audit`) — click "Verify Audit Chain" to confirm mathematical SHA-256 integrity.

