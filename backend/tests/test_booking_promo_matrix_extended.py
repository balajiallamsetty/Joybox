import pytest
import concurrent.futures
from bson import ObjectId
from datetime import datetime, timezone, timedelta
from app.services import BookingService, CatalogService
from app.repositories import (
    PackageRepository,
    AddOnRepository,
    OfferRepository,
    OfferRedemptionRepository,
    SlotClaimRepository,
    BookingHoldRepository,
    BookingRepository,
    CounterRepository,
    IdempotencyRepository,
    RateLimitRepository,
)
import os
from app.utils.datetime_utils import now_ist

@pytest.fixture
def test_db(live_test_client):
    return live_test_client

@pytest.fixture(autouse=True)
def restore_offers_fixture(test_db):
    from scripts.seed_offers import seed_offers
    yield
    test_db.offers.delete_many({})
    seed_offers(db=test_db, dry_run=False)

@pytest.fixture
def app(test_db):
    from app import create_app
    app_instance = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app_instance.extensions["mongo_db"] = test_db
    return app_instance

@pytest.fixture
def booking_svc(test_db, app):
    return BookingService(
        slot_claim_repo=SlotClaimRepository(test_db),
        hold_repo=BookingHoldRepository(test_db),
        booking_repo=BookingRepository(test_db),
        counter_repo=CounterRepository(test_db),
        offer_repo=OfferRepository(test_db),
        offer_redemption_repo=OfferRedemptionRepository(test_db),
        idempotency_repo=IdempotencyRepository(test_db),
        package_repo=PackageRepository(test_db),
        addon_repo=AddOnRepository(test_db),
        rate_limit_repo=RateLimitRepository(test_db),
        config=app.config,
    )

@pytest.fixture
def catalog_svc(test_db):
    return CatalogService(
        package_repo=PackageRepository(test_db),
        addon_repo=AddOnRepository(test_db),
        offer_repo=OfferRepository(test_db),
        offer_redemption_repo=OfferRedemptionRepository(test_db),
    )

