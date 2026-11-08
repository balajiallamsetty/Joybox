# Joybox Party Room — Production Operations & Monitoring Guide

## 1. Uptime Monitoring (UptimeRobot / Better Uptime)

To prevent customer booking outages and monitor Render web service availability:

### Recommended Setup:
1. Create a free account on [UptimeRobot](https://uptimerobot.com/) or [Better Stack](https://betterstack.com/).
2. Add a new **HTTP(s) Monitor**:
   - **Monitor Type:** `HTTP(s)`
   - **Friendly Name:** `Joybox Backend Health`
   - **URL:** `https://joybox-backend.onrender.com/api/health` (or your custom API domain)
   - **HTTP Method:** `HEAD` or `GET`
   - **Monitoring Interval:** `5 minutes` (keeps free/starter Render dynos warm and detects outages quickly)
   - **HTTP Status Expected:** `200`
   - **Keyword Assertion (optional):** `"status": "ok"`
3. Add a second monitor for the frontend:
   - **Friendly Name:** `Joybox Frontend SPA`
   - **URL:** `https://joyboxvadlamudi.com/` (or Vercel production URL)
   - **Monitoring Interval:** `5 minutes`
   - **SSL Expiration Notification:** Enable 7-day and 1-day advance alerts.
4. **Alert Contacts:**
   - Configure Host Kiran Kumar's email and WhatsApp alert webhook.

---

## 2. Application Error Tracking (Sentry Integration)

The application is structured to support zero-friction Sentry initialization for automated exception tracking and real-time alerts.

### Backend (Flask):
1. Create a project in [Sentry.io](https://sentry.io/) with platform `Python / Flask`.
2. Install sentry SDK (already compatible with requirements):
   ```bash
   pip install sentry-sdk[flask]
   ```
3. Set the environment variable in Render Dashboard:
   ```env
   SENTRY_DSN=https://<public_key>@o<org_id>.ingest.sentry.io/<project_id>
   ```
4. Initialization in `backend/app/__init__.py`:
   ```python
   import sentry_sdk
   from sentry_sdk.integrations.flask import FlaskIntegration

   sentry_dsn = os.getenv("SENTRY_DSN")
   if sentry_dsn:
       sentry_sdk.init(
           dsn=sentry_dsn,
           integrations=[FlaskIntegration()],
           traces_sample_rate=0.1,
           send_default_pii=False,  # Enforces PII protection
       )
   ```

### Frontend (React + Vite):
1. In Sentry, create a project with platform `React`.
2. Set in Vercel environment variables:
   ```env
   VITE_SENTRY_DSN=https://<public_key>@o<org_id>.ingest.sentry.io/<project_id>
   ```
3. Sentry automatically captures unhandled exceptions with source map stack traces.

---

## 3. PII-Scrubbed Structured Logging

All application logs pass through `PIIScrubbingFilter` (`backend/app/utils/logging_utils.py`):
- **Phone Numbers:** 10-digit Indian phone numbers (e.g. `9876543210`) are automatically masked as `****3210`.
- **Emails:** Redacted to `[REDACTED_EMAIL]`.
- **Card Numbers & Payment Secrets:** Redacted to `[REDACTED_CARD]` and `rzp_***_REDACTED`.
- **Traceability:** Every incoming request receives an `X-Request-Id` (8-character UUID) logged across handlers and returned in the HTTP response headers for end-to-end tracing without storing user identity.

---

## 4. Production Backup & Recovery Runbook

1. **Automated Daily Atlas Backups:**
   - Verify backup retention in Atlas under **Backup** $\rightarrow$ **Snapshots**.
2. **On-Demand Manual Snapshot Before Deployments:**
   - Run the audited backup drill script:
     ```powershell
     python backend/scripts/db_backup_restore.py backup joybox_party_room
     ```
3. **Disaster Recovery (Restore to Scratch or Replacement Cluster):**
   ```powershell
   python backend/scripts/db_backup_restore.py restore backups/<timestamp_dir> joybox_party_room_recovery
   ```
