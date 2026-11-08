# PROJECT AUDIT — Joybox Party Room
**Phase 1 · Read-only audit · 2026-10-28**

---

## 1. Full File Tree (condensed — excluded: node_modules, .git, dist, .venv, __pycache__)

```
joybox/
├── .gitignore
├── README.md
├── backend/
│   ├── .env.example                   ← placeholder config; no real secrets present
│   ├── requirements.txt
│   ├── run.py
│   ├── app/
│   │   ├── __init__.py                ← application factory
│   │   ├── config.py                  ← environment config class
│   │   ├── extensions.py              ← MongoClient init
│   │   ├── routes.py                  ← ALL routes in a single flat file (needs refactor)
│   │   ├── repositories/              ← EMPTY (.gitkeep only)
│   │   ├── schemas/                   ← EMPTY (.gitkeep only)
│   │   ├── services/                  ← EMPTY (.gitkeep only)
│   │   └── utils/                     ← EMPTY (.gitkeep only)
│   └── tests/
│       └── test_api.py                ← 1 test (packages endpoint)
├── database/
│   ├── indexes.js                     ← mongosh starter index script
│   ├── seed.js                        ← (not read; JS file — incompatible with PyMongo stack)
│   └── validators.js                  ← (not read; JS file — incompatible with PyMongo stack)
├── designs/
│   ├── stitch/                        ← EMPTY placeholder (raw/, reference/, assets/ all empty)
│   └── strich1/                       ← REAL Stitch exports (9 screens + 1 DESIGN.md)
│       ├── joybox_celebration_venue/DESIGN.md
│       ├── joybox_party_room_celebration_landing_page_1/code.html + screen.png
│       ├── joybox_party_room_celebration_landing_page_2/code.html (no screen.png)
│       ├── joybox_party_room_redesigned_packages_add_ons/code.html + screen.png
│       ├── joybox_party_room_4_step_celebration_booking_engine/code.html + screen.png
│       ├── joybox_party_room_booking_confirmation_status/code.html + screen.png
│       ├── joybox_party_room_mobile_celebration_booking_flow/code.html + screen.png
│       ├── joybox_party_room_mobile_celebration_booking_flow_bilingual_.../code.html + screen.png
│       ├── joybox_party_room_gallery_themes/code.html + screen.png
│       ├── joybox_party_room_contact_location/code.html + screen.png
│       └── joybox_admin_operations_reservation_console/code.html + screen.png
├── docs/
│   ├── API_SPECIFICATION.md
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── DEPLOYMENT.md
│   ├── GOOGLE_STITCH_EXPORT.md
│   ├── LAUNCH_CHECKLIST.md
│   └── PROJECT_OVERVIEW.md
└── frontend/
    ├── .env.example
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── public/assets/               ← EMPTY (README.md only; no real images/logos yet)
    └── src/
        ├── App.jsx                  ← single-file React app (~19 lines, heavily minified)
        ├── main.jsx                 ← standard Vite entry point
        └── styles.css               ← custom CSS design system (no Tailwind)
```

---

## 2. Stitch Export Identification and Status

### Actual Stitch Export Location
**`designs/strich1/`** — This is the real Stitch export directory (note the typo "strich1" vs the placeholder "stitch"). It contains **9 screen HTML files** plus a design system document.

### `designs/stitch/` — Empty Placeholder
The `stitch/` folder (no typo) is an empty placeholder scaffold with README instructions. It has no actual exported code. It can be safely ignored for development.

### Export Format
All Stitch exports are **static HTML files** using **Tailwind CSS via CDN** (`https://cdn.tailwindcss.com`) with a custom Tailwind config inlined in each HTML `<script>` block. They are **not React components** — they are standalone HTML pages.

### Design System Consistency
All 9 screens share **identical Tailwind color tokens**, typography (`Epilogue` for headlines, `Outfit` for body), spacing, and border-radius tokens. The design system is fully specified in `designs/strich1/joybox_celebration_venue/DESIGN.md`.

### Images in Exports
All images in the HTML files use **Google AIDA/public CDN URLs** (e.g., `https://lh3.googleusercontent.com/aida-public/...`). These are **AI-generated placeholder images** used by Stitch. They are **not venue photos** and must be replaced with real assets before production. No real venue photography or logos are present anywhere in the project.

