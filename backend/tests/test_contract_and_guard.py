import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    return app.test_client()

def test_canonical_quote_payload_validation(client):
    """Assert 422 with structured field-level errors for invalid quote payload."""
    res = client.post("/api/bookings/quote", json={})
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "packageCode" in data["error"]["details"]
    assert "durationHours" in data["error"]["details"]

def test_canonical_booking_hold_validation(client):
    """Assert 422 with structured field-level errors for invalid booking hold payload."""
    res = client.post("/api/bookings", json={
        "packageCode": "gold",
        "durationHours": 7, # invalid duration (>6)
        "date": "invalid-date",
        "startTime": "bad-time",
        "customerName": "A", # too short
        "customerPhone": "123" # too short
    })
    assert res.status_code == 422
    data = res.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    details = data["error"]["details"]
    assert "durationHours" in details
    assert "date" in details
    assert "startTime" in details
    assert "customerName" in details
    assert "customerPhone" in details

def test_database_abort_guard_on_non_test_db(monkeypatch):
    """Proves that test session strictly aborts if database name does not end in '_test'."""
    from app.utils.db_safety import assert_is_test_database, UnsafeDatabaseError

    with pytest.raises(UnsafeDatabaseError) as exc_info:
        assert_is_test_database("joybox_party_room")
    assert "does not end with '_test'" in str(exc_info.value)

    with pytest.raises(UnsafeDatabaseError) as exc_info2:
        assert_is_test_database("production_db")
    assert "does not end with '_test'" in str(exc_info2.value)

