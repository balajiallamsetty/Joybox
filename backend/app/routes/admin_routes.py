import hashlib
import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, current_app, request, make_response, g
from marshmallow import ValidationError
from bson import ObjectId

from ..schemas.admin_schemas import (
    AdminLoginSchema,
    AdminChangePasswordSchema,
    AdminUpdateBookingSchema,
    AdminCreateBookingSchema,
    AdminCreatePackageSchema,
    AdminUpdatePackageSchema,
    AdminCreateAddOnSchema,
    AdminUpdateAddOnSchema,
    AdminCreateAvailabilityBlockSchema,
    AdminUpdateInquirySchema,
)
from ..repositories import (
    UserRepository,
    AdminSessionRepository,
    AuditLogRepository,
    BookingRepository,
    BookingHoldRepository,
    PaymentRepository,
    RefundRepository,
    SlotClaimRepository,
    PackageRepository,
    AddOnRepository,
    OfferRepository,
    OfferRedemptionRepository,
    CounterRepository,
    AvailabilityBlockRepository,
    RateLimitRepository,
)
from ..services.admin_service import (
    AdminService,
    require_admin_session,
    require_role,
    require_csrf,
    AuthenticationError,
    AccountLockedError,
)
from ..services.payment_service import PaymentService
from ..utils.datetime_utils import (
    now_utc,
    now_ist,
    validate_booking_window,
    generate_slot_claim_intervals,
    get_ist_period_key,
    format_ist_time,
)
from ..utils import (
    api_response,
    api_error,
    ResourceNotFoundError,
    InvalidBookingStateError,
    SlotUnavailableError,
)

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

def get_admin_service():
    db = current_app.extensions.get("mongo_db")
    user_repo = UserRepository(db)
    session_repo = AdminSessionRepository(db)
    audit_repo = AuditLogRepository(db)
    return AdminService(user_repo, session_repo, audit_repo, current_app.config)

def get_payment_service():
    db = current_app.extensions.get("mongo_db")
    return PaymentService(
        booking_repo=BookingRepository(db),
        payment_repo=PaymentRepository(db),
        refund_repo=RefundRepository(db),
        webhook_repo=None,
        slot_claim_repo=SlotClaimRepository(db),
        offer_repo=OfferRepository(db),
        offer_redemption_repo=OfferRedemptionRepository(db),
        hold_repo=BookingHoldRepository(db),
        config=current_app.config,
    )

def _get_client_ip():
    # S1 Fix: Rely on request.remote_addr as sanitized by Werkzeug ProxyFix
    return request.remote_addr or "127.0.0.1"


# ==============================================================================
# AUTHENTICATION ENDPOINTS
# ==============================================================================

@admin_bp.post("/auth/login")
def login():
    schema = AdminLoginSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid login parameters.", status_code=400, details=err.messages)

    svc = get_admin_service()
    client_ip = _get_client_ip()
    user_agent = request.headers.get("User-Agent", "")

    # BUG-10: IP rate limiting on admin login (protects against distributed brute-force)
    db = current_app.extensions.get("mongo_db")
    is_testing = current_app.config.get("TESTING", False)
    enable_test_rl = current_app.config.get("ENABLE_TEST_RATE_LIMIT", False)
    if db is not None and (not is_testing or enable_test_rl):
        rate_repo = RateLimitRepository(db)
        ip_limit = current_app.config.get("ADMIN_RATE_LIMIT_IP_MAX", 10)
        ip_window = current_app.config.get("ADMIN_RATE_LIMIT_IP_WINDOW", 60)
        if not rate_repo.check_and_increment(f"admin_login_ip:{client_ip}", ip_window, ip_limit, now_utc()):
            return api_error(
                "RATE_LIMITED",
                "Too many login attempts from this IP address. Please wait before retrying.",
                status_code=429
            )

    try:
        auth_data = svc.login(data["username"], data["password"], client_ip, user_agent)
        resp = make_response(api_response(
            data={
                "user": auth_data["user"],
                "csrfToken": auth_data["csrfToken"],
                "sessionToken": auth_data["sessionToken"]
            },
            meta={"message": "Login successful."},
            status_code=200
        ))

        # Secure HttpOnly session cookie (BUG-05: resolve ADMIN_COOKIE_SECURE correctly)
        cookie_name = current_app.config.get(
            "ADMIN_SESSION_COOKIE_NAME",
            current_app.config.get("ADMIN_COOKIE_NAME", "joybox_admin_session")
        )
        max_age = int(current_app.config.get("ADMIN_SESSION_LIFETIME_HOURS", 8)) * 3600
        is_secure = bool(current_app.config.get(
            "ADMIN_COOKIE_SECURE",
            current_app.config.get("SESSION_COOKIE_SECURE", False)
        ))
        samesite = current_app.config.get(
            "ADMIN_COOKIE_SAMESITE",
            current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax")
        )
        # Host-only. The browser talks to the Vercel host, which proxies /api
        # to Render, so a parent Domain attribute is not required and is ignored.
        resp.set_cookie(
            cookie_name,
            auth_data["sessionToken"],
            max_age=max_age,
            httponly=True,
            secure=is_secure,
            samesite=samesite,
            path="/api/admin"
        )
        return resp
    except AuthenticationError as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except AccountLockedError as e:
        return api_error(e.code, e.message, status_code=e.status_code)
    except Exception as e:
        logger.exception("Unexpected error in admin login")
        return api_error("INTERNAL_ERROR", "Login processing failed.", status_code=500)


