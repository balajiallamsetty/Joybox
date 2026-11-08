# DATABASE SCHEMA — Joybox Party Room
**Phase 2 · Created 2026-10-28 · MongoDB Atlas / PyMongo**

---

## Global Conventions

| Rule | Detail |
|---|---|
| `_id` | MongoDB `ObjectId` (BSON); serialized as 24-char hex string in JSON |
| Timestamps | All as UTC BSON `datetime`; convert for display using `Asia/Kolkata` |
| `createdAt` / `updatedAt` | On every document; `updatedAt` set on every write |
| `schemaVersion` | Integer, starting at `1`; increment when document structure changes |
| Money | Integer **paise** only (₹999 = `99900`). Never `float`. |
| Soft delete | `isDeleted: bool` + `deletedAt: datetime` on collections where deletion must be auditable |
| Phone | E.164 string, e.g., `"+917842704429"` (always normalized on write) |
| ObjectId refs | Stored as `ObjectId` in BSON; serialized as string in API responses |
| Room | `roomId: "main"` for the current single room |
| Timezone | Store UTC; display IST (`Asia/Kolkata`) |
| Slot keys | Slot start times are on the hour in UTC. E.g., IST 09:00 = UTC 03:30 |

---

## Collection Index

1. [packages](#1-packages)
2. [addOns](#2-addons)
3. [customers](#3-customers)
4. [inquiries](#4-inquiries)
5. [bookings](#5-bookings)
6. [bookingHolds](#6-bookingholds)
7. [slotClaims](#7-slotclaims)
8. [availabilityBlocks](#8-availabilityblocks)
9. [offers](#9-offers)
10. [offerRedemptions](#10-offerredemptions)
11. [payments](#11-payments)
12. [refunds](#12-refunds)
13. [users](#13-users)
14. [galleryAssets](#14-galleryassets)
15. [faqs](#15-faqs)
16. [reviews](#16-reviews)
17. [notifications](#17-notifications)
18. [auditLogs](#18-auditlogs)
19. [webhookEvents](#19-webhookevents)
20. [idempotencyKeys](#20-idempotencykeys)
21. [counters](#21-counters)
22. [rateLimits](#22-ratelimits)

---

## 1. `packages`

**Purpose:** Master catalogue of bookable packages. Served by `GET /api/packages`. Prices here are the live prices used for new quotes. Historical booking prices are preserved in booking snapshots.

**Access:** Public read; admin write.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `code` | string | ✅ | `"basic"` / `"gold"` / `"diamond"`. Unique. Slug used in URLs. |
| `name` | string | ✅ | Display name, e.g., `"Basic"` |
| `nameTe` | string | ❌ | Telugu translation of name |
| `pricePerHourMinor` | int | ✅ | In paise. Basic=99900, Gold=150000, Diamond=250000 |
| `currency` | string | ✅ | Always `"INR"` |
| `features` | [string] | ✅ | Ordered list of included features (English) |
| `featuresTe` | [string] | ❌ | Telugu translations of features |
| `excludes` | [string] | ❌ | Features explicitly NOT included (for comparison UI) |
| `includedAddOnCodes` | [string] | ❌ | Codes of add-ons already bundled (Diamond has all three) |
| `isFeatured` | bool | ✅ | `true` for Gold ("Most Popular") |
| `displayOrder` | int | ✅ | Sort order: Basic=1, Gold=2, Diamond=3 |
| `isActive` | bool | ✅ | `false` to hide without deleting |
| `schemaVersion` | int | ✅ | `1` |
| `createdAt` | datetime | ✅ | UTC |
| `updatedAt` | datetime | ✅ | UTC |

**Indexes:**
- `{ code: 1 }` unique — PK lookup by slug
- `{ isActive: 1, displayOrder: 1 }` — public listing, ordered

**Validation rules:**
- `pricePerHourMinor` must be a positive integer
- `code` must match `/^[a-z_]+$/`

**Sample document:**
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "code": "gold",
  "name": "Gold",
  "nameTe": "గోల్డ్",
  "pricePerHourMinor": 150000,
  "currency": "INR",
  "features": [
    "Everything in Basic",
    "Fresh 0.5 kg Birthday Cake",
    "Personalized Acrylic/Neon Name Display",
    "Easel Stand Custom Welcome Chalkboard"
  ],
  "featuresTe": ["..."],
  "excludes": ["Bubble & Fog Special Effects"],
  "includedAddOnCodes": [],
  "isFeatured": true,
  "displayOrder": 2,
  "isActive": true,
  "schemaVersion": 1,
  "createdAt": "2026-10-01T00:00:00Z",
  "updatedAt": "2026-10-01T00:00:00Z"
}
```

---

## 2. `addOns`

**Purpose:** A-la-carte add-ons purchasable with any package.

**Access:** Public read; admin write.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `code` | string | ✅ | `"bubble_entry"` / `"fog_entry"` / `"cold_fire_one_shot"` |
| `name` | string | ✅ | Display name |
| `nameTe` | string | ❌ | Telugu name |
| `description` | string | ✅ | Short description |
| `descriptionTe` | string | ❌ | Telugu description |
| `priceMinor` | int | ✅ | Flat charge in paise. Not per hour. |
| `currency` | string | ✅ | `"INR"` |
| `iconSymbol` | string | ❌ | Material Symbol name, e.g., `"bubble_chart"` |
| `isActive` | bool | ✅ | |
| `displayOrder` | int | ✅ | |
| `schemaVersion` | int | ✅ | `1` |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ code: 1 }` unique
- `{ isActive: 1, displayOrder: 1 }`

**Sample document:**
```json
{
  "_id": "507f1f77bcf86cd799439021",
  "code": "fog_entry",
  "name": "Low-Lying Fog Cloud",
  "nameTe": "ఫాగ్ ఎంట్రీ",
  "description": "Dense floor-hugging dry smoke effect for royal entry vibes",
  "priceMinor": 50000,
  "currency": "INR",
  "iconSymbol": "cloud",
  "isActive": true,
  "displayOrder": 2,
  "schemaVersion": 1,
  "createdAt": "2026-10-01T00:00:00Z",
  "updatedAt": "2026-10-01T00:00:00Z"
}
```

---

## 3. `customers`

**Purpose:** Stores guest customer contact data. A customer is identified by phone number. Re-bookings by the same phone reuse or update the existing customer document.

**Access:** Internal (never exposed directly to public API).

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `name` | string | ✅ | Full name as given |
| `phone` | string | ✅ | E.164 normalized, e.g., `"+917842704429"` |
| `email` | string | ❌ | Optional; validated format |
| `language` | string | ❌ | Preferred: `"en"` or `"te"` |
| `bookingCount` | int | ✅ | Incremented on each confirmed booking |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ phone: 1 }` unique — deduplication key

**Note:** A booking document stores a `customerSnapshot` (name + masked phone) for immutability. The `customers` collection is the mutable live record.

---

## 4. `inquiries`

**Purpose:** Stores pre-booking enquiries submitted via the web form. Reviewed by admin; may be converted to bookings.

**Access:** Public write (POST); admin read/patch.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `name` | string | ✅ | 2–100 chars |
| `phone` | string | ✅ | Raw input from form; admin should normalize before follow-up |
| `preferredDate` | string | ❌ | ISO date string or free text |
| `preferredTime` | string | ❌ | Time string or free text |
| `packageCode` | string | ✅ | One of `"basic"`, `"gold"`, `"diamond"` |
| `durationHours` | int | ✅ | 1–6 |
| `message` | string | ❌ | Free text, max 2000 chars |
| `language` | string | ✅ | `"en"` or `"te"` |
| `source` | string | ✅ | `"website"` or `"whatsapp"` |
| `status` | string | ✅ | enum: `new`, `contacted`, `converted`, `closed` |
| `adminNotes` | string | ❌ | Internal notes added by admin |
| `convertedToBookingId` | ObjectId | ❌ | Set if this inquiry led to a booking |
| `isDeleted` | bool | ✅ | Soft delete |
| `deletedAt` | datetime | ❌ | |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ status: 1, createdAt: -1 }` — admin inquiry list
- `{ phone: 1, createdAt: -1 }` — find by phone
- `{ createdAt: -1 }` — latest-first listing

**Related endpoints:** `POST /api/inquiries`, `GET /api/admin/inquiries`, `PATCH /api/admin/inquiries/:id`

---

## 5. `bookings`

**Purpose:** Core booking record. Created after slot claim succeeds. Confirmed after payment verified.

**Access:** Public read (safe fields only via `bookingReference`); admin read/patch.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `bookingReference` | string | ✅ | Human-readable unique ID, e.g., `"JBX-2026-0042"`. From `counters`. |
| `accessTokenHash` | string | ✅ | SHA-256 hash of the 32-byte client access token. Raw token is never stored. Required for private lookup and cancellation. |
| `roomId` | string | ✅ | `"main"` (or future room ID) |
| `startAt` | datetime | ✅ | UTC start of the booking (customer's chosen time) |
| `endAt` | datetime | ✅ | UTC end (`startAt + durationHours`) |
| `durationHours` | int | ✅ | 1–6 |
| `timezone` | string | ✅ | Always `"Asia/Kolkata"` |
| `bookingStatus` | string | ✅ | enum: `pending_payment`, `confirmed`, `payment_failed`, `expired`, `cancelled`, `completed` |
| `paymentStatus` | string | ✅ | enum: `unpaid`, `paid`, `refunded`, `partially_refunded`, `failed` |
| `paymentMethod` | string | ❌ | `"razorpay"` or `"cash"` |
| **Customer snapshot** | | | Embedded; never changes after creation |
| `customerSnapshot.name` | string | ✅ | Customer name at time of booking |
| `customerSnapshot.phoneMasked` | string | ✅ | Last 4 digits only, e.g., `"****4429"` |
| `customerSnapshot.language` | string | ❌ | |
| `customerId` | ObjectId | ❌ | Reference to `customers._id` |
| **Event details** | | | |
| `occasionType` | string | ✅ | e.g., `"birthday"`, `"anniversary"`, `"surprise"`, `"other"` |
| `celebrantName` | string | ❌ | Name for banner/welcome board |
| `specialRequests` | string | ❌ | max 1000 chars |
| `guestCount` | int | ❌ | Estimated number of guests |
| **Package snapshot** | | | Embedded at booking time; immutable |
| `packageSnapshot.code` | string | ✅ | |
| `packageSnapshot.name` | string | ✅ | |
| `packageSnapshot.pricePerHourMinor` | int | ✅ | |
| `packageSnapshot.features` | [string] | ✅ | |
| **Add-on snapshots** | | | Array of embedded add-on records |
| `addOnSnapshots[].code` | string | ✅ | |
| `addOnSnapshots[].name` | string | ✅ | |
| `addOnSnapshots[].priceMinor` | int | ✅ | |
| **Pricing breakdown** | | | Server-computed at booking time; immutable |
| `pricing.baseAmountMinor` | int | ✅ | package price × hours |
| `pricing.addOnsAmountMinor` | int | ✅ | sum of add-on prices |
| `pricing.discountAmountMinor` | int | ✅ | promo discount if applicable |
| `pricing.taxAmountMinor` | int | ✅ | GST if applicable (0 initially) |
| `pricing.taxRatePercent` | float | ✅ | e.g., `0` or `18.0` |
| `pricing.totalAmountMinor` | int | ✅ | Final amount charged |
| `pricing.currency` | string | ✅ | `"INR"` |
| **Offer link** | | | |
| `offerRedemptionId` | ObjectId | ❌ | If promo was applied |
| `offerId` | ObjectId | ❌ | Reference to the offer |
| **Payment links** | | | |
| `paymentId` | ObjectId | ❌ | Reference to latest `payments._id` |
| `razorpayOrderId` | string | ❌ | Razorpay order ID for this booking |
| **Cancellation** | | | |
| `cancelledAt` | datetime | ❌ | UTC |
| `cancellationReason` | string | ❌ | |
| `cancelledBy` | string | ❌ | `"customer"` or `"admin"` |
| `refundId` | ObjectId | ❌ | Reference to `refunds._id` |
| **Admin** | | | |
| `adminNotes` | string | ❌ | Internal notes |
| `fromInquiryId` | ObjectId | ❌ | Source inquiry if applicable |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ bookingReference: 1 }` unique — public lookup key
- `{ roomId: 1, startAt: 1, endAt: 1, bookingStatus: 1 }` — availability query
- `{ customerId: 1, createdAt: -1 }` — customer history
- `{ bookingStatus: 1, startAt: 1 }` — admin calendar view
- `{ paymentStatus: 1, createdAt: -1 }` — payment reconciliation
- `{ razorpayOrderId: 1 }` sparse — payment lookup

**Sample document (confirmed booking with promo):**
```json
{
  "_id": "507f1f77bcf86cd799439031",
  "bookingReference": "JBX-2026-0001",
  "roomId": "main",
  "startAt": "2026-11-01T03:30:00Z",
  "endAt": "2026-11-01T07:30:00Z",
  "durationHours": 4,
  "timezone": "Asia/Kolkata",
  "bookingStatus": "confirmed",
  "paymentStatus": "paid",
  "paymentMethod": "razorpay",
  "customerSnapshot": {
    "name": "Ravi Kumar",
    "phoneMasked": "****6789",
    "language": "te"
  },
  "customerId": "507f1f77bcf86cd799439001",
  "occasionType": "birthday",
  "celebrantName": "Priya",
  "specialRequests": "Please keep pink balloons",
  "guestCount": 10,
  "packageSnapshot": {
    "code": "basic",
    "name": "Basic",
    "pricePerHourMinor": 99900,
    "features": ["AC room", "Birthday decoration theme", "Music"]
  },
  "addOnSnapshots": [
    { "code": "bubble_entry", "name": "Bubble Machine Entry", "priceMinor": 30000 }
  ],
  "pricing": {
    "baseAmountMinor": 200000,
    "addOnsAmountMinor": 30000,
    "discountAmountMinor": 199600,
    "taxAmountMinor": 0,
    "taxRatePercent": 0,
    "totalAmountMinor": 30400,
    "currency": "INR"
  },
  "offerRedemptionId": "507f1f77bcf86cd799439051",
  "offerId": "507f1f77bcf86cd799439061",
  "paymentId": "507f1f77bcf86cd799439071",
  "razorpayOrderId": "order_ABC123",
  "schemaVersion": 1,
  "createdAt": "2026-10-28T10:00:00Z",
  "updatedAt": "2026-10-28T10:05:00Z"
}
```

---

## 6. `bookingHolds`

**Purpose:** Temporary slot reservation while a customer completes the booking wizard. TTL index cleans up expired holds, but availability queries check `expiresAt > now` explicitly.

**Access:** Internal (created/released by service layer only).

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `roomId` | string | ✅ | |
| `startAt` | datetime | ✅ | UTC |
| `endAt` | datetime | ✅ | UTC (includes customer duration; does NOT include buffer) |
| `expiresAt` | datetime | ✅ | UTC; when the hold expires. TTL index on this field. |
| `status` | string | ✅ | enum: `active`, `converted`, `expired`, `released` |
| `sessionToken` | string | ✅ | Random token returned to the client; used to claim/extend the hold |
| `packageCode` | string | ✅ | Package selected at hold time |
| `convertedToBookingId` | ObjectId | ❌ | Set when hold → confirmed booking |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ expiresAt: 1 }` TTL with `expireAfterSeconds: 0` — automatic cleanup only
- `{ roomId: 1, startAt: 1, endAt: 1, status: 1 }` — availability overlap check
- `{ sessionToken: 1 }` unique — client reference

---

## 7. `slotClaims`

**Purpose:** The **atomic double-booking prevention mechanism.** One document per hourly slot per room. The `UNIQUE` index on `(roomId, slotStart)` means only one booking/hold can own a given slot at a time. This is the source of truth for "is this slot taken?"

**Access:** Internal only. Created atomically by the booking service; never exposed via API.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `roomId` | string | ✅ | |
| `slotStart` | datetime | ✅ | UTC datetime of the slot's start hour. E.g., IST 09:00 = `2026-11-01T03:30:00Z` |
| `ownerId` | ObjectId | ✅ | Reference to `bookings._id` or `bookingHolds._id` |
| `ownerType` | string | ✅ | `"booking"` or `"hold"` or `"buffer"` |
| `expiresAt` | datetime | ❌ | Set for hold-owned claims; TTL-cleaned |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |

**Indexes:**
- `{ roomId: 1, slotStart: 1 }` **UNIQUE** — THE anti-double-booking index
- `{ ownerId: 1 }` — cleanup: find all claims for a booking/hold
- `{ expiresAt: 1 }` TTL `expireAfterSeconds: 0` — cleanup expired hold claims

**How it works:**
- A 2-hour booking (09:00–11:00 IST) + 1hr buffer = 3 slot claims: `09:30Z`, `10:30Z`, `11:30Z` (buffer slot)
- Inserting each claim: if any unique-key violation occurs → roll back all inserted claims → return "slot unavailable"
- Buffer slots use `ownerType: "buffer"` linked to the same booking

---

## 8. `availabilityBlocks`

**Purpose:** Manual blocks set by admin (maintenance, private events, holidays). Overrides all availability.

**Access:** Admin read/write; considered in public availability query.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `roomId` | string | ✅ | |
| `startAt` | datetime | ✅ | UTC |
| `endAt` | datetime | ✅ | UTC |
| `reason` | string | ✅ | Admin description, e.g., `"Maintenance"` |
| `createdByUserId` | ObjectId | ✅ | Admin who created |
| `isEmergency` | bool | ✅ | For emergency blocks (shows differently in admin UI) |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ roomId: 1, startAt: 1, endAt: 1 }` — overlap check in availability query

---

## 9. `offers`

**Purpose:** Configuration for promotional offers. Currently one active offer: Basic at ₹500/hr for first 5 monthly bookings.

**Access:** Public read (active offers only); admin read/write.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `name` | string | ✅ | e.g., `"Basic Introductory Offer"` |
| `nameTe` | string | ❌ | |
| `description` | string | ✅ | |
| `eligiblePackageCode` | string | ✅ | Only `"basic"` |
| `promoPricePerHourMinor` | int | ✅ | `50000` (₹500) |
| `monthlyLimit` | int | ✅ | `5` |
| `monthlyRedemptionCount` | int | ✅ | Current month's redemptions. Atomically incremented. |
| `currentPeriodKey` | string | ✅ | `"2026-11"` format (YYYY-MM). Resets on new month. |
| `isActive` | bool | ✅ | Admin toggle |
| `startsAt` | datetime | ❌ | UTC; null = always active |
| `endsAt` | datetime | ❌ | UTC; null = no expiry |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ isActive: 1 }` — public active offer lookup
- `{ eligiblePackageCode: 1, isActive: 1 }` — eligibility check

**Atomic quota decrement (Python):**
```python
result = db.offers.find_one_and_update(
    {
        "_id": offer_id,
        "isActive": True,
        "currentPeriodKey": current_period_key,
        "monthlyRedemptionCount": {"$lt": offer["monthlyLimit"]}
    },
    {"$inc": {"monthlyRedemptionCount": 1}, "$set": {"updatedAt": utcnow()}},
    return_document=True
)
# If result is None → quota exhausted → charge regular price
```

---

## 10. `offerRedemptions`

**Purpose:** One document per promo-priced booking. Links the booking, offer, and period; enables release on cancellation.

**Access:** Internal; admin read.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `offerId` | ObjectId | ✅ | Reference to `offers._id` |
| `bookingId` | ObjectId | ✅ | Reference to `bookings._id`. Unique — one redemption per booking. |
| `periodKey` | string | ✅ | `"2026-11"` — the month this redemption counted against |
| `promoPricePerHourMinor` | int | ✅ | Promo price snapshotted at redemption |
| `regularPricePerHourMinor` | int | ✅ | Regular price at time of booking |
| `discountAmountMinor` | int | ✅ | Total saving in paise |
| `status` | string | ✅ | `"active"` or `"released"` (on cancel) |
| `releasedAt` | datetime | ❌ | UTC; set if released |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ holdId: 1 }` sparse unique — one reservation per hold
- `{ bookingId: 1 }` sparse unique — one redemption per converted booking
- `{ offerId: 1, periodKey: 1, status: 1 }` — count active redemptions for a period

---

## 11. `payments`

**Purpose:** Records every payment attempt and its lifecycle.

**Access:** Admin read; internal write.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `bookingId` | ObjectId | ✅ | |
| `bookingReference` | string | ✅ | Denormalized for quick lookup |
| `provider` | string | ✅ | `"razorpay"` or `"cash"` |
| `providerOrderId` | string | ❌ | Razorpay `order_xxx` |
| `providerPaymentId` | string | ❌ | Razorpay `pay_xxx`; set after payment |
| `providerSignature` | string | ❌ | HMAC signature from Razorpay |
| `amountMinor` | int | ✅ | In paise |
| `currency` | string | ✅ | `"INR"` |
| `status` | string | ✅ | enum: `created`, `authorized`, `captured`, `failed`, `refunded` |
| `idempotencyKey` | string | ✅ | Client-supplied idempotency key |
| `webhookEventId` | string | ❌ | Razorpay webhook event ID (for dedup) |
| `metadata` | object | ❌ | Raw provider response (sanitized; no secrets) |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ bookingId: 1, createdAt: -1 }` — payments for a booking
- `{ bookingReference: 1, createdAt: -1 }` — fast query by booking code
- `{ providerOrderId: 1 }` sparse unique — Razorpay order lookup
- `{ providerPaymentId: 1 }` sparse unique — Razorpay payment lookup
- `{ idempotencyKey: 1 }` sparse unique — payment creation idempotency

**Never store:** Card numbers, CVV, UPI PIN, full bank account details.

---

## 12. `refunds`

**Purpose:** Tracks refund requests and their Razorpay processing status.

**Access:** Admin read/write; internal write.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `bookingId` | ObjectId | ✅ | |
| `bookingReference` | string | ✅ | Denormalized for fast status lookup |
| `paymentId` | ObjectId | ✅ | The original payment being refunded |
| `provider` | string | ✅ | `"razorpay"` or `"cash"` |
| `providerRefundId` | string | ❌ | Razorpay `rfnd_xxx` |
| `providerPaymentId` | string | ❌ | Razorpay `pay_xxx` |
| `amountMinor` | int | ✅ | In paise |
| `reason` | string | ✅ | Cancellation reason / policy tier |
| `status` | string | ✅ | enum: `pending`, `processing`, `processed`, `failed` |
| `idempotencyKey` | string | ❌ | Client-supplied idempotency key |
| `processedAt` | datetime | ❌ | UTC |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ bookingId: 1 }` — refunds for a booking
- `{ bookingReference: 1 }` — fast query by booking code
- `{ providerRefundId: 1 }` sparse unique
- `{ idempotencyKey: 1 }` sparse unique

---

## 13. `users`

**Purpose:** Admin accounts only. No public registration. Created by script.

**Access:** Admin auth only.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `username` | string | ✅ | Unique. Lowercase. |
| `email` | string | ✅ | Unique. |
| `passwordHash` | string | ✅ | bcrypt hash. Never exposed in API. |
| `role` | string | ✅ | enum: `super_admin`, `staff` |
| `displayName` | string | ✅ | e.g., `"Kiran Kumar"` |
| `isActive` | bool | ✅ | `false` = deactivated account |
| `lastLoginAt` | datetime | ❌ | UTC |
| `failedLoginAttempts` | int | ✅ | For lockout logic |
| `lockedUntil` | datetime | ❌ | UTC; temporary lockout |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ username: 1 }` unique
- `{ email: 1 }` unique

**Never exposed fields:** `passwordHash`, `failedLoginAttempts`, `lockedUntil`.

---

## 14. `galleryAssets`

**Purpose:** Metadata for gallery images served by `GET /api/gallery`. Actual image files are in Cloudinary/S3.

**Access:** Public read; admin write.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `url` | string | ✅ | CDN URL of the image |
| `thumbnailUrl` | string | ❌ | Smaller version |
| `altText` | string | ✅ | English alt text for accessibility |
| `altTextTe` | string | ❌ | Telugu alt text |
| `caption` | string | ❌ | Display caption |
| `captionTe` | string | ❌ | |
| `category` | string | ✅ | e.g., `"kids"`, `"couples"`, `"teen_adult"`, `"general"` |
| `themeTag` | string | ❌ | e.g., `"peppa_pig"`, `"neon_21st"` |
| `displayOrder` | int | ✅ | |
| `isActive` | bool | ✅ | |
| `uploadedByUserId` | ObjectId | ✅ | |
| `storageKey` | string | ✅ | Object storage key (internal — never expose in public API) |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ isActive: 1, category: 1, displayOrder: 1 }` — filtered gallery listing
- `{ category: 1, isActive: 1 }` — category filter

---

## 15. `faqs`

**Purpose:** FAQ accordion content served by `GET /api/faqs`.

**Access:** Public read; admin write.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `question` | string | ✅ | |
| `questionTe` | string | ❌ | |
| `answer` | string | ✅ | |
| `answerTe` | string | ❌ | |
| `category` | string | ❌ | e.g., `"booking"`, `"pricing"`, `"venue"` |
| `displayOrder` | int | ✅ | |
| `isActive` | bool | ✅ | |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ isActive: 1, displayOrder: 1 }`

---

## 16. `reviews`

**Purpose:** Customer reviews/testimonials. Moderated by admin before display.

**Access:** Public read (approved only); admin read/patch.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `authorName` | string | ✅ | First name + last initial only (privacy) |
| `rating` | int | ✅ | 1–5 |
| `body` | string | ✅ | max 500 chars |
| `bodyTe` | string | ❌ | Telugu version |
| `occasion` | string | ❌ | e.g., `"Birthday"` |
| `status` | string | ✅ | enum: `pending`, `approved`, `hidden` |
| `bookingId` | ObjectId | ❌ | If linked to a verified booking |
| `reviewedByUserId` | ObjectId | ❌ | Admin who approved/hid |
| `displayOrder` | int | ❌ | Manual override of display order |
| `isActive` | bool | ✅ | Derived from status == approved |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ status: 1, displayOrder: 1 }` — public listing of approved reviews

---

## 17. `notifications`

**Purpose:** Outbound notification log (WhatsApp/SMS/email send attempts — future feature).

**Access:** Internal; admin read.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `bookingId` | ObjectId | ❌ | |
| `recipientPhone` | string | ✅ | E.164 (masked in logs) |
| `channel` | string | ✅ | `"whatsapp"`, `"sms"`, `"email"` |
| `templateKey` | string | ✅ | e.g., `"booking_confirmed"` |
| `status` | string | ✅ | `"pending"`, `"sent"`, `"failed"` |
| `providerResponse` | object | ❌ | Sanitized provider response |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ bookingId: 1, createdAt: -1 }`
- `{ status: 1, createdAt: -1 }` — retry queue

---

## 18. `auditLogs`

**Purpose:** Immutable record of every admin mutation and sensitive system event. Never deleted.

**Access:** Admin read (super_admin only); internal write.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `actorId` | ObjectId | ❌ | Admin `users._id`; null for system actions |
| `actorType` | string | ✅ | `"admin"` or `"system"` |
| `action` | string | ✅ | e.g., `"booking.status_changed"`, `"offer.price_updated"` |
| `targetCollection` | string | ✅ | e.g., `"bookings"` |
| `targetId` | ObjectId | ✅ | `_id` of the changed document |
| `diff` | object | ❌ | `{before: {...}, after: {...}}` — only changed fields |
| `ipAddress` | string | ❌ | Hashed or omitted for privacy |
| `requestId` | string | ❌ | Trace ID |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | UTC |

**Indexes:**
- `{ targetCollection: 1, targetId: 1, createdAt: -1 }` — history for a document
- `{ actorId: 1, createdAt: -1 }` — admin activity
- `{ createdAt: -1 }` — chronological feed

**Never expose** `ipAddress` or `diff` in public API.

---

## 19. `webhookEvents`

**Purpose:** Deduplication store for incoming Razorpay webhook events. Idempotency — processing the same event twice does nothing.

**Access:** Internal only.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `provider` | string | ✅ | `"razorpay"` |
| `eventId` | string | ✅ | Provider event ID. Unique. |
| `eventType` | string | ✅ | e.g., `"payment.captured"` |
| `payload` | object | ✅ | Raw (sanitized) event payload |
| `status` | string | ✅ | `"received"`, `"processed"`, `"ignored"`, `"failed"` |
| `processingError` | string | ❌ | Error message if status=failed |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `{ provider: 1, eventId: 1 }` unique — deduplication key
- `{ status: 1, createdAt: -1 }` — retry failed events

---

## 20. `idempotencyKeys`

**Purpose:** Prevents duplicate booking/payment mutations from duplicate HTTP requests.

**Access:** Internal only.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `key` | string | ✅ | Client-supplied UUID. Unique per operation type. |
| `operationType` | string | ✅ | e.g., `"create_booking"`, `"create_payment_order"` |
| `responseSnapshot` | object | ✅ | The response returned on first request; replayed on duplicate |
| `expiresAt` | datetime | ✅ | UTC; TTL-cleaned after 24 hours |
| `schemaVersion` | int | ✅ | |
| `createdAt` | datetime | ✅ | |

**Indexes:**
- `{ key: 1, operationType: 1 }` unique — deduplication key
- `{ expiresAt: 1 }` TTL `expireAfterSeconds: 0`

---

## 21. `counters`

**Purpose:** Auto-incrementing sequences for human-readable IDs (e.g., `JBX-2026-0042`).

**Access:** Internal only (findAndModify for atomic increment).

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | string | ✅ | Counter name, e.g., `"booking_reference_2026"` |
| `seq` | int | ✅ | Current sequence value. Atomically incremented. |
| `prefix` | string | ✅ | e.g., `"JBX-2026-"` |
| `updatedAt` | datetime | ✅ | |

**Indexes:**
- `_id` is the unique key (default `_id` index)

**Usage (Python):**
```python
result = db.counters.find_one_and_update(
    {"_id": "booking_reference_2026"},
    {"$inc": {"seq": 1}, "$set": {"updatedAt": utcnow()}},
    upsert=True,
    return_document=True
)
booking_ref = f"JBX-2026-{result['seq']:04d}"  # e.g., "JBX-2026-0042"
```

---

## MongoDB JSON Schema Validators (key collections)

These are the validators to apply at the Atlas or PyMongo level using `collMod`:

### packages validator
```json
{
  "$jsonSchema": {
    "bsonType": "object",
    "required": ["code", "name", "pricePerHourMinor", "currency", "features", "isActive", "displayOrder"],
    "properties": {
      "code": { "bsonType": "string", "pattern": "^[a-z_]+$" },
      "pricePerHourMinor": { "bsonType": "int", "minimum": 1 },
      "currency": { "bsonType": "string", "enum": ["INR"] },
      "isActive": { "bsonType": "bool" },
      "displayOrder": { "bsonType": "int", "minimum": 1 }
    }
  }
}
```

### bookings validator (key fields)
```json
{
  "$jsonSchema": {
    "bsonType": "object",
    "required": ["bookingReference", "roomId", "startAt", "endAt", "durationHours", "bookingStatus", "paymentStatus"],
    "properties": {
      "durationHours": { "bsonType": "int", "minimum": 1, "maximum": 6 },
      "bookingStatus": { "enum": ["pending_payment", "confirmed", "payment_failed", "expired", "cancelled", "completed"] },
      "paymentStatus": { "enum": ["unpaid", "paid", "refunded", "partially_refunded", "failed"] },
      "pricing.totalAmountMinor": { "bsonType": "int", "minimum": 0 }
    }
  }
}
```

### slotClaims validator
```json
{
  "$jsonSchema": {
    "bsonType": "object",
    "required": ["roomId", "slotStart", "ownerId", "ownerType"],
    "properties": {
      "ownerType": { "enum": ["booking", "hold", "buffer"] }
    }
  }
}
```

---

## 22. `rateLimits`

**Purpose:** Tracks request frequency per IP and per customer phone to prevent slot hoarding and denial-of-service attempts. Uses TTL index for automatic expiration.

**Access:** Internal write/read by service layer only.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | |
| `key` | string | ✅ | Unique key, e.g. `hold_ip:192.168.1.1` or `hold_phone:9876543210` |
| `count` | int | ✅ | Number of requests received within the active window |
| `createdAt` | datetime | ✅ | UTC timestamp of the first request in the window |
| `expiresAt` | datetime | ✅ | UTC timestamp when this rate limit record expires and resets. TTL index. |

**Indexes:**
- `{ key: 1 }` **UNIQUE**
- `{ expiresAt: 1 }` TTL `expireAfterSeconds: 0`

---

## 23. `users`

**Purpose:** Administrative staff, manager, and owner accounts with bcrypt password hashes, RBAC roles, and account lockout tracking.

**Access:** Internal admin auth and user management only. Never exposed in public APIs.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | Primary identifier |
| `username` | string | ✅ | Lowercase unique username (min 3, max 50) |
| `email` | string | ✅ | Unique email address |
| `passwordHash` | string | ✅ | Bcrypt password hash (cost factor >= 12) |
| `role` | string | ✅ | `"owner"`, `"manager"`, or `"staff"` |
| `isActive` | bool | ✅ | Active status flag (inactive users cannot log in) |
| `failedLoginAttempts` | int | ✅ | Number of consecutive failed logins (resets on success) |
| `lockoutUntil` | datetime | ❌ | Lockout timestamp if >= 5 failed attempts within window |
| `lastLoginAt` | datetime | ❌ | UTC timestamp of most recent successful login |
| `createdAt` | datetime | ✅ | Account creation timestamp |
| `updatedAt` | datetime | ✅ | Last update timestamp |

**Indexes:**
- `{ username: 1 }` **UNIQUE**
- `{ email: 1 }` **UNIQUE**

---

## 24. `adminSessions`

**Purpose:** Active server-managed administrative sessions with cryptographically secure token hashes, dual expiry (idle + absolute), and CSRF tokens.

**Access:** Internal session middleware only.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | Primary identifier |
| `userId` | ObjectId | ✅ | Reference to `users._id` |
| `tokenHash` | string | ✅ | SHA-256 hash of the 256-bit opaque cookie token |
| `csrfToken` | string | ✅ | Cryptographic CSRF token matched against `X-CSRF-Token` header |
| `role` | string | ✅ | Cached user role at session creation |
| `createdAt` | datetime | ✅ | UTC timestamp of session creation |
| `lastAccessedAt` | datetime | ✅ | UTC timestamp of most recent request (for idle timeout) |
| `expiresAt` | datetime | ✅ | Absolute expiration timestamp (8 hours from creation) |
| `idleExpiresAt` | datetime | ✅ | Idle expiration timestamp (30 minutes from last activity) |
| `ipAddress` | string | ❌ | Client IP address at session creation |
| `userAgent` | string | ❌ | Browser User-Agent string |
| `revokedAt` | datetime | ❌ | Timestamp of explicit logout or administrative revocation |

**Indexes:**
- `{ tokenHash: 1 }` **UNIQUE**
- `{ userId: 1, revokedAt: 1 }`
- `{ expiresAt: 1 }` TTL `expireAfterSeconds: 0`

---

## 25. `auditLogs`

**Purpose:** Append-only tamper-evident audit trail of all administrative and privileged actions.

**Access:** Append-only for all state mutations; read-only for owner and manager roles.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | Primary identifier |
| `actorId` | ObjectId | ✅ | User ID of the administrator performing the action |
| `actorUsername` | string | ✅ | Username of actor at execution time |
| `actorRole` | string | ✅ | Role of actor at execution time |
| `action` | string | ✅ | Standard action code (e.g., `BOOKING_CANCEL`, `OFFLINE_BOOKING_CREATE`, `PRICE_UPDATE`, `REFUND_PROCESS`, `AVAILABILITY_BLOCK_CREATE`) |
| `targetCollection` | string | ✅ | Name of affected collection (`bookings`, `payments`, etc.) |
| `targetId` | string / ObjectId | ✅ | Reference or ID of affected document |
| `details` | object | ✅ | Structured details of the changes or operation parameters |
| `requestId` | string | ❌ | Trace / correlation ID |
| `ipAddress` | string | ❌ | Originating client IP |
| `createdAt` | datetime | ✅ | UTC timestamp |

**Indexes:**
- `{ targetCollection: 1, targetId: 1, createdAt: -1 }`
- `{ actorId: 1, createdAt: -1 }`
- `{ createdAt: -1 }`

---

## 26. `availabilityBlocks`

**Purpose:** Manually designated maintenance, holiday, or operational blockouts that prevent booking reservations on specific time windows.

**Access:** Admin manage; reflected in public slot availability calculations.

| Field | Type | Req | Notes |
|---|---|---|---|
| `_id` | ObjectId | ✅ | Primary identifier |
| `roomId` | string | ✅ | Room blocked (e.g. `"main"`) |
| `startAt` | datetime | ✅ | Block window start in UTC |
| `endAt` | datetime | ✅ | Block window end in UTC |
| `reason` | string | ✅ | Description (e.g. `"Deep cleaning"`, `"Private maintenance"`) |
| `createdBy` | ObjectId | ✅ | Admin user ID who created the block |
| `createdAt` | datetime | ✅ | UTC timestamp |
| `updatedAt` | datetime | ✅ | UTC timestamp |

**Indexes:**
- `{ roomId: 1, startAt: 1, endAt: 1 }`


