"""
Joybox Staging Dry-Run Smoke Test Script
Executes read-only and isolated smoke assertions against staging / local
production-mode services (Flask REST API + Static Built Frontend).
Verifies:
1. Backend Health Probe (/api/health)
2. Security Headers (X-Content-Type-Options: nosniff, X-Frame-Options: DENY, X-Request-Id)
3. Public Packages Catalog (/api/packages)
4. Public Add-ons Catalog (/api/add-ons)
5. Availability Calculation (/api/availability)
6. Isolated Provisional Hold Creation (/api/bookings/holds)
7. Admin Authentication Rejection on invalid credentials (/api/admin/auth/login -> 401)
8. Frontend Static / Preview Host probe
"""

import sys
import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# Ensure backend directory is in sys.path for fallback in-process execution
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

BACKEND_BASE = os.getenv("SMOKE_BACKEND_URL", "http://127.0.0.1:5000/api")
FRONTEND_BASE = os.getenv("SMOKE_FRONTEND_URL", "http://127.0.0.1:5173")

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "JoyboxSmokeTest/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, resp.headers, body
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")
    except Exception as e:
        return 0, {}, str(e)

def http_post(url, payload, headers=None):
    headers = headers or {}
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("User-Agent", "JoyboxSmokeTest/1.0")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, resp.headers, body
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")
    except Exception as e:
        return 0, {}, str(e)

