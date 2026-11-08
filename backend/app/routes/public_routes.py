import hashlib
import hmac
import uuid
import razorpay
from flask import Blueprint, current_app, request, jsonify
from marshmallow import ValidationError
from ..schemas import (
    InquirySchema,
    QuoteRequestSchema,
    AvailabilityQuerySchema,
    BookingHoldRequestSchema,
    BookingCreateRequestSchema,
    BookingCancelRequestSchema,
)
from ..repositories import (
    PackageRepository,
    AddOnRepository,
    OfferRepository,
    InquiryRepository,
    SlotClaimRepository,
    BookingHoldRepository,
    BookingRepository,
    CounterRepository,
    OfferRedemptionRepository,
    IdempotencyRepository,
    RateLimitRepository,
    GalleryRepository,
    FaqRepository,
)
from ..services import CatalogService, InquiryService, BookingService
from ..utils import (
    api_response,
    api_error,
    serialize_doc,
    SlotUnavailableError,
    HoldExpiredError,
    PromoExhaustedError,
    IdempotencyConflictError,
    IdempotencyPayloadMismatchError,
    ResourceNotFoundError,
    InvalidBookingStateError,
    RateLimitExceededError,
    PaymentVerificationError,
    PaymentGatewayError,
    LatePaymentSlotTakenError,
)
from ..utils.datetime_utils import now_utc

public_bp = Blueprint("public", __name__, url_prefix="/api")

def get_services():
    db = current_app.extensions.get("mongo_db")
    pkg_repo = PackageRepository(db)
    addon_repo = AddOnRepository(db)
    offer_repo = OfferRepository(db)
    inq_repo = InquiryRepository(db)
    slot_claim_repo = SlotClaimRepository(db)
    hold_repo = BookingHoldRepository(db)
    booking_repo = BookingRepository(db)
    counter_repo = CounterRepository(db)
    offer_redemption_repo = OfferRedemptionRepository(db)
    idempotency_repo = IdempotencyRepository(db)
    rate_limit_repo = RateLimitRepository(db)

    catalog_svc = CatalogService(pkg_repo, addon_repo, offer_repo, offer_redemption_repo, config=current_app.config)
    inquiry_svc = InquiryService(inq_repo)
    booking_svc = BookingService(
        slot_claim_repo=slot_claim_repo,
        hold_repo=hold_repo,
        booking_repo=booking_repo,
        counter_repo=counter_repo,
        offer_repo=offer_repo,
        offer_redemption_repo=offer_redemption_repo,
        idempotency_repo=idempotency_repo,
        package_repo=pkg_repo,
        addon_repo=addon_repo,
        rate_limit_repo=rate_limit_repo,
        config=current_app.config,
    )
    return catalog_svc, inquiry_svc, booking_svc

def _get_client_ip():
    # S1 Fix: Rely on request.remote_addr as sanitized by Werkzeug ProxyFix
    return request.remote_addr or "127.0.0.1"

@public_bp.get("/health")
def health():
    db = current_app.extensions.get("mongo_db")
    if db is None:
        return api_response(data={"status": "ok", "database": "not_configured"}, status_code=200)
    try:
        db.command("ping")
        return api_response(data={
            "status": "ok",
            "database": "connected",
            "service": "joybox-party-room",
            "version": "1.0.0"
        }, status_code=200)
    except Exception:
        return api_response(data={"status": "degraded", "database": "unavailable"}, status_code=503)

@public_bp.get("/ready")
def ready():
    """Readiness probe verifying DB connection and seeded catalog status."""
    db = current_app.extensions.get("mongo_db")
    if db is None:
        return api_response(data={"status": "not_ready", "reason": "database_not_configured"}, status_code=503)
    try:
        db.command("ping")
        pkg_count = db.packages.count_documents({"isActive": True}) if hasattr(db.packages, "count_documents") else len(list(db.packages.find({"isActive": True})))
        return api_response(data={
            "status": "ready",
            "database": "connected",
            "activePackagesCount": pkg_count
        }, status_code=200)
    except Exception as exc:
        return api_response(data={"status": "not_ready", "reason": str(exc)}, status_code=503)

@public_bp.get("/packages")
def get_packages():
    catalog_svc, _, _ = get_services()
    items = catalog_svc.get_packages()
    return api_response(data={"items": serialize_doc(items), "currency": "INR"})

