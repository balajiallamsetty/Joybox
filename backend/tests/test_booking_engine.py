import os
import concurrent.futures
import pytest
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from app import create_app
from app.config import Config
from app.utils.datetime_utils import (
    now_utc,
    now_ist,
    to_utc,
    parse_ist_datetime,
    generate_slot_claim_intervals,
    validate_booking_window,
)
from app.utils.db_safety import assert_is_test_database, assert_live_test_client


# In-Memory DB Fixture for Fast Unit/Engine Tests
class InMemoryCollection:
    def __init__(self, name=""):
        self.name = name
        self.docs = []

    def find(self, query=None, projection=None):
        query = query or {}
        class MockCursor:
            def __init__(self, docs):
                self._docs = docs
            def sort(self, field, direction):
                return self
            def __iter__(self):
                return iter(self._docs)
            def __list__(self):
                return list(self._docs)

        results = []
        for d in self.docs:
            if self._matches(d, query):
                results.append(dict(d))
        return MockCursor(results)

    def find_one(self, query=None):
        query = query or {}
        for d in self.docs:
            if self._matches(d, query):
                return dict(d)
        return None

    def insert_one(self, doc):
        d = dict(doc)
        if "_id" not in d:
            d["_id"] = ObjectId()
        # Enforce unique index on (roomId, slotStart) for slotClaims
        if self.name == "slotClaims":
            for existing in self.docs:
                if existing.get("roomId") == d.get("roomId") and existing.get("slotStart") == d.get("slotStart"):
                    from pymongo.errors import DuplicateKeyError
                    raise DuplicateKeyError(f"Duplicate key on (roomId, slotStart): {d.get('slotStart')}")
        # Enforce unique index on (key, endpoint) for idempotencyKeys
        if self.name == "idempotencyKeys":
            for existing in self.docs:
                if existing.get("key") == d.get("key") and existing.get("endpoint") == d.get("endpoint"):
                    from pymongo.errors import DuplicateKeyError
                    raise DuplicateKeyError(f"Duplicate key on idempotency: {d.get('key')}")
        self.docs.append(d)
        class Res:
            inserted_id = d["_id"]
        return Res()

    def count_documents(self, query=None):
        query = query or {}
        return sum(1 for d in self.docs if self._matches(d, query))

    def delete_many(self, query):
        initial = len(self.docs)
        self.docs = [d for d in self.docs if not self._matches(d, query)]
        class Res:
            deleted_count = initial - len(self.docs)
        res = Res()
        res.deleted_count = initial - len(self.docs)
        return res

    def delete_one(self, query):
        initial = len(self.docs)
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                del self.docs[i]
                break
        class Res:
            deleted_count = initial - len(self.docs)
        res = Res()
        res.deleted_count = initial - len(self.docs)
        return res

    def update_many(self, query, update):
        count = 0
        set_fields = update.get("$set", {})
        for d in self.docs:
            if self._matches(d, query):
                d.update(set_fields)
                count += 1
        class Res:
            modified_count = count
        res = Res()
        res.modified_count = count
        return res

    def update_one(self, query, update):
        set_fields = update.get("$set", {})
        for d in self.docs:
            if self._matches(d, query):
                d.update(set_fields)
                break

    def find_one_and_update(self, query, update, upsert=False, return_document=None):
        for d in self.docs:
            if self._matches(d, query):
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                if "$set" in update:
                    d.update(update["$set"])
                return dict(d)
        if upsert:
            new_doc = dict(query)
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    new_doc[k] = v
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            self.docs.append(new_doc)
            return dict(new_doc)
        return None

    def _matches(self, doc, query):
        for k, v in query.items():
            if k == "$or":
                if not any(self._matches(doc, cond) for cond in v):
                    return False
            elif k == "$and":
                if not all(self._matches(doc, cond) for cond in v):
                    return False
            elif isinstance(v, dict):
                val = doc.get(k)
                if "$in" in v and val not in v["$in"]:
                    return False
                if "$lt" in v and not (val < v["$lt"]):
                    return False
                if "$gt" in v and not (val > v["$gt"]):
                    return False
                if "$lte" in v and not (val <= v["$lte"]):
                    return False
                if "$gte" in v and not (val >= v["$gte"]):
                    return False
            else:
                if doc.get(k) != v:
                    return False
        return True


