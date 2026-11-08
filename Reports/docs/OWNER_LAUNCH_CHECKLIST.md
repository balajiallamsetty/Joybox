# Joybox Party Room — Consolidated Venue Owner Launch Checklist

**Venue:** Joybox Party Room (Beside Durga Mart, Vadlamudi, Guntur, AP - 522213)  
**Host Contact:** Kiran Kumar (+91 78427 04429)  
**Audit Branch:** `staging/verification-and-gap-closure`  
**Current Date:** November 2026  

---

## 1. Master Launch Readiness Checklist

| ID | Category | Action Item | Platform / Scope | Status | Verification Procedure |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **SEC-01** | Security | Rotate exposed historical MongoDB Atlas password | MongoDB Atlas | **OPEN / ACTION REQ** | Generate 32-char password in Atlas; verify old password fails. |
| **SEC-02** | Security | Create dedicated least-privilege `joybox_app` user (`readWrite` on `joybox_party_room` only) | MongoDB Atlas | **OPEN / ACTION REQ** | In Atlas Database Access, assign user specific DB privileges. |
| **SEC-03** | Security | Generate high-entropy 64-char `JWT_SECRET_KEY` | Render Environment | **CONFIGURABLE** | `python -c "import secrets; print(secrets.token_hex(32))"` |
| **SEC-04** | Security | Enable `ADMIN_COOKIE_SECURE=true` and `SameSite=Lax` | Render Environment | **DONE** | Audited in Section 6 of `DEPLOYMENT.md`; verified in tests. |
| **SEC-05** | Security | Configure single-origin Vercel rewrite (`/api/:path* -> Render`) | Vercel (`vercel.json`) | **DONE** | Proxy rule committed in `frontend/vercel.json`. |
| **SEC-06** | Security | Enforce PII scrubbing on all backend application logs | Flask Logging Filter | **DONE** | `PIIScrubbingFilter` active and tested (2/2 tests pass). |
| **NET-01** | Networking | Whitelist Render dynamic NAT outbound IPs (`0.0.0.0/0` with SCRAM auth) | MongoDB Atlas | **OPEN / ACTION REQ** | In Atlas Network Access, verify entry with comment. |
| **NET-02** | Networking | Set up custom domain DNS records (`joyboxvadlamudi.com` -> Vercel CNAME) | DNS Registrar (GoDaddy/Cloudflare) | **OPEN / ACTION REQ** | `dig joyboxvadlamudi.com +short` returns Vercel edge IP. |
| **PAY-01** | Payments | Toggle Razorpay Dashboard from Test Mode to Live Mode when ready | Razorpay Dashboard | **OPEN / ACTION REQ** | Generate `rzp_live_...` key and secret. |
| **PAY-02** | Payments | Register production Razorpay webhook URL (`https://.../api/payments/webhook`) | Razorpay Dashboard | **OPEN / ACTION REQ** | Add webhook for `payment.captured`, `payment.failed`, `refund.processed`. |
| **PAY-03** | Payments | Set `PAYMENTS_ENABLED=true` when launch ready (currently deferred `false`) | Render Environment | **CONFIGURABLE** | Flip flag in Render after webhook and live keys configured. |
| **OPS-01** | Operations | Configure UptimeRobot monitor for `HEAD /api/health` (5-minute interval) | UptimeRobot | **OPEN / ACTION REQ** | Set up pinger to keep Render dyno warm and alert host. |
| **OPS-02** | Operations | Configure Sentry error tracking DSNs (`SENTRY_DSN`, `VITE_SENTRY_DSN`) | Sentry.io | **CONFIGURABLE** | Add DSNs to Render and Vercel environment dashboards. |
| **OPS-03** | Operations | Perform verified backup snapshot drill before production traffic | MongoDB Atlas | **DONE** | Drill completed; 100% count parity verified in `DATA_SAFETY.md`. |
| **BIZ-01** | Business | Confirm operating hours 09:00 - 22:00 IST | Venue Rules | **DONE** | Enforced across code and tested in slot generation. |
| **BIZ-02** | Business | Confirm 30-minute cleaning buffer between party slots | Venue Rules | **DONE** | Atomic slot claim buffer verified in tests. |
| **BIZ-03** | Business | Confirm max advance booking window (90 days) | Venue Rules | **DONE** | Enforced in date utils and booking wizard. |
| **BIZ-04** | Business | Confirm first-5-bookings promo quota and non-stacking rules | Promotions Engine | **DONE** | Verified in `BOOKING_AND_PROMO_MATRIX.md`. |
| **BIZ-05** | Business | Review and approve cancellation refund tiers (100% >48h, 50% 24-48h, 0% <24h) | Policy Pages | **OPEN / ACTION REQ** | Review placeholder banners on `/terms`, `/privacy`, `/refund-policy`. |

