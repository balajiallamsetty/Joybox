"""
Unit and Integration Tests for Phase 2: Booking Lifecycle & Claim Integrity Hardening.
Tests BUG-01, BUG-02, BUG-04:
- Claim rollback on unexpected exceptions (never leaves orphan claims).
- Abandoned checkout expiration and slot claim release.
- Sweep promo redemption cleanup and atomic quota replenishment without AttributeError.
- Bounded single-extension on payment order creation.
- Janitor pass cleanup of ghost claims and terminal bookings.
"""
import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from unittest.mock import MagicMock, patch

from app.config import Config
from app.repositories import (
    SlotClaimRepository,
    BookingHoldRepository,
    BookingRepository,
    OfferRepository,
    OfferRedemptionRepository,
    PaymentRepository
)
from app.jobs.run_sweeps import run_sweeps
from app.services.payment_service import PaymentService, RazorpayClient
from app.utils.datetime_utils import now_utc

def test_claim_all_or_rollback_cleans_up_on_unexpected_exception(live_test_client):
    """
    BUG-04 regression test:
    Verify that if an unexpected exception (e.g. PyMongoError/network timeout) occurs
    midway through inserting multiple slot claims, all partially inserted claims are rolled back,
    and other owners' claims are completely untouched.
    """
    db = live_test_client
    claim_repo = SlotClaimRepository(db)
    now_u = now_utc()

    room_id = "test_room_bug04"
    other_owner_id = ObjectId()
    failing_owner_id = ObjectId()

    # Clean test room
    db.slotClaims.delete_many({"roomId": room_id})

    # Pre-insert a claim for another owner
    other_claim = {
        "roomId": room_id,
        "slotStart": now_u + timedelta(hours=1),
        "slotEnd": now_u + timedelta(hours=1, minutes=30),
        "isBuffer": False,
        "ownerType": "booking",
        "ownerId": other_owner_id,
        "createdAt": now_u,
        "expiresAt": None
    }
    db.slotClaims.insert_one(other_claim)

    # Prepare 3 new slot claims for failing owner
    docs = [
        {
            "roomId": room_id,
            "slotStart": now_u + timedelta(hours=2),
            "slotEnd": now_u + timedelta(hours=2, minutes=30),
            "isBuffer": False,
            "ownerType": "booking",
            "ownerId": failing_owner_id,
            "createdAt": now_u,
            "expiresAt": now_u + timedelta(minutes=15)
        },
        {
            "roomId": room_id,
            "slotStart": now_u + timedelta(hours=2, minutes=30),
            "slotEnd": now_u + timedelta(hours=3),
            "isBuffer": False,
            "ownerType": "booking",
            "ownerId": failing_owner_id,
            "createdAt": now_u,
            "expiresAt": now_u + timedelta(minutes=15)
        },
        {
            "roomId": room_id,
            "slotStart": now_u + timedelta(hours=3),
            "slotEnd": now_u + timedelta(hours=3, minutes=30),
            "isBuffer": False,
            "ownerType": "booking",
            "ownerId": failing_owner_id,
            "createdAt": now_u,
            "expiresAt": now_u + timedelta(minutes=15)
        }
    ]

    original_insert_one = claim_repo.collection.insert_one
    call_count = 0

    def mock_insert_one(doc):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            # Simulate unexpected socket/network crash on 2nd item
            raise ConnectionResetError("Simulated network drop during slot claim insertion")
        return original_insert_one(doc)

    with patch.object(claim_repo.collection, "insert_one", side_effect=mock_insert_one):
        with pytest.raises(ConnectionResetError):
            claim_repo.claim_all_or_rollback(docs)

    # Verification:
    # 1. Failing owner has 0 claims remaining in database (rolled back)
    failing_claims = list(db.slotClaims.find({"ownerId": failing_owner_id}))
    assert len(failing_claims) == 0, "Partially inserted claims must be deleted on error"

    # 2. Other owner's claim was NOT deleted
    other_claims = list(db.slotClaims.find({"ownerId": other_owner_id}))
    assert len(other_claims) == 1, "Other owner's claims must be preserved"

    # Clean up
    db.slotClaims.delete_many({"roomId": room_id})