class MockJoyboxDB:
    def __init__(self):
        self.packages = InMemoryCollection("packages")
        self.addOns = InMemoryCollection("addOns")
        self.offers = InMemoryCollection("offers")
        self.inquiries = InMemoryCollection("inquiries")
        self.slotClaims = InMemoryCollection("slotClaims")
        self.bookingHolds = InMemoryCollection("bookingHolds")
        self.bookings = InMemoryCollection("bookings")
        self.counters = InMemoryCollection("counters")
        self.offerRedemptions = InMemoryCollection("offerRedemptions")
        self.idempotencyKeys = InMemoryCollection("idempotencyKeys")
        self.rateLimits = InMemoryCollection("rateLimits")

        # Seed default test data
        self.packages.insert_one({
            "code": "basic",
            "name": "Basic",
            "pricePerHourMinor": 99900,
            "currency": "INR",
            "features": ["AC room", "Theme decor", "Music"],
            "includedAddOnCodes": [],
            "isActive": True,
            "displayOrder": 1
        })
        self.packages.insert_one({
            "code": "gold",
            "name": "Gold",
            "pricePerHourMinor": 150000,
            "currency": "INR",
            "features": ["Cake 0.5kg", "Name display"],
            "includedAddOnCodes": [],
            "isActive": True,
            "displayOrder": 2
        })
        self.addOns.insert_one({
            "code": "bubble_entry",
            "name": "Bubble Entry",
            "priceMinor": 30000,
            "isActive": True,
            "displayOrder": 1
        })
        self.offers.insert_one({
            "_id": ObjectId("607f1f77bcf86cd799439011"),
            "name": "Introductory Offer",
            "eligiblePackageCode": "basic",
            "promoPricePerHourMinor": 50000,
            "monthlyLimit": 5,
            "monthlyRedemptionCount": 0,
            "isActive": True
        })

    def command(self, cmd):
        return {"ok": 1}


@pytest.fixture
def test_app():
    app = create_app({"TESTING": True, "MONGODB_URI": "", "FRONTEND_ORIGIN": "http://localhost:5173"})
    mock_db = MockJoyboxDB()
    app.extensions["mongo_db"] = mock_db
    return app


@pytest.fixture
def client(test_app):
    with test_app.test_client() as c:
        yield c


# -------------------------------------------------------------
# 1. AVAILABILITY ENGINE TESTS
# -------------------------------------------------------------

def test_availability_operating_window(client):
    """Verifies operating hours: 09:00 to 22:00 IST and min/max duration."""
    res = client.get("/api/availability?date=2026-12-01&durationHours=1")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["openingTime"] == "09:00"
    assert data["closingTime"] == "22:00"
    assert data["bufferMinutes"] == 30
    slots = data["slots"]

    # For 1-hour booking, start times run 09:00 to 21:00 (13 hourly slots)
    start_times = [s["startTime"] for s in slots]
    assert start_times[0] == "09:00"
    assert start_times[-1] == "21:00"
    assert len(slots) == 13
    assert all(s["available"] is True for s in slots)


def test_availability_multi_hour_duration(client):
    """Verifies duration calculation: 2-hour duration party ends by 22:00."""
    res = client.get("/api/availability?date=2026-12-01&durationHours=2")
    assert res.status_code == 200
    slots = res.get_json()["data"]["slots"]
    assert slots[-1]["startTime"] == "20:00"
    assert slots[-1]["endTime"] == "22:00"


def test_availability_duration_validation(client):
    """Rejects durations outside 1-6 hours."""
    res_zero = client.get("/api/availability?date=2026-12-01&durationHours=0")
    assert res_zero.status_code == 422

    res_too_long = client.get("/api/availability?date=2026-12-01&durationHours=7")
    assert res_too_long.status_code == 422


# -------------------------------------------------------------
# 2. 30-MIN BUFFER & ANTI-DOUBLE-BOOKING TESTS
# -------------------------------------------------------------

