# DATABASE SETUP GUIDE — Joybox Party Room
**MongoDB Atlas Setup, Security & Operations Reference**

---

## 1. MongoDB Atlas Cluster Configuration

1. **Create Free Tier / Dedicated Cluster:**
   - Provider: AWS (recommended region: `ap-south-1` Mumbai for minimal latency to Andhra Pradesh / Guntur)
   - Cluster Tier: M0 (Sandbox / Free) for development, or M10+ for production with automated backups and replica sets.
   - Database Name: `joybox_party_room`

2. **Network Access (IP Whitelist):**
   - Development: Add your current public IP address (or `0.0.0.0/0` temporarily with strong credentials).
   - Render Deployment: In production on Render, Render uses dynamic outbound IPs. Either allow `0.0.0.0/0` with high-entropy database password, or use Atlas VPC Peering / Render Private Services.

3. **Database User (Principle of Least Privilege):**
   - Username: `joybox_app_user`
   - Role: `readWrite` scoped strictly to `joybox_party_room` database only (do not give `atlasAdmin`).

---

## 2. Environment Variables Configuration

Copy `backend/.env.example` to `backend/.env`:
```powershell
Copy-Item backend\.env.example backend\.env
```

Configure the connection string in `backend/.env`:
```ini
FLASK_ENV=development
PORT=5000
FRONTEND_ORIGIN=http://localhost:5173
MONGODB_URI=mongodb+srv://<DB_USER>:<PASSWORD>@<CLUSTER>.mongodb.net/joybox_party_room?retryWrites=true&w=majority
MONGODB_DB=joybox_party_room
JWT_SECRET_KEY=generate-a-strong-random-key-64-chars
```

---

## 3. Database Initialization Scripts

Execute each idempotent script using PowerShell from the `backend/` directory:

### Step 1: Initialize Production Indexes
```powershell
python scripts/init_indexes.py
```
*Creates all 21 collection indexes, including the unique anti-double-booking index on `(roomId, slotStart)`.*

### Step 2: Seed Packages
```powershell
python scripts/seed_packages.py
```
*Upserts Basic (₹999/hr), Gold (₹1,500/hr), and Diamond (₹2,500/hr).*

### Step 3: Seed Add-Ons
```powershell
python scripts/seed_addons.py
```
*Upserts Bubble Entry (+₹300), Fog Entry (+₹500), and Cold-Fire (+₹300).*

### Step 4: Seed Promotional Offers
```powershell
python scripts/seed_offers.py
```
*Upserts the monthly introductory offer (Basic package at ₹500/hr for first 5 bookings).*

### Step 5: Create Super Admin Account
```powershell
python scripts/create_admin.py
```
*Interactive script to securely hash and register the initial admin (`Kiran Kumar`).*

---

## 4. Disaster Recovery & Backup Strategy

- **Atlas Point-In-Time Restore (PITR):** Available on M10+ clusters for 1-minute granularity recovery.
- **Automated Nightly Snapshot:** Configure 30-day retention on Atlas.
- **Local JSON Dump (Weekly):**
  ```powershell
  mongodump --uri="<MONGODB_URI>" --out="C:\backup\joybox_$(Get-Date -Format 'yyyyMMdd')"
  ```