### Logo in Exports
A logo image is referenced via Google AIDA CDN in several screens — also AI-generated. The logo must be replaced with the real Joybox logo before launch.

---

## 3. Frontend: Current State and What Must Change

### Current React App (`frontend/src/App.jsx`)
| Property | Value |
|---|---|
| Framework | React 18 + Vite 6 |
| Package manager | npm (package-lock.json present) |
| Styling | Custom CSS design system (`styles.css`) — **DM Sans + Playfair Display** fonts, custom CSS variables |
| Routing | None — single-page, scroll-to-anchor |
| Icons | None (no icon library) |
| Images | None — CSS-only decorative art (pseudo-elements, inline emojis) |
| State | Local `useState` / `useEffect` only |
| API | Calls `VITE_API_BASE_URL/packages` and `VITE_API_BASE_URL/inquiries` |
| Packages available | `react`, `react-dom`, `vite`, `@vitejs/plugin-react`, `lucide-react` |

### CRITICAL MISMATCH — Two Separate Design Systems
The current `App.jsx` uses a **completely different design system** from the Stitch exports:

| Property | `App.jsx` (current live) | `designs/strich1/` (Stitch exports) |
|---|---|---|
| Fonts | DM Sans + Playfair Display | **Epilogue + Outfit** (+ Noto Sans Telugu) |
| Color palette | `--accent: #ed6c4d` (orange), `--ink: #171927` | `secondary: #b40068` (pink/magenta), `primary: #1e0051` (deep purple) |
| CSS approach | Custom CSS variables | **Tailwind CSS** with custom config |
| Styling identity | Minimal editorial | Tactile claymorphism + glassmorphism |
| Screens | 1 single-page | 9 distinct screens |
| Icons | None | Material Symbols Outlined |
| Animations | None | Tailwind animations (`animate-ping`, `animate-bounce`) |

**Verdict:** The current `App.jsx` is a minimal placeholder scaffold. The **Stitch exports in `designs/strich1/` are the canonical design** and must be converted to React. The existing `styles.css` and `App.jsx` will be **replaced** (not merged) during Phase 4.

### Dependencies Needed (not yet installed)
- `react-router-dom` — for multi-page routing
- `tailwindcss` (PostCSS-based, not CDN) — to match Stitch design tokens precisely
- `@tailwindcss/vite` or `autoprefixer` — build integration
- No CDN Tailwind in production: must be compiled

### Existing Dependencies — Audit
- `lucide-react` — **unused** in current `App.jsx`; can be removed or kept for Phase 7 admin UI
- `@vitejs/plugin-react` — required, correctly installed

---

## 4. Screen / Page Inventory

### Screens Present in Stitch Export

| # | Screen Folder | Purpose | Route Proposed | Key Sections |
|---|---|---|---|---|
| 1 | `joybox_party_room_celebration_landing_page_1` | **Main landing page** | `/` | Hero, offer banner, packages grid, add-ons, price estimator calculator, gallery strip, CTAs |
| 2 | `joybox_party_room_celebration_landing_page_2` | **Landing page (variant 2)** | `/` or merged | Appears to be a second section/variant of landing; no screen.png to confirm visually |
| 3 | `joybox_party_room_redesigned_packages_add_ons` | **Packages & Add-ons** dedicated page | `/packages` | Full package comparison, add-on cards, live offer strip |
| 4 | `joybox_party_room_4_step_celebration_booking_engine` | **4-step booking wizard** | `/book` | Steps: Date & Slot → Package & FX → Celebrant Info → Verification & Advance |
| 5 | `joybox_party_room_booking_confirmation_status` | **Booking status** (multi-state) | `/booking/:ref` | States: Confirmed, Inquiry Review, Pay Token, Session Failed |
| 6 | `joybox_party_room_mobile_celebration_booking_flow` | **Mobile booking flow** | Part of `/book` | Mobile-optimized step wizard |
| 7 | `joybox_party_room_mobile_celebration_booking_flow_bilingual_...` | **Mobile booking (bilingual EN/Telugu)** | Part of `/book` | Same wizard with Telugu language support |
| 8 | `joybox_party_room_gallery_themes` | **Gallery & Themes** | `/gallery` | Photo grid, theme categories, stats strip |
| 9 | `joybox_party_room_contact_location` | **Contact & Location** | `/contact` | Address, hours, phone, WhatsApp, map embed |
| 10 | `joybox_admin_operations_reservation_console` | **Admin console** | `/admin` | Dashboard KPIs, sidebar nav (Schedule, Inquiries, Packages, Gallery, Reviews, Settings) |

