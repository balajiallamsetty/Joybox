# UI-TO-API MAPPING — Joybox Party Room
**Phase 1 · Read-only audit · 2026-10-28**

Every UI element that reads or writes data is mapped to the API endpoint it needs, the MongoDB collection(s) it touches, and the current implementation status.

---

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | Endpoint exists and works |
| ⚠️ | Endpoint exists but uses hard-coded data (not DB) |
| ❌ | Endpoint missing — must be built |
| 🔒 | Requires admin auth |
| 📖 | Read-only (GET) |
| ✏️ | Write (POST/PATCH/DELETE) |

---

## Page: Landing Page (`/`)
**Stitch source:** `joybox_party_room_celebration_landing_page_1/code.html` + `joybox_party_room_celebration_landing_page_2/code.html`

### Announcement Banner (top strip)
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Offer text: "Basic Package at ₹500/hr for first 5 monthly bookings" | Offer name, promo price, limit count | `GET /api/offers/active` | `offers` | ❌ Missing |
| "Only 2 of 5 slots remaining" counter | `monthlyRedemptionCount` vs `monthlyLimit` | `GET /api/offers/active` | `offers`, `offerRedemptions` | ❌ Missing |

### Sticky Navigation Header
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Logo image | Static asset | — (static file) | — | N/A |
| "Book Now" CTA | — | → navigates to `/book` | — | N/A |
| WhatsApp button | Phone number `+91 78427 04429` | Static `wa.me` link | — | N/A |
| Call button | Phone number | Static `tel:` link | — | N/A |
| Language toggle (EN / తెలుగు) | Current locale | Client-side state only | — | N/A |

### Hero Section
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Promo pill ("Basic at ₹500/hr, First 5 Bookings") | Offer active status, promo price | `GET /api/offers/active` | `offers` | ❌ Missing |
| "Check Live Availability & Slots" button | — | → navigates to `#booking-calculator` or `/book` | — | N/A |
| Hero image | AI-generated CDN placeholder | Static asset (future: real venue photo) | `galleryAssets` | N/A |

### Packages Grid (3 cards)
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Package name, price, features | `name`, `pricePerHourMinor`, `features[]` | `GET /api/packages` | `packages` | ⚠️ Hard-coded |
| Offer badge ("Offer ₹500/hr") on Basic card | Promo price | `GET /api/offers/active` | `offers` | ❌ Missing |
| "Select [Package]" → navigates to estimator | — | Client-side state | — | N/A |

### Add-on Highlights Grid
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Add-on name, description, price | `name`, `description`, `priceMinor` | `GET /api/add-ons` | `addOns` | ❌ Missing |

### Interactive Price Estimator Calculator
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Package tier buttons (Basic/Gold/Diamond) | Package options | `GET /api/packages` | `packages` | ⚠️ Hard-coded |
| Hours slider (1–6 hours) | Client-side input | — | — | N/A |
| Add-on checkboxes | Add-on options and prices | `GET /api/add-ons` | `addOns` | ❌ Missing |
| "Summary Breakdown" live total | Computed total | `POST /api/bookings/quote` | (stateless calculation) | ⚠️ Uses hard-coded prices |
| "Proceed to Reserve Date & Slot" | — | → navigates to `/book` | — | N/A |

### Photo Gallery Strip
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| 4 gallery images (bento grid) | `url`, `altText`, `themeTag` | `GET /api/gallery` | `galleryAssets` | ❌ Missing |
| "Explore All 20+ Themes" link | — | → navigates to `/gallery` | — | N/A |

### Customer Reviews Strip (implied — not explicitly in landing_page_1 HTML read, but part of design system)
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Star rating, review text, name | `rating`, `body`, `authorName` | `GET /api/reviews` (proposed) | `reviews` | ❌ Missing |

---

## Page: Packages & Add-ons (`/packages`)
**Stitch source:** `joybox_party_room_redesigned_packages_add_ons/code.html`

| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Live offer promo strip | Offer price, remaining slots | `GET /api/offers/active` | `offers`, `offerRedemptions` | ❌ Missing |
| 3 package cards (Basic, Gold, Diamond) | Full package details | `GET /api/packages` | `packages` | ⚠️ Hard-coded |
| "Most Popular" ribbon on Gold | `isFeatured` flag | `GET /api/packages` | `packages` | ⚠️ Hard-coded |
| 3 add-on cards | `name`, `description`, `priceMinor` | `GET /api/add-ons` | `addOns` | ❌ Missing |
| Package features include/exclude marks | `features[]`, `excludes[]` | `GET /api/packages` | `packages` | ⚠️ Hard-coded |
| "Book [Package]" CTA → booking wizard | Passes selected package code | → navigates to `/book?package=gold` | — | N/A |
| FAQ accordion (implied) | `question`, `answer` | `GET /api/faqs` | `faqs` | ❌ Missing |

---

## Page: Book Venue – 4-Step Booking Wizard (`/book`)
**Stitch source:** `joybox_party_room_4_step_celebration_booking_engine/code.html` + mobile variants

### Step 1: Date & Slot Selection
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Calendar date picker | Available dates | `GET /api/availability?date=YYYY-MM-DD&roomId=...` | `bookings`, `bookingHolds`, `availabilityBlocks` | ❌ Missing |
| Time slot grid | Available start times, slot duration options | `GET /api/availability` | same | ❌ Missing |
| "Hold slot for 10 minutes" (on selection) | Creates a booking hold | `POST /api/bookings/hold` (proposed) | `bookingHolds`, `slotClaims` | ❌ Missing |
| Countdown timer (10 min hold) | Hold expiry time | Client-side timer from server `expiresAt` | — | N/A |

### Step 2: Package & FX Selection
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Package radio buttons | Package list | `GET /api/packages` | `packages` | ⚠️ Hard-coded |
| Add-on checkboxes | Add-on list | `GET /api/add-ons` | `addOns` | ❌ Missing |
| Live price summary | Computed total | `POST /api/bookings/quote` | (stateless) | ⚠️ Hard-coded prices |
| Offer eligibility indicator | Whether promo applies | `POST /api/bookings/quote` (include offer check) | `offers`, `offerRedemptions` | ❌ Missing |

### Step 3: Celebrant Info
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Name input | Customer name | — (collected for step 4) | — | N/A |
| Phone input | Customer phone | — (collected for step 4) | — | N/A |
| Celebrant name input | For name banner/welcome board | — (collected for step 4) | — | N/A |
| Occasion type select | Occasion | — (collected for step 4) | — | N/A |
| Special requests textarea | Free text | — (collected for step 4) | — | N/A |
| Terms checkbox | Acceptance | — | — | N/A |

### Step 4: Verification & Advance Payment
| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Final price summary (read from server) | Authoritative total | `POST /api/bookings/quote` | (stateless) | ⚠️ Hard-coded |
| "Lock & Pay Advance" button | — | `POST /api/bookings` → then `POST /api/payments/create-order` | `bookings`, `slotClaims`, `payments` | ❌ Missing |
| Razorpay checkout modal | Payment | Razorpay SDK (public key from `VITE_RAZORPAY_KEY_ID`) | — | ❌ Missing |
| Payment verification (on success callback) | — | `POST /api/payments/verify` | `payments`, `bookings` | ❌ Missing |
| Idempotency key | Prevents duplicate bookings | Request header | `idempotencyKeys` | ❌ Missing |

---

## Page: Booking Status (`/booking/:bookingReference`)
**Stitch source:** `joybox_party_room_booking_confirmation_status/code.html`

| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| **State 1: Confirmed** — Booking details | `bookingReference`, date, time, package, celebrant, total paid | `GET /api/bookings/:bookingReference` | `bookings` | ❌ Missing |
| **State 2: Inquiry Review** — Status pending | `bookingStatus: inquiry_review` | `GET /api/bookings/:bookingReference` | `bookings` | ❌ Missing |
| **State 3: Pay Token** — Advance payment pending | Payment amount due, Razorpay CTA | `GET /api/bookings/:bookingReference` + `POST /api/payments/create-order` | `bookings`, `payments` | ❌ Missing |
| **State 4: Session Failed/Expired** — Re-book option | `bookingStatus: expired` | `GET /api/bookings/:bookingReference` | `bookings` | ❌ Missing |
| WhatsApp CTA (help) | Pre-filled message with booking ref | Static `wa.me` link with ref | — | N/A |
| "Secure Hash Token" / private URL | Booking reference in URL path | — (URL-based, no separate auth) | — | N/A |