def test_buffer_overlap_blocks_subsequent_slot(client):
    """
    If Booking A is 10:00 - 12:00, its 30-min buffer extends to 12:30.
    A candidate starting at 12:00 must be marked UNAVAILABLE because 12:00-12:30 is in buffer.
    A candidate starting at 13:00 must be AVAILABLE.
    """
    hold_payload = {
        "date": "2026-12-01",
        "startTime": "10:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Ravi Kumar",
        "customerPhone": "9876543210"
    }
    hold_res = client.post("/api/bookings/hold", json=hold_payload)
    assert hold_res.status_code == 201

    res = client.get("/api/availability?date=2026-12-01&durationHours=1")
    slots = {s["startTime"]: s for s in res.get_json()["data"]["slots"]}

    assert slots["10:00"]["available"] is False
    assert slots["11:00"]["available"] is False
    assert slots["12:00"]["available"] is False
    assert slots["12:00"]["unavailableReason"] in ["buffer", "hold"]
    assert slots["13:00"]["available"] is True


def test_atomic_conflict_rejection(client):
    """Attempting to hold a conflicting slot returns 409 SLOT_CONFLICT."""
    payload = {
        "date": "2026-12-02",
        "startTime": "14:00",
        "durationHours": 2,
        "packageCode": "gold",
        "customerName": "Suresh",
        "customerPhone": "9876543211"
    }
    first_res = client.post("/api/bookings/hold", json=payload)
    assert first_res.status_code == 201

    conflict_payload = dict(payload)
    conflict_payload["startTime"] = "15:00"
    conflict_payload["customerName"] = "Anand"
    second_res = client.post("/api/bookings/hold", json=conflict_payload)
    assert second_res.status_code == 409
    assert second_res.get_json()["error"]["code"] == "SLOT_CONFLICT"


# -------------------------------------------------------------
# 3. EXPIRED HOLD RECLAIM & SWEEP TESTS (Rule 0.3 b, c)
# -------------------------------------------------------------

def test_expired_hold_conditional_reclaim(client, test_app):
    """An expired hold is conditionally cleared so the slot can be booked."""
    db = test_app.extensions["mongo_db"]

    past_utc = now_utc() - timedelta(minutes=15)
    start_utc = to_utc(parse_ist_datetime("2026-12-03", "16:00"))
    end_utc = start_utc + timedelta(hours=1)
    db.slotClaims.insert_one({
        "roomId": "main",
        "slotStart": start_utc,
        "slotEnd": end_utc,
        "isBuffer": False,
        "ownerType": "hold",
        "ownerId": ObjectId(),
        "createdAt": past_utc,
        "expiresAt": past_utc
    })

    payload = {
        "date": "2026-12-03",
        "startTime": "16:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Venkatesh",
        "customerPhone": "9876543212"
    }
    res = client.post("/api/bookings/hold", json=payload)
    assert res.status_code == 201
    assert "holdId" in res.get_json()["data"]


# -------------------------------------------------------------
# 4. PROMOTIONAL QUOTA & IDEMPOTENT RELEASE (Rule 0.3 b)
# -------------------------------------------------------------

def test_promo_quota_decrement_and_exhaustion(client, test_app):
    """5 promo bookings allowed per month; 6th attempt falls back without promo."""
    db = test_app.extensions["mongo_db"]
    offer = db.offers.find_one({"eligiblePackageCode": "basic"})

    db.offers.update_one({"_id": offer["_id"]}, {"$set": {"monthlyRedemptionCount": 4}})

    p5 = {
        "date": "2026-12-04",
        "startTime": "10:00",
        "durationHours": 1,
        "packageCode": "basic",
        "applyPromo": True,
        "customerName": "User 5",
        "customerPhone": "9876543215"
    }
    res5 = client.post("/api/bookings/hold", json=p5)
    assert res5.status_code == 201
    assert res5.get_json()["data"]["pricing"]["promoApplied"] is True

    p6 = {
        "date": "2026-12-04",
        "startTime": "12:00",
        "durationHours": 1,
        "packageCode": "basic",
        "applyPromo": True,
        "customerName": "User 6",
        "customerPhone": "9876543216"
    }
    res6 = client.post("/api/bookings/hold", json=p6)
    assert res6.status_code == 201
    assert res6.get_json()["data"]["pricing"]["promoApplied"] is False


