# Booking Engine Logic Specification

**Version:** 1.0.0 (Launch Specification)  
**Timezone Authority:** `Asia/Kolkata` (IST, UTC+05:30)  
**Database Guard:** Live MongoDB Atlas (`joybox_party_room_test`)  
**Status:** **AUTHORITATIVE RELEASE SPECIFICATION**

---

## 1. Core Business Constants & Invariants

| Parameter | Authoritative Value | Source / Confirmation | Description |
| :--- | :--- | :--- | :--- |
| **Operating Window** | 09:00 AM – 10:00 PM IST | Owner Confirmed | Venue doors open at 09:00 IST; all celebrations must conclude by 22:00 IST. |
| **Sanitization Buffer** | 30 minutes | Owner Confirmed | Post-event hall cleaning and preparation window. |
| **Minimum Duration** | 1 hour (60 minutes) | Owner Confirmed | Shortest permitted celebration booking. |
| **Maximum Duration** | 6 hours (360 minutes) | Owner Confirmed | Longest permitted single celebration booking. |
| **Duration Granularity** | Integer hours (1, 2, 3, 4, 5, 6) | System Rule | Half-hour fractional party durations are rejected. |
| **Slot Unit Size** | 30 minutes | Anti-double-booking Invariant | Discrete atomic reservation unit. |
| **Max Advance Booking** | 90 calendar days | Owner Confirmed | Rolling window from today's date in IST. |
| **Hold Duration (TTL)** | 10 minutes (600 seconds) | System Default | Temporary reservation lock for payment checkout. |
| **Default Room ID** | `"main"` | Single Venue Adda | Joybox Party Room, Vadlamudi (Beside Durga Mart). |
| **Buffer Past Closing** | Permitted (until 22:30 IST) | Operational Rule | Event must end by 22:00; cleaning buffer may extend to 22:30. |

---

## 2. Formal Business Logic Rules (BL-01 through BL-16)

### BL-01: Venue Operating Hours
- Celebrations may only be scheduled between **09:00 AM** and **10:00 PM IST** (`09:00` to `22:00`).
- The earliest valid slot start time is `09:00` IST.
- The latest valid slot start time for a 1-hour booking is `21:00` IST (ending at `22:00` IST).
- Any requested slot starting before `09:00` IST or ending after `22:00` IST must be rejected with validation error `TIME_OUT_OF_BOUNDS`.

### BL-02: Mandatory Post-Event Sanitization Buffer
- Every booking and hold automatically reserves a **30-minute sanitization buffer** immediately following the event end time.
- If a party runs from `18:00` to `20:00`, the room is reserved from `18:00` to `20:30`.
- The buffer is strictly protected against other bookings: a subsequent booking cannot start until `20:30` or later.
- If a party ends at `22:00` IST (closing time), the 30-minute buffer runs from `22:00` to `22:30` IST and is explicitly allowed past closing (`ALLOW_BUFFER_PAST_CLOSING = True`).

### BL-03: Duration Boundaries & Fractional Handling
- Permitted booking durations are strictly integers: **1, 2, 3, 4, 5, or 6 hours**.
- Requested durations of `0` hours, negative values, fractional values (e.g. `0.5`, `1.5`, `2.5`), or durations $> 6$ hours (e.g. `6.5`, `7`) must be rejected with validation error `INVALID_DURATION`.

### BL-04: 90-Day Advance Booking Window
- Customers may book from **Day 0** (today in IST, provided the slot start time is in the future) up to **Day 90** (today + 90 calendar days).
- Bookings on Day 0, Day 89, and Day 90 are permitted.
- Bookings on Day 91 or beyond must be rejected with error `ADVANCE_BOOKING_EXCEEDED`.
- Bookings on past dates (prior to today in IST) or past times today must be rejected with error `PAST_DATETIME_NOT_PERMITTED`.

### BL-05: Discrete 30-Minute Atomic Unit Slot Deferral
- Any party duration and its buffer are decomposed into aligned 30-minute intervals:
  $$\text{Total Intervals} = \frac{\text{Duration Minutes} + \text{Buffer Minutes}}{\text{Slot Unit Minutes}} = \frac{D \times 60 + 30}{30} = 2D + 1$$
- For a 2-hour party ($D=2$), exactly 5 unit intervals are created (4 party slots + 1 buffer slot).
- Each interval is represented by a document in `slotClaims`:
  `{ roomId: "main", slotStart: ISODate, slotEnd: ISODate, isBuffer: bool, ownerType: "hold"|"booking", ownerId: ObjectId }`.

### BL-06: Atomic All-or-Nothing Claim Algorithm
- Concurrency and double-booking prevention are strictly enforced at the database protocol level via a **unique compound index** on `slotClaims`:
  `db.slotClaims.create_index([("roomId", ASCENDING), ("slotStart", ASCENDING)], unique=True)`
- When claiming slots, the system executes an atomic batch insert. If ANY interval conflicts with an existing unexpired claim:
  1. MongoDB Atlas raises `DuplicateKeyError`.
  2. The service catches the error and executes an immediate atomic rollback: all intervals inserted during that transaction for that `ownerId` are deleted.
  3. The API returns HTTP 409 Conflict with `SLOT_UNAVAILABLE`.
  4. Zero orphan locks remain in the database.