@admin_bp.post("/auth/logout")
@require_admin_session
def logout():
    svc = get_admin_service()
    svc.logout(g.admin_session, _get_client_ip())

    cookie_name = current_app.config.get(
        "ADMIN_SESSION_COOKIE_NAME",
        current_app.config.get("ADMIN_COOKIE_NAME", "joybox_admin_session")
    )
    is_secure = bool(current_app.config.get(
        "ADMIN_COOKIE_SECURE",
        current_app.config.get("SESSION_COOKIE_SECURE", False)
    ))
    samesite = current_app.config.get(
        "ADMIN_COOKIE_SAMESITE",
        current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax")
    )
    resp = make_response(api_response(data={"message": "Logged out successfully."}))
    resp.delete_cookie(cookie_name, path="/api/admin", secure=is_secure, samesite=samesite)
    return resp


@admin_bp.get("/auth/me")
@require_admin_session
def get_current_user_profile():
    user = g.current_user
    session = g.admin_session
    return api_response(data={
        "user": {
            "id": str(user["_id"]),
            "username": user["username"],
            "displayName": user.get("displayName", user["username"].title()),
            "email": user.get("email", ""),
            "role": user.get("role", "staff")
        },
        "csrfToken": session.get("csrfToken", "")
    })


@admin_bp.post("/auth/change-password")
@require_admin_session
@require_csrf
def change_password():
    schema = AdminChangePasswordSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid password change payload.", status_code=400, details=err.messages)

    old_pwd = data.get("oldPassword") or data.get("currentPassword")
    svc = get_admin_service()
    try:
        svc.change_password(g.current_user["_id"], old_pwd, data["newPassword"], _get_client_ip())
        return api_response(data={"message": "Password changed successfully. Please log in with your new credentials."})
    except AuthenticationError as e:
        return api_error(e.code, e.message, status_code=e.status_code)


# ==============================================================================
# DASHBOARD KPI ENDPOINT
# ==============================================================================

@admin_bp.get("/dashboard")
@require_admin_session
def get_dashboard_kpis():
    db = current_app.extensions.get("mongo_db")
    now_u = now_utc()
    now_i = now_ist()

    today_str = now_i.strftime("%Y-%m-%d")

    # 1. Today's celebration bookings
    today_start = datetime(now_i.year, now_i.month, now_i.day, 0, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))).astimezone(timezone.utc)
    today_end = today_start + timedelta(days=1)

    today_bookings_count = db.bookings.count_documents({
        "startAt": {"$gte": today_start, "$lt": today_end},
        "bookingStatus": {"$in": ["confirmed", "completed"]}
    })

    # 2. Total revenue (sum of captured payments)
    revenue_agg = list(db.payments.aggregate([
        {"$match": {"status": "captured"}},
        {"$group": {"_id": None, "totalRevenueMinor": {"$sum": "$amountMinor"}}}
    ]))
    total_revenue_minor = revenue_agg[0]["totalRevenueMinor"] if revenue_agg else 0

    # 3. Monthly promo usage
    period_key = get_ist_period_key(now_u)
    promo_count = db.offerRedemptions.count_documents({
        "periodKey": period_key,
        "status": {"$in": ["reserved", "converted"]}
    })
    promo_limit = getattr(current_app.config, "PROMO_MONTHLY_LIMIT", 5)

    # 4. Inquiries needing attention
    pending_inquiries = db.inquiries.count_documents({"status": "new"})

    # 5. Payments needing review
    payments_needs_review = db.payments.count_documents({"needsReview": True})

    # 6. Recent bookings
    recent_cursor = db.bookings.find().sort("createdAt", -1).limit(5)
    recent_bookings = []
    for b in recent_cursor:
        recent_bookings.append({
            "bookingReference": b.get("bookingReference"),
            "customerName": b.get("customer", {}).get("name", ""),
            "customerPhone": b.get("customer", {}).get("phone", ""),
            "packageName": b.get("packageName", ""),
            "date": b.get("startAt", now_u).strftime("%Y-%m-%d"),
            "bookingStatus": b.get("bookingStatus"),
            "paymentStatus": b.get("paymentStatus"),
            "totalRupees": b.get("pricing", {}).get("totalRupees", 0),
        })

    return api_response(data={
        "todayBookingsCount": today_bookings_count,
        "totalRevenueMinor": total_revenue_minor,
        "totalRevenueRupees": total_revenue_minor / 100.0,
        "promoUsage": {
            "periodKey": period_key,
            "claimed": promo_count,
            "limit": promo_limit,
            "remaining": max(0, promo_limit - promo_count)
        },
        "pendingInquiriesCount": pending_inquiries,
        "paymentsNeedsReviewCount": payments_needs_review,
        "recentBookings": recent_bookings
    })


