import concurrent.futures
import hashlib
import json
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from bson import ObjectId

from backend.app import create_app
from backend.app.config import Config
from backend.app.repositories import (
    UserRepository,
    AdminSessionRepository,
    AuditLogRepository,
    BookingRepository,
    SlotClaimRepository,
    AvailabilityBlockRepository,
)
from backend.app.services.admin_service import AdminService
from backend.app.utils.datetime_utils import now_utc, now_ist

@pytest.fixture
def admin_fixture(live_test_client):
    test_db = live_test_client
    app = create_app({"TESTING": True, "BOOKINGS_OPEN": True})
    app.config["TESTING"] = True
    app.config["BOOKINGS_OPEN"] = True
    app.config["MONGODB_DB_NAME"] = test_db.name
    app.extensions["mongo_db"] = test_db
    app.extensions["admin_session_repo"] = AdminSessionRepository(test_db)
    app.extensions["user_repo"] = UserRepository(test_db)
    app.extensions["audit_repo"] = AuditLogRepository(test_db)

    # Seed test users
    user_repo = app.extensions["user_repo"]
    now_u = now_utc()

    # Owner
    owner_pass_hash = AdminService.hash_password("OwnerPassword123!")
    user_repo.collection.update_one(
        {"username": "test_owner"},
        {"$set": {
            "username": "test_owner",
            "email": "owner@test.joybox",
            "displayName": "Test Owner",
            "passwordHash": owner_pass_hash,
            "role": "owner",
            "isActive": True,
            "failedLoginAttempts": 0,
            "lockoutUntil": None,
            "updatedAt": now_u
        }},
        upsert=True
    )

    # Manager
    mgr_pass_hash = AdminService.hash_password("ManagerPassword123!")
    user_repo.collection.update_one(
        {"username": "test_mgr"},
        {"$set": {
            "username": "test_mgr",
            "email": "mgr@test.joybox",
            "displayName": "Test Manager",
            "passwordHash": mgr_pass_hash,
            "role": "manager",
            "isActive": True,
            "failedLoginAttempts": 0,
            "lockoutUntil": None,
            "updatedAt": now_u
        }},
        upsert=True
    )

    # Staff
    staff_pass_hash = AdminService.hash_password("StaffPassword123!")
    user_repo.collection.update_one(
        {"username": "test_staff_user"},
        {"$set": {
            "username": "test_staff_user",
            "email": "staff@test.joybox",
            "displayName": "Test Staff",
            "passwordHash": staff_pass_hash,
            "role": "staff",
            "isActive": True,
            "failedLoginAttempts": 0,
            "lockoutUntil": None,
            "updatedAt": now_u
        }},
        upsert=True
    )

    return {
        "app": app,
        "test_db": test_db,
        "user_repo": user_repo,
        "session_repo": app.extensions["admin_session_repo"],
        "audit_repo": app.extensions["audit_repo"],
    }

def _login(client, username, password):
    res = client.post("/api/admin/auth/login", json={"username": username, "password": password})
    csrf = ""
    if res.is_json and res.json and res.json.get("data"):
        csrf = res.json["data"].get("csrfToken", "")
    return res, csrf

def test_admin_login_success_and_cookie(admin_fixture):
    app = admin_fixture["app"]
    with app.test_client() as client:
        res, csrf = _login(client, "test_owner", "OwnerPassword123!")
        assert res.status_code == 200
        assert res.json["success"] is True
        assert res.json["data"]["user"]["username"] == "test_owner"
        assert res.json["data"]["user"]["role"] == "owner"
        assert len(csrf) > 10

        # Verify HttpOnly cookie was set
        set_cookie_header = res.headers.get("Set-Cookie", "")
        assert "joybox_admin_session" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "Domain=" not in set_cookie_header
        assert "domain=" not in set_cookie_header

        # Verify /auth/me returns current user
        me_res = client.get("/api/admin/auth/me")
        assert me_res.status_code == 200
        assert me_res.json["data"]["user"]["username"] == "test_owner"

def test_admin_login_invalid_password(admin_fixture):
    app = admin_fixture["app"]
    with app.test_client() as client:
        res, _ = _login(client, "test_owner", "WrongPassword!")
        assert res.status_code == 401
        assert res.json["error"]["code"] == "INVALID_CREDENTIALS"

def test_admin_login_nonexistent_user(admin_fixture):
    app = admin_fixture["app"]
    with app.test_client() as client:
        res, _ = _login(client, "nonexistent_user_999", "SomePassword123!")
        assert res.status_code == 401
        assert res.json["error"]["code"] == "INVALID_CREDENTIALS"

