# BUSINESS RULES REQUIRED — Joybox Party Room
**Strict Phase 4 / Pre-Phase 5 Checkpoint · Updated 2026-10-28**

This document captures every business policy for Joybox Party Room.
Per explicit owner directive:
- ✅ **CONFIRMED** — Strictly restricted to only policies confirmed by the owner:
  1. Operating hours: 09:00 AM – 10:00 PM IST
  2. Buffer between bookings: 30 minutes
  3. Host name & contact: Kiran Kumar (+91 78427 04429, Beside Durga Mart, Vadlamudi, Guntur)
  4. Typography / Fonts: Each Stitch export preserved as designed (Landing 2 keeps Fredoka/Poppins; canonical pages use Epilogue/Outfit; do not unify).
- 🔶 **UNCONFIRMED** — Every other business policy remains unconfirmed. Code reads defaults from server-side configuration; never hard-coded.

All monetary amounts in this document are **display values in Indian Rupees (₹)**. The database stores them as **integer paise** (₹999 = 99900 paise).

---

## 1. Venue & Operations

### 1.1 Location & Host
✅ **CONFIRMED**
- Name: Joybox Party Room
- Address: Beside Durga Mart, Vadlamudi, Guntur, Andhra Pradesh, India
- Host / Contact person: **Kiran Kumar** (all occurrences of "Venkat" in exports replaced)
- WhatsApp / Phone: +91 78427 04429 (E.164: `+917842704429`)

### 1.2 Operating Hours & Days
✅ **CONFIRMED (Hours only)**
- Open: **09:00 AM – 10:00 PM** (09:00 to 22:00 IST)
- Timezone: **Asia/Kolkata (IST, UTC+5:30)**
- Storage: UTC in MongoDB; display in IST everywhere
- First possible booking start: 09:00 IST
- Latest possible booking end: 22:00 IST (10:00 PM)
- 🔶 **UNCONFIRMED:** Operating days (proposed: 7 days/week, Monday through Sunday).

### 1.3 Buffer Between Bookings
✅ **CONFIRMED**
- **30 minutes** setup/sanitization buffer between bookings in the same room.
- The buffer time belongs to the venue and is non-bookable by customers.
- Stored and enforced in server availability calculations (`BUFFER_MINUTES = 30`).
- For events ending at closing time (22:00 IST), the 30-minute sanitization buffer runs 22:00–22:30 IST for venue staff (governed by server config `ALLOW_BUFFER_PAST_CLOSING = True`).

### 1.4 Typography & Visual Design
✅ **CONFIRMED**
- **Landing Page 2:** Strictly retains its exported typography: **Fredoka** (headings) + **Poppins** (body & Telugu). Do NOT unify with Epilogue/Outfit.
- **Canonical Pages (Landing 1, Packages, Book, Status, Gallery, Contact):** Retains **Epilogue** (headings) + **Outfit** (body & labels).
- Colors: Purple/Magenta system (`primary: #1e0051`, `secondary: #b40068`, `surface: #fef7ff`).

---

## 2. Unconfirmed Business Policies (Pending Owner Sign-Off)

### 2.1 Booking Duration
🔶 **UNCONFIRMED**
- *[Proposed: Min 1 hour, Max 6 hours, whole hours only]*
- Code reads `MIN_BOOKING_HOURS` and `MAX_BOOKING_HOURS` from config.

### 2.2 Number of Rooms
🔶 **UNCONFIRMED**
- *[Proposed: Currently 1 room ("Main Hall", `main`), extensible schema]*

### 2.3 Base Packages & Pricing
🔶 **UNCONFIRMED**
- *[Proposed: Basic ₹999/hr, Gold ₹1,500/hr, Diamond ₹2,500/hr]*
- Stored in MongoDB `packages` collection and served via `GET /api/packages`.

### 2.4 Add-ons & Diamond Duplication
🔶 **UNCONFIRMED**
- *[Proposed: Bubble ₹300, Fog ₹500, Cold-fire ₹300/shot]*
- Diamond duplicate add-ons: prevent duplicate selection vs charge for extra units.

### 2.5 Promotional Offer & Lifecycle
🔶 **UNCONFIRMED [Decision Pending Owner Input]**
- *[Proposed: Basic package introductory rate ₹500/hr for first 5 bookings/month]*
- *[Proposed Lifecycle: Reserve quota at hold creation, convert to redeemed on verified payment, release back to quota pool on hold expiry or cancellation]*
- Awaiting owner confirmation: `[accepted / changed to ____]`.

