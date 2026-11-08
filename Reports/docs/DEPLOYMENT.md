# DEPLOYMENT GUIDE — Joybox Party Room
**Production Architecture, Configuration, and Deployment Runbook**
*Version 1.0 · Render (Backend + Cron) · Vercel (Frontend) · MongoDB Atlas*

---

## 1. Architecture Overview

```
                      ┌───────────────────────────────────────────┐
                      │            DNS / Cloudflare               │
                      └─────────────┬─────────────────────────────┘
                                    │
             ┌──────────────────────┴──────────────────────┐
             │                                             │
             ▼                                             ▼
┌─────────────────────────┐                   ┌─────────────────────────┐
│     Vercel Frontend     │                   │   Render Web Service    │
│  (React 18 + Vite SPA)  │                   │  (Flask + Gunicorn WSGI)│
│  joyboxpartyroom.com    │                   │  api.joyboxpartyroom.com│
└────────────┬────────────┘                   └────────────┬────────────┘
             │                                             │
             │ HTTPS / REST API                            │ MONGODB-SRV / TLS
             │                                             ▼
             │                                ┌─────────────────────────┐
             │                                │      MongoDB Atlas      │
             │                                │    (Dedicated M10+)     │
             │                                └─────────────────────────┘
             ▼                                             ▲
┌─────────────────────────┐                                │
│   Razorpay Gateway      │──────── Webhooks ──────────────┘
│  (Standard Checkout)    │
└─────────────────────────┘
```

---

## 2. Infrastructure Requirements

### 2.1 MongoDB Atlas
- **Cluster Tier:** Minimum M10 for production (automated daily backups, point-in-time recovery, dedicated vCPU/RAM).
- **Network Access List:**
  - Render static outbound IPs (if using Render Team/Org with outbound IP add-on) OR `0.0.0.0/0` with strong, rotating database user credentials.
- **Database Names:**
  - Production: `joybox_party_room`
  - Testing / Staging: `joybox_party_room_test`
- **Safety Invariant:** All destructive tests and automated test suites strictly verify that database names end in `_test`. Production operations are never run against `*_test`.

### 2.2 Render (Backend & Cron)
- **Service 1: Web Service (`joybox-backend`)**
  - **Environment:** Python 3.11 (`runtime.txt`)
  - **Plan:** Starter or Standard (persistent memory, no cold sleeps)
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn --workers 3 --bind 0.0.0.0:$PORT run:app`
  - **Health Check Path:** `/api/health`
- **Service 2: Cron Job (`joybox-sweeper`)**
  - **Schedule:** `*/10 * * * *` (Every 10 minutes)
  - **Command:** `python -m app.jobs.run_sweeps`

### 2.3 Vercel (Frontend)
- **Framework:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Node Version:** 18.x or 20.x

---

## 3. Environment Variables Reference

### Backend (Render Web & Cron)

| Variable | Description | Example / Required Value |
|---|---|---|
| `FLASK_ENV` | Environment identifier | `production` |
| `DEBUG` | Enable debug logs | `false` |
| `SECRET_KEY` | Flask session & cryptographic salt | Strong 64-char hex string |
| `JWT_SECRET` | Secret key for admin JWT cookies | Strong 64-char hex string |
| `MONGO_URI` | MongoDB Atlas connection string | `mongodb+srv://<user>:<password>@cluster.mongodb.net/joybox_party_room?retryWrites=true&w=majority` |
| `DB_NAME` | Database name | `joybox_party_room` |
| `FRONTEND_ORIGIN` | Allowed CORS origins (comma-separated) | `https://joyboxpartyroom.com,https://www.joyboxpartyroom.com` |
| `RAZORPAY_KEY_ID` | Razorpay Live API Key ID | `rzp_live_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay Live API Key Secret | Secret from Razorpay Dashboard |
| `RAZORPAY_WEBHOOK_SECRET` | Razorpay Webhook Signature Secret | Secret configured in Razorpay Webhooks |
| `HOST_PHONE` | Venue Host Kiran Kumar contact | `+917842704429` |
| `OPERATING_START_HOUR` | Opening hour (IST) | `9` (09:00 AM) |
| `OPERATING_END_HOUR` | Closing hour (IST) | `22` (10:00 PM) |
| `BUFFER_MINUTES` | Turnaround cleaning buffer | `30` |
| `HOLD_DURATION_MINUTES` | Provisional hold window | `15` |
| `RECONCILIATION_AGE_MINUTES`| Pending order age for sweep | `30` |

### Frontend (Vercel)

| Variable | Description | Example / Required Value |
|---|---|---|
| `VITE_API_BASE_URL` | Base URL of deployed backend API | `https://api.joyboxpartyroom.com/api` |
| `VITE_RAZORPAY_KEY_ID` | Razorpay Public Key ID | `rzp_live_...` (matches backend) |
| `VITE_WHATSAPP_NUMBER` | Venue Host phone for WhatsApp | `917842704429` |

