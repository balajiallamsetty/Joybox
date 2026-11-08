import hashlib
import hmac
import json
import pytest
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from backend.app.config import Config
from backend.app.services.payment_service import PaymentService, RazorpayClient
from backend.app.repositories import (
    BookingRepository,
    BookingHoldRepository,
    PaymentRepository,
    RefundRepository,
    WebhookEventRepository,
    SlotClaimRepository,
    OfferRepository,
    OfferRedemptionRepository,
    IdempotencyRepository,
)
from backend.app.utils.datetime_utils import now_utc, format_ist_time
from backend.app.utils.exceptions import (
    PaymentVerificationError,
    RefundNotAllowedError,
    PaymentGatewayError,
)

from backend.app import create_app

@pytest.fixture
def payment_fixture(live_test_client):
    test_db = live_test_client
    app = create_app()
    app.config["TESTING"] = True
    app.config["MONGODB_DB_NAME"] = test_db.name
    app.extensions["mongo_db"] = test_db

    booking_repo = BookingRepository(test_db)
    hold_repo = BookingHoldRepository(test_db)
    payment_repo = PaymentRepository(test_db)
    refund_repo = RefundRepository(test_db)
    webhook_repo = WebhookEventRepository(test_db)
    slot_claim_repo = SlotClaimRepository(test_db)
    offer_repo = OfferRepository(test_db)
    offer_redemption_repo = OfferRedemptionRepository(test_db)
    idempotency_repo = IdempotencyRepository(test_db)

    svc = PaymentService(
        booking_repo=booking_repo,
        payment_repo=payment_repo,
        refund_repo=refund_repo,
        webhook_repo=webhook_repo,
        slot_claim_repo=slot_claim_repo,
        offer_repo=offer_repo,
        offer_redemption_repo=offer_redemption_repo,
        idempotency_repo=idempotency_repo,
        hold_repo=hold_repo,
        config=app.config,
    )

    return {
        "service": svc,
        "booking_repo": booking_repo,
        "hold_repo": hold_repo,
        "payment_repo": payment_repo,
        "refund_repo": refund_repo,
        "webhook_repo": webhook_repo,
        "slot_claim_repo": slot_claim_repo,
        "test_db": test_db,
    }

import uuid

def test_hold_extension_on_create_order(payment_fixture):
    """Verifies that create_order extends hold payment window."""
    svc = payment_fixture["service"]
    hold_repo = payment_fixture["hold_repo"]
    booking_repo = payment_fixture["booking_repo"]

    now_u = now_utc()
    hold_id = ObjectId()
    hold_doc = {
        "_id": hold_id,
        "status": "converted",
        "sessionToken": str(uuid.uuid4()),
        "expiresAt": now_u + timedelta(minutes=5),
        "createdAt": now_u,
    }
    hold_repo.insert(hold_doc)

    raw_token = "secret-token-123"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    ref = f"JBX-T-{uuid.uuid4().hex[:6]}"

    booking_id = ObjectId()
    booking_doc = {
        "_id": booking_id,
        "bookingReference": ref,
        "accessTokenHash": token_hash,
        "holdId": hold_id,
        "bookingStatus": "hold_placed",
        "paymentStatus": "unpaid",
        "pricing": {"totalAmountMinor": 50000},
        "customer": {"name": "Test Guest", "phone": "9876543210"},
        "createdAt": now_u,
        "updatedAt": now_u,
    }
    booking_repo.insert(booking_doc)

    res = svc.create_order(ref, raw_token)
    assert res["orderId"] is not None

    updated_hold = hold_repo.find_by_id(hold_id)
    assert "paymentExpiresAt" in updated_hold
    assert updated_hold["paymentExpiresAt"] > now_u + timedelta(minutes=10)

def test_verify_payment_gateway_amount_mismatch(payment_fixture):
    """Verifies that verify_payment catches amount or currency mismatch from gateway."""
    svc = payment_fixture["service"]
    booking_repo = payment_fixture["booking_repo"]

    raw_token = "token-xyz"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now_u = now_utc()
    ref = f"JBX-T-{uuid.uuid4().hex[:6]}"

    booking_id = ObjectId()
    booking_doc = {
        "_id": booking_id,
        "bookingReference": ref,
        "accessTokenHash": token_hash,
        "bookingStatus": "hold_placed",
        "paymentStatus": "unpaid",
        "pricing": {"totalAmountMinor": 50000},
        "startAt": now_u + timedelta(days=5),
        "endAt": now_u + timedelta(days=5, hours=2),
        "roomId": "main",
        "customer": {"name": "Test Guest"},
        "createdAt": now_u,
        "updatedAt": now_u,
    }
    booking_repo.insert(booking_doc)

    order_id = f"order_{uuid.uuid4().hex[:8]}"
    payment_id = f"pay_{uuid.uuid4().hex[:8]}"
    secret = Config.RAZORPAY_KEY_SECRET or "test_secret"
    svc.config._cfg["RAZORPAY_KEY_SECRET"] = secret
    sig = hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()

    # Create mock client that returns wrong amount
    class MockWrongAmountClient(RazorpayClient):
        def fetch_payment(self, pid, expected_order_id=None, expected_amount=None):
            return {
                "id": pid,
                "entity": "payment",
                "amount": 20000, # Mismatch! Booking is 50000
                "currency": "INR",
                "status": "captured",
                "order_id": order_id,
            }

    svc.client = MockWrongAmountClient(is_mock=True)

    with pytest.raises(PaymentVerificationError) as exc_info:
        svc.verify_payment(ref, raw_token, order_id, payment_id, sig)
    assert "amount does not match" in str(exc_info.value)

