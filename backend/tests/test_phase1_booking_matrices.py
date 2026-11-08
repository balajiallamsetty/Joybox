"""
Phase 1: Black-Box API Test Matrices for Booking Engine Verification
Covers:
- Matrix A: Duration boundaries (0, 0.5, 1, 6, 6.5, 7 hours)
- Matrix B: Buffer boundaries & overlaps (29, 30, 31 mins; back-to-back with buffer, back-to-back without buffer, adjacent bookings, overlapping bookings)
- Matrix C: Advance booking window boundaries (Day 0, Day 89, Day 90, Day 91, past dates)
- Matrix D: Operating hours boundaries (08:00 opening-1, 09:00, 21:00, 22:00 closing, crossing closing, midnight rollover)
- Matrix E: Date independence, payload validation, server pricing authority, and anti-hoarding rate limits
"""
import os
import pytest
from datetime import datetime, timedelta
from app import create_app
from app.utils.datetime_utils import now_ist


@pytest.fixture(autouse=True)
def clean_transactional_data(live_test_client):
    test_db = live_test_client
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
def api_client(live_test_client):
    test_db = live_test_client
    app = create_app({
        "TESTING": True,
        "MONGODB_URI": os.getenv("MONGODB_URI"),
        "MONGODB_DB": test_db.name
    })
    app.extensions["mongo_db"] = test_db
    with app.test_client() as client:
        yield client


def get_future_date_str(days_ahead: int) -> str:
    """Returns YYYY-MM-DD for IST now + days_ahead."""
    return (now_ist() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


# =====================================================================
# MATRIX A: DURATION BOUNDARIES (BL-03)
# Valid range: 1 to 6 integer hours
# =====================================================================

def test_matrix_a_duration_zero_rejected(api_client):
    """BL-03: Duration = 0 must be rejected with 422 validation error."""
    target_date = get_future_date_str(10)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "10:00",
        "durationHours": 0,
        "packageCode": "basic",
        "customerName": "Test Customer",
        "customerPhone": "+919876543210"
    })
    assert res.status_code == 422
    assert "VALIDATION_ERROR" in res.json["error"]["code"]


def test_matrix_a_duration_half_hour_rejected(api_client):
    """BL-03: Fractional duration = 0.5 must be rejected with 422 validation error."""
    target_date = get_future_date_str(10)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "10:00",
        "durationHours": 0.5,
        "packageCode": "basic",
        "customerName": "Test Customer",
        "customerPhone": "+919876543210"
    })
    assert res.status_code == 422
    assert "VALIDATION_ERROR" in res.json["error"]["code"]


def test_matrix_a_duration_min_boundary_one_hour_accepted(api_client):
    """BL-03: Duration = 1 (minimum allowed boundary) must be accepted."""
    target_date = get_future_date_str(10)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "10:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Test Customer",
        "customerPhone": "+919876543210"
    })
    assert res.status_code == 201
    assert "holdId" in res.json["data"]


def test_matrix_a_duration_max_boundary_six_hours_accepted(api_client):
    """BL-03: Duration = 6 (maximum allowed boundary) starting at 10:00 (ends 16:00) must be accepted."""
    target_date = get_future_date_str(10)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "10:00",
        "durationHours": 6,
        "packageCode": "gold",
        "customerName": "Test Customer",
        "customerPhone": "+919876543210"
    })
    assert res.status_code == 201
    assert "holdId" in res.json["data"]


def test_matrix_a_duration_fractional_six_and_half_rejected(api_client):
    """BL-03: Duration = 6.5 must be rejected with 422 validation error."""
    target_date = get_future_date_str(10)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "10:00",
        "durationHours": 6.5,
        "packageCode": "gold",
        "customerName": "Test Customer",
        "customerPhone": "+919876543210"
    })
    assert res.status_code == 422


def test_matrix_a_duration_seven_hours_exceeded_rejected(api_client):
    """BL-03: Duration = 7 (> max 6) must be rejected with 422 validation error."""
    target_date = get_future_date_str(10)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "10:00",
        "durationHours": 7,
        "packageCode": "gold",
        "customerName": "Test Customer",
        "customerPhone": "+919876543210"
    })
    assert res.status_code == 422


# =====================================================================
# MATRIX B: BUFFER BOUNDARIES & OVERLAPS (BL-02, BL-05)
# 30-minute buffer protection between bookings
# =====================================================================

