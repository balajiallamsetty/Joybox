import os
import uuid
import concurrent.futures
import pytest
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from app import create_app
from app.utils.datetime_utils import now_utc, now_ist, to_utc, parse_ist_datetime
from app.utils.db_safety import assert_live_test_client


@pytest.fixture(autouse=True)
def clean_test_collections(live_test_client):
    """Clean all test collections before and after each test."""
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    test_db.slotClaims.delete_many({})
    test_db.bookings.delete_many({})
    test_db.bookingHolds.delete_many({})
    test_db.offerRedemptions.delete_many({})
    test_db.idempotencyKeys.delete_many({})
    test_db.rateLimits.delete_many({})
    yield
    test_db.slotClaims.delete_many({})
    test_db.bookings.delete_many({})
    test_db.bookingHolds.delete_many({})
    test_db.offerRedemptions.delete_many({})
    test_db.idempotencyKeys.delete_many({})
    test_db.rateLimits.delete_many({})


def test_atlas_partial_claim_rollback(live_test_client):
    """
    Partial-claim rollback on real MongoDB Atlas:
    If a 2-hour celebration finds hour 1 free but hour 2 blocked,
    atomic rollback deletes hour 1 claim so 0 orphaned slot claims remain.
    """
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    target_date = "2026-12-15"
    start_time_h1 = "10:00"
    start_time_h2 = "11:00"

    # Pre-claim hour 2 with an existing booking
    h2_utc = to_utc(parse_ist_datetime(target_date, start_time_h2))
    blocker_booking_id = ObjectId()
    test_db.slotClaims.insert_one({
        "roomId": "main",
        "date": target_date,
        "slotStart": h2_utc,
        "slotEnd": h2_utc + timedelta(hours=1),
        "isBuffer": False,
        "ownerType": "booking",
        "ownerId": blocker_booking_id,
        "createdAt": now_utc(),
        "expiresAt": None
    })

    # Now attempt a 2-hour booking starting at 10:00 (needs 10:00-11:00 AND 11:00-12:00)
    with app.test_client() as c:
        res = c.post("/api/bookings", json={
            "roomId": "main",
            "date": target_date,
            "startTime": start_time_h1,
            "durationHours": 2,
            "packageCode": "basic",
            "customerName": "Ravi",
            "customerPhone": "9876543210"
        })
        assert res.status_code == 409
        assert res.get_json()["error"]["code"] == "SLOT_CONFLICT"

    # Verify atomic rollback: hour 1 claim (10:00) must NOT exist in Atlas
    h1_utc = to_utc(parse_ist_datetime(target_date, start_time_h1))
    h1_claims = list(test_db.slotClaims.find({"roomId": "main", "slotStart": h1_utc}))
    assert len(h1_claims) == 0, f"Expected 0 orphaned claims for hour 1, found {len(h1_claims)}"


def test_atlas_expired_hold_conditional_reclaim(live_test_client):
    """
    Expired-hold reclaim on real MongoDB Atlas:
    An expired hold on a slot is cleanly reclaimed by a new reservation.
    Old hold is transitioned to expired, old claims deleted, new claim created.
    """
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    target_date = "2026-12-16"
    target_time = "14:00"
    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    end_utc = start_utc + timedelta(hours=1)
    buffer_utc = end_utc + timedelta(minutes=30)

    old_hold_id = ObjectId()
    # Insert expired hold (expired 5 minutes ago)
    test_db.bookingHolds.insert_one({
        "_id": old_hold_id,
        "roomId": "main",
        "startAt": start_utc,
        "endAt": end_utc,
        "bufferEndAt": buffer_utc,
        "status": "active",
        "createdAt": now_utc() - timedelta(minutes=15),
        "expiresAt": now_utc() - timedelta(minutes=5)
    })
    # Insert expired slot claims
    test_db.slotClaims.insert_one({
        "roomId": "main",
        "date": target_date,
        "slotStart": start_utc,
        "slotEnd": end_utc,
        "isBuffer": False,
        "ownerType": "hold",
        "ownerId": old_hold_id,
        "createdAt": now_utc() - timedelta(minutes=15),
        "expiresAt": now_utc() - timedelta(minutes=5)
    })

    # New customer books the exact same slot
    with app.test_client() as c:
        res = c.post("/api/bookings", json={
            "roomId": "main",
            "date": target_date,
            "startTime": target_time,
            "durationHours": 1,
            "packageCode": "basic",
            "customerName": "Suresh",
            "customerPhone": "9876543211"
        })
        assert res.status_code == 201

    # Verify old hold marked expired (or already purged by Atlas native TTL index)
    old_h = test_db.bookingHolds.find_one({"_id": old_hold_id})
    if old_h is not None:
        assert old_h["status"] == "expired"

    # Verify new booking owns the slot claim
    new_claims = list(test_db.slotClaims.find({"roomId": "main", "slotStart": start_utc}))
    assert len(new_claims) == 1
    assert new_claims[0]["ownerType"] == "booking"
    assert new_claims[0]["ownerId"] != old_hold_id


