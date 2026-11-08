# Joybox Party Room — Venue Owner Production Tasks

**Target Release:** Production Launch (Vadlamudi, Guntur)  
**Host Contact:** Kiran Kumar (+91 78427 04429)  

This checklist details every external dashboard configuration and credential management step required for the owner before taking public traffic live.

---

## 1. MongoDB Atlas Network Access & Security

Because Render web services and background cron jobs use dynamic outbound NAT IP addresses within AWS Oregon (`us-west-2`), you must configure network access:

### Step-by-Step Click Path:
1. Open [cloud.mongodb.com](https://cloud.mongodb.com/) and navigate to your Project.
2. In the left sidebar, click **Security** $\rightarrow$ **Network Access**.
3. Click the green **+ Add IP Address** button:
   - Select **Allow Access From Anywhere** (`0.0.0.0/0`) or enter Render's designated static outbound IP ranges.
   - Set Comment: `Render Web Service & Cron Job Dynamic NAT`.
   - Click **Confirm**.
4. Navigate to **Security** $\rightarrow$ **Database Access**:
   - Create a new database user for this deployment. Do not reuse a developer account.
   - Click **Edit** $\rightarrow$ **Edit Password** $\rightarrow$ **Autogenerate Secure Password**.
   - Copy the new 32-character password.
   - Update `MONGODB_URI` in the Render Environment Dashboard.

### 1.1 Dedicated Least-Privilege Test Database User (Defense-in-Depth)

To ensure that automated integration tests and developers cannot touch the production database even if code guards are somehow bypassed:
1. Open [cloud.mongodb.com](https://cloud.mongodb.com/) $\rightarrow$ **Security** $\rightarrow$ **Database Access**.
2. Click **Add New Database User**:
   - **Authentication Method**: Password
   - **Username**: `joybox_test_user`
   - **Password**: Autogenerate 32-character secure password
   - **Database User Privileges**: Click **Built-in Roles** $\rightarrow$ Change from "Atlas admin" to **Specific Privileges**:
     - Role: `readWrite`
     - Database: `joybox_party_room_test`
   - **Restrictions**: Do NOT grant any privileges on `joybox_party_room` or the `admin` database.
3. Use this restricted user for `MONGODB_TEST_URI`:
   `mongodb+srv://joybox_test_user:<test-password>@cluster0.xxxxx.mongodb.net/joybox_party_room_test?retryWrites=true&w=majority`
   If this user attempts to access `joybox_party_room`, MongoDB Atlas itself rejects the command at the database layer with `not authorized on joybox_party_room to execute command`.

---

## 2. Render Web Service & Cron Deployment

### 2.1 Backend Web Service
1. In the [Render Dashboard](https://dashboard.render.com/):
   - Verify Service `joybox-backend` is deployed on the **Starter** plan (to prevent cold-start latency and webhook timeouts).
   - Verify **Environment Variables**:
     - `FLASK_ENV`: `production`
     - `MONGODB_URI`: `mongodb+srv://<username>:<new-password>@cluster0.xxxxx.mongodb.net/joybox_party_room?retryWrites=true&w=majority`
     - `MONGODB_DB`: `joybox_party_room`
     - `JWT_SECRET_KEY`: High-entropy 64-character random string (e.g. generated via `python -c "import secrets; print(secrets.token_hex(32))"`)
     - `FRONTEND_ORIGIN`: `https://joyboxvadlamudi.com` (or your verified Vercel production domain)
     - `ADMIN_COOKIE_SECURE`: `true`
     - `ADMIN_COOKIE_SAMESITE`: `Lax`
     - `TRUSTED_PROXY_COUNT`: `1`
     - `MAX_ADVANCE_BOOKING_DAYS`: `90`

### 2.2 Background Cron Job (Every 10 Minutes)
1. In Render Dashboard, ensure the cron service `joybox-maintenance-sweeps` is active:
   - **Schedule**: `*/10 * * * *`
   - **Command**: `python -m app.jobs.run_sweeps`
   - **Environment**: Identical `MONGODB_URI`, `MONGODB_DB`, `PYTHONPATH="backend:."`

---

## 3. Razorpay Live Payments & Webhook Setup

When switching from test mode (`rzp_test_...`) to live customer payments:

### Step-by-Step Click Path:
1. Open the [Razorpay Dashboard](https://dashboard.razorpay.com/) and switch the toggle from **Test Mode** to **Live Mode**.
2. Navigate to **Account & Settings** $\rightarrow$ **API Keys**:
   - Click **Generate Live Key**.
   - Safely store `Key Id` (`rzp_live_...`) and `Key Secret`.
3. Configure Backend Environment in Render:
   - `RAZORPAY_KEY_ID`: `rzp_live_...`
   - `RAZORPAY_KEY_SECRET`: Live Secret
4. Configure Frontend Environment in Vercel:
   - `VITE_RAZORPAY_KEY_ID`: `rzp_live_...`
5. Configure Webhook in Razorpay Dashboard:
   - Navigate to **Account & Settings** $\rightarrow$ **Webhooks** $\rightarrow$ **Add New Webhook**.
   - **Webhook URL**: `https://<your-render-backend-domain>/api/payments/webhook`
   - **Secret**: Enter a secure random string and set `RAZORPAY_WEBHOOK_SECRET` in Render.
   - **Active Events**:
     - `payment.captured`
     - `payment.failed`
     - `order.paid`
     - `refund.processed`

---

## 4. Vercel Frontend Custom Domain & HTTPS

1. In [Vercel Dashboard](https://vercel.com/):
   - Navigate to your project $\rightarrow$ **Settings** $\rightarrow$ **Domains**.
   - Add your custom domain (e.g. `joyboxvadlamudi.com`).
   - Configure DNS records at your registrar (GoDaddy, Namecheap, Google Domains):
     - `A` Record: `@` $\rightarrow$ `76.76.21.21`
     - `CNAME` Record: `www` $\rightarrow$ `cname.vercel-dns.com`
   - Wait for Vercel's automated SSL certificate issuance (HTTPS is strictly enforced by the build assertion).
2. Set Environment Variable in Vercel:
   - `VITE_API_BASE_URL`: `https://<your-render-backend-domain>/api`
   - `VITE_WHATSAPP_NUMBER`: `917842704429`

---

## 5. First-Time Production Database Initialization Drill

Before taking public bookings, execute the zero-risk production initialization drill:
```powershell
# 1. Apply indexes and schema validation rules
python backend/scripts/init_indexes.py --db joybox_party_room --allow-production --confirm-production joybox_party_room

# 2. Seed catalog, add-ons, and promo offer
python backend/scripts/seed_all.py --db joybox_party_room --allow-production --confirm-production joybox_party_room

# 3. Create initial Owner administrator account
python backend/scripts/create_admin.py --db joybox_party_room --username kiran --email host@joyboxparty.in --display-name "Kiran Kumar" --role owner --allow-production --confirm-production joybox_party_room

# 4. Read-only verification of release state
python backend/scripts/verify_release_state.py --db joybox_party_room --allow-production
```
All scripts will output `[OK] VERIFICATION PASSED`.

---

## 6. Git History Compromised Secret Rotation Runbook (CRITICAL OWNER ACTION)

A git log analysis (`git log -p`) identified 51 historical instances across 40 unique commits where database credentials or test payment secrets were committed before the secrets were redacted. To ensure complete security, the owner MUST complete the following sequential rotation runbook:

### 6.1 Ordered Rotation Steps & Death Verification

#### Step 1: MongoDB Atlas Production Database User Password
1. **Rotate:** Open [cloud.mongodb.com](https://cloud.mongodb.com/) $\rightarrow$ **Security** $\rightarrow$ **Database Access**.
   - Edit the database user created for this deployment.
   - Select **Edit Password** $\rightarrow$ **Autogenerate Secure Password** (32 characters).
2. **Update:**
   - In Render Dashboard $\rightarrow$ Web Service `joybox-backend` $\rightarrow$ Environment: Update `MONGODB_URI` with the new password.
   - In Render Dashboard $\rightarrow$ Cron Job `joybox-maintenance-sweeps` $\rightarrow$ Environment: Update `MONGODB_URI`.
   - In local `backend/.env` (for local authorized administration).
3. **Verify Old Secret is Dead:**
   Run the following Python test command with the *old* password:
   ```bash
   python -c "from pymongo import MongoClient; client=MongoClient('mongodb+srv://<username>:<old-password>@<cluster>.mongodb.net/joybox_party_room', serverSelectionTimeoutMS=3000); client.admin.command('ping')"
   ```
   *Expected Result:* Must fail immediately with `pymongo.errors.OperationFailure: Authentication failed`.

#### Step 2: Razorpay Test Key & Secret
1. **Rotate:** Open [dashboard.razorpay.com](https://dashboard.razorpay.com/) $\rightarrow$ **Account & Settings** $\rightarrow$ **API Keys**.
   - Click **Regenerate Key**.
   - Copy new `Key Id` (`rzp_test_...`) and `Key Secret`.
2. **Update:**
   - In Render Dashboard: Update `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.
   - In Vercel Dashboard: Update `VITE_RAZORPAY_KEY_ID`.
   - In local `backend/.env` and `frontend/.env.local`.
3. **Verify Old Secret is Dead:**
   Run an API call with the old key and secret:
   ```bash
   curl -s -u <OLD_KEY_ID>:<OLD_SECRET> https://api.razorpay.com/v1/orders
   ```
   *Expected Result:* Must return `HTTP 401 Unauthorized` (`BAD_REQUEST_ERROR: Authentication failed`).

#### Step 3: Admin JWT Secret Key
1. **Rotate:** Generate a high-entropy 64-character hex secret:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
2. **Update:**
   - In Render Dashboard: Update `JWT_SECRET_KEY`.
   - In local `backend/.env`.
3. **Verify Old Secret is Dead:**
   Send a request to `/api/admin/bookings` with an existing old JWT cookie or token.
   *Expected Result:* Must return `HTTP 401 Unauthorized` (`Signature verification failed`).

#### Step 4: Razorpay Webhook Secret
1. **Rotate:** In Razorpay Dashboard $\rightarrow$ **Account & Settings** $\rightarrow$ **Webhooks** $\rightarrow$ Edit webhook.
   - Regenerate the webhook secret with a high-entropy string.
2. **Update:**
   - In Render Dashboard: Update `RAZORPAY_WEBHOOK_SECRET`.
3. **Verify Old Secret is Dead:**
   Send a test webhook payload signed with the old secret.
   *Expected Result:* Must fail with `HTTP 400 Bad Request` (`Invalid signature`).

---

### 6.2 Prepared Git History Purge Runbook (git filter-repo)

> [!WARNING]
> Purging git history rewrites all commit SHAs. Do NOT execute these commands until all team members are coordinated and open pull requests are merged.
> This runbook is prepared and validated, pending owner confirmation.

```bash
# 1. Install git-filter-repo
pip install git-filter-repo

# 2. Create expressions replacement file
cat << 'EOF' > /tmp/expressions.txt
regex:mongodb\+srv:\/\/[^:]+:[^@]+@==>mongodb+srv://<REDACTED_USER>:<REDACTED_PASSWORD>@
regex:rzp_test_[a-zA-Z0-9]{8,}==>rzp_test_<REDACTED_KEY_ID>
regex:H6aodE4uuW5h9KMdrSP6FjCg==><REDACTED_SECRET>
EOF

# 3. Purge secrets from local repository mirror
git filter-repo --replace-text /tmp/expressions.txt --force

# 4. Force push rewritten clean history to remote (OWNER CONFIRMATION REQUIRED)
# git push origin --force --all
# git push origin --force --tags

# 5. Collaborators must re-clone clean repository
# git clone <repo-url> joybox-clean
```




