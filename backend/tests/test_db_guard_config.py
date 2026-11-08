import os
import pytest
from app.utils.db_safety import (
    assert_is_test_database,
    validate_script_db_target,
    UnsafeDatabaseError,
)

def test_db_guard_defaults():
    """Verify default guards allow _test and reject production."""
    # Allowed
    assert_is_test_database("joybox_party_room_test")
    assert_is_test_database("joybox_scratch_test")
    assert_is_test_database("my_custom_db_test")

    # Rejected
    with pytest.raises(UnsafeDatabaseError):
        assert_is_test_database("joybox_party_room")

    with pytest.raises(UnsafeDatabaseError):
        assert_is_test_database("joybox_party_room_dev")

    with pytest.raises(UnsafeDatabaseError):
        assert_is_test_database("joybox_test_other")

def test_db_guard_custom_suffix(monkeypatch):
    """Verify TEST_DB_SUFFIX environment override changes allowed suffix."""
    monkeypatch.setenv("TEST_DB_SUFFIX", "_integration_test")

    # Matches custom suffix
    assert_is_test_database("joybox_party_room_integration_test")
    assert validate_script_db_target("joybox_integration_test") == "joybox_integration_test"

    # Default suffix now rejected
    with pytest.raises(UnsafeDatabaseError):
        assert_is_test_database("joybox_party_room_test")

def test_db_guard_custom_prod_name(monkeypatch):
    """Verify PROD_DB_NAME environment override protects custom production name."""
    monkeypatch.setenv("PROD_DB_NAME", "custom_prod_database")

    # Custom prod rejected
    with pytest.raises(UnsafeDatabaseError):
        assert_is_test_database("custom_prod_database")

    # Script target requires explicit confirmation for custom prod
    with pytest.raises(UnsafeDatabaseError):
        validate_script_db_target("custom_prod_database")

    # Valid confirmation allows script execution
    assert validate_script_db_target("custom_prod_database", allow_production=True, confirm_token="custom_prod_database") == "custom_prod_database"
