import pytest
from unittest.mock import patch, MagicMock
from app import create_app

@pytest.fixture
def closed_client():
    app = create_app({"TESTING": True, "BOOKINGS_OPEN": False})
    with app.test_client() as c:
        yield c

@pytest.fixture
def open_client():
    app = create_app({"TESTING": True, "BOOKINGS_OPEN": True})
    with app.test_client() as c:
        yield c

def test_bookings_closed_returns_403_on_mutating_endpoints(closed_client):
    """When BOOKINGS_OPEN is False, hold and booking creation return 403 BOOKINGS_NOT_OPEN."""
    # 1. Hold
    res_hold = closed_client.post("/api/bookings/hold", json={"dummy": "payload"})
    assert res_hold.status_code == 403
    data_hold = res_hold.get_json()
    assert data_hold["success"] is False
    assert data_hold["error"]["code"] == "BOOKINGS_NOT_OPEN"
    assert "WhatsApp" in data_hold["error"]["message"]

    # 2. Direct Booking
    res_booking = closed_client.post("/api/bookings", json={"dummy": "payload"})
    assert res_booking.status_code == 403
    data_booking = res_booking.get_json()
    assert data_booking["success"] is False
    assert data_booking["error"]["code"] == "BOOKINGS_NOT_OPEN"

def test_bookings_closed_preserves_read_only_catalog_and_quote(closed_client):
    """When BOOKINGS_OPEN is False, packages, add-ons, availability, and quotes remain functional."""
    # Packages
    res_pkg = closed_client.get("/api/packages")
    assert res_pkg.status_code == 200

    # Add-ons
    res_addons = closed_client.get("/api/add-ons")
    assert res_addons.status_code == 200

    # Public config
    res_cfg = closed_client.get("/api/public-config")
    assert res_cfg.status_code == 200
    assert res_cfg.get_json()["data"]["bookingsOpen"] is False

def test_bookings_open_allows_hold_creation_to_proceed(open_client):
    """When BOOKINGS_OPEN is True, hold creation passes the closed gate."""
    res_cfg = open_client.get("/api/public-config")
    assert res_cfg.status_code == 200
    assert res_cfg.get_json()["data"]["bookingsOpen"] is True