@public_bp.get("/packages/<slug>")
def get_package_by_slug(slug):
    catalog_svc, _, _ = get_services()
    pkg = catalog_svc.get_package_by_code(slug)
    if not pkg:
        return api_error("NOT_FOUND", f"Package '{slug}' not found", status_code=404)
    return api_response(data=serialize_doc(pkg))

@public_bp.get("/add-ons")
def get_addons():
    catalog_svc, _, _ = get_services()
    items = catalog_svc.get_addons()
    return api_response(data={"items": serialize_doc(items), "currency": "INR"})

@public_bp.get("/offers/active")
def get_active_offers():
    catalog_svc, _, _ = get_services()
    offers = catalog_svc.get_active_offers()
    return api_response(data={"offers": serialize_doc(offers)})

@public_bp.get("/gallery")
def get_gallery():
    db = current_app.extensions.get("mongo_db")
    category = request.args.get("category")
    repo = GalleryRepository(db)
    items = repo.find_active(category=category)
    safe_items = []
    for item in items:
        serialized = serialize_doc(item)
        serialized.pop("storageKey", None)
        safe_items.append(serialized)
    return api_response(data={"items": safe_items})

@public_bp.get("/faqs")
def get_faqs():
    db = current_app.extensions.get("mongo_db")
    category = request.args.get("category")
    repo = FaqRepository(db)
    items = repo.find_active(category=category)
    return api_response(data={"items": serialize_doc(items)})

@public_bp.post("/bookings/quote")
def quote():
    catalog_svc, _, _ = get_services()
    body = request.get_json(silent=True) or {}
    try:
        data = QuoteRequestSchema().load(body)
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid quote request parameters", details=err.messages, status_code=422)

    try:
        result = catalog_svc.calculate_quote(
            package_code=data["packageCode"],
            duration_hours=data["durationHours"],
            addon_codes=data.get("addOnCodes", []),
            apply_promo=data.get("applyPromo", True),
            event_date=data.get("date"),
            customer_phone=data.get("customerPhone"),
            gst_rate_percent=data.get("gstRatePercent")
        )
        return api_response(data=result)
    except ValueError as val_err:
        return api_error("VALIDATION_ERROR", str(val_err), status_code=422)

@public_bp.post("/inquiries")
def create_inquiry():
    _, inq_svc, _ = get_services()
    db = current_app.extensions.get("mongo_db")
    if db is None:
        return api_error("DATABASE_UNAVAILABLE", "Database not configured for inquiry persistence", status_code=503)

    # BUG-10: IP rate limiting on public inquiries (default 5 inquiries per 5 minutes per IP)
    is_testing = current_app.config.get("TESTING", False)
    enable_test_rl = current_app.config.get("ENABLE_TEST_RATE_LIMIT", False)
    if not is_testing or enable_test_rl:
        client_ip = _get_client_ip()
        rate_repo = RateLimitRepository(db)
        if not rate_repo.check_and_increment(f"inquiry:{client_ip}", 300, 5, now_utc()):
            return api_error(
                "RATE_LIMITED",
                "Too many inquiries submitted from this IP address. Please wait or reach out via WhatsApp.",
                status_code=429
            )

    body = request.get_json(silent=True) or {}
    try:
        payload = InquirySchema().load(body)
    except ValidationError as exc:
        return api_error("VALIDATION_ERROR", "Validation failed for inquiry submission", details=exc.messages, status_code=422)

    try:
        result = inq_svc.submit_inquiry(payload)
        return api_response(data=result, status_code=201)
    except Exception as exc:
        current_app.logger.error(f"Inquiry submission failed: {exc}")
        return api_error("INTERNAL_ERROR", "Could not submit inquiry. Please reach out via WhatsApp.", status_code=500)

@public_bp.get("/availability")
def get_availability():
    _, _, booking_svc = get_services()
    try:
        query_data = AvailabilityQuerySchema().load(request.args.to_dict())
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid availability query parameters", details=err.messages, status_code=422)

    try:
        result = booking_svc.get_availability(
            date_str=query_data["date"],
            duration_hours=query_data.get("durationHours", 1),
            room_id=query_data.get("roomId", "main")
        )
        return api_response(data=result)
    except ValueError as val_err:
        return api_error("VALIDATION_ERROR", str(val_err), status_code=422)
    except Exception as exc:
        current_app.logger.error(f"Error computing availability: {exc}", exc_info=True)
        return api_error("INTERNAL_ERROR", "Could not calculate slot availability.", status_code=500)