---

## 4. Step-by-Step Deployment Instructions

### Step 1: MongoDB Atlas Setup
1. Create a production cluster on MongoDB Atlas in `ap-south-1` (Mumbai).
2. Create database user `joybox_app` with `readWrite` permissions on database `joybox_party_room`.
3. Add Render's outbound IPs to Network Access (or `0.0.0.0/0`).
4. Copy the SRV connection URI.
5. Seed initial packages, add-ons, offers, gallery, FAQs, indexes, and initial super administrator:
   ```bash
   cd backend
   export MONGO_URI="mongodb+srv://..."
   export DB_NAME="joybox_party_room"
   python scripts/init_indexes.py
   python scripts/seed_all.py
   python scripts/create_admin.py --username admin --email admin@joyboxpartyroom.com --password <SECURE_PASS> --role super_admin --name "Kiran Kumar"
   ```

### Step 2: Render Backend Deployment
1. Connect Joybox Git repository to Render.
2. Select **Blueprint** and use root `render.yaml`, or create manually:
   - Create **Web Service**:
     - Root: `backend`
     - Runtime: `Python 3`
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn --workers 3 --bind 0.0.0.0:$PORT run:app`
     - Health Check Path: `/api/health`
   - Create **Cron Job**:
     - Root: `backend`
     - Schedule: `*/10 * * * *`
     - Command: `python -m app.jobs.run_sweeps`
3. Enter all environment variables listed in Section 3 in the Render Dashboard.
4. Trigger manual deploy.
5. Verify health:
   ```bash
   curl -I https://api.joyboxpartyroom.com/api/health
   # Expected HTTP/1.1 200 OK
   # {"success":true,"data":{"database":"connected","status":"ok",...}}
   ```

### Step 3: Razorpay Webhook Configuration
1. Log in to [Razorpay Dashboard](https://dashboard.razorpay.com/) (Live Mode).
2. Navigate to **Settings > Webhooks > Add New Webhook**.
3. **Webhook URL:** `https://api.joyboxpartyroom.com/api/payments/webhook`
4. **Secret:** Generate a high-entropy string (match `RAZORPAY_WEBHOOK_SECRET`).
5. **Active Events:**
   - `order.paid`
   - `payment.authorized`
   - `payment.captured`
   - `payment.failed`
   - `refund.processed`
   - `refund.failed`
6. Save and send a test ping to verify connectivity.

### Step 4: Vercel Frontend Deployment
1. Log in to Vercel and import the Git repository.
2. Configure Project Settings:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. Enter Environment Variables (`VITE_API_BASE_URL`, `VITE_RAZORPAY_KEY_ID`, `VITE_WHATSAPP_NUMBER`).
4. Click **Deploy**.
5. Once deployed, verify:
   - Homepage loads without console errors.
   - Package pricing matches backend database.
   - Fonts render Fredoka and Poppins as designed.
   - Admin route `/admin` redirects cleanly to `/admin/login`.

---

## 5. Security & Maintenance Operations

### 5.1 Routine Database Backups
- Automated Atlas snapshots run daily.
- On-demand manual backups before releases:
  ```bash
  cd backend
  python scripts/db_backup.py backup --db joybox_party_room --out backups/pre_release.json.gz
  ```

### 5.2 Safe Staging Restoration Drill
To test database restoration safely without touching production:
```bash
cd backend
python scripts/db_backup.py restore --db joybox_party_room_test --in backups/pre_release.json.gz
```
*(The restore script enforces that the target database ends in `_test`)*