# ==============================================================================
# BOOKINGS MANAGEMENT ENDPOINTS
# ==============================================================================

@admin_bp.get("/bookings")
@require_admin_session
def list_bookings():
    db = current_app.extensions.get("mongo_db")
    booking_repo = BookingRepository(db)

    status_filter = request.args.get("status")
    payment_status = request.args.get("paymentStatus")
    search_term = request.args.get("search", "").strip()
    date_filter = request.args.get("date")

    query = {}
    if status_filter:
        query["bookingStatus"] = status_filter
    if payment_status:
        query["paymentStatus"] = payment_status
    if date_filter:
        # Match bookings overlapping the date in IST
        try:
            dt = datetime.strptime(date_filter, "%Y-%m-%d").replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
            start_u = dt.astimezone(timezone.utc)
            end_u = start_u + timedelta(days=1)
            query["startAt"] = {"$gte": start_u, "$lt": end_u}
        except ValueError:
            pass

    if search_term:
        query["$or"] = [
            {"bookingReference": {"$regex": search_term, "$options": "i"}},
            {"customer.name": {"$regex": search_term, "$options": "i"}},
            {"customer.phone": {"$regex": search_term, "$options": "i"}},
        ]

    limit = min(int(request.args.get("limit", 50)), 100)
    skip = int(request.args.get("skip", 0))

    total = booking_repo.count(query)
    bookings = booking_repo.find_all(query=query, limit=limit, skip=skip)

    res_list = []
    for b in bookings:
        res_list.append({
            "id": str(b["_id"]),
            "bookingReference": b["bookingReference"],
            "roomId": b.get("roomId", "main"),
            "packageName": b.get("packageName", ""),
            "durationHours": b.get("durationHours", 2),
            "startAt": b["startAt"].isoformat() if "startAt" in b else None,
            "endAt": b["endAt"].isoformat() if "endAt" in b else None,
            "startTimeIst": b.get("startTimeIst", ""),
            "endTimeIst": b.get("endTimeIst", ""),
            "customer": b.get("customer", {}),
            "celebrantName": b.get("celebrantName", ""),
            "celebrantAge": b.get("celebrantAge"),
            "occasionType": b.get("occasionType", "birthday"),
            "notes": b.get("notes", ""),
            "operationalNotes": b.get("operationalNotes", ""),
            "bookingStatus": b.get("bookingStatus"),
            "paymentStatus": b.get("paymentStatus"),
            "paymentMethod": b.get("paymentMethod", "online"),
            "pricing": b.get("pricing", {}),
            "createdAt": b.get("createdAt", now_utc()).isoformat()
        })

    return api_response(data={"bookings": res_list, "total": total, "limit": limit, "skip": skip})


@admin_bp.get("/bookings/<booking_ref>")
@require_admin_session
def get_booking_detail(booking_ref):
    db = current_app.extensions.get("mongo_db")
    booking_repo = BookingRepository(db)
    payment_repo = PaymentRepository(db)
    refund_repo = RefundRepository(db)

    booking = booking_repo.find_by_reference(booking_ref)
    if not booking:
        return api_error("NOT_FOUND", f"Booking '{booking_ref}' not found.", status_code=404)

    payments = payment_repo.find_by_booking_reference(booking_ref)
    refunds = refund_repo.find_by_booking_reference(booking_ref)

    booking_data = dict(booking)
    booking_data["id"] = str(booking["_id"])
    booking_data["_id"] = str(booking["_id"])
    booking_data.pop("accessTokenHash", None)

    return api_response(data={
        "booking": booking_data,
        "payments": payments,
        "refunds": refunds
    })


