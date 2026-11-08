"""
Unit and Integration Tests for Phase 4: Security, Cookie Flags, IP Rate Limiting, ProxyFix, and Operations Hardening.
Tests:
- BUG-05: Admin session cookie respects ADMIN_COOKIE_SECURE and SESSION_COOKIE_SECURE in production and development.
- BUG-10: Mongo-backed IP rate limiting on admin login and inquiries; ProxyFix trusted hop.
- BUG-12: /api/health probes live database connectivity via ping.
- BUG-14: Logging configuration preserves PyMongo INFO visibility while silencing topology noise to WARNING.
"""
import logging
import pytest
from bson import ObjectId
from unittest.mock import MagicMock, patch
from werkzeug.middleware.proxy_fix import ProxyFix

from app import create_app
from app.routes.admin_routes import get_admin_service
from app.services.admin_service import AdminService
from app.utils.datetime_utils import now_utc

class InMemoryCollection:
    def __init__(self):
        self.docs = []

    def insert_one(self, doc):
        d = dict(doc)
        if "_id" not in d:
            d["_id"] = ObjectId()
        self.docs.append(d)
        class Res:
            inserted_id = d["_id"]
        return Res()

    def find_one(self, query=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in (query or {}).items()):
                return dict(d)
        return None

    def find_one_and_update(self, query, update, upsert=False, return_document=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in (query or {}).items()):
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                if "$set" in update:
                    d.update(update["$set"])
                return dict(d)
        if upsert:
            new_doc = dict(query)
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            if "$inc" in update:
                for k, v in update["$inc"].items():
                    new_doc[k] = v
            if "$set" in update:
                new_doc.update(update["$set"])
            self.docs.append(new_doc)
            return dict(new_doc)
        return None

    def update_one(self, query, update, upsert=False):
        return self.find_one_and_update(query, update, upsert=upsert)

class MockDB:
    def __init__(self):
        self.rateLimits = InMemoryCollection()
        self.users = InMemoryCollection()
        self.adminSessions = InMemoryCollection()
        self.auditLogs = InMemoryCollection()
        self.inquiries = InMemoryCollection()

    def command(self, cmd):
        if cmd == "ping":
            return {"ok": 1}
        raise NotImplementedError()


def test_admin_cookie_secure_flag_honored():
    """
    BUG-05: Verify that ADMIN_COOKIE_SECURE is properly read by admin login
    and sets the 'Secure' attribute on the session cookie when enabled.
    """
    # 1. When ADMIN_COOKIE_SECURE is True
    app = create_app({"TESTING": True, "ADMIN_COOKIE_SECURE": True})
    mock_db = MockDB()
    app.extensions["mongo_db"] = mock_db

    # Seed test admin user
    pw_hash = AdminService.hash_password("SecAdminPass123!")
    user_id = ObjectId()
    mock_db.users.docs.append({
        "_id": user_id,
        "username": "sec_admin",
        "displayName": "Security Admin",
        "passwordHash": pw_hash,
        "role": "owner",
        "isActive": True,
        "failedLoginAttempts": 0,
        "lockoutUntil": None,
        "updatedAt": now_utc()
    })

    client = app.test_client()
    res = client.post("/api/admin/auth/login", json={
        "username": "sec_admin",
        "password": "SecAdminPass123!"
    })
    assert res.status_code == 200

    # Inspect Set-Cookie header
    cookie_header = res.headers.get("Set-Cookie", "")
    assert "joybox_admin_session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header

    # 2. When ADMIN_COOKIE_SECURE is False (e.g. local dev without SSL)
    app_insecure = create_app({"TESTING": True, "ADMIN_COOKIE_SECURE": False, "SESSION_COOKIE_SECURE": False})
    app_insecure.extensions["mongo_db"] = mock_db
    client_insecure = app_insecure.test_client()
    res2 = client_insecure.post("/api/admin/auth/login", json={
        "username": "sec_admin",
        "password": "SecAdminPass123!"
    })
    assert res2.status_code == 200
    cookie_header2 = res2.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie_header2
    # In secure=False, Secure flag must NOT be present
    assert "Secure" not in cookie_header2


def test_admin_login_ip_rate_limiting():
    """
    BUG-10: Verify that repeated admin login attempts from the same IP are rate limited
    after exceeding the maximum configured threshold (default 10).
    """
    app = create_app({"TESTING": True, "ENABLE_TEST_RATE_LIMIT": True, "ADMIN_RATE_LIMIT_IP_MAX": 3, "ADMIN_RATE_LIMIT_IP_WINDOW": 60})
    mock_db = MockDB()
    app.extensions["mongo_db"] = mock_db
    client = app.test_client()

    ip_headers = {"X-Forwarded-For": "203.0.113.42"}

    # 3 attempts should be processed (e.g. failing auth)
    for _ in range(3):
        res = client.post("/api/admin/auth/login", json={
            "username": "wrong_user",
            "password": "WrongPassword"
        }, headers=ip_headers)
        assert res.status_code == 401

    # 4th attempt exceeds IP rate limit (max 3) -> 429 RATE_LIMITED
    res_blocked = client.post("/api/admin/auth/login", json={
        "username": "wrong_user",
        "password": "WrongPassword"
    }, headers=ip_headers)
    assert res_blocked.status_code == 429
    assert res_blocked.json["error"]["code"] == "RATE_LIMITED"