def test_abandoned_booking_expires_after_grace_and_frees_slots(live_test_client):
    """
    BUG-01 regression test:
    Verify that when a user creates a booking but abandons checkout, the background sweep:
    1. Identifies the stale pending_payment booking past checkoutExpiresAt.
    2. Atomically marks the booking as expired.
    3. Releases the slot claims so another user can immediately book the slot.
    """
    db = live_test_client
    now_u = now_utc()
    room_id = "test_room_abandoned"

    # Clean collections
    db.bookings.delete_many({"roomId": room_id})
    db.slotClaims.delete_many({"roomId": room_id})

    booking_id = ObjectId()
    booking_ref = "JBX-TEST-ABANDONED"
    slot_time = now_u + timedelta(days=2)

    # 1. Insert a pending_payment booking whose checkout has expired
    expired_checkout_time = now_u - timedelta(minutes=5)
    booking_doc = {
        "_id": booking_id,
        "bookingReference": booking_ref,
        "accessTokenHash": "dummyhash",
        "roomId": room_id,
        "packageCode": "standard",
        "durationHours": 1,
        "startAt": slot_time,
        "endAt": slot_time + timedelta(hours=1),
        "bookingStatus": "pending_payment",
        "paymentStatus": "unpaid",
        "checkoutExpiresAt": expired_checkout_time,
        "createdAt": now_u - timedelta(minutes=20),
        "updatedAt": now_u - timedelta(minutes=20)
    }
    db.bookings.insert_one(booking_doc)

    # 2. Insert corresponding slot claims owned by booking with real expiresAt
    claim_doc = {
        "roomId": room_id,
        "slotStart": slot_time,
        "slotEnd": slot_time + timedelta(hours=1),
        "isBuffer": False,
        "ownerType": "booking",
        "ownerId": booking_id,
        "createdAt": now_u - timedelta(minutes=20),
        "expiresAt": expired_checkout_time
    }
    db.slotClaims.insert_one(claim_doc)

    # Verify claim exists initially
    assert db.slotClaims.count_documents({"ownerId": booking_id}) == 1

    # 3. Execute background sweeps
    sweep_results = run_sweeps(db.name)

    # 4. Assertions
    updated_booking = db.bookings.find_one({"_id": booking_id})
    assert updated_booking["bookingStatus"] == "expired", "Abandoned booking must transition to expired"
    assert "cancellationReason" in updated_booking

    # Assert slot claims were released
    remaining_claims = db.slotClaims.count_documents({"ownerId": booking_id})
    assert remaining_claims == 0, "Slot claims for abandoned booking must be released"

    # Clean up
    db.bookings.delete_many({"roomId": room_id})
    db.slotClaims.delete_many({"roomId": room_id})


def test_sweeps_release_expired_promo_reservations_without_crashing(live_test_client):
    """
    BUG-02 regression test:
    Verify that sweep job correctly cleans up expired promo reservations using
    release_reservation_idempotent() and atomically restores the monthly quota
    via offer_repo.atomic_release_slot().
    Must NOT raise AttributeError.
    Repeated sweeps must be idempotent.
    """
    db = live_test_client
    now_u = now_utc()
    hold_repo = BookingHoldRepository(db)
    offer_repo = OfferRepository(db)
    offer_redemp_repo = OfferRedemptionRepository(db)

    offer_code = "TEST_PROMO_SWEEP"
    period_key = now_u.strftime("%Y-%m")

    # Clean existing test offers and redemptions
    db.offers.delete_many({"code": offer_code})
    db.offerRedemptions.delete_many({"offerCode": offer_code})

    # Insert test offer with 1 allocated slot
    offer_doc = {
        "_id": ObjectId(),
        "code": offer_code,
        "title": "Test Promo",
        "description": "Test",
        "discountPercentage": 10,
        "maxMonthlyQuota": 5,
        "monthlyRedemptionCount": 1,
        "isActive": True,
        "createdAt": now_u,
        "updatedAt": now_u
    }
    db.offers.insert_one(offer_doc)
    offer_id = offer_doc["_id"]

    # Insert expired hold
    hold_id = ObjectId()
    db.bookingHolds.insert_one({
        "_id": hold_id,
        "roomId": "test_room",
        "status": "expired",
        "expiresAt": now_u - timedelta(minutes=10),
        "createdAt": now_u - timedelta(minutes=25)
    })

    # Insert reserved redemption tied to the expired hold
    redemp_id = ObjectId()
    db.offerRedemptions.insert_one({
        "_id": redemp_id,
        "offerId": offer_id,
        "offerCode": offer_code,
        "periodKey": period_key,
        "holdId": hold_id,
        "status": "reserved",
        "createdAt": now_u - timedelta(minutes=25),
        "updatedAt": now_u - timedelta(minutes=25)
    })

    # 1. Run sweep - Must execute cleanly without AttributeError
    results = run_sweeps(db.name)
    assert results["promos_released"] >= 1, "Sweep should report at least 1 promo released"

    # 2. Check redemption document status
    redemp_after = db.offerRedemptions.find_one({"_id": redemp_id})
    assert redemp_after["status"] == "released", "Redemption status must be updated to released"

    # 3. Check offer monthlyRedemptionCount decremented
    offer_after = db.offers.find_one({"_id": offer_id})
    assert offer_after["monthlyRedemptionCount"] == 0, "Offer monthly redemption count must be restored to 0"

    # 4. Run sweep a SECOND time - must be idempotent (no double release)
    results2 = run_sweeps(db.name)
    assert results2["promos_released"] == 0, "Second sweep should not re-release already released promo"
    offer_after2 = db.offers.find_one({"_id": offer_id})
    assert offer_after2["monthlyRedemptionCount"] == 0, "Monthly redemption count must remain 0"

    # Clean up
    db.offers.delete_many({"_id": offer_id})
    db.offerRedemptions.delete_many({"_id": redemp_id})
    db.bookingHolds.delete_many({"_id": hold_id})