> **Security note:** Public booking status lookup (`GET /api/bookings/:ref`) must **never** return sensitive customer data (full phone number, payment details). Return only display-safe fields.

---

## Page: Gallery & Themes (`/gallery`)
**Stitch source:** `joybox_party_room_gallery_themes/code.html`

| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Gallery photo grid | `url`, `altText`, `themeTag`, `category` | `GET /api/gallery` | `galleryAssets` | ❌ Missing |
| Category filter tabs (Kids, Couples, Teen, etc.) | Category list | `GET /api/gallery` (with `?category=` filter) | `galleryAssets` | ❌ Missing |
| Stats strip ("500+ Parties", "20+ Themes") | Marketing counters | `GET /api/gallery` (metadata) or hard-coded | `galleryAssets` | ❌ Missing |
| "Check Date Availability" CTA | — | → navigates to `/book` | — | N/A |
| WhatsApp "Ask about theme" button | Pre-filled message | Static `wa.me` link | — | N/A |

---

## Page: Contact & Location (`/contact`)
**Stitch source:** `joybox_party_room_contact_location/code.html`

| UI Element | Data Shown | API Endpoint | Collection | Status |
|---|---|---|---|---|
| Address: "Beside Durga Mart, Vadlamudi, Guntur, AP" | Static business info | — (static content) | — | N/A |
| Operating hours: "9:00 AM – 11:30 PM · All 7 days" | Opening hours | `GET /api/business-info` (proposed) or static config | — | ❓ Unconfirmed |
| Phone CTA (`tel:+917842704429`) | Static | — | — | N/A |
| WhatsApp CTA | Static `wa.me` link | — | — | N/A |
| Google Maps embed | Static iframe | — | — | N/A |
| Inquiry / contact form (if present on this page) | Name, phone, message | `POST /api/inquiries` | `inquiries` | ✅ Working |
| "10 Mins from Vignan's University" tagline | Static marketing copy | — | — | N/A |

---

## Page: Admin Console (`/admin`)
**Stitch source:** `joybox_admin_operations_reservation_console/code.html`

> 🔒 All admin endpoints require authentication. Admin login screen is **missing** from Stitch exports — must be added.

### Admin Sidebar Navigation → Sections
| Sidebar Item | Purpose | Admin Endpoint | Collection | Status |
|---|---|---|---|---|
| Dashboard & KPIs | Revenue, bookings count, occupancy, promo usage | `GET /api/admin/dashboard` | `bookings`, `payments`, `offerRedemptions` | 🔒 ✅ Built & Verified |
| Schedule & Calendar | View/manage bookings by date | `GET /api/admin/bookings?date=...` | `bookings`, `bookingHolds`, `availabilityBlocks` | 🔒 ✅ Built & Verified |
| Inquiries & Leads | Review and manage inquiries | `GET /api/admin/inquiries`, `PATCH /api/admin/inquiries/:id` | `inquiries`, `auditLogs` | 🔒 ✅ Built & Verified |
| Package Pricing & Quotas | Edit package prices, manage offer limits | `GET/PATCH /api/admin/packages`, `GET/PATCH /api/admin/add-ons` | `packages`, `addOns`, `auditLogs` | 🔒 ✅ Built & Verified |
| Hall Blocks & Slots | Atomically block/release room slots | `GET/POST/DELETE /api/admin/availability-blocks` | `availabilityBlocks`, `slotClaims`, `auditLogs` | 🔒 ✅ Built & Verified |
| Payments & Refunds | Inspect transactions, retry refunds | `GET /api/admin/payments`, `POST /api/admin/payments/:id/retry-refund` | `payments`, `refunds`, `auditLogs` | 🔒 ✅ Built & Verified |
| System Audit Trail | Immutable audit trail for owner/manager | `GET /api/admin/audit-logs` | `auditLogs` | 🔒 ✅ Built & Verified |

### Admin Dashboard KPI Cards
| KPI Shown | Data Source | Admin Endpoint | Status |
|---|---|---|---|
| Today's Bookings | Count of bookings scheduled today | `GET /api/admin/dashboard` | 🔒 ✅ Built & Verified |
| Monthly Revenue | Sum of confirmed advance payments | `GET /api/admin/dashboard` | 🔒 ✅ Built & Verified |
| Promo Quota Usage (X of 5) | `offerRedemptions.count` for current month | `GET /api/admin/dashboard` | 🔒 ✅ Built & Verified |
| Pending Inquiries count | Count of `status: new` inquiries | `GET /api/admin/dashboard` | 🔒 ✅ Built & Verified |

