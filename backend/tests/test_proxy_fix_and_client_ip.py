"""
Tests for ProxyFix and TRUSTED_PROXY_COUNT Behavior:
- count=0: untrusted reverse proxy headers (remote_addr remains direct socket IP)
- count=1: Render single-reverse-proxy topology (accurately unwraps 1 hop)
- Spoofed multi-value X-Forwarded-For: prevents spoofed IP bypass
- Rate limit keys: strictly derived from the sanitized remote_addr
"""
import pytest
from bson import ObjectId
from flask import request
from app import create_app
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
        self.inquiries = InMemoryCollection()
        self.users = InMemoryCollection()
        self.adminSessions = InMemoryCollection()
        self.auditLogs = InMemoryCollection()

    def command(self, cmd):
        if cmd == "ping":
            return {"ok": 1}
        raise NotImplementedError()


def test_proxy_count_zero_ignores_forwarded_headers():
    """
    When TRUSTED_PROXY_COUNT is 0, ProxyFix is not applied (trusted_proxy_count=0).
    The application must ignore any X-Forwarded-For header and use the socket IP.
    """
    app = create_app({"TESTING": True, "TRUSTED_PROXY_COUNT": 0})
    app.extensions["mongo_db"] = MockDB()
    client = app.test_client()

    with client:
        res = client.get(
            "/api/health",
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
            headers={"X-Forwarded-For": "203.0.113.50"}
        )
        assert res.status_code == 200
        # remote_addr should NOT be rewritten to the forwarded header
        assert request.remote_addr == "127.0.0.1"


def test_proxy_count_one_render_topology_unwraps_single_hop():
    """
    Render uses a single reverse proxy (TRUSTED_PROXY_COUNT=1).
    ProxyFix must unwrap exactly 1 hop from X-Forwarded-For.
    """
    app = create_app({"TESTING": True, "TRUSTED_PROXY_COUNT": 1})
    app.extensions["mongo_db"] = MockDB()
    client = app.test_client()

    with client:
        res = client.get(
            "/api/health",
            environ_base={"REMOTE_ADDR": "10.0.0.5"},
            headers={"X-Forwarded-For": "203.0.113.99"}
        )
        assert res.status_code == 200
        assert request.remote_addr == "203.0.113.99"


def test_spoofed_multi_value_x_forwarded_for():
    """
    Attacker attempts to spoof their client IP by sending:
    X-Forwarded-For: 198.51.100.77 (attacker fake IP)
    The trusted Render proxy appends the real connecting IP (203.0.113.99):
    Header received by backend: '198.51.100.77, 203.0.113.99'
    With TRUSTED_PROXY_COUNT=1, ProxyFix must trust only the rightmost hop (203.0.113.99)
    and reject the spoofed 198.51.100.77.
    """
    app = create_app({"TESTING": True, "TRUSTED_PROXY_COUNT": 1})
    app.extensions["mongo_db"] = MockDB()
    client = app.test_client()

    with client:
        res = client.get(
            "/api/health",
            environ_base={"REMOTE_ADDR": "10.0.0.5"},
            headers={"X-Forwarded-For": "198.51.100.77, 203.0.113.99"}
        )
        assert res.status_code == 200
        assert request.remote_addr == "203.0.113.99"
        assert request.remote_addr != "198.51.100.77"


def test_rate_limit_key_derived_from_sanitized_ip_not_spoofed_prefix():
    """
    Verifies that rate limiting on public inquiry route derives rate-limit key
    from the sanitized client IP (203.0.113.99) and cannot be bypassed by changing
    the spoofed X-Forwarded-For prefix.
    """
    app = create_app({
        "TESTING": True,
        "ENABLE_TEST_RATE_LIMIT": True,
        "TRUSTED_PROXY_COUNT": 1
    })
    mock_db = MockDB()
    app.extensions["mongo_db"] = mock_db
    client = app.test_client()

    inquiry_data = {
        "name": "Attacker Test",
        "phone": "+919876543210",
        "message": "Testing IP rate limit key derivation"
    }

    # First 5 submissions with spoofed prefix 1.1.1.i, real proxy IP 203.0.113.99
    for i in range(5):
        res = client.post(
            "/api/inquiries",
            json=inquiry_data,
            environ_base={"REMOTE_ADDR": "10.0.0.5"},
            headers={"X-Forwarded-For": f"1.1.1.{i}, 203.0.113.99"}
        )
        assert res.status_code == 201

    # 6th submission with a different spoofed prefix 8.8.8.8, but SAME real proxy IP 203.0.113.99
    res_blocked = client.post(
        "/api/inquiries",
        json=inquiry_data,
        environ_base={"REMOTE_ADDR": "10.0.0.5"},
        headers={"X-Forwarded-For": "8.8.8.8, 203.0.113.99"}
    )
    # Must be blocked (429) because rate-limit key was derived from 203.0.113.99!
    assert res_blocked.status_code == 429
    assert res_blocked.json["error"]["code"] == "RATE_LIMITED"

    # Verify rate limit record in mock db is keyed on inquiry:203.0.113.99
    rate_doc = mock_db.rateLimits.find_one({"key": "inquiry:203.0.113.99"})
    assert rate_doc is not None
    assert rate_doc.get("count", 0) >= 5


