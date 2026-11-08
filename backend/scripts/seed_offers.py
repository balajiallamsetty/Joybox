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

OFFERS_SEED = [
    {
        "name": "Introductory Monthly Celebration Offer",
        "nameTe": "నెలవారీ ప్రారంభ ప్రత్యేక ఆఫర్",
        "description": "Basic Package at ₹500/hour for the first 5 eligible bookings each month",
        "descriptionTe": "ప్రతి నెల మొదటి 5 బుకింగ్‌లకు బేసిక్ ప్యాకేజీ కేవలం ₹500/గంటకే",
        "eligiblePackageCode": "basic",
        "promoPricePerHourMinor": 50000,
        "monthlyLimit": 5,
        "monthlyRedemptionCount": 0,
        "currentPeriodKey": datetime.now(timezone.utc).strftime("%Y-%m"),
        "isActive": True,
        "schemaVersion": 1,
    }
]


def seed_offers(
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
                appname="joybox-seed-offers"
            )
        except UnsafeDatabaseError as e:
            print(f"[!] SAFETY ERROR: {e}")
            sys.exit(1)

    target_name = db.name
    print(f"[*] Upserting offers in database '{target_name}' (dry_run={dry_run})...")
    if dry_run:
        for offer in OFFERS_SEED:
            print(f"  [DRY-RUN] Would upsert offer: {offer['name']} (Rs. {offer['promoPricePerHourMinor'] // 100}/hr)")
        return

    now = datetime.now(timezone.utc)
    for offer in OFFERS_SEED:
        doc = dict(offer)
        doc["updatedAt"] = now
        res = db.offers.update_one(
            {"eligiblePackageCode": doc["eligiblePackageCode"]},
            {"$set": doc, "$setOnInsert": {"createdAt": now}},
            upsert=True
        )
        action = "Created" if res.upserted_id else "Updated"
        print(f"  [+] {action} offer: {doc['name']} (Rs. {doc['promoPricePerHourMinor'] // 100}/hr)")

    print("[+] Offers seed complete.")


def main():
    parser = argparse.ArgumentParser(description="Seed promotional celebration offers.")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to target production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying database")
    args = parser.parse_args()

    seed_offers(
        db_name=args.db,
        uri=args.uri,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