@admin_bp.patch("/bookings/<booking_ref>")
@require_admin_session
@require_role("owner", "manager", "staff")
@require_csrf
def update_booking(booking_ref):
    schema = AdminUpdateBookingSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid update payload.", status_code=400, details=err.messages)

    db = current_app.extensions.get("mongo_db")
    booking_repo = BookingRepository(db)
    slot_repo = SlotClaimRepository(db)
    offer_repo = OfferRepository(db)
    redemption_repo = OfferRedemptionRepository(db)
    admin_svc = get_admin_service()

    booking = booking_repo.find_by_reference(booking_ref)
    if not booking:
        return api_error("NOT_FOUND", f"Booking '{booking_ref}' not found.", status_code=404)

    role = g.current_user.get("role", "staff")
    now_u = now_utc()
    update_doc = {"updatedAt": now_u}

    # Staff can only update operationalNotes and celebrant info
    if role == "staff":
        if data.get("bookingStatus") or data.get("paymentStatus"):
            return api_error("FORBIDDEN", "Staff role cannot modify booking status or payment status.", status_code=403)
        if data.get("operationalNotes") is not None:
            update_doc["operationalNotes"] = data["operationalNotes"]
        if data.get("celebrantName") is not None:
            update_doc["celebrantName"] = data["celebrantName"]
        if data.get("occasionType") is not None:
            update_doc["occasionType"] = data["occasionType"]
    else:
        # Owner / Manager can update all fields
        if data.get("operationalNotes") is not None:
            update_doc["operationalNotes"] = data["operationalNotes"]
        if data.get("notes") is not None:
            update_doc["notes"] = data["notes"]
        if data.get("celebrantName") is not None:
            update_doc["celebrantName"] = data["celebrantName"]
        if data.get("celebrantAge") is not None:
            update_doc["celebrantAge"] = data["celebrantAge"]
        if data.get("occasionType") is not None:
            update_doc["occasionType"] = data["occasionType"]

        new_status = data.get("bookingStatus")
        if new_status and new_status != booking.get("bookingStatus"):
            update_doc["bookingStatus"] = new_status
            if new_status == "cancelled":
                update_doc["cancelledAt"] = now_u
                update_doc["cancellationReason"] = data.get("cancellationReason", "Cancelled by admin")
                # Release slots and promo quota
                slot_repo.release_by_owner(booking["_id"])
                released = redemption_repo.release_reservation_idempotent(booking["_id"], now_u)
                if released and released.get("offerId"):
                    offer_repo.atomic_release_slot(released["offerId"])

        if data.get("paymentStatus") is not None:
            update_doc["paymentStatus"] = data["paymentStatus"]

    updated = db.bookings.find_one_and_update(
        {"_id": booking["_id"]},
        {"$set": update_doc},
        return_document=True
    )

    admin_svc.write_audit_log(
        actor_id=g.current_user["_id"],
        actor_username=g.current_user["username"],
        actor_role=role,
        action="BOOKING_UPDATE",
        target_collection="bookings",
        target_id=str(booking["_id"]),
        details={"bookingReference": booking_ref, "changes": data},
        ip_address=_get_client_ip()
    )

    return api_response(data={"bookingReference": booking_ref, "updatedFields": list(update_doc.keys())})