def test_two_proxy_chain_uses_browser_ip_for_rate_limit():
    """
    Vercel then Render append two X-Forwarded-For hops.
    With TRUSTED_PROXY_COUNT=2 the rate-limit key is the browser IP,
    and a spoofed prefix further left is ignored.
    """
    app = create_app({
        "TESTING": True,
        "ENABLE_TEST_RATE_LIMIT": True,
        "TRUSTED_PROXY_COUNT": 2,
    })
    mock_db = MockDB()
    app.extensions["mongo_db"] = mock_db
    client = app.test_client()

    with client:
        res = client.get(
            "/api/health",
            environ_base={"REMOTE_ADDR": "10.0.0.8"},
            headers={"X-Forwarded-For": "203.0.113.10, 198.51.100.20"},
        )
        assert res.status_code == 200
        assert request.remote_addr == "203.0.113.10"

        spoofed = client.get(
            "/api/health",
            environ_base={"REMOTE_ADDR": "10.0.0.8"},
            headers={"X-Forwarded-For": "198.51.100.77, 203.0.113.10, 198.51.100.20"},
        )
        assert spoofed.status_code == 200
        assert request.remote_addr == "203.0.113.10"

    inquiry = {"name": "Proxy Chain", "phone": "9876543210", "message": "Two hop check"}
    for i in range(5):
        ok = client.post(
            "/api/inquiries",
            json=inquiry,
            environ_base={"REMOTE_ADDR": "10.0.0.8"},
            headers={"X-Forwarded-For": f"1.2.3.{i}, 203.0.113.10, 198.51.100.20"},
        )
        assert ok.status_code == 201

    blocked = client.post(
        "/api/inquiries",
        json=inquiry,
        environ_base={"REMOTE_ADDR": "10.0.0.8"},
        headers={"X-Forwarded-For": "8.8.8.8, 203.0.113.10, 198.51.100.20"},
    )
    assert blocked.status_code == 429
    assert mock_db.rateLimits.find_one({"key": "inquiry:203.0.113.10"}) is not None


def test_vercel_origin_is_accepted_when_host_is_render():
    app = create_app({
        "TESTING": True,
        "FRONTEND_ORIGIN": "https://joybox.vercel.app",
        "ENABLE_TEST_RATE_LIMIT": True,
    })
    app.extensions["mongo_db"] = MockDB()
    client = app.test_client()
    payload = {"name": "Origin Check", "phone": "9876543210", "message": "Cross host origin"}
    allowed = client.post(
        "/api/inquiries",
        json=payload,
        headers={
            "Origin": "https://joybox.vercel.app",
            "Host": "joybox-backend.onrender.com",
        },
    )
    assert allowed.status_code == 201

    rejected = client.post(
        "/api/inquiries",
        json=payload,
        headers={
            "Origin": "https://evil.example",
            "Host": "joybox-backend.onrender.com",
        },
    )
    assert rejected.status_code == 403
    assert rejected.json["error"]["code"] == "ORIGIN_REJECTED"


def test_api_security_headers_include_csp_permissions_and_hsts():
    app = create_app({"TESTING": True})
    client = app.test_client()
    res = client.get("/api/health", base_url="https://joybox-backend.onrender.com")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert res.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert res.headers["Content-Security-Policy"] == "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    assert res.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert res.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    plain = client.get("/api/health")
    assert "Strict-Transport-Security" not in plain.headers
