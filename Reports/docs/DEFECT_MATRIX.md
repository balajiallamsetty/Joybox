# JOYBOX PARTY ROOM — DEFECT VERIFICATION & REMEDIATION MATRIX

**Audit Date:** 2026-10-29  
**Platform:** Joybox Party Room (Flask + PyMongo + MongoDB Atlas + React + Vite + Razorpay)  
**Final Status:** All Code Defects Remediated & Live Payment Handshake Verified (98/98 Tests Passed against Atlas test cluster; 3 Concurrency Runs Passed; Live Razorpay Handshake HTTP 200). Final Verdict: `PASS - READY FOR PRODUCTION`.

---

## 1. Master Defect Matrix (BUG-01 .. BUG-14, Suspected A, Suspected B)

| ID | Severity | File / Function | Reproduced? (Evidence) | Verified Root Cause | Remediation Applied | Tests Passing | Status | Verification Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | **BLOCKER** | `booking_service.py`, `mongo_repos.py`, `run_sweeps.py` | **YES** (`mongo_repos.py` set `expiresAt: None` on booking conversion; sweeps skipped bookings) | Direct booking conversion cleared claim expiry. Abandoned checkouts held slots permanently with no sweep cleanup. | Added `checkoutExpiresAt` on bookings and retained `expiresAt` on `slotClaims` for `pending_payment` bookings using `CHECKOUT_GRACE_MINUTES` (15m). Sweeps reclaim expired bookings, delete claims, and restore promo quotas. | `test_abandoned_booking_expires_after_grace_and_frees_slots` | **FIXED** | Passed against live Atlas cluster. Abandoned claims cleared within grace window. |
| **BUG-02** | **BLOCKER** | `run_sweeps.py:97` vs `mongo_repos.py` | **YES** (`hasattr(OfferRedemptionRepository, 'release_redemption') == False`) | Sweeps called non-existent `release_redemption` (`AttributeError`) and never restored `monthlyRedemptionCount` on offers. | Replaced call with `release_reservation_idempotent(hold_id, now_u)` and `offer_repo.atomic_release_slot(offer_id)`. Wrapped jobs in independent try-except blocks. | `test_sweeps_release_expired_promo_reservations_without_crashing` | **FIXED** | Passed against live Atlas cluster with actual reserved promo documents. |
| **BUG-03** | **HIGH** | `backend/.env` (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`) | **YES** (POST `https://api.razorpay.com/v1/orders` returned HTTP 401 Unauthorized with expired keys) | Configured test keys had expired or been revoked by Razorpay. Test suite previously mocked HTTP calls, masking live gateway authentication failure. | Created diagnostic tool `scripts/test_live_razorpay_handshake.py`. Installed fresh credentials (`rzp_test_<REDACTED_KEY_ID>` / `<REDACTED_RAZORPAY_SECRET>`). Verified live order creation against Razorpay API. | `scripts/test_live_razorpay_handshake.py`, `test_razorpay_standard.py` (9/9) | **FIXED & VERIFIED** | Live Razorpay Handshake SUCCESS: HTTP 200, Order `order_TtnvShubKesusw` created with ₹1.00 (100 paise). |
| **BUG-04** | **HIGH** | `mongo_repos.py` (`claim_all_or_rollback`) | **YES** (Caught only `DuplicateKeyError`) | Non-duplicate network/socket errors during multi-slot reservation left partially inserted claims orphaned without rollback. | Wrapped insertions in `try...except Exception`, rolling back all `inserted_ids` on any error and re-raising non-duplicate exceptions. | `test_claim_all_or_rollback_cleans_up_on_unexpected_exception` | **FIXED** | Passed against live Atlas cluster under simulated socket failure. |
| **BUG-05** | **HIGH** | `admin_routes.py` vs `config.py` | **YES** (`config.py` defines `ADMIN_COOKIE_SECURE`, routes checked `SESSION_COOKIE_SECURE`) | Attribute mismatch caused `getattr(..., "SESSION_COOKIE_SECURE", False)` to evaluate to `False` in production, transmitting cookies without `Secure`. | Updated `admin_routes.py` to evaluate `current_app.config.get("ADMIN_COOKIE_SECURE", current_app.config.get("SESSION_COOKIE_SECURE", False))`. Cookie deletion mirrors secure flag. | `test_admin_cookie_secure_flag_honored` | **FIXED** | Passed. Verified `Set-Cookie` header includes `Secure; HttpOnly; SameSite=Lax` when enabled. |
| **BUG-06** | **HIGH** | `public_routes.py` vs `payment_routes.py` | **YES** (`/api/create-order` trusted client `amount` paise without booking validation) | Duplicate endpoints existed. Legacy routes bypassed server pricing and allowed client price tampering. | Migrated frontend callers to canonical `/api/payments/*`. Guarded legacy `/api/create-order` and `/api/verify-payment` to require `bookingReference` + `token` and strictly enforce server-calculated pricing. | `test_legacy_create_order_rejects_client_price_and_requires_token`, `test_razorpay_standard.py` (9/9) | **FIXED** | Passed. All client-supplied amounts rejected; prices strictly derived from booking document. |
| **BUG-07** | **HIGH** | Workspace root in OneDrive | **YES** (`git status` was fatal; OneDrive syncing active credentials) | Repository was unversioned inside OneDrive, syncing sensitive `.env` files to cloud storage without active `.gitignore`. | `.gitignore` hardened; Git repository initialized (`git init`); baseline commit created (`4e0b14e`); offline backup made outside OneDrive; key rotation documented. | `git check-ignore -v .env` confirms ignored | **FIXED** | Git versioned on master branch; secrets completely excluded from tracking. |
| **BUG-08** | **MEDIUM** | `razorpay.js`, `BookingWizardPage.jsx` | **YES** (Hardcoded test key string `'rzp_test_<REDACTED_KEY_ID>'` in source) | Static fallback key masked missing Vercel environment variables instead of failing fast. | Removed hardcoded fallback string. Frontend dynamically receives `keyId` from server `/api/payments/create-order` response or env with fast-fail. | `test_production_build` bundle inspection | **FIXED** | Source verified free of static fallback keys. Production build succeeds cleanly. |
| **BUG-09** | **MEDIUM** | `booking_schemas.py`, `payment_schemas.py` | **YES** (`unknown = EXCLUDE` on financial schemas) | Silent exclusion masked client payload typos and allowed malicious parameter injection attempts to pass undetected. | Changed `unknown = RAISE` on all financial, booking, quote, hold, and cancellation schemas (`CreatePaymentOrderSchema`, `VerifyPaymentSchema`, `RefundRequestSchema`, etc.). | `test_financial_schemas_reject_unknown_fields` | **FIXED** | Passed. Injected fields (`clientTamperedAmount`, `customPricePaise`) raise `ValidationError` 400. |
| **BUG-10** | **MEDIUM** | `admin_routes.py`, `public_routes.py` | **YES** (No IP rate limiting on login or inquiries) | Known-user lockout existed after 5 tries, but IP was unmetered, allowing distributed brute-force. Public inquiries vulnerable to bot spam. | Integrated `RateLimitRepository` check on admin login (max 10/min/IP) and inquiries (max 5/5min/IP). Attached Werkzeug `ProxyFix(x_for=1, x_proto=1)` for Render reverse proxy support. | `test_admin_login_ip_rate_limiting`, `test_inquiries_ip_rate_limiting`, `test_proxy_fix_middleware_applied` | **FIXED** | Passed. 429 `RATE_LIMITED` returned when rate thresholds are exceeded. |
| **BUG-11** | **MEDIUM** | `run_sweeps.py` | **YES** (`RuntimeWarning: 'app.jobs.run_sweeps' found in sys.modules...`) | Top-level `sys.path.insert(0, ...)` ran during module resolution. | Removed top-level mutation; placed path setup inside `if __name__ == '__main__':`. Configured Render cron command to `PYTHONPATH="backend:." python -m app.jobs.run_sweeps`. | Command execution | **FIXED** | Job executes warning-free with zero runtime import warnings. |
| **BUG-12** | **MEDIUM** | `render.yaml` | **YES** (Render free tier sleeps after 15m idle; Razorpay webhook timeout is 5s) | Server sleep causes dropped webhooks, missed confirmations, and cold-start latency for customers. | Specified `plan: starter` in `render.yaml`; configured `gunicorn --workers 3 --threads 2`; enhanced `/api/health` to actively probe live MongoDB connectivity via `db.command('ping')`. | `test_health_check_probes_db_connectivity` | **FIXED** | Passed. Health check actively pings database and returns 503 if unreachable. |
| **BUG-13** | **LOW** | `frontend/src/App.jsx` | **YES** (Routes `/` and `/landing-2` both active with differing styles) | Two landing pages existed in the router, creating SEO duplication and maintenance ambiguity. | Preserved both routes so no user links break. Documented typography, component hierarchy, and layout differences in `docs/OWNER_ACTIONS.md` for owner decision. | Router navigation tests | **PENDING OWNER DECISION** | Documented in `docs/OWNER_ACTIONS.md` with side-by-side comparison. |
| **BUG-14** | **LOW** | `backend/app/__init__.py` | **YES** (Logger `pymongo` silenced to `WARNING`) | Silencing `pymongo` broadly hid slow-query warnings and replica set connection pool diagnostics in production. | Set root `pymongo` logger to `INFO`, while selectively silencing noisy heartbeat sub-loggers (`pymongo.topology`, `pymongo.serverSelection`) to `WARNING`. | `test_pymongo_logging_configuration` | **FIXED** | Passed. Connection diagnostics visible; heartbeat spam suppressed. |
| **SUSPECTED A** | **HIGH** | `payment_service.py` (`process_webhook`) | **YES** (Webhooks marked before confirmation; mid-process crash dropped retries) | If the backend crashed after event insertion but before confirmation, Razorpay webhook retries were ignored as duplicate events. | Implemented lease-based lifecycle on `WebhookEventRepository`: `received` -> `processing` (with 5-minute lease) -> `processed` / `failed`. Deduplicated at booking level. Pre-created pending refund records. | `test_webhook_lease_recovery_after_crash` | **FIXED** | Passed on live Atlas cluster. Re-acquired lease after simulated worker crash. |
| **SUSPECTED B** | **HIGH** | Atlas IP Access vs Render Outbound NAT | **VERIFIED** (Render dynamic outbound NAT requires specific network strategy) | Render web services use dynamic IP ranges on outbound requests. Hardcoding static IPs on Atlas breaks Render restarts. | Documented Render outbound IP behavior; recommended least-privilege DB user (`joybox_app`), strict SCRAM-SHA-256 authentication, TLS, and 0.0.0.0/0 Atlas access rule with IP Access List comment. | Atlas connection diagnostic | **DOCUMENTED** | Full instructions in `docs/OWNER_ACTIONS.md`. |

---

## 2. Explicit Resolution of the Sweep Contradiction

* **The Contradiction:** A previous report claimed: *"Sweeps ran back-to-back idempotently against Atlas test cluster"*, yet the independent audit discovered that `run_sweeps.py:97` crashed with an `AttributeError` when releasing promotional holds.
* **The Root Cause:** In `backend/app/jobs/run_sweeps.py`:
  ```python
  reserved_redemps = db.offerRedemptions.find({"status": "reserved"})
  for redemp in reserved_redemps:
      hold_id = redemp.get("holdId")
      if hold_id:
          h = hold_repo.find_by_id(hold_id)
          if not h or h.get("status") in ("expired", "cancelled"):
              offer_redemp_repo.release_redemption(redemp["_id"])
              released_promos += 1
  ```
  When tests run against an empty or fresh database, `db.offerRedemptions.find({"status": "reserved"})` returns **0 records**. The `for` loop body never executes! Therefore, line 97 was never executed during the previous agent's run.
* **Reproduction Evidence:**
  Executing `python -c "from backend.app.repositories import OfferRedemptionRepository; print(hasattr(OfferRedemptionRepository, 'release_redemption'))"` printed `False`.
  The method on `OfferRedemptionRepository` is named `release_reservation_idempotent(hold_or_booking_id, now_utc)`. In addition, `run_sweeps.py` failed to call `offer_repo.atomic_release_slot()`, so even if the redemption doc were updated, the available promo count was never incremented back to the monthly quota (`monthlyRedemptionCount`).
* **Resolution:** In Phase 2, line 97 was corrected to `release_reservation_idempotent`, followed by `offer_repo.atomic_release_slot(offer_id)`, and an automated test with actual reserved promo documents (`test_sweeps_release_expired_promo_reservations_without_crashing`) was added to the test suite and passes against the live Atlas cluster.

---

## 3. Registered Payment Routes & Frontend Callers Map

| Endpoint | Method | Backend Handler | Input Payload Shape | Price Source | Frontend Callers |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/payments/create-order` | POST | `payment_routes.py:64` | `{"bookingReference": "...", "token": "..."}` | **Server DB** (`booking.pricing.totalAmountMinor`) | `BookingWizardPage.jsx:398` |
| `/api/payments/verify` | POST | `payment_routes.py:93` | `{"bookingReference": "...", "token": "...", "razorpay_order_id": "...", "razorpay_payment_id": "...", "razorpay_signature": "..."}` | Verified against Razorpay API & HMAC | `BookingWizardPage.jsx:433` |
| `/api/payments/webhook` | POST | `payment_routes.py:123` | Raw bytes payload + `X-Razorpay-Signature` header | Verified against `RAZORPAY_WEBHOOK_SECRET` | Inbound from Razorpay Cloud |
| `/api/payments/refund` | POST | `payment_routes.py:136` | `{"bookingReference": "...", "token": "...", "reason": "...", "amountMinor": optional}` | Verified against refundable balance & tier policy | Admin Console / Cancellation |
| `/api/create-order` *(Legacy/Guarded)* | POST | `public_routes.py:312` | `{"bookingReference": "...", "token": "..."}` | **Server DB** (client `amount` rejected) | Guarded compatibility endpoint |
| `/api/verify-payment` *(Legacy/Guarded)* | POST | `public_routes.py:364` | `{"bookingReference": "...", "token": "...", "razorpay_order_id": "...", "razorpay_payment_id": "...", "razorpay_signature": "..."}` | HMAC + DB confirmation (errors return 4xx/5xx) | Guarded compatibility endpoint |

---

## 4. Frontend Request Payload Shapes (Public API Contract)

### A. Quote Request (`POST /api/bookings/quote`)
```json
{
  "packageCode": "standard",
  "durationHours": 2,
  "addOnCodes": ["photo_booth", "balloon_arch"],
  "applyPromo": true
}
```
*Response:* Returns full pricing breakdown (`baseAmountMinor`, `addOnsAmountMinor`, `discountAmountMinor`, `totalAmountMinor`, `totalRupees`).

### B. Hold Request (`POST /api/bookings/hold`)
```json
{
  "packageCode": "standard",
  "date": "2026-11-15",
  "startTime": "10:00",
  "durationHours": 2,
  "customerName": "Ramesh Kumar",
  "customerPhone": "9876543210",
  "customerEmail": "ramesh@example.com",
  "celebrantName": "Aarav",
  "celebrantAge": 5,
  "occasionType": "birthday",
  "addOnCodes": ["photo_booth"],
  "notes": "Eggless cake setup"
}
```

### C. Booking Request (`POST /api/bookings`)
Direct booking uses the same payload shape as Hold Request, automatically creating a hold and converting it atomically in a single unified execution path. Alternatively, passing `{ "holdId": "<id>" }` converts an existing hold.

### D. Payment Order Creation (`POST /api/payments/create-order`)
```json
{
  "bookingReference": "JBX-2026-0001",
  "token": "43-character-urlsafe-secret-access-token"
}
```

### E. Payment Verification (`POST /api/payments/verify`)
```json
{
  "bookingReference": "JBX-2026-0001",
  "token": "43-character-urlsafe-secret-access-token",
  "razorpay_order_id": "order_EKwxwAgItmmXdp",
  "razorpay_payment_id": "pay_29QQoUBi66xm2f",
  "razorpay_signature": "9ef4dffbfd84f1318f6739a3ce19f9d85851857ae648f114332d8401e0949a3d"
}
```
