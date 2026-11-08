import hashlib
import hmac
import json
import pytest
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from app import create_app
from app.config import Config
from app.utils.datetime_utils import now_utc
from app.services.payment_service import RazorpayClient, PaymentService
from app.repositories import (
    BookingRepository,
    PaymentRepository,
    RefundRepository,
    WebhookEventRepository,
    SlotClaimRepository,
    OfferRepository,
    OfferRedemptionRepository,
    IdempotencyRepository,
)

# Test HMAC Secrets
TEST_KEY_ID = "rzp_test_example"
TEST_KEY_SECRET = "secret_joybox_key_98765"
TEST_WEBHOOK_SECRET = "webhook_secret_joybox_abcde"

class PaymentInMemoryCollection:
    def __init__(self, name=""):
        self.name = name
        self.docs = []

    def find(self, query=None, projection=None):
        query = query or {}
        class MockCursor:
            def __init__(self, docs):
                self._docs = docs
            def sort(self, field, direction):
                return self
            def __iter__(self):
                return iter(self._docs)
            def __list__(self):
                return list(self._docs)

        results = [dict(d) for d in self.docs if self._matches(d, query)]
        return MockCursor(results)

    def find_one(self, query=None, sort=None):
        query = query or {}
        for d in self.docs:
            if self._matches(d, query):
                return dict(d)
        return None

    def insert_one(self, doc):
        d = dict(doc)
        if "_id" not in d:
            d["_id"] = ObjectId()

        # Enforce unique index on (roomId, slotStart) for slotClaims
        if self.name == "slotClaims":
            for existing in self.docs:
                if existing.get("roomId") == d.get("roomId") and existing.get("slotStart") == d.get("slotStart"):
                    from pymongo.errors import DuplicateKeyError
                    raise DuplicateKeyError(f"Duplicate key on (roomId, slotStart): {d.get('slotStart')}")

        # Enforce unique index for webhookEvents
        if self.name == "webhookEvents":
            for existing in self.docs:
                if existing.get("provider") == d.get("provider") and existing.get("eventId") == d.get("eventId"):
                    from pymongo.errors import DuplicateKeyError
                    raise DuplicateKeyError(f"Duplicate webhook event: {d.get('eventId')}")

        # Enforce unique index for idempotencyKeys
        if self.name == "idempotencyKeys":
            for existing in self.docs:
                if existing.get("key") == d.get("key") and existing.get("endpoint") == d.get("endpoint"):
                    from pymongo.errors import DuplicateKeyError
                    raise DuplicateKeyError(f"Duplicate idempotency key: {d.get('key')}")

        self.docs.append(d)
        class Res:
            inserted_id = d["_id"]
        return Res()

    def find_one_and_update(self, query, update, upsert=False, return_document=None):
        for d in self.docs:
            if self._matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                return dict(d)
        if upsert:
            new_doc = dict(query)
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    new_doc[k] = v
            self.docs.append(new_doc)
            return dict(new_doc)
        return None

    def update_one(self, query, update):
        for d in self.docs:
            if self._matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                break

    def update_many(self, query, update):
        matched_count = 0
        for d in self.docs:
            if self._matches(d, query):
                matched_count += 1
                if "$set" in update:
                    d.update(update["$set"])
        class Res:
            modified_count = matched_count
        return Res()

    def delete_many(self, query):
        initial = len(self.docs)
        self.docs = [d for d in self.docs if not self._matches(d, query)]
        class Res:
            deleted_count = initial - len(self.docs)
        return Res()

    def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                del self.docs[i]
                break

    def _matches(self, doc, query):
        for k, v in query.items():
            if k == "$expr":
                continue
            elif k == "$or":
                if not any(self._matches(doc, c) for c in v):
                    return False
            elif isinstance(v, dict):
                if "$in" in v and doc.get(k) not in v["$in"]:
                    return False
                if "$lt" in v and not (doc.get(k) < v["$lt"]):
                    return False
                if "$gt" in v and not (doc.get(k) > v["$gt"]):
                    return False
                if "$lte" in v and not (doc.get(k) <= v["$lte"]):
                    return False
                if "$gte" in v and not (doc.get(k) >= v["$gte"]):
                    return False
            elif doc.get(k) != v:
                return False
        return True