### 2.6 Payment Model & Advance
🔶 **UNCONFIRMED**
- *[Proposed: Full payment upfront vs token advance]*
- Razorpay gateway integration in Phase 6.

### 2.7 Cancellation & Refund Policy Schedule
🔶 **UNCONFIRMED**
- *[Proposed & Implemented Config Defaults]*:
  - > 48 hours notice before party start: 100% refund (`REFUND_WINDOW_FULL_HOURS = 48`)
  - 24 to 48 hours notice before party start: 50% refund (`REFUND_WINDOW_PARTIAL_HOURS = 24`, `REFUND_WINDOW_PARTIAL_PERCENT = 50`)
  - < 24 hours notice before party start: Non-refundable (`REFUND_MIN_NOTICE_HOURS = 24`)
- On 100% refund / cancellation: slots in `slotClaims` are released immediately, and promotional offer reservations are returned to the monthly quota pool.

### 2.8 Slot Hold Duration
🔶 **UNCONFIRMED**
- Duration of temporary lock during checkout.
- *[Proposed: Server-governed duration; UI text dynamically displays server value, no hard-coded minutes]*

### 2.9 Admin Roles & Session Mechanism
🔶 **UNCONFIRMED**
- *[Proposed: Roles `super_admin` & `staff`, short-lived JWT in `httpOnly` cookie]*

### 2.11 Access Tokens & Security
🔶 **UNCONFIRMED**
- Unguessable 32-byte URL-safe access token generated on booking creation; stored only as SHA-256 hash.
- Required to view full booking details or cancel. Reference-only lookup returns minimal status without names, phones, or prices.

### 2.12 Anti-Hoarding Rate Limits
🔶 **UNCONFIRMED**
- Configurable limits: Max 10 hold requests per IP per minute (`RATE_LIMIT_HOLD_PER_IP_MAX = 10`), Max 3 hold requests per normalized phone per 10 minutes (`RATE_LIMIT_HOLD_PER_PHONE_MAX = 3`).

---

## 3. Summary Matrix

| Policy Area | Status | Active Code Value / Handling |
|---|---|---|
| Operating Hours | ✅ **CONFIRMED** | 09:00 AM – 10:00 PM IST |
| Buffer Between Bookings | ✅ **CONFIRMED** | 30 minutes |
| Host Name & Contact | ✅ **CONFIRMED** | Kiran Kumar (+91 78427 04429) |
| Landing 2 Typography | ✅ **CONFIRMED** | Fredoka (headings) + Poppins (body) |
| Canonical Typography | ✅ **CONFIRMED** | Epilogue (headings) + Outfit (body) |
| Days Open | 🔶 **UNCONFIRMED** | 7 days/week (Config default) |
| Booking Duration | 🔶 **UNCONFIRMED** | 1 to 6 hours (Config default) |
| Room Count | 🔶 **UNCONFIRMED** | 1 room (`main`) (Schema ready for multiple) |
| Pricing & Add-ons | 🔶 **UNCONFIRMED** | Database-driven via `packages` / `addOns` collections |
| Diamond Duplicate Inclusions | 🔶 **UNCONFIRMED** | Server rejects duplicates (Config default) |
| Promo Lifecycle | 🔶 **UNCONFIRMED** | Reserve at hold, convert at payment, release on expiry/cancel |
| Payment Timing | 🔶 **UNCONFIRMED** | Advance payment required (Config default) |
| Cancellation Refund Tiers | 🔶 **UNCONFIRMED** | Pending schedule (Stored in `cancellationPolicy` document) |
| Hold Duration | 🔶 **UNCONFIRMED** | Server-driven (No hard-coded values in UI) |
| Access Token Requirement | 🔶 **UNCONFIRMED** | Token required for details/cancel; reference-only is minimal |
| Anti-Hoarding Rate Limits | 🔶 **UNCONFIRMED** | 10 req/min per IP, 3 req/10min per phone |
| Admin Auth & Roles | 🔶 **UNCONFIRMED** | `super_admin`, `staff`, JWT in cookie |
| GST Tax Rate | 🔴 **UNCONFIRMED** | 0% default |