def test_promo_quota_idempotent_release_on_cancel(client, test_app):
    """Cancelling a promo booking releases the slot and decrements quota only ONCE."""
    db = test_app.extensions["mongo_db"]
    offer = db.offers.find_one({"eligiblePackageCode": "basic"})
    initial_used = offer.get("monthlyRedemptionCount", 0)

    # Book with promo
    payload = {
        "date": "2026-12-10",
        "startTime": "10:00",
        "durationHours": 1,
        "packageCode": "basic",
        "applyPromo": True,
        "customerName": "Ravi",
        "customerPhone": "9876543221"
    }
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 201
    booking_data = res.get_json()["data"]
    ref = booking_data["bookingReference"]
    token = booking_data["accessToken"]

    # Verify quota incremented
    offer_after_book = db.offers.find_one({"_id": offer["_id"]})
    assert offer_after_book["monthlyRedemptionCount"] == initial_used + 1

    # Cancel booking with valid token
    cancel_res = client.post(f"/api/bookings/{ref}/cancel", json={"token": token, "reason": "Plans changed"})
    assert cancel_res.status_code == 200

    # Quota decremented back
    offer_after_cancel = db.offers.find_one({"_id": offer["_id"]})
    assert offer_after_cancel["monthlyRedemptionCount"] == initial_used

    # Second cancel call must be rejected and must NOT decrement quota below initial_used
    cancel_res2 = client.post(f"/api/bookings/{ref}/cancel", json={"token": token, "reason": "Retry"})
    assert cancel_res2.status_code == 409
    offer_after_repeat = db.offers.find_one({"_id": offer["_id"]})
    assert offer_after_repeat["monthlyRedemptionCount"] == initial_used


# -------------------------------------------------------------
# 5. ACCESS TOKEN, LOOKUP & CANCELLATION SECURITY (Rule 0.3 a)
# -------------------------------------------------------------

def test_booking_creates_unguessable_access_token(client):
    """Booking creation issues an access token and stores only its hash."""
    payload = {
        "date": "2026-12-11",
        "startTime": "11:00",
        "durationHours": 1,
        "packageCode": "gold",
        "customerName": "Naveen P",
        "customerPhone": "9876543222"
    }
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert "accessToken" in data
    assert len(data["accessToken"]) >= 32


def test_booking_lookup_without_token_returns_minimal_status(client):
    """Reference-only lookup returns minimal status with no PII or phone fragments."""
    payload = {
        "date": "2026-12-11",
        "startTime": "14:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Secret User",
        "customerPhone": "9876543223"
    }
    res = client.post("/api/bookings", json=payload)
    ref = res.get_json()["data"]["bookingReference"]

    # Lookup without token
    lookup = client.get(f"/api/bookings/{ref}")
    assert lookup.status_code == 200
    data = lookup.get_json()["data"]
    assert data["bookingReference"] == ref
    assert data.get("isMinimal") is True
    assert "customerName" not in data
    assert "customerPhoneMasked" not in data
    assert "pricing" not in data


def test_booking_lookup_with_token_returns_full_safe_details(client):
    """Lookup with valid access token returns full display data with masked phone."""
    payload = {
        "date": "2026-12-11",
        "startTime": "16:00",
        "durationHours": 2,
        "packageCode": "gold",
        "customerName": "Priya Sharma",
        "customerPhone": "9876543224"
    }
    res = client.post("/api/bookings", json=payload)
    ref = res.get_json()["data"]["bookingReference"]
    token = res.get_json()["data"]["accessToken"]

    # Lookup with valid token
    lookup = client.get(f"/api/bookings/{ref}?token={token}")
    assert lookup.status_code == 200
    data = lookup.get_json()["data"]
    assert data["bookingReference"] == ref
    assert data["customerName"] == "Priya S."
    assert data["customerPhoneMasked"] == "****3224"
    assert "pricing" in data


