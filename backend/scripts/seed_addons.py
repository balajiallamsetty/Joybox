import os
import sys
import argparse
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.utils.db_safety import get_script_db_client, UnsafeDatabaseError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

ADDONS_SEED = [
    {
        "code": "bubble_entry",
        "name": "Bubble Machine Entry",
        "nameTe": "బుడగల మెషిన్ ఎంట్రీ",
        "description": "Magical floating bubbles for cake cutting entry",
        "descriptionTe": "కేక్ కట్టింగ్ సమయంలో అద్భుతమైన బుడగల ఎంట్రీ",
        "priceMinor": 30000,
        "currency": "INR",
        "iconSymbol": "bubble_chart",
        "displayOrder": 1,
        "isActive": True,
        "schemaVersion": 1,
    },
    {
        "code": "fog_entry",
        "name": "Low-Lying Fog Cloud",
        "nameTe": "లో-లైయింగ్ ఫాగ్ ఎంట్రీ",
        "description": "Dense floor mist for grand royal entry vibes",
        "descriptionTe": "రాయల్ ఎంట్రీ అనుభూతినిచ్చే దట్టమైన నేల పొగ ఎఫెక్ట్",
        "priceMinor": 50000,
        "currency": "INR",
        "iconSymbol": "cloud",
        "displayOrder": 2,
        "isActive": True,
        "schemaVersion": 1,
    },
    {
        "code": "cold_fire_one_shot",
        "name": "Cold-Fire Spark Gun (1 shot)",
        "nameTe": "కోల్డ్-ఫైర్ స్పార్క్ గన్ (1 షాట్)",
        "description": "Safe indoor pyrotechnic spark blast",
        "descriptionTe": "ఇండోర్ పార్టీలకు సురక్షితమైన స్పార్క్ గన్ పేలుడు",
        "priceMinor": 30000,
        "currency": "INR",
        "iconSymbol": "flare",
        "displayOrder": 3,
        "isActive": True,
        "schemaVersion": 1,
    }
]


def seed_addons(
    db=None,
    db_name=None,
    uri=None,
    allow_production=False,
    confirm_token=None,
    dry_run=False
):
    if db is None:
        if not db_name:
            print("[!] ERROR: Explicit --db target is required.")
            sys.exit(1)
        try:
            client, db = get_script_db_client(
                db_name=db_name,
                uri=uri,
                allow_production=allow_production,
                confirm_token=confirm_token,
                appname="joybox-seed-addons"
            )
        except UnsafeDatabaseError as e:
            print(f"[!] SAFETY ERROR: {e}")
            sys.exit(1)

    target_name = db.name
    print(f"[*] Upserting add-ons in database '{target_name}' (dry_run={dry_run})...")
    if dry_run:
        for addon in ADDONS_SEED:
            print(f"  [DRY-RUN] Would upsert add-on: {addon['name']} (+Rs. {addon['priceMinor'] // 100})")
        return

    now = datetime.now(timezone.utc)
    for addon in ADDONS_SEED:
        doc = dict(addon)
        doc["updatedAt"] = now
        res = db.addOns.update_one(
            {"code": doc["code"]},
            {"$set": doc, "$setOnInsert": {"createdAt": now}},
            upsert=True
        )
        action = "Created" if res.upserted_id else "Updated"
        print(f"  [+] {action} add-on: {doc['name']} (+Rs. {doc['priceMinor'] // 100})")

    print("[+] Add-ons seed complete.")


def main():
    parser = argparse.ArgumentParser(description="Seed party add-ons catalog.")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to target production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying database")
    args = parser.parse_args()

    seed_addons(
        db_name=args.db,
        uri=args.uri,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