### Admin Auth
| UI Element | Data Shown | Admin Endpoint | Status |
|---|---|---|---|
| Login screen (`/admin/login`) | Username + password form with rate limiting | `POST /api/admin/auth/login` | 🔒 ✅ Built & Verified |
| Logout | Revokes session & clears cookie | `POST /api/admin/auth/logout` | 🔒 ✅ Built & Verified |
| Current admin user display | `username`, `displayName`, `role` | `GET /api/admin/auth/me` | 🔒 ✅ Built & Verified |
| Password change modal | Current + new password | `POST /api/admin/auth/change-password` | 🔒 ✅ Built & Verified |

---

## Complete Public API Endpoint Summary

| Endpoint | Method | UI Consumer | Collection(s) | Status |
|---|---|---|---|---|
| `/api/health` | GET | Dev/ops | — | ✅ Built & Verified |
| `/api/packages` | GET | Landing, Packages, Booking pages | `packages` | ✅ Built & Verified |
| `/api/packages/:slug` | GET | Individual package detail | `packages` | ✅ Built & Verified |
| `/api/add-ons` | GET | Landing, Packages, Booking pages | `addOns` | ✅ Built & Verified |
| `/api/offers/active` | GET | Offer banner, Package cards, Estimator | `offers`, `offerRedemptions` | ✅ Built & Verified |
| `/api/availability` | GET | Step 1 of booking wizard | `bookings`, `bookingHolds`, `availabilityBlocks` | ✅ Built & Verified |
| `/api/bookings/quote` | POST | Price estimator, Booking steps 2+4 | `packages`, `addOns`, `offers` | ✅ Built & Verified |
| `/api/bookings` | POST | Booking wizard step 4 | `bookings`, `slotClaims`, `customers` | ✅ Built & Verified |
| `/api/bookings/:ref` | GET | Booking status page | `bookings` | ✅ Built & Verified |
| `/api/bookings/:ref/cancel` | POST | Booking status page (cancel CTA) | `bookings`, `slotClaims` | ✅ Built & Verified |
| `/api/inquiries` | POST | Inquiry form (landing, contact) | `inquiries` | ✅ Built & Verified |
| `/api/payments/create-order` | POST | Booking step 4, Status "Pay Token" | `payments`, `bookings` | ✅ Built & Verified |
| `/api/payments/verify` | POST | Razorpay callback handler | `payments`, `bookings` | ✅ Built & Verified |
| `/api/payments/webhook` | POST | Razorpay server webhook | `webhookEvents`, `payments`, `bookings` | ✅ Built & Verified |
| `/api/payments/refund` | POST | Customer booking cancel | `refunds`, `payments`, `bookings` | ✅ Built & Verified |

## Complete Admin API Endpoint Summary

