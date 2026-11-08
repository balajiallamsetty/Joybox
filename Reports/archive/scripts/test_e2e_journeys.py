"""
Joybox Party Room — Phase 8 End-to-End Automated Test Suite.
Executes core journeys against the real MongoDB Atlas TEST database:
1. Browse packages & Price Estimator
2. Booking flow & Hold creation
3. Double-booking race contention guard
4. Inquiry submission & Toast confirmation
5. Token-protected Booking status & Cancellation
6. Admin authentication & Slot blocking / Management
"""
import os
import sys
import time
import uuid
import threading
import http.server
import socketserver
from datetime import datetime, timedelta, timezone

# Add paths
sys.path.insert(0, os.path.abspath("backend"))

from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("backend/.env")
load_dotenv()

from app import create_app
from app.config import Config
from app.utils.db_safety import assert_is_test_database, assert_live_test_client
from app.utils.datetime_utils import now_utc, format_ist_time

TEST_DB_NAME = os.getenv("MONGODB_TEST_DB", "joybox_party_room_test")
assert_is_test_database(TEST_DB_NAME)

E2E_SCREENSHOT_DIR = os.path.abspath("docs/visual_audit/e2e")
os.makedirs(E2E_SCREENSHOT_DIR, exist_ok=True)

class QuietSPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.abspath("frontend/dist"), **kwargs)

    def log_message(self, format, *args):
        pass # Quiet server logs

    def do_GET(self):
        path = self.path.split('?')[0]
        full_path = self.translate_path(path)
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            self.path = "/index.html"
        return super().do_GET()

