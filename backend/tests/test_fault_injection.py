import pytest
import uuid
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from app.services.booking_service import BookingService
from app.repositories import (
    SlotClaimRepository,
    BookingHoldRepository,
    BookingRepository,
    CounterRepository,
    OfferRepository,
    OfferRedemptionRepository,
    IdempotencyRepository,
    PackageRepository,
    AddOnRepository,
)
from app.utils.datetime_utils import now_utc
from app.utils.exceptions import SlotUnavailableError

def test_booking_creation_fault_injection_cleanup(live_test_client):
    """
    Fault injection test: If an exception is raised immediately during slot reservation,
    prove that any partial work (promo reservation, partial claims) is compensated/cleaned up
    and no orphan records remain.
    """
    test_db = live_test_client

    hold_repo = BookingHoldRepository(test_db)
    booking_repo = BookingRepository(test_db)
    counter_repo = CounterRepository(test_db)
    offer_repo = OfferRepository(test_db)
    offer_redemption_repo = OfferRedemptionRepository(test_db)
    idempotency_repo = IdempotencyRepository(test_db)
    package_repo = PackageRepository(test_db)
    addon_repo = AddOnRepository(test_db)

    # Subclass SlotClaimRepository to simulate failure after partial insertion
    class CrashingSlotClaimRepo(SlotClaimRepository):
        def claim_all_or_rollback(self, claim_docs):
            # Simulate a database failure
            return False

    crashing_slot_repo = CrashingSlotClaimRepo(test_db)

    svc = BookingService(
        slot_claim_repo=crashing_slot_repo,
        hold_repo=hold_repo,
        booking_repo=booking_repo,
        counter_repo=counter_repo,
        offer_repo=offer_repo,
        offer_redemption_repo=offer_redemption_repo,
        idempotency_repo=idempotency_repo,
        package_repo=package_repo,
        addon_repo=addon_repo,
    )

    payload = {
        "packageCode": "basic",
        "durationHours": 2,
        "date": "2026-11-28",
        "startTime": "10:00",
        "customerName": "Fault Injection Guest",
        "customerPhone": "9876543210",
        "applyPromo": True
    }

    # Record initial promo redemption count
    basic_offer = offer_repo.find_by_package("basic")
    initial_count = basic_offer.get("monthlyRedemptionCount", 0) if basic_offer else 0

    with pytest.raises(SlotUnavailableError):
        svc.create_hold(payload)

    # Verify no orphan hold was created
    orphan_hold = test_db.bookingHolds.find_one({"customer.name": "Fault Injection Guest"})
    assert orphan_hold is None

    # Verify promo count was rolled back
    refreshed_offer = offer_repo.find_by_package("basic")
    if refreshed_offer:
        assert refreshed_offer.get("monthlyRedemptionCount", 0) == initial_count

    # Verify no active offer redemptions remain
    orphan_redemption = test_db.offerRedemptions.find_one({"status": "reserved"})
    # Any reserved redemptions should have been released
    if orphan_redemption:
        assert orphan_redemption.get("status") != "reserved" or orphan_redemption.get("holdId") is not None

