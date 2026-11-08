import logging
from flask import Blueprint, current_app, request
from marshmallow import ValidationError

from ..schemas import (
    CreatePaymentOrderSchema,
    VerifyPaymentSchema,
    RefundRequestSchema,
)
from ..repositories import (
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
from ..services import PaymentService
from ..utils import (
    api_response,
    api_error,
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

payment_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

@payment_bp.before_request
def check_payments_enabled():
    if not current_app.config.get("PAYMENTS_ENABLED", False):
        return api_error("PAYMENTS_DISABLED", "Online payments are currently disabled.", status_code=403)

def get_payment_service():
    db = current_app.extensions.get("mongo_db")
    booking_repo = BookingRepository(db)
    hold_repo = BookingHoldRepository(db)
    payment_repo = PaymentRepository(db)
    refund_repo = RefundRepository(db)
    webhook_repo = WebhookEventRepository(db)
    slot_claim_repo = SlotClaimRepository(db)
    offer_repo = OfferRepository(db)
    offer_redemption_repo = OfferRedemptionRepository(db)
    idempotency_repo = IdempotencyRepository(db)

    return PaymentService(
        booking_repo=booking_repo,
        payment_repo=payment_repo,
        refund_repo=refund_repo,
        webhook_repo=webhook_repo,
        slot_claim_repo=slot_claim_repo,
        offer_repo=offer_repo,
        offer_redemption_repo=offer_redemption_repo,
        idempotency_repo=idempotency_repo,
        hold_repo=hold_repo,
        config=current_app.config,
    )

@payment_bp.post("/create-order")
def create_payment_order():
    schema = CreatePaymentOrderSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid payment order request.", status_code=400, details=err.messages)

    idempotency_key = request.headers.get("Idempotency-Key") or data.get("idempotencyKey")
    svc = get_payment_service()

    try:
        res = svc.create_order(
            booking_reference=data["bookingReference"],
            token=data["token"],
            idempotency_key=idempotency_key
        )
        return api_response(data=res, status_code=201)
    except ResourceNotFoundError as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except (InvalidBookingStateError, IdempotencyConflictError, IdempotencyPayloadMismatchError) as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except PaymentGatewayError as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        logger.exception("Unexpected error in create_payment_order")
        return api_error("INTERNAL_ERROR", "An unexpected error occurred while creating payment order.", status_code=500)

@payment_bp.post("/verify")
@payment_bp.post("/verify-payment")
def verify_payment():
    schema = VerifyPaymentSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid payment verification request.", status_code=400, details=err.messages)

    svc = get_payment_service()

    try:
        res = svc.verify_payment(
            booking_reference=data["bookingReference"],
            token=data["token"],
            razorpay_order_id=data["razorpay_order_id"],
            razorpay_payment_id=data["razorpay_payment_id"],
            razorpay_signature=data["razorpay_signature"],
        )
        return api_response(data=res, status_code=200)
    except (ResourceNotFoundError, PaymentVerificationError, LatePaymentSlotTakenError) as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        logger.exception("Unexpected error in verify_payment")
        return api_error("INTERNAL_ERROR", "An unexpected error occurred while verifying payment.", status_code=500)

@payment_bp.post("/webhook")
def handle_webhook():
    raw_body = request.get_data()
    sig_header = request.headers.get("X-Razorpay-Signature", "")

    if not sig_header:
        return api_error("MISSING_SIGNATURE", "X-Razorpay-Signature header is missing.", status_code=400)

    svc = get_payment_service()
    try:
        res = svc.process_webhook(raw_body, sig_header)
        return api_response(data=res, status_code=200)
    except PaymentVerificationError as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        logger.exception("Error processing webhook")
        return api_error("WEBHOOK_PROCESSING_FAILED", str(e), status_code=500)

@payment_bp.post("/refund")
def process_refund():
    schema = RefundRequestSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid refund request.", status_code=400, details=err.messages)

    idempotency_key = request.headers.get("Idempotency-Key") or data.get("idempotencyKey")
    if not idempotency_key:
        import uuid
        idempotency_key = f"auto_{data.get('bookingReference', 'refund')}_{uuid.uuid4().hex[:12]}"

    svc = get_payment_service()

    try:
        res = svc.process_refund(
            booking_reference=data["bookingReference"],
            token=data["token"],
            reason=data.get("reason", ""),
            amount_minor=data.get("amountMinor"),
            idempotency_key=idempotency_key,
        )
        return api_response(data=res, status_code=200)
    except (ResourceNotFoundError, InvalidBookingStateError, RefundNotAllowedError) as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except PaymentGatewayError as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        logger.exception("Unexpected error in process_refund")
        return api_error("INTERNAL_ERROR", "An unexpected error occurred while processing refund.", status_code=500)