class PaymentMockDB:
    def __init__(self):
        self.bookings = PaymentInMemoryCollection("bookings")
        self.payments = PaymentInMemoryCollection("payments")
        self.refunds = PaymentInMemoryCollection("refunds")
        self.webhookEvents = PaymentInMemoryCollection("webhookEvents")
        self.slotClaims = PaymentInMemoryCollection("slotClaims")
        self.offers = PaymentInMemoryCollection("offers")
        self.offerRedemptions = PaymentInMemoryCollection("offerRedemptions")
        self.idempotencyKeys = PaymentInMemoryCollection("idempotencyKeys")
        self.rateLimits = PaymentInMemoryCollection("rateLimits")
        self.packages = PaymentInMemoryCollection("packages")
        self.addOns = PaymentInMemoryCollection("addOns")


@pytest.fixture
def payment_app():
    test_cfg = {
        "TESTING": True,
        "DEBUG": True,
        "PAYMENTS_ENABLED": True,
        "RAZORPAY_KEY_ID": TEST_KEY_ID,
        "RAZORPAY_KEY_SECRET": TEST_KEY_SECRET,
        "RAZORPAY_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET,
        "REFUND_WINDOW_FULL_HOURS": 48,
        "REFUND_WINDOW_PARTIAL_HOURS": 24,
        "REFUND_WINDOW_PARTIAL_PERCENT": 50,
        "REFUND_MIN_NOTICE_HOURS": 24,
    }
    app = create_app(test_config=test_cfg)
    mock_db = PaymentMockDB()
    app.extensions["mongo_db"] = mock_db
    return app


@pytest.fixture
def client(payment_app):
    return payment_app.test_client()


def helper_create_booking(mock_db, hours_ahead=72, amount_minor=99900):
    start_utc = now_utc() + timedelta(hours=hours_ahead)
    end_utc = start_utc + timedelta(hours=2)
    raw_token = "secret_access_token_joybox_test_12345"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    booking_id = ObjectId()
    booking_ref = f"JBX-2026-{mock_db.bookings.docs.__len__() + 1:04d}"

    booking_doc = {
        "_id": booking_id,
        "bookingReference": booking_ref,
        "accessTokenHash": token_hash,
        "roomId": "main",
        "packageCode": "basic",
        "packageName": "Basic Celebration",
        "durationHours": 2,
        "startAt": start_utc,
        "endAt": end_utc,
        "pricing": {
            "totalAmountMinor": amount_minor,
            "totalRupees": amount_minor / 100.0,
            "currency": "INR"
        },
        "customer": {
            "name": "Ravi Kumar",
            "phone": "9876543210",
            "email": "ravi@example.com"
        },
        "bookingStatus": "pending_payment",
        "paymentStatus": "unpaid",
        "createdAt": now_utc(),
        "updatedAt": now_utc()
    }
    mock_db.bookings.insert_one(booking_doc)

    # Claim slots
    mock_db.slotClaims.insert_one({
        "roomId": "main",
        "slotStart": start_utc,
        "slotEnd": end_utc,
        "isBuffer": False,
        "ownerType": "booking",
        "ownerId": booking_id,
        "createdAt": now_utc(),
        "expiresAt": None
    })

    return booking_ref, raw_token, booking_doc


# ---------------------------------------------------------
# GATE A: ORDER CREATION TESTS
# ---------------------------------------------------------

