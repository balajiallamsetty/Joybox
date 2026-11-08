import pytest
from app import create_app

@pytest.fixture
def disabled_client():
    app = create_app({"TESTING": True, "PAYMENTS_ENABLED": False})
    with app.test_client() as c:
        yield c

@pytest.fixture
def enabled_client():
    app = create_app({
        "TESTING": True,
        "PAYMENTS_ENABLED": True,
        "RAZORPAY_KEY_ID": "rzp_test_fixture",
        "RAZORPAY_KEY_SECRET": "secret_test_fixture",
    })
    with app.test_client() as c:
        yield c

def test_payments_disabled_returns_403_on_all_endpoints(disabled_client):
    """When PAYMENTS_ENABLED is False, all payment endpoints return 403 PAYMENTS_DISABLED."""
    endpoints = [
        "/api/payments/create-order",
        "/api/payments/verify",
        "/api/payments/verify-payment",
        "/api/payments/webhook",
        "/api/payments/refund",
        "/api/create-order",
        "/api/verify-payment",
    ]
    for ep in endpoints:
        res = disabled_client.post(ep, json={"dummy": "value"})
        assert res.status_code == 403, f"Endpoint {ep} should return 403 when payments disabled"
        data = res.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "PAYMENTS_DISABLED"
        assert "disabled" in data["error"]["message"].lower()

def test_public_config_reports_payments_status(disabled_client, enabled_client):
    """GET /api/public-config reflects the server PAYMENTS_ENABLED state accurately."""
    res_disabled = disabled_client.get("/api/public-config")
    assert res_disabled.status_code == 200
    data_disabled = res_disabled.get_json()["data"]
    assert data_disabled["paymentsEnabled"] is False

    res_enabled = enabled_client.get("/api/public-config")
    assert res_enabled.status_code == 200
    data_enabled = res_enabled.get_json()["data"]
    assert data_enabled["paymentsEnabled"] is True

