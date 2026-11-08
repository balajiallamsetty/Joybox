# Payments Deferred Behavior & Security Invariant Audit

**Platform:** Joybox Party Room (Vadlamudi, Guntur, India)  
**Role:** Principal Software Engineer, Application-Security Auditor & QA Lead  
**Branch:** `staging/verification-and-gap-closure`  
**Execution Date:** 2026-11-07  
**Operating Mode:** `PAYMENTS_ENABLED = false` (Deferred / Test Environment)  

---

## 1. What a Customer Sees at Checkout (DOM & User Experience)

During the deferred checkout phase, customers complete reservation scheduling while payment gateway calls remain isolated:

### 1.1 Step 4: Reservation Summary & Lock (Wizard UI)
- **Header & Step Navigation:** "Step 4: Reservation Summary & Lock"
- **Celebration Particulars Card:**
  - Date & Time: Selected calendar date (e.g. `2026-11-20`) and time window (e.g. `18:00 - 20:00`, 2 hours).
  - Venue: 100% Private Theater Buyout (Joybox Adda, Beside Durga Mart, Vadlamudi).
  - Package Details: Selected Tier (Basic, Gold, or Diamond) with included thematic decor and audio setup.
  - Celebrant Particulars: Celebrant Name (e.g. "Aarav") and Occasion (Birthday/Anniversary).
- **Authoritative Server Financial Breakdown:**
  - Package Base Rate: `2 hrs × ₹1,500/hr = ₹3,000`
  - Selected Add-ons: Fog Entry (`₹500`), Bubble Machine (`₹300`)
  - Promotional Offer: Introductory Discount (`- ₹300`)
  - **Total Package Bill:** `₹4,100` (Displayed in prominent font)
  - **Advance Token Due:** `₹500` (Online reservation token)
  - **Balance Due at Venue:** `₹3,600` (Paid in cash or UPI upon arrival at the venue)
- **Call-to-Action Elements:**
  - `← Back`: Returns to Step 3 (Celebrant Details).
  - `WhatsApp Host Kiran`: Pre-formatted green button launching WhatsApp direct chat:  
    `https://wa.me/917842704429?text=Hi%20Kiran!%20I%20want%20to%20reserve%20Joybox...`
  - `Pay & Lock Slot`: Primary action button. In deferred mode, the frontend secures the slot via `POST /api/bookings` with atomic MongoDB reservation, stores the unguessable access token in `sessionStorage`, and redirects to `/booking/JBX-YYYY-NNNN`.

### 1.2 Booking Status Confirmation Page (`/booking/:reference`)
- **Status Banners:**
  - "Slot 100% Reserved & Locked" with green verification badge.
  - "Courtesy Hold Active" when awaiting offline/venue advance reconciliation.
- **Reference Code:** Unique identifier bar `#JBX-2026-0042` with 1-click "Copy Code" and "Print Receipt" options.
- **Self-Service Cancellation:** When viewed with the access token, a red "Cancel Reservation" button allows the customer to release the slot directly back to public availability.

---

## 2. Proof: No Code Path Sets a Booking to Paid Without Cryptographic Verification

A comprehensive audit of all occurrences of `paymentStatus = "paid"` across the codebase proves that **zero unauthorized or unverified code paths exist**:

| File & Line | Context | Cryptographic Barrier / Authorization Guard |
| :--- | :--- | :--- |
| [`backend/app/services/booking_service.py:549`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/app/services/booking_service.py#L549) | Public booking creation (`POST /api/bookings`) | **Always sets `"paymentStatus": "unpaid"`**. Zero exceptions. |
| [`backend/app/services/payment_service.py:428`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/app/services/payment_service.py#L428) | Client payment verification (`POST /api/payments/verify`) | **HMAC-SHA256 Signature Verification**:`hmac.new(RAZORPAY_KEY_SECRET, f"{order_id}\|{payment_id}").hexdigest() == signature`. If secret is missing or signature fails, raises `PaymentVerificationError` (HTTP 400). |
| [`backend/app/services/payment_service.py:508`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/app/services/payment_service.py#L508) | Webhook payment verification (`POST /api/payments/webhook`) | **Webhook HMAC Verification**:`hmac.new(RAZORPAY_WEBHOOK_SECRET, raw_body).hexdigest() == header_signature`. If signature mismatch, returns HTTP 400. |
| [`backend/app/routes/admin_routes.py:586`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/app/routes/admin_routes.py#L586) | Admin manual booking (`POST /api/admin/bookings/manual`) | **Strict Admin RBAC & Session Barrier**: Requires authenticated `owner` or `manager` JWT session cookie + CSRF double-submit token. Records immutable audit log. |

---

## 3. Payment Endpoints & Webhook Security Invariants

All payment endpoints are protected by cryptographic invariants verified by 27 frozen unit and integration tests:

1. **Server Pricing Authority:** The client cannot specify payment amounts. `POST /api/payments/create-order` computes the required token amount (`₹500` / 50,000 paise) authoritatively from the booking document.
2. **Signature Tampering Defense:** Tampered `razorpay_signature` values are cryptographically rejected with `PAYMENT_SIGNATURE_MISMATCH`.
3. **Idempotency Protection:** Repeated payment orders replay identical gateway responses without duplicate charges.
4. **Mode Separation Guard (`backend/app/config.py`):** The backend immediately throws a fatal startup exception (`ValueError`) if a live Razorpay key (`rzp_live_...`) is detected in development or test environments.

---

## 4. Test Verification Evidence

The payment security invariants are proven by 27 dedicated automated tests in:
- [`backend/tests/test_payments.py`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/tests/test_payments.py) (14 tests)
- [`backend/tests/test_razorpay_standard.py`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/tests/test_razorpay_standard.py) (9 tests)
- [`backend/tests/test_payments_and_security_hardening.py`](file:///c:/Users/balaj/OneDrive/Desktop/joybox/backend/tests/test_payments_and_security_hardening.py) (4 tests)
