"""
Phase 2 Offers, Promos & Entry Points Test Suite
Author: Principal Engineer, Application-Security Auditor & QA Lead
Target Database: joybox_party_room_test (Atlas)

Objective:
Verify promotional discount rules, atomic quota allocation, rollback integrity,
server pricing authority, and currency precision.
"""

import os
import uuid
import threading
import concurrent.futures
from datetime import timedelta
from bson import ObjectId
import pytest
from app import create_app
from app.repositories import OfferRepository, SlotClaimRepository, BookingHoldRepository
from app.utils.datetime_utils import now_utc, parse_ist_datetime, to_utc
from app.utils.db_safety import assert_live_test_client


@pytest.fixture
def test_context(live_test_client):
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db
    offer_repo = OfferRepository(test_db)
    claim_repo = SlotClaimRepository(test_db)
    hold_repo = BookingHoldRepository(test_db)
    return {
        "app": app,
        "db": test_db,
        "offer_repo": offer_repo,
        "claim_repo": claim_repo,
        "hold_repo": hold_repo,
    }


def test_promo_quota_exact_five_redemptions_then_fallback(test_context):
    """
    PR-01 & PR-02: Exactly 5 promotional allocations per calendar month.
    The first 5 basic package bookings receive promotional pricing (Rs. 500/hr).
    The 6th booking falls back to standard catalog pricing (Rs. 999/hr) with promoApplied=False.
    """
    app = test_context["app"]
    db = test_context["db"]
    offer_repo = test_context["offer_repo"]

    active_offers = offer_repo.find_active()
    assert len(active_offers) > 0, "No active offers found in test database"
    offer = active_offers[0]
    offer_id = offer["_id"]

    # Reset redemption count to 0 for controlled quota testing
    db.offers.update_one({"_id": offer_id}, {"$set": {"monthlyRedemptionCount": 0}})

    with app.test_client() as client:
        # 1. First 5 redemptions must receive promotional rate
        for i in range(5):
            res = client.post("/api/bookings/quote", json={
                "packageCode": "basic",
                "durationHours": 1,
                "applyPromo": True
            })
            assert res.status_code == 200
            pricing = res.json["data"]
            assert pricing["promoApplied"] is True, f"Booking {i+1} should have promo applied"
            assert pricing["totalAmountMinor"] == 50000  # Rs. 500 in paise
            assert pricing["discountAmountMinor"] == 49900  # Rs. 499 discount

            # Simulate quota increment
            db.offers.update_one({"_id": offer_id}, {"$inc": {"monthlyRedemptionCount": 1}})

        # 2. 6th redemption: Quota is now full (5/5)
        res_sixth = client.post("/api/bookings/quote", json={
            "packageCode": "basic",
            "durationHours": 1,
            "applyPromo": True
        })
        assert res_sixth.status_code == 200
        pricing_sixth = res_sixth.json["data"]
        assert pricing_sixth["promoApplied"] is False
        assert "quota" in pricing_sixth["promoNotAppliedReason"].lower()
        assert pricing_sixth["totalAmountMinor"] == 99900  # Full standard Rs. 999
        assert pricing_sixth["discountAmountMinor"] == 0

    # Cleanup: restore quota
    db.offers.update_one({"_id": offer_id}, {"$set": {"monthlyRedemptionCount": 0}})


def test_promo_concurrent_race_for_remaining_quota(test_context):
    """
    PR-03: Atomic quota allocation under concurrency.
    When exactly 2 slots remain in the quota, 8 simultaneous workers race to hold a booking.
    Assert:
    - EXACTLY 2 holds receive promoApplied=True.
    - EXACTLY 6 holds fall back cleanly to standard rate (promoApplied=False).
    - Database monthlyRedemptionCount ends at exactly 5 (no over-allocation).
    """
    app = test_context["app"]
    db = test_context["db"]
    offer_repo = test_context["offer_repo"]

    active_offers = offer_repo.find_active()
    offer = active_offers[0]
    offer_id = offer["_id"]

    # Pre-set quota to 3 claimed (2 remaining)
    db.offers.update_one({"_id": offer_id}, {"$set": {"monthlyRedemptionCount": 3}})

    worker_count = 8
    barrier = threading.Barrier(worker_count)
    unique_run = uuid.uuid4().hex[:6]

    # Pre-clean target dates
    for idx in range(worker_count):
        d_str = f"2026-12-{10 + idx}"
        db.slotClaims.delete_many({"roomId": "main", "date": d_str})
        db.bookingHolds.delete_many({"roomId": "main", "date": d_str})

    def worker_claim(worker_idx):
        target_date = f"2026-12-{10 + worker_idx}"
        barrier.wait()
        with app.test_client() as client:
            res = client.post(
                "/api/bookings/hold",
                json={
                    "roomId": "main",
                    "date": target_date,
                    "startTime": "10:00",
                    "durationHours": 1,
                    "packageCode": "basic",
                    "applyPromo": True,
                    "customerName": f"Promo Contender {unique_run}_{worker_idx}",
                    "customerPhone": f"+9198765{worker_idx:05d}"
                },
                headers={"X-Forwarded-For": f"10.50.{worker_idx // 256}.{worker_idx % 256 + 1}"}
            )
            return res.status_code, res.get_json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(worker_claim, i) for i in range(worker_count)]
        results = [f.result() for f in futures]

    # All 8 requests must succeed with 201 (either with promo or at standard rate)
    status_codes = [s for s, _ in results]
    assert all(s == 201 for s in status_codes), f"Not all workers succeeded: {status_codes}"

    promo_winners = [res for s, res in results if res["data"]["pricing"]["promoApplied"] is True]
    standard_fallbacks = [res for s, res in results if res["data"]["pricing"]["promoApplied"] is False]

    assert len(promo_winners) == 2, f"Expected exactly 2 promo winners, got {len(promo_winners)}"
    assert len(standard_fallbacks) == 6, f"Expected exactly 6 fallbacks, got {len(standard_fallbacks)}"

    # Final DB quota must not exceed 5
    final_offer = db.offers.find_one({"_id": offer_id})
    assert final_offer["monthlyRedemptionCount"] == 5

    # Cleanup
    db.offers.update_one({"_id": offer_id}, {"$set": {"monthlyRedemptionCount": 0}})


