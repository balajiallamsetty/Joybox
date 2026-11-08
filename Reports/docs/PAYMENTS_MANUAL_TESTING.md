# RAZORPAY MANUAL TESTING & WEBHOOK REPLAY GUIDE
**Joybox Party Room — Standard Web Checkout**
*Version 1.0 · Test Mode Verification Runbook*

---

## 1. Overview
This runbook guides manual testing of the Razorpay checkout and webhook flow on local developer workstations and staging environments.

---

## 2. Test-Mode Credentials Setup & Handshake Verification
1. Log in to [Razorpay Dashboard](https://dashboard.razorpay.com/) and toggle to **Test Mode**.
2. Navigate to **Account & Settings > API Keys > Generate Key**.
3. Copy `Key Id` (`rzp_test_...`) and `Key Secret`.
4. In `backend/.env`:
   ```env
   RAZORPAY_KEY_ID=rzp_test_YOUR_KEY_ID
   RAZORPAY_KEY_SECRET=YOUR_KEY_SECRET
   RAZORPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET
   ```
5. **Verify Handshake Before Testing:**
   Run the automated live handshake diagnostic:
   ```powershell
   python scripts/test_live_razorpay_handshake.py
   ```
   *If this returns HTTP 401 Unauthorized, regenerate keys on the dashboard before attempting checkout.*
6. In `frontend/.env` (optional fallback):
   ```env
   VITE_RAZORPAY_KEY_ID=rzp_test_YOUR_KEY_ID
   ```

---

## 3. End-to-End Test Checkout Flow
1. Start the Flask backend:
   ```powershell
   cd backend
   python run.py
   ```
2. Start the Vite frontend:
   ```powershell
   cd frontend
   npm run dev
   ```
3. Open `http://localhost:5173/book`.
4. Step 1: Select Date & Time slot.
5. Step 2: Select Package (Basic, Gold, or Diamond).
6. Step 3: Enter Customer & Celebrant details.
7. Step 4: Click **Pay & Lock Slot**.
8. Razorpay checkout modal opens. Select **UPI > Google Pay (Test)** or **Card (Success test card)**:
   - Card Number: `4111 1111 1111 1111`
   - Expiry: Any future date (e.g. `12/28`)
   - CVV: `123`
   - OTP: `123456`
9. Upon payment success, frontend automatically submits verification to `POST /api/payments/verify`.
10. Browser redirects to `/booking/JBX-YYYY-NNNN` displaying **CONFIRMED** status.

---

## 4. Exposing & Testing Local Webhooks with ngrok / Localtunnel
1. Expose local port 5000:
   ```bash
   ngrok http 5000
   # or
   npx localtunnel --port 5000
   ```
2. Copy the HTTPS forwarding URL (e.g. `https://abc1234.ngrok-free.app`).
3. In Razorpay Dashboard (**Settings > Webhooks > Add New Webhook**):
   - **Webhook URL:** `https://abc1234.ngrok-free.app/api/payments/webhook`
   - **Secret:** Must match `RAZORPAY_WEBHOOK_SECRET` in `backend/.env`.
   - **Events to Select:**
     - `order.paid`
     - `payment.authorized`
     - `payment.captured`
     - `payment.failed`
     - `refund.processed`
     - `refund.failed`

---

## 5. Webhook Replay Script (Manual CLI Verification)
To test webhook verification locally without waiting for gateway triggers, use this HMAC signature replay snippet:

```python
import hmac
import hashlib
import requests
import json

WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET"
ENDPOINT = "http://127.0.0.1:5000/api/payments/webhook"

payload = {
    "entity": "event",
    "account_id": "acc_test123",
    "event": "payment.captured",
    "contains": ["payment"],
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_test_001",
                "order_id": "order_test_001",
                "amount": 99900,
                "currency": "INR",
                "status": "captured",
                "notes": {
                    "bookingReference": "JBX-2026-0001"
                }
            }
        }
    }
}

raw_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
signature = hmac.new(WEBHOOK_SECRET.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Razorpay-Signature": signature
}

res = requests.post(ENDPOINT, data=raw_body, headers=headers)
print("Status:", res.status_code)
print("Response:", res.json())
```

