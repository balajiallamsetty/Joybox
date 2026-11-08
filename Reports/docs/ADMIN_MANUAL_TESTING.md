# ADMIN SYSTEM & OPERATIONS MANUAL TESTING GUIDE
**Joybox Party Room · Phase 7 Administrator Operations**

This guide provides end-to-end instructions for manually verifying and testing the administrator authentication, role-based authorization (RBAC), anti-double-booking emergency blocks, payment audit tools, and operations console.

---

## 1. Seeded Credentials

The database contains the following seeded accounts (created with `bcrypt`, work factor 12):

| Role | Username | Password | Permitted Operations |
|---|---|---|---|
| **Owner (Super Admin)** | `kiran` | `Admin123!` (or seeded value) | All endpoints: booking management, pricing changes, refunds, audit logs, user management |
| **Owner (Test)** | `test_owner` | `OwnerPassword123!` | Full test suite permissions |
| **Manager (Test)** | `test_manager` | `ManagerPassword123!` | Bookings, inquiries, packages PATCH, audit logs, blocks |
| **Staff (Test)** | `test_staff` | `StaffPassword123!` | Bookings view/update, inquiries view/update, blocks view (read-only for audit/packages) |

To re-seed or create a new admin user:
```bash
python backend/scripts/create_admin.py --username kiran --role owner --display-name "Kiran Kumar"
```

---

## 2. Testing via Browser UI

### Step 2.1: Login Flow
1. Start the backend:
   ```bash
   python backend/run.py
   ```
2. Start the frontend:
   ```bash
   npm --prefix frontend run dev
   ```
3. Open `http://localhost:5173/admin` in your browser.
4. Verify that you are automatically redirected to `http://localhost:5173/admin/login` because no active session exists.
5. In the login form:
   - Try an invalid password: enter `kiran` and `WrongPassword!`. Verify that a red alert banner appears: *"Invalid username or password."*
   - Try entering valid credentials: `kiran` / password. Click **Sign In**.
6. Verify successful login:
   - You are redirected to `/admin`.
   - The top header shows `Kiran Kumar (owner)` and venue badge `Vadlamudi Venue (Beside Durga Mart)`.
   - The MongoDB status badge in the bottom-left sidebar displays `MongoDB Atlas ReplicaSet: Connected`.

### Step 2.2: Dashboard & KPIs
1. On the **Dashboard & KPIs** tab (`#dashboard`):
   - Inspect the KPI cards: Today's Bookings, Monthly Revenue, Monthly Quota Cycle (X of 5 slots), Pending Inquiries.
   - If any payment has `needsReview: true`, verify the urgent warning banner appears at the top.
   - Inspect the **Recent Reservations** table.

### Step 2.3: Manual / Offline Booking
1. Switch to the **Schedule & Bookings** tab.
2. Click **New Manual Booking**:
   - Enter Customer Name: `Suresh Babu`
   - Customer Phone: `9876543210`
   - Package: `Gold`
   - Select a future date and time window (e.g. tomorrow 10:00 AM to 12:00 PM).
   - Enter Advance Paid: `500` (₹500). Method: `Cash`.
   - Click **Create Booking**.
3. Verify that the booking appears in the table with status `confirmed`, advance ₹500, and an immutable slot claim is recorded.

### Step 2.4: Emergency Hall Blocks
1. Switch to **Hall Blocks & Slots** tab (`#blocks`).
2. In the "Create New Hall Block" form:
   - Reason: `Deep Sanitation & Light Maintenance`
   - Start Time: Select a 2-hour window.
   - End Time: 2 hours later.
   - Click **Block Slots**.
3. Verify that the new block appears under **Active Hall Blocks**.
4. Try to book that same slot via the public booking wizard at `/book`. Verify that the slot is shown as unavailable.
5. In the admin console, click **Release Block**. Verify that the block is deleted and slots are freed.

### Step 2.5: Payments & Refunds
1. Switch to the **Payments & Refunds** tab.
2. Filter by `Needs Review Only` to see flagged transactions.
3. For any transaction flagged with failed refund, click **Retry Refund**.

### Step 2.6: Audit Logs
1. Switch to the **Audit Logs** tab (`#audit`).
2. Verify that all your actions (logins, manual bookings, block creations, password updates) appear in chronological order with exact IST timestamps, username, action name, and IP address.

### Step 2.7: Logout
1. Click **Sign Out** in the top header.
2. Verify the session cookie is destroyed and you are redirected to `/admin/login`.
3. Try pressing the browser Back button; verify that access is blocked and you remain on `/admin/login`.

---

## 3. Testing via cURL / HTTP Requests

### 3.1: Authenticate and Extract Session Cookie & CSRF Token
```bash
# Login request
curl -c cookies.txt -b cookies.txt -X POST http://127.0.0.1:5000/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "kiran", "password": "AdminPassword123!"}'
```
Response:
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "...",
      "username": "kiran",
      "displayName": "Kiran Kumar",
      "role": "owner"
    },
    "csrfToken": "4fa83d9b1c7e..."
  }
}
```
*Note the returned `csrfToken` for subsequent mutating POST/PATCH/DELETE calls.*

### 3.2: Verify Session Identity (`/auth/me`)
```bash
curl -b cookies.txt -X GET http://127.0.0.1:5000/api/admin/auth/me
```

### 3.3: Fetch Dashboard KPIs
```bash
curl -b cookies.txt -X GET http://127.0.0.1:5000/api/admin/dashboard
```

### 3.4: CSRF Protection Test (Omitted Token)
Try a mutating call without `X-CSRF-Token`:
```bash
curl -b cookies.txt -X POST http://127.0.0.1:5000/api/admin/availability-blocks \
  -H "Content-Type: application/json" \
  -d '{"roomId": "main", "reason": "Test Block", "slotStart": "2026-11-10T04:30:00Z", "slotEnd": "2026-11-10T06:30:00Z"}'
```
**Expected Response:** `403 Forbidden` (`CSRF_TOKEN_MISSING`).

### 3.5: CSRF Protection Test (Valid Token)
```bash
curl -b cookies.txt -X POST http://127.0.0.1:5000/api/admin/availability-blocks \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: <CSRF_TOKEN_FROM_LOGIN>" \
  -d '{"roomId": "main", "reason": "Test Block", "slotStart": "2026-11-10T04:30:00Z", "slotEnd": "2026-11-10T06:30:00Z"}'
```
**Expected Response:** `201 Created` (`SLOTS_LOCKED`).

### 3.6: Account Lockout Test (Brute Force Protection)
Execute 5 consecutive invalid login attempts:
```bash
for i in {1..5}; do
  curl -s -X POST http://127.0.0.1:5000/api/admin/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "test_owner", "password": "WrongPassword!"}'
done
```
The 5th attempt triggers lockout. Attempting a 6th login with the *correct* password returns:
```json
{
  "success": false,
  "error": {
    "code": "ACCOUNT_LOCKED",
    "message": "Account temporarily locked due to repeated failed login attempts. Try again after 15 minutes."
  }
}
```

### 3.7: Logout
```bash
curl -b cookies.txt -X POST http://127.0.0.1:5000/api/admin/auth/logout \
  -H "X-CSRF-Token: <CSRF_TOKEN>"
```
Session is revoked in MongoDB `adminSessions` and cookie is cleared with `Max-Age=0`.