def test_atlas_promo_quota_exhaustion_concurrent(live_test_client):
    """
    Promo quota exhaustion on real MongoDB Atlas:
    8 concurrent requests for 5 available promo allocations:
    Exactly 5 receive the promo discount; remaining 3 fall back to regular price.
    Atlas offers collection monthlyRedemptionCount is capped at exactly 5.
    """
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    # Reset promo offer in test DB to 0 redemptions with limit 5
    test_db.offers.update_one(
        {"eligiblePackageCode": "basic"},
        {"$set": {"monthlyRedemptionCount": 0, "monthlyLimit": 5, "isActive": True}},
        upsert=True
    )

    def attempt_promo_booking(worker_idx):
        with app.test_client() as c:
            # Different dates to completely avoid slot/buffer collisions, isolating promo quota concurrency
            target_date = f"2026-12-{10 + worker_idx:02d}"
            res = c.post(
                "/api/bookings",
                json={
                    "roomId": "main",
                    "date": target_date,
                    "startTime": "10:00",
                    "durationHours": 1,
                    "packageCode": "basic",
                    "applyPromo": True,
                    "customerName": f"PromoUser {worker_idx}",
                    "customerPhone": f"9876540{worker_idx:03d}"
                },
                headers={"X-Forwarded-For": f"10.0.1.{worker_idx}"}
            )
            data = res.get_json().get("data") or {}
            pricing = data.get("pricing", {})
            return pricing.get("promoApplied", False)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(attempt_promo_booking, i) for i in range(8)]
        results = [f.result() for f in futures]

    promo_granted = results.count(True)
    promo_denied = results.count(False)

    assert promo_granted == 5, f"Expected exactly 5 promo grants, got {promo_granted}"
    assert promo_denied == 3, f"Expected 3 promo denials, got {promo_denied}"

    # Verify database counter on Atlas is exactly 5
    offer_doc = test_db.offers.find_one({"eligiblePackageCode": "basic"})
    assert offer_doc["monthlyRedemptionCount"] == 5


def test_atlas_same_key_concurrent_idempotency(live_test_client):
    """
    Same-key concurrent idempotency on real MongoDB Atlas:
    Multiple threads submit the identical booking with the SAME Idempotency-Key.
    Exactly 1 executes and creates the booking; others get 409 or the identical response.
    Exactly 1 booking document and 1 slot claim created in Atlas.
    """
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    unique_run_id = uuid.uuid4().hex[:8]
    shared_key = f"idemp_atlas_{unique_run_id}"
    target_date = "2026-12-25"
    target_time = "16:00"

    payload = {
        "roomId": "main",
        "date": target_date,
        "startTime": target_time,
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Idempotent User",
        "customerPhone": "9876543299"
    }

    def send_idempotent_request(worker_idx):
        with app.test_client() as c:
            res = c.post(
                "/api/bookings",
                json=payload,
                headers={
                    "Idempotency-Key": shared_key,
                    "X-Forwarded-For": f"10.0.2.{worker_idx}"
                }
            )
            return res.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(send_idempotent_request, i) for i in range(5)]
        status_codes = [f.result() for f in futures]

    # Exactly 1 request successfully created (201); any in-flight collisions returned 409
    assert status_codes.count(201) == 1, f"Expected 1 creation, got {status_codes.count(201)}"

    # Verify exactly 1 booking exists in Atlas for this customer phone
    bookings = list(test_db.bookings.find({"customer.phone": "9876543299"}))
    assert len(bookings) == 1, f"Expected exactly 1 booking doc, found {len(bookings)}"


def test_atlas_real_contention_same_slot_one_winner(live_test_client):
    """
    Proves real contention on MongoDB Atlas (T3 requirement):
    10 threads simultaneously attempt to book the exact same room, date, and time slot.
    Atomic compound unique index on slotClaims guarantees:
    - EXACTLY ONE thread wins and receives HTTP 201 Created.
    - EXACTLY 9 threads receive HTTP 409 Conflict (SLOT_CONFLICT).
    - Exactly 1 booking document and 1 slot claim exist in Atlas.
    """
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    unique_run = uuid.uuid4().hex[:6]
    target_date = "2026-12-28"
    target_time = "18:00"

    def attempt_booking(worker_idx):
        with app.test_client() as c:
            res = c.post(
                "/api/bookings",
                json={
                    "roomId": "main",
                    "date": target_date,
                    "startTime": target_time,
                    "durationHours": 1,
                    "packageCode": "basic",
                    "customerName": f"Contender {unique_run}_{worker_idx}",
                    "customerPhone": f"987650{worker_idx:04d}"
                },
                headers={"X-Forwarded-For": f"10.10.{worker_idx // 256}.{worker_idx % 256 + 1}"}
            )
            return res.status_code, res.get_json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_booking, i) for i in range(10)]
        results = [f.result() for f in futures]

    status_codes = [status for status, _ in results]
    successes = [res for status, res in results if status == 201]
    conflicts = [res for status, res in results if status == 409]

    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}. Statuses: {status_codes}"
    assert len(conflicts) == 9, f"Expected exactly 9 conflicts, got {len(conflicts)}. Statuses: {status_codes}"

    for conf in conflicts:
        assert conf.get("error", {}).get("code") in ("SLOT_CONFLICT", "SLOT_UNAVAILABLE")

    # Verify exactly 1 booking exists in the database for that date and time
    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    bookings = list(test_db.bookings.find({"roomId": "main", "startAt": start_utc}))
    assert len(bookings) == 1, f"Expected exactly 1 booking in database, found {len(bookings)}"

    claims = list(test_db.slotClaims.find({"roomId": "main", "slotStart": start_utc}))
    assert len(claims) == 1, f"Expected exactly 1 claim in database, found {len(claims)}"