def test_promo_validity_window(test_db, booking_svc, catalog_svc):
    """Verifies promo is rejected outside validFrom/validUntil and accepted within."""
    offers_col = test_db.offers
    # Set validity window: from tomorrow to next week
    now_str = now_ist().strftime("%Y-%m-%d")
    tomorrow = (now_ist() + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday = (now_ist() - timedelta(days=1)).strftime("%Y-%m-%d")
    next_week = (now_ist() + timedelta(days=7)).strftime("%Y-%m-%d")

    offer_id = ObjectId()
    offers_col.delete_many({"eligiblePackageCode": "basic"})
    offers_col.insert_one({
        "_id": offer_id,
        "name": "Summer Special",
        "eligiblePackageCode": "basic",
        "promoPricePerHourMinor": 79900,
        "monthlyLimit": 5,
        "monthlyRedemptionCount": 0,
        "validFrom": tomorrow,
        "validUntil": next_week,
        "isActive": True
    })

    # 1. Query for today (before validFrom) -> rejected with reason
    quote_today = catalog_svc.calculate_quote("basic", 1, event_date=now_str)
    assert quote_today["promoApplied"] is False
    assert "starts on" in quote_today["promoNotAppliedReason"]

    # 2. Query for event in window (e.g. Day + 3) -> accepted
    in_window_date = (now_ist() + timedelta(days=3)).strftime("%Y-%m-%d")
    quote_valid = catalog_svc.calculate_quote("basic", 1, event_date=in_window_date)
    assert quote_valid["promoApplied"] is True
    assert quote_valid["discountAmountMinor"] == 20000

    # 3. Query for event after window -> rejected
    past_window_date = (now_ist() + timedelta(days=10)).strftime("%Y-%m-%d")
    quote_expired = catalog_svc.calculate_quote("basic", 1, event_date=past_window_date)
    assert quote_expired["promoApplied"] is False
    assert "ended on" in quote_expired["promoNotAppliedReason"]

def test_promo_per_customer_limit(test_db, booking_svc, catalog_svc):
    """Verifies a single phone number cannot exceed maxPerCustomer redemptions."""
    offers_col = test_db.offers
    redemptions_col = test_db.offerRedemptions

    offers_col.delete_many({"eligiblePackageCode": "gold"})
    offer_id = ObjectId()
    offers_col.insert_one({
        "_id": offer_id,
        "name": "Gold VIP Welcome",
        "eligiblePackageCode": "gold",
        "promoPricePerHourMinor": 120000,
        "monthlyLimit": 10,
        "monthlyRedemptionCount": 0,
        "maxPerCustomer": 1,
        "isActive": True
    })

    test_phone = "9876500111"

    # First quote for customer -> promo eligible
    q1 = catalog_svc.calculate_quote("gold", 2, customer_phone=test_phone)
    assert q1["promoApplied"] is True

    # Customer redeems offer once
    redemptions_col.insert_one({
        "offerId": offer_id,
        "holdId": ObjectId(),
        "customerPhone": test_phone,
        "status": "reserved",
        "createdAt": datetime.now(timezone.utc)
    })

    # Second quote for same phone -> rejected
    q2 = catalog_svc.calculate_quote("gold", 2, customer_phone=test_phone)
    assert q2["promoApplied"] is False
    assert "limit reached" in q2["promoNotAppliedReason"]

    # Different customer phone -> still eligible
    q3 = catalog_svc.calculate_quote("gold", 2, customer_phone="9876500222")
    assert q3["promoApplied"] is True

def test_promo_non_stacking_invariant(test_db, catalog_svc):
    """Verifies only a single promotional offer is applied per reservation quote."""
    q = catalog_svc.calculate_quote("gold", 2, apply_promo=True)
    promo_lines = [item for item in q["lineItems"] if "Promotional" in item["description"]]
    assert len(promo_lines) <= 1

def test_percent_vs_flat_rounding(test_db, catalog_svc):
    """Verifies percentage discount and flat discount calculation with paise precision."""
    offers_col = test_db.offers
    offers_col.delete_many({"eligiblePackageCode": "basic"})

    # Test 1: Percentage discount with fractional paise (15% on 99900 = 14985 paise)
    offers_col.insert_one({
        "_id": ObjectId(),
        "name": "15% Off Festive",
        "eligiblePackageCode": "basic",
        "discountPercent": 15.0,
        "monthlyLimit": 10,
        "monthlyRedemptionCount": 0,
        "isActive": True
    })

    q_pct = catalog_svc.calculate_quote("basic", 1)
    assert q_pct["promoApplied"] is True
    assert q_pct["discountAmountMinor"] == 14985
    assert q_pct["totalAmountMinor"] == 99900 - 14985

    # Test 2: Flat discount (₹300 flat = 30000 paise)
    offers_col.delete_many({"eligiblePackageCode": "basic"})
    offers_col.insert_one({
        "_id": ObjectId(),
        "name": "Flat ₹300 Off",
        "eligiblePackageCode": "basic",
        "discountFlatMinor": 30000,
        "monthlyLimit": 10,
        "monthlyRedemptionCount": 0,
        "isActive": True
    })

    q_flat = catalog_svc.calculate_quote("basic", 1)
    assert q_flat["promoApplied"] is True
    assert q_flat["discountAmountMinor"] == 30000
    assert q_flat["totalAmountMinor"] == 69900

def test_gst_tax_calculation(test_db, catalog_svc):
    """Verifies 18% GST calculation on taxable net amount with line items breakdown."""
    offers_col = test_db.offers
    offers_col.delete_many({"eligiblePackageCode": "gold"})

    # Gold 2 hrs = 300,000 paise. 18% GST = 54,000 paise. Total = 354,000 paise (₹3,540)
    q_gst = catalog_svc.calculate_quote("gold", 2, apply_promo=False, gst_rate_percent=18.0)
    assert q_gst["taxRatePercent"] == 18.0
    assert q_gst["taxAmountMinor"] == 54000
    assert q_gst["totalAmountMinor"] == 354000
    assert q_gst["totalRupees"] == 3540.0

    gst_line = next(item for item in q_gst["lineItems"] if "GST" in item["description"])
    assert gst_line["amountMinor"] == 54000
    assert gst_line["amountRupees"] == 540.0

def test_quota_return_on_cancellation(test_db, booking_svc):
    """Verifies promo quota count decrements back when a booking is cancelled."""
    offers_col = test_db.offers
    offers_col.delete_many({"eligiblePackageCode": "basic"})
    offer_id = ObjectId()
    offers_col.insert_one({
        "_id": offer_id,
        "name": "Quota Return Test",
        "eligiblePackageCode": "basic",
        "promoPricePerHourMinor": 79900,
        "monthlyLimit": 5,
        "monthlyRedemptionCount": 0,
        "isActive": True
    })

    target_date = (now_ist() + timedelta(days=25)).strftime("%Y-%m-%d")
    test_phone = "9876543999"

    # Create booking with promo
    booking_res = booking_svc.create_booking({
        "packageCode": "basic",
        "durationHours": 1,
        "date": target_date,
        "startTime": "10:00",
        "customerName": "Quota Test",
        "customerPhone": test_phone,
        "applyPromo": True
    })

    ref = booking_res["bookingReference"]
    token = booking_res["accessToken"]

    # Verify quota incremented to 1
    offer_after_booking = offers_col.find_one({"_id": offer_id})
    assert offer_after_booking["monthlyRedemptionCount"] == 1

    # Cancel booking
    cancel_res = booking_svc.cancel_booking(ref, token=token, reason="Customer schedule changed")
    assert cancel_res["bookingStatus"] == "cancelled"

    # Verify quota was returned back to 0
    offer_after_cancel = offers_col.find_one({"_id": offer_id})
    assert offer_after_cancel["monthlyRedemptionCount"] == 0

def test_two_concurrent_buyers_for_last_promo(test_db, booking_svc):
    """Verifies race condition when 2 concurrent threads compete for the 5th (final) promo slot."""
    offers_col = test_db.offers
    offers_col.delete_many({"eligiblePackageCode": "basic"})
    offer_id = ObjectId()
    offers_col.insert_one({
        "_id": offer_id,
        "name": "Last Slot Race",
        "eligiblePackageCode": "basic",
        "promoPricePerHourMinor": 79900,
        "monthlyLimit": 5,
        "monthlyRedemptionCount": 4,  # Only 1 slot remains
        "isActive": True
    })

    date1 = (now_ist() + timedelta(days=26)).strftime("%Y-%m-%d")
    date2 = (now_ist() + timedelta(days=27)).strftime("%Y-%m-%d")

    results = []

    def book_worker(date_str, phone_str):
        try:
            res = booking_svc.create_hold({
                "packageCode": "basic",
                "durationHours": 1,
                "date": date_str,
                "startTime": "11:00",
                "customerName": f"Racer {phone_str}",
                "customerPhone": phone_str,
                "applyPromo": True
            })
            return res
        except Exception as e:
            return str(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(book_worker, date1, "9876543001")
        f2 = executor.submit(book_worker, date2, "9876543002")
        results = [f1.result(), f2.result()]

    promo_applied_count = sum(
        1 for r in results if isinstance(r, dict) and r.get("pricing", {}).get("promoApplied") is True
    )

    # Exactly 1 thread must win the last promo slot
    assert promo_applied_count == 1

    # Final redemption count must cap exactly at 5
    final_offer = offers_col.find_one({"_id": offer_id})
    assert final_offer["monthlyRedemptionCount"] == 5
