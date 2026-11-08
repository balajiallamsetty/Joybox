"""
Phase 1.4 Hold Expiry & Sweeps Idempotency Test Suite
Author: Principal Engineer, Application-Security Auditor & QA Lead
Target Database: joybox_party_room_test (Atlas)

Objective:
Verify hold TTL expiry and idempotent sweep execution:
1. Hold TTL expiry releases all slot claims and allows immediate re-booking.
2. Hold TTL expiry restores reserved promotional offer quota.
3. run_sweeps scheduled maintenance job executes idempotently across repeated runs without crashing.
"""

import os
import uuid
from datetime import timedelta
from bson import ObjectId
import pytest
from app import create_app
from app.jobs.run_sweeps import run_sweeps
from app.repositories import (
    BookingHoldRepository,
    SlotClaimRepository,
    OfferRepository,
    OfferRedemptionRepository,
    BookingRepository,
    PackageRepository,
    AddOnRepository,
    CounterRepository,
    IdempotencyRepository,
    RateLimitRepository,
)
from app.services.booking_service import BookingService
from app.utils.datetime_utils import now_utc, parse_ist_datetime, to_utc
from app.utils.db_safety import assert_live_test_client


@pytest.fixture
def test_setup(live_test_client):
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    hold_repo = BookingHoldRepository(test_db)
    claim_repo = SlotClaimRepository(test_db)
    offer_repo = OfferRepository(test_db)
    offer_redemp_repo = OfferRedemptionRepository(test_db)
    booking_repo = BookingRepository(test_db)
    pkg_repo = PackageRepository(test_db)
    addon_repo = AddOnRepository(test_db)
    counter_repo = CounterRepository(test_db)
    idemp_repo = IdempotencyRepository(test_db)
    rate_repo = RateLimitRepository(test_db)

    svc = BookingService(
        slot_claim_repo=claim_repo,
        hold_repo=hold_repo,
        booking_repo=booking_repo,
        counter_repo=counter_repo,
        offer_repo=offer_repo,
        offer_redemption_repo=offer_redemp_repo,
        idempotency_repo=idemp_repo,
        package_repo=pkg_repo,
        addon_repo=addon_repo,
        rate_limit_repo=rate_repo,
        config=app.config,
    )

    return {
        "app": app,
        "db": test_db,
        "svc": svc,
        "hold_repo": hold_repo,
        "claim_repo": claim_repo,
        "offer_repo": offer_repo,
        "offer_redemp_repo": offer_redemp_repo,
    }


def test_hold_expiry_releases_slot_claims_and_allows_rebooking(test_setup):
    """
    BL-05 / BL-07: When a hold passes its 10-minute TTL, sweeping it releases
    all slot claims, transitions the hold to 'expired', and allows immediate re-booking.
    """
    app = test_setup["app"]
    db = test_setup["db"]
    svc = test_setup["svc"]

    target_date = "2026-12-20"
    target_time = "11:00"
    duration = 2  # 2 hours = 4 party slots + 1 buffer slot = 5 total 30m slots

    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    buffer_end_utc = to_utc(parse_ist_datetime(target_date, "13:30"))

    # Cleanup
    db.slotClaims.delete_many({"roomId": "main", "slotStart": {"$gte": start_utc, "$lt": buffer_end_utc}})
    db.bookingHolds.delete_many({"roomId": "main", "date": target_date})

    # 1. Create active hold
    with app.test_client() as client:
        res = client.post("/api/bookings/hold", json={
            "roomId": "main",
            "date": target_date,
            "startTime": target_time,
            "durationHours": duration,
            "packageCode": "basic",
            "customerName": "Expiring Customer",
            "customerPhone": "+919876543210"
        })
        assert res.status_code == 201
        hold_id_str = res.json["data"]["holdId"]
        hold_oid = ObjectId(hold_id_str)

    # Verify 5 slot claims exist
    claims = list(db.slotClaims.find({"ownerId": hold_oid}))
    assert len(claims) == 5, f"Expected 5 slot claims for 2h booking + buffer, found {len(claims)}"

    # Verify slot is currently unavailable for another customer
    with app.test_client() as client:
        res_conflict = client.post("/api/bookings/hold", json={
            "roomId": "main",
            "date": target_date,
            "startTime": target_time,
            "durationHours": duration,
            "packageCode": "basic",
            "customerName": "Second Customer",
            "customerPhone": "+919876543211"
        })
        assert res_conflict.status_code == 409

    # 2. Age the hold past its TTL into the past
    past_time = now_utc() - timedelta(minutes=15)
    db.bookingHolds.update_one({"_id": hold_oid}, {"$set": {"expiresAt": past_time}})
    db.slotClaims.update_many({"ownerId": hold_oid}, {"$set": {"expiresAt": past_time}})

    # 3. Trigger sweep
    reclaimed = svc.sweep_expired_holds()
    assert reclaimed >= 1, f"Expected at least 1 hold reclaimed, got {reclaimed}"

    # 4. Verify hold transitioned to expired
    hold_doc = db.bookingHolds.find_one({"_id": hold_oid})
    assert hold_doc["status"] == "expired"

    # 5. Verify all slot claims are deleted
    remaining_claims = list(db.slotClaims.find({"ownerId": hold_oid}))
    assert len(remaining_claims) == 0, f"Expected 0 claims remaining, found {len(remaining_claims)}"

    # 6. Verify second customer can now successfully acquire the slot
    with app.test_client() as client:
        res_rebooked = client.post("/api/bookings/hold", json={
            "roomId": "main",
            "date": target_date,
            "startTime": target_time,
            "durationHours": duration,
            "packageCode": "gold",
            "customerName": "New Winner Customer",
            "customerPhone": "+919876543212"
        })
        assert res_rebooked.status_code == 201
        new_hold_id = res_rebooked.json["data"]["holdId"]
        new_hold_doc = db.bookingHolds.find_one({"_id": ObjectId(new_hold_id)})
        assert new_hold_doc["status"] == "active"


