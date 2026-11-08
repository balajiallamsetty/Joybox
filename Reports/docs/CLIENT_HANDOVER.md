# Joybox Party Room — client handover

This package does not include a MongoDB cluster, database user, Razorpay keys, backups, or test databases. Create every account below in the client's own name. Payments stay off until the client finishes Razorpay onboarding (`PAYMENTS_ENABLED=false`). When `PAYMENTS_ENABLED=false`, customers can reserve slots without immediate card/UPI payment and pay balance at the venue. Setting `PAYMENTS_ENABLED=true` on Render enables live Razorpay Standard Web Checkout.

## Accounts the client creates

| Account | What to create | Purpose |
| --- | --- | --- |
| MongoDB Atlas | A new cluster and a user with `readWrite` on `joybox_party_room` only | Application data |
| Render | Web service `joybox-backend` from `render.yaml`, plus the sweep cron | API |
| Vercel | Frontend project, root `frontend` | Public site and `/api` rewrite to Render |
| Domain / DNS | The client's domain pointed at Vercel | Public hostname |
| Razorpay | Live account, when the client is ready | Card and UPI advance. Leave unset until then |
| Sentry | Two projects (API and browser) | Error tracking. Optional until the DSNs exist |
| UptimeRobot | Monitor `HEAD /api/health` every 5 minutes | Wake the Render service and alert the host |

Atlas network access must allow the Render service to connect. Use the client's cluster host in `MONGODB_URI`. Do not reuse a developer cluster.

## Environment variables

Placeholders only. Obtain each value from the account that owns it.

| Name | Where | Purpose | Placeholder |
| --- | --- | --- | --- |
| `MONGODB_URI` | Render | Atlas connection string for the new user | `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/joybox_party_room?retryWrites=true&w=majority` |
| `MONGODB_DB` | Render | Database name | `joybox_party_room` |
| `JWT_SECRET_KEY` | Render | Admin session signing secret | long random string from a password generator |
| `FRONTEND_ORIGIN` | Render | Browser origin allowed to call the API | `https://<the-vercel-domain>` |
| `FLASK_ENV` | Render | Runtime mode | `production` |
| `ADMIN_COOKIE_SECURE` | Render | Cookie only on HTTPS | `true` |
| `ADMIN_COOKIE_SAMESITE` | Render | Cookie site policy | `Lax` |
| `TRUSTED_PROXY_COUNT` | Render | Hops to trust for the client IP. Use `2` for browser, then Vercel, then Render | `2` |
| `RAZORPAY_KEY_ID` | Render | Live key id, later | `rzp_live_replace_me` |
| `RAZORPAY_KEY_SECRET` | Render | Live key secret, later | `replace-with-live-secret` |
| `RAZORPAY_WEBHOOK_SECRET` | Render | Webhook signing secret, later | `replace-with-webhook-secret` |
| `SENTRY_DSN` | Render | API error reporting | `https://<public_key>@o<org>.ingest.sentry.io/<project>` |
| `VITE_API_BASE_URL` | Vercel | API base the browser calls. With the rewrite this is the site origin plus `/api` | `https://<the-vercel-domain>/api` |
| `VITE_RAZORPAY_KEY_ID` | Vercel | Public live key id, same account as the backend | `rzp_live_replace_me` |
| `VITE_WHATSAPP_NUMBER` | Vercel | Host WhatsApp number, digits only | `91XXXXXXXXXX` |
| `VITE_SENTRY_DSN` | Vercel | Browser error reporting | `https://<public_key>@o<org>.ingest.sentry.io/<project>` |

`backend/.env.example` lists the remaining tuning names (session length, rate limits, refund windows, opening hours). Copy it to `backend/.env` on a private machine. `.env` files are git-ignored. Admin cookies are host-only. Do not set a parent cookie domain.

## First run

1. Deploy the API and the site with the variables above. Confirm `GET /api/health` returns success.
2. Create the first admin on a private machine that has the production URI. There is no default password. The interactive script prompts securely via `getpass` with zero terminal echoing. Passwords must strictly satisfy complexity requirements: at least 10 characters, at least one uppercase letter, one lowercase letter, one numeric digit, and one special character (`!@#$%^&*(),.?":{}|<>`). Prompt fields: username, email, display name, role (`owner`), and password:

```powershell
cd backend
python scripts/init_indexes.py --db joybox_party_room --allow-production --confirm-production joybox_party_room
python scripts/create_admin.py --db joybox_party_room --allow-production --confirm-production joybox_party_room
```

3. Sign in at `/admin/login` and change the password from the admin console. The app does not force a password change on first login.
4. Add packages, prices, add-ons, and availability in the admin console. The public site shows "Bookings open soon" and the booking wizard stays closed until packages exist.
5. Replace the policy pages (`/terms`, `/privacy`, `/refund-policy`) with text the host has approved. Verify with the automated policy gate:
```powershell
python backend/scripts/check_policy_placeholders.py
# Or check the live URL:
python backend/scripts/check_policy_placeholders.py https://<the-vercel-domain>
```
The script exits with code 0 only when all placeholder notices have been removed.
6. Book a slot end to end while payments are still deferred, and confirm the hold expires on its own.
7. Turn on the UptimeRobot check and the Sentry projects.

`seed/old_config_export.json` is a catalog snapshot from the previous database (packages, add-ons, one offer, FAQs, and the time-slot constants). It has no customers, bookings, payments, or users. It is not imported automatically. Import it only if the client wants those previous prices.

## Payments & bookings operational switches

The backend provides two primary feature toggles configured via environment variables on Render:

