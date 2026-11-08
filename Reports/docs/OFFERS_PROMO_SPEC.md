# Joybox Party Room — Offers, Promos & Entry Points Specification

**Document Version:** 1.0.0  
**Effective Date:** 2026-11-05  
**Scope:** Promotional Quotas, Pricing Integrity, Atomic Redemptions & UI Entry Points

---

## 1. Business Requirements & Invariants

### Rule PR-01: Introductory Monthly Celebration Offer
- Joybox provides a promotional introductory offer for the **Basic** celebration package:
  - Base catalog rate: **₹999/hr** (`99900` paise).
  - Promotional rate: **₹500/hr** (`50000` paise).
  - Discount per hour: **₹499/hr** (`49900` paise).
- Applicable to bookings selecting `packageCode: "basic"` with `applyPromo: true`.

### Rule PR-02: Strictly Enforced Monthly Redemption Quota
- Each promotional offer is capped by a strict monthly redemption limit (`monthlyLimit = 5`).
- Total active reservations + completed bookings in a calendar month cannot exceed 5.
- Once 5 redemptions are claimed in the period, subsequent bookings for the Basic package are automatically quoted at the standard catalog rate (₹999/hr) with `promoApplied: false` and `promoNotAppliedReason: "Monthly promotional quota (5 bookings) already claimed."`.

### Rule PR-03: Atomic Claim Under Concurrency (Zero Race Conditions)
- Slot reservation must use atomic MongoDB operations (`find_one_and_update`) with query filters:
  ```json
  {
    "_id": offerId,
    "isActive": true,
    "monthlyRedemptionCount": { "$lt": 5 }
  }
  ```
  Increment: `{ "$inc": { "monthlyRedemptionCount": 1 } }`.
- Under high concurrent contention (e.g., 10 simultaneous threads racing for 2 remaining quota slots), exactly 2 must succeed and 8 must fall back to standard pricing or reject cleanly.

### Rule PR-04: Non-Stackable Promotions
- Promotions do not stack. Only one promo discount can be applied per reservation.
- Add-ons are priced a-la-carte and are never discounted by package-level promotions.
- Duplicate add-ons already included in a package (e.g., cake in Gold package) are strictly rejected with HTTP 422.

### Rule PR-05: Atomic Quota Replenishment on Abandonment or Collision
- If slot reservation fails due to a room schedule collision, any pre-reserved promo allocation must be immediately rolled back (`$inc: { monthlyRedemptionCount: -1 }`).
- If an active hold expires (10-minute TTL) without payment completion, the background sweep job (`run_sweeps` / `sweep_expired_holds`) must idempotently release the promo reservation and restore the monthly quota.
- Sweeping an already released reservation must never double-decrement the counter.

### Rule PR-06: Absolute Server Pricing Authority (Tamper-Proof)
- The client cannot dictate line item prices, discount amounts, or total payable figures.
- Passing `totalAmountMinor` or custom price keys in hold or booking payloads is rejected (schema `unknown = RAISE`) or ignored in favor of server catalog calculation.
- All pricing is calculated in integer minor currency units (paise: `1 INR = 100 paise`), preventing floating-point precision flaws.

### Rule PR-07: Seamless UI Entry Points
- Every "Book Now" CTA across the site must carry the package parameter in the URL:
  - Home Page Hero / Header: `/book` or `/book?package=basic`
  - Home Page Package Cards: `/book?package=basic`, `/book?package=gold`, `/book?package=diamond`
  - Interactive Price Estimator: `/book?package=${tier}&duration=${hours}`
  - Packages & Pricing Page: `/book?package=${pkg.code}`
  - Gallery Showcase Bottom CTA: `/book?package=gold`
- The booking wizard detects `?package=<slug>`, validates it against active catalog packages, and immediately opens Step 2 (Date & Slot) with the requested package pre-selected.

---

## 2. Test Verification Matrix

| Test ID | Test Description | Invariant Tested |
|---|---|---|
| `test_promo_quota_exact_5_redemptions_allowed` | Book 5 consecutive basic slots with promo; all 5 receive ₹500/hr. 6th receives ₹999/hr. | PR-01, PR-02 |
| `test_promo_concurrent_contention_exact_winners` | 8 parallel threads race for 3 remaining quota slots; exactly 3 win promo, 5 receive non-discounted quotes. | PR-03 |
| `test_promo_no_stacking` | Multiple promo codes or repeated application rejected; single discount applied. | PR-04 |
| `test_promo_rollback_on_failed_slot_claim` | Intentionally trigger slot conflict on hold; verify promo quota is immediately rolled back. | PR-05 |
| `test_promo_restore_on_hold_expiry` | Expired hold sweep restores promo quota. Verified in Phase 1.4 (`test_phase1_hold_expiry.py`). | PR-05 |
| `test_server_pricing_authority_paise_precision` | Client tampering rejected; integer paise math verifies exact catalog totals without floats. | PR-06 |
| `test_all_ui_entry_points_carry_package_param` | Unit tests verify all routes and CTAs pass `?package=<slug>`. | PR-07 |

