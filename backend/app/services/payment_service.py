import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from bson import ObjectId
import requests
from requests.auth import HTTPBasicAuth

from ..config import Config
from ..utils.datetime_utils import now_utc, generate_slot_claim_intervals, ensure_utc
from ..utils.exceptions import (
    ResourceNotFoundError,
    InvalidBookingStateError,
    PaymentVerificationError,
    PaymentGatewayError,
    RefundNotAllowedError,
    LatePaymentSlotTakenError,
    IdempotencyConflictError,
    IdempotencyPayloadMismatchError,
)

logger = logging.getLogger(__name__)

class ConfigAdapter:
    def __init__(self, config_obj):
        self._cfg = config_obj

    def __getattr__(self, name):
        if hasattr(self._cfg, "get"):
            val = self._cfg.get(name)
            if val is not None and val != "":
                return val
        if hasattr(self._cfg, name):
            val = getattr(self._cfg, name)
            if val is not None and val != "":
                return val
        if hasattr(Config, name):
            return getattr(Config, name)
        raise AttributeError(f"Configuration key '{name}' not found.")

    def get(self, name, default=None):
        try:
            return getattr(self, name)
        except AttributeError:
            return default


class RazorpayClient:
    """
    Direct REST Razorpay integration client using standard requests and HMAC.
    Implements full payment lifecycle without requiring external SDK binaries.
    """
    def __init__(self, key_id: str = None, key_secret: str = None, api_base: str = None, is_mock: bool = False):
        self.key_id = key_id or Config.RAZORPAY_KEY_ID
        self.key_secret = key_secret or Config.RAZORPAY_KEY_SECRET
        self.api_base = (api_base or Config.RAZORPAY_API_BASE).rstrip("/")
        self.is_mock = is_mock
        self.auth = HTTPBasicAuth(self.key_id, self.key_secret) if self.key_id and self.key_secret else None

    def create_order(self, amount: int, currency: str = "INR", receipt: str = None, notes: dict = None) -> dict:
        """Creates an order on Razorpay."""
        if self.is_mock or not self.key_id or not self.key_secret or "replace-with" in self.key_id:
            mock_order_id = f"order_{hashlib.md5(f'{receipt}_{amount}'.encode()).hexdigest()[:14]}"
            return {
                "id": mock_order_id,
                "entity": "order",
                "amount": amount,
                "amount_paid": 0,
                "amount_due": amount,
                "currency": currency,
                "receipt": receipt,
                "status": "created",
                "notes": notes or {}
            }

        url = f"{self.api_base}/orders"
        payload = {
            "amount": amount,
            "currency": currency,
            "receipt": receipt or "",
            "notes": notes or {}
        }
        try:
            resp = requests.post(url, json=payload, auth=self.auth, timeout=10)
            if resp.status_code not in (200, 201):
                logger.error(f"Razorpay order creation failed: {resp.status_code} {resp.text}")
                raise PaymentGatewayError(f"Razorpay order creation error: {resp.text}")
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Razorpay network error on order creation: {str(e)}")
            raise PaymentGatewayError(f"Network error communicating with payment gateway: {str(e)}")

    def fetch_payment(self, payment_id: str, expected_order_id: str = None, expected_amount: int = None) -> dict:
        """Fetches payment details by payment ID."""
        if self.is_mock or not self.key_id or not self.key_secret or "replace-with" in self.key_id:
            return {
                "id": payment_id,
                "entity": "payment",
                "amount": expected_amount or 0,
                "currency": "INR",
                "status": "captured",
                "order_id": expected_order_id,
                "method": "upi"
            }

        url = f"{self.api_base}/payments/{payment_id}"
        try:
            resp = requests.get(url, auth=self.auth, timeout=10)
            if resp.status_code != 200:
                logger.error(f"Razorpay fetch payment failed: {resp.status_code} {resp.text}")
                raise PaymentGatewayError(f"Razorpay payment fetch error: {resp.text}")
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Razorpay network error on fetch payment: {str(e)}")
            raise PaymentGatewayError(f"Network error communicating with payment gateway: {str(e)}")

    def create_refund(self, payment_id: str, amount: int = None, notes: dict = None) -> dict:
        """Creates a refund for a captured payment."""
        if self.is_mock or not self.key_id or not self.key_secret or "replace-with" in self.key_id:
            mock_refund_id = f"rfnd_{hashlib.md5(f'{payment_id}_{amount}'.encode()).hexdigest()[:14]}"
            return {
                "id": mock_refund_id,
                "entity": "refund",
                "amount": amount,
                "currency": "INR",
                "payment_id": payment_id,
                "status": "processed",
                "notes": notes or {}
            }

        url = f"{self.api_base}/payments/{payment_id}/refund"
        payload = {}
        if amount is not None:
            payload["amount"] = amount
        if notes:
            payload["notes"] = notes

        try:
            resp = requests.post(url, json=payload, auth=self.auth, timeout=10)
            if resp.status_code not in (200, 201):
                logger.error(f"Razorpay refund creation failed: {resp.status_code} {resp.text}")
                raise PaymentGatewayError(f"Razorpay refund error: {resp.text}")
            return resp.json()
        except requests.RequestException as e:
            logger.error(f"Razorpay network error on refund creation: {str(e)}")
            raise PaymentGatewayError(f"Network error communicating with payment gateway: {str(e)}")

    @staticmethod
    def verify_payment_signature(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
        """
        Cryptographic verification of Razorpay checkout payment signature.
        HMAC-SHA256(order_id + '|' + payment_id, secret)
        """
        if not order_id or not payment_id or not signature or not secret:
            return False
        payload = f"{order_id}|{payment_id}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, signature)

    @staticmethod
    def verify_webhook_signature(raw_body_bytes: bytes, signature: str, webhook_secret: str) -> bool:
        """
        Cryptographic verification of Razorpay webhook signature over raw payload bytes.
        HMAC-SHA256(raw_body_bytes, webhook_secret)
        """
        if not raw_body_bytes or not signature or not webhook_secret:
            return False
        expected_sig = hmac.new(webhook_secret.encode("utf-8"), raw_body_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, signature)


class PaymentService:
    def __init__(
        self,
        booking_repo,
        payment_repo,
        refund_repo,
        webhook_repo,
        slot_claim_repo=None,
        offer_repo=None,
        offer_redemption_repo=None,
        idempotency_repo=None,
        hold_repo=None,
        config=None,
        razorpay_client=None,
    ):
        self.booking_repo = booking_repo
        self.payment_repo = payment_repo
        self.refund_repo = refund_repo
        self.webhook_repo = webhook_repo
        self.slot_claim_repo = slot_claim_repo
        self.offer_repo = offer_repo
        self.offer_redemption_repo = offer_redemption_repo
        self.idempotency_repo = idempotency_repo
        self.hold_repo = hold_repo
        self.config = ConfigAdapter(config or Config)
        is_mock = bool(getattr(self.config, "TESTING", False) or getattr(self.config, "RAZORPAY_MOCK", False))
        self.client = razorpay_client or RazorpayClient(
            key_id=getattr(self.config, "RAZORPAY_KEY_ID", ""),
            key_secret=getattr(self.config, "RAZORPAY_KEY_SECRET", ""),
            api_base=getattr(self.config, "RAZORPAY_API_BASE", "https://api.razorpay.com/v1"),
            is_mock=is_mock,
        )

    def _verify_booking_token(self, booking: dict, token: str):
        if not token or not token.strip():
            raise ResourceNotFoundError(f"Booking reference '{booking.get('bookingReference')}' not found.")
        token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
        stored_hash = booking.get("accessTokenHash", "")
        if not stored_hash or not hmac.compare_digest(token_hash, stored_hash):
            raise ResourceNotFoundError(f"Booking reference '{booking.get('bookingReference')}' not found.")

    def create_order(self, booking_reference: str, token: str, idempotency_key: str = None) -> dict:
        """
        Creates a Razorpay payment order for an existing booking.
        Trusts ONLY server-calculated pricing from the database.
        Extends the hold payment window if configured.
        """
        booking = self.booking_repo.find_by_reference(booking_reference)
        if not booking:
            raise ResourceNotFoundError(f"Booking reference '{booking_reference}' not found.")

        self._verify_booking_token(booking, token)

        if booking.get("bookingStatus") == "cancelled":
            raise InvalidBookingStateError("Cannot initiate payment for a cancelled booking.")
        if booking.get("paymentStatus") == "paid":
            raise InvalidBookingStateError("Booking is already fully paid.")

        endpoint = "POST /api/payments/create-order"
        req_hash = hashlib.sha256(f"{booking_reference}:{idempotency_key}".encode()).hexdigest()

        if idempotency_key and self.idempotency_repo:
            existing = self.idempotency_repo.get_key(idempotency_key, endpoint)
            if existing:
                if existing.get("status") == "completed":
                    return existing.get("response", {})
                elif existing.get("status") == "in_progress":
                    raise IdempotencyConflictError("Payment order creation already in progress.")

            self.idempotency_repo.insert_in_progress(
                idempotency_key, endpoint, req_hash, now_utc() + timedelta(hours=24)
            )

        pricing = booking.get("pricing", {})
        amount_minor = pricing.get("totalAmountMinor")
        if not amount_minor or amount_minor <= 0:
            raise InvalidBookingStateError("Booking has invalid total amount.")

        now_u = now_utc()

        # Hold & Booking window extension (bounded by MAX_PAYMENT_WINDOW_MINUTES, extended once)
        extension_minutes = getattr(self.config, "PAYMENT_WINDOW_EXTENSION_MINUTES", 15)
        max_window_minutes = getattr(self.config, "MAX_PAYMENT_WINDOW_MINUTES", 30)

        if not booking.get("paymentWindowExtended"):
            booking_created_at = booking.get("createdAt", now_u)
            max_expiry = booking_created_at + timedelta(minutes=max_window_minutes)
            extended_expiry = min(now_u + timedelta(minutes=extension_minutes), max_expiry)

            # Update booking checkout expiry and record extension flag
            self.booking_repo.collection.update_one(
                {"_id": booking["_id"]},
                {"$set": {"checkoutExpiresAt": extended_expiry, "paymentWindowExtended": True, "updatedAt": now_u}}
            )

            # Extend slot claims expiry to match
            if self.slot_claim_repo and self.slot_claim_repo.collection is not None:
                self.slot_claim_repo.collection.update_many(
                    {"ownerId": booking["_id"], "ownerType": "booking"},
                    {"$set": {"expiresAt": extended_expiry}}
                )

        if self.hold_repo and booking.get("holdId"):
            self.hold_repo.extend_hold(booking["holdId"], extension_minutes, now_u)

        # Check for existing created order
        existing_payment = self.payment_repo.find_latest_by_booking_reference(booking_reference)
        if existing_payment and existing_payment.get("status") == "created" and existing_payment.get("amountMinor") == amount_minor:
            order_id = existing_payment.get("providerOrderId")
        else:
            customer = booking.get("customer", {})
            rzp_order = self.client.create_order(
                amount=amount_minor,
                currency="INR",
                receipt=booking_reference,
                notes={
                    "bookingReference": booking_reference,
                    "customerName": customer.get("name", ""),
                    "customerPhone": customer.get("phone", ""),
                }
            )
            order_id = rzp_order["id"]

            payment_doc = {
                "_id": ObjectId(),
                "bookingId": booking["_id"],
                "bookingReference": booking_reference,
                "provider": "razorpay",
                "providerOrderId": order_id,
                "amountMinor": amount_minor,
                "currency": "INR",
                "status": "created",
                "receipt": booking_reference,
                "notes": {
                    "bookingReference": booking_reference,
                    "packageName": booking.get("packageName", "")
                },
                "createdAt": now_u,
                "updatedAt": now_u
            }
            if idempotency_key:
                payment_doc["idempotencyKey"] = idempotency_key
            self.payment_repo.insert(payment_doc)

            # Update booking with razorpayOrderId
            self.booking_repo.update_status(
                booking["_id"], booking.get("bookingStatus"), booking.get("bookingStatus"),
                {"razorpayOrderId": order_id}
            )

        key_id = getattr(self.config, "RAZORPAY_KEY_ID", "")
        response_data = {
            "orderId": order_id,
            "bookingReference": booking_reference,
            "amountMinor": amount_minor,
            "amountRupees": amount_minor / 100.0,
            "currency": "INR",
            "keyId": key_id if (key_id and "replace-with" not in key_id) else "rzp_test_public_key",
            "customer": {
                "name": booking.get("customer", {}).get("name", ""),
                "phone": booking.get("customer", {}).get("phone", ""),
                "email": booking.get("customer", {}).get("email", "")
            }
        }

        if idempotency_key and self.idempotency_repo:
            self.idempotency_repo.complete(idempotency_key, endpoint, 201, response_data)

        return response_data

    def _atomic_confirm_booking_and_payment(
        self,
        booking: dict,
        order_id: str,
        payment_id: str,
        amount_minor: int,
        now_u: datetime,
        method: str = "razorpay"
    ) -> dict:
        """
        Unified atomic confirmation routine for payments verified via checkout,
        webhook, or reconciliation sweep.
        Guarantees slot consistency, late-payment auto-refunds on collision,
        and promo redemption finalization.
        """
        booking_ref = booking.get("bookingReference")

        # 1. Anti-Double-Booking / Late-Payment Conflict Check
        if self.slot_claim_repo and self.slot_claim_repo.collection is not None:
            active_claims = list(self.slot_claim_repo.collection.find({
                "ownerId": booking["_id"],
                "ownerType": "booking"
            }))
            if not active_claims:
                # Slot claims were swept or lost during late payment
                logger.warning(f"Late payment detected for booking {booking_ref}. Verifying slot availability.")
                intervals = generate_slot_claim_intervals(
                    booking["startAt"],
                    booking["endAt"],
                    getattr(self.config, "BUFFER_MINUTES", 30),
                    getattr(self.config, "SLOT_UNIT_MINUTES", 30)
                )
                reclaim_docs = [{
                    "roomId": booking["roomId"],
                    "slotStart": inv["slotStart"],
                    "slotEnd": inv["slotEnd"],
                    "isBuffer": inv["isBuffer"],
                    "ownerType": "booking",
                    "ownerId": booking["_id"],
                    "createdAt": now_u,
                    "expiresAt": None
                } for inv in intervals]

                reclaimed = self.slot_claim_repo.claim_all_or_rollback(reclaim_docs)
                if not reclaimed:
                    logger.error(f"Slot conflict on late payment for {booking_ref}. Initiating full automatic refund.")
                    try:
                        refund_res = self.client.create_refund(
                            payment_id=payment_id,
                            amount=amount_minor,
                            notes={"reason": "Late payment slot conflict - auto refund", "bookingReference": booking_ref}
                        )
                    except Exception as re:
                        logger.error(f"Gateway auto-refund call failed for {booking_ref}: {str(re)}")
                        refund_res = {"id": None, "status": "failed"}

                    refund_doc = {
                        "_id": ObjectId(),
                        "bookingId": booking["_id"],
                        "bookingReference": booking_ref,
                        "provider": "razorpay",
                        "providerPaymentId": payment_id,
                        "amountMinor": amount_minor,
                        "currency": "INR",
                        "status": refund_res.get("status", "processed"),
                        "reason": "Late payment slot conflict",
                        "createdAt": now_u,
                        "updatedAt": now_u
                    }
                    if refund_res.get("id"):
                        refund_doc["providerRefundId"] = refund_res["id"]
                    if self.refund_repo:
                        self.refund_repo.insert(refund_doc)
                    self.booking_repo.update_status(
                        booking["_id"], booking.get("bookingStatus"), "cancelled_due_to_conflict",
                        {"paymentStatus": "refunded"}
                    )
                    raise LatePaymentSlotTakenError("The celebration slot was reserved by another guest. A full refund has been initiated.")

        # 2. Atomic Transition: Booking -> Confirmed, Payment -> Paid
        self.booking_repo.update_status(
            booking["_id"],
            booking.get("bookingStatus"),
            "confirmed",
            {
                "paymentStatus": "paid",
                "paymentMethod": method,
                "razorpayOrderId": order_id,
                "razorpayPaymentId": payment_id,
                "confirmedAt": now_u,
                "updatedAt": now_u
            }
        )

        # Remove expiry from slot claims since booking is now permanently confirmed
        if self.slot_claim_repo and self.slot_claim_repo.collection is not None:
            self.slot_claim_repo.collection.update_many(
                {"ownerId": booking["_id"], "ownerType": "booking"},
                {"$set": {"expiresAt": None, "updatedAt": now_u}}
            )

        # 3. Update payment document
        if order_id:
            self.payment_repo.update_by_order_id(
                order_id,
                {
                    "status": "captured",
                    "providerPaymentId": payment_id,
                    "paymentMethod": method,
                    "capturedAt": now_u,
                    "updatedAt": now_u
                }
            )

        # 4. Finalize promo redemption if any
        if self.offer_redemption_repo:
            self.offer_redemption_repo.convert_to_booking(booking["_id"], booking["_id"], now_u)

        return {
            "bookingReference": booking_ref,
            "bookingStatus": "confirmed",
            "paymentStatus": "paid",
            "orderId": order_id,
            "paymentId": payment_id,
            "amountMinor": amount_minor,
            "currency": "INR",
            "confirmedAt": now_u.isoformat(),
            "message": "Payment verified and booking confirmed successfully."
        }

    def verify_payment(
        self,
        booking_reference: str,
        token: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> dict:
        """
        Cryptographically verifies Razorpay signature and confirms booking.
        Protects against late-payment conflicts with automatic refund on collision.
        """
        booking = self.booking_repo.find_by_reference(booking_reference)
        if not booking:
            raise ResourceNotFoundError(f"Booking reference '{booking_reference}' not found.")

        self._verify_booking_token(booking, token)

        # 1. Cryptographic HMAC-SHA256 signature check
        secret = getattr(self.config, "RAZORPAY_KEY_SECRET", "")
        is_valid = RazorpayClient.verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
            secret=secret
        )
        if not is_valid:
            logger.warning(f"Payment signature verification failed for booking {booking_reference}")
            raise PaymentVerificationError("Cryptographic payment signature verification failed.")

        # 2. Check if already confirmed (idempotent replay)
        if booking.get("bookingStatus") == "confirmed" and booking.get("paymentStatus") == "paid":
            return {
                "bookingReference": booking_reference,
                "bookingStatus": "confirmed",
                "paymentStatus": "paid",
                "orderId": razorpay_order_id,
                "paymentId": razorpay_payment_id,
                "amountMinor": booking["pricing"]["totalAmountMinor"],
                "currency": "INR",
                "message": "Payment verified and booking confirmed."
            }

        now_u = now_utc()
        amount_minor = booking["pricing"]["totalAmountMinor"]

        # 3. Gateway state verification
        fetched = self.client.fetch_payment(
            razorpay_payment_id,
            expected_order_id=razorpay_order_id,
            expected_amount=amount_minor
        )
        if fetched.get("order_id") and fetched.get("order_id") != razorpay_order_id:
            raise PaymentVerificationError("Payment gateway order ID does not match.")
        if fetched.get("currency") and fetched.get("currency") != "INR":
            raise PaymentVerificationError("Payment currency must be INR.")
        if fetched.get("amount") and fetched.get("amount") != amount_minor:
            raise PaymentVerificationError("Payment gateway amount does not match booking total.")
        if fetched.get("status") not in ("captured", "authorized"):
            raise PaymentVerificationError(f"Payment gateway status is '{fetched.get('status')}', not captured.")

        method = fetched.get("method", "razorpay")

        # 4. Atomic confirmation
        return self._atomic_confirm_booking_and_payment(
            booking=booking,
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            amount_minor=amount_minor,
            now_u=now_u,
            method=method
        )

    def process_webhook(self, raw_body_bytes: bytes, signature_header: str) -> dict:
        """
        Processes inbound Razorpay webhooks with cryptographic HMAC verification
        and atomic deduplication via webhookEvents collection.
        """
        webhook_secret = getattr(self.config, "RAZORPAY_WEBHOOK_SECRET", "")
        if not RazorpayClient.verify_webhook_signature(raw_body_bytes, signature_header, webhook_secret):
            logger.warning("Invalid Razorpay webhook signature header.")
            raise PaymentVerificationError("Invalid webhook signature.")

        try:
            event_data = json.loads(raw_body_bytes.decode("utf-8"))
        except Exception:
            raise PaymentVerificationError("Malformed webhook JSON payload.")

        event_id = event_data.get("event_id") or event_data.get("id") or hashlib.md5(raw_body_bytes).hexdigest()
        event_type = event_data.get("event")
        now_u = now_utc()

        # Atomic deduplication claim
        claimed, event_record = self.webhook_repo.claim_event_atomically(
            provider="razorpay",
            event_id=event_id,
            event_type=event_type,
            payload=event_data,
            now_utc=now_u
        )

        if not claimed:
            logger.info(f"Duplicate webhook event {event_id} ignored.")
            return {"status": "already_processed", "eventId": event_id}

        try:
            payload_entity = event_data.get("payload", {})

            if event_type in ("payment.captured", "order.paid"):
                payment_entity = payload_entity.get("payment", {}).get("entity", {})
                order_id = payment_entity.get("order_id")
                payment_id = payment_entity.get("id")
                notes = payment_entity.get("notes", {})
                booking_ref = notes.get("bookingReference")
                method = payment_entity.get("method", "razorpay")
                amount = payment_entity.get("amount")

                booking = None
                if booking_ref:
                    booking = self.booking_repo.find_by_reference(booking_ref)
                elif order_id:
                    pay_record = self.payment_repo.find_by_order_id(order_id)
                    if pay_record:
                        booking = self.booking_repo.find_by_id(pay_record["bookingId"])

                if booking and booking.get("bookingStatus") != "confirmed":
                    actual_amount = amount or booking["pricing"]["totalAmountMinor"]
                    self._atomic_confirm_booking_and_payment(
                        booking=booking,
                        order_id=order_id,
                        payment_id=payment_id,
                        amount_minor=actual_amount,
                        now_u=now_u,
                        method=method
                    )
                elif order_id:
                    self.payment_repo.update_by_order_id(
                        order_id,
                        {
                            "status": "captured",
                            "providerPaymentId": payment_id,
                            "paymentMethod": method,
                            "capturedAt": now_u,
                            "updatedAt": now_u
                        }
                    )

            elif event_type == "payment.failed":
                payment_entity = payload_entity.get("payment", {}).get("entity", {})
                order_id = payment_entity.get("order_id")
                payment_id = payment_entity.get("id")
                error_desc = payment_entity.get("error_description", "Payment failed")
                if order_id:
                    self.payment_repo.update_by_order_id(
                        order_id,
                        {
                            "status": "failed",
                            "providerPaymentId": payment_id,
                            "errorDescription": error_desc,
                            "updatedAt": now_u
                        }
                    )

            elif event_type == "refund.processed":
                refund_entity = payload_entity.get("refund", {}).get("entity", {})
                refund_id = refund_entity.get("id")
                payment_id = refund_entity.get("payment_id")
                amount = refund_entity.get("amount", 0)

                self.refund_repo.update_status(refund_id, "processed")
                payment = self.payment_repo.find_by_payment_id(payment_id)
                if payment:
                    new_ref = payment.get("amountRefundedMinor", 0) + amount
                    status = "refunded" if new_ref >= payment.get("amountMinor", 0) else "partially_refunded"
                    self.payment_repo.update_by_payment_id(
                        payment_id,
                        {"amountRefundedMinor": new_ref, "refundStatus": status, "updatedAt": now_u}
                    )

            self.webhook_repo.mark_processed("razorpay", event_id)
            return {"status": "processed", "eventId": event_id, "eventType": event_type}

        except Exception as e:
            logger.error(f"Error handling webhook event {event_id}: {str(e)}")
            self.webhook_repo.mark_failed("razorpay", event_id, str(e))
            raise

    def process_refund(
        self,
        booking_reference: str,
        token: str,
        reason: str = "",
        amount_minor: int = None,
        idempotency_key: str = None
    ) -> dict:
        """
        Processes a policy-compliant or manual refund for a confirmed booking.
        Uses atomic DB reservation (atomic_record_refund) before calling gateway,
        recording failed attempts in refunds and marking payments for review.
        Releases slot claims and promo quota on full refund.
        """
        booking = self.booking_repo.find_by_reference(booking_reference)
        if not booking:
            raise ResourceNotFoundError(f"Booking reference '{booking_reference}' not found.")

        self._verify_booking_token(booking, token)

        if booking.get("paymentStatus") not in ("paid", "partially_refunded"):
            raise InvalidBookingStateError("Booking has no settled payments to refund.")

        payment = self.payment_repo.find_latest_by_booking_reference(booking_reference)
        if not payment or not payment.get("providerPaymentId"):
            raise InvalidBookingStateError("Payment transaction record not found.")

        total_paid = payment.get("amountMinor", 0)
        already_refunded = payment.get("amountRefundedMinor", 0)
        max_refundable = total_paid - already_refunded

        if max_refundable <= 0:
            raise RefundNotAllowedError("Booking has already been fully refunded.")

        now_u = now_utc()
        start_at = ensure_utc(booking["startAt"])
        hours_before = (start_at - now_u).total_seconds() / 3600.0

        if amount_minor is not None:
            if amount_minor > max_refundable:
                raise RefundNotAllowedError(f"Requested refund amount exceeds refundable balance of {max_refundable} paise.")
            refund_amount = amount_minor
        else:
            # Policy-based tier calculation
            full_window = getattr(self.config, "REFUND_WINDOW_FULL_HOURS", 48)
            part_window = getattr(self.config, "REFUND_WINDOW_PARTIAL_HOURS", 24)
            part_percent = getattr(self.config, "REFUND_WINDOW_PARTIAL_PERCENT", 50)
            min_notice = getattr(self.config, "REFUND_MIN_NOTICE_HOURS", 24)

            if hours_before >= full_window:
                refund_amount = max_refundable
            elif hours_before >= part_window:
                refund_amount = int(max_refundable * (part_percent / 100.0))
            else:
                raise RefundNotAllowedError(
                    f"Cancellations less than {min_notice} hours before the celebration are non-refundable."
                )

        if refund_amount <= 0:
            raise RefundNotAllowedError("Calculated refund amount is zero.")

        if idempotency_key:
            existing_refund = self.refund_repo.find_by_idempotency_key(idempotency_key)
            if existing_refund:
                return {
                    "refundId": existing_refund.get("providerRefundId"),
                    "bookingReference": booking_reference,
                    "amountMinor": existing_refund.get("amountMinor"),
                    "status": existing_refund.get("status"),
                    "message": "Refund already processed (idempotent)."
                }

        # Step 1: Atomically record and reserve the refund in database
        updated_payment = self.payment_repo.atomic_record_refund(
            payment["providerPaymentId"], refund_amount, now_u
        )
        if not updated_payment:
            raise RefundNotAllowedError("Refund amount exceeds available captured balance.")

        new_total_refunded = updated_payment.get("amountRefundedMinor", already_refunded + refund_amount)
        refund_status = "refunded" if new_total_refunded >= total_paid else "partially_refunded"

        # Step 2: Call payment gateway
        try:
            rzp_refund = self.client.create_refund(
                payment_id=payment["providerPaymentId"],
                amount=refund_amount,
                notes={"bookingReference": booking_reference, "reason": reason}
            )
            refund_id = rzp_refund.get("id")
            refund_doc_status = rzp_refund.get("status", "processed")
        except Exception as e:
            logger.error(f"Gateway refund call failed for booking {booking_reference}: {str(e)}")
            failed_doc = {
                "_id": ObjectId(),
                "bookingId": booking["_id"],
                "bookingReference": booking_reference,
                "provider": "razorpay",
                "providerPaymentId": payment["providerPaymentId"],
                "amountMinor": refund_amount,
                "currency": "INR",
                "status": "failed",
                "errorDescription": str(e),
                "reason": reason,
                "createdAt": now_u,
                "updatedAt": now_u
            }
            if idempotency_key:
                failed_doc["idempotencyKey"] = idempotency_key
            if self.refund_repo:
                self.refund_repo.insert(failed_doc)
            self.payment_repo.update_by_payment_id(
                payment["providerPaymentId"],
                {"needsReview": True, "reviewReason": f"Gateway refund failed: {str(e)}", "updatedAt": now_u}
            )
            raise PaymentGatewayError(f"Gateway refund processing failed: {str(e)}")

        # Step 3: Record successful refund document
        refund_doc = {
            "_id": ObjectId(),
            "bookingId": booking["_id"],
            "bookingReference": booking_reference,
            "provider": "razorpay",
            "providerRefundId": refund_id,
            "providerPaymentId": payment["providerPaymentId"],
            "amountMinor": refund_amount,
            "currency": "INR",
            "status": refund_doc_status,
            "reason": reason,
            "idempotencyKey": idempotency_key,
            "createdAt": now_u,
            "updatedAt": now_u
        }
        self.refund_repo.insert(refund_doc)

        self.payment_repo.update_by_payment_id(
            payment["providerPaymentId"],
            {
                "refundStatus": refund_status,
                "updatedAt": now_u
            }
        )

        # If fully refunded, cancel booking and release slots
        if refund_status == "refunded":
            self.booking_repo.update_status(
                booking["_id"],
                booking.get("bookingStatus"),
                "cancelled",
                {"paymentStatus": refund_status, "cancelledAt": now_u, "cancellationReason": reason}
            )
            if self.slot_claim_repo:
                self.slot_claim_repo.release_by_owner(booking["_id"])
            if self.offer_redemption_repo and self.offer_repo:
                released = self.offer_redemption_repo.release_reservation_idempotent(booking["_id"], now_u)
                if released and released.get("offerId"):
                    self.offer_repo.atomic_release_slot(released["offerId"])

        return {
            "refundId": refund_id,
            "bookingReference": booking_reference,
            "amountMinor": refund_amount,
            "amountRupees": refund_amount / 100.0,
            "currency": "INR",
            "status": refund_doc_status,
            "refundStatus": refund_status,
            "refundedAt": now_u.isoformat(),
            "message": "Refund processed successfully."
        }

    def retry_refund(self, refund_id: str) -> dict:
        """
        Retries a failed refund against the gateway and clears review flags upon success.
        """
        refund = self.refund_repo.find_by_id(refund_id)
        if not refund:
            refund = self.refund_repo.find_by_refund_id(refund_id)
        if not refund:
            raise ResourceNotFoundError(f"Refund record '{refund_id}' not found.")

        if refund.get("status") == "processed":
            return {"status": "already_processed", "refundId": refund.get("providerRefundId")}

        payment_id = refund["providerPaymentId"]
        now_u = now_utc()

        try:
            rzp_refund = self.client.create_refund(
                payment_id=payment_id,
                amount=refund["amountMinor"],
                notes={"bookingReference": refund["bookingReference"], "reason": "Retry failed refund"}
            )
            new_refund_id = rzp_refund.get("id")
            self.refund_repo.update_status(
                refund.get("providerRefundId") or refund["_id"],
                "processed",
                {"providerRefundId": new_refund_id, "updatedAt": now_u}
            )
            # Check if any failed refunds remain for this payment
            failed_remaining = list(self.refund_repo.collection.find({
                "providerPaymentId": payment_id,
                "status": "failed"
            }))
            if not failed_remaining:
                self.payment_repo.update_by_payment_id(
                    payment_id,
                    {"needsReview": False, "reviewReason": None, "updatedAt": now_u}
                )

            return {
                "refundId": new_refund_id,
                "status": "processed",
                "message": "Refund retry succeeded."
            }
        except Exception as e:
            logger.error(f"Retry refund failed for {refund_id}: {str(e)}")
            raise PaymentGatewayError(f"Refund retry failed: {str(e)}")

    def reconcile_pending_payments(self, age_minutes: int = 15) -> dict:
        """
        Reconciles stale payments in 'created' status against the payment gateway.
        """
        now_u = now_utc()
        pending = self.payment_repo.find_pending_for_reconciliation(age_minutes, now_u)
        reconciled = []

        for pay in pending:
            order_id = pay.get("providerOrderId")
            booking = self.booking_repo.find_by_id(pay.get("bookingId"))
            if not order_id or not booking:
                continue

            try:
                payment_id = pay.get("providerPaymentId")
                if payment_id:
                    fetched = self.client.fetch_payment(payment_id)
                    if fetched.get("status") == "captured":
                        self._atomic_confirm_booking_and_payment(
                            booking=booking,
                            order_id=order_id,
                            payment_id=payment_id,
                            amount_minor=pay.get("amountMinor"),
                            now_u=now_u,
                            method=fetched.get("method", "reconciliation")
                        )
                        reconciled.append({"orderId": order_id, "action": "confirmed"})
                    elif fetched.get("status") == "failed":
                        self.payment_repo.update_by_order_id(order_id, {"status": "failed", "updatedAt": now_u})
                        reconciled.append({"orderId": order_id, "action": "failed"})
                else:
                    self.payment_repo.update_by_order_id(order_id, {"status": "expired", "updatedAt": now_u})
                    reconciled.append({"orderId": order_id, "action": "expired"})
            except Exception as e:
                logger.error(f"Reconciliation error for order {order_id}: {str(e)}")
                self.payment_repo.update_by_order_id(
                    order_id,
                    {"needsReview": True, "reviewReason": f"Reconciliation error: {str(e)}", "updatedAt": now_u}
                )

        return {"reconciledCount": len(reconciled), "details": reconciled}
