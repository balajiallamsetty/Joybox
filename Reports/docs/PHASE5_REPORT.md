# Phase 5 Deployment Readiness & Operational Verification Report

**Joybox Party Room Platform**  
**Role:** Principal Engineer, Application-Security Auditor & QA Lead  
**Branch:** `audit/production-hardening-and-verification`  
**Execution Date:** 2026-11-05  
**Target Test Database:** `joybox_party_room_test` (MongoDB Atlas)  
**Status:** **PHASE 5 COMPLETE — 100% PASS**

---

## 1. Executive Summary

Phase 5 verified the production deployment configuration, cloud infrastructure topologies, environment parity, health-check instrumentation, disaster recovery procedures, and operational runbooks for Joybox Party Room.

The platform topology consists of:
- **Frontend:** React + Vite Single Page Application hosted on **Vercel** with global CDN edge caching, SPA routing fallbacks, and strict Content Security Policy (CSP) headers.
- **Backend Web Service:** Python 3.11 Flask REST API hosted on **Render** (Starter Plan) behind Gunicorn with 3 worker processes, 2 threads per worker, and 120-second timeout.
- **Automated Sweeps Cron:** Scheduled background task hosted on **Render Cron** running `python -m app.jobs.run_sweeps` every 10 minutes (`*/10 * * * *`) to release expired holds, restore promo quotas, and reconcile pending payment states.
- **Database:** **MongoDB Atlas** M0/Dedicated multi-region replica set with atomic unique compound indexes on `slotClaims` and automated backup tooling.

---

## 2. Infrastructure & Service Verification

| Service / Asset | Configuration Path | Verified Invariants | Status |
|---|---|---|---|
| **Render Web Service** | [`render.yaml`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/render.yaml) & [`backend/Procfile`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/Procfile) | Gunicorn 3 workers, 2 threads; `/api/health` healthCheckPath; 120s timeout; production env variables | **PASS** |
| **Render Sweep Cron** | [`render.yaml`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/render.yaml) | 10-minute cron schedule `*/10 * * * *`; idempotent sweeps execution; holds release & promo restore | **PASS** |
| **Vercel Frontend** | [`frontend/vercel.json`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/frontend/vercel.json) | SPA rewrite rule `/(.*) -> /index.html`; security headers (nosniff, SAMEORIGIN, strict-origin, strict CSP) | **PASS** |
| **MongoDB Atlas** | Client-owned Atlas replica set | Production DB `joybox_party_room` guarded; test DB name must end in `_test`; unique compound index on slotClaims | **PASS** |
| **Database Backup CLI** | [`backend/scripts/db_backup.py`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/scripts/db_backup.py) | Full JSON BSON serialization; dry-run & automated restore drills; 30-day retention pruning | **PASS** |
| **Health Check API** | `GET /api/health` & `GET /health` | Fast-fail health probe returning `{ status: "ok", timestamp: ... }` with DB ping | **PASS** |

---

## 3. Environment Variable Parity Table

| Variable Name | Render (Web) | Render (Cron) | Vercel (Frontend) | Local `.env` | Purpose & Security Classification |
|---|---|---|---|---|---|
| `FLASK_ENV` | `production` | `production` | — | `development` / `testing` | Enforces production fast-fail startup guards |
| `MONGODB_URI` | Secret | Secret | — | Secret | MongoDB Atlas connection string |
| `MONGODB_DB` | `joybox_party_room` | `joybox_party_room` | — | `joybox_party_room_test` | Target database name (`_test` enforced in dev) |
| `JWT_SECRET_KEY` | Auto-Generated Secret | — | — | Secret | Admin session signing key |
| `RAZORPAY_KEY_ID` | Secret | Secret | Public (`VITE_RAZORPAY_KEY_ID`) | Secret | Razorpay client key ID |
| `RAZORPAY_KEY_SECRET` | Secret | Secret | — | Secret | Razorpay payment verification secret |
| `RAZORPAY_WEBHOOK_SECRET`| Secret | — | — | Secret | HMAC signature verification for Razorpay webhooks |
| `FRONTEND_ORIGIN` | `https://<domain>` | — | — | `http://localhost:5173,http://127.0.0.1:5173` | Strict CORS allow-list |
| `ADMIN_COOKIE_SECURE` | `true` | — | — | `false` | Enforces HTTPS-only cookies in production |
| `ADMIN_COOKIE_SAMESITE` | `Lax` | — | — | `Lax` | Cross-site request cookie policy |
| `VITE_API_BASE_URL` | — | — | `https://<backend>.onrender.com/api` | `http://127.0.0.1:5000/api` | Client REST API base URL |
| `VITE_WHATSAPP_NUMBER` | — | — | `917842704429` | `917842704429` | Venue contact WhatsApp number |
| `VITE_HOST_NAME` | — | — | `Kiran Kumar` | `Kiran Kumar` | Venue host display name |

---

## 4. Disaster Recovery & Rollback Runbook

### 4.1 Frontend Rollback (Vercel)
1. **Instant Rollback via CLI:**
   ```bash
   vercel rollback
   ```
2. **Instant Rollback via Dashboard:**
   - Navigate to Vercel Project Dashboard -> **Deployments**.
   - Select the previous stable deployment and click **Promote to Production**.
   - Zero downtime cutover in < 5 seconds.

### 4.2 Backend Rollback (Render)
1. **Rollback via Git Commit:**
   ```bash
   git revert HEAD
   git push origin main
   ```
2. **Rollback via Render Dashboard:**
   - Open Render Service -> **Deploys**.
   - Locate the previous successful deploy and select **Rollback to this deploy**.
   - Zero-downtime blue/green deployment ensures old instances continue serving traffic until new workers report healthy.

### 4.3 Database Backup & Restore Procedure
- **Automated Backup Command:**
  ```bash
  python backend/scripts/db_backup.py --backup --db joybox_party_room --allow-production --confirm-production joybox_party_room
  ```
- **Restore Drill into Test Database:**
  ```bash
  python backend/scripts/db_backup.py --restore-drill --backup-dir backups/<timestamp> --target-db joybox_party_room_test
  ```

---

## 5. Owner Actions & Open Business Decisions

Detailed, step-by-step owner actions are maintained in [`docs/OWNER_TASKS.md`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/docs/OWNER_TASKS.md) and [`docs/OWNER_ACTIONS.md`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/docs/OWNER_ACTIONS.md):
1. **IP Allow-listing:** Configure Atlas Network Access to allow Render web service and cron IPs (or `0.0.0.0/0` with strong, rotated credentials).
2. **Domain Registration:** Map custom domain (e.g. `joyboxparty.in`) in Vercel DNS and update `FRONTEND_ORIGIN` in Render.
3. **Live Razorpay Credentials & Webhook:** Replace test credentials with live keys (`rzp_live_...`) and register the Render webhook endpoint.
4. **Credential Rotation:** Complete the ordered secret rotation runbook outlined in `docs/OWNER_TASKS.md`.
5. **Business Decision Sign-offs:**
   - Hold checkout TTL (15 minutes recommended).
   - Cancellation refund schedule.
   - Canonical landing page (`/`).
   - GST invoicing applicability.
   - Data retention timeline.

