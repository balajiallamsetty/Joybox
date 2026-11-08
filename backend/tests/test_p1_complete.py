import os
import concurrent.futures
import pytest
from datetime import datetime, timedelta
from bson import ObjectId

from app import create_app
from app.utils.datetime_utils import now_utc, now_ist, to_utc, parse_ist_datetime, format_ist_date
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
    test_db.availabilityBlocks.delete_many({})
    yield
    test_db.slotClaims.delete_many({})
    test_db.bookings.delete_many({})
    test_db.bookingHolds.delete_many({})
    test_db.offerRedemptions.delete_many({})
    test_db.idempotencyKeys.delete_many({})
    test_db.rateLimits.delete_many({})
    test_db.availabilityBlocks.delete_many({})


@pytest.fixture
def app_client(live_test_client):
    test_db = live_test_client
    app = create_app({
        "TESTING": True,
        "MONGODB_URI": os.getenv("MONGODB_URI"),
        "MONGODB_DB": test_db.name
    })
    app.extensions["mongo_db"] = test_db
    with app.test_client() as c:
        yield c


# 1. same slot, two different dates: both bookings succeed
def test_same_slot_two_different_dates_both_succeed(app_client):
    res_a = app_client.post("/api/bookings", json={
        "date": "2026-12-10",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer Date A",
        "customerPhone": "9876543210"
    })
    assert res_a.status_code == 201

    res_b = app_client.post("/api/bookings", json={
        "date": "2026-12-11",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer Date B",
        "customerPhone": "9876543211"
    })
    assert res_b.status_code == 201


# 2. same slot, same date: second fails with the normal conflict result
def test_same_slot_same_date_second_fails_with_conflict(app_client):
    res_1 = app_client.post("/api/bookings", json={
        "date": "2026-12-10",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer 1",
        "customerPhone": "9876543210"
    })
    assert res_1.status_code == 201

    res_2 = app_client.post("/api/bookings", json={
        "date": "2026-12-10",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer 2",
        "customerPhone": "9876543211"
    })
    assert res_2.status_code == 409
    assert res_2.get_json()["error"]["code"] in ["SLOT_CONFLICT", "SLOT_UNAVAILABLE"]


# 3. availability for each date reflects only that date
def test_availability_reflects_only_that_date(app_client):
    res = app_client.post("/api/bookings", json={
        "date": "2026-12-10",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer Date A",
        "customerPhone": "9876543210"
    })
    assert res.status_code == 201

    # Date A: 18:00 is booked
    res_a = app_client.get("/api/availability?date=2026-12-10&durationHours=1")
    slots_a = {s["startTime"]: s for s in res_a.get_json()["data"]["slots"]}
    assert slots_a["18:00"]["available"] is False
    assert slots_a["18:00"]["unavailableReason"] == "booked"

    # Date B: 18:00 is free
    res_b = app_client.get("/api/availability?date=2026-12-11&durationHours=1")
    slots_b = {s["startTime"]: s for s in res_b.get_json()["data"]["slots"]}
    assert slots_b["18:00"]["available"] is True


# 4. multi-hour booking spanning several units is per-date
def test_multi_hour_booking_is_per_date(app_client):
    res_a = app_client.post("/api/bookings", json={
        "date": "2026-12-12",
        "startTime": "14:00",
        "durationHours": 3,
        "packageCode": "basic",
        "customerName": "Multi Hour A",
        "customerPhone": "9876543210"
    })
    assert res_a.status_code == 201

    # On Date A, 14:00, 15:00, 16:00 are unavailable
    res_avail_a = app_client.get("/api/availability?date=2026-12-12&durationHours=1")
    slots_a = {s["startTime"]: s for s in res_avail_a.get_json()["data"]["slots"]}
    assert slots_a["14:00"]["available"] is False
    assert slots_a["15:00"]["available"] is False
    assert slots_a["16:00"]["available"] is False

    # On Date B, all those slots are completely free
    res_avail_b = app_client.get("/api/availability?date=2026-12-13&durationHours=1")
    slots_b = {s["startTime"]: s for s in res_avail_b.get_json()["data"]["slots"]}
    assert slots_b["14:00"]["available"] is True
    assert slots_b["15:00"]["available"] is True
    assert slots_b["16:00"]["available"] is True