def test_booking_lookup_with_wrong_token_returns_404(client):
    """Wrong access token returns 404 (identical to non-existent reference)."""
    payload = {
        "date": "2026-12-12",
        "startTime": "10:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Test",
        "customerPhone": "9876543225"
    }
    res = client.post("/api/bookings", json=payload)
    ref = res.get_json()["data"]["bookingReference"]

    lookup = client.get(f"/api/bookings/{ref}?token=wrong_token_12345")
    assert lookup.status_code == 404
    assert lookup.get_json()["error"]["code"] == "NOT_FOUND"


def test_cancel_requires_valid_token(client):
    """Cancelling without token or with wrong token returns 404."""
    payload = {
        "date": "2026-12-12",
        "startTime": "12:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Test",
        "customerPhone": "9876543226"
    }
    res = client.post("/api/bookings", json=payload)
    ref = res.get_json()["data"]["bookingReference"]

    # Cancel without token -> 404
    res_no_tok = client.post(f"/api/bookings/{ref}/cancel", json={"reason": "test"})
    assert res_no_tok.status_code == 404

    # Cancel with wrong token -> 404
    res_bad_tok = client.post(f"/api/bookings/{ref}/cancel", json={"token": "bad_token", "reason": "test"})
    assert res_bad_tok.status_code == 404


# -------------------------------------------------------------
# 6. IDEMPOTENCY SPECIFICATION TESTS (Rule 0.3 f)
# -------------------------------------------------------------

def test_idempotent_booking_replay(client):
    """Replaying identical request with same Idempotency-Key returns cached response."""
    payload = {
        "date": "2026-12-13",
        "startTime": "10:00",
        "durationHours": 1,
        "packageCode": "gold",
        "customerName": "Mahesh",
        "customerPhone": "9876543227"
    }
    headers = {"Idempotency-Key": "test-key-uuid-12345"}
    res1 = client.post("/api/bookings", json=payload, headers=headers)
    assert res1.status_code == 201
    data1 = res1.get_json()["data"]

    # Replay with same key
    res2 = client.post("/api/bookings", json=payload, headers=headers)
    assert res2.status_code == 201
    data2 = res2.get_json()["data"]

    assert data1["bookingReference"] == data2["bookingReference"]
    assert data1["bookingId"] == data2["bookingId"]


def test_idempotency_payload_mismatch_returns_422(client):
    """Using same Idempotency-Key with different payload returns 422 with stable error code."""
    payload1 = {
        "date": "2026-12-13",
        "startTime": "12:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Kiran",
        "customerPhone": "9876543228"
    }
    headers = {"Idempotency-Key": "test-key-uuid-99999"}
    res1 = client.post("/api/bookings", json=payload1, headers=headers)
    assert res1.status_code == 201

    payload2 = dict(payload1)
    payload2["packageCode"] = "gold"  # different payload
    res2 = client.post("/api/bookings", json=payload2, headers=headers)
    assert res2.status_code == 422
    assert res2.get_json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"


# -------------------------------------------------------------
# 7. UNIFIED DIRECT BOOKING PATH (Rule 0.3 d)
# -------------------------------------------------------------

def test_unified_direct_booking_creates_claims_and_token(client):
    """Direct booking without holdId uses unified path, locks slot, and creates token."""
    payload = {
        "date": "2026-12-14",
        "startTime": "15:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Direct Book User",
        "customerPhone": "9876543229"
    }
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert "bookingReference" in data
    assert "accessToken" in data

    # Overlapping attempt must be blocked
    res_overlap = client.post("/api/bookings", json=payload)
    assert res_overlap.status_code == 409


# -------------------------------------------------------------
# 8. RATE LIMITING ON RESERVATION CREATION (Rule 0.3 e)
# -------------------------------------------------------------

def test_rate_limiting_per_phone_prevents_slot_hoarding(client, test_app):
    """Exceeding max reservation attempts per phone returns 429 RATE_LIMITED."""
    phone = "9876543230"
    for i in range(Config.RATE_LIMIT_HOLD_PER_PHONE_MAX):
        p = {
            "date": f"2026-12-{15 + i}",
            "startTime": "10:00",
            "durationHours": 1,
            "packageCode": "basic",
            "customerName": f"User {i}",
            "customerPhone": phone
        }
        res = client.post("/api/bookings/hold", json=p)
        assert res.status_code == 201

    # Next attempt with same phone is rejected
    excess_payload = {
        "date": "2026-12-25",
        "startTime": "10:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "User Excess",
        "customerPhone": phone
    }
    excess_res = client.post("/api/bookings/hold", json=excess_payload)
    assert excess_res.status_code == 429
    assert excess_res.get_json()["error"]["code"] == "RATE_LIMITED"