def test_hold_expiry_restores_promotional_quota(test_setup):
    """
    BL-08: When a hold with a promotional discount expires, the monthly quota
    is atomically restored to its pre-reservation count.
    """
    app = test_setup["app"]
    db = test_setup["db"]
    svc = test_setup["svc"]
    offer_repo = test_setup["offer_repo"]

    # Locate active offer
    active_offers = offer_repo.find_active()
    assert len(active_offers) > 0, "No active offers found in test database"
    offer = active_offers[0]
    offer_id = offer["_id"]

    # Reset redemption count to 0 for deterministic promo quota testing
    db.offers.update_one({"_id": offer_id}, {"$set": {"monthlyRedemptionCount": 0}})
    initial_redemptions = 0

    target_date = "2026-12-21"
    target_time = "15:00"

    # Clean target slots
    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    buffer_end_utc = to_utc(parse_ist_datetime(target_date, "16:30"))
    db.slotClaims.delete_many({"roomId": "main", "slotStart": {"$gte": start_utc, "$lt": buffer_end_utc}})

    # Create hold with promo applied
    with app.test_client() as client:
        res = client.post("/api/bookings/hold", json={
            "roomId": "main",
            "date": target_date,
            "startTime": target_time,
            "durationHours": 1,
            "packageCode": "basic",
            "applyPromo": True,
            "customerName": "Promo Customer",
            "customerPhone": "+919876543215"
        })
        assert res.status_code == 201
        hold_id_str = res.json["data"]["holdId"]
        hold_oid = ObjectId(hold_id_str)
        pricing = res.json["data"]["pricing"]
        assert pricing["promoApplied"] is True

    # Quota should reflect increment
    after_hold_offer = db.offers.find_one({"_id": offer_id})
    assert after_hold_offer.get("monthlyRedemptionCount", 0) == initial_redemptions + 1

    # Age hold past TTL
    past_time = now_utc() - timedelta(minutes=15)
    db.bookingHolds.update_one({"_id": hold_oid}, {"$set": {"expiresAt": past_time}})

    # Run sweep
    svc.sweep_expired_holds()

    # Quota must be restored
    restored_offer = db.offers.find_one({"_id": offer_id})
    assert restored_offer.get("monthlyRedemptionCount", 0) == initial_redemptions, (
        f"Promo quota was not restored: expected {initial_redemptions}, found {restored_offer.get('monthlyRedemptionCount')}"
    )


def test_run_sweeps_cli_job_idempotent_repeated_execution(test_setup):
    """
    BL-07: run_sweeps maintenance job must be completely idempotent:
    Running it multiple times sequentially cleans up remaining records on run 1,
    and safely does nothing on subsequent runs without throwing any error.
    """
    db = test_setup["db"]

    # Release any lingering cronLock
    db.cronLocks.delete_many({"_id": "maintenance_sweeps_lease"})

    target_date = "2026-12-22"
    target_time = "10:00"
    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    buffer_end_utc = to_utc(parse_ist_datetime(target_date, "11:30"))

    # Create an artificially expired hold in DB
    hold_id = ObjectId()
    db.bookingHolds.insert_one({
        "_id": hold_id,
        "roomId": "main",
        "date": target_date,
        "startTime": target_time,
        "durationHours": 1,
        "packageCode": "basic",
        "packageName": "Basic",
        "customer": {"name": "Test Stale", "phone": "+919876543210"},
        "pricing": {"totalAmountMinor": 99900},
        "status": "active",
        "expiresAt": now_utc() - timedelta(minutes=20),
        "createdAt": now_utc() - timedelta(minutes=25)
    })
    db.slotClaims.insert_one({
        "roomId": "main",
        "slotStart": start_utc,
        "slotEnd": buffer_end_utc,
        "ownerType": "hold",
        "ownerId": hold_id,
        "expiresAt": now_utc() - timedelta(minutes=20)
    })

    # Run 1: Must reclaim
    result1 = run_sweeps(db.name)
    assert result1["expired_holds_reclaimed"] >= 1

    # Verify hold is now expired
    h = db.bookingHolds.find_one({"_id": hold_id})
    assert h["status"] == "expired"
    c = db.slotClaims.find_one({"ownerId": hold_id})
    assert c is None

    # Run 2: Must execute cleanly with 0 newly reclaimed holds
    # Release cronLock so run 2 acquires fresh lease
    db.cronLocks.delete_many({"_id": "maintenance_sweeps_lease"})
    result2 = run_sweeps(db.name)
    assert result2["expired_holds_reclaimed"] == 0

    # Run 3: Idempotent stability check
    db.cronLocks.delete_many({"_id": "maintenance_sweeps_lease"})
    result3 = run_sweeps(db.name)
    assert result3["expired_holds_reclaimed"] == 0