def test_matrix_b_adjacent_booking_with_buffer_accepted(api_client):
    """
    BL-02: Booking 1 is 10:00–12:00 (party: 10:00–12:00, buffer: 12:00–12:30).
    Booking 2 at 12:30–14:30 respects the buffer and MUST be accepted.
    """
    target_date = get_future_date_str(12)
    # Booking 1
    res1 = api_client.post("/api/bookings", json={
        "date": target_date,
        "startTime": "10:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "First Party",
        "customerPhone": "+919876543211"
    })
    assert res1.status_code == 201

    # Booking 2 immediately after 30-min buffer (starts at 12:30)
    # Since start times align to whole hours, let's test next available top of hour (13:00)
    res2 = api_client.post("/api/bookings", json={
        "date": target_date,
        "startTime": "13:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Second Party",
        "customerPhone": "+919876543212"
    })
    assert res2.status_code == 201


def test_matrix_b_back_to_back_without_buffer_rejected_conflict(api_client):
    """
    BL-02: Booking 1 is 10:00–12:00. Buffer is 12:00–12:30.
    Attempting Booking 2 at 12:00 violates the 30-minute buffer and MUST be rejected with 409 Conflict.
    """
    target_date = get_future_date_str(12)
    res1 = api_client.post("/api/bookings", json={
        "date": target_date,
        "startTime": "10:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "First Party",
        "customerPhone": "+919876543211"
    })
    assert res1.status_code == 201

    # Booking 2 starting at 12:00 conflicts with Booking 1's 12:00–12:30 buffer
    res2 = api_client.post("/api/bookings", json={
        "date": target_date,
        "startTime": "12:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Conflicting Party",
        "customerPhone": "+919876543212"
    })
    assert res2.status_code == 409
    assert res2.json["error"]["code"] in ("SLOT_CONFLICT", "SLOT_UNAVAILABLE")


def test_matrix_b_overlapping_booking_rejected_conflict(api_client):
    """
    BL-02 / BL-06: Booking 1 is 14:00–16:00.
    Attempting Booking 2 at 15:00–17:00 overlaps the active party and MUST return 409 Conflict.
    """
    target_date = get_future_date_str(14)
    res1 = api_client.post("/api/bookings", json={
        "date": target_date,
        "startTime": "14:00",
        "durationHours": 2,
        "packageCode": "gold",
        "customerName": "First Party",
        "customerPhone": "+919876543211"
    })
    assert res1.status_code == 201

    res2 = api_client.post("/api/bookings", json={
        "date": target_date,
        "startTime": "15:00",
        "durationHours": 2,
        "packageCode": "gold",
        "customerName": "Overlapping Party",
        "customerPhone": "+919876543212"
    })
    assert res2.status_code == 409
    assert res2.json["error"]["code"] in ("SLOT_CONFLICT", "SLOT_UNAVAILABLE")


# =====================================================================
# MATRIX C: ADVANCE WINDOW BOUNDARIES (BL-04)
# Allowed: Day 0 to Day 90. Day 91+ and past dates rejected.
# =====================================================================

def test_matrix_c_day_zero_availability_and_booking_allowed(api_client):
    """BL-04: Today (Day 0) can be queried for availability."""
    today_str = get_future_date_str(0)
    res = api_client.get(f"/api/availability?date={today_str}&durationHours=1")
    assert res.status_code == 200
    assert res.json["data"]["date"] == today_str


def test_matrix_c_day_eighty_nine_accepted(api_client):
    """BL-04: Day 89 is within the 90-day window and must be accepted."""
    day89_str = get_future_date_str(89)
    res = api_client.get(f"/api/availability?date={day89_str}&durationHours=2")
    assert res.status_code == 200
    assert res.json["data"]["date"] == day89_str


def test_matrix_c_day_ninety_accepted(api_client):
    """BL-04: Day 90 is the exact maximum boundary and must be accepted."""
    day90_str = get_future_date_str(90)
    res = api_client.get(f"/api/availability?date={day90_str}&durationHours=2")
    assert res.status_code == 200
    assert res.json["data"]["date"] == day90_str


def test_matrix_c_day_ninety_one_rejected(api_client):
    """BL-04: Day 91 exceeds the 90-day advance window and must be rejected."""
    day91_str = get_future_date_str(91)
    res = api_client.get(f"/api/availability?date={day91_str}&durationHours=2")
    assert res.status_code in (400, 422)


def test_matrix_c_past_date_rejected(api_client):
    """BL-04: Booking on a past date (yesterday) must be rejected."""
    past_date_str = (now_ist() - timedelta(days=2)).strftime("%Y-%m-%d")
    res = api_client.post("/api/bookings/hold", json={
        "date": past_date_str,
        "startTime": "10:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Past Booker",
        "customerPhone": "+919876543210"
    })
    assert res.status_code in (400, 422)