# 5. buffer applies within a date, not across dates
def test_buffer_applies_within_date_not_across_dates(app_client):
    # 21:00-22:00 booking has 30 min buffer extending to 22:30 on date A
    res = app_client.post("/api/bookings", json={
        "date": "2026-12-14",
        "startTime": "20:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Buffer Test",
        "customerPhone": "9876543210"
    })
    assert res.status_code == 201

    # On date A, buffer blocks 21:00 starting if a 2-hour duration is attempted, etc.
    # Buffer check: 20:00-21:00 is booked, buffer is 21:00-21:30.
    res_avail_a = app_client.get("/api/availability?date=2026-12-14&durationHours=1")
    slots_a = {s["startTime"]: s for s in res_avail_a.get_json()["data"]["slots"]}
    assert slots_a["20:00"]["available"] is False
    assert slots_a["21:00"]["available"] is False
    assert slots_a["21:00"]["unavailableReason"] in ["buffer", "booked"]

    # On next day (date B), opening slot 09:00 is completely free
    res_avail_b = app_client.get("/api/availability?date=2026-12-15&durationHours=1")
    slots_b = {s["startTime"]: s for s in res_avail_b.get_json()["data"]["slots"]}
    assert slots_b["09:00"]["available"] is True
    assert slots_b["20:00"]["available"] is True


# 6. cancel or expire a date-A booking: date-B booking of the same slot stays
def test_cancel_date_a_booking_leaves_date_b_booking_intact(app_client):
    res_a = app_client.post("/api/bookings", json={
        "date": "2026-12-16",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer A",
        "customerPhone": "9876543210"
    })
    assert res_a.status_code == 201
    ref_a = res_a.get_json()["data"]["bookingReference"]
    token_a = res_a.get_json()["data"]["accessToken"]

    res_b = app_client.post("/api/bookings", json={
        "date": "2026-12-17",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer B",
        "customerPhone": "9876543211"
    })
    assert res_b.status_code == 201
    ref_b = res_b.get_json()["data"]["bookingReference"]
    token_b = res_b.get_json()["data"]["accessToken"]

    # Cancel booking on Date A
    cancel_res = app_client.post(f"/api/bookings/{ref_a}/cancel", json={
        "token": token_a,
        "reason": "Customer cancellation"
    })
    assert cancel_res.status_code == 200

    # Date A is now free
    res_avail_a = app_client.get("/api/availability?date=2026-12-16&durationHours=1")
    slots_a = {s["startTime"]: s for s in res_avail_a.get_json()["data"]["slots"]}
    assert slots_a["18:00"]["available"] is True

    # Date B remains booked and confirmed/active
    res_avail_b = app_client.get("/api/availability?date=2026-12-17&durationHours=1")
    slots_b = {s["startTime"]: s for s in res_avail_b.get_json()["data"]["slots"]}
    assert slots_b["18:00"]["available"] is False
    assert slots_b["18:00"]["unavailableReason"] == "booked"


# 7. sweep/expiry releases only the claims of the expired booking
def test_sweep_releases_only_expired_claims(app_client, live_test_client):
    test_db = live_test_client

    # Create active booking on Date A
    res_a = app_client.post("/api/bookings", json={
        "date": "2026-12-18",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Active Booking",
        "customerPhone": "9876543210"
    })
    assert res_a.status_code == 201
    booking_id_a = res_a.get_json()["data"]["bookingReference"]

    # Create hold on Date B and manually expire it
    hold_res = app_client.post("/api/bookings/hold", json={
        "date": "2026-12-19",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Hold Booking",
        "customerPhone": "9876543211"
    })
    assert hold_res.status_code == 201
    hold_id_str = hold_res.get_json()["data"]["holdId"]

    # Backdate the hold's expiresAt to 10 minutes ago
    past_time = now_utc() - timedelta(minutes=10)
    test_db.bookingHolds.update_one({"_id": ObjectId(hold_id_str)}, {"$set": {"expiresAt": past_time}})
    test_db.slotClaims.update_many({"ownerId": ObjectId(hold_id_str)}, {"$set": {"expiresAt": past_time}})

    # Trigger sweep via GET /api/availability
    app_client.get("/api/availability?date=2026-12-19&durationHours=1")

    # Date B slot is now released (available)
    res_b = app_client.get("/api/availability?date=2026-12-19&durationHours=1")
    slots_b = {s["startTime"]: s for s in res_b.get_json()["data"]["slots"]}
    assert slots_b["18:00"]["available"] is True

    # Date A slot remains booked!
    res_a = app_client.get("/api/availability?date=2026-12-18&durationHours=1")
    slots_a = {s["startTime"]: s for s in res_a.get_json()["data"]["slots"]}
    assert slots_a["18:00"]["available"] is False