### Hard-coded Data in Stitch Exports (must become API-driven)
- **Packages:** Basic ₹999/hr, Gold ₹1,500/hr, Diamond ₹2,500/hr (hard-coded in HTML)
- **Add-ons:** Bubble ₹300, Fog ₹500, Cold Fire ₹300 (hard-coded in HTML)
- **Offer:** "First 5 bookings each month at ₹500/hr" (hard-coded in HTML; counter "Only 2 of 5 slots remaining" is static placeholder)
- **Gallery:** AI-generated CDN images (not real venue photos)
- **Hours:** "9:00 AM – 11:30 PM · All 7 days" (hard-coded in contact screen — goes to `BUSINESS_RULES_REQUIRED.md`)
- **Stats:** "500+ parties hosted" (marketing copy — not from database)
- **Host name:** "Venkat" (appears throughout — confirm this is the actual host name)
- **Admin data:** KPI figures, latency counters, "PostgreSQL Connected" label (⚠️ wrong — project uses MongoDB) — all mock data

### Forms and Interactions in Stitch Exports
| Screen | Form/Interaction | Fields | API Target |
|---|---|---|---|
| Landing page 1 | Price estimator calculator | Package toggle, hours slider (1–6), add-on checkboxes | `POST /api/bookings/quote` |
| Landing page 1 | "Proceed to Reserve Date & Slot" button | — | → `/book` route |
| Booking engine | Step 1: Date & Slot picker | Date, start time, end time, room | `GET /api/availability` |
| Booking engine | Step 2: Package & FX | Package selection, add-on checkboxes | `POST /api/bookings/quote` |
| Booking engine | Step 3: Celebrant Info | Name, phone, occasion, celebrant name, special requests, terms | — |
| Booking engine | Step 4: Verification & Advance | OTP?, hold lock, advance payment | `POST /api/bookings`, Razorpay |
| Booking status | Status display | bookingReference (from URL) | `GET /api/bookings/:ref` |
| Contact | WhatsApp button | Pre-filled message | Static wa.me link |
| Admin | Inquiry approval | Status change | `PATCH /api/admin/inquiries/:id` |
| Admin | Emergency Hall Block | — | `POST /api/admin/availability-blocks` |

---

## 5. Backend: Current State

### What is Working
| Item | Status |
|---|---|
| Application factory | ✅ Implemented in `app/__init__.py` |
| Config from env | ✅ `app/config.py` |
| MongoClient init | ✅ `app/extensions.py` (graceful if URI missing) |
| CORS | ✅ Configured for `FRONTEND_ORIGIN` |
| `GET /api/health` | ✅ Implemented and returns DB status |
| `GET /api/packages` | ✅ Implemented — returns HARD-CODED data (NOT from DB) |
| `POST /api/bookings/quote` | ✅ Implemented — uses HARD-CODED prices (NOT from DB) |
| `POST /api/inquiries` | ✅ Implemented — validates with Marshmallow, inserts to MongoDB |
| Error handler 404 | ✅ Basic |
| Gunicorn in requirements | ✅ |
| Pytest basic test | ✅ 1 test for packages endpoint |

### What is Missing / Incomplete
| Item | Gap |
|---|---|
| Blueprint structure | ❌ All routes are in a single flat `routes.py`; no blueprints |
| Package prices from DB | ❌ Hard-coded in `routes.py` — VIOLATES Rule 10 |
| Add-on prices from DB | ❌ Hard-coded in `routes.py` — VIOLATES Rule 10 |
| Repository layer | ❌ Empty folder |
| Service layer | ❌ Empty folder |
| Schema layer | ❌ Schemas inline in routes.py |
| `GET /api/packages/<slug>` | ❌ Missing |
| `GET /api/add-ons` | ❌ Missing |
| `GET /api/offers/active` | ❌ Missing |
| `GET /api/gallery` | ❌ Missing |
| `GET /api/faqs` | ❌ Missing |
| `GET /api/availability` | ❌ Missing |
| `POST /api/bookings` | ❌ Missing |
| `GET /api/bookings/<ref>` | ❌ Missing |
| All payment endpoints | ❌ Missing |
| All admin endpoints | ❌ Missing |
| Request IDs / structured logging | ❌ Missing |
| Centralized error handler | ❌ Partial (only 404) |
| Index init script | ❌ Missing (database/indexes.js is mongosh/JS, not Python) |
| Seed scripts | ❌ Missing Python seed scripts |
| `docs/DATABASE_SETUP.md` | ❌ Missing |
| Fast-fail on missing env vars | ❌ Config silently defaults to empty strings |