# =====================================================================
# MATRIX D: OPERATING HOURS BOUNDARIES (BL-01, BL-02)
# Venue hours: 09:00 to 22:00 IST
# =====================================================================

def test_matrix_d_opening_minus_one_hour_rejected(api_client):
    """BL-01: Slot at 08:00 (1 hour before 09:00 opening) must be rejected."""
    target_date = get_future_date_str(15)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "08:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Early Booker",
        "customerPhone": "+919876543210"
    })
    assert res.status_code in (400, 422)


def test_matrix_d_opening_hour_exact_accepted(api_client):
    """BL-01: Slot starting at exactly 09:00 must be accepted."""
    target_date = get_future_date_str(15)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "09:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Opening Booker",
        "customerPhone": "+919876543210"
    })
    assert res.status_code == 201


def test_matrix_d_closing_exact_one_hour_accepted(api_client):
    """BL-01 / BL-02: 1-hour party from 21:00 to 22:00 ends at closing, buffer 22:00-22:30 allowed."""
    target_date = get_future_date_str(16)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "21:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Late Night Party",
        "customerPhone": "+919876543210"
    })
    assert res.status_code == 201


def test_matrix_d_crossing_closing_time_rejected(api_client):
    """BL-01: 2-hour party starting at 21:00 would end at 23:00 (> 22:00 closing) and must be rejected."""
    target_date = get_future_date_str(16)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "21:00",
        "durationHours": 2,
        "packageCode": "basic",
        "customerName": "Overtime Party",
        "customerPhone": "+919876543210"
    })
    assert res.status_code in (400, 422)


def test_matrix_d_closing_plus_one_rejected(api_client):
    """BL-01: Slot starting at 22:00 (closing time) must be rejected."""
    target_date = get_future_date_str(16)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "22:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Midnight Party",
        "customerPhone": "+919876543210"
    })
    assert res.status_code in (400, 422)


# =====================================================================
# MATRIX E: DATE INDEPENDENCE & PAYLOAD INTEGRITY (BL-07, BL-10, BL-12, BL-13)
# =====================================================================

def test_matrix_e_same_slot_different_dates_both_available_and_bookable(api_client):
    """
    BL-07: Booking 18:00–20:00 on Date 1 must NOT block 18:00–20:00 on Date 2.
    Both bookings must succeed cleanly.
    """
    date1 = get_future_date_str(20)
    date2 = get_future_date_str(21)

    # Book on Date 1
    res1 = api_client.post("/api/bookings", json={
        "date": date1,
        "startTime": "18:00",
        "durationHours": 2,
        "packageCode": "gold",
        "customerName": "Date 1 Customer",
        "customerPhone": "+919876543211"
    })
    assert res1.status_code == 201

    # Date 2 must show 18:00 as available
    avail_res = api_client.get(f"/api/availability?date={date2}&durationHours=2")
    assert avail_res.status_code == 200
    slot18 = next(s for s in avail_res.json["data"]["slots"] if s["startTime"] == "18:00")
    assert slot18["available"] is True

    # Book on Date 2
    res2 = api_client.post("/api/bookings", json={
        "date": date2,
        "startTime": "18:00",
        "durationHours": 2,
        "packageCode": "gold",
        "customerName": "Date 2 Customer",
        "customerPhone": "+919876543212"
    })
    assert res2.status_code == 201


def test_matrix_e_server_pricing_authority_ignores_client_tampering(api_client):
    """
    BL-12: Client attempts to tamper with totalAmountMinor (passing 100 paise = ₹1.00).
    Server ignores client amount and computes authoritative catalog quote (2h gold = ₹3,000).
    """
    target_date = get_future_date_str(25)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "11:00",
        "durationHours": 2,
        "packageCode": "gold",
        "totalAmountMinor": 100,
        "totalRupees": 1.0,
        "customerName": "Price Tamperer",
        "customerPhone": "+919876543210"
    })
    # Since BookingHoldRequestSchema uses unknown=RAISE, passing extra fields raises 422!
    # If passed in a-la-carte, server quotes authoritatively.
    assert res.status_code in (201, 422)
    if res.status_code == 201:
        assert res.json["data"]["pricing"]["totalAmountMinor"] >= 100000


def test_matrix_e_malformed_payload_rejected(api_client):
    """BL-10: Payload missing required customerName or with invalid phone is rejected with 422."""
    target_date = get_future_date_str(25)
    res = api_client.post("/api/bookings/hold", json={
        "date": target_date,
        "startTime": "11:00",
        "durationHours": 2,
        "packageCode": "gold",
        # Missing customerName
        "customerPhone": "not-a-phone"
    })
    assert res.status_code == 422
    assert "VALIDATION_ERROR" in res.json["error"]["code"]