@admin_bp.post("/bookings")
@require_admin_session
@require_role("owner", "manager")
@require_csrf
def create_manual_booking():
    """
    Creates an offline / manual booking with atomic slot claim guarantee.
    Enforces that manual bookings never collide with online reservations.
    """
    schema = AdminCreateBookingSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid manual booking payload.", status_code=400, details=err.messages)

    db = current_app.extensions.get("mongo_db")
    booking_repo = BookingRepository(db)
    slot_repo = SlotClaimRepository(db)
    counter_repo = CounterRepository(db)
    pkg_repo = PackageRepository(db)
    addon_repo = AddOnRepository(db)
    admin_svc = get_admin_service()

    now_u = now_utc()
    now_i = now_ist()
    room_id = data.get("roomId", "main")

    # Validate window
    start_utc, end_utc, buffer_end_utc = validate_booking_window(
        data["date"], data["startTime"], data["durationHours"], current_app.config
    )

    # Validate package
    pkg = pkg_repo.find_by_code(data["packageCode"])
    if not pkg:
        return api_error("RESOURCE_NOT_FOUND", f"Package '{data['packageCode']}' not found.", status_code=404)

    # Calculate pricing
    base_minor = pkg["pricePerHourMinor"] * data["durationHours"]
    addons_minor = 0
    addons_selected = []
    for code in data.get("addOnCodes", []):
        add = addon_repo.find_by_code(code)
        if add:
            addons_selected.append(add)
            addons_minor += add["priceMinor"]

    total_minor = base_minor + addons_minor

    # Generate aligned slot claims
    intervals = generate_slot_claim_intervals(
        start_utc, end_utc, current_app.config.get("BUFFER_MINUTES", 30), current_app.config.get("SLOT_UNIT_MINUTES", 30)
    )

    new_booking_id = ObjectId()
    claim_docs = [{
        "roomId": room_id,
        "date": data["date"],
        "slotStart": inv["slotStart"],
        "slotEnd": inv["slotEnd"],
        "isBuffer": inv["isBuffer"],
        "ownerType": "booking",
        "ownerId": new_booking_id,
        "createdAt": now_u,
        "expiresAt": None
    } for inv in intervals]

    # Atomically lock slots
    claimed = slot_repo.claim_all_or_rollback(claim_docs)
    if not claimed:
        return api_error("SLOT_UNAVAILABLE", "The requested time slot conflicts with an existing booking or block.", status_code=409)

    current_year = now_i.year
    seq_num = counter_repo.get_next_sequence(f"booking_{current_year}")
    booking_ref = f"JBX-{current_year}-{seq_num:04d}"

    booking_doc = {
        "_id": new_booking_id,
        "bookingReference": booking_ref,
        "roomId": room_id,
        "packageCode": pkg["code"],
        "packageName": pkg["name"],
        "durationHours": data["durationHours"],
        "startAt": start_utc,
        "endAt": end_utc,
        "bufferEndAt": buffer_end_utc,
        "startTimeIst": f"{data['date']} {data['startTime']} IST",
        "endTimeIst": f"{data['date']} {format_ist_time(end_utc)} IST",
        "pricing": {
            "baseAmountMinor": base_minor,
            "addOnsAmountMinor": addons_minor,
            "discountAmountMinor": 0,
            "totalAmountMinor": total_minor,
            "totalRupees": total_minor / 100.0,
            "currency": "INR",
            "promoApplied": False
        },
        "customer": {
            "name": data["customerName"],
            "phone": data["customerPhone"],
            "email": data.get("customerEmail", "")
        },
        "celebrantName": data.get("celebrantName", ""),
        "celebrantAge": data.get("celebrantAge"),
        "occasionType": data.get("occasionType", "birthday"),
        "notes": data["notes"],
        "operationalNotes": f"Manual booking by {g.current_user['username']} ({data.get('paymentMethod', 'offline')})",
        "bookingStatus": "confirmed",
        "paymentStatus": "paid",
        "paymentMethod": data.get("paymentMethod", "offline"),
        "confirmedAt": now_u,
        "createdAt": now_u,
        "updatedAt": now_u
    }

    booking_repo.insert(booking_doc)

    # Record offline payment
    payment_repo = PaymentRepository(db)
    payment_repo.insert({
        "_id": ObjectId(),
        "bookingId": new_booking_id,
        "bookingReference": booking_ref,
        "provider": "offline",
        "providerOrderId": f"offline_{booking_ref}",
        "providerPaymentId": f"pay_offline_{booking_ref}",
        "amountMinor": total_minor,
        "currency": "INR",
        "status": "captured",
        "paymentMethod": data.get("paymentMethod", "offline"),
        "createdAt": now_u,
        "updatedAt": now_u
    })

    admin_svc.write_audit_log(
        actor_id=g.current_user["_id"],
        actor_username=g.current_user["username"],
        actor_role=g.current_user.get("role", "manager"),
        action="OFFLINE_BOOKING_CREATE",
        target_collection="bookings",
        target_id=str(new_booking_id),
        details={"bookingReference": booking_ref, "amountMinor": total_minor, "notes": data["notes"]},
        ip_address=_get_client_ip()
    )

    return api_response(data={
        "bookingReference": booking_ref,
        "status": "confirmed",
        "totalRupees": total_minor / 100.0,
        "message": "Manual reservation created successfully."
    }, status_code=201)


# ==============================================================================
# AVAILABILITY BLOCKS (MAINTENANCE / CLOSURES)
# ==============================================================================

@admin_bp.get("/availability-blocks")
@require_admin_session
def list_availability_blocks():
    db = current_app.extensions.get("mongo_db")
    block_repo = AvailabilityBlockRepository(db)
    blocks = block_repo.find_all()
    res = []
    for b in blocks:
        res.append({
            "id": str(b["_id"]),
            "roomId": b["roomId"],
            "startAt": b["startAt"].isoformat(),
            "endAt": b["endAt"].isoformat(),
            "reason": b.get("reason", ""),
            "createdAt": b.get("createdAt", now_utc()).isoformat()
        })
    return api_response(data={"blocks": res})


