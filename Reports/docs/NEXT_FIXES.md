# Next Fixes (Joybox Party Room)
Date: 2026-10-30 · Branch: `fix/booking-date-and-package` · Last commit: `f9776c3`

## Status Snapshot
- Overall verdict: **Blocked** until Razorpay test access and the failing backend/Atlas suite are resolved.
- Backend: `99 passed, 25 failed` in the full run; payment contracts alone: `27 passed`.
- Frontend: production build passes; no lint script is configured.
- Secret scan: no live-key/private-key matches in the built bundle; credential-like values exist in tracked history/docs and need review.
- Still unverified: live Razorpay handshake, deployed Atlas indexes/data, Render/Vercel settings, webhook delivery, and production monitoring.

## 1. Razorpay and Payments
- [ ] P0 · M · Make the Razorpay test handshake pass (where: `scripts/test_live_razorpay_handshake.py`, `docs/STABILIZATION_LOG.md:18`) - the prior audit records HTTP 401, while other docs claim success, so checkout readiness is contradictory and unproven.
  Fix: regenerate/verify test credentials in the dashboard and rerun the 100-paise handshake without exposing values.
- [ ] P0 · M · Correct `order.paid` webhook parsing (where: `backend/app/services/payment_service.py:581-598`) - both `payment.captured` and `order.paid` read `payload.payment.entity`, but Razorpay `order.paid` carries an order entity, so that event may not confirm the booking.
  Fix: parse each subscribed event shape and add a real payload test for `order.paid`.
- [ ] P1 · M · Remove duplicate payment entry points (where: `backend/app/routes/public_routes.py:325-424`, `backend/app/routes/payment_routes.py:64-160`) - legacy public order/verify routes coexist with canonical `/api/payments/*` routes.
  Fix: select one canonical flow, redirect or deprecate aliases, and test every frontend caller against it.
- [ ] P1 · S · Remove the fake payment key fallback (where: `backend/app/services/payment_service.py:329`) - a missing configured key returns a hard-coded test public-key fallback, causing a misleading checkout response instead of a configuration error.
  Fix: fail closed with an explicit server error when `RAZORPAY_KEY_ID` is absent or invalid.
- [ ] P1 · M · Add abuse controls to payment endpoints (where: `backend/app/routes/payment_routes.py:64-160`) - order, verify, webhook, and refund routes have no route-level rate limiting.
  Fix: add bounded limits and preserve provider/webhook retry semantics.
- [ ] P1 · M · Prove provider-side failure and recovery paths (where: `backend/app/services/payment_service.py:546-659`, `backend/tests/test_payments_and_security_hardening.py`) - webhook lease recovery is a failing test and real gateway behavior is not verified.
  Fix: repair the lease/retry path and run captured, failed, cancelled, browser-closed, late-payment, duplicate-event, and refund cases against Razorpay test mode.
- [ ] P1 · S · Stop sending unnecessary customer PII in order notes (where: `backend/app/services/payment_service.py:280-306`) - customer name and phone are included in the provider order payload.
  Fix: retain only the booking reference or document the minimum provider-required metadata and retention.

## 2. Booking and Logic
- [ ] P1 · M · Restore a seeded, isolated integration-test database (where: `backend/tests/conftest.py`, full pytest output) - quote and booking tests return “Package not found or inactive”; 25 tests fail, including date and concurrency coverage.
  Fix: seed `joybox_audit_test` in a controlled setup step and assert required catalog fixtures before tests.
- [ ] P1 · M · Re-run and explain Atlas concurrency failures (where: `backend/tests/test_real_atlas.py`) - all 3 repetitions fail 4/4 at the same test-data/contract boundary instead of proving contention behavior.
  Fix: make the tests self-contained, clean up their test records, and require three consecutive green runs.
- [ ] P1 · S · Make pytest invocation consistent (where: `backend/tests/conftest.py`, repository root) - `pytest -q` fails collection with `ModuleNotFoundError: app`, while another invocation fails on `backend` imports.
  Fix: document one supported command or package the test imports so root and CI execution agree.
- [ ] P1 · M · Reconcile application indexes and validators (where: `backend/scripts/init_indexes.py`, `database/indexes.js`, `database/validators.js`) - starter scripts use `status`/`venueId`, while code uses `bookingStatus`/`roomId`, and validators omit live booking states.
  Fix: choose one authoritative migration-safe initializer and validate it against a fresh test database.