### 5.3 Secret Rotation Protocol
1. **JWT Secret:** Change `JWT_SECRET` in Render. Existing admin sessions will be invalidated and require re-login.
2. **Flask Secret Key:** Change `SECRET_KEY` in Render.
3. **Razorpay Secrets:** Update both in Razorpay Dashboard and Render environment simultaneously.

---

## 6. Cross-Site & Single-Origin Authentication Architecture

### 6.1 Architecture Selection: Vercel Reverse Proxy Rewrite
To eliminate third-party cookie blocking across modern privacy-focused browsers (Apple Safari ITP, Google Chrome Privacy Sandbox, Firefox ETP), Joybox employs the **Single-Origin Vercel Reverse Proxy Rewrite**:

```
Browser Client (Vercel Origin: https://joyboxparty.in or https://joybox.vercel.app)
  │
  ├──► Static Assets & SPA Routes  ──► Served directly from Vercel Edge CDN
  │
  └──► /api/:path*                 ──► Proxied transparently to Render Web Service
                                       (https://joybox-backend.onrender.com/api/:path*)
```

#### Why This Approach:
1. **First-Party Context:** All API requests made by the frontend (including `/api/admin/auth/login`) are directed to `/api/...` on the **exact same origin** as the frontend. The resulting `joybox_admin_session` cookie is treated as a **first-party cookie**, completely immune to third-party cookie deprecation.
2. **Zero Preflight Latency:** Eliminates cross-origin CORS `OPTIONS` preflight roundtrips for same-origin API interactions.
3. **Host-only cookies:** The browser talks to the Vercel host, and Vercel proxies `/api` to Render. The admin session cookie is host-only. Do not set a `Domain` attribute. `ADMIN_COOKIE_DOMAIN` is not used.

### 6.2 Cookie Security Specifications

| Attribute | Value | Enforced Guard & Description |
| :--- | :--- | :--- |
| **Name** | `joybox_admin_session` | Configurable via `ADMIN_SESSION_COOKIE_NAME`. |
| **HttpOnly** | `True` | Inaccessible to JavaScript; prevents session hijacking via XSS. |
| **Secure** | `True` | Enforced in staging & production (`ADMIN_COOKIE_SECURE = true`). HTTPS only. |
| **SameSite** | `Lax` | Protects against CSRF on state-changing cross-origin requests while permitting top-level navigation. |
| **Path** | `/api/admin` | Restricted to admin endpoint hierarchy; not sent on public assets or customer booking routes. |
| **Domain** | Host-only | No `Domain` attribute. The Vercel rewrite keeps the cookie on the site host. |

### 6.3 CSRF Protection Pattern
- **Pattern:** Cryptographic Double-Submit Token.
- **Login Response:** Returns `csrfToken` in authenticated response JSON payload (`data.csrfToken`).
- **Client Storage:** Kept in-memory in React `AdminAuthProvider` state (never written to `localStorage`).
- **Mutation Verification:** Every state-changing admin request (`POST`, `PUT`, `DELETE`, `PATCH`) must supply the `X-CSRF-Token` header. Rejection with HTTP 403 `CSRF_TOKEN_INVALID` occurs if missing or mismatched.

### 6.4 Staging Login Verification Checklist

Follow these verification steps when staging is deployed:
1. Open Chrome/Safari Developer Tools -> **Application > Cookies**.
2. Navigate to `https://<staging-app>.vercel.app/admin/login`.
3. Enter valid staging admin credentials (`owner` / password).
4. Inspect Network tab:
   - Request to `POST /api/admin/auth/login` returns HTTP 200.
   - Response header contains `Set-Cookie: joybox_admin_session=...; Path=/api/admin; Secure; HttpOnly; SameSite=Lax`.
   - Cookie is registered under the Vercel domain as a **first-party cookie** (no yellow warning icon).
5. Navigate through Admin tabs (Bookings, Add-ons, Pricing, Inquiries, Audit Logs):
   - All subsequent requests to `/api/admin/*` automatically include the `joybox_admin_session` cookie.
   - Mutating actions (e.g. updating booking status) send header `X-CSRF-Token: <token>` and succeed.