1. **`BOOKINGS_OPEN` (default: `false`):**
   - When `false`, the catalog, quote calculator, and add-on showcases remain viewable, but the booking wizard displays a friendly "Bookings are temporarily closed" banner with a direct WhatsApp contact link, and booking endpoints return `403 Forbidden` (`BOOKINGS_NOT_OPEN`).
   - When set to `true`, the booking wizard opens fully and customers can complete reservations.

2. **`PAYMENTS_ENABLED` (default: `false`):**
   - When `false`, payment endpoints (`/api/create-order`, `/api/verify-payment`, `/api/payments/webhook`) return `403 Forbidden` (`PAYMENTS_DISABLED`), and the checkout step informs customers to reserve without online deposit and settle balance directly at the venue.
   - When the client's live Razorpay merchant account is activated:
     1. Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` on Render, and `VITE_RAZORPAY_KEY_ID` on Vercel.
     2. Register the webhook URL `https://<render-host>/api/payments/webhook` for `payment.captured`, `payment.failed`, and `refund.processed`.
     3. Set `PAYMENTS_ENABLED=true` on Render and `VITE_PAYMENTS_ENABLED=true` on Vercel, then redeploy.

## Live site verification

Before handing over DNS to the client or after deploying new changes, run the automated verification script from any machine with Python 3:

```powershell
python backend/scripts/verify_live.py https://<the-vercel-domain> https://<render-host>/api
```

This script automatically verifies:
- API `/api/health` returns HTTP 200 with status `ok`.
- Public config `/api/public-config` returns valid JSON with `paymentsEnabled` and `bookingsOpen` booleans.
- Catalog `/api/packages` returns at least one package with expected fields.
- Frontend root `/` returns HTTP 200 with proper HTML markup.
- HTTP security headers are present (`X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`).
- No external font requests (`fonts.googleapis.com`, `fonts.gstatic.com`) or design-tool images (`lh3.googleusercontent.com`) leak from the deployed HTML.

## Backup and restore

From `backend`, with the production URI only in the private environment:

```powershell
python scripts/db_backup.py --backup --db joybox_party_room --allow-production --confirm-production joybox_party_room
python scripts/db_backup.py --restore-drill --target-db joybox_party_room_test
```

The restore drill writes into a database whose name ends in `_test`. It does not write over `joybox_party_room`. Keep backup folders outside the git repository and outside any synced drive that other people can open. Delete a backup when it is no longer needed for a restore. `backend/scripts/reset_for_delivery.py` empties a database. It is not part of the Render start command. It refuses to run unless the operator passes `--confirm`, types the database name, and sets `ALLOW_DESTRUCTIVE_SCRIPTS=true` in a local shell. It also refuses pytest, CI, and Render.

## Owner decisions still open (UNCONFIRMED Defaults)

| Decision | Status | What the code does until the owner decides | Config Variable & Default |
| --- | --- | --- | --- |
| **Hold TTL** | Open (UNCONFIRMED) | Reconciled across code, backend, and documentation to 15 minutes | `HOLD_DURATION_MINUTES=15`, `CHECKOUT_GRACE_MINUTES=15` |
| **Refund Tiers** | Open (UNCONFIRMED) | 100% refund at > 48 hours, 50% from 24 to 48 hours, 0% under 24 hours | `REFUND_WINDOW_FULL_HOURS=48`, `REFUND_WINDOW_PARTIAL_HOURS=24`, `REFUND_WINDOW_PARTIAL_PERCENT=50` |
| **GST Invoicing** | Open (UNCONFIRMED) | Defaults to 0% tax until GSTIN registration is confirmed by owner | `GST_RATE_PERCENT=0.0` |
| **Data Retention** | Open (UNCONFIRMED) | No automated retention purge. Backups keep 30 days unless `--retention-days` is passed | `db_backup.py --retention-days 30` |

## Photos needed (replacement of design placeholders)

The landing page uses self-hosted placeholder images stored in `frontend/public/images/placeholders/`. Replace these with actual high-resolution photographs of the Vadlamudi venue:

| Photo Slot | Current File | Display Aspect Ratio | Recommended Resolution | Description & Visual Subject |
| --- | --- | --- | --- | --- |
| **Hero Featured Hall** | `hero-hall-neon.jpg` | 4:5 portrait | 1080 x 1350 px | Wide-angle shot of Joybox Vadlamudi party hall with balloon arch, lighting, and stage setup. |
| **Bento 1: Kids Special** | `gallery-peppa-kids.jpg` | 1:1 square | 1000 x 1000 px | Peppa Pig & Rainbow children's birthday theme party setup. |
| **Bento 2: Teen & Adult** | `gallery-chic-neon.jpg` | 1:1 square | 1000 x 1000 px | Chic neon 21st birthday setup with custom LED signage and mood lighting. |
| **Bento 3: Couples & Anniversary** | `gallery-warm-anniversary.jpg` | 1:1 square | 1000 x 1000 px | Romantic warm gold fairy lights anniversary/proposal room setup. |
| **Bento 4: Squad Adda / Theater** | `hero-hall-neon.jpg` | 1:1 square | 1000 x 1000 px | Private theater / movie screening room setup with high-definition laser projector and sound. |

To replace an image, drop the new JPG file into `frontend/public/images/placeholders/` with the exact filename above, or update the `src` attribute in `frontend/src/pages/LandingPage.jsx`.

## Release commands

This repository has no git remote. Merge and tag on this machine. Tag only after the verification commands in the delivery report have passed.

```powershell
git checkout staging/verification-and-gap-closure
git merge --no-ff release/v1.0.0-delivery
git tag -a v1.0.0 -m "Joybox Party Room v1.0.0 client delivery"
```
