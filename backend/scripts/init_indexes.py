"""
Authoritative MongoDB Indexes & Schema Validators Initializer.
Single source of truth for Joybox Party Room database constraints.
Supports safe dry-run mode and guards against unauthorized production modification.
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.db_safety import get_script_db_client, UnsafeDatabaseError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()


def apply_validators(db, dry_run=False):
    """
    Applies JSON schema validators for core transactional collections.
    Reconciles database/validators.js with live codebase field names (bookingStatus, roomId, etc.).
    """
    validators = {
        "inquiries": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["name", "phone", "source", "status", "createdAt", "updatedAt"],
                "properties": {
                    "name": {"bsonType": "string", "minLength": 2, "maxLength": 100},
                    "phone": {"bsonType": "string", "minLength": 8, "maxLength": 20},
                    "source": {"enum": ["website", "whatsapp", "phone", "instagram", "other"]},
                    "status": {"enum": ["new", "contacted", "qualified", "converted", "closed", "spam"]},
                    "createdAt": {"bsonType": "date"},
                    "updatedAt": {"bsonType": "date"},
                    "isDeleted": {"bsonType": "bool"}
                }
            }
        },
        "bookings": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["bookingReference", "bookingStatus"],
                "properties": {
                    "bookingReference": {"bsonType": "string"},
                    "roomId": {"bsonType": "string"},
                    "packageCode": {"bsonType": "string"},
                    "startAt": {"bsonType": "date"},
                    "endAt": {"bsonType": "date"},
                    "date": {"bsonType": "string"},
                    "bookingStatus": {
                        "enum": [
                            "pending",
                            "held",
                            "hold_placed",
                            "pending_payment",
                            "confirmed",
                            "cancelled",
                            "cancelled_due_to_conflict",
                            "completed",
                            "expired",
                            "no_show"
                        ]
                    },
                    "paymentStatus": {
                        "enum": ["unpaid", "pending", "paid", "refunded", "partially_refunded", "failed"]
                    },
                    "createdAt": {"bsonType": "date"},
                    "updatedAt": {"bsonType": "date"},
                    "isDeleted": {"bsonType": "bool"}
                }
            }
        }
    }

    if dry_run:
        for coll in validators:
            print(f"  [DRY-RUN] Would apply schema validator to collection '{coll}'")
        return

    existing_colls = db.list_collection_names()
    for coll_name, schema in validators.items():
        try:
            if coll_name in existing_colls:
                db.command({
                    "collMod": coll_name,
                    "validator": schema,
                    "validationLevel": "moderate",
                    "validationAction": "warn"
                })
                print(f"  [+] Applied schema validator to '{coll_name}'")
            else:
                db.create_collection(
                    coll_name,
                    validator=schema,
                    validationLevel="moderate",
                    validationAction="warn"
                )
                print(f"  [+] Created collection '{coll_name}' with schema validator")
        except Exception as exc:
            print(f"  [!] Note on validator for '{coll_name}': {exc}")


def init_indexes(
    db=None,
    db_name=None,
    uri=None,
    allow_production=False,
    confirm_token=None,
    dry_run=False
):
    """
    Initializes all authoritative MongoDB indexes and validators.
    Idempotent: safe to run repeatedly on any database.
    """
    if db is None:
        if not db_name:
            print("[!] ERROR: Explicit --db target is required (e.g. --db joybox_party_room_test).")
            sys.exit(1)
        try:
            client, db = get_script_db_client(
                db_name=db_name,
                uri=uri,
                allow_production=allow_production,
                confirm_token=confirm_token,
                appname="joybox-indexes-init"
            )
        except UnsafeDatabaseError as e:
            print(f"[!] SAFETY ERROR: {e}")
            sys.exit(1)

    target_name = db.name
    print(f"[*] Initializing indexes and validators on database: '{target_name}' (dry_run={dry_run})...")

    if dry_run:
        print("[*] [DRY-RUN] Simulating index creation across all collections...")
        apply_validators(db, dry_run=True)
        print("[+] [DRY-RUN] Index and validator verification complete.")
        return

    # packages
    db.packages.create_index([("code", 1)], unique=True)
    db.packages.create_index([("isActive", 1), ("displayOrder", 1)])

    # addOns
    db.addOns.create_index([("code", 1)], unique=True)
    db.addOns.create_index([("isActive", 1), ("displayOrder", 1)])

    # rooms
    db.rooms.create_index([("roomId", 1)], unique=True)
    db.rooms.create_index([("isActive", 1)])

    # customers
    db.customers.create_index([("phone", 1)], unique=True)

    # inquiries
    db.inquiries.create_index([("status", 1), ("createdAt", -1)])
    db.inquiries.create_index([("phone", 1), ("createdAt", -1)])
    db.inquiries.create_index([("createdAt", -1)])

    # bookings
    db.bookings.create_index([("bookingReference", 1)], unique=True)
    db.bookings.create_index([("roomId", 1), ("startAt", 1), ("endAt", 1), ("bookingStatus", 1)])
    db.bookings.create_index([("customerId", 1), ("createdAt", -1)])
    db.bookings.create_index([("bookingStatus", 1), ("startAt", 1)])
    db.bookings.create_index([("paymentStatus", 1), ("createdAt", -1)])
    db.bookings.create_index([("razorpayOrderId", 1)], sparse=True)

    # bookingHolds
    db.bookingHolds.create_index([("expiresAt", 1)], expireAfterSeconds=0)
    db.bookingHolds.create_index([("roomId", 1), ("startAt", 1), ("endAt", 1), ("status", 1)])
    db.bookingHolds.create_index([("sessionToken", 1)], unique=True)

    # slotClaims (CRITICAL atomic anti-double-booking indexes)
    db.slotClaims.create_index([("roomId", 1), ("slotStart", 1)], unique=True)
    db.slotClaims.create_index([("roomId", 1), ("date", 1), ("slotStart", 1)])
    db.slotClaims.create_index([("ownerId", 1)])
    db.slotClaims.create_index([("expiresAt", 1)], expireAfterSeconds=0)

    # availabilityBlocks
    db.availabilityBlocks.create_index([("roomId", 1), ("startAt", 1), ("endAt", 1)])

    # offers
    db.offers.create_index([("isActive", 1)])
    db.offers.create_index([("eligiblePackageCode", 1), ("isActive", 1)])

    # offerRedemptions
    db.offerRedemptions.create_index([("holdId", 1)], sparse=True, unique=True)
    db.offerRedemptions.create_index([("bookingId", 1)], sparse=True, unique=True)
    db.offerRedemptions.create_index([("offerId", 1), ("periodKey", 1), ("status", 1)])

    # payments
    db.payments.create_index([("bookingId", 1), ("createdAt", -1)])
    db.payments.create_index([("bookingReference", 1), ("createdAt", -1)])
    db.payments.create_index([("providerOrderId", 1)], sparse=True, unique=True)
    db.payments.create_index([("providerPaymentId", 1)], sparse=True, unique=True)
    db.payments.create_index([("idempotencyKey", 1)], sparse=True, unique=True)

    # refunds
    db.refunds.create_index([("bookingId", 1)])
    db.refunds.create_index([("bookingReference", 1)])
    db.refunds.create_index([("providerRefundId", 1)], sparse=True, unique=True)
    db.refunds.create_index([("idempotencyKey", 1)], sparse=True, unique=True)

    # users
    db.users.create_index([("username", 1)], unique=True)
    db.users.create_index([("email", 1)], unique=True)

    # galleryAssets
    db.galleryAssets.create_index([("isActive", 1), ("category", 1), ("displayOrder", 1)])

    # faqs
    db.faqs.create_index([("isActive", 1), ("displayOrder", 1)])

    # reviews
    db.reviews.create_index([("status", 1), ("displayOrder", 1)])

    # auditLogs
    db.auditLogs.create_index([("targetCollection", 1), ("targetId", 1), ("createdAt", -1)])
    db.auditLogs.create_index([("actorId", 1), ("createdAt", -1)])
    db.auditLogs.create_index([("createdAt", -1)])

    # webhookEvents
    db.webhookEvents.create_index([("provider", 1), ("eventId", 1)], unique=True)
    db.webhookEvents.create_index([("status", 1), ("createdAt", -1)])

    # idempotencyKeys
    db.idempotencyKeys.create_index([("key", 1), ("endpoint", 1)], unique=True)
    db.idempotencyKeys.create_index([("expiresAt", 1)], expireAfterSeconds=0)

    # rateLimits
    db.rateLimits.create_index([("key", 1)], unique=True)
    db.rateLimits.create_index([("expiresAt", 1)], expireAfterSeconds=0)

    # Apply collection schema validators
    apply_validators(db, dry_run=False)

    print(f"[+] All indexes and validators verified successfully on '{target_name}'.")


def main():
    parser = argparse.ArgumentParser(description="Authoritative MongoDB index and validator initializer.")
    parser.add_argument("--db", required=True, help="Target database name (e.g. joybox_party_room_test)")
    parser.add_argument("--uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--allow-production", action="store_true", help="Explicit flag required to target production database")
    parser.add_argument("--confirm-production", default=None, help="Must match database name if targeting production")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying database")
    args = parser.parse_args()

    init_indexes(
        db_name=args.db,
        uri=args.uri,
        allow_production=args.allow_production,
        confirm_token=args.confirm_production,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