def test_admin_login_lockout_after_consecutive_failures(admin_fixture):
    app = admin_fixture["app"]
    with app.test_client() as client:
        # Reset user
        admin_fixture["user_repo"].update_user(
            admin_fixture["user_repo"].find_by_username("test_owner")["_id"],
            {"failedLoginAttempts": 0, "lockoutUntil": None}
        )
        # 5 consecutive bad logins
        for i in range(5):
            res, _ = _login(client, "test_owner", "BadPass!")
            assert res.status_code == 401

        # 6th attempt must trigger account lockout (423)
        res6, _ = _login(client, "test_owner", "BadPass!")
        assert res6.status_code == 423
        assert res6.json["error"]["code"] == "ACCOUNT_LOCKED"

        # Even with correct password, account remains locked
        res7, _ = _login(client, "test_owner", "OwnerPassword123!")
        assert res7.status_code == 423

        # Clean up lockout
        admin_fixture["user_repo"].update_user(
            admin_fixture["user_repo"].find_by_username("test_owner")["_id"],
            {"failedLoginAttempts": 0, "lockoutUntil": None}
        )

def test_admin_logout(admin_fixture):
    app = admin_fixture["app"]
    with app.test_client() as client:
        res, _ = _login(client, "test_owner", "OwnerPassword123!")
        assert res.status_code == 200

        logout_res = client.post("/api/admin/auth/logout")
        assert logout_res.status_code == 200

        # After logout, accessing protected route must fail with 401
        me_res = client.get("/api/admin/auth/me")
        assert me_res.status_code == 401

def test_admin_csrf_protection(admin_fixture):
    app = admin_fixture["app"]
    with app.test_client() as client:
        res, csrf = _login(client, "test_owner", "OwnerPassword123!")
        assert res.status_code == 200

        # POST without X-CSRF-Token must be rejected with 403
        no_csrf_res = client.post("/api/admin/availability-blocks", json={
            "date": "2026-11-20",
            "startTime": "10:00",
            "durationHours": 2,
            "reason": "Test maintenance"
        })
        assert no_csrf_res.status_code == 403
        assert no_csrf_res.json["error"]["code"] == "CSRF_TOKEN_MISSING"

        # POST with invalid X-CSRF-Token must be rejected with 403
        bad_csrf_res = client.post(
            "/api/admin/availability-blocks",
            json={"date": "2026-11-20", "startTime": "10:00", "durationHours": 2, "reason": "Test maintenance"},
            headers={"X-CSRF-Token": "invalid-token-123"}
        )
        assert bad_csrf_res.status_code == 403
        assert bad_csrf_res.json["error"]["code"] == "CSRF_TOKEN_INVALID"

def test_admin_rbac_permissions(admin_fixture):
    app = admin_fixture["app"]

    # Staff user tests
    with app.test_client() as staff_client:
        res, csrf = _login(staff_client, "test_staff_user", "StaffPassword123!")
        assert res.status_code == 200

        # Staff CAN view bookings
        bookings_res = staff_client.get("/api/admin/bookings")
        assert bookings_res.status_code == 200

        # Staff CANNOT create manual booking (requires owner/manager)
        manual_b_res = staff_client.post(
            "/api/admin/bookings",
            json={
                "packageCode": "basic",
                "date": "2026-11-25",
                "startTime": "11:00",
                "durationHours": 2,
                "customerName": "Test Customer",
                "customerPhone": "9876543210",
                "notes": "Staff attempt"
            },
            headers={"X-CSRF-Token": csrf}
        )
        assert manual_b_res.status_code == 403
        assert manual_b_res.json["error"]["code"] == "FORBIDDEN"

        # Staff CANNOT create availability blocks
        block_res = staff_client.post(
            "/api/admin/availability-blocks",
            json={"date": "2026-11-25", "startTime": "11:00", "durationHours": 2, "reason": "Test"},
            headers={"X-CSRF-Token": csrf}
        )
        assert block_res.status_code == 403

        # Staff CANNOT view payments or audit logs
        pay_res = staff_client.get("/api/admin/payments")
        assert pay_res.status_code == 403
        audit_res = staff_client.get("/api/admin/audit-logs")
        assert audit_res.status_code == 403

    # Manager tests
    with app.test_client() as mgr_client:
        res, csrf = _login(mgr_client, "test_mgr", "ManagerPassword123!")
        assert res.status_code == 200

        # Manager CAN view payments and audit logs
        pay_res = mgr_client.get("/api/admin/payments")
        assert pay_res.status_code == 200
        audit_res = mgr_client.get("/api/admin/audit-logs")
        assert audit_res.status_code == 200

        # Manager CANNOT create a new package (owner only)
        pkg_res = mgr_client.post(
            "/api/admin/packages",
            json={"code": "super_vip", "name": "Super VIP", "pricePerHourMinor": 100000},
            headers={"X-CSRF-Token": csrf}
        )
        assert pkg_res.status_code == 403

