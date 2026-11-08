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

PACKAGES_SEED = [
    {
        "code": "basic",
        "name": "Basic",
        "nameTe": "బేసిక్",
        "pricePerHourMinor": 99900,
        "currency": "INR",
        "features": [
            "Entire Air-Conditioned Private Hall",
            "Curated Birthday / Occasion Theme Decor",
            "High-output Sound System & Party Music",
            "Vibrant Ambient Hall Lighting"
        ],
        "featuresTe": [
            "పూర్తి ప్రైవేట్ ఏసీ హాల్",
            "బర్త్‌డే / ప్రత్యేక సందర్భం థీమ్ డెకరేషన్",
            "హై-క్వాలిటీ సౌండ్ సిస్టమ్ & మ్యూజిక్",
            "లైటింగ్ & పార్టీ అంబియన్స్"
        ],
        "excludes": [
            "Fresh Celebration Cake",
            "Customized Name Display",
            "Special FX (Fog, Bubbles, Spark Guns)"
        ],
        "includedAddOnCodes": [],
        "isFeatured": False,
        "displayOrder": 1,
        "isActive": True,
        "schemaVersion": 1,
    },
    {
        "code": "gold",
        "name": "Gold",
        "nameTe": "గోల్డ్",
        "pricePerHourMinor": 150000,
        "currency": "INR",
        "features": [
            "Everything in Basic Package",
            "Fresh 0.5 kg Birthday / Celebration Cake",
            "Personalized Acrylic / Neon Name Display",
            "Easel Stand Custom Welcome Chalkboard",
            "Dedicated Table for Guest Treats & Gifts"
        ],
        "featuresTe": [
            "బేసిక్ ప్యాకేజీలోని ప్రతి ఫీచర్",
            "తాజా 0.5 కేజీ బర్త్‌డే కేక్",
            "కస్టమైజ్డ్ పేరు లెటర్స్ డిస్ప్లే",
            "వెల్కమ్ బోర్డు",
            "గిఫ్ట్స్ & ట్రీట్స్ టేబుల్ అరేంజ్‌మెంట్"
        ],
        "excludes": [
            "Bubble & Fog Special Effects"
        ],
        "includedAddOnCodes": [],
        "isFeatured": True,
        "displayOrder": 2,
        "isActive": True,
        "schemaVersion": 1,
    },
    {
        "code": "diamond",
        "name": "Diamond",
        "nameTe": "డైమండ్",
        "pricePerHourMinor": 250000,
        "currency": "INR",
        "features": [
            "Everything in Gold Package",
            "Magical High-Density Bubble Machine Entry",
            "Cinematic Low-Lying Fog Cloud Entry",
            "1 Indoor Cold-Fire Spark Gun Blast",
            "Assisted Lighting for 4K Video Captures"
        ],
        "featuresTe": [
            "గోల్డ్ ప్యాకేజీలోని ప్రతి ఫీచర్",
            "బుడగల మెషిన్ ఎంట్రీ",
            "సినిమాటిక్ ఫాగ్ క్లౌడ్ ఎంట్రీ",
            "1 కోల్డ్-ఫైర్ స్పార్క్ గన్ షాట్",
            "వీడియో కవరేజ్ కోసం ప్రత్యేక లైటింగ్"
        ],
        "excludes": [],
        "includedAddOnCodes": ["bubble_entry", "fog_entry", "cold_fire_one_shot"],
        "isFeatured": False,
        "displayOrder": 3,
        "isActive": True,
        "schemaVersion": 1,
    }
]

def seed_packages(
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
                appname="joybox-seed-packages"
            )
        except UnsafeDatabaseError as e:
            print(f"[!] SAFETY ERROR: {e}")
            sys.exit(1)

    target_name = db.name
    print(f"[*] Upserting packages in database '{target_name}' (dry_run={dry_run})...")
    if dry_run:
        for pkg in PACKAGES_SEED:
            print(f"  [DRY-RUN] Would upsert package: {pkg['name']} (Rs. {pkg['pricePerHourMinor'] // 100}/hr)")
        return

    now = datetime.now(timezone.utc)
    for pkg in PACKAGES_SEED:
        doc = dict(pkg)
        doc["updatedAt"] = now
        res = db.packages.update_one(
            {"code": doc["code"]},
            {"$set": doc, "$setOnInsert": {"createdAt": now}},
            upsert=True
        )
        action = "Created" if res.upserted_id else "Updated"
        print(f"  [+] {action} package: {doc['name']} (Rs. {doc['pricePerHourMinor'] // 100}/hr)")

    print("[+] Packages seed complete.")


def main():
    parser = argparse.ArgumentParser(description="Seed celebration packages catalog.")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to target production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying database")
    args = parser.parse_args()

    seed_packages(
        db_name=args.db,
        uri=args.uri,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()

