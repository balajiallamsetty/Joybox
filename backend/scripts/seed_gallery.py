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

GALLERY_SEED = [
    {
        "code": "neon_birthday_wonderland",
        "title": "Neon Birthday Wonderland & Balloon Arch",
        "titleTe": "నియాన్ బర్త్‌డే వండర్‌ల్యాండ్ & బెలూన్ ఆర్చ్",
        "category": "birthday",
        "tier": "Gold Tier",
        "tierClass": "bg-tertiary-fixed text-on-tertiary-fixed",
        "themeTag": "Kids & Milestone",
        "time": "2h Event",
        "guests": "15–20 Guests",
        "description": "Organic balloon arch, neon cursive Happy Birthday sign, custom acrylic nameplate, dedicated cake pedestal, and surround party lighting.",
        "descriptionTe": "ఆర్గానిక్ బెలూన్ ఆర్చ్, నియాన్ హ్యాపీ బర్త్‌డే లైట్ బోర్డు, పేరు బోర్డు మరియు లైటింగ్.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuCiVJUo2cnESvHf0iIJRBWqZIyAb0UaZ06LAT1pLOJRYpkoJ5bZgWhbJquoopTdOCrbsf4lDte7Tmc6Bqg0UMaH05Ln28UbYXuNDlTwVupevBy4t5p5fIfgr17RKoFINTRIoJAqkkNGoChHjA-fK-IZ-t8qnhHQ3t5I9aGju2PEp0A-gPQwlC31p3Y2zMh1b_Sim2csyqipO-tZy1v68BxZowCqfhFBhQ67G-BCNkSi",
        "altText": "Joybox Party Room Neon Birthday Setup",
        "displayOrder": 1,
        "isActive": True,
    },
    {
        "code": "midnight_dj_bass_adda",
        "title": "Midnight DJ Bass & Laser Squad Adda",
        "titleTe": "మిడ్‌నైట్ డీజే బాస్ & లేజర్ అడ్డా",
        "category": "adda",
        "tier": "Basic Tier",
        "tierClass": "bg-primary-fixed text-primary",
        "themeTag": "College Reunion",
        "time": "3h Booking",
        "guests": "Up to 25 Squad",
        "description": "High-output acoustic speakers, club moving-head lighting, Bluetooth full DJ control from your mobile, chilled AC at 19°C.",
        "descriptionTe": "హై-పవర్ స్పీకర్లు, క్లబ్ లైటింగ్ మరియు బ్లూటూత్ డీజే కంట్రోల్.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuB2BmLC4DpmYGC_NEkUFJeOLq0VcG5YJbKmJBf4a8H2v2V75c9W4UOnSLtrD7X-vhvzKcBsNQahJ30wbJMVXs1nPNAK9EmARvktY8Ue_9mO47E4MAi_AgaLqU02Z_wv3y2twid6bKwEQGwhmbJNn4bNVbAF1KHrkkkPoLqnJmr5ErKpteRvyxCVCSro--yKPKNnl44NMmqSRDhxI_y4dyIZwf7lQPUyRF_UYGwguLz9",
        "altText": "Joybox Party Room Midnight DJ Setup",
        "displayOrder": 2,
        "isActive": True,
    },
    {
        "code": "cinematic_low_fog_entry",
        "title": "Cinematic Low-Fog Fairytale Cloud Entry",
        "titleTe": "సినిమాటిక్ లో-ఫాగ్ క్లౌడ్ ఎంట్రీ",
        "category": "fx",
        "tier": "Diamond Tier",
        "tierClass": "bg-primary-container text-on-primary",
        "themeTag": "Grand Entry FX",
        "time": "Add-on Feature",
        "guests": "Visual Spectacle",
        "description": "Heavy cold dry-ice fog hugging the floor below knees. Odorless, non-toxic, and creates dreamlike video moments.",
        "descriptionTe": "నేలంతా దట్టమైన పొగతో అద్భుతమైన రాయల్ ఎంట్రీ అనుభూతి.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuCrPjm_h7gOjEX3nXCGBlDSHF6XzhXgTfRAihFDny3DyEyew-gcRm_PVFKUWW7sKEt8qukHhIA1gkbKVW5n-8ySPEnnD9FzwAaXMQ_7mMC7N5oEM_g_9lWJ6GsYvTQnNxd5rNTYq9ncuqCTbdgVHchQlgLTVi8ASuipAXV3CeFTwh9229FUEk4eWahmi9u9Iqcd_YBNPHCaUU2WklKKbRl_B8JvZuH1sTf31KQBTH1P",
        "altText": "Joybox Party Room Low Fog Effect",
        "displayOrder": 3,
        "isActive": True,
    },
    {
        "code": "wedding_anniversary_red_gold",
        "title": "10th Wedding Anniversary Romantic Red & Gold",
        "titleTe": "వెడ్డింగ్ యానివర్సరీ రొమాంటిక్ రెడ్ & గోల్డ్",
        "category": "anniversary",
        "tier": "Gold Tier",
        "tierClass": "bg-tertiary-fixed text-on-tertiary-fixed",
        "themeTag": "Couple Special",
        "time": "2h Evening Slot",
        "guests": "Intimate Family",
        "description": "Fairy light backdrop, heart metallic balloon cluster, couple dining setup, customized retro photo video screening.",
        "descriptionTe": "రొమాంటిక్ ఫెయిరీ లైట్లు, కపుల్ టేబుల్ సెటప్ మరియు ఫోటో స్క్రీనింగ్.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuCms6jA-Pyp92AdKy7v7pGL6w_JyEwUF2sEUNeQqv11p8Zj4Z3cGBJ8GqpzNf7e5OQ17E2BlTHo1M5FbYAQMjlmiYqLVg5UplzCTk9NmVSuGMoPmxKiE_pbhKKldETsfObO5jMAAcii-N3DyxJULvsgFwNrNXvSfmnt8WfVm8DJ33w1JeBt5542MBpMPwPCxuFBFxap3d5PA_GIMGn0-JGCD8oqWHhki2fQMefF_tzM",
        "altText": "Joybox Party Room Anniversary Setup",
        "displayOrder": 4,
        "isActive": True,
    },
    {
        "code": "spark_gun_fountain",
        "title": "Indoor Cold-Fire Pyrotechnic Spark Gun",
        "titleTe": "ఇండోర్ కోల్డ్-ఫైర్ స్పార్క్ గన్",
        "category": "fx",
        "tier": "Diamond Tier",
        "tierClass": "bg-primary-container text-on-primary",
        "themeTag": "Cake Cutting FX",
        "time": "Instant Blast",
        "guests": "100% Touch Safe",
        "description": "Cold spark fountain without gunpowder, smoke, or fire hazard. Safe touch sparkles reaching 2.5 meters high.",
        "descriptionTe": "నిప్పు మరియు పొగ లేని సురక్షితమైన స్పార్క్ గన్ పేలుడు.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuBLuf1THI89JRYZoH-KaFG2Aa3owNBD60zbAog3DMqN3e9h_Qkh401pmavYRdkDLUmCYwNPMv43t7O_ISkJPRnPtXY86L_ik5zbX5p2_9xffzkzxwxZg-YKAJD1CntBhn_YZGpdniJRZg_wsbDWeMpNlZFKEwdCs14RX0OTinJcwMpX98jb8cm-zZSL8XsiLCifU1Hk5MAG9xxjNVYBCp-ajVPcp0ANTbQc4EYL6CaA",
        "altText": "Joybox Party Room Cold Fire Spark Gun",
        "displayOrder": 5,
        "isActive": True,
    },
    {
        "code": "neon_21st_rose_gold",
        "title": "Chic 21st Birthday Neon & Rose Gold",
        "titleTe": "21వ బర్త్‌డే నియాన్ & రోజ్ గోల్డ్",
        "category": "birthday",
        "tier": "Gold Tier",
        "tierClass": "bg-tertiary-fixed text-on-tertiary-fixed",
        "themeTag": "Youth Milestone",
        "time": "2h Slot",
        "guests": "Up to 20 Guests",
        "description": "Circular grid backdrop with jumbo glowing 21 LED numerals, metallic balloon framing, and custom welcome chalkboard.",
        "descriptionTe": "ఎల్ఈడీ నంబర్స్, మెటాలిక్ బెలూన్లు మరియు వెల్కమ్ బోర్డు.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuC4NGi3hE338vRVB-9hm2GILwCuv3rgNrbu7qsg_T_gIIggYXdB78mAl0K-moM1IXz04qzsBca-SND3jFKHdsGMi9lA6RbuQJFZQbL7qzMOuH24Q3PjQFyYgkxGbjVtA6ncc_v7ygqLptynQT9sUgfX5JCaKcpUjXMmP0pxcrs4I2swfEvmF3FDGXfGvjg2iDrhEh-IT_9LUnNOi25ivInCfXT8kcyc0rq6e31KOukz",
        "altText": "Joybox Party Room Neon 21st Birthday",
        "displayOrder": 6,
        "isActive": True,
    },
    {
        "code": "cinema_premiere_projector",
        "title": "150-Inch Cinema Premiere & Match Screening",
        "titleTe": "150-అంగుళాల సినిమా ప్రీమియర్ స్క్రీనింగ్",
        "category": "adda",
        "tier": "Basic Tier",
        "tierClass": "bg-primary-fixed text-primary",
        "themeTag": "Movie & Sports Adda",
        "time": "3–4h Slot",
        "guests": "Lounge Comfort",
        "description": "Laser 4K projector wall, Dolby sound setup, plush couch seating, outside popcorn & pizza completely permitted.",
        "descriptionTe": "లేజర్ ప్రొజెక్టర్, డాల్బీ సౌండ్ మరియు హాయిగా కూర్చునే సోఫాలు.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuBOK--pw51UckqEzFwu6EOusW0WXC-Trj-etHPKUSsE3er6-PJsjXJLhRwxc_mef0Io6pdg14CiLisa9C4gWj-Do-P1T8-ok-hBqOO1IoUACfrOA5PXeDIwDOY8Kb1rbHs7LcpyoIqXW2AZjursQe7aH2WFMxz2ulfIgiWADXR0yo61LV6jKT524WI5Vu2elGBch7KZLQzz8maCtqK6DN-ZDKROOwOnG98_hu7JKXVh",
        "altText": "Joybox Party Room Cinema Projector Setup",
        "displayOrder": 7,
        "isActive": True,
    },
    {
        "code": "baby_shower_botanical",
        "title": "Family Baby Shower Botanical & Pastel Glow",
        "titleTe": "బేబీ షవర్ బొటానికల్ & పాస్టెల్ గ్లో",
        "category": "anniversary",
        "tier": "Gold Tier",
        "tierClass": "bg-tertiary-fixed text-on-tertiary-fixed",
        "themeTag": "Family Milestone",
        "time": "2.5h Afternoon",
        "guests": "Multigen Family",
        "description": "Mint and blush pink organic arches, natural eucalyptus accents, golden easel calligraphy, peaceful AC setting.",
        "descriptionTe": "పాస్టెల్ బెలూన్ ఆర్చ్ మరియు ప్రశాంతమైన ఏసీ వాతావరణం.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuBuvliHsQ51VYFIkDK6JF4_61Yd-ioePyIEqErMsJn_42KH6pNYNeh2Uz_dIjZr46pjFxJKUsYiwcZXeeCyfQ9MwJm4hMzGs_tsjlzEGOFdpewJd1xCSB9nncf645r-ght7UeaQib8sdwjfarrUxuXeUatBGxkAILiTsWp-vrpE_7ksdhN5HGTpN1PaCDnsv6RR7P7gaKPSvQ1yodiBkibYW8L5_V_QqOrFl-nikWgd",
        "altText": "Joybox Party Room Baby Shower Setup",
        "displayOrder": 8,
        "isActive": True,
    },
    {
        "code": "bubble_streamer_kids",
        "title": "High-Density Floating Bubble Streamer Blast",
        "titleTe": "బుడగల స్టీమర్ బ్లాస్ట్",
        "category": "kids",
        "tier": "Diamond Tier",
        "tierClass": "bg-primary-container text-on-primary",
        "themeTag": "Kids Wonder FX",
        "time": "Continuous Flow",
        "guests": "All Ages Fun",
        "description": "Double-wheel bubble blower producing thousands of non-staining iridescent bubbles floating across the entire room.",
        "descriptionTe": "పిల్లలు ఎంతో ఇష్టపడే వేలాది అందమైన బుడగల మెషిన్ ఎఫెక్ట్.",
        "url": "https://lh3.googleusercontent.com/aida-public/AB6AXuAHLUhVjmgHU0xl2JZP5uk2VvrMAKNAuDy2MhAi9z7nLClE77NgWAeFZEOVnoMFYAEe6Sacn1YcBUKnQgGg1lKM_nRhVolU7kel8pg3IH0ZZY80CLG7WuF8aHpCN9LqF7p62gjpUcKeEvm3cK0aWfU25mQfHCit6eKDv0rhcy26cZ3c0mnwvhcmjYMzAYcVqzudPW94paaiixo_fCZZN2fy-evbeYm5PFBlIilaMcr1",
        "altText": "Joybox Party Room Bubble Machine",
        "displayOrder": 9,
        "isActive": True,
    }
]

def seed_gallery(
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
                appname="joybox-seed-gallery"
            )
        except UnsafeDatabaseError as e:
            print(f"[!] SAFETY ERROR: {e}")
            sys.exit(1)

    target_name = db.name
    print(f"[*] Upserting gallery assets in database '{target_name}' (dry_run={dry_run})...")
    if dry_run:
        for item in GALLERY_SEED:
            print(f"  [DRY-RUN] Would upsert gallery asset: {item['title']}")
        return

    now = datetime.now(timezone.utc)
    for item in GALLERY_SEED:
        doc = dict(item)
        doc["updatedAt"] = now
        res = db.galleryAssets.update_one(
            {"code": doc["code"]},
            {"$set": doc, "$setOnInsert": {"createdAt": now}},
            upsert=True
        )
        action = "Created" if res.upserted_id else "Updated"
        print(f"  [+] {action} gallery asset: {doc['title']}")

    print("[+] Gallery assets seed complete.")


def main():
    parser = argparse.ArgumentParser(description="Seed gallery assets showcase.")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to target production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying database")
    args = parser.parse_args()

    seed_gallery(
        db_name=args.db,
        uri=args.uri,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()

