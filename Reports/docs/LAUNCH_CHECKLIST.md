# Launch Checklist

## Business
- [ ] Confirm exact map pin/address, opening hours and taxes.
- [ ] Define deposit, cancellation, refund, overtime and late-arrival rules.
- [ ] Define whether the ₹500 offer applies to enquiries, holds, paid bookings or confirmed bookings.
- [ ] Confirm offer eligibility and add-on availability/safety.
- [ ] Add approved real venue photos, logo, Telugu translations and FAQs.

## Engineering
- [ ] Implement admin auth/roles, rate limiting and authorization.
- [ ] Implement availability checks and atomic slot claims.
- [ ] Implement booking lifecycle, cancellation and refunds.
- [ ] Implement offer quota atomically.
- [ ] Implement Razorpay orders, signature verification, signed webhooks and idempotency.
- [ ] Complete validators/indexes for all production collections.
- [ ] Test concurrent booking attempts, duplicate webhooks, expired holds and promotion contention.
- [ ] Add backups, retention policy, monitoring and restore test.
- [ ] Restrict CORS, enable HTTPS and avoid logging sensitive data.

## UI
- [ ] Import approved Stitch screens/assets.
- [ ] Review responsive layouts, accessibility and keyboard navigation.
- [ ] Add English/Telugu switching with reviewed translations.
- [ ] Test loading/error/success states and WhatsApp on mobile/desktop.
- [ ] Add privacy notice and enquiry consent.
