"""
MongoDB Backup and Restore Automation Script for Joybox Party Room.
Provides CLI utilities for:
1. Creating a timestamped backup directory (with BSON JSON serialization).
2. Performing an audited restore drill into a verified test database.
3. Retention pruning for older backup snapshots.

Guarded by db_safety: refuses production operations without explicit operator flags.
"""
import os
import sys
import json
import argparse
import shutil
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.utils.db_safety import get_script_db_client, assert_is_test_database, UnsafeDatabaseError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backups"))
os.makedirs(BACKUP_DIR, exist_ok=True)

COLLECTIONS_TO_BACKUP = [
    "packages",
    "addOns",
    "rooms",
    "offers",
    "galleryAssets",
    "faqs",
    "bookings",
    "bookingHolds",
    "slotClaims",
    "availabilityBlocks",
    "payments",
    "refunds",
    "users",
    "inquiries",
    "auditLogs"
]


def prune_old_backups(retention_days: int = 30):
    """Deletes backup directories older than retention_days."""
    if retention_days <= 0:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    print(f"[*] Pruning backups older than {retention_days} days (before {cutoff.isoformat()})...")
    for item in os.listdir(BACKUP_DIR):
        item_path = os.path.join(BACKUP_DIR, item)
        if os.path.isdir(item_path):
            manifest = os.path.join(item_path, "backup_manifest.json")
            if os.path.exists(manifest):
                try:
                    with open(manifest, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    ts_str = data.get("timestamp")
                    if ts_str:
                        backup_dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
                        if backup_dt < cutoff:
                            shutil.rmtree(item_path)
                            print(f"  [-] Deleted expired backup: {item}")
                except Exception as e:
                    print(f"  [!] Could not parse manifest for {item}: {e}")


def backup_database(
    db_name: str,
    uri: str = None,
    allow_production: bool = False,
    confirm_token: str = None,
    retention_days: int = 30,
    dry_run: bool = False
) -> str:
    """Exports collection JSON documents to a timestamped backup directory."""
    if not db_name:
        print("[!] ERROR: Explicit --db target is required.")
        sys.exit(1)

    try:
        client, db = get_script_db_client(
            db_name=db_name,
            uri=uri,
            allow_production=allow_production,
            confirm_token=confirm_token,
            appname="joybox-db-backup"
        )
    except UnsafeDatabaseError as e:
        print(f"[!] SAFETY ERROR: {e}")
        sys.exit(1)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_dir = os.path.join(BACKUP_DIR, f"{db.name}_{timestamp}")

    print(f"[*] Starting JSON backup of database '{db.name}' (dry_run={dry_run})...")
    if dry_run:
        print(f"  [DRY-RUN] Would backup collections {COLLECTIONS_TO_BACKUP} to {target_dir}")
        return target_dir

    os.makedirs(target_dir, exist_ok=True)
    meta = {"database": db.name, "timestamp": timestamp, "collections": {}}
    from bson import json_util

    for coll_name in COLLECTIONS_TO_BACKUP:
        docs = list(db[coll_name].find())
        out_file = os.path.join(target_dir, f"{coll_name}.json")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(json_util.dumps(docs, indent=2))
        meta["collections"][coll_name] = len(docs)
        print(f"  [+] Exported {len(docs)} documents from '{coll_name}'")

    meta_file = os.path.join(target_dir, "backup_manifest.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[+] Backup completed successfully into: {target_dir}")
    prune_old_backups(retention_days)
    return target_dir


def restore_drill(
    backup_dir: str,
    target_db_name: str,
    uri: str = None,
    dry_run: bool = False
) -> dict:
    """
    Restores collection documents from a backup directory into a verified _test database.
    Verifies restored document counts against the backup manifest.
    """
    assert_is_test_database(target_db_name)

    manifest_file = os.path.join(backup_dir, "backup_manifest.json")
    if not os.path.exists(manifest_file):
        raise ValueError(f"Invalid backup directory '{backup_dir}': missing backup_manifest.json")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"[*] Starting Restore Drill into TEST database: '{target_db_name}' (dry_run={dry_run})...")
    print(f"[*] Source manifest: {manifest.get('database')} at {manifest.get('timestamp')}")

    if dry_run:
        print(f"  [DRY-RUN] Would restore {len(manifest.get('collections', {}))} collections into '{target_db_name}'")
        return {"status": "DRY_RUN", "manifest": manifest}

    client, db = get_script_db_client(
        db_name=target_db_name,
        uri=uri,
        allow_production=False,
        appname="joybox-restore-drill"
    )

    from bson import json_util
    results = {"targetDatabase": target_db_name, "verified": {}, "allMatched": True}

    for coll_name, expected_count in manifest.get("collections", {}).items():
        json_path = os.path.join(backup_dir, f"{coll_name}.json")
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                docs = json_util.loads(f.read())
            db[coll_name].delete_many({})
            if docs:
                db[coll_name].insert_many(docs)
            restored_count = db[coll_name].count_documents({})
            matched = (restored_count == expected_count)
            results["verified"][coll_name] = {
                "expected": expected_count,
                "restored": restored_count,
                "matched": matched
            }
            if not matched:
                results["allMatched"] = False
            status_symbol = "OK" if matched else "FAIL"
            print(f"  [{status_symbol}] Restored {restored_count}/{expected_count} documents into '{target_db_name}.{coll_name}'")

    print(f"[+] Restore drill complete! All counts match: {results['allMatched']}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Joybox Database Backup & Restore Automation.")
    parser.add_argument("--backup", action="store_true", help="Run database backup export")
    parser.add_argument("--restore-drill", action="store_true", help="Run restore drill into test database")
    parser.add_argument("--db", default=None, help="Database to backup (e.g. joybox_party_room_test)")
    parser.add_argument("--target-db", default="joybox_party_room_test", help="Target test DB for restore (must end in _test)")
    parser.add_argument("--backup-dir", default=None, help="Directory to restore from (defaults to latest backup)")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to backup production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")
    parser.add_argument("--retention-days", type=int, default=30, help="Retention period for backups in days (default: 30)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without modifying filesystem or database")
    args = parser.parse_args()

    if args.backup:
        if not args.db:
            print("[!] ERROR: --db is required for --backup. Example: --db joybox_party_room_test")
            sys.exit(1)
        backup_database(
            db_name=args.db,
            allow_production=args.allow_production,
            confirm_token=args.confirm_production,
            retention_days=args.retention_days,
            dry_run=args.dry_run
        )
    elif args.restore_drill:
        if args.backup_dir:
            b_dir = args.backup_dir
        else:
            subdirs = sorted([os.path.join(BACKUP_DIR, d) for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))])
            if not subdirs:
                print("[*] No existing backups found; running backup of test database first...")
                b_dir = backup_database(
                    db_name=args.target_db,
                    retention_days=args.retention_days,
                    dry_run=args.dry_run
                )
            else:
                b_dir = subdirs[-1]

        restore_drill(
            backup_dir=b_dir,
            target_db_name=args.target_db,
            dry_run=args.dry_run
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
