# Backup & Disaster Recovery Restore Drill Runbook

**Service:** Joybox Party Room Platform  
**Target Environment:** MongoDB Atlas  
**Audit & Drill Date:** 2026-10-30  
**Status:** **PASSED & VERIFIED** (`All counts match: True`)

---

## 1. Overview & Objective

This runbook outlines the operational procedure for backing up the transactional and catalog data of Joybox Party Room, verifying backup integrity, and executing a non-destructive restore drill into a verified test database (`*_test`).

### Target Safety Invariant
- Under **no circumstances** may a restore drill or test script write to, overwrite, or drop collections in the production database `joybox_party_room`.
- The restore utility enforces `assert_is_test_database()` and strictly rejects target database names that do not end with `_test`.

---

## 2. Automated Drill Execution & Verified Evidence

### 2.1 Backup Export Step
Command executed:
```powershell
python backend/scripts/db_backup.py --backup --db joybox_party_room_test
```
**Output:**
```
[*] Starting JSON backup of database 'joybox_party_room_test' (dry_run=False)...
  [+] Exported 3 documents from 'packages'
  [+] Exported 3 documents from 'addOns'
  [+] Exported 0 documents from 'rooms'
  [+] Exported 1 documents from 'offers'
  [+] Exported 9 documents from 'galleryAssets'
  [+] Exported 5 documents from 'faqs'
  [+] Exported 0 documents from 'bookings'
  [+] Exported 0 documents from 'bookingHolds'
  [+] Exported 0 documents from 'slotClaims'
  [+] Exported 0 documents from 'availabilityBlocks'
  [+] Exported 39 documents from 'payments'
  [+] Exported 13 documents from 'refunds'
  [+] Exported 5 documents from 'users'
  [+] Exported 1 documents from 'inquiries'
  [+] Exported 233 documents from 'auditLogs'
[+] Backup completed successfully into: backups/joybox_party_room_test_20261030_042101
[*] Pruning backups older than 30 days...
```

### 2.2 Restore Drill & Count Verification Step
Command executed:
```powershell
python backend/scripts/db_backup.py --restore-drill --target-db joybox_party_room_test
```
**Output:**
```
[*] Starting Restore Drill into TEST database: 'joybox_party_room_test' (dry_run=False)...
[*] Source manifest: joybox_party_room_test at 20261030_042101
  [OK] Restored 3/3 documents into 'joybox_party_room_test.packages'
  [OK] Restored 3/3 documents into 'joybox_party_room_test.addOns'
  [OK] Restored 0/0 documents into 'joybox_party_room_test.rooms'
  [OK] Restored 1/1 documents into 'joybox_party_room_test.offers'
  [OK] Restored 9/9 documents into 'joybox_party_room_test.galleryAssets'
  [OK] Restored 5/5 documents into 'joybox_party_room_test.faqs'
  [OK] Restored 0/0 documents into 'joybox_party_room_test.bookings'
  [OK] Restored 0/0 documents into 'joybox_party_room_test.bookingHolds'
  [OK] Restored 0/0 documents into 'joybox_party_room_test.slotClaims'
  [OK] Restored 0/0 documents into 'joybox_party_room_test.availabilityBlocks'
  [OK] Restored 39/39 documents into 'joybox_party_room_test.payments'
  [OK] Restored 13/13 documents into 'joybox_party_room_test.refunds'
  [OK] Restored 5/5 documents into 'joybox_party_room_test.users'
  [OK] Restored 1/1 documents into 'joybox_party_room_test.inquiries'
  [OK] Restored 233/233 documents into 'joybox_party_room_test.auditLogs'
[+] Restore drill complete! All counts match: True
```

---

## 3. Routine Production Backup Procedure (For System Owner)

> [!NOTE]
> MongoDB Atlas provides native continuous cloud backups. This script serves as an independent, portable JSON archive for disaster recovery and offsite auditing.

### Recommended Schedule
- **Daily Automated Export:** Run via scheduled cron at 02:00 AM IST.
- **Retention Period:** 30 days retention (automatic pruning of older directories).

### Production Backup Command
```powershell
python backend/scripts/db_backup.py --backup --db joybox_party_room --allow-production --confirm-production joybox_party_room --retention-days 30
```

### Owner Verification Tasks
1. Verify automated cloud backup snapshots in the MongoDB Atlas console (Backup tab).
2. Schedule regular quarterly disaster recovery drills using `--restore-drill --target-db joybox_drill_test`.

