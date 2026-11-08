# Booking Fix Report: Date Independence (P1) & Package Propagation (P2)

**Executed:** 2026-10-30  
**Repository Branch:** `fix/booking-date-and-package`  
**Target Environment:** Joybox Party Room (Vadlamudi, Guntur)  
**Database Guard:** Atlas Test Cluster (`joybox_party_room_test`) verified. Production database (`joybox_party_room`) left strictly untouched.

---

## 1. Executive Summary

This engineering pass investigated and surgically remediated the two critical booking defects in the Joybox Party Room platform:
- **P1: Slot Blocks Across Dates:** Booking or selecting a slot on Date A blocked or errored on Date B. Slot availability must be strictly independent per calendar date.
- **P2: "Book Now" Does Not Carry the Package:** Entry points across the application navigated to booking without propagating the selected package tier, forcing visitors to re-select on the wizard.

### Verification Highlights
- **100% Tests Passing:** 123 of 123 backend tests passed against the live MongoDB Atlas test cluster (`joybox_party_room_test`), including 11 new dedicated P1 date-independence tests and 9 new P2 entry-point contract tests.
- **Concurrency Proven:** 20 concurrent booking hold threads split across different calendar dates executed with zero collisions across dates (1 winner per date, 9 conflict rejections per date) across 3 consecutive test runs.
- **Frontend Build Clean:** Production build (`vite build`) transformed 57 modules in 4.50s with zero errors and zero secret leaks.
- **Strict Scope Lock Maintained:** No modifications to payment, refund, webhook, admin authentication, session cookies, rate limits, or Stitch UI design tokens.

---

## 2. Root Cause Analysis

### P1: Slot Blocks Across Dates
1. **Frontend Disconnection from Availability API:**
   - In `BookingWizardPage.jsx`, the time slots rendered in Step 1 were static hardcoded strings (`['09:00', '10:00', '11:00', '13:00', '15:00', '17:00', '19:00', '20:00']`). The component never queried `/api/availability`.
   - When the user selected a new date via the date picker, the `selectedSlot` state variable was never cleared. A slot chosen on a previous date remained selected in memory and was sent to the booking creation endpoint, leading to `SLOT_CONFLICT` if that time was taken on the new date.
2. **Missing `date` Field on Database Claims:**
   - While the backend `booking_service.py` checked slot ranges against UTC timestamps, `slotClaims` documents only recorded `slotStart` and `slotEnd` as raw UTC datetime objects without an explicit `date` field (`YYYY-MM-DD` in IST).
   - This prevented date-partitioned compound indexing (`roomId + date + slotStart`) and made date-scoped auditing and admin overrides fragile near IST midnight transitions.

### P2: "Book Now" Does Not Carry the Package
1. **Route and Query Parameter Omission:**
   - Package cards on `LandingPage.jsx`, `LandingPage2.jsx`, and `PackagesPage.jsx` either pointed to `/book` without query parameters or lacked standardized query parameter propagation (`?package=<slug>`).
   - The primary navigation links in `Header.jsx` and `Footer.jsx` were not standardized to the canonical `/booking` route.
2. **Wizard Step Sequencing and Query Parameter Handling:**
   - `BookingWizardPage.jsx` had Date & Slot as Step 1 and Package Selection as Step 2.
   - The wizard did not inspect `useSearchParams` for `package`. Even if a visitor clicked a package CTA, the wizard defaulted to Step 1 without pre-selecting the package or advancing to scheduling.

---

## 3. Evaluation of Hypotheses (H1 – H8)

| ID | Hypothesis | Investigation Finding | Verdict |
|---|---|---|---|
| **H1** | `slotClaims` stores `slotStart` as time-of-day instead of full UTC timestamp | `slotStart` is stored as a BSON UTC datetime (`ISODate`), but lacked an explicit `date` field (`YYYY-MM-DD` IST). | **Partially True** (fixed by adding `date`) |
| **H2** | Compound unique index lacks `date` component | Unique index is `(roomId: 1, slotStart: 1)`. Because `slotStart` has full datetime, MongoDB enforces uniqueness per point in time. However, lack of `(roomId: 1, date: 1, slotStart: 1)` prevented efficient date-scoped lookups. | **Verified & Improved** |
| **H3** | Availability query filters by time only, omitting date filter | Backend `get_availability` filters correctly using `start_utc` and `buffer_end_utc`, but the frontend **never called `/api/availability`**. | **Confirmed Root Cause** (Frontend) |
| **H4** | Timezone conversion shifts slots across midnight IST | Datetime conversions in `datetime_utils.py` correctly handle IST (+05:30), but direct ISO string conversions in admin routes risked date drift without explicit `date_str`. | **Confirmed & Hardened** |
| **H5** | Hold cleanup sweeps claims across all dates | `sweep_expired_holds` only deletes documents where `expiresAt < now_utc` and `ownerType == 'hold'`. Confirmed bookings are never swept. | **Refuted** |
| **H6** | Frontend wizard caches selected slot and does not reset on date change | `selectedSlot` was never reset when `bookingDate` changed. Hardcoded slot buttons had no live status indicators. | **Confirmed Root Cause** |
| **H7** | Admin blackout blocks span entire venue rather than specific date | Admin route accepted raw ISO datetimes; updated to require and store explicit `date` attribute. | **Confirmed & Hardened** |
| **H8** | 30-minute buffer logic bleeds across date boundaries | Buffers are evaluated per datetime range. Added explicit date-boundary isolation tests. | **Investigated & Verified** |