def test_create_order_unauthorized_token_returns_404(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, _, _ = helper_create_booking(mock_db)

    # Wrong token
    res = client.post("/api/payments/create-order", json={
        "bookingReference": ref,
        "token": "wrong_token_12345678"
    })
    assert res.status_code == 404
    assert res.json["error"]["code"] == "NOT_FOUND"


def test_create_order_nonexistent_booking_returns_404(client):
    res = client.post("/api/payments/create-order", json={
        "bookingReference": "JBX-9999-9999",
        "token": "some_random_token_12345"
    })
    assert res.status_code == 404


def test_create_order_success(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db, amount_minor=99900)

    res = client.post("/api/payments/create-order", json={
        "bookingReference": ref,
        "token": token
    })
    assert res.status_code == 201
    data = res.json["data"]
    assert data["bookingReference"] == ref
    assert data["amountMinor"] == 99900
    assert data["currency"] == "INR"
    assert data["keyId"] == TEST_KEY_ID
    assert data["orderId"].startswith("order_")

    # Payment record persisted in DB
    payment_record = mock_db.payments.find_one({"bookingReference": ref})
    assert payment_record is not None
    assert payment_record["providerOrderId"] == data["orderId"]
    assert payment_record["status"] == "created"


def test_create_order_trusts_only_server_pricing(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, _ = helper_create_booking(mock_db, amount_minor=150000)

    # 1. Unknown field tampering (e.g. injected amountMinor) is rejected by strict schema (BUG-09)
    res_tamper = client.post("/api/payments/create-order", json={
        "bookingReference": ref,
        "token": token,
        "amountMinor": 100  # Attempting tampering
    })
    assert res_tamper.status_code == 400
    assert "amountMinor" in res_tamper.json["error"]["details"]

    # 2. Server creates order using strictly server-side booking pricing (150000 paise)
    res = client.post("/api/payments/create-order", json={
        "bookingReference": ref,
        "token": token
    })
    assert res.status_code == 201
    assert res.json["data"]["amountMinor"] == 150000


def test_create_order_cancelled_or_paid_booking_rejected(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db)

    # Update to cancelled
    mock_db.bookings.update_one({"_id": doc["_id"]}, {"$set": {"bookingStatus": "cancelled"}})
    res = client.post("/api/payments/create-order", json={"bookingReference": ref, "token": token})
    assert res.status_code == 409
    assert res.json["error"]["code"] == "INVALID_STATE"

    # Update to confirmed + paid
    mock_db.bookings.update_one({"_id": doc["_id"]}, {"$set": {"bookingStatus": "confirmed", "paymentStatus": "paid"}})
    res2 = client.post("/api/payments/create-order", json={"bookingReference": ref, "token": token})
    assert res2.status_code == 409


# ---------------------------------------------------------
# GATE B: PAYMENT VERIFICATION & SIGNATURE TESTS
# ---------------------------------------------------------

def test_verify_payment_real_hmac_success(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db)

    # First create order
    order_res = client.post("/api/payments/create-order", json={"bookingReference": ref, "token": token})
    order_id = order_res.json["data"]["orderId"]
    payment_id = "pay_joybox_test_998877"

    # Generate real HMAC-SHA256 signature
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    real_sig = hmac.new(TEST_KEY_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    # Verify payment
    verify_res = client.post("/api/payments/verify", json={
        "bookingReference": ref,
        "token": token,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": real_sig
    })
    assert verify_res.status_code == 200
    assert verify_res.json["data"]["bookingStatus"] == "confirmed"
    assert verify_res.json["data"]["paymentStatus"] == "paid"

    # Verify DB transition
    updated_b = mock_db.bookings.find_one({"bookingReference": ref})
    assert updated_b["bookingStatus"] == "confirmed"
    assert updated_b["paymentStatus"] == "paid"
    assert updated_b["razorpayPaymentId"] == payment_id

    updated_p = mock_db.payments.find_one({"providerOrderId": order_id})
    assert updated_p["status"] == "captured"
    assert updated_p["providerPaymentId"] == payment_id


def test_verify_payment_tampered_signature_fails(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db)

    order_res = client.post("/api/payments/create-order", json={"bookingReference": ref, "token": token})
    order_id = order_res.json["data"]["orderId"]
    payment_id = "pay_test_tampered_1"

    # Send tampered signature
    res = client.post("/api/payments/verify", json={
        "bookingReference": ref,
        "token": token,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    })
    assert res.status_code == 400
    assert res.json["error"]["code"] == "PAYMENT_VERIFICATION_FAILED"


def test_verify_payment_wrong_secret_fails(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db)

    order_res = client.post("/api/payments/create-order", json={"bookingReference": ref, "token": token})
    order_id = order_res.json["data"]["orderId"]
    payment_id = "pay_test_wrong_secret"

    # Sign with attacker's secret
    attacker_sig = hmac.new(b"attacker_secret_key", f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()

    res = client.post("/api/payments/verify", json={
        "bookingReference": ref,
        "token": token,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": attacker_sig
    })
    assert res.status_code == 400
    assert res.json["error"]["code"] == "PAYMENT_VERIFICATION_FAILED"


def test_verify_payment_idempotent_replay(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db)

    order_res = client.post("/api/payments/create-order", json={"bookingReference": ref, "token": token})
    order_id = order_res.json["data"]["orderId"]
    payment_id = "pay_replay_1"

    payload = f"{order_id}|{payment_id}".encode()
    sig = hmac.new(TEST_KEY_SECRET.encode(), payload, hashlib.sha256).hexdigest()

    # First verify
    res1 = client.post("/api/payments/verify", json={
        "bookingReference": ref,
        "token": token,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": sig
    })
    assert res1.status_code == 200

    # Second verify (replay)
    res2 = client.post("/api/payments/verify", json={
        "bookingReference": ref,
        "token": token,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": sig
    })
    assert res2.status_code == 200
    assert res2.json["data"]["bookingStatus"] == "confirmed"


def test_verify_payment_late_payment_slot_taken_triggers_auto_refund(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db)

    order_res = client.post("/api/payments/create-order", json={"bookingReference": ref, "token": token})
    order_id = order_res.json["data"]["orderId"]
    payment_id = "pay_late_taken_1"

    # Simulate slot being claimed by another customer while user was on checkout page
    mock_db.slotClaims.docs.clear()
    other_booking_id = ObjectId()
    mock_db.slotClaims.insert_one({
        "roomId": "main",
        "slotStart": doc["startAt"],
        "slotEnd": doc["endAt"],
        "isBuffer": False,
        "ownerType": "booking",
        "ownerId": other_booking_id,
        "createdAt": now_utc(),
        "expiresAt": None
    })

    sig = hmac.new(TEST_KEY_SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()

    # Verification must detect slot conflict and trigger auto-refund
    res = client.post("/api/payments/verify", json={
        "bookingReference": ref,
        "token": token,
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": sig
    })
    assert res.status_code == 409
    assert res.json["error"]["code"] == "LATE_PAYMENT_SLOT_TAKEN"

    # Verify auto refund created
    refund = mock_db.refunds.find_one({"bookingReference": ref})
    assert refund is not None
    assert refund["status"] == "processed"
    assert refund["amountMinor"] == doc["pricing"]["totalAmountMinor"]

    # Verify booking marked cancelled
    updated_b = mock_db.bookings.find_one({"bookingReference": ref})
    assert updated_b["bookingStatus"] == "cancelled_due_to_conflict"
    assert updated_b["paymentStatus"] == "refunded"


# ---------------------------------------------------------
# GATE C: WEBHOOK INTEGRATION & DEDUPLICATION TESTS
# ---------------------------------------------------------

def test_webhook_hmac_verification_valid(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db)

    payload_dict = {
        "event_id": "evt_webhook_test_001",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_hook_123",
                    "order_id": "order_hook_123",
                    "amount": 99900,
                    "notes": {"bookingReference": ref}
                }
            }
        }
    }
    raw_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = hmac.new(TEST_WEBHOOK_SECRET.encode(), raw_bytes, hashlib.sha256).hexdigest()

    res = client.post(
        "/api/payments/webhook",
        data=raw_bytes,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig}
    )
    assert res.status_code == 200
    assert res.json["data"]["status"] == "processed"
    assert res.json["data"]["eventId"] == "evt_webhook_test_001"

    # Booking was updated
    updated_b = mock_db.bookings.find_one({"bookingReference": ref})
    assert updated_b["bookingStatus"] == "confirmed"
    assert updated_b["paymentStatus"] == "paid"


def test_webhook_tampered_body_fails(client):
    payload_dict = {"event_id": "evt_tampered", "event": "payment.captured"}
    raw_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = hmac.new(TEST_WEBHOOK_SECRET.encode(), raw_bytes, hashlib.sha256).hexdigest()

    # Tamper 1 character
    tampered_bytes = raw_bytes.replace(b"evt_tampered", b"evt_tamperX")
    res = client.post(
        "/api/payments/webhook",
        data=tampered_bytes,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig}
    )
    assert res.status_code == 400
    assert res.json["error"]["code"] == "PAYMENT_VERIFICATION_FAILED"