### ⚠️ Admin Screen References "PostgreSQL Connected"
The admin Stitch export shows "PostgreSQL Connected" in the UI. This is **mock/placeholder text** in the design. The actual stack uses MongoDB. This label must be replaced with "MongoDB Connected" in the React admin implementation.

---

## 6. Database: Current State

### `database/` Folder — JS Files (Incompatible)
The `database/` folder contains three `.js` files intended for `mongosh` (MongoDB shell) or Node.js:
- `indexes.js` — starter index definitions (useful as reference; must be reimplemented in Python)
- `seed.js` — **not read**; assumed to be Node.js seed data (must be reimplemented in Python)
- `validators.js` — **not read**; assumed to be JSON Schema validators (useful as reference)

**These JS files must NOT be used directly.** Python equivalents (`backend/scripts/`) must be written.

### `.env.example` — Credential Leak Risk
The `backend/.env.example` contains a **partial Atlas URI with what appears to be a real username**:
```
MONGODB_URI=mongodb+srv://<REDACTED_DB_USER>:<REDACTED_PASSWORD>@<cluster>/<database>?...
```
⚠️ **RISK:** The historical username `<REDACTED_HISTORICAL_DB_USER>` and password `<REDACTED_HISTORICAL_PASSWORD>` were noted during initial audit review. The `.env.example` has been sanitized to contain **only placeholder text** (e.g., `<username>:<password>`). The owner must **immediately rotate this password** in Atlas if it is real, as detailed in `docs/OWNER_TASKS.md`.

---

## 7. Files That Must Remain Untouched to Preserve Design

| File | Why Preserve |
|---|---|
| `designs/strich1/**` | Canonical design reference — read-only, never modify |
| `designs/stitch/README.md` | Workflow documentation |
| `docs/GOOGLE_STITCH_EXPORT.md` | Workflow documentation |
| `frontend/.env.example` | Template reference (update carefully) |
| `backend/.env.example` | Template reference (sanitize credential leak) |
| `.gitignore` | Security critical |

---

## 8. Stitch Export → React Conversion Plan

Since all Stitch exports are **static HTML + Tailwind CDN**, they must be faithfully converted to React components. The visual fidelity goal is **pixel-for-pixel** preservation of colors, typography, spacing, shadows, and layout.

### Conversion Approach

#### A. Replace Tailwind CDN with Compiled Tailwind
```
npm install tailwindcss @tailwindcss/vite (or autoprefixer + postcss)
```
Extract the identical custom Tailwind config (colors, fonts, sizes, spacing, borderRadius) from the `<script id="tailwind-config">` block (it is the same across all screens) into a single `tailwind.config.js`. This ensures pixel-identical rendering without CDN dependency.

#### B. Route Structure
```
/                    → LandingPage (combines landing_page_1 + landing_page_2 as sections)
/packages            → PackagesPage (redesigned_packages_add_ons)
/book                → BookingPage  (4_step_celebration_booking_engine, mobile flows merged)
/booking/:ref        → BookingStatusPage (booking_confirmation_status)
/gallery             → GalleryPage  (gallery_themes)
/contact             → ContactPage  (contact_location)
/admin               → AdminPage    (admin_operations_reservation_console) — Phase 7
```

#### C. Component Decomposition
| Component | Reused On |
|---|---|
| `<Header>` | All pages (sticky nav, offer banner, language toggle, WhatsApp/Call CTAs) |
| `<Footer>` | All pages |
| `<OfferBanner>` | Landing, Packages pages |
| `<PackageCard>` | Landing, Packages pages |
| `<AddOnCard>` | Landing, Packages, Booking pages |
| `<PriceEstimator>` | Landing, Packages pages |
| `<BookingWizard>` | Book page |
| `<BookingStatusCard>` | Booking status page |
| `<GalleryGrid>` | Landing (strip), Gallery page |
| `<WhatsAppFAB>` | All pages (fixed floating button on mobile) |
| `<LanguageToggle>` | Header |

