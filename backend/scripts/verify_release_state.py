"""
Read-Only Release State Verifier for Joybox Party Room.
Confirms required database indexes, active packages, add-ons, rooms, offers, and admin users exist.
Prints PASS/FAIL status without exposing sensitive credentials, tokens, or customer data.
"""
import os
import sys
import argparse
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.utils.db_safety import get_script_db_client, UnsafeDatabaseError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

REQUIRED_INDEXES = {
    "packages": ["code_1"],
    "addOns": ["code_1"],
    "customers": ["phone_1"],
    "bookings": ["bookingReference_1", "roomId_1_startAt_1_endAt_1_bookingStatus_1"],
    "bookingHolds": ["expiresAt_1", "sessionToken_1"],
    "slotClaims": ["roomId_1_slotStart_1", "roomId_1_date_1_slotStart_1", "expiresAt_1"],
    "offers": ["isActive_1"],
    "payments": ["providerOrderId_1", "providerPaymentId_1"],
    "users": ["username_1", "email_1"],
}


def verify_release_state(
    db_name: str,
    uri: str = None,
    allow_production: bool = False,
    confirm_token: str = None
) -> bool:
    print("==================================================================")
    print("   JOYBOX PARTY ROOM — READ-ONLY RELEASE STATE VERIFICATION")
    print(f"   Target Database: '{db_name}'")
    print("==================================================================")

    try:
        client, db = get_script_db_client(
            db_name=db_name,
            uri=uri,
            allow_production=allow_production,
            confirm_token=confirm_token,
            appname="joybox-release-verify"
        )
    except UnsafeDatabaseError as e:
        print(f"[!] SAFETY ERROR: {e}")
        return False

    all_passed = True

    # 1. Check Indexes
    print("\n[1/5] Verifying authoritative database indexes...")
    for coll_name, expected_idx_names in REQUIRED_INDEXES.items():
        try:
            indexes = db[coll_name].index_information()
            for idx_name in expected_idx_names:
                if idx_name in indexes:
                    print(f"  [PASS] Index '{idx_name}' exists on '{coll_name}'")
                else:
                    print(f"  [FAIL] Missing required index '{idx_name}' on '{coll_name}'")
                    all_passed = False
        except Exception as exc:
            print(f"  [FAIL] Could not inspect collection '{coll_name}': {exc}")
            all_passed = False

    # 2. Check Packages
    print("\n[2/5] Verifying celebration packages catalog...")
    active_packages = list(db.packages.find({"isActive": True}, {"code": 1, "name": 1, "pricePerHourMinor": 1}))
    pkg_codes = {p["code"] for p in active_packages}
    required_codes = {"basic", "gold", "diamond"}
    if required_codes.issubset(pkg_codes):
        print(f"  [PASS] Found {len(active_packages)} active packages: {sorted(list(pkg_codes))}")
    else:
        print(f"  [FAIL] Missing required package codes: {required_codes - pkg_codes}")
        all_passed = False

    # 3. Check Add-ons and Rooms
    print("\n[3/5] Verifying add-ons and rooms catalogs...")
    active_addons = db.addOns.count_documents({"isActive": True})
    if active_addons >= 3:
        print(f"  [PASS] Found {active_addons} active celebration add-ons")
    else:
        print(f"  [FAIL] Expected at least 3 active add-ons, found {active_addons}")
        all_passed = False

    main_room = db.rooms.find_one({"roomId": "main", "isActive": True})
    if main_room:
        print(f"  [PASS] Room 'main' exists and is active ({main_room.get('name')})")
    else:
        print("  [FAIL] Default room 'main' missing or inactive")
        all_passed = False

    # 4. Check Promotional Offers
    print("\n[4/5] Verifying active celebration promotional offers...")
    active_offers = db.offers.count_documents({"isActive": True})
    if active_offers >= 1:
        print(f"  [PASS] Found {active_offers} active promotional offer(s)")
    else:
        print("  [FAIL] No active promotional offers configured in database")
        all_passed = False

    # 5. Check Admin User
    print("\n[5/5] Verifying administrator user accounts...")
    owner_user = db.users.find_one({"role": "owner", "isActive": True}, {"username": 1, "role": 1})
    if owner_user:
        print(f"  [PASS] Active administrator account with owner privileges exists ('{owner_user['username']}')")
    else:
        print("  [FAIL] No active user with 'owner' role found in database")
        all_passed = False

    print("\n==================================================================")
    if all_passed:
        print("   [+] ALL VERIFICATION CHECKS PASSED: Environment ready for release.")
    else:
        print("   [!] ONE OR MORE VERIFICATION CHECKS FAILED: Review items above.")
    print("==================================================================")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Verify database release state (indexes, catalog, users).")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to inspect production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if inspecting production")
    args = parser.parse_args()

    passed = verify_release_state(
        db_name=args.db,
        uri=args.uri,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production
    )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

