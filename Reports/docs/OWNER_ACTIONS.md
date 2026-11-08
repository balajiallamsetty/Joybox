# JOYBOX PARTY ROOM — OWNER ACTIONS & DECISION LOG

**Date:** 2026-10-29  
**Platform:** Joybox Party Room (Hourly Party-Hall Booking Platform, Guntur, AP)  
**Author:** Principal Full-Stack Engineer & Payments Reliability Specialist  

This document outlines the required administrator actions across external dashboards (Razorpay, MongoDB Atlas, Render, Vercel) and business policy decisions that cannot be performed programmatically by automated agents.

---

## 1. Razorpay Dashboard Actions

> [!NOTE]
> **Test Handshake Status: VERIFIED (HTTP 200)**  
> Fresh test credentials (`rzp_test_<REDACTED_KEY_ID>`) were installed in `backend/.env` and verified via `scripts/test_live_razorpay_handshake.py`, generating live test order `order_TtnvShubKesusw`. When preparing for actual production launch, follow the steps below with your Live Mode keys.

### A. Test vs Production API Keys
1. **Current Test Mode (Active):**
   - Key ID: `rzp_test_<REDACTED_KEY_ID>` (Verified working with live gateway)
2. **Production Launch Preparation:**
   - Log in to [Razorpay Dashboard](https://dashboard.razorpay.com/).
   - When ready for real payments, switch toggle from **Test Mode** to **Live Mode**.
   - Navigate to **Account & Settings** -> **API Keys**.
   - Generate Live Key (`rzp_live_...`) and configure in Render / Vercel environment variables.
   - Run diagnostic with `python scripts/test_live_razorpay_handshake.py` to confirm connectivity.

### B. Configure Webhooks
1. In Razorpay Dashboard (Test Mode), navigate to **Account & Settings** -> **Webhooks**.
2. Click **Add New Webhook**.
3. Fill in the webhook settings:
   - **Webhook URL**: `https://<your-render-backend-url>/api/payments/webhook`
   - **Secret**: Create a strong 32-character random string (e.g. `openssl rand -hex 16`).
   - **Alert Email**: Enter venue owner's email for notification on delivery failures.
4. Select the following **Active Events**:
   - `payment.captured` — Finalizes booking confirmation if frontend checkout modal closes prematurely.
   - `payment.failed` — Marks payment transaction as failed and records error description.
   - `refund.processed` — Updates refund status and reconciles captured payment balance.
5. Save the webhook and copy the secret into `backend/.env` and Render environment variables:
   ```env
   RAZORPAY_WEBHOOK_SECRET=YourWebhookSecretHere
   ```

---

## 2. MongoDB Atlas Configuration Actions

### A. Least-Privilege Database User
Do not use admin credentials (`atlasAdmin` or cluster owner) in the application runtime.
1. In MongoDB Atlas, go to **Database Access** -> **Add New Database User**.
2. **Authentication Method**: Password (SCRAM-SHA-256).
3. **Username**: `joybox_app`
4. **Password**: Generate a secure 32-character password.
5. **Database User Privileges**:
   - Select **Built-in Role** -> **Specific Privileges**.
   - Add privilege: `readWrite` on database `joybox_party_room`.
   - Add privilege: `readWrite` on database `joybox_party_room_test`.
6. Save user.

### B. Network Access & Render Outbound NAT Strategy
Render web services route outbound HTTP and database traffic through dynamic IP address pools that change upon container restart or redeployment.
1. In MongoDB Atlas, navigate to **Network Access** -> **IP Access List**.
2. Click **Add IP Address**.
3. Add `0.0.0.0/0` (Allow Access from Anywhere) with the comment:
   `Render Dynamic Outbound NAT - Restricted via joybox_app user password and TLS`
4. Strict access control is maintained by:
   - Mandatory TLS 1.3 encryption on connection string (`mongodb+srv://...`).
   - High-entropy database password.
   - Least-privilege user scoped strictly to `joybox_party_room`.

---

## 3. Render Deployment Actions (Backend & Background Sweeps)

### A. Web Service Configuration
1. In Render Dashboard, click **New +** -> **Web Service**.
2. Connect your Git repository.
3. Configure the service:
   - **Name**: `joybox-backend`
   - **Region**: `Oregon (US West)` (or closest to audience, e.g. Singapore)
   - **Branch**: `master`
   - **Root Directory**: Leave blank (uses repo root)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `gunicorn --chdir backend --workers 3 --threads 2 --timeout 120 --bind 0.0.0.0:$PORT "app:create_app()"`
   - **Plan**: **Starter ($7/mo)**
     > [!IMPORTANT]
     > Do **NOT** use the Free plan. Free-tier containers spin down after 15 minutes of inactivity. Cold starts take 30–50 seconds, which will cause Razorpay webhooks (5-second timeout) to fail and customers to experience dropped confirmations.
   - **Health Check Path**: `/api/health`
4. Set Environment Variables:
   ```env
   FLASK_ENV=production
   PORT=10000
   MONGODB_URI=mongodb+srv://joybox_app:<password>@<cluster>.mongodb.net/joybox_party_room?retryWrites=true&w=majority
   MONGODB_DB=joybox_party_room
   JWT_SECRET_KEY=<generate-long-random-string>
   RAZORPAY_KEY_ID=rzp_test_...
   RAZORPAY_KEY_SECRET=...
   RAZORPAY_WEBHOOK_SECRET=...
   FRONTEND_ORIGIN=https://joybox-party-room.vercel.app
   ADMIN_COOKIE_SECURE=true
   ADMIN_COOKIE_SAMESITE=Lax
   CHECKOUT_GRACE_MINUTES=15
   MAX_PAYMENT_WINDOW_MINUTES=30
   REFUND_WINDOW_FULL_HOURS=48
   REFUND_WINDOW_PARTIAL_HOURS=24
   REFUND_WINDOW_PARTIAL_PERCENT=50
   REFUND_MIN_NOTICE_HOURS=24
   WHATSAPP_NUMBER=917842704429
   ```

### B. Scheduled Maintenance Sweep (Cron Job)
1. In Render Dashboard, click **New +** -> **Cron Job**.
2. Configure the cron job:
   - **Name**: `joybox-maintenance-sweeps`
   - **Schedule**: `*/10 * * * *` (Runs every 10 minutes)
   - **Command**: `python -m app.jobs.run_sweeps`
   - **Environment Variables**: Add `PYTHONPATH=backend:.` along with `MONGODB_URI` and `MONGODB_DB`.

---

## 4. Vercel Frontend Deployment Actions

1. In Vercel Dashboard, click **Add New...** -> **Project**.
2. Import the Git repository.
3. Configure project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Set Environment Variables:
   ```env
   VITE_API_BASE_URL=https://joybox-backend.onrender.com/api
   VITE_WHATSAPP_NUMBER=917842704429
   VITE_OPENING_TIME=09:00
   VITE_CLOSING_TIME=22:00
   VITE_HOST_NAME=Kiran Kumar
   VITE_RAZORPAY_KEY_ID=rzp_test_...
   ```
5. Deploy and note the assigned production domain (e.g. `joybox-party-room.vercel.app`). Update `FRONTEND_ORIGIN` in Render to match.

---

## 5. Owner Decisions Required

### Decision 1: Landing Page Selection (BUG-13)
The repository contains two landing page implementations converted from Stitch exports:

| Feature / Attribute | `LandingPage.jsx` (`/`) | `LandingPage2.jsx` (`/landing-2`) |
| :--- | :--- | :--- |
| **Architecture** | Modular: Uses shared `Header`, `Footer`, `LanguageContext` | Self-contained: Embeds inline header and footer |
| **Typography** | Standard design system (`Plus Jakarta Sans`) | Alternative typography sizing and weights |
| **Add-On Selection** | Multi-select interactive pills | Custom individual entry checkboxes (Bubble, Fog, Spark) |
| **Responsiveness** | Mobile-first layout with collapsible sections | Desktop-oriented hero banner with fixed calculator |
| **Recommendation** | **Keep as Primary (`/`)** | Keep as secondary preview or redirect to `/` |

**Action Required:** Owner to confirm whether `LandingPage2` (`/landing-2`) should:
- [ ] Be removed from `frontend/src/App.jsx`.
- [ ] Be redirected (`<Route path="/landing-2" element={<Navigate to="/" replace />} />`).
- [ ] Be retained as an A/B testing variant.

### Decision 2: Booking Lifecycle Windows
The following operational defaults are currently implemented in code:
- **Temporary Hold Window**: 10 minutes (`HOLD_DURATION_MINUTES = 10`)
- **Checkout Grace Window**: 15 minutes (`CHECKOUT_GRACE_MINUTES = 15`)
- **Payment Extension Limit**: 30 minutes total (`MAX_PAYMENT_WINDOW_MINUTES = 30`)

**Action Required:** Owner to approve these durations or specify venue adjustments.

### Decision 3: Refund Policy Tiers
The following cancellation tiers are currently implemented in `PaymentService.process_refund`:
- Cancellation `> 48 hours` before celebration: **100% refund**
- Cancellation `24 to 48 hours` before celebration: **50% refund**
- Cancellation `< 24 hours` before celebration: **0% refund (non-refundable)**

**Action Required:** Owner to approve these policy percentages for customer cancellations.

