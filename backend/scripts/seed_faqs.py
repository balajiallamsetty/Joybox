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

FAQS_SEED = [
    {
        "code": "advance_booking_time",
        "question": "How far in advance should I book my celebration?",
        "questionTe": "వేడుక కోసం ఎన్ని రోజుల ముందు బుక్ చేసుకోవాలి?",
        "answer": "We recommend booking at least 2–3 days in advance for weekends and popular evening slots (6:00 PM – 10:00 PM). Same-day bookings are accepted subject to instant slot availability.",
        "answerTe": "వారాంతాలు మరియు సాయంత్రం స్లాట్ల కోసం కనీసం 2-3 రోజుల ముందు బుక్ చేసుకోవాలని సిఫార్సు చేస్తున్నాము.",
        "category": "booking",
        "displayOrder": 1,
        "isActive": True,
    },
    {
        "code": "outside_food_policy",
        "question": "Can we bring outside food, snacks, and cake?",
        "questionTe": "బయటి ఆహారం, స్నాక్స్ మరియు కేక్ తీసుకురావచ్చా?",
        "answer": "Yes! Outside food, snacks, cold beverages, and celebration cakes are 100% permitted. We provide dedicated serving tables and a clean eating area.",
        "answerTe": "అవును! బయటి ఫుడ్, స్నాక్స్, కూల్ డ్రింక్స్ మరియు కేక్ తీసుకురావడానికి పూర్తి అనుమతి ఉంది.",
        "category": "food",
        "displayOrder": 2,
        "isActive": True,
    },
    {
        "code": "guest_capacity",
        "question": "What is the maximum guest capacity of Joybox?",
        "questionTe": "జాయ్‌బాక్స్ గరిష్ట అతిథుల సామర్థ్యం ఎంత?",
        "answer": "Joybox Party Room comfortably accommodates up to 25–30 guests for intimate birthdays, college reunions, family celebrations, and screening parties.",
        "answerTe": "బర్త్‌డేలు, రీయూనియన్లు మరియు ఫ్యామిలీ వేడుకల కోసం 25-30 మంది అతిథులు సౌకర్యవంతంగా ఉండవచ్చు.",
        "category": "venue",
        "displayOrder": 3,
        "isActive": True,
    },
    {
        "code": "music_and_dj_control",
        "question": "Can we play our own music and DJ playlist?",
        "questionTe": "మా స్వంత పాటలు మరియు డీజే ప్లేలిస్ట్ ప్లే చేసుకోవచ్చా?",
        "answer": "Yes! You have full wireless Bluetooth access to our high-output club sound system and party laser lighting directly from your smartphone.",
        "answerTe": "ఖచ్చితంగా! మీ మొబైల్ నుండి బ్లూటూత్ ద్వారా హై-క్వాలిటీ సౌండ్ మరియు లైటింగ్ మీరే కంట్రోల్ చేసుకోవచ్చు.",
        "category": "amenities",
        "displayOrder": 4,
        "isActive": True,
    },
    {
        "code": "cancellation_policy",
        "question": "What is the cancellation and refund policy?",
        "questionTe": "రద్దు మరియు రీఫండ్ నిబంధనలు ఏమిటి?",
        "answer": "Cancellations made more than 48 hours prior to start time receive a 100% full refund. Cancellations between 24 and 48 hours receive a 50% refund. Within 24 hours of start time, advance payments are non-refundable.",
        "answerTe": "48 గంటల ముందు రద్దు చేస్తే 100% రీఫండ్, 24 నుండి 48 గంటల మధ్య రద్దు చేస్తే 50% రీఫండ్ లభిస్తుంది.",
        "category": "policy",
        "displayOrder": 5,
        "isActive": True,
    }
]

def seed_faqs(
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
                appname="joybox-seed-faqs"
            )
        except UnsafeDatabaseError as e:
            print(f"[!] SAFETY ERROR: {e}")
            sys.exit(1)

    target_name = db.name
    print(f"[*] Upserting FAQs in database '{target_name}' (dry_run={dry_run})...")
    if dry_run:
        for item in FAQS_SEED:
            print(f"  [DRY-RUN] Would upsert FAQ: {item['question']}")
        return

    now = datetime.now(timezone.utc)
    for item in FAQS_SEED:
        doc = dict(item)
        doc["updatedAt"] = now
        res = db.faqs.update_one(
            {"code": doc["code"]},
            {"$set": doc, "$setOnInsert": {"createdAt": now}},
            upsert=True
        )
        action = "Created" if res.upserted_id else "Updated"
        print(f"  [+] {action} FAQ: {doc['question']}")

    print("[+] FAQs seed complete.")


def main():
    parser = argparse.ArgumentParser(description="Seed customer FAQs.")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to target production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying database")
    args = parser.parse_args()

    seed_faqs(
        db_name=args.db,
        uri=args.uri,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()