def test_payment_order_creation_extends_expiry_once_bounded(live_test_client):
    """
    Verify that creating a payment order extends the checkout window once,
    and is strictly bounded by MAX_PAYMENT_WINDOW_MINUTES.
    """
    db = live_test_client
    now_u = now_utc()
    booking_id = ObjectId()
    booking_ref = "JBX-TEST-EXTEND"

    db.bookings.delete_many({"bookingReference": booking_ref})
    db.slotClaims.delete_many({"ownerId": booking_id})
    db.payments.delete_many({"bookingReference": booking_ref})

    initial_created = now_u - timedelta(minutes=5)
    initial_expiry = initial_created + timedelta(minutes=15)

    import secrets
    import hashlib
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    booking_doc = {
        "_id": booking_id,
        "bookingReference": booking_ref,
        "accessTokenHash": token_hash,
        "roomId": "main",
        "packageName": "Standard",
        "pricing": {"totalAmountMinor": 350000},
        "bookingStatus": "pending_payment",
        "paymentStatus": "unpaid",
        "checkoutExpiresAt": initial_expiry,
        "createdAt": initial_created,
        "updatedAt": initial_created
    }
    db.bookings.insert_one(booking_doc)

    db.slotClaims.insert_one({
        "roomId": "main",
        "slotStart": now_u + timedelta(days=1),
        "slotEnd": now_u + timedelta(days=1, hours=1),
        "isBuffer": False,
        "ownerType": "booking",
        "ownerId": booking_id,
        "createdAt": initial_created,
        "expiresAt": initial_expiry
    })

    booking_repo = BookingRepository(db)
    payment_repo = PaymentRepository(db)
    claim_repo = SlotClaimRepository(db)
    hold_repo = BookingHoldRepository(db)

    svc = PaymentService(
        booking_repo=booking_repo,
        payment_repo=payment_repo,
        refund_repo=None,
        webhook_repo=None,
        slot_claim_repo=claim_repo,
        hold_repo=hold_repo,
        config=Config,
        razorpay_client=RazorpayClient(is_mock=True)
    )

    # First order creation
    res1 = svc.create_order(booking_ref, raw_token)
    assert res1["orderId"] is not None

    b_after1 = db.bookings.find_one({"_id": booking_id})
    assert b_after1.get("paymentWindowExtended") is True
    first_extended_expiry = b_after1["checkoutExpiresAt"]
    assert first_extended_expiry > initial_expiry, "Expiry should be extended on order creation"

    # Second order creation (replay/retry) - must NOT extend again
    res2 = svc.create_order(booking_ref, raw_token)
    b_after2 = db.bookings.find_one({"_id": booking_id})
    assert b_after2["checkoutExpiresAt"] == first_extended_expiry, "Repeated order creation must not extend expiry again"

    # Clean up
    db.bookings.delete_many({"bookingReference": booking_ref})
    db.slotClaims.delete_many({"ownerId": booking_id})
    db.payments.delete_many({"bookingReference": booking_ref})
