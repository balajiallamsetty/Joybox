"""Empty the production database for client delivery.

This script is not part of the Render build or start command.
It refuses to run under pytest, CI, or Render.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class DeliveryResetRefused(RuntimeError):
    pass


def assert_delivery_reset_allowed(db_name: str, typed_name: str, confirm: bool, environ: dict) -> str:
    """Refuse unless this is an explicit local wipe of the configured production database."""
    if not confirm:
        raise DeliveryResetRefused("REFUSED: pass --confirm and type the database name.")

    blocked_markers = ("PYTEST_CURRENT_TEST", "CI", "RENDER", "RENDER_SERVICE_ID", "RENDER_SERVICE_NAME")
    if any(environ.get(marker) for marker in blocked_markers):
        raise DeliveryResetRefused(
            "REFUSED: destructive reset is blocked in tests, CI, and the deployed Render service."
        )

    if str(environ.get("ALLOW_DESTRUCTIVE_SCRIPTS", "")).strip().lower() != "true":
        raise DeliveryResetRefused("REFUSED: set ALLOW_DESTRUCTIVE_SCRIPTS=true in the local shell.")

    configured = (environ.get("MONGODB_DB") or "joybox_party_room").strip()
    typed = (typed_name or "").strip()
    if not typed or typed != configured or typed != (db_name or "").strip():
        raise DeliveryResetRefused(
            "REFUSED: typed database name must equal the configured production database name."
        )
    return configured


def empty_all_collections(db) -> dict:
    """Delete every document. Returns before/after counts and does not print document bodies."""
    before = {}
    after = {}
    for name in sorted(db.list_collection_names()):
        before[name] = db[name].count_documents({})
        db[name].delete_many({})
        after[name] = db[name].count_documents({})
    return {"before": before, "after": after}


def test_database_names(client) -> list:
    names = []
    for name in sorted(client.list_database_names()):
        if name in ("admin", "local", "config"):
            continue
        if name.endswith("_test") or name.endswith("_scratch_test"):
            names.append(name)
    return names


def main():
    import argparse
    from pymongo import MongoClient

    parser = argparse.ArgumentParser(description="Empty the Joybox production database for delivery.")
    parser.add_argument("--confirm", action="store_true", help="Required acknowledgement.")
    args = parser.parse_args()

    typed = input("Type the database name to wipe: ").strip()
    configured = assert_delivery_reset_allowed(
        db_name=os.getenv("MONGODB_DB", "joybox_party_room"),
        typed_name=typed,
        confirm=args.confirm,
        environ=os.environ,
    )
    uri = os.getenv("MONGODB_URI", "")
    if not uri or "<" in uri:
        raise DeliveryResetRefused("REFUSED: MONGODB_URI is missing.")

    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    print("TARGET", configured)
    print("WILL_DROP_TEST_DATABASES")
    drop_names = [name for name in test_database_names(client) if name != configured]
    for name in drop_names:
        print(name)

    db = client[configured]
    print("WILL_EMPTY")
    for name in sorted(db.list_collection_names()):
        print(f"{name} {db[name].count_documents({})}")

    result = empty_all_collections(db)
    print("AFTER_EMPTY")
    for name, count in result["after"].items():
        print(f"{name} {count}")

    for name in drop_names:
        client.drop_database(name)
        print("DROPPED", name)
    print("RESET_COMPLETE")


if __name__ == "__main__":
    try:
        main()
    except DeliveryResetRefused as exc:
        print(str(exc))
        sys.exit(1)