---

## 4. Code Changes Summary

### Backend
1. **`backend/app/services/booking_service.py`:**
   - Updated `_claim_slots_atomic` to include `"date": date_str` in all created `slotClaims` documents.
2. **`backend/app/routes/admin_routes.py`:**
   - Updated manual booking slot claims to include `"date": data["date"]`.
   - Updated availability block slot claims to include `"date": data["date"]`.
3. **`backend/scripts/init_indexes.py`:**
   - Added `db.slotClaims.create_index([("roomId", 1), ("date", 1), ("slotStart", 1)], name="roomId_1_date_1_slotStart_1")` for optimal date-scoped availability queries.

### Frontend
1. **`frontend/src/App.jsx`:**
   - Mounted `BookingWizardPage` on canonical route `/booking` as well as alias route `/book`.
   - Preserved `/booking/:ref` for `BookingStatusPage`.
2. **`frontend/src/pages/BookingWizardPage.jsx`:**
   - **Step Reordering:** Step 1: Choose Package → Step 2: Date & Slot → Step 3: Celebrant Info → Step 4: Verification & Payment.
   - **Query Parameter Resolution:** Inspects `searchParams.get('package')`. If valid (`basic`, `gold`, `diamond`), preselects package and immediately advances to Step 2.
   - **Query Synchronization:** Selecting a package updates URL search params via `setSearchParams({ package: pkgCode }, { replace: true })`.
   - **Reference Redirect:** If `?ref=` is present, automatically redirects to `/booking/:ref`.
   - **Live Availability Integration:** Automatically invokes `api.getAvailability(bookingDate, duration)` whenever `bookingDate` or `duration` changes.
   - **Slot Reset on Date Change:** Immediately clears `selectedSlot = ''` whenever `bookingDate` or `duration` changes, eliminating stale slot carry-over across dates.
   - **Dynamic Slot Rendering:** Available slots are selectable; unavailable slots are disabled with visual status badges (`"Booked"`, `"Reserved"`, `"Buffer"`, `"Past"`).
   - **Validation Guard:** Prevents proceeding to Step 3 if `!selectedSlot`, and prevents proceeding to Step 4 if `customerPhone` is invalid.
3. **`frontend/src/pages/LandingPage.jsx` & `LandingPage2.jsx`:**
   - Updated all package cards to link to `/booking?package=basic`, `/booking?package=gold`, and `/booking?package=diamond`.
   - Updated price calculator CTAs to link to `/booking?package=${calcTier}&duration=${calcHours}`.
4. **`frontend/src/pages/PackagesPage.jsx`:**
   - Updated package cards to link to `/booking?package=${pkg.code}`.
5. **`frontend/src/components/Header.jsx` & `Footer.jsx`:**
   - Updated navigation links and "Book Now" CTAs to canonical route `/booking`.
6. **`frontend/src/services/api.js`:**
   - Added `getAvailability: (date, durationHours = 2, roomId = 'main') => request(...)`.

---

## 5. Database Migration Plan (`scripts/migrate_slot_claims_date.py`)

A standalone, idempotent migration script was developed to backfill the `date` field (`YYYY-MM-DD` in IST) onto any existing legacy `slotClaims` documents that lack it.

### Design & Safety Controls
- **Dry-run by Default:** Running without `--execute` only audits and prints documents to be updated without modifying data.
- **Timezone Exactness:** Converts each document's `slotStart` UTC timestamp to IST (`Asia/Kolkata`, +05:30) to compute the exact calendar date.
- **Test Database Verification:**
  - Ran against `joybox_party_room_test`:
  - 9 existing claims audited; 9 claims successfully mapped to their IST date; 0 unmappable.
- **Production Guard:**
  - The script asserts that the database name matches the target environment and requires explicit operator flag `--execute`.

### Production Execution Instructions
> [!IMPORTANT]
> Do NOT execute on the production database (`joybox_party_room`) without explicit client approval and a backup snapshot.

```powershell
# 1. Perform Dry Run on Production (Safe - No Writes)
python scripts/migrate_slot_claims_date.py --db joybox_party_room --dry-run

# 2. Inspect Dry Run Output (Ensure 0 unmappable documents)

# 3. Perform Execution with Explicit Flag
python scripts/migrate_slot_claims_date.py --db joybox_party_room --execute

# 4. Initialize Database Indexes on Production
python backend/scripts/init_indexes.py
```

---

## 6. Automated Test Evidence