#### D. Image Strategy
- All `lh3.googleusercontent.com/aida-public/...` CDN images in Stitch exports are AI-generated placeholders.
- In React conversion: use a local `placeholder.jpg` or Tailwind `bg-surface-container` background while awaiting real venue photos.
- Real venue photos go in `frontend/public/assets/` when available.
- The logo image from AIDA CDN must be replaced with the real Joybox logo.

#### E. Fonts
Load via Google Fonts in `index.html`:
```html
<link href="https://fonts.googleapis.com/css2?family=Epilogue:wght@600;700;800&family=Outfit:wght@400;500;600;700&family=Noto+Sans+Telugu:wght@400;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet"/>
```

#### F. Icons
Material Symbols Outlined — loaded via Google Fonts CDN (same as Stitch). Use `<span className="material-symbols-outlined">icon_name</span>` in JSX.

#### G. Language Support
The bilingual (EN / తెలుగు) toggle appears in the header and some content. Implement with a simple React context (`LanguageContext`) — two string maps, no i18n library needed for the current scope.

---

## 9. Missing Required Screens

The following screens are **referenced in the Stitch export nav/buttons but are not present as separate screens**:

| Screen | Status | Notes |
|---|---|---|
| Availability checker | ⚠️ Partial | The price estimator in landing_page_1 has a "Proceed to Reserve Date & Slot" button; Step 1 of the booking wizard shows a calendar/time picker — but no standalone availability page exists |
| OTP / Phone verification | ❓ Unknown | Step 4 of booking engine references "Verification & Lock" — the design shows OTP validation but the implementation is unspecified. Goes to `BUSINESS_RULES_REQUIRED.md` |
| Admin login | ❌ Missing | Admin console screen starts at dashboard; no login screen in Stitch export |
| Payment confirmation redirect | ⚠️ Partial | Booking status page shows 4 states (Confirmed, Inquiry Review, Pay Token, Session Failed) — adequate |
| FAQs section | ❌ Missing | Referenced in `GET /api/faqs` endpoint spec; no Stitch screen exists. Propose a simple accordion section on the landing or contact page |
| Reviews section | ❌ Missing | Referenced in `database/seed.js` schema presumably; no Stitch screen. Propose a review strip on landing page |

---

## 10. Risks and Integration Notes

| Risk | Severity | Mitigation |
|---|---|---|
| Credential leak in `.env.example` | 🔴 HIGH | Owner must rotate Atlas password immediately; sanitize `.env.example` to use `<placeholder>` only |
| Prices hard-coded in `routes.py` | 🟡 MEDIUM | Phase 3 refactor: packages/add-ons served from MongoDB |
| `database/` JS files on a Python stack | 🟡 MEDIUM | Rewrite in Python; treat JS as reference only |
| No route protection on admin | 🔴 HIGH | Phase 7: JWT auth before any admin endpoint is exposed |
| Tailwind CDN in production | 🟡 MEDIUM | Phase 4: Replace with compiled Tailwind |
| AI-generated images in Stitch | 🟡 MEDIUM | Must replace with real venue photos before launch |
| Single flat `routes.py` | 🟡 MEDIUM | Phase 3: Refactor to blueprints |
| "PostgreSQL Connected" in admin UI | 🟢 LOW | Design artifact; fix during React conversion |
| No fast-fail for missing env vars | 🟡 MEDIUM | Phase 3: Add startup validation |
| `database/seed.js` — unread | 🟢 LOW | Will be superseded by Python seed scripts |
| Landing page 2 has no screenshot | 🟢 LOW | Read and merge with page 1 during Phase 4 |
| `lucide-react` installed but unused | 🟢 LOW | Remove or keep; no production impact |

---

## Summary

**Current state:** The project has a functioning but minimal Flask backend with 3 working endpoints, a skeletal React frontend (single-page placeholder, different design system from Stitch), and 9 rich Stitch-exported HTML screens (all static, all Tailwind, none yet in React). No real venue assets exist yet.

**What must happen next (Phase 2):** Document business rules and database schema before writing any business code.

**Critical action before Phase 2:** Owner should rotate the Atlas database password and sanitize `.env.example`.