@admin_bp.post("/availability-blocks")
@require_admin_session
@require_role("owner", "manager")
@require_csrf
def create_availability_block():
    schema = AdminCreateAvailabilityBlockSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid block parameters.", status_code=400, details=err.messages)

    db = current_app.extensions.get("mongo_db")
    block_repo = AvailabilityBlockRepository(db)
    slot_repo = SlotClaimRepository(db)
    admin_svc = get_admin_service()

    now_u = now_utc()
    room_id = data.get("roomId", "main")

    start_utc, end_utc, _ = validate_booking_window(
        data["date"], data["startTime"], data["durationHours"], current_app.config
    )

    intervals = generate_slot_claim_intervals(start_utc, end_utc, 0, current_app.config.get("SLOT_UNIT_MINUTES", 30))

    block_id = ObjectId()
    claim_docs = [{
        "roomId": room_id,
        "date": data["date"],
        "slotStart": inv["slotStart"],
        "slotEnd": inv["slotEnd"],
        "isBuffer": False,
        "ownerType": "block",
        "ownerId": block_id,
        "createdAt": now_u,
        "expiresAt": None
    } for inv in intervals]

    # Atomically lock slots against customer reservations
    claimed = slot_repo.claim_all_or_rollback(claim_docs)
    if not claimed:
        return api_error("SLOT_UNAVAILABLE", "Cannot block slot: an active booking already occupies this window.", status_code=409)

    block_doc = {
        "_id": block_id,
        "roomId": room_id,
        "startAt": start_utc,
        "endAt": end_utc,
        "reason": data["reason"],
        "createdBy": g.current_user["_id"],
        "createdAt": now_u,
        "updatedAt": now_u
    }
    block_repo.insert(block_doc)

    admin_svc.write_audit_log(
        actor_id=g.current_user["_id"],
        actor_username=g.current_user["username"],
        actor_role=g.current_user.get("role", "manager"),
        action="AVAILABILITY_BLOCK_CREATE",
        target_collection="availabilityBlocks",
        target_id=str(block_id),
        details={"roomId": room_id, "startAt": start_utc.isoformat(), "endAt": end_utc.isoformat(), "reason": data["reason"]},
        ip_address=_get_client_ip()
    )

    return api_response(data={"id": str(block_id), "message": "Availability block created successfully."}, status_code=201)


@admin_bp.delete("/availability-blocks/<block_id>")
@require_admin_session
@require_role("owner", "manager")
@require_csrf
def delete_availability_block(block_id):
    db = current_app.extensions.get("mongo_db")
    block_repo = AvailabilityBlockRepository(db)
    slot_repo = SlotClaimRepository(db)
    admin_svc = get_admin_service()

    block = block_repo.find_by_id(block_id)
    if not block:
        return api_error("NOT_FOUND", "Availability block not found.", status_code=404)

    # Release slots
    slot_repo.release_by_owner(block["_id"])
    block_repo.delete_by_id(block["_id"])

    admin_svc.write_audit_log(
        actor_id=g.current_user["_id"],
        actor_username=g.current_user["username"],
        actor_role=g.current_user.get("role", "manager"),
        action="AVAILABILITY_BLOCK_DELETE",
        target_collection="availabilityBlocks",
        target_id=str(block_id),
        details={"reason": block.get("reason")},
        ip_address=_get_client_ip()
    )

    return api_response(data={"message": "Availability block deleted and slots released."})


# ==============================================================================
# PACKAGES & ADD-ONS MANAGEMENT
# ==============================================================================

@admin_bp.get("/packages")
@require_admin_session
def admin_list_packages():
    db = current_app.extensions.get("mongo_db")
    pkg_repo = PackageRepository(db)
    packages = pkg_repo.find_all(active_only=False)
    for p in packages:
        p["id"] = str(p["_id"])
        p["_id"] = str(p["_id"])
    return api_response(data={"packages": packages})


@admin_bp.post("/packages")
@require_admin_session
@require_role("owner")
@require_csrf
def admin_create_package():
    schema = AdminCreatePackageSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid package payload.", status_code=400, details=err.messages)

    db = current_app.extensions.get("mongo_db")
    pkg_repo = PackageRepository(db)
    admin_svc = get_admin_service()

    existing = pkg_repo.find_by_code(data["code"])
    if existing:
        return api_error("CONFLICT", f"Package with code '{data['code']}' already exists.", status_code=409)

    doc = dict(data)
    doc["_id"] = ObjectId()
    doc["createdAt"] = now_utc()
    doc["updatedAt"] = now_utc()
    pkg_repo.insert(doc)

    admin_svc.write_audit_log(
        actor_id=g.current_user["_id"],
        actor_username=g.current_user["username"],
        actor_role="owner",
        action="PACKAGE_CREATE",
        target_collection="packages",
        target_id=str(doc["_id"]),
        details={"code": data["code"], "pricePerHourMinor": data["pricePerHourMinor"]},
        ip_address=_get_client_ip()
    )

    return api_response(data={"code": data["code"], "message": "Package created successfully."}, status_code=201)


