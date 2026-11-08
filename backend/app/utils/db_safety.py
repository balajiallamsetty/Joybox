import os
import re

PROD_DB_NAME = os.getenv("PROD_DB_NAME", "joybox_party_room")
TEST_DB_SUFFIX = os.getenv("TEST_DB_SUFFIX", "_test")

def get_prod_db_name() -> str:
    return os.getenv("PROD_DB_NAME", "joybox_party_room").strip()

def get_test_db_suffix() -> str:
    return os.getenv("TEST_DB_SUFFIX", "_test").strip()

class UnsafeDatabaseError(RuntimeError):
    """Raised when a test or destructive operation attempts to run against a non-test database."""
    pass

def assert_is_test_database(db_name: str) -> None:
    """
    Enforces the non-negotiable safety invariant:
    Concurrency tests and destructive integration tests must strictly refuse
    to run unless the database name ends with TEST_DB_SUFFIX (default: '_test')
    and does not match PROD_DB_NAME.
    """
    if not db_name or not isinstance(db_name, str):
        raise UnsafeDatabaseError(
            f"CRITICAL TEST ABORTED: Invalid database name '{db_name}'. "
            "Automated test suites require an explicit test database."
        )

    suffix = get_test_db_suffix()
    prod_name = get_prod_db_name()
    clean_name = db_name.strip().lower()

    if clean_name == prod_name.lower() or not clean_name.endswith(suffix.lower()):
        raise UnsafeDatabaseError(
            f"CRITICAL TEST ABORTED: Database name '{db_name}' does not end with '{suffix}'. "
            f"Per safety rules, tests must target a database ending in '{suffix}' and cannot match '{prod_name}'."
        )

def assert_live_test_client(client, db_name: str = None) -> str:
    """
    Verifies that the provided live PyMongo client is actively connected and targeting
    a database whose name strictly ends in '_test'.
    
    1. Probes live connectivity via ping command.
    2. Inspects the target database directly from the live client connection.
    3. Asserts the database name ends in '_test'.
    """
    if client is None:
        raise UnsafeDatabaseError("CRITICAL TEST ABORTED: Live MongoDB client instance is required.")

    # Resolve target database on the client
    target_db = None
    resolved_name = None

    if db_name:
        target_db = client[db_name]
        resolved_name = target_db.name
    else:
        try:
            target_db = client.get_default_database()
            resolved_name = target_db.name if target_db is not None else None
        except Exception:
            resolved_name = None

    if not resolved_name:
        raise UnsafeDatabaseError(
            "CRITICAL TEST ABORTED: Unable to determine active database name on live MongoDB client."
        )

    # Validate name ending with _test
    assert_is_test_database(resolved_name)

    # Check live client connectivity via ping command
    try:
        if hasattr(client, 'admin') and hasattr(client.admin, 'command'):
            client.admin.command('ping')
        elif hasattr(target_db, 'command'):
            target_db.command('ping')
    except Exception as exc:
        raise UnsafeDatabaseError(
            f"CRITICAL TEST ABORTED: Live MongoDB ping check failed: {exc}"
        )

    return resolved_name


def validate_script_db_target(
    db_name: str,
    allow_production: bool = False,
    confirm_token: str = None
) -> str:
    """
    Validates script target database per D2 production-safe requirements:
    1. An explicit database target is required (not empty/None).
    2. Any database ending in '_test' is permitted for automated tests/drills.
    3. Production or non-test databases (e.g. 'joybox_party_room') are STRICTLY REFUSED
       unless both allow_production is True AND (confirm_token == db_name or os.getenv("JOYBOX_ALLOW_PRODUCTION") == "true").
    """
    if not db_name or not isinstance(db_name, str) or not db_name.strip():
        raise UnsafeDatabaseError(
            "CRITICAL: Explicit --db target is required. "
            "Example: --db joybox_party_room_test"
        )

    suffix = get_test_db_suffix()
    prod_name = get_prod_db_name()
    clean_name = db_name.strip()
    if clean_name.lower().endswith(suffix.lower()) and clean_name.lower() != prod_name.lower():
        return clean_name

    # Target is production or non-test database
    env_confirmed = os.getenv("JOYBOX_ALLOW_PRODUCTION", "").strip().lower() in ("true", "1", "yes")
    token_confirmed = (confirm_token or "").strip() == clean_name

    if not allow_production or not (env_confirmed or token_confirmed):
        raise UnsafeDatabaseError(
            f"REFUSED: Operation targeted production/non-test database '{clean_name}'. "
            "To execute against production, you must supply both --allow-production "
            f"AND --confirm-production {clean_name} (or set JOYBOX_ALLOW_PRODUCTION=true)."
        )

    return clean_name


def get_script_db_client(
    db_name: str,
    uri: str = None,
    allow_production: bool = False,
    confirm_token: str = None,
    appname: str = "joybox-script"
):
    """
    Connects to MongoDB client and returns (client, db) guarded by validate_script_db_target.
    Refuses production databases unless explicitly overridden.
    """
    from pymongo import MongoClient
    target_name = validate_script_db_target(
        db_name=db_name,
        allow_production=allow_production,
        confirm_token=confirm_token
    )
    resolved_uri = uri or os.getenv("MONGODB_URI") or os.getenv("MONGODB_TEST_URI")
    if not resolved_uri or "<" in resolved_uri:
        raise ValueError("Valid MongoDB URI not found in environment or arguments.")
    client = MongoClient(resolved_uri, serverSelectionTimeoutMS=5000, tz_aware=True, appname=appname)
    return client, client[target_name]
