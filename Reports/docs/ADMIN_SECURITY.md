# Joybox Party Room — Administrator Security Architecture

## 1. Overview and Threat Model

This document outlines the security architecture, authentication protocols, role-based access control (RBAC), audit logging, and mitigation strategies for the Joybox Party Room administrative console (`joybox_admin_operations_reservation_console`).

The admin console provides privileged access to customer bookings, financial payment status, manual reservations, package configurations, calendar blocks, and system audit logs. The system treats the server as the **single source of truth** for all authorization decisions.

---

## 2. Threat Model & Mitigations

| Threat | Attack Vector | Architecture Mitigation |
| :--- | :--- | :--- |
| **Credential Guessing / Brute Force** | Automated dictionary attacks against `/api/admin/auth/login` | Account lockout after 5 consecutive failed attempts (30-minute lockout window), IP/username rate limits, and constant-time dummy verification on nonexistent users to eliminate timing side-channels. |
| **Session Hijacking / Sniffing** | Interception of session identifiers over network or via malicious browser extensions | Tokens issued as opaque 256-bit cryptographically secure strings (`secrets.token_urlsafe(32)`), stored exclusively as SHA-256 hashes in MongoDB, delivered via `HttpOnly`, `Secure`, `SameSite=Lax` cookies. |
| **Cross-Site Request Forgery (CSRF)** | Third-party malicious sites issuing cross-origin requests using ambient browser credentials | SameSite cookie attribute plus mandatory custom header `X-CSRF-Token` verified against the authenticated session on all mutating HTTP methods (`POST`, `PATCH`, `PUT`, `DELETE`). |
| **Privilege Escalation** | Low-privilege staff attempting refund or user administration | Multi-tier server-side RBAC middleware (`@require_role`) verifying roles on every request from verified database records. Client-side hiding of UI is never treated as security. |
| **Insider Fraud / Repudiation** | Staff member tampering with bookings or issuing unauthorized offline reservations | Append-only `auditLogs` collection recording actor identity, role, IP, request ID, target record, and change details. Critical financial operations fail closed if the audit log cannot be written. |
| **Information Leakage via Caching** | Shared terminals in party room viewing cached customer PII | `Cache-Control: no-store, no-cache, must-revalidate` and `Pragma: no-cache` enforced across all `/api/admin/*` endpoints. |

---

## 3. Authentication & Session Architecture

### 3.1 Password Storage and Verification
- **Algorithm:** `bcrypt` with work factor 12.
- **Timing Attack Mitigation:** When an invalid username is submitted, the backend performs a deterministic dummy bcrypt verification against a static benchmark hash so response times are indistinguishable between invalid usernames and incorrect passwords.
- **Rehashing:** If system password cost parameters increase, successful logins automatically rehash and update the user's password hash in MongoDB.

### 3.2 Session Lifecycle & Token Management
1. **Login (`POST /api/admin/auth/login`):**
   - Validates username and password.
   - Checks account lockout status (`lockoutUntil > now_utc()`).
   - Resets failed login counters on successful authentication.
   - Generates two unguessable cryptographically secure random values:
     - `session_token`: 256 bits (`secrets.token_urlsafe(32)`)
     - `csrf_token`: 256 bits (`secrets.token_urlsafe(32)`)
   - Computes `token_hash = sha256(session_token)` and stores in `adminSessions` collection:
     ```json
     {
       "_id": ObjectId("..."),
       "userId": ObjectId("..."),
       "tokenHash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
       "csrfToken": "...",
       "role": "owner",
       "createdAt": ISODate("2026-10-28T18:00:00Z"),
       "lastAccessedAt": ISODate("2026-10-28T18:00:00Z"),
       "expiresAt": ISODate("2026-10-29T02:00:00Z"),
       "idleExpiresAt": ISODate("2026-10-28T18:30:00Z"),
       "ipAddress": "192.168.1.100",
       "userAgent": "Mozilla/5.0 ...",
       "revokedAt": null
     }
     ```
   - Sets the session cookie:
     - Name: `joybox_admin_session`
     - Value: `session_token`
     - Attributes: `HttpOnly; Secure; SameSite=Lax; Path=/api/admin; Max-Age=28800`
   - Returns user details and `csrfToken` in the response payload for frontend inclusion in request headers.