@admin_bp.patch("/packages/<code_or_id>")
@require_admin_session
@require_role("owner", "manager")
@require_csrf
def admin_update_package(code_or_id):
    schema = AdminUpdatePackageSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid package update payload.", status_code=400, details=err.messages)

    db = current_app.extensions.get("mongo_db")
    pkg_repo = PackageRepository(db)
    admin_svc = get_admin_service()

    pkg = pkg_repo.find_by_code(code_or_id)
    if not pkg and ObjectId.is_valid(code_or_id):
        pkg = db.packages.find_one({"_id": ObjectId(code_or_id)})

    if not pkg:
        return api_error("NOT_FOUND", f"Package '{code_or_id}' not found.", status_code=404)

    update_fields = {k: v for k, v in data.items() if v is not None}
    update_fields["updatedAt"] = now_utc()

    db.packages.update_one({"_id": pkg["_id"]}, {"$set": update_fields})

    admin_svc.write_audit_log(
        actor_id=g.current_user["_id"],
        actor_username=g.current_user["username"],
        actor_role=g.current_user.get("role", "manager"),
        action="PACKAGE_UPDATE",
        target_collection="packages",
        target_id=str(pkg["_id"]),
        details={"changes": update_fields},
        ip_address=_get_client_ip()
    )

    return api_response(data={"message": "Package updated successfully."})


@admin_bp.get("/add-ons")
@require_admin_session
def admin_list_addons():
    db = current_app.extensions.get("mongo_db")
    addon_repo = AddOnRepository(db)
    addons = addon_repo.find_all(active_only=False)
    for a in addons:
        a["id"] = str(a["_id"])
        a["_id"] = str(a["_id"])
    return api_response(data={"addOns": addons})


@admin_bp.post("/add-ons")
@require_admin_session
@require_role("owner", "manager")
@require_csrf
def admin_create_addon():
    schema = AdminCreateAddOnSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid add-on payload.", status_code=400, details=err.messages)

    db = current_app.extensions.get("mongo_db")
    addon_repo = AddOnRepository(db)
    admin_svc = get_admin_service()

    existing = addon_repo.find_by_code(data["code"])
    if existing:
        return api_error("CONFLICT", f"Add-on with code '{data['code']}' already exists.", status_code=409)

    doc = dict(data)
    doc["_id"] = ObjectId()
    doc["createdAt"] = now_utc()
    doc["updatedAt"] = now_utc()
    addon_repo.insert(doc)

    admin_svc.write_audit_log(
        actor_id=g.current_user["_id"],
        actor_username=g.current_user["username"],
        actor_role=g.current_user.get("role", "manager"),
        action="ADDON_CREATE",
        target_collection="addOns",
        target_id=str(doc["_id"]),
        details={"code": data["code"], "priceMinor": data["priceMinor"]},
        ip_address=_get_client_ip()
    )

    return api_response(data={"code": data["code"], "message": "Add-on created successfully."}, status_code=201)


@admin_bp.patch("/add-ons/<code_or_id>")
@require_admin_session
@require_role("owner", "manager")
@require_csrf
def admin_update_addon(code_or_id):
    schema = AdminUpdateAddOnSchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid add-on update payload.", status_code=400, details=err.messages)

    db = current_app.extensions.get("mongo_db")
    addon_repo = AddOnRepository(db)
    admin_svc = get_admin_service()

    add = addon_repo.find_by_code(code_or_id)
    if not add and ObjectId.is_valid(code_or_id):
        add = db.addOns.find_one({"_id": ObjectId(code_or_id)})

    if not add:
        return api_error("NOT_FOUND", f"Add-on '{code_or_id}' not found.", status_code=404)

    update_fields = {k: v for k, v in data.items() if v is not None}
    update_fields["updatedAt"] = now_utc()

    db.addOns.update_one({"_id": add["_id"]}, {"$set": update_fields})

    admin_svc.write_audit_log(
        actor_id=g.current_user["_id"],
        actor_username=g.current_user["username"],
        actor_role=g.current_user.get("role", "manager"),
        action="ADDON_UPDATE",
        target_collection="addOns",
        target_id=str(add["_id"]),
        details={"changes": update_fields},
        ip_address=_get_client_ip()
    )

    return api_response(data={"message": "Add-on updated successfully."})