def test_admin_availability_block_and_slot_locking(admin_fixture):
    """
    Verifies that creating an availability block locks the slot and prevents
    customer bookings from claiming it.
    """
    app = admin_fixture["app"]
    test_db = admin_fixture["test_db"]

    with app.test_client() as client:
        res, csrf = _login(client, "test_owner", "OwnerPassword123!")
        assert res.status_code == 200

        target_date = "2026-12-10"
        target_time = "14:00"

        # Ensure slot is clean from previous runs
        test_db.slotClaims.delete_many({"roomId": "main"})
        test_db.availabilityBlocks.delete_many({"roomId": "main"})

        # 1. Create availability block
        block_res = client.post(
            "/api/admin/availability-blocks",
            json={
                "date": target_date,
                "startTime": target_time,
                "durationHours": 2,
                "reason": "Facility maintenance and repaint"
            },
            headers={"X-CSRF-Token": csrf}
        )
        assert block_res.status_code == 201
        block_id = block_res.json["data"]["id"]

        # 2. Public customer booking for overlapping slot must fail with 409
        cust_res = client.post(
            "/api/bookings",
            json={
                "packageCode": "basic",
                "date": target_date,
                "startTime": target_time,
                "durationHours": 2,
                "customerName": "Blocked Customer",
                "customerPhone": "9112233445"
            },
            headers={"X-Forwarded-For": "10.88.99.1"}
        )
        assert cust_res.status_code == 409
        assert cust_res.json["error"]["code"] in ("SLOT_UNAVAILABLE", "SLOT_CONFLICT")

        # 3. Delete the block
        del_res = client.delete(
            f"/api/admin/availability-blocks/{block_id}",
            headers={"X-CSRF-Token": csrf}
        )
        assert del_res.status_code == 200

        # 4. Public customer booking now succeeds
        cust_res2 = client.post(
            "/api/bookings",
            json={
                "packageCode": "basic",
                "date": target_date,
                "startTime": target_time,
                "durationHours": 2,
                "customerName": "Unblocked Customer",
                "customerPhone": "9112233446"
            },
            headers={"X-Forwarded-For": "10.88.99.2"}
        )
        assert cust_res2.status_code == 201

def test_admin_availability_block_concurrent_contention(admin_fixture):
    """
    Concurrency test: 20 simultaneous workers attempting to block the same slot.
    Guarantees exactly 1 winner and 19 409 conflicts in MongoDB Atlas.
    """
    app = admin_fixture["app"]

    with app.test_client() as client:
        res, csrf = _login(client, "test_owner", "OwnerPassword123!")
        assert res.status_code == 200
        cookie = client.get_cookie("joybox_admin_session", path="/api/admin")
        assert cookie is not None
        auth_cookie = cookie.value

    target_date = "2026-12-15"
    target_time = "15:00"

    # Clean target slot from previous runs
    admin_fixture["test_db"].slotClaims.delete_many({"roomId": "main"})
    admin_fixture["test_db"].availabilityBlocks.delete_many({"roomId": "main"})

    def attempt_block(worker_idx):
        with app.test_client() as c:
            c.set_cookie("joybox_admin_session", auth_cookie, path="/api/admin")
            resp = c.post(
                "/api/admin/availability-blocks",
                json={
                    "date": target_date,
                    "startTime": target_time,
                    "durationHours": 2,
                    "reason": f"Worker {worker_idx} maintenance"
                },
                headers={
                    "X-CSRF-Token": csrf,
                    "X-Forwarded-For": f"10.0.5.{worker_idx}"
                }
            )
            return resp.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(attempt_block, i) for i in range(20)]
        statuses = [f.result() for f in futures]

    assert statuses.count(201) == 1, f"Expected exactly 1 block winner, got {statuses.count(201)}"
    assert statuses.count(409) == 19, f"Expected 19 conflicts, got {statuses.count(409)}"

def test_admin_audit_logs_populated(admin_fixture):
    """Verifies that audit logs capture administrative actions with actor metadata."""
    app = admin_fixture["app"]
    with app.test_client() as client:
        res, csrf = _login(client, "test_owner", "OwnerPassword123!")
        assert res.status_code == 200

        # Query audit logs
        logs_res = client.get("/api/admin/audit-logs")
        assert logs_res.status_code == 200
        logs = logs_res.json["data"]["auditLogs"]

        assert any(l["action"] == "ADMIN_LOGIN_SUCCESS" for l in logs)
        assert any(l["actorUsername"] == "test_owner" for l in logs)