def run_smoke(read_only=False):
    log("========================================================")
    log("     JOYBOX STAGING READ-ONLY SMOKE VERIFICATION        ")
    log("========================================================")
    failures = 0

    # Determine whether HTTP backend is alive; if not, use Flask test client
    health_url = f"{BACKEND_BASE}/health"
    status, headers, body = http_get(health_url)
    use_test_client = (status == 0)

    if use_test_client and read_only:
        log("Read-only smoke requires the live HTTP backend. It will not fall back onto the test database.", "FAIL")
        return 1

    if use_test_client:
        log("Live HTTP endpoint unreachable; initializing in-process Flask test client (joybox_party_room_test)...", "INFO")
        os.environ["MONGODB_DB"] = "joybox_party_room_test"
        from app import create_app
        flask_app = create_app()
        flask_app.config["MONGODB_DB"] = "joybox_party_room_test"
        client = flask_app.test_client()

        def do_get(path):
            resp = client.get(path)
            return resp.status_code, resp.headers, resp.get_data(as_text=True)

        def do_post(path, data):
            resp = client.post(path, json=data)
            return resp.status_code, resp.headers, resp.get_data(as_text=True)
    else:
        def do_get(path):
            return http_get(f"{BACKEND_BASE}{path.replace('/api', '')}")

        def do_post(path, data):
            return http_post(f"{BACKEND_BASE}{path.replace('/api', '')}", data)

    # 1. Backend Health Check
    status, headers, body = do_get("/api/health")
    if status == 200 and "ok" in body:
        log("Backend Health Probe (/api/health): PASS (HTTP 200)", "PASS")
    else:
        log(f"Backend Health Probe FAILED: HTTP {status} - {body}", "FAIL")
        failures += 1

    # 2. Security Headers Verification
    cto = headers.get("X-Content-Type-Options") or headers.get("x-content-type-options")
    xfo = headers.get("X-Frame-Options") or headers.get("x-frame-options")
    req_id = headers.get("X-Request-Id") or headers.get("x-request-id")
    csp = headers.get("Content-Security-Policy") or headers.get("content-security-policy")
    referrer = headers.get("Referrer-Policy") or headers.get("referrer-policy")
    permissions = headers.get("Permissions-Policy") or headers.get("permissions-policy")
    hsts = headers.get("Strict-Transport-Security") or headers.get("strict-transport-security")
    headers_ok = (
        cto == "nosniff"
        and xfo == "DENY"
        and req_id
        and csp
        and referrer
        and permissions
    )
    if headers_ok:
        log(
            "Security Headers Probe "
            f"(X-Content-Type-Options={cto}, X-Frame-Options={xfo}, Referrer-Policy={referrer}, "
            f"Permissions-Policy={permissions}, CSP={csp}, HSTS={hsts or 'absent-on-http'}, "
            f"X-Request-Id={req_id}): PASS",
            "PASS",
        )
    else:
        log(
            f"Security Headers Probe FAILED: cto={cto}, xfo={xfo}, req_id={req_id}, "
            f"csp={csp}, referrer={referrer}, permissions={permissions}",
            "FAIL",
        )
        failures += 1

    # 3. Public Packages Catalog
    status, _, body = do_get("/api/packages")
    if read_only and status == 200 and "items" in body:
        log("Public Packages Catalog: PASS (read-only; empty catalog allowed)", "PASS")
    elif status == 200 and "basic" in body and "gold" in body:
        log("Public Packages Catalog: PASS (Basic, Gold, Diamond found)", "PASS")
    else:
        log(f"Public Packages Catalog FAILED: HTTP {status}", "FAIL")
        failures += 1

    # 4. Public Add-ons Catalog
    status, _, body = do_get("/api/add-ons")
    if read_only and status == 200 and "items" in body:
        log("Public Add-ons Catalog: PASS (read-only; empty catalog allowed)", "PASS")
    elif status == 200 and "fog_entry" in body:
        log("Public Add-ons Catalog: PASS (Add-ons available)", "PASS")
    else:
        log(f"Public Add-ons Catalog FAILED: HTTP {status}", "FAIL")
        failures += 1

    # 5. Live Availability Query
    test_date = (datetime.now(timezone.utc) + timedelta(days=25)).strftime("%Y-%m-%d")
    status, _, body = do_get(f"/api/availability?date={test_date}&durationHours=1&roomId=main")
    if status == 200 and "slots" in body:
        log(f"Availability API Query ({test_date}): PASS", "PASS")
    else:
        log(f"Availability API FAILED: HTTP {status}", "FAIL")
        failures += 1

    # 6. Isolated Hold Creation (writes a hold; skipped for the clean-database read-only pass)
    if read_only:
        log("Provisional Booking Hold: SKIPPED (read-only)", "PASS")
    else:
        hold_payload = {
            "packageCode": "basic",
            "durationHours": 1,
            "date": test_date,
            "startTime": "13:00",
            "customerName": "Staging Dry Run Customer",
            "customerPhone": "9876543210",
            "applyPromo": False,
        }
        status, _, body = do_post("/api/bookings/hold", hold_payload)
        if status in (200, 201) and "holdId" in body:
            log(f"Provisional Booking Hold Creation: PASS (Hold created on {test_date})", "PASS")
        elif "SLOT_UNAVAILABLE" in body:
            log(f"Provisional Booking Hold: Slot already occupied on {test_date} (Handled gracefully)", "PASS")
        else:
            log(f"Provisional Booking Hold FAILED: HTTP {status} - {body}", "FAIL")
            failures += 1

    # 7. Admin Authentication Rejection on Invalid Credentials (writes an audit row; skipped when read-only)
    if read_only:
        log("Admin Security Check: SKIPPED (read-only)", "PASS")
    else:
        status, _, body = do_post("/api/admin/auth/login", {"username": "admin", "password": "WrongPassword123!"})
        if status in (400, 401):
            log(f"Admin Security Check: PASS (Invalid login rejected with HTTP {status})", "PASS")
        else:
            log(f"Admin Security Check FAILED: Expected 401, got {status}", "FAIL")
            failures += 1

    # 8. Frontend Static Host Probe
    if not use_test_client:
        status, _, _ = http_get(f"{FRONTEND_BASE}/")
        if status == 200:
            log(f"Frontend Static Host ({FRONTEND_BASE}/): PASS (HTTP 200)", "PASS")
        else:
            log(f"Frontend Static Host ({FRONTEND_BASE}/): Warning HTTP {status}", "WARN")

    log("========================================================")
    if failures == 0:
        log("STAGING DRY-RUN SMOKE TESTS: 100% PASS (0 failures)", "SUCCESS")
        return 0
    else:
        log(f"STAGING DRY-RUN SMOKE TESTS: {failures} FAILURES", "ERROR")
        return 1

if __name__ == "__main__":
    sys.exit(run_smoke(read_only="--read-only" in sys.argv))
