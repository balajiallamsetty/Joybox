#!/usr/bin/env python3
"""
Joybox Party Room — Live Production / Staging Preview Verification Script
Performs read-only validation against deployed or local staging services.

Usage:
    python backend/scripts/verify_live.py <frontend_url> <api_url>
Example:
    python backend/scripts/verify_live.py http://127.0.0.1:5173 http://127.0.0.1:5000
"""

import sys
import time
import urllib.request
import urllib.error
import json
import re

BANNED_FRONTEND_DOMAINS = [
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "lh3.googleusercontent.com",
]

def make_request(url, headers=None):
    headers = headers or {"User-Agent": "Joybox-Live-Verifier/1.0"}
    req = urllib.request.Request(url, headers=headers)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            body = resp.read().decode("utf-8")
            return resp.status, resp.headers, body, elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        body = e.read().decode("utf-8") if e.fp else ""
        return e.code, e.headers, body, elapsed_ms
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return 0, {}, str(e), elapsed_ms

def check(name, condition, details=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name} {details}")
    return condition

def main():
    if len(sys.argv) < 3:
        print("Usage: python backend/scripts/verify_live.py <frontend_url> <api_url>")
        sys.exit(1)

    frontend_url = sys.argv[1].rstrip("/")
    api_url = sys.argv[2].rstrip("/")

    # Ensure api_url ends with /api if omitted
    if not api_url.endswith("/api") and "/api" not in api_url:
        api_base = f"{api_url}/api"
    else:
        api_base = api_url

    print("=" * 70)
    print("JOYBOX PARTY ROOM — LIVE PREVIEW VERIFICATION")
    print(f"Frontend URL : {frontend_url}")
    print(f"API Base URL : {api_base}")
    print("=" * 70)

    all_passed = True

    # 1. GET /api/health
    status, headers, body, elapsed = make_request(f"{api_base}/health")
    db_connected = False
    if status == 200:
        try:
            data = json.loads(body)
            db_connected = data.get("data", {}).get("database") in ("connected", "ok", True)
        except Exception:
            pass
    all_passed &= check("1. GET /api/health", status == 200 and db_connected, f"({elapsed:.1f}ms, HTTP {status}, DB: {'connected' if db_connected else 'down'})")

    # 2. Security Headers on API
    ct_opts = headers.get("X-Content-Type-Options") == "nosniff" if headers else False
    has_frame_opts = bool(headers.get("X-Frame-Options")) if headers else False
    all_passed &= check("2. API Security Headers", ct_opts, f"(nosniff: {ct_opts}, X-Frame-Options: {has_frame_opts})")

    # 3. GET /api/public-config
    status, _, body, elapsed = make_request(f"{api_base}/public-config")
    cfg_valid = False
    bookings_open = None
    payments_enabled = None
    if status == 200:
        try:
            data = json.loads(body).get("data", {})
            bookings_open = data.get("bookingsOpen")
            payments_enabled = data.get("paymentsEnabled")
            cfg_valid = bookings_open is not None and payments_enabled is not None
        except Exception:
            pass
    all_passed &= check("3. GET /api/public-config", cfg_valid, f"({elapsed:.1f}ms, bookingsOpen: {bookings_open}, paymentsEnabled: {payments_enabled})")

    # 4. GET /api/packages (count >= 3)
    status, _, body, elapsed = make_request(f"{api_base}/packages")
    pkg_count = 0
    if status == 200:
        try:
            data = json.loads(body).get("data", {})
            pkg_count = len(data.get("items", []))
        except Exception:
            pass
    all_passed &= check("4. GET /api/packages", pkg_count >= 3, f"({elapsed:.1f}ms, count: {pkg_count} packages)")

    # 5. GET /api/add-ons (count >= 3)
    status, _, body, elapsed = make_request(f"{api_base}/add-ons")
    addon_count = 0
    if status == 200:
        try:
            data = json.loads(body).get("data", {})
            addon_count = len(data.get("items", []))
        except Exception:
            pass
    all_passed &= check("5. GET /api/add-ons", addon_count >= 3, f"({elapsed:.1f}ms, count: {addon_count} celebration add-ons)")

    # 6. Frontend Index HTML Validation
    status, _, body, elapsed = make_request(f"{frontend_url}/")
    html_ok = status == 200 and ("Joybox" in body or "<div id=\"root\">" in body)
    leaked_domains = [d for d in BANNED_FRONTEND_DOMAINS if d in body]
    assets_clean = len(leaked_domains) == 0
    all_passed &= check("6. Frontend HTML Load & Integrity", html_ok, f"({elapsed:.1f}ms, HTTP {status})")
    all_passed &= check("7. Self-Hosted Asset Guard (No Google Fonts/Images in HTML)", assets_clean, f"(Banned domains found: {leaked_domains})")

    print("=" * 70)
    if all_passed:
        print("VERIFICATION RESULT: ALL CHECKS PASSED (Ready for customer traffic)")
        sys.exit(0)
    else:
        print("VERIFICATION RESULT: ONE OR MORE CHECKS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
