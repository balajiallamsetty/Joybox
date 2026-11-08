import logging
from datetime import timedelta
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from ..utils import utcnow

logger = logging.getLogger(__name__)

class PackageRepository:
    def __init__(self, db):
        self.collection = getattr(db, "packages", None) if db is not None else None

    def find_all_active(self):
        if self.collection is None:
            return []
        cursor = self.collection.find({"isActive": True}).sort("displayOrder", 1)
        return list(cursor)

    def find_all(self, active_only: bool = False):
        if self.collection is None:
            return []
        query = {"isActive": True} if active_only else {}
        cursor = self.collection.find(query).sort("displayOrder", 1)
        return list(cursor)

    def find_by_code(self, code, active_only: bool = False):
        if self.collection is None:
            return None
        query = {"code": code}
        if active_only:
            query["isActive"] = True
        return self.collection.find_one(query)

    def insert(self, package_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(package_doc)
        return res.inserted_id


class AddOnRepository:
    def __init__(self, db):
        self.collection = getattr(db, "addOns", None) if db is not None else None

    def find_all_active(self):
        if self.collection is None:
            return []
        cursor = self.collection.find({"isActive": True}).sort("displayOrder", 1)
        return list(cursor)

    def find_all(self, active_only: bool = False):
        if self.collection is None:
            return []
        query = {"isActive": True} if active_only else {}
        cursor = self.collection.find(query).sort("displayOrder", 1)
        return list(cursor)

    def find_by_code(self, code, active_only: bool = False):
        if self.collection is None:
            return None
        query = {"code": code}
        if active_only:
            query["isActive"] = True
        return self.collection.find_one(query)

    def find_by_codes(self, codes):
        if self.collection is None:
            return []
        return list(self.collection.find({"code": {"$in": codes}, "isActive": True}))

    def insert(self, addon_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(addon_doc)
        return res.inserted_id


class OfferRepository:
    def __init__(self, db):
        self.collection = getattr(db, "offers", None) if db is not None else None

    def find_active(self):
        if self.collection is None:
            return []
        return list(self.collection.find({"isActive": True}))

    def find_by_package(self, package_code):
        if self.collection is None:
            return None
        return self.collection.find_one({"eligiblePackageCode": package_code, "isActive": True})

    def atomic_claim_slot(self, offer_id, limit: int):
        if self.collection is None:
            return None
        return self.collection.find_one_and_update(
            {
                "_id": offer_id,
                "isActive": True,
                "monthlyRedemptionCount": {"$lt": limit}
            },
            {"$inc": {"monthlyRedemptionCount": 1}},
            return_document=ReturnDocument.AFTER
        )

    def atomic_release_slot(self, offer_id):
        if self.collection is None:
            return None
        return self.collection.find_one_and_update(
            {"_id": offer_id, "monthlyRedemptionCount": {"$gt": 0}},
            {"$inc": {"monthlyRedemptionCount": -1}},
            return_document=ReturnDocument.AFTER
        )


class InquiryRepository:
    def __init__(self, db):
        self.collection = getattr(db, "inquiries", None) if db is not None else None

    def insert(self, inquiry_doc):
        if self.collection is None:
            return None
        result = self.collection.insert_one(inquiry_doc)
        return result.inserted_id

    def find_all(self, query=None, limit=50, skip=0):
        if self.collection is None:
            return []
        cursor = self.collection.find(query or {}).sort("createdAt", -1).skip(skip).limit(limit)
        return list(cursor)

    def count(self, query=None):
        if self.collection is None:
            return 0
        return self.collection.count_documents(query or {})

    def update_status(self, inquiry_id, status: str, admin_notes: str = None, now_u=None):
        if self.collection is None or not inquiry_id:
            return None
        oid = inquiry_id if isinstance(inquiry_id, ObjectId) else ObjectId(inquiry_id)
        update_set = {"status": status, "updatedAt": now_u or utcnow()}
        if admin_notes is not None:
            update_set["adminNotes"] = admin_notes
        return self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": update_set},
            return_document=ReturnDocument.AFTER
        )


class SlotClaimRepository:
    def __init__(self, db):
        self.collection = getattr(db, "slotClaims", None) if db is not None else None

    def find_claims_in_range(self, room_id: str, start_utc, end_utc, now_utc):
        if self.collection is None:
            return []
        query = {
            "roomId": room_id,
            "slotStart": {"$lt": end_utc},
            "slotEnd": {"$gt": start_utc},
            "$or": [
                {"ownerType": {"$in": ["booking", "block"]}},
                {"ownerType": "hold", "expiresAt": {"$gt": now_utc}}
            ]
        }
        return list(self.collection.find(query))

    def claim_all_or_rollback(self, claim_docs: list) -> bool:
        if self.collection is None or not claim_docs:
            return False

        inserted_ids = []
        try:
            for doc in claim_docs:
                res = self.collection.insert_one(doc)
                inserted_ids.append(res.inserted_id)
            return True
        except DuplicateKeyError:
            if inserted_ids:
                try:
                    self.collection.delete_many({"_id": {"$in": inserted_ids}})
                except Exception as del_err:
                    logger.error(f"Error rolling back duplicate key claims: {del_err}")
            return False
        except Exception as e:
            if inserted_ids:
                try:
                    self.collection.delete_many({"_id": {"$in": inserted_ids}})
                except Exception as del_err:
                    logger.error(f"Error rolling back claims after failure: {del_err}")
            logger.error(f"claim_all_or_rollback failed with unexpected error: {e}")
            raise

    def release_by_owner(self, owner_id) -> int:
        if self.collection is None:
            return 0
        oid = owner_id if isinstance(owner_id, ObjectId) else owner_id
        res = self.collection.delete_many({"ownerId": oid})
        return res.deleted_count

    def transfer_owner(self, old_owner_id, new_owner_id, new_owner_type="booking", expires_at=None):
        if self.collection is None:
            return 0
        update_doc = {"ownerId": new_owner_id, "ownerType": new_owner_type, "expiresAt": expires_at}
        res = self.collection.update_many(
            {"ownerId": old_owner_id},
            {"$set": update_doc}
        )
        return res.modified_count

    def reclaim_expired_holds(self, room_id: str, slot_starts: list, now_u):
        if self.collection is None or not slot_starts:
            return 0
        res = self.collection.delete_many({
            "roomId": room_id,
            "slotStart": {"$in": slot_starts},
            "ownerType": "hold",
            "expiresAt": {"$lte": now_u}
        })
        return res.deleted_count


class BookingHoldRepository:
    def __init__(self, db):
        self.collection = getattr(db, "bookingHolds", None) if db is not None else None

    def insert(self, hold_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(hold_doc)
        return res.inserted_id

    def find_by_id(self, hold_id):
        if self.collection is None:
            return None
        oid = hold_id if isinstance(hold_id, ObjectId) else ObjectId(hold_id)
        return self.collection.find_one({"_id": oid})

    def transition_status(self, hold_id, from_status: str, to_status: str, extra_fields: dict = None):
        if self.collection is None:
            return None
        oid = hold_id if isinstance(hold_id, ObjectId) else ObjectId(hold_id)
        update_doc = {"status": to_status}
        if extra_fields:
            update_doc.update(extra_fields)
        return self.collection.find_one_and_update(
            {"_id": oid, "status": from_status},
            {"$set": update_doc},
            return_document=ReturnDocument.AFTER
        )

    def extend_hold(self, hold_id, additional_minutes: int, now_u):
        if self.collection is None:
            return None
        oid = hold_id if isinstance(hold_id, ObjectId) else ObjectId(hold_id)
        new_expiry = now_u + timedelta(minutes=additional_minutes)
        return self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": {"expiresAt": new_expiry, "paymentExpiresAt": new_expiry, "updatedAt": now_u}},
            return_document=ReturnDocument.AFTER
        )


class BookingRepository:
    def __init__(self, db):
        self.collection = getattr(db, "bookings", None) if db is not None else None

    def insert(self, booking_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(booking_doc)
        return res.inserted_id

    def find_by_reference(self, reference: str):
        if self.collection is None:
            return None
        return self.collection.find_one({"bookingReference": reference.strip()})

    def find_by_id(self, booking_id):
        if self.collection is None:
            return None
        oid = booking_id if isinstance(booking_id, ObjectId) else ObjectId(booking_id)
        return self.collection.find_one({"_id": oid})

    def update_status(self, booking_id, from_status: str, to_status: str, extra_fields: dict = None):
        if self.collection is None:
            return None
        oid = booking_id if isinstance(booking_id, ObjectId) else ObjectId(booking_id)
        update_doc = {"bookingStatus": to_status}
        if extra_fields:
            update_doc.update(extra_fields)
        return self.collection.find_one_and_update(
            {"_id": oid, "bookingStatus": from_status},
            {"$set": update_doc},
            return_document=ReturnDocument.AFTER
        )

    def find_all(self, query=None, limit=50, skip=0, sort_by="createdAt", sort_dir=-1):
        if self.collection is None:
            return []
        cursor = self.collection.find(query or {}).sort(sort_by, sort_dir).skip(skip).limit(limit)
        return list(cursor)

    def count(self, query=None):
        if self.collection is None:
            return 0
        return self.collection.count_documents(query or {})


class CounterRepository:
    def __init__(self, db):
        self.collection = getattr(db, "counters", None) if db is not None else None

    def get_next_sequence(self, sequence_name: str) -> int:
        if self.collection is None:
            return 1
        doc = self.collection.find_one_and_update(
            {"_id": sequence_name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return doc["seq"]


class OfferRedemptionRepository:
    def __init__(self, db):
        self.collection = getattr(db, "offerRedemptions", None) if db is not None else None

    def insert_reservation(self, redemption_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(redemption_doc)
        return res.inserted_id

    def convert_to_booking(self, hold_or_booking_id, new_booking_id, now_utc):
        if self.collection is None:
            return None
        return self.collection.find_one_and_update(
            {
                "$or": [
                    {"holdId": hold_or_booking_id},
                    {"bookingId": hold_or_booking_id}
                ],
                "status": "reserved"
            },
            {
                "$set": {
                    "bookingId": new_booking_id,
                    "status": "converted",
                    "convertedAt": now_utc,
                    "updatedAt": now_utc
                }
            },
            return_document=ReturnDocument.AFTER
        )

    def release_reservation_idempotent(self, hold_or_booking_id, now_utc):
        if self.collection is None:
            return None
        return self.collection.find_one_and_update(
            {
                "$or": [
                    {"holdId": hold_or_booking_id},
                    {"bookingId": hold_or_booking_id}
                ],
                "status": {"$in": ["reserved", "converted"]}
            },
            {
                "$set": {
                    "status": "released",
                    "releasedAt": now_utc,
                    "updatedAt": now_utc
                }
            },
            return_document=ReturnDocument.AFTER
        )

    def count_active_period(self, offer_id, period_key: str):
        if self.collection is None:
            return 0
        return self.collection.count_documents({
            "offerId": offer_id,
            "periodKey": period_key,
            "status": {"$in": ["reserved", "converted"]}
        })

    def count_by_phone_and_offer(self, phone: str, offer_id):
        if self.collection is None or not phone:
            return 0
        return self.collection.count_documents({
            "offerId": offer_id,
            "customerPhone": phone,
            "status": {"$in": ["reserved", "converted"]}
        })


class IdempotencyRepository:
    def __init__(self, db):
        self.collection = getattr(db, "idempotencyKeys", None) if db is not None else None

    def get_key(self, key: str, endpoint: str):
        if self.collection is None:
            return None
        return self.collection.find_one({"key": key, "endpoint": endpoint})

    def insert_in_progress(self, key: str, endpoint: str, request_hash: str, expires_at):
        if self.collection is None:
            return True
        doc = {
            "key": key,
            "endpoint": endpoint,
            "requestHash": request_hash,
            "status": "in_progress",
            "createdAt": utcnow(),
            "expiresAt": expires_at
        }
        self.collection.insert_one(doc)
        return True

    def complete(self, key: str, endpoint: str, status_code: int, response_data: dict):
        if self.collection is None:
            return
        self.collection.update_one(
            {"key": key, "endpoint": endpoint},
            {
                "$set": {
                    "status": "completed",
                    "statusCode": status_code,
                    "response": response_data,
                    "completedAt": utcnow()
                }
            }
        )

    def fail_and_release(self, key: str, endpoint: str):
        if self.collection is None:
            return
        self.collection.delete_one({"key": key, "endpoint": endpoint})


class RateLimitRepository:
    def __init__(self, db):
        self.collection = getattr(db, "rateLimits", None) if db is not None else None

    def check_and_increment(self, key: str, window_seconds: int, max_limit: int, now_utc) -> bool:
        if self.collection is None:
            return True
        expires_at = now_utc + timedelta(seconds=window_seconds)
        doc = self.collection.find_one_and_update(
            {"key": key},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {"createdAt": now_utc, "expiresAt": expires_at}
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return doc.get("count", 1) <= max_limit


class PaymentRepository:
    def __init__(self, db):
        self.collection = getattr(db, "payments", None) if db is not None else None

    def insert(self, payment_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(payment_doc)
        return res.inserted_id

    def find_by_order_id(self, order_id: str):
        if self.collection is None or not order_id:
            return None
        return self.collection.find_one({"providerOrderId": order_id.strip()})

    def find_by_payment_id(self, payment_id: str):
        if self.collection is None or not payment_id:
            return None
        return self.collection.find_one({"providerPaymentId": payment_id.strip()})

    def find_by_booking_reference(self, booking_ref: str):
        if self.collection is None or not booking_ref:
            return []
        cursor = self.collection.find({"bookingReference": booking_ref.strip()}).sort("createdAt", -1)
        return list(cursor)

    def find_latest_by_booking_reference(self, booking_ref: str):
        if self.collection is None or not booking_ref:
            return None
        return self.collection.find_one({"bookingReference": booking_ref.strip()}, sort=[("createdAt", -1)])

    def update_by_order_id(self, order_id: str, update_fields: dict):
        if self.collection is None or not order_id:
            return None
        return self.collection.find_one_and_update(
            {"providerOrderId": order_id.strip()},
            {"$set": update_fields},
            return_document=ReturnDocument.AFTER
        )

    def update_by_payment_id(self, payment_id: str, update_fields: dict):
        if self.collection is None or not payment_id:
            return None
        return self.collection.find_one_and_update(
            {"providerPaymentId": payment_id.strip()},
            {"$set": update_fields},
            return_document=ReturnDocument.AFTER
        )

    def find_pending_for_reconciliation(self, min_age_minutes: int, now_u):
        if self.collection is None:
            return []
        cutoff = now_u - timedelta(minutes=min_age_minutes)
        cursor = self.collection.find({"status": "created", "createdAt": {"$lte": cutoff}})
        return list(cursor)

    def find_needs_review(self):
        if self.collection is None:
            return []
        cursor = self.collection.find({"needsReview": True}).sort("createdAt", -1)
        return list(cursor)

    def atomic_record_refund(self, provider_payment_id: str, refund_amount_minor: int, now_u):
        if self.collection is None or not provider_payment_id:
            return None
        try:
            return self.collection.find_one_and_update(
                {
                    "providerPaymentId": provider_payment_id.strip(),
                    "status": "captured",
                    "$expr": {
                        "$lte": [
                            {"$add": [{"$ifNull": ["$amountRefundedMinor", 0]}, refund_amount_minor]},
                            "$amountMinor"
                        ]
                    }
                },
                {
                    "$inc": {"amountRefundedMinor": refund_amount_minor},
                    "$set": {"updatedAt": now_u}
                },
                return_document=ReturnDocument.AFTER
            )
        except TypeError:
            # Fallback for test mocks or in-memory collections that do not support $expr aggregation
            doc = self.collection.find_one({"providerPaymentId": provider_payment_id.strip(), "status": "captured"})
            if not doc:
                return None
            curr_refunded = doc.get("amountRefundedMinor", 0) or 0
            total_amount = doc.get("amountMinor", 0) or 0
            if curr_refunded + refund_amount_minor > total_amount:
                return None
            return self.collection.find_one_and_update(
                {"_id": doc["_id"]},
                {
                    "$inc": {"amountRefundedMinor": refund_amount_minor},
                    "$set": {"updatedAt": now_u}
                },
                return_document=ReturnDocument.AFTER
            )

    def find_all(self, query=None, limit=50, skip=0):
        if self.collection is None:
            return []
        cursor = self.collection.find(query or {}).sort("createdAt", -1).skip(skip).limit(limit)
        return list(cursor)

    def count(self, query=None):
        if self.collection is None:
            return 0
        return self.collection.count_documents(query or {})


class RefundRepository:
    def __init__(self, db):
        self.collection = getattr(db, "refunds", None) if db is not None else None

    def insert(self, refund_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(refund_doc)
        return res.inserted_id

    def find_by_id(self, refund_id):
        if self.collection is None or not refund_id:
            return None
        oid = refund_id if isinstance(refund_id, ObjectId) else ObjectId(refund_id)
        return self.collection.find_one({"_id": oid})

    def find_by_refund_id(self, refund_id: str):
        if self.collection is None or not refund_id:
            return None
        return self.collection.find_one({"providerRefundId": refund_id.strip()})

    def find_by_idempotency_key(self, idempotency_key: str):
        if self.collection is None or not idempotency_key:
            return None
        return self.collection.find_one({"idempotencyKey": idempotency_key.strip()})

    def find_by_booking_reference(self, booking_ref: str):
        if self.collection is None or not booking_ref:
            return []
        cursor = self.collection.find({"bookingReference": booking_ref.strip()}).sort("createdAt", -1)
        return list(cursor)

    def update_status(self, refund_id, status: str, extra_fields: dict = None):
        if self.collection is None or not refund_id:
            return None
        set_dict = {"status": status, "updatedAt": utcnow()}
        if extra_fields:
            set_dict.update(extra_fields)
        if isinstance(refund_id, ObjectId):
            query = {"_id": refund_id}
        elif ObjectId.is_valid(str(refund_id)):
            query = {"$or": [{"_id": ObjectId(str(refund_id))}, {"providerRefundId": str(refund_id).strip()}]}
        else:
            query = {"providerRefundId": str(refund_id).strip()}

        return self.collection.find_one_and_update(
            query,
            {"$set": set_dict},
            return_document=ReturnDocument.AFTER
        )

    def find_failed_refunds(self):
        if self.collection is None:
            return []
        cursor = self.collection.find({"status": "failed"}).sort("createdAt", -1)
        return list(cursor)

    def find_all(self, query=None, limit=50, skip=0):
        if self.collection is None:
            return []
        cursor = self.collection.find(query or {}).sort("createdAt", -1).skip(skip).limit(limit)
        return list(cursor)

    def count(self, query=None):
        if self.collection is None:
            return 0
        return self.collection.count_documents(query or {})


class WebhookEventRepository:
    def __init__(self, db):
        self.collection = getattr(db, "webhookEvents", None) if db is not None else None

    def find_event(self, provider: str, event_id: str):
        if self.collection is None or not event_id:
            return None
        return self.collection.find_one({"provider": provider, "eventId": event_id.strip()})

    def claim_event_atomically(self, provider: str, event_id: str, event_type: str, payload: dict, now_utc, lease_seconds: int = 60):
        if self.collection is None:
            return True, {"provider": provider, "eventId": event_id, "status": "processing"}

        lease_exp = now_utc + timedelta(seconds=lease_seconds)
        doc = {
            "provider": provider,
            "eventId": event_id.strip(),
            "eventType": event_type,
            "payload": payload,
            "status": "processing",
            "leaseExpiresAt": lease_exp,
            "createdAt": now_utc,
            "updatedAt": now_utc
        }
        try:
            self.collection.insert_one(doc)
            return True, doc
        except DuplicateKeyError:
            existing = self.collection.find_one({"provider": provider, "eventId": event_id.strip()})
            if not existing:
                return False, None
            # If already processed, ignore as genuine duplicate
            if existing.get("status") == "processed":
                return False, existing
            # If stuck in processing or failed and lease has expired, re-acquire lease
            lease_at = existing.get("leaseExpiresAt")
            if (existing.get("status") in ("processing", "failed")) and (lease_at is None or lease_at <= now_utc):
                reacquired = self.collection.find_one_and_update(
                    {
                        "provider": provider,
                        "eventId": event_id.strip(),
                        "status": {"$in": ["processing", "failed"]},
                        "$or": [
                            {"leaseExpiresAt": {"$lte": now_utc}},
                            {"leaseExpiresAt": None}
                        ]
                    },
                    {
                        "$set": {
                            "status": "processing",
                            "leaseExpiresAt": lease_exp,
                            "retryCount": existing.get("retryCount", 0) + 1,
                            "updatedAt": now_utc
                        }
                    },
                    return_document=ReturnDocument.AFTER
                )
                if reacquired:
                    return True, reacquired
            return False, existing

    def mark_processed(self, provider: str, event_id: str, extra_fields: dict = None):
        if self.collection is None or not event_id:
            return None
        set_dict = {"status": "processed", "leaseExpiresAt": None, "processedAt": utcnow(), "updatedAt": utcnow()}
        if extra_fields:
            set_dict.update(extra_fields)
        return self.collection.find_one_and_update(
            {"provider": provider, "eventId": event_id.strip()},
            {"$set": set_dict},
            return_document=ReturnDocument.AFTER
        )

    def mark_failed(self, provider: str, event_id: str, error_msg: str):
        if self.collection is None or not event_id:
            return None
        return self.collection.find_one_and_update(
            {"provider": provider, "eventId": event_id.strip()},
            {
                "$set": {
                    "status": "failed",
                    "leaseExpiresAt": utcnow(),
                    "errorMessage": error_msg,
                    "failedAt": utcnow(),
                    "updatedAt": utcnow()
                }
            },
            return_document=ReturnDocument.AFTER
        )


class UserRepository:
    def __init__(self, db):
        self.collection = getattr(db, "users", None) if db is not None else None

    def find_by_username(self, username: str):
        if self.collection is None or not username:
            return None
        return self.collection.find_one({"username": username.strip().lower()})

    def find_by_id(self, user_id):
        if self.collection is None or not user_id:
            return None
        oid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        return self.collection.find_one({"_id": oid})

    def insert(self, user_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(user_doc)
        return res.inserted_id

    def update_password(self, user_id, password_hash: str, now_u):
        if self.collection is None or not user_id:
            return None
        oid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        return self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": {"passwordHash": password_hash, "updatedAt": now_u}},
            return_document=ReturnDocument.AFTER
        )

    def record_login_success(self, user_id, now_u):
        if self.collection is None or not user_id:
            return None
        oid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        return self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": {"failedLoginAttempts": 0, "lockedUntil": None, "lastLoginAt": now_u, "updatedAt": now_u}},
            return_document=ReturnDocument.AFTER
        )

    def record_login_failure(self, username: str, now_u, max_attempts: int = 5, lockout_minutes: int = 15):
        if self.collection is None or not username:
            return None
        user = self.find_by_username(username)
        if not user:
            return None
        new_attempts = user.get("failedLoginAttempts", 0) + 1
        locked_until = now_u + timedelta(minutes=lockout_minutes) if new_attempts >= max_attempts else None
        return self.collection.find_one_and_update(
            {"_id": user["_id"]},
            {"$set": {"failedLoginAttempts": new_attempts, "lockedUntil": locked_until, "updatedAt": now_u}},
            return_document=ReturnDocument.AFTER
        )

    def list_active(self):
        if self.collection is None:
            return []
        cursor = self.collection.find({"isActive": True})
        return list(cursor)

    def update_user(self, user_id, update_fields: dict):
        if self.collection is None or not user_id:
            return None
        oid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        return self.collection.find_one_and_update(
            {"_id": oid},
            {"$set": update_fields},
            return_document=ReturnDocument.AFTER
        )


class AdminSessionRepository:
    def __init__(self, db):
        self.collection = getattr(db, "adminSessions", None) if db is not None else None

    def create_session(self, session_doc: dict):
        if self.collection is None:
            return None
        res = self.collection.insert_one(session_doc)
        return res.inserted_id

    def find_active_session(self, token_hash: str, now_u):
        if self.collection is None or not token_hash:
            return None
        return self.collection.find_one({
            "tokenHash": token_hash,
            "isRevoked": False,
            "expiresAt": {"$gt": now_u},
            "idleExpiresAt": {"$gt": now_u}
        })

    def touch_session(self, token_hash: str, arg2, arg3=None):
        if self.collection is None or not token_hash:
            return None
        if isinstance(arg2, (int, float)):
            idle_minutes = int(arg2)
            now_u = arg3 or datetime.now(timezone.utc)
        elif isinstance(arg3, (int, float)):
            idle_minutes = int(arg3)
            now_u = arg2 or datetime.now(timezone.utc)
        else:
            now_u = arg2 or datetime.now(timezone.utc)
            idle_minutes = 30
        new_idle = now_u + timedelta(minutes=idle_minutes)
        return self.collection.find_one_and_update(
            {"tokenHash": token_hash, "isRevoked": False},
            {"$set": {"lastActivityAt": now_u, "idleExpiresAt": new_idle}},
            return_document=ReturnDocument.AFTER
        )

    def revoke_session(self, token_hash: str, now_u):
        if self.collection is None or not token_hash:
            return None
        return self.collection.find_one_and_update(
            {"tokenHash": token_hash},
            {"$set": {"isRevoked": True, "revokedAt": now_u}},
            return_document=ReturnDocument.AFTER
        )

    def revoke_all_user_sessions(self, user_id, now_u, except_token_hash: str = None):
        if self.collection is None or not user_id:
            return 0
        oid = user_id if isinstance(user_id, ObjectId) else ObjectId(user_id)
        query = {"userId": oid, "isRevoked": False}
        if except_token_hash:
            query["tokenHash"] = {"$ne": except_token_hash}
        res = self.collection.update_many(query, {"$set": {"isRevoked": True, "revokedAt": now_u}})
        return res.modified_count

    revoke_all_for_user = revoke_all_user_sessions

    def find_by_token_hash(self, token_hash: str):
        if self.collection is None or not token_hash:
            return None
        return self.collection.find_one({
            "tokenHash": token_hash,
            "revokedAt": None,
            "isRevoked": {"$ne": True}
        })


class AuditLogRepository:
    def __init__(self, db):
        self.collection = getattr(db, "auditLogs", None) if db is not None else None

    def insert_log(self, log_doc: dict):
        if self.collection is None:
            return None
        res = self.collection.insert_one(log_doc)
        return res.inserted_id

    def insert(self, log_doc: dict):
        return self.insert_log(log_doc)

    def find_all(self, query=None, limit=50, skip=0):
        return self.find_logs(query=query, limit=limit, skip=skip)

    def find_logs(self, query=None, limit=50, skip=0):
        if self.collection is None:
            return []
        cursor = self.collection.find(query or {}).sort("createdAt", -1).skip(skip).limit(limit)
        return list(cursor)

    def count_logs(self, query=None):
        if self.collection is None:
            return 0
        return self.collection.count_documents(query or {})

    def count(self, query=None):
        return self.count_logs(query)


class AvailabilityBlockRepository:
    def __init__(self, db):
        self.collection = getattr(db, "availabilityBlocks", None) if db is not None else None

    def insert(self, block_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(block_doc)
        return res.inserted_id

    def find_all(self, query=None, limit=100):
        if self.collection is None:
            return []
        cursor = self.collection.find(query or {}).sort("startAt", 1).limit(limit)
        return list(cursor)

    def find_by_id(self, block_id):
        if self.collection is None or not block_id:
            return None
        oid = block_id if isinstance(block_id, ObjectId) else ObjectId(block_id)
        return self.collection.find_one({"_id": oid})

    def delete(self, block_id):
        if self.collection is None or not block_id:
            return 0
        oid = block_id if isinstance(block_id, ObjectId) else ObjectId(block_id)
        res = self.collection.delete_one({"_id": oid})
        return res.deleted_count

    def delete_by_id(self, block_id):
        return self.delete(block_id)


class GalleryRepository:
    def __init__(self, db):
        self.collection = getattr(db, "galleryAssets", None) if db is not None else None

    def find_active(self, category: str = None):
        if self.collection is None:
            return []
        query = {"isActive": True}
        if category and category.lower() != "all":
            query["category"] = category.lower()
        cursor = self.collection.find(query).sort("displayOrder", 1)
        return list(cursor)

    def insert(self, asset_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(asset_doc)
        return res.inserted_id


class FaqRepository:
    def __init__(self, db):
        self.collection = getattr(db, "faqs", None) if db is not None else None

    def find_active(self, category: str = None):
        if self.collection is None:
            return []
        query = {"isActive": True}
        if category:
            query["category"] = category.lower()
        cursor = self.collection.find(query).sort("displayOrder", 1)
        return list(cursor)

    def insert(self, faq_doc):
        if self.collection is None:
            return None
        res = self.collection.insert_one(faq_doc)
        return res.inserted_id


