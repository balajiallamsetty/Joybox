"""
Pytest configuration and session fixtures for Joybox Party Room.
Guarantees isolated, seeded integration testing against a verified _test database.
"""
import os
import sys
from datetime import datetime, timezone
import pytest
from dotenv import load_dotenv
from pymongo import MongoClient

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.db_safety import assert_is_test_database, assert_live_test_client
from scripts.init_indexes import init_indexes
from scripts.seed_packages import seed_packages
from scripts.seed_addons import seed_addons
from scripts.seed_offers import seed_offers
from scripts.create_admin import create_admin_user

# Automatically load backend/.env if running pytest from workspace root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()


@pytest.fixture(autouse=True)
def guard_test_database_target():
    """
    Non-negotiable runtime invariant:
    Ensure that any test execution environment strictly refuses to run
    unless MONGODB_TEST_DB ends in '_test'. Raises RuntimeError immediately.
    """
    test_db = os.getenv("MONGODB_TEST_DB", "joybox_party_room_test")
    if not test_db or not test_db.strip().endswith("_test"):
        raise RuntimeError(
            f"CRITICAL TEST GUARD ABORT: MONGODB_TEST_DB '{test_db}' does not end in '_test'. "
            "Automated test executions are forbidden against non-test databases."
        )


@pytest.fixture(scope="session")
def live_test_client():
    """
    Provides a live MongoDB Atlas test database client.
    1. Strictly validates that test database name ends with '_test' (hard abort otherwise).
    2. Probes live connectivity via ping command.
    3. Builds indexes and collection validators via the authoritative initializer (D1).
    4. Seeds required catalog fixtures (packages, add-ons, rooms, offers, admin).
    5. Asserts required fixtures exist before tests execute.
    6. Cleans up transactional records after test session.
    """
    uri = os.getenv("MONGODB_TEST_URI") or os.getenv("MONGODB_URI", "")
    test_db_name = os.getenv("MONGODB_TEST_DB", "joybox_party_room_test")

    # Hard-abort if database does not end with _test
    if not test_db_name or not test_db_name.strip().endswith("_test"):
        raise RuntimeError(
            f"ABORTED: MONGODB_TEST_DB must end in '_test', got '{test_db_name}'. "
            "No fallback to production or development databases is allowed."
        )

    if not uri or "<" in uri:
        pytest.skip(
            "NOT RUN: Live MongoDB Atlas test credentials not found in environment or backend/.env. "
            "Set MONGODB_URI or MONGODB_TEST_URI to an active Atlas cluster."
        )

    assert_is_test_database(test_db_name)

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True, appname="joybox-pytest-session")
        assert_live_test_client(client, test_db_name)
    except Exception as exc:
        pytest.skip(
            f"NOT RUN: Live MongoDB Atlas cluster unreachable or not configured: {str(exc)}. "
            "Integration and concurrency tests require an active Atlas cluster."
        )

    test_db = client[test_db_name]

    # 1. Authoritative Index & Schema Validator Initialization (D1)
    init_indexes(db=test_db, dry_run=False)

    # 2. Seed Catalog Fixtures (T2)
    # Rooms
    test_db.rooms.update_one(
        {"roomId": "main"},
        {"$set": {"roomId": "main", "name": "Main Celebration Hall", "isActive": True, "updatedAt": datetime.now(timezone.utc)}},
        upsert=True
    )

    # Packages
    seed_packages(db=test_db, dry_run=False)

    # Add-ons
    seed_addons(db=test_db, dry_run=False)

    # Offers
    seed_offers(db=test_db, dry_run=False)

    # Admin User
    create_admin_user(
        username="admin_test",
        email="admintest@joyboxparty.in",
        display_name="Test Admin",
        password="TestAdminPassword123!",
        role="owner",
        db=test_db
    )

    # 3. Assert fixtures exist before tests execute (T2 Guard)
    assert test_db.packages.count_documents({"code": "basic", "isActive": True}) > 0, "Package 'basic' fixture missing!"
    assert test_db.packages.count_documents({"code": "gold", "isActive": True}) > 0, "Package 'gold' fixture missing!"
    assert test_db.packages.count_documents({"code": "diamond", "isActive": True}) > 0, "Package 'diamond' fixture missing!"
    assert test_db.addOns.count_documents({"isActive": True}) >= 3, "Add-ons fixtures missing!"
    assert test_db.offers.count_documents({"isActive": True}) >= 1, "Promotional offer fixture missing!"
    assert test_db.rooms.count_documents({"roomId": "main", "isActive": True}) > 0, "Main room fixture missing!"
    assert test_db.users.count_documents({"role": "owner", "isActive": True}) > 0, "Owner user fixture missing!"

    yield test_db

    # Session Teardown: Clean transactional data
    test_db.slotClaims.delete_many({})
    test_db.bookings.delete_many({})
    test_db.bookingHolds.delete_many({})
    test_db.offerRedemptions.delete_many({})
    test_db.idempotencyKeys.delete_many({})
    test_db.rateLimits.delete_many({})
    test_db.availabilityBlocks.delete_many({})
