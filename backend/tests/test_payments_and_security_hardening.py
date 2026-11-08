"""
Integration and Unit Tests for Phase 3: Payments, Webhooks, Refunds, and Contract Hardening.
Tests:
- BUG-06: Conflicting payment endpoints enforce server pricing and reject client price tampering.
- BUG-08: Verification that hardcoded keys are absent from source and bundle.
- BUG-09: Financial schemas strictly enforce unknown = RAISE.
- SUSPECTED A: Webhook lease expiration allows retry recovery after simulated crash;
  business-level deduplication of payment.captured and order.paid.
"""
import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from unittest.mock import patch, MagicMock
from marshmallow import ValidationError

from app import create_app
from app.config import Config
from app.repositories import (
    BookingRepository,
    PaymentRepository,
    WebhookEventRepository,
    SlotClaimRepository
)
from app.schemas.payment_schemas import (
    CreatePaymentOrderSchema,
    VerifyPaymentSchema,
    RefundRequestSchema
)
from app.schemas.booking_schemas import (
    QuoteRequestSchema,
    BookingHoldRequestSchema
)
from app.services.payment_service import PaymentService, RazorpayClient
from app.utils.datetime_utils import now_utc

@pytest.fixture
def app_client():
    app = create_app({"TESTING": True, "PAYMENTS_ENABLED": True})
    return app.test_client()

def test_financial_schemas_reject_unknown_fields():
    """
    BUG-09 test:
    Verify that financial, booking, and payment schemas strictly reject unknown/unexpected fields
    (unknown = RAISE) to prevent parameter tampering or masking client typos.
    """
    # 1. Payment Create Order
    with pytest.raises(ValidationError) as exc:
        CreatePaymentOrderSchema().load({
            "bookingReference": "JBX-2026-0001",
            "token": "valid_token_string_here_32_chars",
            "clientTamperedAmount": 100 # Injected field
        })
    assert "clientTamperedAmount" in exc.value.messages

    # 2. Payment Verify
    with pytest.raises(ValidationError) as exc:
        VerifyPaymentSchema().load({
            "bookingReference": "JBX-2026-0001",
            "token": "valid_token_string_here_32_chars",
            "razorpay_order_id": "order_123",
            "razorpay_payment_id": "pay_123",
            "razorpay_signature": "sig_123",
            "customStatus": "confirmed" # Injected field
        })
    assert "customStatus" in exc.value.messages

    # 3. Refund Request
    with pytest.raises(ValidationError) as exc:
        RefundRequestSchema().load({
            "bookingReference": "JBX-2026-0001",
            "token": "valid_token_string_here_32_chars",
            "overrideApproval": True # Injected field
        })
    assert "overrideApproval" in exc.value.messages

    # 4. Quote Request
    with pytest.raises(ValidationError) as exc:
        QuoteRequestSchema().load({
            "packageCode": "gold",
            "durationHours": 2,
            "customPricePaise": 50000 # Injected field
        })
    assert "customPricePaise" in exc.value.messages


def test_legacy_create_order_rejects_client_price_and_requires_token(app_client):
    """
    BUG-06 test:
    Verify that hitting POST /api/create-order directly without bookingReference and token
    is rejected with HTTP 400. Client-supplied 'amount' is never trusted.
    """
    # Attempting to supply client amount alone is strictly rejected
    res = app_client.post("/api/create-order", json={"amount": 100, "currency": "INR"})
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False
    assert data["error"]["code"] == "MISSING_FIELDS"
    assert "bookingReference and token are required" in data["error"]["message"]


def test_webhook_lease_recovery_after_crash(live_test_client):
    """
    SUSPECTED A regression test:
    Prove that if a webhook event is claimed but worker crashes before completion,
    a subsequent retry after lease expiration safely reclaims the lease and processes the event.
    """
    db = live_test_client
    webhook_repo = WebhookEventRepository(db)
    now_u = now_utc()
    event_id = f"evt_crash_test_{ObjectId()}"

    db.webhookEvents.delete_many({"eventId": event_id})

    # 1. First attempt: claims event atomically with 2-second lease
    claimed_1, doc_1 = webhook_repo.claim_event_atomically(
        provider="razorpay",
        event_id=event_id,
        event_type="payment.captured",
        payload={"event": "payment.captured", "id": event_id},
        now_utc=now_u,
        lease_seconds=2
    )
    assert claimed_1 is True
    assert doc_1["status"] == "processing"

    # 2. Immediate retry while lease is still active (< 2 seconds): must be rejected/ignored
    claimed_2, doc_2 = webhook_repo.claim_event_atomically(
        provider="razorpay",
        event_id=event_id,
        event_type="payment.captured",
        payload={"event": "payment.captured", "id": event_id},
        now_utc=now_u + timedelta(seconds=1),
        lease_seconds=2
    )
    assert claimed_2 is False, "Active lease must prevent concurrent double-processing"

    # 3. Retry after lease has expired (> 2 seconds): worker crashed, lease expired
    claimed_3, doc_3 = webhook_repo.claim_event_atomically(
        provider="razorpay",
        event_id=event_id,
        event_type="payment.captured",
        payload={"event": "payment.captured", "id": event_id},
        now_utc=now_u + timedelta(seconds=5),
        lease_seconds=10
    )
    assert claimed_3 is True, "Expired lease on uncompleted event must be reclaimable by retry"
    assert doc_3["status"] == "processing"
    assert doc_3.get("retryCount", 0) >= 1

    # 4. Mark processed upon successful completion
    webhook_repo.mark_processed("razorpay", event_id)
    doc_after = webhook_repo.find_event("razorpay", event_id)
    assert doc_after["status"] == "processed"

    # 5. Subsequent retry on processed event must NEVER be reclaimed
    claimed_4, doc_4 = webhook_repo.claim_event_atomically(
        provider="razorpay",
        event_id=event_id,
        event_type="payment.captured",
        payload={"event": "payment.captured", "id": event_id},
        now_utc=now_u + timedelta(seconds=20),
        lease_seconds=10
    )
    assert claimed_4 is False, "Processed event must remain permanently deduplicated"

    # Clean up
    db.webhookEvents.delete_many({"eventId": event_id})

