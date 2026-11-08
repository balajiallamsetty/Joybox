import pytest
from app.utils.db_safety import (
    assert_is_test_database,
    assert_live_test_client,
    UnsafeDatabaseError
)

class MockLiveClient:
    def __init__(self, db_name="joybox_party_room_test", ping_ok=True):
        self.active_db_name = db_name
        self.ping_ok = ping_ok
        self.admin = self

    def command(self, cmd):
        if not self.ping_ok:
            raise ConnectionError("Network unreachable")
        if cmd == "ping":
            return {"ok": 1}
        return {}

    def get_default_database(self):
        class MockDB:
            name = self.active_db_name
            def command(self, cmd):
                return {"ok": 1}
        return MockDB()

    def __getitem__(self, name):
        class MockDB:
            def __init__(self, dbname):
                self.name = dbname
            def command(self, cmd):
                return {"ok": 1}
        return MockDB(name)

def test_database_safety_guard_rejects_non_test_and_mid_test():
    unsafe_names = [
        "joybox_party_room",
        "joybox_prod",
        "production_db",
        "test_joybox",           # Starts with test, but does NOT end with _test
        "joybox_test_db",        # Contains test, but does NOT end with _test
        "joybox_testing",        # Ends in ing, not _test
        "joybox_test_",          # Trailing underscore, not _test
        "",
        None
    ]
    for db_name in unsafe_names:
        with pytest.raises(UnsafeDatabaseError) as exc_info:
            assert_is_test_database(db_name)
        assert "does not end with '_test'" in str(exc_info.value) or "Invalid database name" in str(exc_info.value)

def test_database_safety_guard_allows_ending_in_underscore_test():
    safe_names = [
        "joybox_party_room_test",
        "joybox_concurrency_test",
        "ci_integration_test",
        "JOYBOX_APP_TEST"
    ]
    for db_name in safe_names:
        # Should execute cleanly without raising
        assert_is_test_database(db_name)

def test_live_client_check_succeeds_on_valid_test_db():
    client = MockLiveClient(db_name="joybox_party_room_test")
    resolved = assert_live_test_client(client)
    assert resolved == "joybox_party_room_test"

def test_live_client_check_rejects_production_db():
    client = MockLiveClient(db_name="joybox_party_room")
    with pytest.raises(UnsafeDatabaseError) as exc_info:
        assert_live_test_client(client)
    assert "does not end with '_test'" in str(exc_info.value)

def test_live_client_check_rejects_disconnected_client():
    client = MockLiveClient(db_name="joybox_party_room_test", ping_ok=False)
    with pytest.raises(UnsafeDatabaseError) as exc_info:
        assert_live_test_client(client)
    assert "Live MongoDB ping check failed" in str(exc_info.value)
