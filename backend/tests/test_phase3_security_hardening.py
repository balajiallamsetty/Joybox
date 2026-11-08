"""
Phase 3 Security Hardening Test Suite
Author: Principal Engineer, Application-Security Auditor & QA Lead
Target Database: joybox_party_room_test (Atlas)

Objective:
Verify production configuration validation, fast-fail guards, Admin RBAC negative
security boundaries, CSRF enforcement, and NoSQL injection resilience.
"""

import os
import uuid
import pytest
from app import create_app
from app.config import Config
from app.repositories import (
    UserRepository,
    AdminSessionRepository,
    AuditLogRepository,
)
from app.services.admin_service import AdminService
from app.utils.datetime_utils import now_utc
from app.utils.db_safety import assert_live_test_client


@pytest.fixture
def security_test_setup(live_test_client):
    test_db = live_test_client
    assert_live_test_client(test_db.client, test_db.name)
    app = create_app({"TESTING": True, "MONGODB_URI": os.getenv("MONGODB_URI"), "MONGODB_DB": test_db.name})
    app.extensions["mongo_db"] = test_db

    user_repo = UserRepository(test_db)
    session_repo = AdminSessionRepository(test_db)
    audit_repo = AuditLogRepository(test_db)

    app.extensions["user_repo"] = user_repo
    app.extensions["admin_session_repo"] = session_repo
    app.extensions["audit_repo"] = audit_repo

    # Seed test users
    now_u = now_utc()
    user_repo.collection.update_one(
        {"username": "sec_owner"},
        {"$set": {
            "username": "sec_owner",
            "email": "owner@joybox.sec",
            "displayName": "Security Owner",
            "passwordHash": AdminService.hash_password("OwnerPassword123!"),
            "role": "owner",
            "isActive": True,
            "failedLoginAttempts": 0,
            "lockoutUntil": None,
            "updatedAt": now_u
        }},
        upsert=True
    )

    user_repo.collection.update_one(
        {"username": "sec_viewer"},
        {"$set": {
            "username": "sec_viewer",
            "email": "viewer@joybox.sec",
            "displayName": "Security Viewer",
            "passwordHash": AdminService.hash_password("ViewerPassword123!"),
            "role": "viewer",
            "isActive": True,
            "failedLoginAttempts": 0,
            "lockoutUntil": None,
            "updatedAt": now_u
        }},
        upsert=True
    )

    return {
        "app": app,
        "db": test_db,
        "user_repo": user_repo,
        "session_repo": session_repo,
    }


# =====================================================================
# 1. FAST-FAIL ENVIRONMENT VALIDATION TESTS
# =====================================================================

def test_fast_fail_production_insecure_jwt_secret():
    """Config.validate_production must raise ValueError if JWT_SECRET_KEY is insecure in production."""
    original_jwt = Config.JWT_SECRET_KEY
    original_db = Config.MONGODB_URI
    original_env = Config.FLASK_ENV
    original_debug = Config.DEBUG
    try:
        Config.FLASK_ENV = "production"
        Config.DEBUG = False
        Config.JWT_SECRET_KEY = "dev-secret-key-change-in-prod"
        Config.MONGODB_URI = "mongodb://localhost:27017/joybox_prod"
        with pytest.raises(ValueError) as excinfo:
            Config.validate_production()
        assert "JWT_SECRET_KEY" in str(excinfo.value)
    finally:
        Config.JWT_SECRET_KEY = original_jwt
        Config.MONGODB_URI = original_db
        Config.FLASK_ENV = original_env
        Config.DEBUG = original_debug


def test_fast_fail_production_missing_mongodb_uri():
    """Config.validate_production must raise ValueError if MONGODB_URI is empty in production."""
    original_db = Config.MONGODB_URI
    original_env = Config.FLASK_ENV
    original_debug = Config.DEBUG
    try:
        Config.FLASK_ENV = "production"
        Config.DEBUG = False
        Config.MONGODB_URI = ""
        with pytest.raises(ValueError) as excinfo:
            Config.validate_production()
        assert "MONGODB_URI" in str(excinfo.value)
    finally:
        Config.MONGODB_URI = original_db
        Config.FLASK_ENV = original_env
        Config.DEBUG = original_debug


# =====================================================================
# 2. ADMIN RBAC & CSRF NEGATIVE TESTS
# =====================================================================

def test_admin_unauthenticated_request_rejected(security_test_setup):
    """Accessing protected admin routes without session cookie must return 401."""
    app = security_test_setup["app"]
    with app.test_client() as client:
        res = client.get("/api/admin/bookings")
        assert res.status_code == 401
        assert res.json["error"]["code"] in ("UNAUTHORIZED", "AUTH_REQUIRED")


