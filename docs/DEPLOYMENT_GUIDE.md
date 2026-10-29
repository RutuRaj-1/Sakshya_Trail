# SAKSHYATRAIL CLOUD DEPLOYMENT GUIDE (RENDER & VERCEL)

**Project:** SakshyaTrail — Security Deposit / FDR Lifecycle Integrity Platform  
**Architecture:**
- **Backend:** FastAPI + Python 3.11 -> **Render Web Service**
- **Frontend:** React 19 + TypeScript + Vite -> **Render Web Service (or Static Site) / Vercel**
- **Document Storage:** Firebase Cloud Storage (`sih-26265-fdr.firebasestorage.app`)
- **Database:** SQLite (Auto-seeded with 20 demo institutions) or Render PostgreSQL

---

## PART 1: DEPLOY BACKEND ON RENDER (FIRST)

Deploy the backend first to obtain your backend API URL (e.g. `https://sakshyatrail-backend.onrender.com`).

### Manual Web Service Setup (Backend):
1. In the Render Dashboard, click **+ New** -> **Web Service** (from the menu in your screenshot).
2. Connect your GitHub repository.
3. Configure the backend settings:
   - **Name:** `sakshyatrail-backend`
   - **Language / Runtime:** `Python`
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
4. Under **Environment Variables**, add:
   - `PYTHON_VERSION`: `3.11.9`
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `false`
   - `SECRET_KEY`: *(Click "Generate")*
   - `DOCUMENT_STORAGE_BACKEND`: `firebase`
   - `FIREBASE_STORAGE_ENABLED`: `true`
   - `FIREBASE_STORAGE_BUCKET`: `sih-26265-fdr.firebasestorage.app`
   - `SAKSHYATRAIL_DEMO_MODE`: `true`
   - `FIREBASE_SERVICE_ACCOUNT_JSON`: *(Paste the entire contents of your serviceAccountKey.json)*
5. Click **Deploy Web Service**.
6. Once deployed, test `https://<your-backend-name>.onrender.com/healthz` and copy your URL.

---

## PART 2: DEPLOY FRONTEND AS A WEB SERVICE ON RENDER

To deploy the frontend as a **Web Service** on Render:

### Step-by-Step Setup:
1. In the Render Dashboard, click **+ New** -> **Web Service**.
2. Select the same GitHub repository.
3. Configure the following service settings:
   - **Name:** `sakshyatrail-frontend`
   - **Language / Runtime:** `Node`
   - **Branch:** `main`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Start Command:** `npx serve -s dist -l $PORT`
   - **Instance Type:** `Free`

4. Under **Environment Variables**, add:
   - **Key:** `NODE_VERSION`
     **Value:** `20.18.0`
   - **Key:** `VITE_API_BASE_URL`
     **Value:** `https://<your-backend-name>.onrender.com/api/v1`  
     *(Replace with your actual backend Render URL)*

5. Click **Create Web Service**.

> **Note on Start Command:** A compiled React/Vite single-page app requires a lightweight HTTP server to listen on Render's dynamic `$PORT`. The `npx serve -s dist -l $PORT` command serves the compiled production build and automatically handles SPA client-side routing.

---

### Alternative: Deploy Frontend as "Static Site" on Render (100% Free, Zero Cold Starts)
In the **+ New** dropdown in Render, the first option is **Static Site**:
- **Why Render offers this:** Pure React applications do not require a Node server running 24/7.
- **Benefits:** Unlike free Web Services which sleep after 15 minutes of inactivity, Render Static Sites **never sleep**, have **no spin-up delays**, and include a free global CDN.
- **Settings if using Static Site:**
  - **Root Directory:** `frontend`
  - **Build Command:** `npm run build`
  - **Publish Directory:** `dist`
  - Under **Redirects/Rewrites**:
    - **Source:** `/*`
    - **Destination:** `/index.html`
    - **Action:** `Rewrite`
  - **Environment Variable:** `VITE_API_BASE_URL` = `https://<your-backend-name>.onrender.com/api/v1`

---

## PART 3: 1-CLICK DEPLOY BOTH VIA BLUEPRINT

You can also deploy both Backend and Frontend Web Services at once using Render's **Blueprint** feature (the last item in your "+ New" menu):
1. In Render, click **+ New** -> **Blueprint**.
2. Select your repository.
3. Render reads [`render.yaml`](file:///c:/Users/bhome/OneDrive/Desktop/VIT/SIH/SIH%202026/TOP%2075/FDR_Sentinel/render.yaml) and provisions:
   - `sakshyatrail-backend` (Python Web Service)
   - `sakshyatrail-frontend` (Node Web Service)
4. It automatically binds the backend URL to the frontend environment.
5. Paste your `FIREBASE_SERVICE_ACCOUNT_JSON` and click **Apply**.