- [ ] P1 · M · Make seed and index commands refuse production by default (where: `backend/scripts/seed_*.py`, `backend/scripts/init_indexes.py`) - scripts default to `joybox_party_room` without a test/prod safety confirmation.
  Fix: require an explicit target and refuse production unless an operator flag is supplied.
- [ ] P1 · S · Keep displayed prices sourced from the server (where: `frontend/src/pages/BookingWizardPage.jsx:7-42`, `frontend/src/pages/LandingPage.jsx`) - hard-coded UI prices can disagree with the authoritative quote.
  Fix: render package/add-on prices from catalog responses and show quote errors instead of stale values.

## 3. UI and Frontend
- [ ] P1 · M · Add a browser test for the full booking journey (where: `frontend/package.json`, `frontend/src/pages/BookingWizardPage.jsx`) - no frontend test script or browser test proves date change, package preselect, booking, Checkout, and payment-result recovery.
  Fix: add a test-only journey with mocked API/provider boundaries and one manually verified Razorpay test-mode run.
- [ ] P2 · S · Add an explicit lint check (where: `frontend/package.json`) - only `dev`, `build`, and `preview` scripts exist.
  Fix: add the repository-approved lint command and run it in CI.
- [ ] P2 · S · Surface catalog load failures (where: `frontend/src/pages/PackagesPage.jsx`) - request failures are converted to empty arrays, which looks like an empty catalog.
  Fix: show loading, error, retry, and genuinely empty states separately.
- [ ] P2 · S · Resolve duplicate landing-page ownership (where: `frontend/src/App.jsx:24-25`) - `/` and `/landing-2` remain separate implementations and create duplicate maintenance/SEO behavior.
  Fix: choose the public route and mark the alternate route intentionally or remove it after owner approval.
- [ ] P2 · S · Add favicon and social metadata (where: `frontend/index.html`) - title/description exist, but no favicon or Open Graph metadata was found.
  Fix: add verified assets and metadata after the canonical landing route is chosen.

## 4. Security
- [ ] P1 · M · Validate client-IP trust at the Render boundary (where: `backend/app/__init__.py:39-40`, `backend/app/routes/public_routes.py:83-86`) - rate limits trust forwarded headers and `ProxyFix` is configured without a deployment-level proof of proxy depth.
  Fix: document the trusted proxy hop and test spoofed `X-Forwarded-For` behavior.
- [ ] P1 · M · Remove credential-like material from tracked docs/history (where: `docs/DEFECT_MATRIX.md:15,116`, `docs/FINAL_REPORT.md:31`, history scan) - scans found key/signature/URI-like strings in committed documentation/history.
  Fix: determine whether each value is placeholder or real, scrub non-placeholder values, and rotate any exposed credential.
- [ ] P2 · S · Add a dependency vulnerability baseline (where: `frontend/package.json`, `backend/requirements.txt`) - `npm audit --omit=dev` is clean, but no repeatable Python CVE audit is configured.
  Fix: add an approved CI vulnerability check without installing packages during this audit.

## 5. Data and Config
- [ ] P1 · S · Reconcile environment templates (where: `backend/app/config.py`, `backend/.env.example`) - example-only names include `ADMIN_COOKIE_SECURE`, `OPENING_HOUR_IST`, and `MONGODB_TEST_URI`; config-only names include `RAZORPAY_API_BASE` and `RECONCILIATION_AGE_MINUTES`.
  Fix: document every consumed variable and remove or wire unused template names.
- [ ] P1 · M · Verify production indexes and catalog seeds before launch (where: `render.yaml`, `backend/scripts/init_indexes.py`, `backend/scripts/seed_all.py`) - source declares the steps, but deployed execution and required package/offer/admin data were not verified.
  Fix: run the guarded release checklist against a non-production clone, then record production verification.
- [ ] P1 · M · Add backup/restore acceptance evidence (where: `backend/scripts/db_backup.py`, `docs/DATABASE_SETUP.md`) - scripts exist, but no current scheduled backup, restore drill, retention, or alert evidence was available.
  Fix: assign an owner and prove a recent restore to a non-production database.