def test_admin_tampered_session_rejected(security_test_setup):
    """Accessing admin routes with invalid or forged session cookie must return 401."""
    app = security_test_setup["app"]
    with app.test_client() as client:
        client.set_cookie("joybox_admin_session", "forged-session-token-12345")
        res = client.get("/api/admin/bookings")
        assert res.status_code == 401


def test_admin_mutating_request_missing_csrf_rejected(security_test_setup):
    """Mutating admin request without valid CSRF header must return 403 Forbidden."""
    app = security_test_setup["app"]
    with app.test_client() as client:
        # 1. Log in as owner to get valid session
        login_res = client.post("/api/admin/auth/login", json={
            "username": "sec_owner",
            "password": "OwnerPassword123!"
        })
        assert login_res.status_code == 200

        # 2. Attempt mutating action (creating availability block) WITHOUT X-CSRF-Token header
        block_res = client.post("/api/admin/availability-blocks", json={
            "date": "2026-12-29",
            "startTime": "10:00",
            "durationHours": 2,
            "reason": "Security Test Block"
        })
        assert block_res.status_code == 403
        assert "csrf" in block_res.json["error"]["message"].lower() or block_res.json["error"]["code"] == "CSRF_ERROR"


def test_admin_mutating_request_with_valid_csrf_accepted(security_test_setup):
    """Mutating admin request with valid session and matching CSRF header succeeds."""
    app = security_test_setup["app"]
    db = security_test_setup["db"]
    # Clean test slot
    db.availabilityBlocks.delete_many({"reason": "Security Test Block With CSRF"})

    with app.test_client() as client:
        login_res = client.post("/api/admin/auth/login", json={
            "username": "sec_owner",
            "password": "OwnerPassword123!"
        })
        assert login_res.status_code == 200
        csrf_token = login_res.json["data"]["csrfToken"]

        # Mutating action with correct CSRF token
        block_res = client.post(
            "/api/admin/availability-blocks",
            json={
                "date": "2026-12-29",
                "startTime": "10:00",
                "durationHours": 2,
                "reason": "Security Test Block With CSRF"
            },
            headers={"X-CSRF-Token": csrf_token}
        )
        assert block_res.status_code == 201


def test_admin_viewer_role_forbidden_from_admin_mutations(security_test_setup):
    """Users with viewer role cannot perform manager/owner mutating operations."""
    app = security_test_setup["app"]
    with app.test_client() as client:
        # Log in as viewer
        login_res = client.post("/api/admin/auth/login", json={
            "username": "sec_viewer",
            "password": "ViewerPassword123!"
        })
        assert login_res.status_code == 200
        csrf_token = login_res.json["data"]["csrfToken"]

        # Viewer attempts to create an availability block (owner/manager only)
        block_res = client.post(
            "/api/admin/availability-blocks",
            json={
                "date": "2026-12-30",
                "startTime": "14:00",
                "durationHours": 2,
                "reason": "Unauthorized Viewer Block"
            },
            headers={"X-CSRF-Token": csrf_token}
        )
        assert block_res.status_code == 403


# =====================================================================
# 3. NOSQL INJECTION DEFENSE TESTS
# =====================================================================

def test_nosql_injection_in_quote_request_rejected(security_test_setup):
    """Injecting MongoDB operator dicts like {'$gt': ''} into quote request is rejected with 422."""
    app = security_test_setup["app"]
    with app.test_client() as client:
        res = client.post("/api/bookings/quote", json={
            "packageCode": {"$gt": ""},
            "durationHours": {"$ne": 0}
        })
        assert res.status_code == 422


def test_nosql_injection_in_hold_request_rejected(security_test_setup):
    """Injecting MongoDB operator dicts into hold request is rejected with 422."""
    app = security_test_setup["app"]
    with app.test_client() as client:
        res = client.post("/api/bookings/hold", json={
            "packageCode": "basic",
            "durationHours": 1,
            "date": {"$regex": ".*"},
            "startTime": {"$gt": "00:00"},
            "customerName": "Attacker",
            "customerPhone": "+919876543210"
        })
        assert res.status_code == 422


def test_nosql_injection_in_booking_lookup_returns_404_not_leak(security_test_setup):
    """Attempting operator injection via booking reference route returns 404 and does not dump database."""
    app = security_test_setup["app"]
    with app.test_client() as client:
        res = client.get('/api/bookings/{"$gt": ""}')
        assert res.status_code == 404
        assert res.json.get("success") is False