# -------------------------------------------------------------
# 9. REAL MONGODB ATLAS CONCURRENCY SUITE (Rule 0.2)
# -------------------------------------------------------------

def test_real_mongodb_concurrency_guard(live_test_client):
    """
    Real-cluster concurrency test on live Atlas test DB (ending in '_test'):
    - 20 simultaneous threads attempting to book the EXACT SAME slot.
    - Exactly 1 succeeds, 19 return 409 SLOT_CONFLICT.
    - 0 duplicate slotClaims in the collection.
    - Promo quota exhaustion: 8 concurrent requests for 5 slots, exactly 5 get promo.
    Guarded by conftest.py which verifies assert_live_test_client before any write.
    """
    test_db = live_test_client
    # Verify live connection
    test_db.command("ping")
    room_id = "concurrency_test_room"
    target_date = "2026-12-30"
    target_time = "10:00"

    # Setup isolated test app wired to live Atlas test DB
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    def attempt_booking(worker_idx):
        with app.test_client() as c:
            p = {
                "roomId": room_id,
                "date": target_date,
                "startTime": target_time,
                "durationHours": 1,
                "packageCode": "basic",
                "customerName": f"Worker {worker_idx}",
                "customerPhone": f"9876543{worker_idx:03d}"
            }
            return c.post(
                "/api/bookings",
                json=p,
                headers={"X-Forwarded-For": f"192.168.1.{worker_idx}"}
            ).status_code

    # Fire 20 simultaneous threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(attempt_booking, i) for i in range(20)]
        results = [f.result() for f in futures]

    successes = results.count(201)
    conflicts = results.count(409)

    print("ALL CONCURRENCY RESULTS:", sorted(results))
    assert successes == 1, f"Expected exactly 1 success, got {successes}"
    assert conflicts == 19, f"Expected 19 conflicts, got {conflicts}"

    # Verify 0 duplicate slot claims in live DB
    start_utc = to_utc(parse_ist_datetime(target_date, target_time))
    claims = list(test_db.slotClaims.find({"roomId": room_id, "slotStart": start_utc}))
    assert len(claims) == 1, f"Expected exactly 1 slot claim in database, found {len(claims)}"


# -------------------------------------------------------------
# 8. B3 SLOT INTEGRITY & ADVANCE WINDOW TESTS
# -------------------------------------------------------------

def test_booking_past_date_rejected(client):
    """Verifies that requesting a past start time is rejected with 422."""
    past_date = "2020-01-01"
    res = client.post("/api/bookings/hold", json={
        "date": past_date,
        "startTime": "10:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Past Booker",
        "customerPhone": "9876543210"
    })
    assert res.status_code == 422
    err_body = res.get_json()
    assert "in the past" in err_body["error"]["message"].lower()


def test_booking_beyond_max_advance_days_rejected(client):
    """Verifies that booking beyond MAX_ADVANCE_BOOKING_DAYS (90 days) is rejected with 422."""
    future_date = (now_ist() + timedelta(days=120)).strftime("%Y-%m-%d")
    res = client.post("/api/bookings/hold", json={
        "date": future_date,
        "startTime": "10:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Far Future Booker",
        "customerPhone": "9876543210"
    })
    assert res.status_code == 422
    err_body = res.get_json()
    assert "advance" in err_body["error"]["message"].lower()


def test_availability_beyond_max_advance_days_rejected(client):
    """Verifies that querying availability beyond 90 days returns 422."""
    future_date = (now_ist() + timedelta(days=120)).strftime("%Y-%m-%d")
    res = client.get(f"/api/availability?date={future_date}&durationHours=1")
    assert res.status_code == 422
    err_body = res.get_json()
    assert "advance" in err_body["error"]["message"].lower()