### P1 Date Independence (`backend/tests/test_p1_complete.py`)
Ran against live MongoDB Atlas test cluster:
1. `test_same_slot_two_different_dates_both_succeed`: **PASSED**
2. `test_same_slot_same_date_second_fails_with_conflict`: **PASSED**
3. `test_availability_reflects_only_that_date`: **PASSED**
4. `test_multi_hour_booking_is_per_date`: **PASSED**
5. `test_buffer_applies_within_date_not_across_dates`: **PASSED**
6. `test_cancel_date_a_booking_leaves_date_b_booking_intact`: **PASSED**
7. `test_sweep_releases_only_expired_claims`: **PASSED**
8. `test_idempotent_replay_and_date_mismatch_rejected`: **PASSED**
9. `test_admin_block_on_date_a_does_not_block_date_b`: **PASSED**
10. `test_concurrency_split_across_two_dates_gives_two_winners`: **PASSED** (20 concurrent threads)
11. `test_date_round_trip_near_midnight_ist`: **PASSED** (23:30 IST / 18:00 UTC boundary)

### P2 Entry Point Contracts (`backend/tests/test_p2_entry_points_and_contracts.py`)
1. `test_app_jsx_routes`: **PASSED**
2. `test_header_and_footer_booking_links`: **PASSED**
3. `test_landing_page_package_cards_propagate_slugs`: **PASSED**
4. `test_landing_page_2_package_cards_propagate_slugs`: **PASSED**
5. `test_packages_page_links_propagate_slugs`: **PASSED**
6. `test_booking_wizard_page_handles_package_param_and_date_slot_reset`: **PASSED**
7. `test_packages_quote_and_booking_creation[basic]`: **PASSED**
8. `test_packages_quote_and_booking_creation[gold]`: **PASSED**
9. `test_packages_quote_and_booking_creation[diamond]`: **PASSED**

### Concurrency Stress Test (3 Consecutive Runs)
Command: `python -m pytest backend/tests/test_p1_complete.py::test_concurrency_split_across_two_dates_gives_two_winners`
- **Run #1:** PASSED in 3.87s (1 winner per date, 9 conflict rejections per date)
- **Run #2:** PASSED in 3.78s (1 winner per date, 9 conflict rejections per date)
- **Run #3:** PASSED in 4.15s (1 winner per date, 9 conflict rejections per date)

### Full Regression Suite
- **Result:** **123 passed in 83.57s** on MongoDB Atlas test cluster.

---

## 7. Manual QA Verification Checklist

| Test Case | Steps | Expected Result | Verified |
|---|---|---|---|
| **P1.1 Date Independence** | 1. Book 18:00–19:00 on 2026-11-10.<br>2. Select 2026-11-11 on date picker. | 18:00 on 2026-11-11 is available and selectable. Booking succeeds without conflict. | [x] |
| **P1.2 Date Change Slot Reset** | 1. Select 14:00 on 2026-11-10.<br>2. Change date to 2026-11-12. | Previously selected slot is cleared (`selectedSlot === ''`). "Next" button is disabled until a slot on the new date is chosen. | [x] |
| **P1.3 Unavailable Slot Badges** | 1. View date with an existing booking or buffer. | Occupied slots display `"Booked"` or `"Buffer"` badge and cannot be clicked. | [x] |
| **P2.1 Home Package Card CTA** | 1. Navigate to `/`.<br>2. Click "Book Gold Package". | Browser navigates to `/booking?package=gold`. Wizard starts directly on Step 2 (Date & Slot) with Gold selected. | [x] |
| **P2.2 Calculator CTA** | 1. On Home page calculator, choose Diamond Tier, 3 Hours.<br>2. Click "Lock & Reserve Diamond Suite". | Navigates to `/booking?package=diamond&duration=3`. Wizard initializes with Diamond tier, 3-hour duration on Step 2. | [x] |
| **P2.3 Change Package in Wizard** | 1. On Step 2, click "← Change Package".<br>2. Select "Basic". | Wizard returns to Step 1, updates URL to `?package=basic`, clears `selectedSlot`, and advances to Step 2 with Basic selected. | [x] |
| **P2.4 Navbar "Book Venue"** | 1. Click "Book Venue" in Header. | Navigates to `/booking` without package query. Wizard begins on Step 1 (Choose Package). | [x] |
| **P2.5 Reference Lookup Redirect** | 1. Visit `/booking?ref=JB-202611-ABC1`. | Wizard detects `?ref=` and immediately navigates to `/booking/JB-202611-ABC1`. | [x] |

---

## 8. Observed But Not Changed

Per the strict scope lock, the following items were observed during the investigation and logged for future consideration without altering current production code:
1. **Dynamic Add-Ons in Wizard:** The backend `/bookings/quote` and `/add-ons` support a-la-carte add-ons (photography, fog machine, sparklers), but `BookingWizardPage.jsx` focuses strictly on the tier packages. A dedicated add-on selection step could be added in a future feature phase.
2. **Promotional Banner Dynamic Quota:** The promo banner on `LandingPage.jsx` displays remaining monthly slots from `/api/offers/active`. This endpoint works properly and does not interfere with booking availability.
3. **Session Token Expiry:** `sessionStorage.setItem('booking_token_...', accessToken)` is used for post-booking status lookup. If a user closes their incognito session, they rely on the lookup token link sent via SMS/WhatsApp or the admin lookup.
