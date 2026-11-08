"""
Master Seed Script for Joybox Party Room.
Runs all catalog, pricing, room, offer, gallery, and FAQ seeds idempotently.
Guarded against accidental execution on production without explicit overrides.
"""
import os
import sys
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.db_safety import get_script_db_client, UnsafeDatabaseError
from scripts.init_indexes import init_indexes
from scripts.seed_packages import seed_packages
from scripts.seed_addons import seed_addons
from scripts.seed_offers import seed_offers
from scripts.seed_gallery import seed_gallery
from scripts.seed_faqs import seed_faqs

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()


def seed_rooms(db, dry_run=False):
    """Upserts default main hall room record."""
    room_doc = {
        "roomId": "main",
        "name": "Main Celebration Hall",
        "capacityMax": 35,
        "isActive": True,
        "updatedAt": datetime.now(timezone.utc)
    }
    if dry_run:
        print("  [DRY-RUN] Would upsert room: Main Celebration Hall ('main')")
        return
    db.rooms.update_one(
        {"roomId": room_doc["roomId"]},
        {"$set": room_doc, "$setOnInsert": {"createdAt": datetime.now(timezone.utc)}},
        upsert=True
    )
    print("  [+] Upserted room: Main Celebration Hall ('main')")


def seed_all(
    db=None,
    db_name=None,
    uri=None,
    allow_production=False,
    confirm_token=None,
    dry_run=False
):
    if db is None:
        if not db_name:
            print("[!] ERROR: Explicit --db target is required (e.g. --db joybox_party_room_test).")
            sys.exit(1)
        try:
            client, db = get_script_db_client(
                db_name=db_name,
                uri=uri,
                allow_production=allow_production,
                confirm_token=confirm_token,
                appname="joybox-seed-all"
            )
        except UnsafeDatabaseError as e:
            print(f"[!] SAFETY ERROR: {e}")
            sys.exit(1)

    target_name = db.name
    print("==================================================================")
    print(f"   JOYBOX PARTY ROOM — MASTER SEED & INDEX SYNCHRONIZATION")
    print(f"   Target Database: '{target_name}' (dry_run={dry_run})")
    print("==================================================================")

    print("\n1. Initializing and verifying MongoDB indexes and validators...")
    init_indexes(
        db=db,
        dry_run=dry_run
    )

    print("\n2. Upserting rooms catalog...")
    seed_rooms(db, dry_run=dry_run)

    print("\n3. Upserting packages catalog...")
    seed_packages(
        db=db,
        dry_run=dry_run
    )

    print("\n4. Upserting party add-ons...")
    seed_addons(
        db=db,
        dry_run=dry_run
    )

    print("\n5. Upserting celebration promotional offers...")
    seed_offers(
        db=db,
        dry_run=dry_run
    )

    print("\n6. Upserting gallery showcase assets...")
    seed_gallery(
        db=db,
        dry_run=dry_run
    )

    print("\n7. Upserting customer FAQs...")
    seed_faqs(
        db=db,
        dry_run=dry_run
    )

    print("\n==================================================================")
    print("   [+] MASTER SEED COMPLETE! All records synchronized idempotently.")
    print("==================================================================")


def main():
    parser = argparse.ArgumentParser(description="Master seed and index synchronizer.")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to target production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying database")
    args = parser.parse_args()

    seed_all(
        db_name=args.db,
        uri=args.uri,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
