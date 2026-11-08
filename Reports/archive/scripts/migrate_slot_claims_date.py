import os
import sys
import argparse
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Ensure environment is loaded
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv()

# Add backend to sys.path so we can import datetime_utils and db_safety
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.utils.datetime_utils import format_ist_date, ensure_utc
from app.utils.db_safety import assert_is_test_database, assert_live_test_client


def migrate_slot_claims(dry_run: bool = True, force_prod: bool = False):
    """
    Backfills the 'date' field (YYYY-MM-DD in Asia/Kolkata timezone) for all
    documents in the slotClaims collection that lack it.
    Defaults to dry-run mode. Requires explicit safety verification.
    """
    uri = os.getenv("MONGODB_TEST_URI") or os.getenv("MONGODB_URI", "")
    target_db_name = os.getenv("MONGODB_TEST_DB", "joybox_party_room_test")

    print("================================================================================")
    print("JOYBOX PARTY ROOM — SLOT CLAIMS DATE MIGRATION SCRIPT")
    print("================================================================================")
    print(f"Mode          : {'DRY RUN (No writes)' if dry_run else 'APPLY (Live writes)'}")
    print(f"Target DB     : {target_db_name}")

    if not force_prod:
        assert_is_test_database(target_db_name)

    client = MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True, appname="joybox-migration")
    if not force_prod:
        assert_live_test_client(client, target_db_name)

    db = client[target_db_name]

    # Find claims missing or null 'date'
    unmigrated_cursor = db.slotClaims.find({"$or": [{"date": {"$exists": False}}, {"date": None}]})
    unmigrated = list(unmigrated_cursor)

    total_found = len(unmigrated)
    print(f"Unmigrated slotClaims found: {total_found}")

    if total_found == 0:
        print("[+] All slotClaims already possess a valid 'date' field. Nothing to migrate.")
        return 0

    mappable = []
    unmappable = []

    for doc in unmigrated:
        doc_id = doc.get("_id")
        slot_start = doc.get("slotStart")

        if not slot_start:
            unmappable.append((doc_id, "Missing slotStart field"))
            continue

        try:
            if isinstance(slot_start, datetime):
                dt_utc = ensure_utc(slot_start)
                cal_date_ist = format_ist_date(dt_utc)
                mappable.append((doc_id, cal_date_ist))
            else:
                unmappable.append((doc_id, f"Invalid slotStart type: {type(slot_start)}"))
        except Exception as exc:
            unmappable.append((doc_id, f"Date conversion error: {exc}"))

    print(f"Mappable claims   : {len(mappable)}")
    print(f"Unmappable claims : {len(unmappable)}")

    if unmappable:
        print("\n[!] WARNING: Unmappable claims detected (will not be guessed):")
        for u_id, reason in unmappable:
            print(f"    - ID {u_id}: {reason}")

    if dry_run:
        print("\n[*] DRY RUN COMPLETE: 0 database modifications made.")
        print("    Run with --apply to execute the updates on the target database.")
        return len(mappable)

    # Perform updates
    updated_count = 0
    for doc_id, cal_date_ist in mappable:
        res = db.slotClaims.update_one(
            {"_id": doc_id},
            {"$set": {"date": cal_date_ist}}
        )
        if res.modified_count > 0:
            updated_count += 1

    print(f"\n[+] Successfully updated {updated_count} slotClaims with 'date'.")

    # Ensure index exists
    print("[*] Ensuring index on ('roomId', 'date', 'slotStart')...")
    db.slotClaims.create_index([("roomId", 1), ("date", 1), ("slotStart", 1)])
    print("[+] Index verified successfully.")

    return updated_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill 'date' on slotClaims.")
    parser.add_argument("--apply", action="store_true", help="Apply updates (default is dry run).")
    parser.add_argument("--force-prod", action="store_true", help="Allow running on non-test DB (requires owner approval).")
    args = parser.parse_args()

    migrate_slot_claims(dry_run=not args.apply, force_prod=args.force_prod)