def test_read_time_hold_expiry_and_promo_rejection_with_cron_disabled(test_setup):
    """
    Proves that expired holds and exhausted promos are strictly ignored at read time
    EVEN IF THE CRON JOB NEVER RUNS. The cron only acts as a janitor.
    """
    db = test_setup["db"]
    svc = test_setup["svc"]
    app = test_setup["app"]
    from app.services.catalog_service import CatalogService

    catalog_svc = CatalogService(
        package_repo=svc.package_repo,
        addon_repo=svc.addon_repo,
        offer_repo=svc.offer_repo,
        offer_redemption_repo=svc.offer_redemption_repo,
    )

    target_date = "2026-12-28"
    target_time = "14:00"
    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    buffer_end_utc = to_utc(parse_ist_datetime(target_date, "15:30"))

    # Explicitly clear out any existing claims for this slot
    db.slotClaims.delete_many({"roomId": "main", "slotStart": start_utc})
    db.bookingHolds.delete_many({"date": target_date, "startTime": target_time})

    import uuid
    from scripts.seed_offers import seed_offers

    # Step 1: Insert an expired hold directly into DB without running the cron job
    stale_hold_id = ObjectId()
    stale_expiry = now_utc() - timedelta(minutes=15)
    stale_session_token = str(uuid.uuid4())
    new_hold_id = None

    try:
        db.bookingHolds.insert_one({
            "_id": stale_hold_id,
            "roomId": "main",
            "date": target_date,
            "startTime": target_time,
            "durationHours": 1,
            "packageCode": "basic",
            "packageName": "Basic",
            "sessionToken": stale_session_token,
            "customer": {"name": "Unswept Hold", "phone": "+919876543210"},
            "pricing": {"totalAmountMinor": 99900},
            "status": "active",  # Status still marked active in DB!
            "expiresAt": stale_expiry,
            "createdAt": stale_expiry - timedelta(minutes=10)
        })
        db.slotClaims.insert_one({
            "roomId": "main",
            "slotStart": start_utc,
            "slotEnd": buffer_end_utc,
            "ownerType": "hold",
            "ownerId": stale_hold_id,
            "expiresAt": stale_expiry
        })

        # Assert that the cron sweeps job was NOT run (stale hold is still in bookingHolds as active)
        assert db.bookingHolds.find_one({"_id": stale_hold_id})["status"] == "active"

        # Step 2: Read availability at query time -> Expired hold must be ignored!
        avail = svc.get_availability(target_date, 1, "main")
        target_slot = next((s for s in avail["slots"] if s["startTime"] == target_time), None)
        assert target_slot is not None
        assert target_slot["available"] is True, "Expired hold must NOT block slot availability at read time"

        # Step 3: A new customer reserves the slot -> Succeeds without running cron!
        new_hold = svc.create_hold({
            "packageCode": "basic",
            "durationHours": 1,
            "date": target_date,
            "startTime": target_time,
            "customerName": "Fresh Customer",
            "customerPhone": "9876543299",
            "applyPromo": False
        })
        new_hold_id = new_hold.get("holdId")
        assert new_hold_id is not None
        assert new_hold_id != str(stale_hold_id)

        # Step 4: Prove exhausted promos are rejected at read time without cron
        db.offers.update_one(
            {"eligiblePackageCode": "basic"},
            {"$set": {"monthlyLimit": 5, "monthlyRedemptionCount": 5, "isActive": True}},
            upsert=True
        )
        quote = catalog_svc.calculate_quote("basic", 1, apply_promo=True)
        assert quote["promoApplied"] is False
        assert "already claimed" in quote["promoNotAppliedReason"]
    finally:
        db.bookingHolds.delete_many({"_id": stale_hold_id})
        db.slotClaims.delete_many({"roomId": "main", "slotStart": start_utc})
        if new_hold_id:
            db.bookingHolds.delete_many({"_id": ObjectId(new_hold_id)})
        seed_offers(db=db, dry_run=False)