def test_inquiries_ip_rate_limiting():
    """
    BUG-10: Verify that public inquiry submissions are rate limited per IP
    to prevent spam and resource exhaustion.
    """
    app = create_app({"TESTING": True, "ENABLE_TEST_RATE_LIMIT": True})
    mock_db = MockDB()
    app.extensions["mongo_db"] = mock_db
    client = app.test_client()

    inquiry_payload = {
        "name": "Spam Tester",
        "phone": "9876543210",
        "email": "tester@example.com",
        "message": "Is Joybox available on Sunday?"
    }
    ip_headers = {"X-Forwarded-For": "198.51.100.25"}

    # 5 inquiries should succeed
    for _ in range(5):
        res = client.post("/api/inquiries", json=inquiry_payload, headers=ip_headers)
        assert res.status_code == 201

    # 6th inquiry should be rate limited
    res_limit = client.post("/api/inquiries", json=inquiry_payload, headers=ip_headers)
    assert res_limit.status_code == 429
    assert res_limit.json["error"]["code"] == "RATE_LIMITED"


def test_health_check_probes_db_connectivity():
    """
    BUG-12: Verify that /api/health actively pings MongoDB and returns 503 if unreachable.
    """
    app = create_app({"TESTING": True, "ENABLE_TEST_RATE_LIMIT": True})
    mock_db = MockDB()
    app.extensions["mongo_db"] = mock_db
    client = app.test_client()

    # 1. Normal connected database
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json["data"]["database"] == "connected"

    # 2. Database ping failure
    mock_db.command = MagicMock(side_effect=Exception("Connection lost"))
    res_unhealthy = client.get("/api/health")
    assert res_unhealthy.status_code == 503
    assert res_unhealthy.json["data"]["database"] == "unavailable"


def test_pymongo_logging_configuration():
    """
    BUG-14: Verify PyMongo root logger is at INFO (preserving diagnostics and slow queries)
    while noisy topology sub-loggers are silenced to WARNING.
    """
    create_app({"TESTING": True})
    assert logging.getLogger("pymongo").level == logging.INFO
    assert logging.getLogger("pymongo.topology").level == logging.WARNING
    assert logging.getLogger("pymongo.serverSelection").level == logging.WARNING


def test_proxy_fix_middleware_applied():
    """
    BUG-10: Verify ProxyFix is attached to the WSGI app for proper reverse proxy handling.
    """
    app = create_app({"TESTING": True, "ENABLE_TEST_RATE_LIMIT": True})
    assert isinstance(app.wsgi_app, ProxyFix)


def test_spoofed_x_forwarded_for_cannot_bypass_rate_limit():
    """
    S1: Verify that an attacker cannot bypass IP rate limiting by spoofing leftmost
    X-Forwarded-For headers. When behind a trusted proxy (TRUSTED_PROXY_COUNT=1),
    ProxyFix evaluates the real client IP from the right, preventing bypass.
    """
    app = create_app({"TESTING": True, "ENABLE_TEST_RATE_LIMIT": True, "TRUSTED_PROXY_COUNT": 1})
    mock_db = MockDB()
    app.extensions["mongo_db"] = mock_db
    client = app.test_client()

    inquiry_payload = {
        "name": "Attacker",
        "phone": "9876543210",
        "email": "attacker@example.com",
        "message": "Spam message"
    }

    # Attacker tries varying the leftmost spoofed IP while the real proxy hop is 198.51.100.25
    # Request 1-5 succeed
    for i in range(5):
        headers = {"X-Forwarded-For": f"10.0.0.{i}, 198.51.100.25"}
        res = client.post("/api/inquiries", json=inquiry_payload, headers=headers)
        assert res.status_code == 201

    # Request 6 from the same real client (even with a new spoofed prefix) must be rate limited
    headers_attack = {"X-Forwarded-For": "10.0.0.99, 198.51.100.25"}
    res_blocked = client.post("/api/inquiries", json=inquiry_payload, headers=headers_attack)
    assert res_blocked.status_code == 429
    assert res_blocked.json["error"]["code"] == "RATE_LIMITED"


def test_production_config_validation_fail_fast():
    """
    D3: Verify that Config.validate_production() fails fast with descriptive errors
    if insecure settings or default keys are present in production.
    """
    from app.config import Config

    orig_env = Config.FLASK_ENV
    orig_debug = Config.DEBUG
    orig_key = Config.JWT_SECRET_KEY
    orig_secure = Config.ADMIN_COOKIE_SECURE
    orig_origin = Config.FRONTEND_ORIGIN
    orig_uri = Config.MONGODB_URI

    try:
        Config.FLASK_ENV = "production"
        Config.DEBUG = False
        Config.JWT_SECRET_KEY = "dev-secret-key-change-in-prod"
        Config.ADMIN_COOKIE_SECURE = False
        Config.FRONTEND_ORIGIN = "*"
        Config.MONGODB_URI = "mongodb+srv://<username>:<password>@cluster0.mongodb.net/joybox_party_room"

        with pytest.raises(ValueError) as excinfo:
            Config.validate_production()

        err_msg = str(excinfo.value)
        assert "MONGODB_URI" in err_msg
        assert "JWT_SECRET_KEY" in err_msg
        assert "FRONTEND_ORIGIN" in err_msg
        assert "ADMIN_COOKIE_SECURE" in err_msg
    finally:
        Config.FLASK_ENV = orig_env
        Config.DEBUG = orig_debug
        Config.JWT_SECRET_KEY = orig_key
        Config.ADMIN_COOKIE_SECURE = orig_secure
        Config.FRONTEND_ORIGIN = orig_origin
        Config.MONGODB_URI = orig_uri