## 6. Deployment and Operations
- [ ] P1 · M · Verify the Render cron and webhook configuration (where: `render.yaml`, `backend/app/jobs/run_sweeps.py`) - the cron is declared, but actual execution, duplicate-run safety, and Razorpay webhook URL were not observable.
  Fix: run two safe sweeps against test data and verify dashboard logs, alerts, and the HTTPS webhook endpoint.
- [ ] P1 · M · Add uptime/error monitoring (where: `backend/app/__init__.py`, `render.yaml`) - health and logging exist, but external uptime checks, exception alerts, and payment/refund alerts were not found.
  Fix: configure non-secret monitoring and alert thresholds before accepting bookings.
- [ ] P2 · S · Confirm frontend production API/HTTPS settings (where: `frontend/.env.example`, `frontend/vercel.json`) - local HTTP origins are allowed in CSP/template defaults and deployed Vercel variables/custom domain were not verified.
  Fix: verify production `VITE_API_BASE_URL`, HTTPS, CORS origin, CSP connect-src, and domain routing.

## 7. Tests and Docs
- [ ] P1 · S · Correct stale readiness claims (where: `docs/BOOKING_FIX_REPORT.md:17`, `docs/DEFECT_MATRIX.md:15`, `docs/PRODUCTION_READINESS.md:10`) - docs claim 100%/live-handshake success while this audit found 25 failures and the prior record says HTTP 401.
  Fix: update status only from reproducible current results and link the exact commands.
- [ ] P1 · M · Separate mocked payment confidence from real-provider confidence (where: `backend/tests/test_payments.py`, `backend/tests/test_razorpay_standard.py`, `scripts/test_live_razorpay_handshake.py`) - 27 payment contract tests pass, but they do not prove live credentials, Checkout, or webhook delivery.
  Fix: keep mock tests and add a gated test-mode acceptance record.
- [ ] P2 · S · Document a clean developer setup (where: `README.md`, `backend/tests/conftest.py`) - the default root pytest command fails import collection and the required seeded test database is not self-evident.
  Fix: document environment names, safe test DB setup, seed/index order, and supported commands.

## 8. Owner Tasks (dashboards, decisions, policies; things code cannot fix)
- [ ] P0 · S · Confirm Razorpay test/live account readiness (where: Razorpay Dashboard) - keys, capture mode, payment methods, webhook secret, webhook URL, and settlement/refund permissions are external settings.
  Fix: record a successful test-mode order, Checkout, captured payment, webhook, and refund before enabling live traffic.
- [ ] P1 · S · Approve refund/cancellation and GST/invoice policy (where: `backend/app/config.py`, `docs/BUSINESS_RULES_REQUIRED.md`) - configured windows and tax behavior require owner/legal approval.
  Fix: publish the approved policy and ensure the UI and gateway receipts match it.
- [ ] P1 · S · Publish customer legal/contact policies (where: frontend routes/pages) - terms, privacy, refund/cancellation, data-retention, and clear contact policy pages were not found.
  Fix: provide approved text, retention period, business identity, and verified WhatsApp/contact details.
- [ ] P1 · S · Confirm Atlas operations (where: MongoDB Atlas Dashboard) - network allow-list, least-privilege user, backups, alerts, and production index state were not accessible.
  Fix: complete and retain an owner-approved production operations checklist.

## Do These First (top 5)
- [ ] P0 · M · Fix and test the `order.paid` webhook payload handling (`backend/app/services/payment_service.py`).
- [ ] P0 · M · Resolve Razorpay test credentials and rerun the live handshake (`scripts/test_live_razorpay_handshake.py`).
- [ ] P0 · S · Confirm Razorpay Dashboard capture/webhook/refund settings (owner task).
- [ ] P1 · M · Seed a disposable `_test` database and make the full backend suite green.
- [ ] P1 · M · Reconcile index/validator/seed scripts before production initialization.

## Unverified / Could Not Check
- No live Razorpay request was made during this audit; the prior HTTP 401 record and contradictory success claims require dashboard access and a controlled test-mode run.
- No production database, Render/Vercel dashboard, Atlas network rules, deployed indexes, webhook deliveries, uptime alerts, or live payment/refund was accessed.
- Full tests were run only with a database name ending `_test`; failures indicate missing/mismatched test fixtures, not a production-data diagnosis.
- Existing pre-audit changes were preserved: `docs/BOOKING_FIX_REPORT.md` is modified and `PROJECT_LOGIC_DOCUMENTATION.md` is untracked.
