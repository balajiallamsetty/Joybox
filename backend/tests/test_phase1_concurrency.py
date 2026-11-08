"""
Phase 1.3 Concurrency Test Suite
Author: Principal Engineer, Application-Security Auditor & QA Lead
Target Database: joybox_party_room_test (Atlas)

Objective:
Verify atomic slot claim concurrency under high contention:
- 20 parallel threads synchronized with threading.Barrier(20) racing for the exact same slot.
- Test 1: 20 parallel workers racing to acquire a booking hold (/api/bookings/hold).
- Test 2: 20 parallel workers racing to create a direct booking (/api/bookings).
- In both tests:
    - EXACTLY 1 worker succeeds (HTTP 201 Created).
    - EXACTLY 19 workers receive clean conflict (HTTP 409 Conflict with code SLOT_CONFLICT / SLOT_UNAVAILABLE).
    - Database verification: exactly 1 winner record, exactly 1 set of unit slot claims (3 claims for 1h + 30m buffer), 0 orphan locks.
"""

import os
import uuid
import threading
import concurrent.futures
from bson import ObjectId
import pytest
from app import create_app
from app.utils.datetime_utils import parse_ist_datetime, to_utc
from app.utils.db_safety import assert_live_test_client


@pytest.fixture
def test_app(live_test_client):
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db
    return app, test_db


def test_twenty_parallel_threads_racing_for_hold(test_app):
    """
    BL-05 / BL-06: 20 parallel threads synchronized by Barrier race for the same hold slot.
    Assert:
    - Exactly 1 winner receives HTTP 201.
    - Exactly 19 receive HTTP 409 Conflict.
    - Exactly 3 slot claims in slotClaims collection (1h + 30m buffer = 3 x 30m intervals).
    - Exactly 0 orphan slot claims.
    """
    app, test_db = test_app
    concurrency_count = 20
    barrier = threading.Barrier(concurrency_count)
    target_date = "2026-12-15"
    target_time = "14:00"
    unique_run = uuid.uuid4().hex[:6]

    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    buffer_end_utc = to_utc(parse_ist_datetime(target_date, "15:30"))

    # Pre-clean any leftover claims for target slot
    test_db.slotClaims.delete_many({
        "roomId": "main",
        "slotStart": {"$gte": start_utc, "$lt": buffer_end_utc}
    })
    test_db.bookingHolds.delete_many({"roomId": "main", "date": target_date})

    def worker_race(worker_idx):
        # Synchronize all threads so they release at the exact same instant
        barrier.wait()
        with app.test_client() as client:
            res = client.post(
                "/api/bookings/hold",
                json={
                    "roomId": "main",
                    "date": target_date,
                    "startTime": target_time,
                    "durationHours": 1,
                    "packageCode": "basic",
                    "customerName": f"Hold Contender {unique_run}_{worker_idx}",
                    "customerPhone": f"+9198765{worker_idx:05d}"
                },
                headers={"X-Forwarded-For": f"10.20.{worker_idx // 256}.{worker_idx % 256 + 1}"}
            )
            return res.status_code, res.get_json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_count) as executor:
        futures = [executor.submit(worker_race, i) for i in range(concurrency_count)]
        results = [f.result() for f in futures]

    status_codes = [s for s, _ in results]
    successes = [(s, body) for s, body in results if s == 201]
    conflicts = [(s, body) for s, body in results if s == 409]

    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}. Status codes: {status_codes}"
    assert len(conflicts) == 19, f"Expected exactly 19 conflicts, got {len(conflicts)}. Status codes: {status_codes}"

    winner_hold_id = successes[0][1]["data"]["holdId"]

    # Verify all conflicts have clean structured error payload
    for _, conf in conflicts:
        code = conf.get("error", {}).get("code")
        assert code in ("SLOT_CONFLICT", "SLOT_UNAVAILABLE"), f"Unexpected conflict code: {code}"

    # Database state verification
    # 1h duration + 30 min buffer = 3 x 30m slots: 14:00-14:30, 14:30-15:00, 15:00-15:30 IST
    claims = list(test_db.slotClaims.find({
        "roomId": "main",
        "slotStart": {"$gte": start_utc, "$lt": buffer_end_utc}
    }))
    assert len(claims) == 3, f"Expected exactly 3 slot claims in DB, found {len(claims)}"

    for c in claims:
        assert c["ownerType"] == "hold"
        assert str(c["ownerId"]) == winner_hold_id

    # Verify exactly 1 hold document exists and matches winner ID
    all_holds = list(test_db.bookingHolds.find({"roomId": "main", "date": target_date}))
    assert len(all_holds) == 1
    assert str(all_holds[0]["_id"]) == winner_hold_id