@public_bp.post("/bookings/hold")
def create_booking_hold():
    if not current_app.config.get("BOOKINGS_OPEN", False):
        return api_error(
            "BOOKINGS_NOT_OPEN",
            "Bookings are not open yet. Please contact us via WhatsApp to reserve.",
            status_code=403
        )

    _, _, booking_svc = get_services()
    body = request.get_json(silent=True) or {}
    try:
        payload = BookingHoldRequestSchema().load(body)
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid booking hold parameters", details=err.messages, status_code=422)

    idempotency_key = request.headers.get("Idempotency-Key")
    client_ip = _get_client_ip()

    try:
        result = booking_svc.create_hold(payload, idempotency_key=idempotency_key, client_ip=client_ip)
        return api_response(data=result, status_code=201)
    except SlotUnavailableError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except PromoExhaustedError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except RateLimitExceededError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except ValueError as val_err:
        return api_error("VALIDATION_ERROR", str(val_err), status_code=422)
    except Exception as exc:
        current_app.logger.error(f"Hold creation failed: {exc}", exc_info=True)
        return api_error("INTERNAL_ERROR", "Could not hold celebration slot.", status_code=500)

@public_bp.post("/bookings")
def create_booking():
    if not current_app.config.get("BOOKINGS_OPEN", False):
        return api_error(
            "BOOKINGS_NOT_OPEN",
            "Bookings are not open yet. Please contact us via WhatsApp to reserve.",
            status_code=403
        )

    _, _, booking_svc = get_services()
    body = request.get_json(silent=True) or {}

    # Support either conversion from hold or direct booking creation
    if "holdId" in body:
        try:
            payload = BookingCreateRequestSchema().load(body)
        except ValidationError as err:
            return api_error("VALIDATION_ERROR", "Invalid booking payload", details=err.messages, status_code=422)
    else:
        try:
            payload = BookingHoldRequestSchema().load(body)
        except ValidationError as err:
            return api_error("VALIDATION_ERROR", "Invalid booking payload", details=err.messages, status_code=422)

    idempotency_key = request.headers.get("Idempotency-Key")
    client_ip = _get_client_ip()

    try:
        result = booking_svc.create_booking(payload, idempotency_key=idempotency_key, client_ip=client_ip)
        return api_response(data=result, status_code=201)
    except SlotUnavailableError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except HoldExpiredError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except IdempotencyPayloadMismatchError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except IdempotencyConflictError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except RateLimitExceededError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except ResourceNotFoundError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except ValueError as val_err:
        return api_error("VALIDATION_ERROR", str(val_err), status_code=422)
    except Exception as exc:
        current_app.logger.error(f"Booking creation failed: {exc}", exc_info=True)
        return api_error("INTERNAL_ERROR", "Could not complete booking.", status_code=500)

@public_bp.get("/bookings/<reference>")
def get_booking_by_reference(reference):
    _, _, booking_svc = get_services()
    token = request.args.get("token") or request.headers.get("X-Booking-Token")
    booking = booking_svc.get_booking_by_reference(reference, token=token)
    if not booking:
        return api_error("NOT_FOUND", f"Booking with reference '{reference}' not found", status_code=404)
    return api_response(data=booking)

@public_bp.post("/bookings/<reference>/cancel")
def cancel_booking(reference):
    _, _, booking_svc = get_services()
    body = request.get_json(silent=True) or {}
    try:
        data = BookingCancelRequestSchema().load(body)
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid cancellation request", details=err.messages, status_code=422)

    token = data.get("token") or request.args.get("token") or request.headers.get("X-Booking-Token")
    try:
        result = booking_svc.cancel_booking(reference, token=token, reason=data.get("reason", ""))
        return api_response(data=result, status_code=200)
    except ResourceNotFoundError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except InvalidBookingStateError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except PaymentGatewayError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except Exception as exc:
        current_app.logger.error(f"Cancellation failed: {exc}", exc_info=True)
        return api_error("INTERNAL_ERROR", "Could not process cancellation.", status_code=500)


# ==============================================================================
# RAZORPAY PAYMENT ENDPOINTS (MIGRATED & LOCKED TO CANONICAL RULES)
# ==============================================================================

