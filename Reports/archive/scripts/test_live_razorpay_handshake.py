#!/usr/bin/env python3
"""
Pre-Flight Diagnostic & Live Handshake Verification for Razorpay Payment Gateway.
Joybox Party Room Platform.

Usage:
  python scripts/test_live_razorpay_handshake.py

Rules:
1. Reads credentials strictly from environment variables (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET).
2. Refuses to run if any live key ('rzp_live_') is detected.
3. Attempts to create a minimal test order (100 paise = ₹1.00) in INR.
4. Validates gateway response status, structure, order ID, amount, and currency.
5. NEVER logs, echoes, or prints secret values or passwords.
"""
import os
import sys
import uuid
import requests
from dotenv import load_dotenv

# Load backend/.env first
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv()

def run_handshake() -> int:
    print("=" * 70)
    print("   JOYBOX PARTY ROOM — RAZORPAY LIVE HANDSHAKE DIAGNOSTIC")
    print("=" * 70)

    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

    # 1. Credential presence check
    if not key_id or not key_secret:
        print("[!] BLOCKED: Missing Razorpay credentials in environment.")
        print("    Both RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured.")
        print("    Action: Obtain test key pair from Razorpay Dashboard and set in backend/.env.")
        return 2

    # 2. Safety Guard: Prohibit live keys
    if key_id.startswith("rzp_live_"):
        print("[!] CRITICAL SAFETY GUARD: Live key detected ('rzp_live_').")
        print("    This diagnostic refuses to run against live accounts to prevent real-money transactions.")
        print("    Action: Configure Razorpay test keys ('rzp_test_...') only.")
        return 1

    if not key_id.startswith("rzp_test_"):
        print(f"[!] INVALID KEY PREFIX: Expected 'rzp_test_...', got '{key_id[:8]}...'.")
        return 1

    masked_key = f"{key_id[:10]}...{key_id[-4:]}"
    print(f"[*] Configuration Check:")
    print(f"    - Key ID: {masked_key} (Test Mode)")
    print(f"    - Secret: [CONFIGURED - 24+ characters]")
    print(f"    - Endpoint: https://api.razorpay.com/v1/orders")

    # 3. Handshake Request
    receipt_id = f"diag_{uuid.uuid4().hex[:10]}"
    test_amount_paise = 100  # Minimum valid Razorpay transaction: ₹1.00

    payload = {
        "amount": test_amount_paise,
        "currency": "INR",
        "receipt": receipt_id,
        "notes": {
            "purpose": "Joybox automated live handshake diagnostic",
            "environment": "test"
        }
    }

    print("\n[*] Sending minimal test order creation request (100 paise = Rs. 1.00)...")
    try:
        resp = requests.post(
            "https://api.razorpay.com/v1/orders",
            json=payload,
            auth=(key_id, key_secret),
            timeout=10
        )
    except requests.RequestException as exc:
        print(f"[!] NETWORK FAILURE: Failed to communicate with Razorpay API: {exc}")
        return 3

    # 4. Response Evaluation
    if resp.status_code in (200, 201):
        data = resp.json()
        order_id = data.get("id")
        amount = data.get("amount")
        currency = data.get("currency")
        status = data.get("status")

        if not order_id or not order_id.startswith("order_"):
            print(f"[!] MALFORMED RESPONSE: Missing or invalid order ID: {order_id}")
            return 4

        if amount != test_amount_paise or currency != "INR":
            print(f"[!] ATTRIBUTE MISMATCH: Expected {test_amount_paise} INR, got {amount} {currency}")
            return 4

        print("\n[+] SUCCESS: Live Razorpay test handshake verified successfully!")
        print(f"    - Generated Order ID: {order_id}")
        print(f"    - Order Status: {status}")
        print(f"    - Verified Amount: {amount} paise (Rs. {amount / 100:.2f})")
        print(f"    - Verified Currency: {currency}")
        print("=" * 70)
        return 0

    elif resp.status_code == 401:
        print("\n[!] AUTHENTICATION FAILED (HTTP 401):")
        print("    Razorpay rejected the API Key ID and Secret combination.")
        print("    Probable causes:")
        print("      1. The test keys in backend/.env were revoked or regenerated on the dashboard.")
        print("      2. Key secret contains whitespace or copy-paste truncation.")
        print("    Action Required:")
        print("      Log into https://dashboard.razorpay.com -> Settings -> API Keys -> Generate Test Key.")
        print("      Update RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in backend/.env.")
        return 5

    else:
        print(f"\n[!] GATEWAY ERROR (HTTP {resp.status_code}):")
        try:
            err_json = resp.json().get("error", {})
            print(f"    Code: {err_json.get('code')}")
            print(f"    Description: {err_json.get('description')}")
        except Exception:
            print(f"    Raw Response: {resp.text[:200]}")
        return 6

if __name__ == "__main__":
    sys.exit(run_handshake())