def test_twenty_parallel_threads_racing_for_direct_booking(test_app):
    """
    BL-05 / BL-06: 20 parallel threads synchronized by Barrier race for direct booking creation.
    Assert:
    - Exactly 1 winner receives HTTP 201 Created.
    - Exactly 19 receive HTTP 409 Conflict.
    - Database verification: exactly 1 booking created, exactly 3 booked slot claims, 0 orphan locks.
    """
    app, test_db = test_app
    concurrency_count = 20
    barrier = threading.Barrier(concurrency_count)
    target_date = "2026-12-16"
    target_time = "16:00"
    unique_run = uuid.uuid4().hex[:6]

    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    buffer_end_utc = to_utc(parse_ist_datetime(target_date, "17:30"))

    # Pre-clean any leftover claims for target slot
    test_db.slotClaims.delete_many({
        "roomId": "main",
        "slotStart": {"$gte": start_utc, "$lt": buffer_end_utc}
    })
    test_db.bookings.delete_many({
        "roomId": "main",
        "startAt": start_utc
    })

    def worker_race(worker_idx):
        barrier.wait()
        with app.test_client() as client:
            res = client.post(
                "/api/bookings",
                json={
                    "roomId": "main",
                    "date": target_date,
                    "startTime": target_time,
                    "durationHours": 1,
                    "packageCode": "gold",
                    "customerName": f"Direct Contender {unique_run}_{worker_idx}",
                    "customerPhone": f"+9198766{worker_idx:05d}"
                },
                headers={"X-Forwarded-For": f"10.30.{worker_idx // 256}.{worker_idx % 256 + 1}"}
            )
            return res.status_code, res.get_json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_count) as executor:
        futures = [executor.submit(worker_race, i) for i in range(concurrency_count)]
        results = [f.result() for f in futures]

    status_codes = [s for s, _ in results]
    successes = [(s, body) for s, body in results if s == 201]
    conflicts = [(s, body) for s, body in results if s == 409]

    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}. Status codes: {status_codes}"
    assert len(conflicts) == 19, f"Expected exactly 19 conflicts, got {len(conflicts)}. Status codes: {status_codes}"

    winner_booking_id = successes[0][1]["data"]["bookingId"]

    # Verify all conflicts have clean structured error payload
    for _, conf in conflicts:
        code = conf.get("error", {}).get("code")
        assert code in ("SLOT_CONFLICT", "SLOT_UNAVAILABLE"), f"Unexpected conflict code: {code}"

    # Database state verification
    # Exactly 1 booking in database matching winner_booking_id
    bookings = list(test_db.bookings.find({"_id": ObjectId(winner_booking_id)}))
    assert len(bookings) == 1, f"Expected 1 booking document, found {len(bookings)}"
    assert str(bookings[0]["_id"]) == winner_booking_id

    # Exactly 3 slot claims in database, all marked booked and referencing winner booking ID
    claims = list(test_db.slotClaims.find({
        "roomId": "main",
        "slotStart": {"$gte": start_utc, "$lt": buffer_end_utc}
    }))
    assert len(claims) == 3, f"Expected exactly 3 claims in DB, found {len(claims)}"

    for c in claims:
        assert c["ownerType"] == "booking"
        assert str(c["ownerId"]) == winner_booking_id

    # 0 orphan locks
    orphan_claims = list(test_db.slotClaims.find({
        "roomId": "main",
        "slotStart": {"$gte": start_utc, "$lt": buffer_end_utc},
        "ownerId": {"$ne": ObjectId(winner_booking_id)}
    }))
    assert len(orphan_claims) == 0, f"Found orphan claims: {orphan_claims}"