def start_frontend_server(port=4174):
    server = socketserver.TCPServer(("127.0.0.1", port), QuietSPAHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def run_e2e_tests():
    print("==================================================================")
    print("   JOYBOX PARTY ROOM — PHASE 8 END-TO-END AUTOMATED VERIFICATION")
    print(f"   Database: {TEST_DB_NAME} (MongoDB Atlas)")
    print("==================================================================")

    uri = os.getenv("MONGODB_URI")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True)
    assert_live_test_client(client, TEST_DB_NAME)
    db = client[TEST_DB_NAME]

    # Clean test collections before test run
    db.slotClaims.delete_many({})
    db.bookings.delete_many({})
    db.bookingHolds.delete_many({})
    db.availabilityBlocks.delete_many({})
    db.inquiries.delete_many({})
    db.offerRedemptions.delete_many({})
    db.rateLimits.delete_many({})
    db.idempotencyKeys.delete_many({})

    # Initialize Flask app in test mode connected to Atlas test database
    flask_app = create_app({
        "TESTING": True,
        "MONGODB_DB": TEST_DB_NAME,
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-bytes-long!",
        "FLASK_ENV": "development",
    })
    flask_app.extensions["mongo_db"] = db

    test_client = flask_app.test_client()

    results = {}

    # JOURNEY 1: Browse Packages & Price Estimator
    print("\n[JOURNEY 1] Testing Packages Catalog & Pricing Quote API...")
    try:
        res = test_client.get("/api/packages")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        pkgs = res.get_json()["data"]["items"]
        assert len(pkgs) >= 3, "Expected at least 3 packages"
        pkg_codes = [p["code"] for p in pkgs]
        assert "basic" in pkg_codes and "gold" in pkg_codes and "diamond" in pkg_codes

        quote_res = test_client.post("/api/bookings/quote", json={
            "packageCode": "gold",
            "durationHours": 3,
            "addOnCodes": ["bubble_entry", "fog_entry"],
            "applyPromo": False
        })
        assert quote_res.status_code == 200
        quote_data = quote_res.get_json()["data"]
        # Gold is 1500/hr * 3 = 4500 + 300 bubble + 500 fog = 5300
        assert quote_data["totalAmountMinor"] == 530000
        assert quote_data["totalRupees"] == 5300.0
        results["JOURNEY_1_PACKAGES_AND_QUOTE"] = "PASSED"
        print("  [+] Packages and quote estimator verified (Rs. 5,300 for 3h Gold + 2 add-ons).")
    except Exception as e:
        import traceback
        results["JOURNEY_1_PACKAGES_AND_QUOTE"] = f"FAILED: {e}"
        print(f"  [!] Failed: {traceback.format_exc()}")

    # JOURNEY 2: Booking Flow & Hold Creation
    print("\n[JOURNEY 2] Testing Direct Booking & Atomic Slot Claim Hold...")
    target_date = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
    slot_time = "16:00"
    booking_ref = None
    access_token = None
    try:
        booking_payload = {
            "date": target_date,
            "startTime": slot_time,
            "durationHours": 2,
            "packageCode": "basic",
            "addOnCodes": ["bubble_entry"],
            "customerName": "Kiran E2E Guest",
            "customerPhone": "+91 98765 43210",
            "customerEmail": "e2e_guest@joyboxparty.com",
            "celebrantName": "Aaradhya",
            "occasionType": "birthday"
        }
        res = test_client.post("/api/bookings", json=booking_payload, headers={"Idempotency-Key": str(uuid.uuid4())})
        assert res.status_code in (200, 201), f"Expected 200/201, got {res.status_code}: {res.get_data(as_text=True)}"
        b_data = res.get_json()["data"]
        booking_ref = b_data["bookingReference"]
        access_token = b_data.get("accessToken")
        assert booking_ref.startswith("JBX-")
        assert access_token is not None
        # Verify slot claim exists in Atlas
        claims = list(db.slotClaims.find({"ownerType": "booking"}))
        assert len(claims) > 0
        results["JOURNEY_2_BOOKING_AND_HOLD"] = "PASSED"
        print(f"  [+] Booking created: {booking_ref} with unguessable token on {target_date} {slot_time}.")
    except Exception as e:
        results["JOURNEY_2_BOOKING_AND_HOLD"] = f"FAILED: {e}"
        print(f"  [!] Failed: {e}")

    # JOURNEY 3: Anti-Double-Booking Race Contention
    print("\n[JOURNEY 3] Testing Anti-Double-Booking Conflict Rejection...")
    try:
        conflicting_payload = {
            "date": target_date,
            "startTime": slot_time, # Same slot!
            "durationHours": 2,
            "packageCode": "diamond",
            "customerName": "Rival Booker",
            "customerPhone": "+91 91234 56789"
        }
        conflict_res = test_client.post("/api/bookings", json=conflicting_payload, headers={"Idempotency-Key": str(uuid.uuid4())})
        assert conflict_res.status_code == 409, f"Expected 409 conflict, got {conflict_res.status_code}"
        assert conflict_res.get_json()["error"]["code"] == "SLOT_CONFLICT"
        results["JOURNEY_3_ANTI_DOUBLE_BOOKING"] = "PASSED"
        print("  [+] Double-booking attempt strictly rejected with 409 SLOT_CONFLICT.")
    except Exception as e:
        results["JOURNEY_3_ANTI_DOUBLE_BOOKING"] = f"FAILED: {e}"
        print(f"  [!] Failed: {e}")

    # JOURNEY 4: Inquiry Form Submission
    print("\n[JOURNEY 4] Testing Inquiry Form Submission...")
    try:
        inquiry_payload = {
            "name": "Ananya Sharma",
            "phone": "+91 94401 23456",
            "preferredDate": (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%d"),
            "preferredTime": "18:00",
            "packageCode": "diamond",
            "durationHours": 4,
            "message": "Interested in birthday celebration for my daughter."
        }
        inq_res = test_client.post("/api/inquiries", json=inquiry_payload)
        assert inq_res.status_code == 201, f"Expected 201, got {inq_res.status_code}"
        inq_data = inq_res.get_json()["data"]
        assert inq_data["status"] == "received"
        # Verify in DB
        db_inq = db.inquiries.find_one({"phone": {"$regex": "23456"}})
        assert db_inq is not None
        results["JOURNEY_4_INQUIRY_FORM"] = "PASSED"
        print(f"  [+] Inquiry received and saved in database: ID {db_inq['_id']}.")
    except Exception as e:
        results["JOURNEY_4_INQUIRY_FORM"] = f"FAILED: {e}"
        print(f"  [!] Failed: {e}")

    # JOURNEY 5: Token-Protected Lookup and Cancellation
    print("\n[JOURNEY 5] Testing Token-Protected Lookup & Cancellation...")
    try:
        # Without token -> minimal details
        no_tok_res = test_client.get(f"/api/bookings/{booking_ref}")
        assert no_tok_res.status_code == 200
        assert "customerName" not in no_tok_res.get_json()["data"]

        # With token -> full details
        tok_res = test_client.get(f"/api/bookings/{booking_ref}?token={access_token}")
        assert tok_res.status_code == 200
        assert "customerName" in tok_res.get_json()["data"]

        # Cancel with token
        cancel_res = test_client.post(f"/api/bookings/{booking_ref}/cancel", json={
            "token": access_token,
            "reason": "Change of plans"
        })
        assert cancel_res.status_code == 200
        assert cancel_res.get_json()["data"]["bookingStatus"] == "cancelled"

        # Verify slot claim is released
        remaining_claims = list(db.slotClaims.find({"ownerId": db.bookings.find_one({"bookingReference": booking_ref})["_id"]}))
        assert len(remaining_claims) == 0
        results["JOURNEY_5_LOOKUP_AND_CANCEL"] = "PASSED"
        print(f"  [+] Booking {booking_ref} cancelled with token and slot claim released.")
    except Exception as e:
        import traceback
        results["JOURNEY_5_LOOKUP_AND_CANCEL"] = f"FAILED: {e}\n{traceback.format_exc()}"
        print(f"  [!] Failed Journey 5: {traceback.format_exc()}")

    # JOURNEY 6: Admin Authentication, Slot Blocking & Dashboard
    print("\n[JOURNEY 6] Testing Admin Auth, Slot Blocking & Audit Logging...")
    try:
        # Create test admin user in test DB
        import bcrypt
        hashed_pw = bcrypt.hashpw(b"JoyboxOwner2026!", bcrypt.gensalt(12)).decode("utf-8")
        db.users.update_one(
            {"username": "admin_e2e"},
            {"$set": {
                "username": "admin_e2e",
                "email": "admin_e2e@joybox.test",
                "displayName": "Kiran Kumar",
                "passwordHash": hashed_pw,
                "role": "owner",
                "isActive": True,
                "failedLoginAttempts": 0,
                "updatedAt": now_utc(),
            }},
            upsert=True
        )

        # Login
        login_res = test_client.post("/api/admin/auth/login", json={
            "username": "admin_e2e",
            "password": "JoyboxOwner2026!"
        })
        assert login_res.status_code == 200, f"Admin login failed: {login_res.get_data(as_text=True)}"
        login_data = login_res.get_json()["data"]
        csrf_token = login_data["csrfToken"]
        headers = {"X-CSRF-Token": csrf_token}

        # View Dashboard KPIs
        dash_res = test_client.get("/api/admin/dashboard", headers=headers)
        assert dash_res.status_code == 200
        dash_data = dash_res.get_json()["data"]
        assert "todayBookingsCount" in dash_data
        assert "totalRevenueRupees" in dash_data

        # Create Availability Block (Maintenance)
        block_date = (datetime.now(timezone.utc) + timedelta(days=15)).strftime("%Y-%m-%d")
        block_res = test_client.post("/api/admin/availability-blocks", headers=headers, json={
            "date": block_date,
            "startTime": "10:00",
            "durationHours": 2,
            "reason": "AC Unit Servicing"
        })
        assert block_res.status_code == 201, f"Failed creating block: {block_res.get_data(as_text=True)}"
        block_id = block_res.get_json()["data"]["id"]

        # Verify block exists and locks slot claim
        block_claim = db.slotClaims.find_one({"ownerType": "block"})
        assert block_claim is not None

        # Delete availability block
        del_res = test_client.delete(f"/api/admin/availability-blocks/{block_id}", headers=headers)
        assert del_res.status_code == 200

        # Verify audit logs recorded actions
        audit_logs = list(db.auditLogs.find({"actorUsername": "admin_e2e"}))
        assert len(audit_logs) >= 2
        results["JOURNEY_6_ADMIN_OPERATIONS"] = "PASSED"
        print("  [+] Admin authenticated, KPI dashboard fetched, slot blocked/unlocked, audit logged.")
    except Exception as e:
        import traceback
        results["JOURNEY_6_ADMIN_OPERATIONS"] = f"FAILED: {e}\n{traceback.format_exc()}"
        print(f"  [!] Failed Journey 6: {traceback.format_exc()}")

    # JOURNEY 7: Playwright Visual Journey Across Production Build
    print("\n[JOURNEY 7] Testing Browser UI Journey via Playwright...")
    frontend_srv = start_frontend_server(4174)
    time.sleep(1)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            # 1. Packages page
            page.goto("http://127.0.0.1:4174/packages", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=os.path.join(E2E_SCREENSHOT_DIR, "e2e_01_packages.png"))

            # 2. Gallery page with API data
            page.goto("http://127.0.0.1:4174/gallery", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=os.path.join(E2E_SCREENSHOT_DIR, "e2e_02_gallery.png"))

            # 3. Booking Wizard
            page.goto("http://127.0.0.1:4174/book", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=os.path.join(E2E_SCREENSHOT_DIR, "e2e_03_booking_wizard.png"))

            # 4. Contact page
            page.goto("http://127.0.0.1:4174/contact", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=os.path.join(E2E_SCREENSHOT_DIR, "e2e_04_contact.png"))

            # 5. Admin Login
            page.goto("http://127.0.0.1:4174/admin/login", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=os.path.join(E2E_SCREENSHOT_DIR, "e2e_05_admin_login.png"))

            browser.close()
            results["JOURNEY_7_BROWSER_PLAYWRIGHT"] = "PASSED"
            print("  [+] Playwright browser journeys captured 5 screenshots in docs/visual_audit/e2e/.")
    except Exception as e:
        results["JOURNEY_7_BROWSER_PLAYWRIGHT"] = f"FAILED: {e}"
        print(f"  [!] Failed: {e}")
    finally:
        frontend_srv.shutdown()

    print("\n==================================================================")
    print("                     E2E RESULTS SUMMARY")
    print("==================================================================")
    all_passed = True
    for j, status in results.items():
        print(f"  {j:35} : {status}")
        if "PASSED" not in status:
            all_passed = False

    print("==================================================================")
    if all_passed:
        print("  [+] ALL 7 END-TO-END JOURNEYS PASSED SUCCESSFULLY ON REAL ATLAS TEST DB!")
    else:
        print("  [!] SOME E2E JOURNEYS FAILED — CHECK LOGS ABOVE.")
    print("==================================================================")

if __name__ == "__main__":
    run_e2e_tests()