def test_webhook_deduplication(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db)

    payload_dict = {
        "event_id": "evt_dedup_001",
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_dedup",
                    "order_id": "order_dedup",
                    "amount": 99900,
                    "notes": {"bookingReference": ref}
                }
            }
        }
    }
    raw_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = hmac.new(TEST_WEBHOOK_SECRET.encode(), raw_bytes, hashlib.sha256).hexdigest()

    # First delivery
    res1 = client.post(
        "/api/payments/webhook",
        data=raw_bytes,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig}
    )
    assert res1.status_code == 200
    assert res1.json["data"]["status"] == "processed"

    # Second delivery with same event_id
    res2 = client.post(
        "/api/payments/webhook",
        data=raw_bytes,
        headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig}
    )
    assert res2.status_code == 200
    assert res2.json["data"]["status"] == "already_processed"


# ---------------------------------------------------------
# GATE D: REFUND TESTS & CANCELLATION POLICIES
# ---------------------------------------------------------

def test_refund_unpaid_booking_rejected(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, _ = helper_create_booking(mock_db)

    res = client.post("/api/payments/refund", json={
        "bookingReference": ref,
        "token": token
    })
    assert res.status_code == 409
    assert res.json["error"]["code"] == "INVALID_STATE"


def test_refund_policy_full_window(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    # 72 hours ahead: > 48 hours -> 100% refund
    ref, token, doc = helper_create_booking(mock_db, hours_ahead=72, amount_minor=100000)

    # Set payment to paid
    mock_db.bookings.update_one({"_id": doc["_id"]}, {"$set": {"paymentStatus": "paid", "bookingStatus": "confirmed"}})
    mock_db.payments.insert_one({
        "bookingId": doc["_id"],
        "bookingReference": ref,
        "provider": "razorpay",
        "providerOrderId": "order_refund_1",
        "providerPaymentId": "pay_refund_1",
        "amountMinor": 100000,
        "amountRefundedMinor": 0,
        "status": "captured",
        "createdAt": now_utc()
    })

    res = client.post("/api/payments/refund", json={
        "bookingReference": ref,
        "token": token,
        "reason": "Change of plans"
    })
    assert res.status_code == 200
    data = res.json["data"]
    assert data["amountMinor"] == 100000
    assert data["refundStatus"] == "refunded"

    # Booking cancelled & slots released
    updated_b = mock_db.bookings.find_one({"bookingReference": ref})
    assert updated_b["bookingStatus"] == "cancelled"
    assert updated_b["paymentStatus"] == "refunded"
    assert len(mock_db.slotClaims.docs) == 0


def test_refund_policy_partial_window(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    # 30 hours ahead: between 24 and 48 hours -> 50% refund
    ref, token, doc = helper_create_booking(mock_db, hours_ahead=30, amount_minor=100000)

    mock_db.bookings.update_one({"_id": doc["_id"]}, {"$set": {"paymentStatus": "paid", "bookingStatus": "confirmed"}})
    mock_db.payments.insert_one({
        "bookingId": doc["_id"],
        "bookingReference": ref,
        "provider": "razorpay",
        "providerOrderId": "order_refund_part",
        "providerPaymentId": "pay_refund_part",
        "amountMinor": 100000,
        "amountRefundedMinor": 0,
        "status": "captured",
        "createdAt": now_utc()
    })

    res = client.post("/api/payments/refund", json={
        "bookingReference": ref,
        "token": token
    })
    assert res.status_code == 200
    data = res.json["data"]
    assert data["amountMinor"] == 50000  # 50% of 100000
    assert data["refundStatus"] == "partially_refunded"


def test_refund_policy_late_cancellation_rejected(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    # 10 hours ahead: < 24 hours -> non-refundable
    ref, token, doc = helper_create_booking(mock_db, hours_ahead=10, amount_minor=100000)

    mock_db.bookings.update_one({"_id": doc["_id"]}, {"$set": {"paymentStatus": "paid", "bookingStatus": "confirmed"}})
    mock_db.payments.insert_one({
        "bookingId": doc["_id"],
        "bookingReference": ref,
        "provider": "razorpay",
        "providerOrderId": "order_refund_late",
        "providerPaymentId": "pay_refund_late",
        "amountMinor": 100000,
        "amountRefundedMinor": 0,
        "status": "captured",
        "createdAt": now_utc()
    })

    res = client.post("/api/payments/refund", json={
        "bookingReference": ref,
        "token": token
    })
    assert res.status_code == 400
    assert res.json["error"]["code"] == "REFUND_NOT_ALLOWED"


def test_refund_exceeds_refundable_balance_rejected(client, payment_app):
    mock_db = payment_app.extensions["mongo_db"]
    ref, token, doc = helper_create_booking(mock_db, hours_ahead=72, amount_minor=100000)

    mock_db.bookings.update_one({"_id": doc["_id"]}, {"$set": {"paymentStatus": "paid", "bookingStatus": "confirmed"}})
    mock_db.payments.insert_one({
        "bookingId": doc["_id"],
        "bookingReference": ref,
        "provider": "razorpay",
        "providerOrderId": "order_refund_exceed",
        "providerPaymentId": "pay_refund_exceed",
        "amountMinor": 100000,
        "amountRefundedMinor": 0,
        "status": "captured",
        "createdAt": now_utc()
    })

    res = client.post("/api/payments/refund", json={
        "bookingReference": ref,
        "token": token,
        "amountMinor": 150000  # Exceeds total
    })
    assert res.status_code == 400
    assert res.json["error"]["code"] == "REFUND_NOT_ALLOWED"
