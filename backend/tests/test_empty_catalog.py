import os

from pymongo import MongoClient

from app import create_app
from app.utils.db_safety import assert_is_test_database


def test_empty_throwaway_database_has_no_packages_and_does_not_error():
    name = "joybox_party_room_empty_catalog_test"
    assert_is_test_database(name)
    uri = os.getenv("MONGODB_URI", "")
    if not uri or "<" in uri:
        import pytest
        pytest.skip("MONGODB_URI is not configured")

    import pytest
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except Exception as exc:
        pytest.skip(f"NOT RUN: MongoDB Atlas cluster unreachable: {exc}")
    client.drop_database(name)
    try:
        app = create_app({"TESTING": True, "MONGODB_DB": name})
        http = app.test_client()
        packages = http.get("/api/packages")
        assert packages.status_code == 200
        assert packages.json["data"]["items"] == []
        addons = http.get("/api/add-ons")
        assert addons.status_code == 200
        assert addons.json["data"]["items"] == []
        offers = http.get("/api/offers/active")
        assert offers.status_code == 200
        availability = http.get("/api/availability?date=2026-12-01&durationHours=1&roomId=main")
        assert availability.status_code == 200
        assert "slots" in availability.json["data"]
    finally:
        client.drop_database(name)
        client.close()
