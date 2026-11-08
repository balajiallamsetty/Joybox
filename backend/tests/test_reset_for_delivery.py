import os

import pytest
from pymongo import MongoClient

from app.utils.db_safety import UnsafeDatabaseError, assert_is_test_database
from scripts.reset_for_delivery import (
    DeliveryResetRefused,
    assert_delivery_reset_allowed,
    empty_all_collections,
)


def test_delivery_reset_guards_refuse_non_production_and_hosted_environments():
    local = {"ALLOW_DESTRUCTIVE_SCRIPTS": "true", "MONGODB_DB": "joybox_party_room"}
    with pytest.raises(DeliveryResetRefused):
        assert_delivery_reset_allowed(
            "joybox_party_room_delivery_logic_test",
            "joybox_party_room_delivery_logic_test",
            True,
            local,
        )
    with pytest.raises(DeliveryResetRefused):
        assert_delivery_reset_allowed("joybox_party_room", "joybox_party_room", True, {**local, "CI": "true"})
    with pytest.raises(DeliveryResetRefused):
        assert_delivery_reset_allowed("joybox_party_room", "joybox_party_room", True, {**local, "RENDER": "true"})
    with pytest.raises(DeliveryResetRefused):
        assert_delivery_reset_allowed("joybox_party_room", "other_name", True, local)
    with pytest.raises(DeliveryResetRefused):
        assert_delivery_reset_allowed("joybox_party_room", "joybox_party_room", False, local)
    with pytest.raises(DeliveryResetRefused):
        assert_delivery_reset_allowed("joybox_party_room", "joybox_party_room", True, dict(os.environ))

    assert assert_delivery_reset_allowed("joybox_party_room", "joybox_party_room", True, local) == "joybox_party_room"
    with pytest.raises(UnsafeDatabaseError):
        assert_is_test_database("joybox_party_room")


def test_empty_all_collections_only_against_throwaway_database():
    name = "joybox_party_room_delivery_logic_test"
    assert_is_test_database(name)
    uri = os.getenv("MONGODB_TEST_URI") or os.getenv("MONGODB_URI", "")
    if not uri or "<" in uri:
        pytest.skip("MongoDB URI is not configured")

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except Exception as exc:
        pytest.skip(f"NOT RUN: MongoDB Atlas cluster unreachable: {exc}")
    db = client[name]
    try:
        db.probe.insert_one({"marker": "delivery-logic"})
        result = empty_all_collections(db)
        assert result["before"]["probe"] == 1
        assert result["after"]["probe"] == 0
        assert db.probe.count_documents({}) == 0
    finally:
        client.drop_database(name)
        client.close()
