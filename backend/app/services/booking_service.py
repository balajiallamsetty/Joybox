import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from ..config import Config
from ..utils.datetime_utils import (
    now_utc,
    now_ist,
    to_utc,
    ensure_utc,
    to_ist,
    parse_ist_datetime,
    format_ist_time,
    format_ist_date,
    format_ist_display,
    get_ist_period_key,
    generate_slot_claim_intervals,
    validate_booking_window,
)
from ..utils.helpers import mask_phone, format_customer_display_name, serialize_doc
from ..utils.exceptions import (
    SlotUnavailableError,
    HoldExpiredError,
    PromoExhaustedError,
    IdempotencyConflictError,
    IdempotencyPayloadMismatchError,
    ResourceNotFoundError,
    InvalidBookingStateError,
    RateLimitExceededError,
)

class ConfigAdapter:
    def __init__(self, config_obj):
        self._cfg = config_obj

    def __getattr__(self, name):
        if hasattr(self._cfg, name):
            val = getattr(self._cfg, name)
            if val is not None:
                return val
        if hasattr(self._cfg, "get"):
            val = self._cfg.get(name)
            if val is not None:
                return val
        if hasattr(Config, name):
            return getattr(Config, name)
        raise AttributeError(f"Configuration key '{name}' not found.")

