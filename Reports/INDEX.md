# Joybox Party Room — Non-Production & Documentation Relocation Index

This file tracks every non-production file and directory relocated into the `Reports/` folder structure, preserving full Git history while maintaining a clean, production-ready repository root.

---

## 1. Directory Structure

```
Reports/
├── docs/                # All operational documentation, specifications, audit logs, and checklists
├── audit/               # Production release audit reports and scorecards
├── mobile-audit/        # Emulated mobile screenshots across 7 viewports and verification metrics
├── archive/             # Non-production leftovers (design prototypes, legacy scripts, mock exports)
└── INDEX.md             # This comprehensive relocation index
```

---

## 2. Relocated Files Index

| Original Repository Path | New Path in `Reports/` | Category | Reason for Relocation |
|---|---|---|---|
| `PROJECT_LOGIC_DOCUMENTATION.md` | `Reports/docs/PROJECT_LOGIC_DOCUMENTATION.md` | Documentation | Core architectural audit documentation relocated to dedicated docs structure. |
| `docs/*.md` (45+ operational documents) | `Reports/docs/*.md` | Documentation | Clean root organization; preserved for reference, runbooks, and handover. |
| `docs/audit-baseline/*` | `Reports/docs/audit-baseline/*` | Audit Artifact | Historical audit baseline command outputs. |
| `docs/contrast-audit/*` | `Reports/docs/contrast-audit/*` | A11y Artifact | WCAG 2.2 AA color contrast audit matrices and proof images. |
| `docs/delivery-screenshots/*` | `Reports/docs/delivery-screenshots/*` | Screenshots | Visual proof captures for desktop and mobile flows. |
| `docs/evidence/*` | `Reports/docs/evidence/*` | Evidence | Phase 0–7 test outputs and verification transcripts. |
| `docs/responsive-review/*` | `Reports/docs/responsive-review/*` | Screenshots | Viewport audit screenshots and metrics. |
| `docs/visual_audit/*` | `Reports/docs/visual_audit/*` | Screenshots | Pixel-by-pixel comparisons against Stitch designs. |
| `database/indexes.js` | `Reports/archive/database/indexes.js` | Archive | Legacy mongosh index definition; superseded by `backend/scripts/init_indexes.py`. |
| `database/seed.js` | `Reports/archive/database/seed.js` | Archive | Legacy mongosh catalog seeder; superseded by Python seeders. |
| `database/validators.js` | `Reports/archive/database/validators.js` | Archive | Legacy mongosh JSON schema validators; superseded by `init_indexes.py`. |
| `designs/stitch/` | `Reports/archive/designs/stitch/` | Archive | Raw and reference assets from Google Stitch. |
| `designs/strich1/` (9 screens) | `Reports/archive/designs/strich1/` | Archive | Exported static HTML/CSS files from Google Stitch; React implementation is canonical. |
| `seed/old_config_export.json` | `Reports/archive/seed/old_config_export.json` | Archive | Historical backup export; not required for runtime or deployment. |
| `scripts/audit_helpers.py` | `Reports/archive/scripts/audit_helpers.py` | Archive | One-time audit helper utility. |
| `scripts/capture_comparisons.py` | `Reports/archive/scripts/capture_comparisons.py` | Archive | Design comparison capture script. |
| `scripts/find_booking_links.py` | `Reports/archive/scripts/find_booking_links.py` | Archive | Static AST link scanner used during Phase 2. |
| `scripts/find_cta_buttons.py` | `Reports/archive/scripts/find_cta_buttons.py` | Archive | Static CTA scanner used during Phase 2. |
| `scripts/inspect_test_db_claims.py` | `Reports/archive/scripts/inspect_test_db_claims.py` | Archive | Temporary DB claim diagnostic script. |
| `scripts/migrate_slot_claims_date.py` | `Reports/archive/scripts/migrate_slot_claims_date.py` | Archive | One-time date format migration script. |
| `scripts/restore_drill.md` | `Reports/archive/scripts/restore_drill.md` | Archive | Redundant notes superseded by `backend/scripts/db_backup.py`. |
| `scripts/test_e2e_journeys.py` | `Reports/archive/scripts/test_e2e_journeys.py` | Archive | Pre-Playwright python-requests browser runner; replaced by Playwright E2E suite. |
| `scripts/test_live_razorpay_handshake.py` | `Reports/archive/scripts/test_live_razorpay_handshake.py` | Archive | Standalone diagnostic tool; payment flows covered by pytest and live verification. |
| `scripts/test_production_build.py` | `Reports/archive/scripts/test_production_build.py` | Archive | Static build tester superseded by Vite and Playwright. |
| `frontend/scripts/generate_contact_sheet.js` | `Reports/archive/frontend-scripts/generate_contact_sheet.js` | Archive | Standalone contact sheet generator script. |

---

## 3. Files Kept in Root / Active Trees (Safety Invariant)

The following files were intentionally **kept in their original locations** because they are required for build, runtime, deployment, testing, or repository root standards:

- `README.md` — Project root entry point and release documentation.
- `LICENSE` / `pytest.ini` — Root pytest configuration file.
- `.env.example` / `backend/.env.example` / `frontend/.env.example` — Configuration templates.
- `render.yaml` — Infrastructure as Code blueprint for Render web and cron services.
- `backend/Procfile` / `backend/runtime.txt` — Heroku / Render deployment specifications.
- `backend/scripts/*.py` — Operational deployment and administrative commands (`init_indexes.py`, `seed_all.py`, `create_admin.py`, `db_backup.py`, `scan_secrets.py`, `verify_live.py`).
- `.github/workflows/security_and_tests.yml` — Automated CI/CD pipeline.