---

## 2. Step-by-Step Owner Execution Runbooks

### Runbook 1: MongoDB Atlas Credential Rotation & Least-Privilege Setup
1. Log in to [cloud.mongodb.com](https://cloud.mongodb.com/).
2. Navigate to **Security** $\rightarrow$ **Database Access**.
3. Create production app user:
   - Click **+ Add New Database User**
   - Username: `joybox_app`
   - Password: Click **Autogenerate Secure Password** (save to password manager).
   - Database User Privileges: Select **Specific Privileges**:
     - Role: `readWrite` $\rightarrow$ Database: `joybox_party_room`
   - Click **Add User**.
4. Create test database user (for CI/CD and staging):
   - Click **+ Add New Database User**
   - Username: `joybox_test_runner`
   - Database User Privileges: `readWrite` on `joybox_party_room_test` ONLY.
5. In **Security** $\rightarrow$ **Network Access**:
   - Ensure an active entry allows Render dynamic IP access (e.g. `0.0.0.0/0` with comment `Render Dynamic NAT`).

### Runbook 2: Render Backend Environment Configuration
In [dashboard.render.com](https://dashboard.render.com/) under service `joybox-backend` $\rightarrow$ **Environment**:
```env
FLASK_ENV=production
MONGODB_URI=mongodb+srv://joybox_app:<new-password>@<cluster>.mongodb.net/joybox_party_room?retryWrites=true&w=majority
MONGODB_DB=joybox_party_room
JWT_SECRET_KEY=<generate-random-64-character-hex-string>
FRONTEND_ORIGIN=https://joyboxvadlamudi.com,https://joybox.party
ADMIN_COOKIE_SECURE=true
ADMIN_COOKIE_SAMESITE=Lax
# Do not set ADMIN_COOKIE_DOMAIN. Admin cookies are host-only.
TRUSTED_PROXY_COUNT=2
MAX_ADVANCE_BOOKING_DAYS=90
PAYMENTS_ENABLED=false
```
*(When payments are ready to go live, set `PAYMENTS_ENABLED=true` and input Live Razorpay keys).*

### Runbook 3: Vercel Frontend Environment Configuration
In [vercel.com](https://vercel.com/) under your project $\rightarrow$ **Settings** $\rightarrow$ **Environment Variables**:
```env
VITE_API_BASE_URL=https://joyboxvadlamudi.com/api
```
*(Single-origin rewrite in `vercel.json` automatically routes `/api/:path*` to `https://joybox-backend.onrender.com/api/:path*`).*

### Runbook 4: Razorpay Live Activation (When Launching Payments)
1. In [dashboard.razorpay.com](https://dashboard.razorpay.com/), toggle switch to **Live Mode**.
2. Go to **Account & Settings** $\rightarrow$ **API Keys** $\rightarrow$ **Generate Live Key**.
3. Copy Key ID and Key Secret to Render backend environment variables.
4. Go to **Account & Settings** $\rightarrow$ **Webhooks** $\rightarrow$ **Add New Webhook**:
   - URL: `https://joyboxvadlamudi.com/api/payments/webhook`
   - Secret: Generate random 32-character string.
   - Events: Check `payment.captured`, `payment.failed`, `refund.processed`.
5. Set `RAZORPAY_WEBHOOK_SECRET` in Render.

### Runbook 5: Business Policy Review & Legal Text Approval
Host Kiran Kumar must read through the three public policy drafts:
1. `https://joyboxvadlamudi.com/terms` (Cancellation notice, house rules, alcohol & smoke restrictions).
2. `https://joyboxvadlamudi.com/privacy` (Customer phone number handling, WhatsApp notifications).
3. `https://joyboxvadlamudi.com/refund-policy` (Notice windows: 48h full refund, 24-48h 50% refund, <24h non-refundable).
Confirm approval and request removal of the `[Owner Review Placeholder Notice]` banners.