def test_atomic_refund_and_failed_gateway_handling(payment_fixture):
    """Verifies that failed gateway calls record failed refund doc and flag payment for review."""
    svc = payment_fixture["service"]
    booking_repo = payment_fixture["booking_repo"]
    payment_repo = payment_fixture["payment_repo"]
    refund_repo = payment_fixture["refund_repo"]

    raw_token = "token-ref"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now_u = now_utc()
    ref = f"JBX-T-{uuid.uuid4().hex[:6]}"

    booking_id = ObjectId()
    booking_doc = {
        "_id": booking_id,
        "bookingReference": ref,
        "accessTokenHash": token_hash,
        "bookingStatus": "confirmed",
        "paymentStatus": "paid",
        "pricing": {"totalAmountMinor": 50000},
        "startAt": now_u + timedelta(days=5), # > 48h, eligible for 100%
        "endAt": now_u + timedelta(days=5, hours=2),
        "createdAt": now_u,
        "updatedAt": now_u,
    }
    booking_repo.insert(booking_doc)

    payment_id = f"pay_{uuid.uuid4().hex[:8]}"
    payment_doc = {
        "_id": ObjectId(),
        "bookingId": booking_id,
        "bookingReference": ref,
        "provider": "razorpay",
        "providerOrderId": f"order_{uuid.uuid4().hex[:8]}",
        "providerPaymentId": payment_id,
        "amountMinor": 50000,
        "amountRefundedMinor": 0,
        "currency": "INR",
        "status": "captured",
        "createdAt": now_u,
        "updatedAt": now_u,
    }
    payment_repo.insert(payment_doc)

    # Mock client that raises network/gateway error
    class FailingRefundClient(RazorpayClient):
        def create_refund(self, payment_id, amount=None, notes=None):
            raise PaymentGatewayError("Simulated Razorpay gateway 500 failure")

    svc.client = FailingRefundClient(is_mock=True)

    with pytest.raises(PaymentGatewayError):
        svc.process_refund(
            booking_reference=ref,
            token=raw_token,
            reason="Customer requested cancellation",
            idempotency_key=f"idemp_{uuid.uuid4().hex[:8]}"
        )

    # Check that failed refund is recorded
    failed_refunds = refund_repo.find_failed_refunds()
    assert any(r["bookingReference"] == ref and r["status"] == "failed" for r in failed_refunds)

    # Check that payment is flagged for review
    updated_pay = payment_repo.find_by_payment_id(payment_id)
    assert updated_pay.get("needsReview") is True

    # Test retry_refund clears needsReview once successful
    class SuccessRetryClient(RazorpayClient):
        def create_refund(self, payment_id, amount=None, notes=None):
            return {"id": f"rfnd_retry_{uuid.uuid4().hex[:8]}", "status": "processed"}

    svc.client = SuccessRetryClient(is_mock=True)
    target_failed = [r for r in failed_refunds if r["bookingReference"] == ref][0]
    retry_res = svc.retry_refund(str(target_failed["_id"]))
    assert retry_res["status"] == "processed"

    updated_pay_after = payment_repo.find_by_payment_id(payment_id)
    assert updated_pay_after.get("needsReview") is False

def test_reconcile_pending_payments(payment_fixture):
    """Verifies that reconcile_pending_payments detects stale payments and transitions them."""
    svc = payment_fixture["service"]
    booking_repo = payment_fixture["booking_repo"]
    payment_repo = payment_fixture["payment_repo"]

    now_u = now_utc()
    stale_time = now_u - timedelta(minutes=30)
    ref = f"JBX-T-{uuid.uuid4().hex[:6]}"

    booking_id = ObjectId()
    booking_doc = {
        "_id": booking_id,
        "bookingReference": ref,
        "accessTokenHash": "hash",
        "bookingStatus": "hold_placed",
        "paymentStatus": "unpaid",
        "pricing": {"totalAmountMinor": 50000},
        "startAt": now_u + timedelta(days=2),
        "endAt": now_u + timedelta(days=2, hours=2),
        "roomId": "main",
        "createdAt": stale_time,
        "updatedAt": stale_time,
    }
    booking_repo.insert(booking_doc)

    order_id = f"order_{uuid.uuid4().hex[:8]}"
    payment_id = f"pay_{uuid.uuid4().hex[:8]}"
    payment_doc = {
        "_id": ObjectId(),
        "bookingId": booking_id,
        "bookingReference": ref,
        "provider": "razorpay",
        "providerOrderId": order_id,
        "providerPaymentId": payment_id,
        "amountMinor": 50000,
        "status": "created",
        "createdAt": stale_time,
        "updatedAt": stale_time,
    }
    payment_repo.insert(payment_doc)

    class MockReconcileClient(RazorpayClient):
        def fetch_payment(self, pid, expected_order_id=None, expected_amount=None):
            return {
                "id": pid,
                "entity": "payment",
                "amount": 50000,
                "currency": "INR",
                "status": "captured",
                "order_id": order_id,
                "method": "upi"
            }

    svc.client = MockReconcileClient(is_mock=True)

    reconcile_res = svc.reconcile_pending_payments(age_minutes=15)
    assert reconcile_res["reconciledCount"] >= 1

    updated_booking = booking_repo.find_by_reference(ref)
    assert updated_booking["bookingStatus"] == "confirmed"
    assert updated_booking["paymentStatus"] == "paid"