# 8. idempotent replay returns the right booking; same key with different date is rejected as payload mismatch
def test_idempotent_replay_and_date_mismatch_rejected(app_client):
    idemp_key = "idemp_date_test_key_9999"
    headers = {"Idempotency-Key": idemp_key}
    payload_a = {
        "date": "2026-12-20",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer Idemp",
        "customerPhone": "9876543210"
    }
    # 1. First execution
    res1 = app_client.post("/api/bookings", json=payload_a, headers=headers)
    assert res1.status_code == 201
    ref1 = res1.get_json()["data"]["bookingReference"]

    # 2. Replay with identical body -> same booking replayed
    res2 = app_client.post("/api/bookings", json=payload_a, headers=headers)
    assert res2.status_code == 201
    assert res2.get_json()["data"]["bookingReference"] == ref1

    # 3. Same idempotency key with DIFFERENT date -> 422 IDEMPOTENCY_PAYLOAD_MISMATCH
    payload_b = dict(payload_a)
    payload_b["date"] = "2026-12-21"
    res3 = app_client.post("/api/bookings", json=payload_b, headers=headers)
    assert res3.status_code == 422
    assert res3.get_json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"


# 9. admin block on date A does not block date B
def test_admin_block_on_date_a_does_not_block_date_b(app_client, live_test_client):
    test_db = live_test_client
    # Insert an admin block directly into DB on Date A
    block_id = ObjectId()
    start_utc = to_utc(parse_ist_datetime("2026-12-22", "18:00"))
    end_utc = to_utc(parse_ist_datetime("2026-12-22", "19:00"))
    now_u = now_utc()

    test_db.availabilityBlocks.insert_one({
        "_id": block_id,
        "roomId": "main",
        "startAt": start_utc,
        "endAt": end_utc,
        "reason": "Emergency maintenance",
        "createdAt": now_u
    })
    test_db.slotClaims.insert_one({
        "roomId": "main",
        "date": "2026-12-22",
        "slotStart": start_utc,
        "slotEnd": end_utc,
        "isBuffer": False,
        "ownerType": "block",
        "ownerId": block_id,
        "createdAt": now_u,
        "expiresAt": None
    })

    # Check Date A: 18:00 is unavailable
    res_a = app_client.get("/api/availability?date=2026-12-22&durationHours=1")
    slots_a = {s["startTime"]: s for s in res_a.get_json()["data"]["slots"]}
    assert slots_a["18:00"]["available"] is False

    # Check Date B: 18:00 is available
    res_b = app_client.get("/api/availability?date=2026-12-23&durationHours=1")
    slots_b = {s["startTime"]: s for s in res_b.get_json()["data"]["slots"]}
    assert slots_b["18:00"]["available"] is True


# 10. concurrency: 20 threads on same slot same date -> exactly 1 winner; 20 threads split across two dates -> exactly 2 winners
def test_concurrency_split_across_two_dates_gives_two_winners(live_test_client):
    test_db = live_test_client
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    def try_book(thread_idx, date_val):
        with app.test_client() as c:
            res = c.post(
                "/api/bookings",
                json={
                    "date": date_val,
                    "startTime": "18:00",
                    "durationHours": 1,
                    "packageCode": "basic",
                    "customerName": f"Concurrent User {thread_idx}",
                    "customerPhone": f"987654{thread_idx:04d}"
                },
                headers={"X-Forwarded-For": f"192.168.1.{thread_idx}"}
            )
            return date_val, res.status_code

    # 10 workers for date A (2026-12-24), 10 workers for date B (2026-12-25)
    tasks = []
    for i in range(10):
        tasks.append((i, "2026-12-24"))
    for i in range(10, 20):
        tasks.append((i, "2026-12-25"))

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(try_book, idx, d) for idx, d in tasks]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    date_a_results = [code for d, code in results if d == "2026-12-24"]
    date_b_results = [code for d, code in results if d == "2026-12-25"]

    assert date_a_results.count(201) == 1, f"Expected 1 winner for Date A, got {date_a_results.count(201)}"
    assert date_a_results.count(409) == 9

    assert date_b_results.count(201) == 1, f"Expected 1 winner for Date B, got {date_b_results.count(201)}"
    assert date_b_results.count(409) == 9


# 11. date round-trip: a date picked near midnight IST arrives on server as same calendar date
def test_date_round_trip_near_midnight_ist(app_client):
    # Picking late slot 21:00 on 2026-12-31 (ends at 22:00 IST)
    # In UTC, 21:00 IST is 15:30 UTC on 2026-12-31.
    res = app_client.post("/api/bookings", json={
        "date": "2026-12-31",
        "startTime": "21:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "New Year Eve Host",
        "customerPhone": "9876543210"
    })
    assert res.status_code == 201
    booking_ref = res.get_json()["data"]["bookingReference"]
    token = res.get_json()["data"]["accessToken"]

    # Lookup booking
    lookup_res = app_client.get(f"/api/bookings/{booking_ref}?token={token}")
    assert lookup_res.status_code == 200
    booking_data = lookup_res.get_json()["data"]
    assert "2026-12-31" in booking_data["startTimeIst"]
    assert "2026-12-31" in booking_data["endTimeIst"]

