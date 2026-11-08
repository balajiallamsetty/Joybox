// DEPRECATED: Do not use for production deployments.
// The authoritative source of truth for all MongoDB indexes and schema validators is
// backend/scripts/init_indexes.py (which uses live codebase field names: bookingStatus, roomId, etc.).
// Run with mongosh against the intended database. Review before production.
db.inquiries.createIndex({ createdAt: -1 });
db.inquiries.createIndex({ status: 1, createdAt: -1 });
db.inquiries.createIndex({ phone: 1, createdAt: -1 });
db.bookings.createIndex({ status: 1, startAt: 1 });
db.bookingHolds.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 });
db.bookingHolds.createIndex({ venueId: 1, startAt: 1, endAt: 1, status: 1 });
db.payments.createIndex({ bookingId: 1, createdAt: -1 });
db.payments.createIndex({ provider: 1, providerPaymentId: 1 }, { unique: true, partialFilterExpression: { providerPaymentId: { $type: "string" } } });
db.offerRedemptions.createIndex({ offerId: 1, periodKey: 1, status: 1 });
db.offerRedemptions.createIndex({ bookingId: 1 }, { unique: true });
db.auditLogs.createIndex({ tenantId: 1, createdAt: -1 });
db.idempotencyKeys.createIndex({ expiresAt: 1 }, { expireAfterSeconds: 0 });
db.idempotencyKeys.createIndex({ tenantId: 1, key: 1 }, { unique: true });
print("Starter indexes created. Add the remaining production indexes after finalizing access patterns.");