### BL-07: Calendar Date Independence
- Slot claims are indexed and checked per specific date and time interval in UTC.
- A booked slot on Date A (e.g., `2026-11-10 18:00–20:00`) has ZERO effect on Date B (e.g., `2026-11-11 18:00–20:00`).
- The same time slot on any other calendar date remains 100% available for booking.

### BL-08: Checkout Hold TTL & Automated Expiry
- Creating a hold places an active reservation lock for **10 minutes** (`HOLD_DURATION_MINUTES = 10`).
- The hold record contains `expiresAt = now_utc + 10m`.
- If checkout is not completed within 10 minutes:
  1. The hold status transitions to `expired`.
  2. All associated `slotClaims` are released.
  3. Any reserved promotional quota is idempotently restored.
- Both active sweep jobs and on-demand lookups automatically clean up expired holds.

### BL-09: Background Sweeps Idempotency
- The background maintenance sweep (`python -m app.jobs.run_sweeps` / `sweep_expired_holds`) is idempotent.
- Running the sweep concurrently or multiple times in succession produces consistent state without crashing or double-releasing promotional quotas.

### BL-10: Unified Booking Code Path
- Whether a booking is created via direct `POST /api/bookings` or via two-step hold `POST /api/bookings/holds` $\rightarrow$ `POST /api/bookings`, both requests share the exact same validation, pricing, slot claim, and promotional reservation pipeline.

### BL-11: Package Selection Carry-Through
- When a user enters the booking wizard with a `?package=gold` URL query parameter, the system preselects that package without requiring the user to re-select it.
- If the user changes package, date, or duration, the server-side quote recalculates authoritatively.

### BL-12: Server-Side Pricing Authority
- The frontend never submits or dictates monetary amounts.
- All package base rates (`pricePerHourMinor`) and add-on rates (`priceMinor`) are fetched and calculated authoritatively by the backend quote engine from the active catalog in `db.packages` and `db.addOns`.
- Client tampering with pricing fields is ignored or rejected.

### BL-13: Anti-Hoarding Rate Limits
- To prevent malicious bots from locking up slots without paying:
  1. IP Rate Limit: Maximum 10 hold requests per 60 seconds per IP address (`RATE_LIMIT_HOLD_PER_IP_MAX = 10`).
  2. Phone Rate Limit: Maximum 3 active reservation attempts per 10 minutes per normalized 10-digit phone number (`RATE_LIMIT_HOLD_PER_PHONE_MAX = 3`).
- Requests exceeding these thresholds are rejected with HTTP 429 `RATE_LIMITED`.

### BL-14: Unguessable Customer Access Token
- Every confirmed booking issues a cryptographically secure 256-bit access token (`secrets.token_urlsafe(32)`).
- The raw token is returned once to the booking creator; only its `SHA-256` hash is persisted in `db.bookings`.
- Booking status lookups via `GET /api/bookings/:ref?token=...` require this token to inspect private customer details; public lookups without the token receive only sanitized scheduling information.

### BL-15: Deferred Payments Invariant
- While payments are in deferred testing status (`PAYMENTS_ENABLED = false`):
  - Checkout hold and booking creation record a pending reservation without falsely marking the booking as `paid` or `confirmed`.
  - No calls are made to live Razorpay servers.
  - Payment contracts and frozen tests (`backend/tests/test_payments*.py`, `test_razorpay_standard.py`) remain untouched.

### BL-16: Anti-Double-Booking Concurrency Invariant
- Under high concurrent load (e.g. 20 parallel requests racing for the same slot), exactly ONE request wins and receives an active reservation.
- All competing requests receive HTTP 409 Conflict `SLOT_UNAVAILABLE`.
- No duplicate bookings, overlapping slots, or partial claims can exist in the database.

---

## 3. Test Traceability Matrix

| Test Matrix | Target Rule IDs | Verification Scope |
| :--- | :--- | :--- |
| **Matrix A** | `BL-03` | Duration boundary testing (0, 0.5, 1, 6, 6.5, 7 hours). |
| **Matrix B** | `BL-02`, `BL-05` | Buffer boundaries (29, 30, 31 mins, back-to-back with/without buffer, overlapping). |
| **Matrix C** | `BL-04` | Advance window bounds (Day 0, Day 89, Day 90, Day 91, past dates). |
| **Matrix D** | `BL-01`, `BL-02` | Operating hours boundaries (08:00, 09:00, 21:00, 22:00, crossing closing time, midnight). |
| **Matrix E** | `BL-07`, `BL-10`, `BL-12`, `BL-13` | Date independence, payload validation, server price authority, anti-hoarding rate limits. |
| **Matrix F** | `BL-06`, `BL-16` | High concurrency race conditions (20 parallel threads & separate processes). |
| **Matrix G** | `BL-08`, `BL-09` | Hold TTL expiration and sweep job idempotency. |
| **Matrix H** | `BL-11`, `BL-14`, `BL-15` | Playwright E2E full journey, viewport testing, and deferred payments confirmation. |

