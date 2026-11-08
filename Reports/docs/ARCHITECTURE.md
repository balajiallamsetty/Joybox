# Architecture

Browser (React/Vite) → HTTPS JSON API → Flask Blueprints → validation schemas → service layer → PyMongo repositories → MongoDB Atlas.

Razorpay sends signed webhooks to Flask. Gallery media lives in object storage/CDN; MongoDB stores metadata and storage keys. WhatsApp enquiries use a prefilled link.

## Layer responsibilities
- `routes`: HTTP request/response handling
- `schemas`: request validation
- `services`: booking/offer/payment business rules
- `repositories`: database operations
- `models`: optional document factories/constants
- `utils`: time handling, ObjectId serialization, idempotency, safe errors

## Booking lifecycle target
1. Check business hours, closures, confirmed bookings and active holds.
2. Claim slots atomically.
3. Calculate package/add-ons/offer/tax/deposit on the server.
4. Create a payment order if online payment is enabled.
5. Verify payment signature and signed webhook; process idempotently.
6. Confirm booking according to payment policy.
7. Send notifications with safe retry logic.