2. **Session Expiration Windows:**
   - **Absolute Expiration:** 8 hours from creation. No session may persist past this timestamp.
   - **Idle Timeout:** 30 minutes of inactivity. Each authenticated request updates `lastAccessedAt` and extends `idleExpiresAt` by 30 minutes (up to the absolute expiration).

3. **Logout (`POST /api/admin/auth/logout`):**
   - Sets `revokedAt = now_utc()` on the session document in MongoDB.
   - Clears the `joybox_admin_session` cookie in the client response (`Max-Age=0`).

4. **Global Revocation:**
   - Owners can revoke all active sessions for a target user via `adminSessionRepo.revoke_all_for_user(user_id)`.

---

## 4. Role-Based Access Control (RBAC) Matrix

The system defines three administrative roles with explicit, hierarchical permissions:

| Permission / Action | Owner | Manager | Staff |
| :--- | :---: | :---: | :---: |
| **Authentication & Profile** |
| Login / Logout / View Self | Yes | Yes | Yes |
| Change Own Password | Yes | Yes | Yes |
| Reset Other User Passwords | Yes | No | No |
| Create / Deactivate Admin Users | Yes | No | No |
| **Bookings & Operations** |
| View Bookings & Filters | Yes | Yes | Yes |
| View Full Customer PII (Phone/Email) | Yes | Yes | Yes |
| Update Operational Notes / Check-in | Yes | Yes | Yes |
| Manual / Offline Booking Creation | Yes | Yes | No |
| Administrative Booking Cancellation | Yes | Yes | No |
| **Pricing & Catalog** |
| View Packages & Add-ons | Yes | Yes | Yes |
| Update Package Prices / Add-ons | Yes | Yes | No |
| Create / Deactivate Packages | Yes | No | No |
| **Availability & Calendar Blocks** |
| View Availability & Calendar | Yes | Yes | Yes |
| Create Maintenance / Closed Blocks | Yes | Yes | No |
| Delete Availability Blocks | Yes | Yes | No |
| **Financial & Payments** |
| View Payments & Reconciliations | Yes | Yes | No |
| Process Manual Refunds | Yes | Yes | No |
| Retry Failed Gateway Refunds | Yes | Yes | No |
| Flag / Unflag Payment Reviews | Yes | Yes | No |
| **Audit Logs & Compliance** |
| View Audit Logs | Yes | Yes (Read) | No |
| Export Audit Trail | Yes | No | No |

---

## 5. Audit Logging Architecture

### 5.1 Storage & Immutability
All sensitive state transitions generate an audit log record stored in the MongoDB `auditLogs` collection:
- `_id`: ObjectId
- `actorId`: ObjectId of authenticated user
- `actorUsername`: Username string for fast human-readable triage
- `actorRole`: Role at execution time (`owner`, `manager`, `staff`)
- `action`: Specific standardized action code (e.g., `BOOKING_CANCEL`, `OFFLINE_BOOKING_CREATE`, `REFUND_PROCESS`, `AVAILABILITY_BLOCK_CREATE`, `PRICE_UPDATE`, `USER_CREATE`, `PASSWORD_CHANGE`)
- `targetCollection`: Name of modified collection (e.g., `bookings`, `payments`, `packages`, `availabilityBlocks`)
- `targetId`: String or ObjectId of target document
- `details`: Structured JSON detailing the changes (e.g., previous state vs. new state, refund amount, cancellation reason)
- `requestId`: Unique request trace ID
- `ipAddress`: Client IP (extracted with proxy trust verification)
- `createdAt`: UTC timestamp

### 5.2 Fail-Closed Invariant
For financial operations (refunds) and availability lockouts (calendar blocks), writing the audit log is mandatory: if the audit log insertion raises an exception, the transaction is rejected or rolled back.

---

## 6. HTTP Security Headers

The application factory registers a response middleware applying the following security headers across all responses, with heightened protection on `/api/admin/*`:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin` (and `no-referrer` on admin routes)
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` (on `/api/admin/*`)
- `Content-Security-Policy: default-src 'self'; script-src 'self' https://checkout.razorpay.com; frame-src https://api.razorpay.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://api.razorpay.com;`

