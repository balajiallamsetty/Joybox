# KNOWN ISSUES — Joybox Party Room
**Tracked Issues, Audit Findings, and Technical Debt**
*Consolidated Record for Post-Build Hardening Pass (Phase 9)*

---

## 1. Issue Log

| ID | Title | Severity | Location | Description & How to Reproduce | Suggested Fix | Status |
|---|---|---|---|---|---|---|
| `ISS-001` | Turnaround Buffer Crosses Venue Closing Time | Low | `backend/app/services/booking_service.py` | Bookings ending at 22:00 IST require a 30-minute sanitization buffer ending at 22:30 IST. While guests leave by 22:00, host buffer extends 30 minutes past nominal venue operating hours. *Repro:* Quote a booking for 20:00 to 22:00 IST; observe buffer slot claim extends to 22:30 IST. | Documented as UNCONFIRMED default in `docs/BUSINESS_RULES_REQUIRED.md`. Confirm with Kiran Kumar if a 21:30 hard cutoff for guest departure is preferred. | Tracked |
| `ISS-002` | Hotlinked Google AIDA Public Images | Medium | `frontend/src/` & `galleryAssets` seeds | Hero and decorative images use Google CDN URLs (`lh3.googleusercontent.com/aida-public/...`) exported from Stitch that may expire or have external caching latency. *Repro:* Inspect network waterfall on `LandingPage.jsx`. | Migrate static assets to Cloudinary or AWS S3 bucket under Joybox domain and update asset URLs in `galleryAssets` collection. | Open (Phase 9) |
| `ISS-003` | Admin UI Development Auth Fallback Token | Medium | `frontend/src/pages/AdminPage.jsx` | Admin UI supports session authentication via HttpOnly cookies and bearer tokens, but on hard reload in local dev without cookie forwarding, state resets. *Repro:* Log in via admin console, clear session cookies, and reload without token in localStorage. | Implement a persistent session check endpoint (`GET /api/admin/auth/me`) on frontend app mount with automatic silent refresh. | Open (Phase 9) |
| `ISS-004` | DNS SRV Lookup Latency in Restricted Sandboxes | Low | `backend/app/extensions.py` | Under certain local Windows sandbox configurations or DNS proxies, `mongodb+srv://` lookups may fail or take >5s unless direct host seeds are used or network bypass is permitted. *Repro:* Run Python script without network DNS permission. | Maintain standardized fallback configuration or direct host seed documentation in `.env.example`. | Handled in docs |
| `ISS-005` | Automated WhatsApp/SMS Notification Dispatch | Low | `backend/app/services/booking_service.py` | Booking confirmation currently generates a direct `wa.me` click-to-chat link with pre-filled template for instant WhatsApp messaging. Automated direct API notification (e.g., Gupshup/Twilio/Meta Cloud API) is deferred. *Repro:* Create booking; observe `confirmationPayload.whatsappLink` returned. | Integrate official WhatsApp Cloud API or SMS webhook worker triggered upon `booking.confirmed` event. | Deferred (Post-Launch) |
| `ISS-006` | Payment Sweep Reconciliation Window | Low | `backend/app/jobs/run_sweeps.py:75` | Reconciliation sweep targets pending payments older than `RECONCILIATION_AGE_MINUTES=30`. Payments between 15m hold expiration and 30m sweep rely on customer verification or webhook. *Repro:* Initiate Razorpay payment modal, let hold expire at 15m, and run sweep before 30m. | Parameterize reconciliation window to synchronize with `HOLD_DURATION_MINUTES` + 5m grace period. | Open (Phase 9) |
| `ISS-007` | Gallery and FAQ Fallback to Seed Data in Frontend | Low | `frontend/src/pages/GalleryPage.jsx`, `FaqSection.jsx` | If the backend API is unreachable or returns an empty array, frontend components gracefully fall back to local seed data to avoid rendering blank screens. *Repro:* Disconnect backend API and navigate to `/gallery`. | Add explicit offline/maintenance banner when fallback mode is active. | Open (Phase 9) |
| `ISS-008` | Rate Limiter In-Memory Fallback Under Standalone Workers | Low | `backend/app/utils/rate_limit.py` | Rate limiting uses MongoDB collection `rateLimits`. If MongoDB is temporarily unreachable during a burst, rate limiting fails open rather than blocking legitimate requests. *Repro:* Terminate DB connection and flood endpoint with requests. | Add local in-memory leaky-bucket fallback during transient database outages. | Open (Phase 9) |
| `ISS-009` | Unconfirmed Business Policies Awaiting Owner Sign-Off | Medium | `docs/BUSINESS_RULES_REQUIRED.md` | Cancellation and refund percentages (>48h 100%, 24-48h 50%, <24h 0%) and security deposit amounts remain UNCONFIRMED defaults. *Repro:* Review `docs/BUSINESS_RULES_REQUIRED.md`. | Review and confirm policies with Kiran Kumar prior to public launch. | Open (Go-Live Gate) |
| `ISS-010` | Customer Phone Masking Consistency | Low | `backend/app/routes/public_routes.py` | Minimal booking lookup returns `customerPhoneMasked` (`+91 78427 •••••`), whereas tokenized lookup returns full phone number for customer verification. *Repro:* Query `/api/bookings/<ref>` with and without query token. | Working as designed for privacy; verify if email masking should also be added if customer emails are collected. | Closed / Verified |
| `ISS-011` | Razorpay Webhook Event Deduplication Garbage Collection | Low | `backend/app/repositories/mongo_repos.py:WebhookEventRepository` | `webhookEvents` collection prevents duplicate processing using unique `(provider, eventId)`. Old events currently do not have a TTL index. *Repro:* Inspect `webhookEvents` collection over 6 months of operation. | Add a 90-day TTL index on `webhookEvents.createdAt` in `init_indexes.py`. | Open (Phase 9) |