| Endpoint | Method | UI Consumer | Collection(s) | Status |
|---|---|---|---|---|
| `/api/admin/auth/login` | POST | Admin login screen | `users`, `adminSessions` | 🔒 ✅ Built & Verified |
| `/api/admin/auth/logout` | POST | Admin console header | `adminSessions` | 🔒 ✅ Built & Verified |
| `/api/admin/auth/me` | GET | AdminProtectedRoute | `users`, `adminSessions` | 🔒 ✅ Built & Verified |
| `/api/admin/auth/change-password` | POST | Admin console modal | `users`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/dashboard` | GET | Admin dashboard KPIs | `bookings`, `payments`, `offerRedemptions`, `inquiries` | 🔒 ✅ Built & Verified |
| `/api/admin/bookings` | GET | Schedule & Calendar | `bookings` | 🔒 ✅ Built & Verified |
| `/api/admin/bookings` | POST | Manual booking modal | `bookings`, `slotClaims`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/bookings/:ref` | GET | Booking details modal | `bookings`, `payments`, `refunds` | 🔒 ✅ Built & Verified |
| `/api/admin/bookings/:ref` | PATCH | Status change / notes | `bookings`, `slotClaims`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/availability-blocks` | GET | Hall blocks tab | `availabilityBlocks` | 🔒 ✅ Built & Verified |
| `/api/admin/availability-blocks` | POST | Create hall block | `availabilityBlocks`, `slotClaims`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/availability-blocks/:id` | DELETE | Release hall block | `availabilityBlocks`, `slotClaims`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/inquiries` | GET | Inquiries & Leads | `inquiries` | 🔒 ✅ Built & Verified |
| `/api/admin/inquiries/:id` | PATCH | Inquiry status update | `inquiries`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/packages` | GET | Catalog tab | `packages` | 🔒 ✅ Built & Verified |
| `/api/admin/packages` | POST | Create package (owner) | `packages`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/packages/:id` | PATCH | Update package price | `packages`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/add-ons` | GET | Catalog tab | `addOns` | 🔒 ✅ Built & Verified |
| `/api/admin/add-ons` | POST | Create add-on | `addOns`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/add-ons/:id` | PATCH | Update add-on | `addOns`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/payments` | GET | Payments tab | `payments` | 🔒 ✅ Built & Verified |
| `/api/admin/payments/:id/retry-refund` | POST | Payments retry button | `payments`, `refunds`, `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/audit-logs` | GET | Audit logs tab | `auditLogs` | 🔒 ✅ Built & Verified |
| `/api/admin/reviews/:id` | PATCH | Approve/hide | `reviews`, `auditLogs` | 🔒 ❌ |
| `/api/admin/availability-blocks` | GET | Schedule & Calendar | `availabilityBlocks` | 🔒 ❌ |
| `/api/admin/availability-blocks` | POST | Block time range / emergency | `availabilityBlocks`, `auditLogs` | 🔒 ❌ |
| `/api/admin/availability-blocks/:id` | DELETE | Remove block | `availabilityBlocks`, `auditLogs` | 🔒 ❌ |
| `/api/admin/payments` | GET | Payments list | `payments` | 🔒 ❌ |
| `/api/admin/refunds` | GET | Refunds list | `refunds` | 🔒 ❌ |
| `/api/admin/refunds` | POST | Initiate refund | `refunds`, `payments`, `auditLogs` | 🔒 ❌ |

---

## Data Flow Diagram (Booking Journey)

```
Customer Browser                Flask API               MongoDB Atlas
     │                              │                        │
     │  GET /api/offers/active      │                        │
     │──────────────────────────────▶  offers                │
     │                              │──────────────────────▶ │
     │  GET /api/packages           │                        │
     │──────────────────────────────▶  packages              │
     │                              │──────────────────────▶ │
     │  GET /api/add-ons            │                        │
     │──────────────────────────────▶  addOns                │
     │                              │──────────────────────▶ │
     │  GET /api/availability       │                        │
     │  ?date=2026-11-01            │  bookings,             │
     │──────────────────────────────▶  bookingHolds,         │
     │                              │  availabilityBlocks    │
     │                              │──────────────────────▶ │
     │  POST /api/bookings/quote    │                        │
     │  {package,hours,addOns}      │  packages, addOns,     │
     │──────────────────────────────▶  offers (read-only)    │
     │                              │──────────────────────▶ │
     │                              │  ◀─── pricing snapshot │
     │  POST /api/bookings          │                        │
     │  {quote,customerInfo,...}    │  bookings              │
     │  Idempotency-Key: <uuid>     │  slotClaims (UNIQUE)   │
     │──────────────────────────────▶  customers             │
     │                              │  idempotencyKeys       │
     │                              │──────────────────────▶ │
     │                              │  ◀─── bookingRef       │
     │  POST /api/payments/         │                        │
     │  create-order                │  payments              │
     │──────────────────────────────▶  bookings              │
     │                              │──────────────────────▶ │
     │                              │  ◀─── razorpayOrderId  │
     │  [Razorpay Checkout]         │                        │
     │  POST /api/payments/verify   │  payments              │
     │  {payment_id,sig,...}        │  bookings              │
     │──────────────────────────────▶  webhookEvents         │
     │                              │──────────────────────▶ │
     │  GET /api/bookings/:ref      │                        │
     │──────────────────────────────▶  bookings (safe fields)│
     │                              │──────────────────────▶ │
```