class BookingService:
    def __init__(
        self,
        slot_claim_repo,
        hold_repo,
        booking_repo,
        counter_repo,
        offer_repo,
        offer_redemption_repo,
        idempotency_repo,
        package_repo,
        addon_repo,
        rate_limit_repo=None,
        config=None,
    ):
        self.slot_claim_repo = slot_claim_repo
        self.hold_repo = hold_repo
        self.booking_repo = booking_repo
        self.counter_repo = counter_repo
        self.offer_repo = offer_repo
        self.offer_redemption_repo = offer_redemption_repo
        self.idempotency_repo = idempotency_repo
        self.package_repo = package_repo
        self.addon_repo = addon_repo
        self.rate_limit_repo = rate_limit_repo
        self.config = ConfigAdapter(config or Config)

    def sweep_expired_holds(self, now_utc_val=None) -> int:
        """
        Sweeps all active booking holds that have passed their expiration time.
        Releases slot claims and promo allocations idempotently.
        Callable on request access and by scheduled background task.
        """
        now_u = now_utc_val or now_utc()
        if self.hold_repo.collection is None:
            return 0

        expired_cursor = self.hold_repo.collection.find({
            "status": "active",
            "expiresAt": {"$lte": now_u}
        })
        expired_holds = list(expired_cursor)
        swept_count = 0

        for hold in expired_holds:
            hold_id = hold["_id"]
            # Transition hold to expired
            self.hold_repo.transition_status(hold_id, "active", "expired")
            # Release slot claims
            self.slot_claim_repo.release_by_owner(hold_id)
            # Idempotently release promo reservation
            released = self.offer_redemption_repo.release_reservation_idempotent(hold_id, now_u)
            if released and released.get("offerId"):
                self.offer_repo.atomic_release_slot(released["offerId"])
            swept_count += 1

        return swept_count

    def get_availability(self, date_str: str, duration_hours: int = 1, room_id: str = "main") -> dict:
        """
        Calculates time slot availability for the given date, duration, and room.
        Operating hours: OPENING_HOUR_IST (09:00) to CLOSING_HOUR_IST (22:00) IST.
        Buffer between bookings: BUFFER_MINUTES (30 mins).
        """
        if not (self.config.MIN_DURATION_HOURS <= duration_hours <= self.config.MAX_DURATION_HOURS):
            raise ValueError(f"Duration must be between {self.config.MIN_DURATION_HOURS} and {self.config.MAX_DURATION_HOURS} hours.")

        now_u = now_utc()
        now_i = now_ist()

        # Reject queries beyond max advance window
        max_advance_days = getattr(self.config, "MAX_ADVANCE_BOOKING_DAYS", 90)
        start_of_day_ist = parse_ist_datetime(date_str, f"{self.config.OPENING_HOUR_IST:02d}:00")
        if start_of_day_ist.date() > (now_i + timedelta(days=max_advance_days)).date():
            raise ValueError(f"Availability cannot be queried more than {max_advance_days} days in advance.")

        # Lazy sweep of any expired holds before querying availability
        self.sweep_expired_holds(now_u)

        slots = []
        max_start_hour = self.config.CLOSING_HOUR_IST - duration_hours

        for hour in range(self.config.OPENING_HOUR_IST, max_start_hour + 1):
            time_str = f"{hour:02d}:00"
            start_ist = parse_ist_datetime(date_str, time_str)
            end_ist = start_ist + timedelta(hours=duration_hours)

            start_utc = to_utc(start_ist)
            end_utc = to_utc(end_ist)
            buffer_end_utc = end_utc + timedelta(minutes=self.config.BUFFER_MINUTES)

            # Check if in the past
            if start_ist < now_i:
                slots.append({
                    "startTime": time_str,
                    "endTime": end_ist.strftime("%H:%M"),
                    "startAt": start_utc.isoformat().replace("+00:00", "Z"),
                    "endAt": end_utc.isoformat().replace("+00:00", "Z"),
                    "available": False,
                    "unavailableReason": "past"
                })
                continue

            # Query existing active claims covering the event + buffer window
            claims = self.slot_claim_repo.find_claims_in_range(room_id, start_utc, buffer_end_utc, now_u)
            if claims:
                # Slot or buffer is taken
                has_booking = any(c.get("ownerType") == "booking" for c in claims)
                has_hold = any(c.get("ownerType") == "hold" for c in claims)
                has_buffer_overlap = any(c.get("isBuffer", False) for c in claims)

                if has_booking:
                    reason = "booked"
                elif has_hold:
                    reason = "hold"
                elif has_buffer_overlap:
                    reason = "buffer"
                else:
                    reason = "unavailable"

                slots.append({
                    "startTime": time_str,
                    "endTime": end_ist.strftime("%H:%M"),
                    "startAt": start_utc.isoformat().replace("+00:00", "Z"),
                    "endAt": end_utc.isoformat().replace("+00:00", "Z"),
                    "available": False,
                    "unavailableReason": reason
                })
            else:
                slots.append({
                    "startTime": time_str,
                    "endTime": end_ist.strftime("%H:%M"),
                    "startAt": start_utc.isoformat().replace("+00:00", "Z"),
                    "endAt": end_utc.isoformat().replace("+00:00", "Z"),
                    "available": True
                })

        return {
            "date": date_str,
            "roomId": room_id,
            "durationHours": duration_hours,
            "timezone": self.config.TIMEZONE_IST,
            "openingTime": f"{self.config.OPENING_HOUR_IST:02d}:00",
            "closingTime": f"{self.config.CLOSING_HOUR_IST:02d}:00",
            "bufferMinutes": self.config.BUFFER_MINUTES,
            "slots": slots
        }

    def _compute_price_quote(self, package_code: str, duration_hours: int, add_on_codes: list, apply_promo: bool = True, event_date: str = None, customer_phone: str = None, gst_rate_percent: float = None):
        """Authoritatively computes price quote and line items directly from active DB records."""
        pkg = self.package_repo.find_by_code(package_code)
        if not pkg:
            raise ValueError(f"Package '{package_code}' not found or inactive")

        add_on_codes = add_on_codes or []
        included_codes = set(pkg.get("includedAddOnCodes", []))
        duplicate_addons = set(add_on_codes).intersection(included_codes)
        if duplicate_addons:
            raise ValueError(f"Selected add-on(s) {list(duplicate_addons)} are already included in the {pkg['name']} package.")

        selected_addons = self.addon_repo.find_by_codes(add_on_codes)
        found_codes = {a["code"] for a in selected_addons}
        missing_codes = set(add_on_codes) - found_codes
        if missing_codes:
            raise ValueError(f"Add-on(s) {list(missing_codes)} not found or inactive")

        base_minor = pkg["pricePerHourMinor"] * duration_hours
        addons_minor = sum(a["priceMinor"] for a in selected_addons)

        line_items = [
            {
                "description": f"{pkg['name']} package ({duration_hours} hr{'s' if duration_hours > 1 else ''} × ₹{pkg['pricePerHourMinor'] // 100}/hr)",
                "amountMinor": base_minor,
                "amountRupees": base_minor / 100.0
            }
        ]
        for a in selected_addons:
            line_items.append({
                "description": a["name"],
                "amountMinor": a["priceMinor"],
                "amountRupees": a["priceMinor"] / 100.0
            })

        promo_offer = None
        promo_applied = False
        promo_not_applied_reason = None
        discount_minor = 0

        if apply_promo:
            offer = self.offer_repo.find_by_package(package_code)
            if offer and offer.get("isActive", True):
                # 1. Validity Window Check
                valid_from = offer.get("validFrom")
                valid_until = offer.get("validUntil")
                check_date = event_date or now_ist().strftime("%Y-%m-%d")

                if valid_from and check_date < valid_from:
                    promo_not_applied_reason = f"Promotional offer starts on {valid_from}."
                elif valid_until and check_date > valid_until:
                    promo_not_applied_reason = f"Promotional offer ended on {valid_until}."
                else:
                    # 2. Per-Customer Limit Check
                    max_per_customer = offer.get("maxPerCustomer", 1)
                    norm_phone = "".join([c for c in str(customer_phone or "") if c.isdigit()])[-10:]
                    user_redemptions = 0
                    if norm_phone and self.offer_redemption_repo:
                        user_redemptions = self.offer_redemption_repo.count_by_phone_and_offer(norm_phone, offer["_id"])

                    if norm_phone and user_redemptions >= max_per_customer:
                        promo_not_applied_reason = f"Promotional quota limit reached ({max_per_customer} per customer)."
                    else:
                        # 3. Monthly Quota Check
                        limit = offer.get("monthlyLimit", 5)
                        used = offer.get("monthlyRedemptionCount", 0)
                        if used < limit:
                            # 4. Percent vs Flat vs Hourly calculation with paise precision
                            if offer.get("discountPercent"):
                                pct = float(offer["discountPercent"])
                                discount_minor = round(base_minor * (pct / 100.0))
                            elif offer.get("discountFlatMinor"):
                                discount_minor = min(base_minor, int(offer["discountFlatMinor"]))
                            else:
                                promo_price_minor = offer.get("promoPricePerHourMinor", pkg["pricePerHourMinor"])
                                discount_per_hour = pkg["pricePerHourMinor"] - promo_price_minor
                                discount_minor = max(0, discount_per_hour * duration_hours)

                            if discount_minor > 0:
                                promo_applied = True
                                promo_offer = offer
                                line_items.append({
                                    "description": f"Promotional Offer ({offer['name']})",
                                    "amountMinor": -discount_minor,
                                    "amountRupees": -(discount_minor / 100.0)
                                })
                        else:
                            promo_not_applied_reason = f"Monthly promotional quota ({limit} bookings) already claimed."
            else:
                promo_not_applied_reason = f"No active promotion applicable for {pkg['name']} package."

        taxable_minor = max(0, base_minor + addons_minor - discount_minor)
        tax_rate = float(gst_rate_percent if gst_rate_percent is not None else getattr(self.config, "GST_PERCENT", 0.0) if hasattr(self, "config") else 0.0)
        if tax_rate > 0:
            tax_minor = round(taxable_minor * (tax_rate / 100.0))
            line_items.append({
                "description": f"GST ({tax_rate:g}%)",
                "amountMinor": tax_minor,
                "amountRupees": tax_minor / 100.0
            })
        else:
            tax_minor = 0

        total_minor = taxable_minor + tax_minor

        pricing = {
            "packageCode": pkg["code"],
            "packageName": pkg["name"],
            "durationHours": duration_hours,
            "currency": "INR",
            "lineItems": line_items,
            "baseAmountMinor": base_minor,
            "addOnsAmountMinor": addons_minor,
            "promoApplied": promo_applied,
            "promoNotAppliedReason": promo_not_applied_reason,
            "discountAmountMinor": discount_minor,
            "taxAmountMinor": tax_minor,
            "taxRatePercent": tax_rate,
            "totalAmountMinor": total_minor,
            "totalRupees": total_minor / 100.0,
        }

        return pkg, selected_addons, pricing, promo_offer

    def create_hold(self, payload: dict, idempotency_key: str = None, client_ip: str = None) -> dict:
        """
        Atomically locks unit slot intervals for HOLD_DURATION_MINUTES.
        If promotional quota is requested and available, atomically claims promo slot.
        Rolls back all slot insertions if any collision occurs.
        Enforces rate limits per IP and per customer phone.
        """
        now_u = now_utc()

        # Enforce rate limits to prevent slot hoarding
        if self.rate_limit_repo:
            if client_ip:
                ip_ok = self.rate_limit_repo.check_and_increment(
                    f"hold_ip:{client_ip}",
                    self.config.RATE_LIMIT_HOLD_PER_IP_WINDOW,
                    self.config.RATE_LIMIT_HOLD_PER_IP_MAX,
                    now_u
                )
                if not ip_ok:
                    raise RateLimitExceededError("Too many hold requests from this network. Please wait a minute.")

            raw_phone = payload.get("customerPhone", "")
            norm_phone = "".join([c for c in raw_phone if c.isdigit()])[-10:]
            if norm_phone:
                phone_ok = self.rate_limit_repo.check_and_increment(
                    f"hold_phone:{norm_phone}",
                    self.config.RATE_LIMIT_HOLD_PER_PHONE_WINDOW,
                    self.config.RATE_LIMIT_HOLD_PER_PHONE_MAX,
                    now_u
                )
                if not phone_ok:
                    raise RateLimitExceededError("Too many active reservation attempts for this phone number. Please complete or release existing requests.")

        # Sweep expired holds to free up slots
        self.sweep_expired_holds(now_u)

        room_id = payload.get("roomId", self.config.DEFAULT_ROOM_ID)
        date_str = payload["date"]
        time_str = payload["startTime"]
        duration_hours = payload["durationHours"]

        # Validate time window against business constraints
        start_utc, end_utc, buffer_end_utc = validate_booking_window(
            date_str, time_str, duration_hours, self.config
        )

        expires_at = now_u + timedelta(minutes=self.config.HOLD_DURATION_MINUTES)

        # Generate aligned 30-min unit slot intervals (party + post-event buffer)
        intervals = generate_slot_claim_intervals(
            start_utc, end_utc, self.config.BUFFER_MINUTES, self.config.SLOT_UNIT_MINUTES
        )

        # Conditionally reclaim expired holds on these target slots prior to insertion
        slot_starts = [inv["slotStart"] for inv in intervals]
        self.slot_claim_repo.reclaim_expired_holds(room_id, slot_starts, now_u)

        # Compute price quote and check promo eligibility
        pkg, selected_addons, pricing, promo_offer = self._compute_price_quote(
            package_code=payload["packageCode"],
            duration_hours=duration_hours,
            add_on_codes=payload.get("addOnCodes", []),
            apply_promo=payload.get("applyPromo", True),
            event_date=payload.get("date"),
            customer_phone=payload.get("customerPhone"),
            gst_rate_percent=payload.get("gstRatePercent")
        )

        hold_id = ObjectId()
        promo_reserved = False

        if promo_offer and pricing.get("promoApplied", False):
            # Atomically claim promo slot in offers collection
            updated_offer = self.offer_repo.atomic_claim_slot(
                promo_offer["_id"], promo_offer.get("monthlyLimit", 5)
            )
            if updated_offer:
                promo_reserved = True
                norm_phone = "".join([c for c in str(payload.get("customerPhone", "")) if c.isdigit()])[-10:]
                self.offer_redemption_repo.insert_reservation({
                    "offerId": promo_offer["_id"],
                    "holdId": hold_id,
                    "customerPhone": norm_phone,
                    "periodKey": get_ist_period_key(start_utc),
                    "status": "reserved",
                    "createdAt": now_u,
                    "updatedAt": now_u
                })
            else:
                # Quota exhausted right before reservation; recompute quote without promo
                pkg, selected_addons, pricing, promo_offer = self._compute_price_quote(
                    package_code=payload["packageCode"],
                    duration_hours=duration_hours,
                    add_on_codes=payload.get("addOnCodes", []),
                    apply_promo=False,
                    event_date=payload.get("date"),
                    customer_phone=payload.get("customerPhone"),
                    gst_rate_percent=payload.get("gstRatePercent")
                )
                pricing["promoNotAppliedReason"] = "Promotional offer quota was claimed concurrently."
                pricing["discountAmountMinor"] = 0
                pricing["totalAmountMinor"] = pricing["baseAmountMinor"] + pricing["addOnsAmountMinor"]
                pricing["totalRupees"] = pricing["totalAmountMinor"] / 100.0
                pricing["lineItems"] = [item for item in pricing["lineItems"] if "Promotional" not in item["description"]]

        # Build claim documents
        claim_docs = []
        for inv in intervals:
            claim_docs.append({
                "roomId": room_id,
                "date": date_str,
                "slotStart": inv["slotStart"],
                "slotEnd": inv["slotEnd"],
                "isBuffer": inv["isBuffer"],
                "ownerType": "hold",
                "ownerId": hold_id,
                "createdAt": now_u,
                "expiresAt": expires_at
            })

        # Atomically claim slots
        claimed = self.slot_claim_repo.claim_all_or_rollback(claim_docs)
        if not claimed:
            # Rollback promo reservation if reserved
            if promo_reserved:
                released = self.offer_redemption_repo.release_reservation_idempotent(hold_id, now_u)
                if released:
                    self.offer_repo.atomic_release_slot(promo_offer["_id"])
            raise SlotUnavailableError("The requested celebration time slot is no longer available.")

        # Create booking hold document
        hold_doc = {
            "_id": hold_id,
            "roomId": room_id,
            "packageCode": pkg["code"],
            "packageName": pkg["name"],
            "durationHours": duration_hours,
            "date": date_str,
            "startTime": time_str,
            "startAt": start_utc,
            "endAt": end_utc,
            "bufferEndAt": buffer_end_utc,
            "addOnCodes": [a["code"] for a in selected_addons],
            "pricing": pricing,
            "customer": {
                "name": payload["customerName"],
                "phone": payload["customerPhone"],
                "email": payload.get("customerEmail", "")
            },
            "celebrantName": payload.get("celebrantName", ""),
            "celebrantAge": payload.get("celebrantAge"),
            "occasionType": payload.get("occasionType", "birthday"),
            "notes": payload.get("notes", ""),
            "status": "active",
            "sessionToken": str(uuid.uuid4()),
            "createdAt": now_u,
            "expiresAt": expires_at
        }
        self.hold_repo.insert(hold_doc)

        return {
            "holdId": str(hold_id),
            "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
            "holdDurationSeconds": self.config.HOLD_DURATION_MINUTES * 60,
            "pricing": pricing,
            "bookingSummary": {
                "date": date_str,
                "startTime": time_str,
                "durationHours": duration_hours,
                "packageName": pkg["name"],
                "roomId": room_id,
                "hostName": self.config.HOST_NAME
            }
        }

    def create_booking(self, payload: dict, idempotency_key: str = None, client_ip: str = None) -> dict:
        """
        Creates a confirmed booking with atomic anti-double-booking guarantee.
        Unified code path: direct booking requests automatically route through create_hold
        followed immediately by hold conversion, sharing 100% of slot, promo, and pricing logic.
        Issues an unguessable access token (storing only its SHA-256 hash).
        Enforces idempotency when idempotency_key is passed: same key + same body replays;
        same key + different body returns 422 IDEMPOTENCY_PAYLOAD_MISMATCH.
        """
        endpoint = "POST /api/bookings"
        req_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

        if idempotency_key:
            existing = self.idempotency_repo.get_key(idempotency_key, endpoint)
            if existing:
                if existing.get("status") == "completed":
                    if existing.get("requestHash") != req_hash:
                        raise IdempotencyPayloadMismatchError("Idempotency key reused with different request payload.")
                    return existing.get("response", {})
                elif existing.get("status") == "in_progress":
                    raise IdempotencyConflictError("A booking with this idempotency key is currently processing.")

            # Claim idempotency key in progress
            key_expiry = now_utc() + timedelta(hours=24)
            try:
                self.idempotency_repo.insert_in_progress(idempotency_key, endpoint, req_hash, key_expiry)
            except Exception:
                raise IdempotencyConflictError("A booking with this idempotency key is currently processing.")

        try:
            now_u = now_utc()
            now_i = now_ist()

            # Rule 0.3 d: Unified path. If holdId is not provided, create a hold first.
            if not payload.get("holdId"):
                hold_result = self.create_hold(payload, client_ip=client_ip)
                hold_id_str = hold_result["holdId"]
            else:
                hold_id_str = payload["holdId"]

            hold = self.hold_repo.find_by_id(hold_id_str)
            if not hold or hold.get("status") != "active":
                raise ResourceNotFoundError("Booking hold not found or already processed.")

            if ensure_utc(hold["expiresAt"]) <= now_u:
                self.hold_repo.transition_status(hold["_id"], "active", "expired")
                self.slot_claim_repo.release_by_owner(hold["_id"])
                released = self.offer_redemption_repo.release_reservation_idempotent(hold["_id"], now_u)
                if released and released.get("offerId"):
                    self.offer_repo.atomic_release_slot(released["offerId"])
                raise HoldExpiredError("Booking hold has expired. Please reselect your slot.")

            # Generate sequential reference JBX-YYYY-NNNN
            current_year = now_i.year
            seq_num = self.counter_repo.get_next_sequence(f"booking_{current_year}")
            booking_ref = f"JBX-{current_year}-{seq_num:04d}"

            new_booking_id = ObjectId()

            # Issue random unguessable access token; store ONLY its hash
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

            checkout_grace_mins = getattr(self.config, "CHECKOUT_GRACE_MINUTES", 15)
            checkout_expires_at = now_u + timedelta(minutes=checkout_grace_mins)

            # Transition hold to converted
            self.hold_repo.transition_status(
                hold["_id"], "active", "converted", {"bookingReference": booking_ref, "bookingId": new_booking_id}
            )

            # Transfer slot claims from hold to booking (retaining checkout grace expiry until confirmed payment)
            self.slot_claim_repo.transfer_owner(
                hold["_id"], new_booking_id, new_owner_type="booking", expires_at=checkout_expires_at
            )

            # Convert promo redemption if present
            self.offer_redemption_repo.convert_to_booking(hold["_id"], new_booking_id, now_u)

            start_at = hold["startAt"]
            end_at = hold["endAt"]

            booking_doc = {
                "_id": new_booking_id,
                "bookingReference": booking_ref,
                "accessTokenHash": token_hash,
                "holdId": hold["_id"],
                "roomId": hold["roomId"],
                "packageCode": hold["packageCode"],
                "packageName": hold["packageName"],
                "durationHours": hold["durationHours"],
                "startAt": start_at,
                "endAt": end_at,
                "bufferEndAt": hold["bufferEndAt"],
                "startTimeIst": f"{hold['date']} {hold['startTime']} IST",
                "endTimeIst": f"{hold['date']} {format_ist_time(end_at)} IST",
                "pricing": hold["pricing"],
                "customer": hold["customer"],
                "celebrantName": hold.get("celebrantName", ""),
                "celebrantAge": hold.get("celebrantAge"),
                "occasionType": hold.get("occasionType", "birthday"),
                "notes": hold.get("notes", ""),
                "bookingStatus": "pending_payment",
                "paymentStatus": "unpaid",
                "checkoutExpiresAt": checkout_expires_at,
                "createdAt": now_u,
                "updatedAt": now_u
            }
            self.booking_repo.insert(booking_doc)

            response_data = {
                "bookingReference": booking_doc["bookingReference"],
                "accessToken": raw_token,
                "bookingId": str(booking_doc["_id"]),
                "bookingStatus": booking_doc["bookingStatus"],
                "startAt": booking_doc["startAt"].isoformat().replace("+00:00", "Z"),
                "endAt": booking_doc["endAt"].isoformat().replace("+00:00", "Z"),
                "startTimeIst": booking_doc["startTimeIst"],
                "endTimeIst": booking_doc["endTimeIst"],
                "durationHours": booking_doc["durationHours"],
                "packageName": booking_doc["packageName"],
                "pricing": booking_doc["pricing"],
                "whatsappLink": f"https://wa.me/{self.config.WHATSAPP_NUMBER}?text=Hi%20Joybox!%20My%20booking%20ref%20is%20{booking_doc['bookingReference']}"
            }

            if idempotency_key:
                self.idempotency_repo.complete(idempotency_key, endpoint, 201, response_data)

            return response_data

        except Exception as exc:
            if idempotency_key:
                self.idempotency_repo.fail_and_release(idempotency_key, endpoint)
            raise

    def get_booking_by_reference(self, reference: str, token: str = None) -> dict:
        """
        Public booking lookup by reference.
        - If token is provided and valid: returns full public-safe booking details (masked phone, etc.).
        - If token is NOT provided: returns minimal status only (no customer name, phone, or pricing).
        - If token is WRONG: returns None (translated to 404 NOT_FOUND, identical to unknown reference).
        """
        booking = self.booking_repo.find_by_reference(reference)
        if not booking:
            return None

        # Minimal status lookup when no token is supplied (Rule 0.3 a)
        if not token or not token.strip():
            return {
                "bookingReference": booking["bookingReference"],
                "bookingStatus": booking.get("bookingStatus", "pending_payment"),
                "paymentStatus": booking.get("paymentStatus", "unpaid"),
                "isMinimal": True
            }

        # Token verification with constant-time comparison
        token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
        stored_hash = booking.get("accessTokenHash", "")
        if not stored_hash or not hmac.compare_digest(token_hash, stored_hash):
            return None  # Return 404, identical to unknown reference

        customer = booking.get("customer", {})
        pricing = booking.get("pricing", {})

        return {
            "bookingReference": booking["bookingReference"],
            "bookingStatus": booking.get("bookingStatus", "pending_payment"),
            "paymentStatus": booking.get("paymentStatus", "unpaid"),
            "startTimeIst": booking.get("startTimeIst", format_ist_display(booking["startAt"])),
            "endTimeIst": booking.get("endTimeIst", format_ist_display(booking["endAt"])),
            "durationHours": booking.get("durationHours", 1),
            "packageName": booking.get("packageName", "Basic"),
            "occasionType": booking.get("occasionType", "birthday"),
            "celebrantName": booking.get("celebrantName", ""),
            "customerName": format_customer_display_name(customer.get("name", "")),
            "customerPhoneMasked": mask_phone(customer.get("phone", "")),
            "pricing": {
                "totalAmountMinor": pricing.get("totalAmountMinor", 0),
                "totalRupees": pricing.get("totalRupees", 0.0),
                "currency": pricing.get("currency", "INR"),
                "paymentStatus": booking.get("paymentStatus", "unpaid")
            },
            "whatsappLink": f"https://wa.me/{self.config.WHATSAPP_NUMBER}?text=Hi%20Joybox!%20My%20booking%20ref%20is%20{booking['bookingReference']}"
        }

    def cancel_booking(self, reference: str, token: str = None, reason: str = "") -> dict:
        """
        Cancels a booking, releases all slot claims, and idempotently releases any claimed promo quota.
        Requires valid unguessable access token. Wrong or missing tokens return 404 (Rule 0.3 a).
        """
        booking = self.booking_repo.find_by_reference(reference)
        if not booking:
            raise ResourceNotFoundError(f"Booking reference '{reference}' not found.")

        # Require access token
        if not token or not token.strip():
            raise ResourceNotFoundError(f"Booking reference '{reference}' not found.")

        token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
        stored_hash = booking.get("accessTokenHash", "")
        if not stored_hash or not hmac.compare_digest(token_hash, stored_hash):
            raise ResourceNotFoundError(f"Booking reference '{reference}' not found.")

        current_status = booking.get("bookingStatus")
        if current_status == "cancelled":
            raise InvalidBookingStateError("Booking is already cancelled.")
        if current_status == "completed":
            raise InvalidBookingStateError("Cannot cancel a completed celebration.")

        now_u = now_utc()

        # Update booking status
        self.booking_repo.update_status(
            booking["_id"],
            current_status,
            "cancelled",
            {"cancellationReason": reason, "cancelledAt": now_u}
        )

        # Release all slot claims
        self.slot_claim_repo.release_by_owner(booking["_id"])

        # Idempotently release promo quota if this booking had claimed one
        target_id = booking.get("holdId") or booking["_id"]
        released = self.offer_redemption_repo.release_reservation_idempotent(target_id, now_u)
        if released and released.get("offerId"):
            self.offer_repo.atomic_release_slot(released["offerId"])

        return {
            "bookingReference": booking["bookingReference"],
            "bookingStatus": "cancelled",
            "cancelledAt": now_u.isoformat().replace("+00:00", "Z"),
            "message": "Booking has been successfully cancelled and slot released."
        }
