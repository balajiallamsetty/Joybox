import pytest
from bson import ObjectId
from backend.tests.test_booking_engine import test_app, client

def test_same_slot_different_dates_both_bookable(client):
    """
    P1 Step 1 Requirement:
    Book date A 18:00-19:00 -> success.
    Book date B (A+1 day) 18:00-19:00 -> must succeed.
    """
    payload_a = {
        "date": "2026-12-10",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer Date A",
        "customerPhone": "9876543210"
    }
    res_a = client.post("/api/bookings", json=payload_a)
    assert res_a.status_code == 201, f"Date A booking failed: {res_a.get_json()}"
    data_a = res_a.get_json()["data"]
    assert "bookingReference" in data_a

    # Next date: 2026-12-11 at 18:00
    payload_b = {
        "date": "2026-12-11",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer Date B",
        "customerPhone": "9876543211"
    }
    res_b = client.post("/api/bookings", json=payload_b)
    assert res_b.status_code == 201, f"Date B booking failed: {res_b.get_json()}"
    data_b = res_b.get_json()["data"]
    assert "bookingReference" in data_b


def test_availability_is_per_date(client):
    """
    P1 Step 1 Requirement:
    After booking date A (18:00), the availability endpoint for date B shows
    18:00 free, and for date A shows it taken.
    """
    payload_a = {
        "date": "2026-12-12",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer Date A",
        "customerPhone": "9876543210"
    }
    res_a = client.post("/api/bookings", json=payload_a)
    assert res_a.status_code == 201

    # Check Date A availability
    res_avail_a = client.get("/api/availability?date=2026-12-12&durationHours=1")
    assert res_avail_a.status_code == 200
    slots_a = {s["startTime"]: s for s in res_avail_a.get_json()["data"]["slots"]}
    assert slots_a["18:00"]["available"] is False
    assert slots_a["18:00"]["unavailableReason"] == "booked"

    # Check Date B availability (same time must be free)
    res_avail_b = client.get("/api/availability?date=2026-12-13&durationHours=1")
    assert res_avail_b.status_code == 200
    slots_b = {s["startTime"]: s for s in res_avail_b.get_json()["data"]["slots"]}
    assert slots_b["18:00"]["available"] is True, f"Slot 18:00 on date B was blocked: {slots_b['18:00']}"


def test_same_slot_same_date_conflicts(client):
    """
    P1 Step 1 Requirement:
    Same date, same slot -> conflict.
    """
    payload_1 = {
        "date": "2026-12-14",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer 1",
        "customerPhone": "9876543210"
    }
    res_1 = client.post("/api/bookings", json=payload_1)
    assert res_1.status_code == 201

    payload_2 = {
        "date": "2026-12-14",
        "startTime": "18:00",
        "durationHours": 1,
        "packageCode": "basic",
        "customerName": "Customer 2",
        "customerPhone": "9876543211"
    }
    res_2 = client.post("/api/bookings", json=payload_2)
    assert res_2.status_code == 409, f"Expected 409 conflict, got {res_2.status_code}: {res_2.get_json()}"
    json_2 = res_2.get_json()
    assert json_2["error"]["code"] in ["SLOT_CONFLICT", "SLOT_UNAVAILABLE"]


def test_atlas_same_slot_different_dates_both_bookable(live_test_client):
    """Real MongoDB Atlas cluster test: same slot across two dates both succeed."""
    test_db = live_test_client
    from app import create_app
    import os
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db
    with app.test_client() as c:
        payload_a = {
            "date": "2026-12-20",
            "startTime": "18:00",
            "durationHours": 1,
            "packageCode": "basic",
            "customerName": "Customer A",
            "customerPhone": "9876543210"
        }
        res_a = c.post("/api/bookings", json=payload_a)
        assert res_a.status_code == 201

        payload_b = {
            "date": "2026-12-21",
            "startTime": "18:00",
            "durationHours": 1,
            "packageCode": "basic",
            "customerName": "Customer B",
            "customerPhone": "9876543211"
        }
        res_b = c.post("/api/bookings", json=payload_b)
        assert res_b.status_code == 201


def test_atlas_availability_is_per_date(live_test_client):
    """Real MongoDB Atlas cluster test: availability for date B is free after booking date A."""
    test_db = live_test_client
    from app import create_app
    import os
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db
    with app.test_client() as c:
        payload_a = {
            "date": "2026-12-22",
            "startTime": "18:00",
            "durationHours": 1,
            "packageCode": "basic",
            "customerName": "Customer A",
            "customerPhone": "9876543210"
        }
        res_a = c.post("/api/bookings", json=payload_a)
        assert res_a.status_code == 201

        res_avail_a = c.get("/api/availability?date=2026-12-22&durationHours=1")
        assert res_avail_a.status_code == 200
        slots_a = {s["startTime"]: s for s in res_avail_a.get_json()["data"]["slots"]}
        assert slots_a["18:00"]["available"] is False

        res_avail_b = c.get("/api/availability?date=2026-12-23&durationHours=1")
        assert res_avail_b.status_code == 200
        slots_b = {s["startTime"]: s for s in res_avail_b.get_json()["data"]["slots"]}
        assert slots_b["18:00"]["available"] is True