# ==============================================================================
# INQUIRIES MANAGEMENT
# ==============================================================================

@admin_bp.get("/inquiries")
@require_admin_session
def admin_list_inquiries():
    db = current_app.extensions.get("mongo_db")
    status_filter = request.args.get("status")
    query = {"status": status_filter} if status_filter else {}
    limit = min(int(request.args.get("limit", 50)), 100)
    skip = int(request.args.get("skip", 0))

    cursor = db.inquiries.find(query).sort("createdAt", -1).skip(skip).limit(limit)
    inquiries = list(cursor)
    for inq in inquiries:
        inq["id"] = str(inq["_id"])
        inq["_id"] = str(inq["_id"])
    total = db.inquiries.count_documents(query)

    return api_response(data={"inquiries": inquiries, "total": total, "limit": limit, "skip": skip})


@admin_bp.patch("/inquiries/<inquiry_id>")
@require_admin_session
@require_csrf
def admin_update_inquiry(inquiry_id):
    schema = AdminUpdateInquirySchema()
    try:
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return api_error("VALIDATION_ERROR", "Invalid inquiry update payload.", status_code=400, details=err.messages)

    db = current_app.extensions.get("mongo_db")
    if not ObjectId.is_valid(inquiry_id):
        return api_error("NOT_FOUND", "Invalid inquiry ID.", status_code=404)

    now_u = now_utc()
    res = db.inquiries.update_one(
        {"_id": ObjectId(inquiry_id)},
        {"$set": {"status": data["status"], "adminNotes": data.get("adminNotes", ""), "updatedAt": now_u}}
    )

    if res.matched_count == 0:
        return api_error("NOT_FOUND", "Inquiry not found.", status_code=404)

    return api_response(data={"message": "Inquiry status updated."})


# ==============================================================================
# PAYMENTS & REFUNDS RETRY
# ==============================================================================

@admin_bp.get("/payments")
@require_admin_session
@require_role("owner", "manager")
def admin_list_payments():
    db = current_app.extensions.get("mongo_db")
    needs_review = request.args.get("needsReview")

    query = {}
    if needs_review and needs_review.lower() == "true":
        query["needsReview"] = True

    cursor = db.payments.find(query).sort("createdAt", -1).limit(100)
    payments = list(cursor)
    for p in payments:
        p["id"] = str(p["_id"])
        p["_id"] = str(p["_id"])
        p["bookingId"] = str(p.get("bookingId", ""))

    return api_response(data={"payments": payments})


@admin_bp.post("/payments/<refund_id>/retry-refund")
@require_admin_session
@require_role("owner", "manager")
@require_csrf
def admin_retry_refund(refund_id):
    svc = get_payment_service()
    admin_svc = get_admin_service()

    try:
        res = svc.retry_refund(refund_id)
        admin_svc.write_audit_log(
            actor_id=g.current_user["_id"],
            actor_username=g.current_user["username"],
            actor_role=g.current_user.get("role", "manager"),
            action="REFUND_RETRY",
            target_collection="refunds",
            target_id=refund_id,
            details=res,
            ip_address=_get_client_ip()
        )
        return api_response(data=res)
    except Exception as e:
        logger.exception("Failed to retry refund")
        return api_error("GATEWAY_ERROR", str(e), status_code=502)


# ==============================================================================
# AUDIT LOGS
# ==============================================================================

@admin_bp.get("/audit-logs")
@require_admin_session
@require_role("owner", "manager")
def admin_list_audit_logs():
    db = current_app.extensions.get("mongo_db")
    audit_repo = AuditLogRepository(db)

    actor_filter = request.args.get("actor")
    action_filter = request.args.get("action")
    collection_filter = request.args.get("collection")

    query = {}
    if actor_filter:
        query["actorUsername"] = actor_filter
    if action_filter:
        query["action"] = action_filter
    if collection_filter:
        query["targetCollection"] = collection_filter

    limit = min(int(request.args.get("limit", 50)), 100)
    skip = int(request.args.get("skip", 0))

    logs = audit_repo.find_all(query=query, limit=limit, skip=skip)
    for log in logs:
        log["id"] = str(log["_id"])
        log["_id"] = str(log["_id"])
        if log.get("actorId"):
            log["actorId"] = str(log["actorId"])
        if isinstance(log.get("createdAt"), datetime):
            log["createdAt"] = log["createdAt"].isoformat()

    total = audit_repo.count(query)
    return api_response(data={"auditLogs": logs, "total": total, "limit": limit, "skip": skip})