@public_bp.post("/create-order")
def create_order():
    """
    POST /api/create-order
    Guarded compatibility endpoint: strictly enforces server-side pricing from booking.
    Rejects any unverified client-supplied pricing.
    """
    if not current_app.config.get("PAYMENTS_ENABLED", False):
        return api_error("PAYMENTS_DISABLED", "Online payments are currently disabled.", status_code=403)

    body = request.get_json(silent=True) or {}
    booking_reference = body.get("bookingReference")
    token = body.get("token") or request.headers.get("X-Booking-Token")

    if not booking_reference or not token:
        return api_error(
            "MISSING_FIELDS",
            "bookingReference and token are required. Order amount is strictly calculated server-side from booking records.",
            status_code=400
        )

    from .payment_routes import get_payment_service
    idempotency_key = request.headers.get("Idempotency-Key") or body.get("idempotencyKey")
    svc = get_payment_service()

    try:
        res = svc.create_order(booking_reference, token, idempotency_key=idempotency_key)
        return jsonify({
            "success": True,
            "order_id": res["orderId"],
            "amount": res["amountMinor"],
            "currency": res["currency"],
            "key_id": res["keyId"],
            "data": {
                "order_id": res["orderId"],
                "orderId": res["orderId"],
                "amount": res["amountMinor"],
                "amountMinor": res["amountMinor"],
                "currency": res["currency"],
                "key_id": res["keyId"],
                "keyId": res["keyId"]
            },
            "error": None
        }), 200
    except ResourceNotFoundError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except InvalidBookingStateError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except PaymentGatewayError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except Exception as exc:
        current_app.logger.error(f"Failed to create order: {exc}", exc_info=True)
        return api_error("INTERNAL_ERROR", "Failed to communicate with payment gateway.", status_code=500)


@public_bp.post("/verify-payment")
def verify_payment_signature():
    """
    POST /api/verify-payment
    Guarded compatibility endpoint: validates signature AND enforces atomic DB booking confirmation.
    Returns HTTP error status if confirmation fails; never reports false success.
    """
    if not current_app.config.get("PAYMENTS_ENABLED", False):
        return api_error("PAYMENTS_DISABLED", "Online payments are currently disabled.", status_code=403)

    body = request.get_json(silent=True) or {}
    order_id = body.get("razorpay_order_id") or body.get("order_id")
    payment_id = body.get("razorpay_payment_id") or body.get("payment_id")
    signature = body.get("razorpay_signature") or body.get("signature")
    booking_reference = body.get("bookingReference")
    token = body.get("token") or request.headers.get("X-Booking-Token")

    if not order_id or not payment_id or not signature or not booking_reference or not token:
        return api_error(
            "MISSING_FIELDS",
            "Missing required fields: order_id, payment_id, signature, bookingReference, and token are required.",
            status_code=400
        )

    from .payment_routes import get_payment_service
    pay_svc = get_payment_service()

    try:
        verified_data = pay_svc.verify_payment(
            booking_reference=booking_reference,
            token=token,
            razorpay_order_id=order_id,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature
        )
        return jsonify({
            "success": True,
            "message": "Payment verified successfully",
            "data": verified_data,
            "error": None
        }), 200
    except PaymentVerificationError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except ResourceNotFoundError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except LatePaymentSlotTakenError as err:
        return api_error(err.code, err.message, status_code=err.status_code)
    except Exception as exc:
        current_app.logger.error(f"Verification failed: {exc}", exc_info=True)
        return api_error("INTERNAL_ERROR", "Payment confirmation failed.", status_code=500)


# ==============================================================================
# PUBLIC CONFIGURATION ENDPOINT
# ==============================================================================

@public_bp.get("/public-config")
def get_public_config():
    """
    GET /api/public-config
    Public venue & booking configuration consumed by the frontend client.
    Single source of truth for bookingsOpen, paymentsEnabled, and WhatsApp contact.
    """
    cfg = current_app.config
    raw_phone = str(cfg.get("WHATSAPP_NUMBER", "") or "").strip()
    digits_only_phone = "".join([c for c in raw_phone if c.isdigit()])

    return api_response(data={
        "bookingsOpen": bool(cfg.get("BOOKINGS_OPEN", False)),
        "paymentsEnabled": bool(cfg.get("PAYMENTS_ENABLED", False)),
        "whatsappNumber": digits_only_phone,
        "venueAddress": cfg.get("VENUE_ADDRESS", "Beside Durga Mart, Vadlamudi, Guntur, Andhra Pradesh 522213"),
        "hostName": cfg.get("HOST_NAME", "Kiran Kumar"),
        "advanceDepositPaise": int(cfg.get("ADVANCE_DEPOSIT_PAISE", 50000)),
        "currency": cfg.get("PAYMENT_CURRENCY", "INR"),
    })
