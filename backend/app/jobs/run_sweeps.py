"""
Scheduled Background Maintenance Sweeps for Joybox Party Room.
Can be executed as a standalone CLI job (e.g. Render Cron Job):
  python -m app.jobs.run_sweeps

Performs idempotent maintenance routines:
1. Reclaims expired holds and unlocks slot claims.
2. Reclaims expired pending_payment bookings (abandoned checkouts) and frees slots.
3. Janitor reconciliation: frees claims on cancelled/expired bookings and handles ghost claims.
4. Releases reserved promotional discounts for expired holds/bookings back to monthly quota.
5. Reconciles stale pending payments (>15 minutes old) against Razorpay.
"""
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

from pymongo import MongoClient, ReturnDocument
from app.config import Config
from app.repositories import (
    BookingHoldRepository,
    SlotClaimRepository,
    OfferRepository,
    OfferRedemptionRepository,
    PaymentRepository,
    BookingRepository,
    RefundRepository,
    WebhookEventRepository,
)
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService, RazorpayClient
from app.utils.datetime_utils import now_utc

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [job=run_sweeps] %(message)s"
)
logger = logging.getLogger("joybox_sweeps")

def run_sweeps(db_name: str = None) -> dict:
    target_db = db_name or Config.MONGODB_DB
    logger.info(f"Starting scheduled maintenance sweeps on database: '{target_db}'...")

    client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000, tz_aware=True, appname="joybox-sweeps")
    db = client[target_db]
    now_u = now_utc()

    # O1: Distributed Lease Lock - prevent dual concurrent execution across cron or workers
    lease_window_minutes = 5
    lease_expires = now_u + timedelta(minutes=lease_window_minutes)
    pid = os.getpid()

    try:
        lock_res = db.cronLocks.find_one_and_update(
            {
                "_id": "maintenance_sweeps_lease",
                "$or": [
                    {"lockedUntil": {"$lte": now_u}},
                    {"lockedUntil": None}
                ]
            },
            {
                "$set": {
                    "lockedUntil": lease_expires,
                    "lockedAt": now_u,
                    "holderPid": pid
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
    except Exception as lock_err:
        logger.warning(f"Could not check cronLocks: {lock_err}. Proceeding without distributed lease.")
        lock_res = {"holderPid": pid}

    if lock_res and lock_res.get("holderPid") != pid:
        logger.warning(f"[-] Another sweep job currently holds the active lease (lockedUntil: {lock_res.get('lockedUntil')}). Skipping this run.")
        return {"status": "skipped", "reason": "concurrent_lease_held"}

    hold_repo = BookingHoldRepository(db)
    claim_repo = SlotClaimRepository(db)
    offer_repo = OfferRepository(db)
    offer_redemp_repo = OfferRedemptionRepository(db)
    payment_repo = PaymentRepository(db)
    booking_repo = BookingRepository(db)

    results = {
        "timestamp": now_u.isoformat(),
        "database": target_db,
        "expired_holds_reclaimed": 0,
        "expired_bookings_reclaimed": 0,
        "promos_released": 0,
        "payments_reconciled": 0,
    }

    # 1. Sweep expired holds
    try:
        expired_cursor = db.bookingHolds.find({
            "status": "active",
            "expiresAt": {"$lte": now_u}
        })
        reclaimed_count = 0
        for hold in expired_cursor:
            hold_id = hold["_id"]
            # Transition hold to expired
            hold_repo.transition_status(hold_id, "active", "expired")
            # Release slot claims held by this hold
            claim_repo.release_by_owner(hold_id)
            reclaimed_count += 1

        results["expired_holds_reclaimed"] = reclaimed_count
        logger.info(f"[+] Reclaimed {reclaimed_count} expired holds and released associated slot claims.")
    except Exception as e:
        logger.error(f"[!] Error sweeping expired holds: {str(e)}")

    # 1b. Sweep abandoned checkouts (pending_payment bookings past checkout grace)
    try:
        grace_mins = getattr(Config, "CHECKOUT_GRACE_MINUTES", 15)
        expired_bookings_cursor = db.bookings.find({
            "bookingStatus": "pending_payment",
            "$or": [
                {"checkoutExpiresAt": {"$lte": now_u}},
                {
                    "checkoutExpiresAt": None,
                    "createdAt": {"$lte": now_u - timedelta(minutes=grace_mins)}
                }
            ]
        })
        reclaimed_bookings = 0
        for b in expired_bookings_cursor:
            b_id = b["_id"]
            b_ref = b.get("bookingReference")

            # Guard: do not expire if payment was already captured or authorized
            latest_payment = payment_repo.find_latest_by_booking_reference(b_ref) if b_ref else None
            if latest_payment and latest_payment.get("status") in ("captured", "authorized", "paid"):
                continue

            # Compare-and-set: status must still be pending_payment
            res = db.bookings.update_one(
                {"_id": b_id, "bookingStatus": "pending_payment"},
                {
                    "$set": {
                        "bookingStatus": "expired",
                        "cancellationReason": "Checkout grace window expired before payment confirmation",
                        "updatedAt": now_u
                    }
                }
            )
            if res.modified_count > 0:
                # Release slot claims
                claim_repo.release_by_owner(b_id)
                # Release promo reservation if any
                released = offer_redemp_repo.release_reservation_idempotent(b_id, now_u)
                if released and released.get("status") == "released":
                    offer_id = released.get("offerId")
                    if offer_id and offer_repo:
                        offer_repo.atomic_release_slot(offer_id)
                reclaimed_bookings += 1

        results["expired_bookings_reclaimed"] = reclaimed_bookings
        logger.info(f"[+] Reclaimed {reclaimed_bookings} abandoned pending bookings and released slot claims.")
    except Exception as e:
        logger.error(f"[!] Error sweeping abandoned bookings: {str(e)}")

    # 1c. Janitor reconciliation pass
    try:
        # Release any claims still owned by terminal bookings
        terminal_bookings = db.bookings.find(
            {"bookingStatus": {"$in": ["expired", "cancelled", "cancelled_due_to_conflict"]}},
            {"_id": 1}
        )
        for tb in terminal_bookings:
            claim_repo.release_by_owner(tb["_id"])

        # Detect ghost bookings whose claims vanished via TTL or eviction
        stale_pending = db.bookings.find({
            "bookingStatus": "pending_payment",
            "createdAt": {"$lte": now_u - timedelta(minutes=2)}
        })
        for pb in stale_pending:
            active_count = db.slotClaims.count_documents({"ownerId": pb["_id"], "ownerType": "booking"})
            if active_count == 0:
                res = db.bookings.update_one(
                    {"_id": pb["_id"], "bookingStatus": "pending_payment"},
                    {
                        "$set": {
                            "bookingStatus": "expired",
                            "cancellationReason": "Slot claims expired or evicted",
                            "updatedAt": now_u
                        }
                    }
                )
                if res.modified_count > 0:
                    released = offer_redemp_repo.release_reservation_idempotent(pb["_id"], now_u)
                    if released and released.get("status") == "released" and released.get("offerId") and offer_repo:
                        offer_repo.atomic_release_slot(released["offerId"])
    except Exception as e:
        logger.error(f"[!] Error running janitor claim sweep: {str(e)}")

    # 2. Sweep expired promo redemptions
    try:
        released_promos = 0
        reserved_redemps = db.offerRedemptions.find({"status": "reserved"})
        for redemp in reserved_redemps:
            hold_id = redemp.get("holdId")
            booking_id = redemp.get("bookingId")
            target_id = hold_id or booking_id

            if not target_id:
                continue

            should_release = False
            if hold_id:
                h = hold_repo.find_by_id(hold_id)
                if not h or h.get("status") in ("expired", "cancelled"):
                    should_release = True
            elif booking_id:
                b = booking_repo.find_by_id(booking_id)
                if not b or b.get("bookingStatus") in ("expired", "cancelled", "cancelled_due_to_conflict"):
                    should_release = True

            if should_release:
                try:
                    released = offer_redemp_repo.release_reservation_idempotent(target_id, now_u)
                    if released and released.get("status") == "released":
                        offer_id = redemp.get("offerId") or released.get("offerId")
                        if offer_id and offer_repo:
                            offer_repo.atomic_release_slot(offer_id)
                        released_promos += 1
                except Exception as ind_err:
                    logger.error(f"[!] Error releasing individual promo reservation for {target_id}: {ind_err}")

        results["promos_released"] = released_promos
        logger.info(f"[+] Released {released_promos} expired promo reservations back to monthly quota.")
    except Exception as e:
        logger.error(f"[!] Error releasing expired promo redemptions: {str(e)}")

    # 3. Reconcile stale pending payments
    try:
        refund_repo = RefundRepository(db)
        webhook_repo = WebhookEventRepository(db)
        payment_svc = PaymentService(
            booking_repo=booking_repo,
            payment_repo=payment_repo,
            refund_repo=refund_repo,
            webhook_repo=webhook_repo,
            hold_repo=hold_repo,
            slot_claim_repo=claim_repo,
            offer_repo=offer_repo,
            offer_redemption_repo=offer_redemp_repo,
            razorpay_client=RazorpayClient(is_mock=Config.FLASK_ENV == "development" and not Config.RAZORPAY_KEY_ID),
            config=Config
        )
        reconciled = payment_svc.reconcile_pending_payments(
            age_minutes=Config.RECONCILIATION_AGE_MINUTES
        )
        results["payments_reconciled"] = len(reconciled)
        logger.info(f"[+] Reconciled {len(reconciled)} pending payments against payment gateway.")
    except Exception as e:
        logger.error(f"[!] Error reconciling pending payments: {str(e)}")

    # Release distributed lease lock upon completion
    try:
        db.cronLocks.update_one(
            {"_id": "maintenance_sweeps_lease", "holderPid": pid},
            {"$set": {"lockedUntil": None}}
        )
    except Exception as lock_err:
        logger.warning(f"Could not release maintenance lease: {lock_err}")

    logger.info(f"[+] Scheduled sweeps finished successfully: {results}")
    return results

if __name__ == "__main__":
    # If run directly as script, ensure backend directory is in path
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    run_sweeps()