---

## 2. Consolidated Hardening Backlog

1. **Security & Session Hardening:**
   - Add CSRF token validation header (`X-CSRF-Token`) for all state-modifying admin cookie requests (`POST`, `PUT`, `DELETE`).
   - Implement IP-based brute-force progressive delay on `/api/admin/auth/login`.
   - Add 90-day TTL index on `webhookEvents` and `idempotencyKeys` collections.

2. **Concurrency & Edge Cases:**
   - Synchronize `RECONCILIATION_AGE_MINUTES` with `HOLD_DURATION_MINUTES + 5` so pending payments on expired holds are reconciled faster.
   - Verify zero-second overlap boundary on multi-hour slot claims under high parallel load.

3. **Performance & Asset Delivery:**
   - Migrate hotlinked Stitch Google CDN images to a dedicated Cloudinary or AWS S3 account with WebP compression.
   - Add Redis cache layer for `GET /api/packages`, `GET /api/add-ons`, and `GET /api/offers/active` to reduce Atlas read operations under heavy ad campaign traffic.

4. **Monitoring & Alerting:**
   - Integrate Sentry or Datadog for unhandled backend exceptions and 500 error alerts.
   - Configure Render webhook alert to notify administrator via WhatsApp/email on job sweep failures.

---

## 3. Proposed Phase 9: Hardening Plan

- **Sprint 1 (Security Pass):**
  - Implement CSRF tokens for admin endpoints.
  - Add progressive rate-limiting on login.
  - Add TTL indexes to `webhookEvents` and `idempotencyKeys`.
- **Sprint 2 (Media & Performance):**
  - Host all gallery and hero imagery on private CDN/Cloudinary.
  - Implement Redis caching for read-heavy catalogue endpoints.
- **Sprint 3 (Owner Sign-Off & Launch):**
  - Review `docs/BUSINESS_RULES_REQUIRED.md` with Kiran Kumar.
  - Switch Razorpay keys from test (`rzp_test_...`) to live (`rzp_live_...`).
  - Perform live zero-rupee or Rs. 1 test transaction on production URL.
