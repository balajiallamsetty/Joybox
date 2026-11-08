# Production Release & Database Verification Checklist

**Application:** Joybox Party Room Platform  
**Target Release:** Production Deployment  
**Auditor:** Principal Full-Stack Engineer & Release Owner  
**Last Verified:** 2026-10-30  

---

## 1. Overview & Operational Principles

To ensure zero downtime, index consistency, and complete catalog availability prior to routing live traffic, every release must follow this strict, ordered checklist.

> [!IMPORTANT]
> Never run initializations or destructive actions against the production database `joybox_party_room` directly without first executing against an isolated `_test` clone and verifying the results with `verify_release_state.py`.

---

## 2. Release Execution Order

### Step 1: Pre-Release Non-Production Validation
Execute the initialization and seed pipeline against the test cluster (`joybox_party_room_test`) to verify index creation and catalog synchronization:
```powershell
# 1. Initialize authoritative indexes and validators
python backend/scripts/init_indexes.py --db joybox_party_room_test

# 2. Synchronize master catalog data (packages, add-ons, room, offers, gallery, faqs)
python backend/scripts/seed_all.py --db joybox_party_room_test

# 3. Create or verify initial owner account
python backend/scripts/create_admin.py --db joybox_party_room_test --username kiran --email host@joyboxparty.in --display-name "Kiran Kumar" --role owner --password "<ADMIN_PASSWORD>"

# 4. Verify release state (read-only verification gate)
python backend/scripts/verify_release_state.py --db joybox_party_room_test
```
*Expected Result:* `[+] ALL VERIFICATION CHECKS PASSED: Environment ready for release.`

---

### Step 2: Automated Test Gate
Run the full test suite from the repository root:
```powershell
python -m pytest backend/tests -v
```
*Requirement:* **0 failures** across all unit, integration, and Atlas concurrency tests.

---

### Step 3: Production Initialization (Guarded Execution)
Once non-production verification passes, execute against production with explicit safety override flags:
```powershell
# 1. Dry-run audit of production indexes
python backend/scripts/init_indexes.py --db joybox_party_room --allow-production --confirm-production joybox_party_room --dry-run

# 2. Live production index and schema validator initialization
python backend/scripts/init_indexes.py --db joybox_party_room --allow-production --confirm-production joybox_party_room

# 3. Live production catalog synchronization (idempotent upserts)
python backend/scripts/seed_all.py --db joybox_party_room --allow-production --confirm-production joybox_party_room

# 4. Read-only verification of production release state
python backend/scripts/verify_release_state.py --db joybox_party_room --allow-production --confirm-production joybox_party_room
```

---

## 3. Post-Release Verification & Smoke Check

1. **Health Probes:**
   - Verify `GET /api/health` returns `{"status": "ok", "database": "connected"}`.
   - Verify `GET /api/ready` returns `{"status": "ready"}`.
2. **Catalog Integrity:**
   - Verify `GET /api/packages` returns 3 active tiers (`basic`, `gold`, `diamond`).
   - Verify `GET /api/add-ons` returns 3 active party boosters.
3. **Availability Engine:**
   - Query `GET /api/availability?date=<TOMORROW>&durationHours=2` and verify hourly slots are computed with active cleaning buffers.
4. **Admin Console:**
   - Log into `/admin` with owner credentials; verify dashboard loads booking metrics and audit log stream without errors.

