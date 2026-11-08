# API SPECIFICATION — Joybox Party Room
**Phase 2 · Created 2026-10-28 · Flask REST API**

---

## Global Conventions

### Base Path
All endpoints are prefixed with `/api`. Example: `GET /api/health`

### Response Envelope
Every response uses this structure:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { "pagination": { "page": 1, "limit": 20, "total": 45 } }
}
```
- On success: `"success": true`, `"data": <payload>`, `"error": null`
- On error: `"success": false`, `"data": null`, `"error": { "code": "SNAKE_CASE_CODE", "message": "Human-readable message" }`
- `"meta"` is present only on paginated list responses

### Error Codes (standard set)
| HTTP | code | Meaning |
|---|---|---|
| 400 | `INVALID_REQUEST` | Malformed JSON / missing required field |
| 422 | `VALIDATION_ERROR` | Field validation failed (Marshmallow); `error.details` contains field-level messages |
| 422 | `IDEMPOTENCY_PAYLOAD_MISMATCH` | Idempotency key was previously submitted with a different request payload |
| 404 | `NOT_FOUND` | Resource does not exist or invalid access token |
| 409 | `SLOT_CONFLICT` | Slot already taken / buffer overlap |
| 409 | `IDEMPOTENCY_CONFLICT` | A request with this idempotency key is currently processing |
| 409 | `INVALID_STATE` | Operation not allowed in current booking state (e.g. already cancelled) |
| 410 | `HOLD_EXPIRED` | Hold expired |
| 429 | `RATE_LIMITED` | Too many requests per IP or phone number |
| 500 | `INTERNAL_ERROR` | Unexpected server error (no stack trace exposed) |
| 503 | `DATABASE_UNAVAILABLE` | MongoDB unreachable |

### Authentication
- Public endpoints: no auth header required
- Admin endpoints: `Authorization: Bearer <jwt_token>` or `httpOnly` cookie
- All admin endpoints return `401 UNAUTHORIZED` if token missing/invalid
- All admin endpoints return `403 FORBIDDEN` if role insufficient

### Money
- All `*Minor` fields are **integer paise** (₹999 = `99900`)
- API responses also include `*Rupees` float for display convenience: `"totalRupees": 999.00`
- **The server is the only source of truth for prices.** Never trust browser-submitted prices.

### Timestamps
- All timestamps in responses are ISO 8601 UTC strings: `"2026-11-01T03:30:00Z"`
- The client displays them in IST (`Asia/Kolkata`, UTC+5:30)

### Idempotency
- `POST /api/bookings` and `POST /api/payments/*` require header:
  `Idempotency-Key: <client-generated UUID v4>`
- Duplicate requests with the same key return the cached first response

### Pagination
List endpoints accept query params: `?page=1&limit=20`
Default: `page=1`, `limit=20`, max `limit=100`

---

## Public Endpoints

---

### `GET /api/health`

**Purpose:** Service and database health check. Used by Render health checks.

**Auth:** None

**Response 200:**
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "database": "connected",
    "timestamp": "2026-10-28T00:00:00Z"
  },
  "error": null
}
```
`"database"` values: `"connected"` | `"not_configured"` | `"unavailable"`

Response is `503` if database is `"unavailable"`.

---

### `GET /api/packages`

**Purpose:** Retrieve the active package catalogue, ordered by `displayOrder`.

**Auth:** None

**Query params:** None

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "507f...011",
        "code": "basic",
        "name": "Basic",
        "nameTe": "బేసిక్",
        "pricePerHourMinor": 99900,
        "pricePerHourRupees": 999.0,
        "currency": "INR",
        "features": ["AC room", "Birthday decoration theme", "Music"],
        "featuresTe": ["ఏసీ హాల్", "బర్త్‌డే డెకరేషన్ థీమ్", "మ్యూజిక్"],
        "excludes": ["Fresh Cake", "Name Letters"],
        "includedAddOnCodes": [],
        "isFeatured": false,
        "displayOrder": 1
      }
    ],
    "currency": "INR"
  },
  "error": null
}
```

---

### `GET /api/packages/<code>`

**Purpose:** Retrieve a single package by its code slug.

**Auth:** None

**Path params:** `code` — one of `basic`, `gold`, `diamond`

**Response 200:** Single package object (same structure as items in list above)

**Response 404:** `NOT_FOUND`

---

### `GET /api/add-ons`

**Purpose:** Retrieve all active add-ons.

**Auth:** None

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "507f...021",
        "code": "bubble_entry",
        "name": "Bubble Machine Entry",
        "nameTe": "బుడగల మెషిన్ ఎంట్రీ",
        "description": "Magical floating bubbles for cake entry",
        "descriptionTe": "...",
        "priceMinor": 30000,
        "priceRupees": 300.0,
        "currency": "INR",
        "iconSymbol": "bubble_chart",
        "displayOrder": 1
      }
    ]
  },
  "error": null
}
```

---

### `GET /api/offers/active`

**Purpose:** Returns the currently active promotional offer(s). Used for the offer banner, package cards, and price estimator. The remaining slot count is informational — do not trust for final eligibility.

**Auth:** None

**Response 200:**
```json
{
  "success": true,
  "data": {
    "offers": [
      {
        "id": "507f...061",
        "name": "Basic Introductory Offer",
        "nameTe": "బేసిక్ పరిచయ ఆఫర్",
        "description": "Basic package at ₹500/hr for the first 5 bookings each month",
        "eligiblePackageCode": "basic",
        "promoPricePerHourMinor": 50000,
        "promoPricePerHourRupees": 500.0,
        "regularPricePerHourMinor": 99900,
        "monthlyLimit": 5,
        "slotsRemainingThisMonth": 3
      }
    ]
  },
  "error": null
}
```
`slotsRemainingThisMonth` = `monthlyLimit - monthlyRedemptionCount`. Returns `0` if exhausted — the offer is still listed so the customer knows it exists but is full for the month.

---

### `GET /api/gallery`

**Purpose:** Returns gallery images for the gallery page and landing page strip.

**Auth:** None

**Query params:** `?category=kids` (optional filter), `?limit=12&page=1`

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "507f...081",
        "url": "https://cdn.cloudinary.com/joybox/...",
        "thumbnailUrl": "https://cdn.cloudinary.com/joybox/.../w_400",
        "altText": "Peppa & Rainbow Birthday Theme at Joybox Vadlamudi",
        "altTextTe": "...",
        "caption": "Peppa & Rainbow Theme",
        "category": "kids",
        "themeTag": "peppa_pig"
      }
    ]
  },
  "meta": { "pagination": { "page": 1, "limit": 12, "total": 24 } },
  "error": null
}
```
**Never expose:** `storageKey`

---

### `GET /api/faqs`

**Purpose:** FAQ accordion content.

**Auth:** None

**Query params:** `?category=booking` (optional)

**Response 200:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "507f...091",
        "question": "How far in advance should I book?",
        "questionTe": "...",
        "answer": "We recommend booking at least 2–3 days in advance for weekends.",
        "answerTe": "...",
        "category": "booking",
        "displayOrder": 1
      }
    ]
  },
  "error": null
}
```

---

### `GET /api/availability`

**Purpose:** Returns available time slots for a given date and room. Used by the booking wizard Step 1 calendar.

**Auth:** None

**Query params:**
- `date` (required): `YYYY-MM-DD` in IST
- `roomId` (optional, default: `"main"`)
- `durationHours` (required): `1`–`6` integer — returns only slots that can fit the requested duration

**Logic (server-enforced):**
1. Convert requested date to UTC range (00:00–23:59 IST)
2. Operating window: 09:00–22:00 IST
3. Generate all possible start times on the hour within operating window that fit `durationHours` (end ≤ 22:00)
4. For each candidate slot, check if ALL constituent hours + 1-hour buffer are unclaimed:
   - No `slotClaims` document with matching `roomId` and `slotStart`
   - No `availabilityBlock` overlapping the range
5. Return available and unavailable slots so the UI can render a calendar

**Response 200:**
```json
{
  "success": true,
  "data": {
    "date": "2026-11-01",
    "roomId": "main",
    "durationHours": 2,
    "timezone": "Asia/Kolkata",
    "openingTime": "09:00",
    "closingTime": "22:00",
    "slots": [
      {
        "startTime": "09:00",
        "endTime": "11:00",
        "startAt": "2026-11-01T03:30:00Z",
        "endAt": "2026-11-01T05:30:00Z",
        "available": true
      },
      {
        "startTime": "10:00",
        "endTime": "12:00",
        "startAt": "2026-11-01T04:30:00Z",
        "endAt": "2026-11-01T06:30:00Z",
        "available": false,
        "unavailableReason": "booked"
      }
    ]
  },
  "error": null
}
```
`unavailableReason` values: `"booked"` | `"hold"` | `"buffer"` | `"blocked"` | `"outside_hours"`

**Response 422:** `date` missing/invalid, `durationHours` out of range

---

### `POST /api/bookings/quote`

**Purpose:** Returns a server-computed itemized price breakdown. **No booking is created.** Call this for the live price estimator and at every step of the booking wizard.

**Auth:** None

**Request body:**
```json
{
  "packageCode": "gold",
  "durationHours": 3,
  "addOnCodes": ["bubble_entry"],
  "applyPromo": true
}
```

**Validation:**
- `packageCode` required, must be active package code
- `durationHours` required, integer 1–6
- `addOnCodes` optional array, each must be active add-on code
- `addOnCodes` must not contain add-ons already included in the selected package

**Response 200:**
```json
{
  "success": true,
  "data": {
    "packageCode": "gold",
    "packageName": "Gold",
    "durationHours": 3,
    "currency": "INR",
    "lineItems": [
      { "description": "Gold package × 3 hours", "amountMinor": 450000, "amountRupees": 4500.0 },
      { "description": "Bubble Machine Entry", "amountMinor": 30000, "amountRupees": 300.0 }
    ],
    "baseAmountMinor": 450000,
    "addOnsAmountMinor": 30000,
    "promoApplied": false,
    "promoNotAppliedReason": "Package not eligible for current offer",
    "discountAmountMinor": 0,
    "taxAmountMinor": 0,
    "taxRatePercent": 0,
    "totalAmountMinor": 480000,
    "totalRupees": 4800.0,
    "note": "Indicative. Final total is locked at booking confirmation."
  },
  "error": null
}
```
If promo applies:
- `promoApplied: true`
- `lineItems` shows discount as a negative line item
- `slotsRemainingThisMonth` in response (informational)

**Response 422:** Invalid package, invalid add-on, duration out of range

---

### `POST /api/inquiries`

**Purpose:** Saves a customer enquiry from the web form. No booking is created.

**Auth:** None

**Rate limit:** 5 per IP per 10 minutes

**Request body:**
```json
{
  "name": "Ravi Kumar",
  "phone": "9876543210",
  "preferredDate": "2026-11-15",
  "preferredTime": "10:00",
  "packageCode": "gold",
  "durationHours": 2,
  "message": "Birthday party for my daughter",
  "language": "en"
}
```

**Validation (Marshmallow `InquirySchema`):**
- `name`: string, required, 2–100 chars
- `phone`: string, required, 8–20 chars
- `preferredDate`: string, optional, max 30 chars
- `preferredTime`: string, optional, max 30 chars
- `packageCode`: string, optional, default `"basic"`, one of `["basic","gold","diamond"]`
- `durationHours`: integer, optional, default `1`, range 1–6
- `message`: string, optional, max 2000 chars
- `language`: string, optional, default `"en"`, one of `["en","te"]`

**Response 201:**
```json
{
  "success": true,
  "data": {
    "id": "507f...041",
    "status": "received",
    "message": "Thank you, Ravi. We will contact you on 98*****210 within 15 minutes."
  },
  "error": null
}
```
**Never echo back** the raw phone number — mask it in the response.

**Response 422:** Validation error with field-level details

---

### `POST /api/bookings`

**Purpose:** Creates a booking. Atomically claims slots. Returns `bookingReference` and Razorpay order details.

**Auth:** None

**Required header:** `Idempotency-Key: <uuid-v4>`

**Rate limit:** 3 per IP per minute

**Request body:**
```json
{
  "roomId": "main",
  "date": "2026-11-01",
  "startTime": "09:00",
  "durationHours": 2,
  "packageCode": "basic",
  "addOnCodes": ["bubble_entry"],
  "applyPromo": true,
  "customer": {
    "name": "Ravi Kumar",
    "phone": "9876543210",
    "email": "ravi@example.com",
    "language": "te"
  },
  "occasionType": "birthday",
  "celebrantName": "Priya",
  "specialRequests": "Pink balloons please",
  "guestCount": 12,
  "termsAccepted": true
}
```

**Validation:**
- All fields validated by Marshmallow `BookingCreateSchema`
- `termsAccepted` must be `true`
- `startTime` must be on the hour (`:00`)
- `date` must be today or future (not past)
- `durationHours` must be 1–6
- Start + duration must be within 09:00–22:00 IST

**Server processing order:**
1. Validate all fields
2. Check idempotency key (return cached response if duplicate)
3. Check date is not in the past
4. Compute UTC `startAt` / `endAt`
5. Re-verify slot availability (overlap + buffer + blocks + hours)
6. Compute authoritative price (never trust request body prices)
7. Check promo eligibility; atomically claim promo slot if applicable
8. Atomically insert `slotClaims` for all booking hours + 1-hour buffer
9. If any slot claim fails (duplicate key): roll back all inserted claims; return `409 CONFLICT`
10. Create `bookings` document with `status: pending_payment`
11. Create `customers` upsert (by phone)
12. Create Razorpay order for `totalAmountMinor`
13. Store idempotency key with response snapshot
14. Return response

**Response 201:**
```json
{
  "success": true,
  "data": {
    "bookingReference": "JBX-2026-0001",
    "accessToken": "bK9_x8QZ2yP1LmN4wE7rT0vC3uI6oA...",
    "bookingId": "507f...031",
    "bookingStatus": "pending_payment",
    "startAt": "2026-11-01T03:30:00Z",
    "endAt": "2026-11-01T05:30:00Z",
    "startTimeIst": "2026-11-01 09:00 IST",
    "endTimeIst": "2026-11-01 11:00 IST",
    "durationHours": 2,
    "pricing": {
      "baseAmountMinor": 100000,
      "addOnsAmountMinor": 30000,
      "discountAmountMinor": 0,
      "taxAmountMinor": 0,
      "totalAmountMinor": 130000,
      "totalRupees": 1300.0,
      "currency": "INR"
    },
    "whatsappLink": "https://wa.me/917842704429?text=Hi%20Joybox!%20My%20booking%20ref%20is%20JBX-2026-0001"
  },
  "error": null
}
```
`accessToken` is an unguessable 32-byte URL-safe string. The server stores only its SHA-256 hash. The client must store this token in session memory or URL fragment to access full booking details or cancel.

**Response 422 (Idempotency mismatch):**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "IDEMPOTENCY_PAYLOAD_MISMATCH",
    "message": "Idempotency key reused with different request payload."
  }
}
```

**Response 409 (slot conflict):**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "SLOT_CONFLICT",
    "message": "The 09:00–11:00 slot on 1 Nov is no longer available. Please choose a different time."
  }
}
```

**Response 429 (rate limited):**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Please wait before creating more reservation requests."
  }
}
```

---

### `GET /api/bookings/<bookingReference>`

**Purpose:** Booking status lookup.
- **Reference-only lookup (no token):** Returns minimal status only (`isMinimal: true`). NEVER returns customer name, phone fragments, pricing, or celebrant name.
- **Authorized lookup (with `?token=...` or `X-Booking-Token` header):** Returns full display-safe details.
- **Wrong token:** Returns `404 NOT_FOUND` (identical to unknown reference to prevent token or reference enumeration).

**Auth:** None (bearer access token verified via constant-time HMAC comparison)

**Path params:** `bookingReference` — e.g., `JBX-2026-0001`
**Query params:** `?token=<access_token>` (optional)
**Headers:** `X-Booking-Token: <access_token>` (optional alternative)

**Response 200 (Minimal lookup without token):**
```json
{
  "success": true,
  "data": {
    "bookingReference": "JBX-2026-0001",
    "bookingStatus": "pending_payment",
    "paymentStatus": "unpaid",
    "isMinimal": true
  },
  "error": null
}
```

**Response 200 (Authorized lookup with valid token):**
```json
{
  "success": true,
  "data": {
    "bookingReference": "JBX-2026-0001",
    "bookingStatus": "confirmed",
    "paymentStatus": "paid",
    "startTimeIst": "Sun, Nov 01, 2026 09:00 AM",
    "endTimeIst": "Sun, Nov 01, 2026 11:00 AM",
    "durationHours": 2,
    "packageName": "Basic",
    "occasionType": "birthday",
    "celebrantName": "Priya",
    "customerName": "Ravi K.",
    "customerPhoneMasked": "****3210",
    "pricing": {
      "totalAmountMinor": 130000,
      "totalRupees": 1300.0,
      "currency": "INR",
      "paymentStatus": "paid"
    },
    "whatsappLink": "https://wa.me/917842704429?text=Hi%20Joybox!%20My%20booking%20ref%20is%20JBX-2026-0001"
  },
  "error": null
}
```

**Fields NEVER returned:** full phone, email, `adminNotes`, `accessTokenHash`, `customerId`

**Response 404:** Booking reference not found OR wrong access token.

---

### `POST /api/bookings/<bookingReference>/cancel`

**Purpose:** Cancels a booking, releases its slots and returns any promo allocation.
**Auth:** Requires `token` in body, query param `?token=...`, or header `X-Booking-Token`. Wrong or missing token returns 404.

**Request body:**
```json
{
  "token": "bK9_x8QZ2yP1LmN4wE7rT0vC3uI6oA...",
  "reason": "Change of schedule"
}
```

**Response 200:**
```json
{
  "success": true,
  "data": {
    "bookingReference": "JBX-2026-0001",
    "bookingStatus": "cancelled",
    "cancelledAt": "2026-10-28T10:00:00Z",
    "message": "Booking has been successfully cancelled and slot released."
  },
  "error": null
}
```

---

### `POST /api/payments/create-order`

**Purpose:** Creates a Razorpay payment order for an existing booking. Called just before showing the Razorpay checkout modal.

**Auth:** Unguessable `token` in payload (SHA-256 validated). Returns 404 on invalid token.

**Required header:** `Idempotency-Key: <uuid-v4>` (Optional)

**Rate limit:** 5 per IP per minute

**Request body:**
```json
{
  "bookingReference": "JBX-2026-0001",
  "token": "unguessable_access_token_32_bytes"
}
```

**Server logic:**
1. Look up booking; confirm `bookingStatus = pending_payment` and `paymentStatus = unpaid`
2. Verify `token` with constant-time HMAC check against stored `accessTokenHash`
3. Use the server-stored `pricing.totalAmountMinor` — never use a client-supplied amount
4. Create Razorpay order via direct REST client using `RAZORPAY_KEY_SECRET`
5. Store payment record with `providerOrderId` in the database
6. Return public-safe fields to the client

**Response 201:**
```json
{
  "success": true,
  "data": {
    "orderId": "order_ABC123",
    "keyId": "rzp_test_xxx",
    "amountMinor": 130000,
    "amountRupees": 1300.0,
    "currency": "INR",
    "bookingReference": "JBX-2026-0001",
    "customer": {
      "name": "Priya",
      "phone": "9876543210",
      "email": ""
    }
  },
  "error": null
}
```
`keyId` is the **public key** (starts with `rzp_`). Never return the secret.

---

### `POST /api/payments/verify`

**Purpose:** Verifies Razorpay payment signature after customer completes payment. Updates booking to `confirmed`.

**Auth:** Unguessable `token` in payload (SHA-256 validated).

**Request body:**
```json
{
  "bookingReference": "JBX-2026-0001",
  "token": "unguessable_access_token_32_bytes",
  "razorpay_order_id": "order_ABC123",
  "razorpay_payment_id": "pay_XYZ789",
  "razorpay_signature": "abc123def456..."
}
```

**Server logic:**
1. Verify HMAC: `HMAC-SHA256(razorpay_order_id + "|" + razorpay_payment_id, RAZORPAY_KEY_SECRET)` must equal `razorpay_signature`
2. If verification fails: return `400 PAYMENT_VERIFICATION_FAILED` — do NOT mark booking as paid
3. Verify slot claims remain active in `slotClaims`. If claims were lost and slot taken by another guest, trigger automatic full refund and return `409 LATE_PAYMENT_SLOT_TAKEN`
4. If signature valid and slots intact: update `bookings` → `bookingStatus: confirmed`, `paymentStatus: paid`
5. Update `payments` document with captured status and provider payment ID
6. Return confirmed booking summary

**Response 200:**
```json
{
  "success": true,
  "data": {
    "bookingReference": "JBX-2026-0001",
    "bookingStatus": "confirmed",
    "paymentStatus": "paid",
    "orderId": "order_ABC123",
    "paymentId": "pay_XYZ789",
    "amountMinor": 130000,
    "currency": "INR",
    "confirmedAt": "2026-10-28T18:00:00Z",
    "message": "Payment verified and booking confirmed successfully."
  },
  "error": null
}
```

---

### `POST /api/payments/webhook`

**Purpose:** Razorpay server-to-server webhook. Idempotent — processing the same event twice is safe.

**Auth:** Webhook signature in `X-Razorpay-Signature` header, verified against `RAZORPAY_WEBHOOK_SECRET`

**IMPORTANT:** Verify signature on the **raw request body bytes** before JSON parsing.

**Server logic:**
1. Read raw body bytes
2. Compute `HMAC-SHA256(raw_body, RAZORPAY_WEBHOOK_SECRET)`; compare to `X-Razorpay-Signature`
3. If signature invalid: return `400` immediately; log the attempt
4. Atomically claim `(provider, eventId)` in `webhookEvents` collection
5. If already claimed: return `200` with `status: "already_processed"`
6. Parse event type and process:
   - `payment.captured` → confirm booking, update payment
   - `payment.failed` → update booking to `payment_failed`
   - `refund.processed` → update refund record and payment refunded totals
7. Mark `webhookEvents.status` as `processed`

**Response 200:** `{ "success": true, "data": { "status": "processed", "eventId": "evt_..." } }`

---

### `POST /api/payments/refund`

**Purpose:** Processes a cancellation refund compliant with business notice tiers or explicit authorized amount.

**Auth:** Unguessable `token` in payload (SHA-256 validated).

**Request body:**
```json
{
  "bookingReference": "JBX-2026-0001",
  "token": "unguessable_access_token_32_bytes",
  "reason": "Change of schedule",
  "amountMinor": 50000
}
```

**Server logic:**
1. Validates access token and confirmed payment status
2. Calculates refundable balance and applies cancellation policy tiers (>48h = 100%, 24-48h = 50%, <24h = non-refundable)
3. Issues refund through Razorpay API
4. Records entry in `refunds` collection and updates `payments`
5. On full refund, cancels booking and releases slot claims and promo reservations

**Response 200:**
```json
{
  "success": true,
  "data": {
    "refundId": "rfnd_ABC123",
    "bookingReference": "JBX-2026-0001",
    "amountMinor": 50000,
    "amountRupees": 500.0,
    "currency": "INR",
    "status": "processed",
    "refundStatus": "partially_refunded",
    "refundedAt": "2026-10-28T18:05:00Z",
    "message": "Refund processed successfully."
  },
  "error": null
}
```

---

## Admin Endpoints

All admin endpoints are under `/api/admin/`. All require valid JWT or session cookie.

---

### `POST /api/admin/auth/login`

**Rate limit:** 5 attempts per IP per 15 minutes (lockout after 5 failures)

**Request body:** `{ "username": "kiran", "password": "..." }`

**Response 200:** Sets `httpOnly` session cookie; returns `{ "role": "super_admin", "displayName": "Kiran Kumar" }`

**Response 401:** Invalid credentials (same message for wrong username or wrong password — never leak which)

---

### `POST /api/admin/auth/logout`

**Auth:** Required

**Response 200:** Clears session cookie

---

### `GET /api/admin/dashboard`

**Auth:** Required (any admin role)

**Response 200:** KPI summary — total revenue this month, bookings count, promo usage, pending inquiries count

---

### `GET /api/admin/bookings`

**Auth:** Required

**Query params:** `?date=2026-11-01&status=confirmed&page=1&limit=20`

**Response 200:** Paginated list of bookings (full fields including customer phone for admin use)

---

### `GET /api/admin/bookings/<id>`

Full booking detail including admin notes.

---

### `PATCH /api/admin/bookings/<id>`

**Auth:** Required (any role)

**Allowed mutations:** `bookingStatus`, `adminNotes`, `paymentMethod` (cash)

**Response 200:** Updated booking. Creates `auditLogs` entry on every change.

---

### `GET /api/admin/inquiries`

**Query params:** `?status=new&page=1&limit=20`

---

### `PATCH /api/admin/inquiries/<id>`

**Allowed mutations:** `status`, `adminNotes`, `convertedToBookingId`

---

### `GET /api/admin/packages`

Full list including inactive packages.

---

### `PATCH /api/admin/packages/<id>`

**Auth:** Required (super_admin only)

**Allowed mutations:** `pricePerHourMinor`, `features`, `isActive`, `isFeatured`

**Audit:** Always logged.

---

### `GET /api/admin/add-ons` / `PATCH /api/admin/add-ons/<id>`

Same pattern as packages.

---

### `GET /api/admin/offers`

Returns offers with `monthlyRedemptionCount` and remaining quota.

---

### `PATCH /api/admin/offers/<id>`

**Auth:** super_admin only

**Allowed mutations:** `isActive`, `monthlyLimit`, `promoPricePerHourMinor`

---

### `GET /api/admin/gallery` / `POST /api/admin/gallery` / `DELETE /api/admin/gallery/<id>`

Gallery asset management. `POST` accepts `url`, `altText`, `category`, `themeTag`, `storageKey`.

---

### `GET /api/admin/reviews` / `PATCH /api/admin/reviews/<id>`

Review moderation. `PATCH` allows `status: approved | hidden`.

---

### `GET /api/admin/availability-blocks`

**Query params:** `?from=2026-11-01&to=2026-11-30`

---

### `POST /api/admin/availability-blocks`

**Request body:**
```json
{
  "roomId": "main",
  "startAt": "2026-11-05T03:30:00Z",
  "endAt": "2026-11-05T16:30:00Z",
  "reason": "Deep cleaning",
  "isEmergency": false
}
```

---

### `POST /api/admin/auth/login`
Authenticates an administrator, initializes a session in `adminSessions` with SHA-256 token hashing, sets a secure `HttpOnly` session cookie (`joybox_admin_session`), and issues an HMAC-SHA256 `csrfToken`. Enforces account lockout (15 minutes) after 5 consecutive failed attempts.

**Request body:**
```json
{
  "username": "kiran",
  "password": "Password123!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "671fb4d012a953ad082fdad1",
      "username": "kiran",
      "email": "kiran@joyboxparty.com",
      "displayName": "Kiran Kumar",
      "role": "owner"
    },
    "csrfToken": "a1b2c3d4..."
  },
  "error": null,
  "meta": { "message": "Login successful." }
}
```

---

### `POST /api/admin/auth/logout`
Revokes the current administrator session in `adminSessions` and clears the `joybox_admin_session` cookie.

---

### `GET /api/admin/auth/me`
Validates the current session cookie, touches the session sliding idle window (30 mins), and returns the authenticated user profile with a freshly derived `csrfToken`.

---

### `POST /api/admin/auth/change-password`
Requires authenticated session + `X-CSRF-Token` header. Verifies current password, hashes new password with bcrypt (work factor 12), and logs `admin_change_password` to `auditLogs`.

---

### `GET /api/admin/dashboard`
Returns operational KPIs: today's bookings count, monthly total revenue (paise), monthly promo slot usage count, pending inquiries count, and `needsReview` payments count.

---

### `GET /api/admin/bookings`
Lists bookings with pagination and optional filters (`status`, `date`, `search`, `page`, `limit`).

---

### `GET /api/admin/bookings/<ref>`
Retrieves full booking details, associated payment records, and refund items.

---

### `PATCH /api/admin/bookings/<ref>`
Requires `X-CSRF-Token`. Allows updating booking status (e.g. `cancelled`, `completed`) or internal notes. If cancelling a confirmed booking, atomically releases slot claims and rolls back promo redemption quota.

---

### `POST /api/admin/bookings`
Requires `X-CSRF-Token`. Creates a manual/offline booking with atomic slot claim reservation against MongoDB `slotClaims`. Prevents double-booking.

---

### `GET /api/admin/availability-blocks`
Lists current emergency and maintenance availability blocks.

---

### `POST /api/admin/availability-blocks`
Requires `X-CSRF-Token`. Atomically claims all 30-minute intervals covering the block window in `slotClaims`. If any slot is already booked or blocked, rejects with `409 SLOT_CONFLICT`.

---

### `DELETE /api/admin/availability-blocks/<id>`
Requires `X-CSRF-Token`. Deletes availability block and atomically releases all associated slot claims.

---

### `GET /api/admin/inquiries`
Lists customer inquiries with status filter (`new`, `responded`, `booked`, `archived`).

---

### `PATCH /api/admin/inquiries/<id>`
Requires `X-CSRF-Token`. Updates inquiry status and notes.

---

### `GET /api/admin/packages` & `POST /api/admin/packages` & `PATCH /api/admin/packages/<id>`
Lists or manages packages. `POST` requires `owner` role; `PATCH` requires `owner` or `manager`.

---

### `GET /api/admin/add-ons` & `POST /api/admin/add-ons` & `PATCH /api/admin/add-ons/<id>`
Lists or manages add-ons.

---

### `GET /api/admin/payments`
Lists gateway transactions with optional `needsReview=true` filter.

---

### `POST /api/admin/payments/<id>/retry-refund`
Requires `X-CSRF-Token`. Retries a failed refund via the payment gateway and updates audit log.

---

### `GET /api/admin/audit-logs`
Requires `owner` or `manager` role. Returns chronological list of system actions with user, role, action, target, timestamp, and IP address.

---

## Endpoint Matrix (Phase Implementation Order)

| Phase | Endpoint | Status |
|---|---|---|
| 3 | `GET /api/health` | ✅ Built & Verified |
| 3 | `GET /api/packages` | ✅ Built & Verified |
| 3 | `GET /api/packages/<code>` | ✅ Built & Verified |
| 3 | `GET /api/add-ons` | ✅ Built & Verified |
| 3 | `GET /api/offers/active` | ✅ Built & Verified |
| 3 | `POST /api/inquiries` | ✅ Built & Verified |
| 3 | `POST /api/bookings/quote` | ✅ Built & Verified |
| 4 | `GET /api/gallery` | ✅ Built & Verified |
| 4 | `GET /api/faqs` | ✅ Built & Verified |
| 5 | `GET /api/availability` | ✅ Built & Verified |
| 5 | `POST /api/bookings` | ✅ Built & Verified |
| 5 | `GET /api/bookings/<ref>` | ✅ Built & Verified |
| 5 | `POST /api/bookings/<ref>/cancel` | ✅ Built & Verified |
| 6 | `POST /api/payments/create-order` | ✅ Built & Verified |
| 6 | `POST /api/payments/verify` | ✅ Built & Verified |
| 6 | `POST /api/payments/webhook` | ✅ Built & Verified |
| 6 | `POST /api/payments/refund` | ✅ Built & Verified |
| 7 | All `/api/admin/*` (Auth, Dashboard, Bookings, Blocks, Catalog, Payments, Audit) | ✅ Built & Verified (69 tests on Atlas) |