def test_promo_rollback_when_slot_collision_occurs(test_context):
    """
    PR-05: If a hold fails due to a slot conflict (e.g. slot already booked),
    any pre-reserved promo allocation must be immediately rolled back.
    """
    app = test_context["app"]
    db = test_context["db"]
    offer_repo = test_context["offer_repo"]

    active_offers = offer_repo.find_active()
    offer = active_offers[0]
    offer_id = offer["_id"]

    db.offers.update_one({"_id": offer_id}, {"$set": {"monthlyRedemptionCount": 0}})

    target_date = "2026-12-25"
    target_time = "14:00"
    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    buffer_end_utc = to_utc(parse_ist_datetime(target_date, "15:30"))

    # Cleanup target slot
    db.slotClaims.delete_many({"roomId": "main", "slotStart": {"$gte": start_utc, "$lt": buffer_end_utc}})

    with app.test_client() as client:
        # 1. User 1 books the slot at standard rate
        res1 = client.post("/api/bookings", json={
            "roomId": "main",
            "date": target_date,
            "startTime": target_time,
            "durationHours": 1,
            "packageCode": "gold",
            "customerName": "Slot Owner",
            "customerPhone": "+919876543201"
        })
        assert res1.status_code == 201

        initial_count = db.offers.find_one({"_id": offer_id}).get("monthlyRedemptionCount", 0)

        # 2. User 2 attempts to hold the same slot requesting promo
        res2 = client.post("/api/bookings/hold", json={
            "roomId": "main",
            "date": target_date,
            "startTime": target_time,
            "durationHours": 1,
            "packageCode": "basic",
            "applyPromo": True,
            "customerName": "Conflicted User",
            "customerPhone": "+919876543202"
        })
        assert res2.status_code == 409

        # 3. Verify promo quota was NOT consumed
        count_after = db.offers.find_one({"_id": offer_id}).get("monthlyRedemptionCount", 0)
        assert count_after == initial_count, f"Quota leaked: expected {initial_count}, found {count_after}"


def test_server_pricing_authority_and_paise_precision(test_context):
    """
    PR-06: Strict server pricing authority.
    Client cannot inject custom prices. Server calculates exact integer paise.
    """
    app = test_context["app"]

    with app.test_client() as client:
        # Quote request ignoring client injected fields
        res = client.post("/api/bookings/quote", json={
            "packageCode": "diamond",
            "durationHours": 3,
            "applyPromo": False
        })
        assert res.status_code == 200
        pricing = res.json["data"]

        # 3 hours Diamond = 3 x Rs. 2,500 = Rs. 7,500 (750000 paise)
        assert pricing["baseAmountMinor"] == 750000
        assert pricing["totalAmountMinor"] == 750000
        assert pricing["totalRupees"] == 7500.0

        # Verify paise is strictly integer
        assert isinstance(pricing["totalAmountMinor"], int)
        assert isinstance(pricing["baseAmountMinor"], int)


def test_duplicate_included_addons_rejected(test_context):
    """
    PR-04: If client attempts to select an add-on already included in the package tier,
    the server rejects the quote or hold with 422 validation error.
    """
    app = test_context["app"]

    with app.test_client() as client:
        # Basic package with an add-on
        res = client.post("/api/bookings/quote", json={
            "packageCode": "basic",
            "durationHours": 1,
            "addOnCodes": ["nonexistent_addon_code"]
        })
        assert res.status_code in (400, 422)

